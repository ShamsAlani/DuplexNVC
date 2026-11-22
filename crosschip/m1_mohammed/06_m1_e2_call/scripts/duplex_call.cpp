// duplex_call.cpp: one endpoint of a REAL two-laptop call for E2 (DuplexNVC plan, section 8).
// Built from baseline/common/code/duplex_bench.cpp: the codec calls, the pacing, the dropped-frame rule and the
// frames.csv format are the same, so analyze_run.py reads a call run exactly like a bench run. What is new:
//   * the encoder's access units go to the other laptop over UDP (fragments of <= --mtu bytes) instead of staying
//     in memory, and the decoder decodes what arrives from the other laptop instead of a stored incoming stream;
//   * every packet carries a send time and echoes the last time stamp it received, so each side measures the
//     round trip and the clock offset to the peer (NTP-style) and can correct one-way delays (clock.csv);
//   * lost and incomplete frames are counted; a frame that arrives after a gap is still given to the decoder, so
//     the decoder's own recovery (fail until the next I-frame) is what the log shows.
// Usage (the same on both laptops, each with the other's address):
//   duplex_call --peer 192.168.1.20 --port 5600 --input cam.nv12 --size 640x360 --qp 26 --iframe-period 64
//               --bundles <dir> --enc-cu npu --dec-cu npu --fps 30 --seconds 60 --out-dir <dir> [--mtu 1200]
//               [--listen-port 5600] [--start-at <epoch seconds>]
// Loopback test on one Mac: two processes with --peer 127.0.0.1, --port 5601 --listen-port 5600 and the reverse.
// Output: frames.csv (E rows: sent frames; D rows: received+decoded frames), clock.csv (rtt, offset), received.aus
// and received.mlvc (what arrived, in decode order, for an offline decode with `mlvc decode`), run.txt.
// NOT compiled in the cloud session that wrote it: build it with ./m1_call_build and run the loopback test first.
#include <libmlvc/libmlvc.hpp>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

using namespace libmlvc;
using Clock = std::chrono::steady_clock;
namespace fs = std::filesystem;

struct Args {
    std::string peer = "127.0.0.1";
    int port = 5600, listenPort = -1;
    std::string input;
    int width = 640, height = 360;
    std::string outDir = "call";
    std::string bundles;
    std::string encCu = "npu", decCu = "npu";
    int qp = 26;
    int iframePeriod = 64;
    double fps = 30.0;
    double deadlineMs = 0.0;
    int seconds = 60;
    int warmupFrames = 64;
    int mtu = 1200;
    double startAt = 0.0;  // epoch seconds; 0 = start 2 s after launch
};

static Args ParseArgs(int argc, char** argv)
{
    Args a;
    for (int i = 1; i + 1 < argc; i += 2) {
        std::string k = argv[i], v = argv[i + 1];
        if (k == "--peer") a.peer = v;
        else if (k == "--port") a.port = std::stoi(v);
        else if (k == "--listen-port") a.listenPort = std::stoi(v);
        else if (k == "--input") a.input = v;
        else if (k == "--size") std::sscanf(v.c_str(), "%dx%d", &a.width, &a.height);
        else if (k == "--out-dir") a.outDir = v;
        else if (k == "--bundles") a.bundles = v;
        else if (k == "--enc-cu") a.encCu = v;
        else if (k == "--dec-cu") a.decCu = v;
        else if (k == "--qp") a.qp = std::stoi(v);
        else if (k == "--iframe-period") a.iframePeriod = std::stoi(v);
        else if (k == "--fps") a.fps = std::stod(v);
        else if (k == "--deadline-ms") a.deadlineMs = std::stod(v);
        else if (k == "--seconds") a.seconds = std::stoi(v);
        else if (k == "--warmup-frames") a.warmupFrames = std::stoi(v);
        else if (k == "--mtu") a.mtu = std::stoi(v);
        else if (k == "--start-at") a.startAt = std::stod(v);
        else { std::cerr << "unknown option " << k << "\n"; std::exit(2); }
    }
    if (a.input.empty() || a.bundles.empty()) {
        std::cerr << "usage: duplex_call --peer <ip> --port <p> --input cam.nv12 --size WxH --bundles <dir> [options]\n";
        std::exit(2);
    }
    if (a.listenPort < 0) a.listenPort = a.port;
    if (a.deadlineMs <= 0.0) a.deadlineMs = a.fps > 0 ? 1000.0 / a.fps : 33.333;
    if (a.fps <= 0) { std::cerr << "a call must be paced: --fps > 0\n"; std::exit(2); }
    return a;
}

// ---------- packet format (little-endian, 44 bytes) ----------
#pragma pack(push, 1)
struct PktHdr {
    uint32_t magic;      // 'DNVC'
    uint32_t frame;      // sequence number of the access unit: 0 = the warm-up IDR, 1, 2, ... for every frame actually
                         // encoded (frames the sender drops are never numbered, so a gap means a frame lost in the
                         // network); 0xFFFFFFFF = bye
    uint16_t frag, nfrag;
    uint32_t len;        // whole access unit in bytes
    uint64_t sendUs;     // sender's system clock at send, epoch microseconds (t1 / t3)
    uint64_t echoT1Us;   // sendUs of the last packet this side received from the peer (0 = none yet)
    uint64_t echoT2Us;   // this side's clock when that packet arrived
    uint8_t frameType;   // 0 I, 1 P, 2 LTR recovery
    uint8_t pad[3];
};
#pragma pack(pop)
static_assert(sizeof(PktHdr) == 44, "packet header size");
static const uint32_t MAGIC = 0x43564E44;  // "DNVC"
static const uint32_t BYE = 0xFFFFFFFFu;

static uint64_t NowUs()
{
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
}

// ---------- I/O helpers (as in duplex_bench) ----------
static std::vector<std::vector<std::byte>> LoadNv12(const std::string& path, int w, int h)
{
    const size_t frameBytes = static_cast<size_t>(w) * h * 3 / 2;
    std::ifstream f(path, std::ios::binary);
    if (!f) { std::cerr << "cannot open " << path << "\n"; std::exit(1); }
    std::vector<std::vector<std::byte>> frames;
    while (true) {
        std::vector<std::byte> buf(frameBytes);
        if (!f.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(frameBytes))) break;
        frames.push_back(std::move(buf));
    }
    if (frames.empty()) { std::cerr << "no complete frames in " << path << "\n"; std::exit(1); }
    return frames;
}

static void WriteAusAndMlvc(const std::string& stem, const std::vector<std::vector<std::byte>>& aus)
{
    std::ofstream a(stem + ".aus", std::ios::binary), m(stem + ".mlvc", std::ios::binary);
    for (const auto& au : aus) {
        uint32_t n = static_cast<uint32_t>(au.size());
        a.write(reinterpret_cast<const char*>(&n), 4);
        a.write(reinterpret_cast<const char*>(au.data()), n);
        m.write(reinterpret_cast<const char*>(au.data()), n);
    }
}

static MlvcManager MakeManager(const Args& a, const std::string& cuName)
{
    ComputeUnit cu = cuName == "npu" ? ComputeUnit::NPU : cuName == "gpu" ? ComputeUnit::GPU
                   : cuName == "cpu" ? ComputeUnit::CPU : ComputeUnit::AUTO;
    ManagerParams p{};
    p.computeUnit = cu;
    auto m = MlvcManager::CreateFromDirectory(p, a.bundles);
    if (!m) { std::cerr << "manager init failed: " << m.error().message() << "\n"; std::exit(1); }
    std::cerr << "manager: requested=" << ComputeUnitToString(cu)
              << " resolved=" << ComputeUnitToString(m->GetInfo().computeUnit) << "\n";
    return m.value();
}

static MlvcEncoder MakeEncoder(const MlvcManager& m, const Args& a)
{
    const auto version = m.GetAvailableVersions().front();
    auto cfg = m.GetDefaultEncoderConfig(version);
    if (!cfg) { std::cerr << "config failed\n"; std::exit(1); }
    std::cerr << "model " << version.ToString() << " default iframe_period=" << cfg->iframePeriod
              << " -> using " << a.iframePeriod << "\n";
    cfg->SetSize(a.width, a.height);
    cfg->iframePeriod = a.iframePeriod;
    auto e = m.CreateEncoder(cfg.value());
    if (!e) { std::cerr << "encoder failed: " << e.error().message() << "\n"; std::exit(1); }
    return std::move(e.value());
}

// ---------- per-frame record: duplex_bench's columns plus the network columns ----------
struct Rec {
    char dir;
    long k, src;
    double schedMs, startMs, endMs, inferMs, totalMs;
    int frameType;
    size_t bytes;
    int ok;
    int pkts = 0;          // fragments sent (E) or received (D)
    uint64_t sendUs = 0;   // E: last fragment sent; D: peer's send time of this frame (its clock)
    uint64_t firstUs = 0;  // D: first fragment arrived (this clock)
    uint64_t lastUs = 0;   // D: last fragment arrived = frame complete
    long lostBefore = 0;   // D: frames of the peer that never completed before this one
};

static void WriteCsv(const std::string& path, const std::vector<Rec>& recs, const Args& a)
{
    std::ofstream f(path);
    f << "dir,slot,src,sched_ms,start_ms,end_ms,service_ms,latency_ms,late,infer_ms,call_ms,frame_type,bytes,ok,warmup,"
         "pkts,send_us,first_recv_us,complete_recv_us,lost_before\n";
    for (const auto& r : recs) {
        const double latency = r.endMs - r.schedMs;
        const bool late = latency > a.deadlineMs;
        f << r.dir << ',' << r.k << ',' << r.src << ',' << r.schedMs << ',' << r.startMs << ',' << r.endMs << ','
          << (r.endMs - r.startMs) << ',' << latency << ',' << late << ',' << r.inferMs << ',' << r.totalMs << ','
          << r.frameType << ',' << r.bytes << ',' << r.ok << ',' << (r.k < a.warmupFrames) << ','
          << r.pkts << ',' << r.sendUs << ',' << r.firstUs << ',' << r.lastUs << ',' << r.lostBefore << '\n';
    }
}

static double Ms(Clock::time_point t, Clock::time_point t0)
{
    return std::chrono::duration<double, std::milli>(t - t0).count();
}

int main(int argc, char** argv)
{
    const Args a = ParseArgs(argc, argv);
    fs::create_directories(a.outDir);
    const auto period = std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double, std::milli>(1000.0 / a.fps));

    // ---- socket ----
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) { perror("socket"); return 1; }
    int one = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    int buf = 4 << 20;
    setsockopt(sock, SOL_SOCKET, SO_RCVBUF, &buf, sizeof(buf));
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buf, sizeof(buf));
    timeval tv{ 0, 100000 };  // 100 ms receive timeout so the receiver can notice the end of the run
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    sockaddr_in me{};
    me.sin_family = AF_INET; me.sin_addr.s_addr = htonl(INADDR_ANY); me.sin_port = htons(static_cast<uint16_t>(a.listenPort));
    if (bind(sock, reinterpret_cast<sockaddr*>(&me), sizeof(me)) < 0) { perror("bind"); return 1; }
    sockaddr_in peer{};
    peer.sin_family = AF_INET; peer.sin_port = htons(static_cast<uint16_t>(a.port));
    if (inet_pton(AF_INET, a.peer.c_str(), &peer.sin_addr) != 1) { std::cerr << "bad peer address " << a.peer << "\n"; return 1; }

    // ---- codec ----
    auto frames = LoadNv12(a.input, a.width, a.height);
    std::map<std::string, MlvcManager> managers;
    auto getManager = [&](const std::string& cu) -> MlvcManager& {
        auto it = managers.find(cu);
        if (it == managers.end()) it = managers.emplace(cu, MakeManager(a, cu)).first;
        return it->second;
    };
    MlvcEncoder enc = MakeEncoder(getManager(a.encCu), a);
    auto d = getManager(a.decCu).CreateDecoder();
    if (!d) { std::cerr << "decoder failed\n"; return 1; }
    MlvcDecoder dec = std::move(d.value());

    // Pre-warm the encoder (the first call initialises the model); the first IDR is sent at slot -1 so the peer's
    // decoder can start from it. The decoder is warmed by the peer's first frame.
    std::vector<Rec> sendRecs, recvRecs;
    std::vector<std::vector<std::byte>> received;
    std::vector<std::vector<std::byte>> outAus;
    std::atomic<uint64_t> lastRxSendUs{ 0 }, lastRxArriveUs{ 0 };  // for the NTP-style echo
    std::mutex clockMu;
    std::vector<std::array<double, 3>> clockRows;                 // t4 epoch s, rtt ms, offset ms (peer - me)
    long dropped = 0, lostFrames = 0, incomplete = 0, failures = 0;

    const size_t payloadMax = static_cast<size_t>(a.mtu) - sizeof(PktHdr);
    auto sendAu = [&](uint32_t frame, const std::vector<std::byte>& au, uint8_t ft) -> std::pair<int, uint64_t> {
        const uint32_t nfrag = static_cast<uint32_t>((au.size() + payloadMax - 1) / payloadMax);
        std::vector<char> pkt(sizeof(PktHdr) + payloadMax);
        uint64_t last = 0;
        for (uint32_t i = 0; i < std::max<uint32_t>(nfrag, 1); ++i) {
            PktHdr h{};
            h.magic = MAGIC; h.frame = frame; h.frag = static_cast<uint16_t>(i); h.nfrag = static_cast<uint16_t>(std::max<uint32_t>(nfrag, 1));
            h.len = static_cast<uint32_t>(au.size()); h.frameType = ft;
            h.echoT1Us = lastRxSendUs.load(); h.echoT2Us = lastRxArriveUs.load();
            const size_t off = i * payloadMax, n = std::min(payloadMax, au.size() - off);
            h.sendUs = last = NowUs();
            std::memcpy(pkt.data(), &h, sizeof(h));
            if (n) std::memcpy(pkt.data() + sizeof(h), au.data() + off, n);
            sendto(sock, pkt.data(), sizeof(h) + n, 0, reinterpret_cast<sockaddr*>(&peer), sizeof(peer));
        }
        return { static_cast<int>(std::max<uint32_t>(nfrag, 1)), last };
    };

    {
        const auto s = Clock::now();
        auto r = enc.Encode(Nv12FrameView(a.width, a.height, frames[0]), EncodeParams{ .qp = QpParams(a.qp) });
        std::cerr << "encoder first-frame (init) ms: " << Ms(Clock::now(), s) << (r ? "" : " FAILED") << "\n";
        if (!r) { std::cerr << "the encoder could not encode the first frame\n"; return 1; }
        outAus.emplace_back(r->bitStream.begin(), r->bitStream.end());
        Rec rec{ 'E', -1, 0, 0, 0, 0, 0, 0, static_cast<int>(r->info.frameType), r->bitStream.size(), 1 };
        sendRecs.push_back(rec);  // sent at t0, below, so that the peer is listening
    }

    // ---- start time: shared (--start-at) or 2 s from now ----
    Clock::time_point t0;
    double t0EpochMs;
    if (a.startAt > 0) {
        const double waitS = a.startAt - NowUs() / 1e6;
        if (waitS < 0) { std::cerr << "--start-at is in the past\n"; return 1; }
        t0 = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(waitS));
        t0EpochMs = a.startAt * 1000.0;
    } else {
        t0 = Clock::now() + std::chrono::seconds(2);
        t0EpochMs = NowUs() / 1000.0 + 2000.0;
    }
    const auto tEnd = t0 + std::chrono::seconds(a.seconds);
    std::atomic<bool> peerDone{ false };
    std::cerr << "call: peer " << a.peer << ":" << a.port << ", listening on " << a.listenPort << ", start in "
              << Ms(t0, Clock::now()) / 1000.0 << " s\n";

    // ---- sender: the camera delivers frame k at t0 + k*period; missed frames are dropped (as in duplex_bench) ----
    auto sendLoop = [&] {
        std::this_thread::sleep_until(t0 - std::chrono::milliseconds(50));
        {   // the warm-up IDR is sequence number 0
            auto [n, t] = sendAu(0u, outAus[0], static_cast<uint8_t>(sendRecs[0].frameType));
            sendRecs[0].pkts = n; sendRecs[0].sendUs = t;
        }
        uint32_t seq = 1;
        long k = 0;
        while (true) {
            auto now = Clock::now();
            if (now > t0 + period) {
                const long newest = static_cast<long>((now - t0) / period);
                if (newest > k) { dropped += newest - k; k = newest; }
            }
            const auto sched = t0 + k * period;
            if (sched >= tEnd) break;
            std::this_thread::sleep_until(sched);
            const long src = k % static_cast<long>(frames.size());
            Rec r{ 'E', k, src, Ms(sched, t0), 0, 0, 0, 0, 0, 0, 0 };
            const auto s = Clock::now();
            auto res = enc.Encode(Nv12FrameView(a.width, a.height, frames[src]), EncodeParams{ .qp = QpParams(a.qp) });
            r.startMs = Ms(s, t0);
            r.ok = static_cast<bool>(res);
            if (res) {
                r.frameType = static_cast<int>(res->info.frameType);
                r.bytes = res->bitStream.size();
                outAus.emplace_back(res->bitStream.begin(), res->bitStream.end());
                auto [n, t] = sendAu(seq++, outAus.back(), static_cast<uint8_t>(r.frameType));
                r.pkts = n; r.sendUs = t;
            }
            r.endMs = Ms(Clock::now(), t0);  // end = encoded AND handed to the network
            r.inferMs = enc.GetStats().inference.LatestMs();
            r.totalMs = enc.GetStats().total.LatestMs();
            sendRecs.push_back(r);
            ++k;
        }
        std::vector<std::byte> empty;
        for (int i = 0; i < 5; ++i) { sendAu(BYE, empty, 0); std::this_thread::sleep_for(std::chrono::milliseconds(20)); }
    };

    // ---- receiver: reassemble, decode in arrival order, count gaps ----
    auto recvLoop = [&] {
        struct Pending { std::vector<std::byte> data; std::vector<bool> got; uint32_t have = 0, nfrag = 0; uint64_t firstUs = 0, sendUs = 0; uint8_t ft = 0; };
        std::map<int64_t, Pending> pending;  // sequence number -> fragments
        int64_t lastDecoded = -1;            // the first frame expected is sequence number 0
        long slot = 0;
        std::vector<char> pkt(65536);
        const auto hardEnd = tEnd + std::chrono::seconds(3);
        while (!peerDone.load() && Clock::now() < hardEnd) {
            sockaddr_in from{}; socklen_t fl = sizeof(from);
            const ssize_t n = recvfrom(sock, pkt.data(), pkt.size(), 0, reinterpret_cast<sockaddr*>(&from), &fl);
            if (n < static_cast<ssize_t>(sizeof(PktHdr))) continue;
            const uint64_t arrive = NowUs();
            PktHdr h; std::memcpy(&h, pkt.data(), sizeof(h));
            if (h.magic != MAGIC) continue;
            lastRxSendUs.store(h.sendUs); lastRxArriveUs.store(arrive);
            if (h.echoT1Us) {  // NTP: t1 = echoT1 (my send), t2 = echoT2 (peer arrive), t3 = h.sendUs (peer send), t4 = arrive
                const double rtt = (static_cast<double>(arrive) - static_cast<double>(h.echoT1Us)) - (static_cast<double>(h.sendUs) - static_cast<double>(h.echoT2Us));
                const double off = ((static_cast<double>(h.echoT2Us) - static_cast<double>(h.echoT1Us)) + (static_cast<double>(h.sendUs) - static_cast<double>(arrive))) / 2.0;
                std::lock_guard<std::mutex> g(clockMu);
                if (clockRows.empty() || arrive - static_cast<uint64_t>(clockRows.back()[0] * 1e6) > 100000)  // at most 10 rows per second
                    clockRows.push_back({ arrive / 1e6, rtt / 1000.0, off / 1000.0 });
            }
            if (h.frame == BYE) { peerDone.store(true); break; }
            const int64_t id = static_cast<int64_t>(h.frame);
            if (id <= lastDecoded) continue;  // a late fragment of a frame already decoded or given up
            auto& p = pending[id];
            if (p.nfrag == 0) { p.nfrag = h.nfrag; p.data.resize(h.len); p.got.assign(h.nfrag, false); p.firstUs = arrive; p.sendUs = h.sendUs; p.ft = h.frameType; }
            if (h.frag < p.nfrag && !p.got[h.frag]) {
                const size_t off = static_cast<size_t>(h.frag) * payloadMax, len = static_cast<size_t>(n) - sizeof(PktHdr);
                if (off + len <= p.data.size()) std::memcpy(p.data.data() + off, pkt.data() + sizeof(PktHdr), len);
                p.got[h.frag] = true; ++p.have;
            }
            if (p.have < p.nfrag) continue;
            // complete: give up on older incomplete frames, decode this one
            long gaveUp = 0;
            for (auto it = pending.begin(); it != pending.end();) {
                if (it->first < id) { ++gaveUp; it = pending.erase(it); } else break;
            }
            incomplete += gaveUp;
            // frames of the peer between the last decoded one and this one that never arrived at all
            const long lost = static_cast<long>(std::max<int64_t>(0, id - lastDecoded - 1 - gaveUp));
            lostFrames += lost + gaveUp;
            Pending fr = std::move(pending[id]); pending.erase(id);
            const auto sched = Clock::now();  // "due" = the moment the frame is complete and could be decoded
            Rec r{ 'D', slot++, static_cast<long>(id), Ms(sched, t0), 0, 0, 0, 0, 0, 0, 0 };
            const auto s = Clock::now();
            auto res = dec.Decode(fr.data);
            const auto e = Clock::now();
            r.startMs = Ms(s, t0); r.endMs = Ms(e, t0);
            r.ok = static_cast<bool>(res);
            if (res) r.frameType = static_cast<int>(res->info.frameType); else { r.frameType = fr.ft; ++failures; }
            r.bytes = fr.data.size(); r.pkts = static_cast<int>(fr.nfrag);
            r.sendUs = fr.sendUs; r.firstUs = fr.firstUs; r.lastUs = arrive; r.lostBefore = lost + gaveUp;
            r.inferMs = dec.GetStats().inference.LatestMs();
            r.totalMs = dec.GetStats().total.LatestMs();
            recvRecs.push_back(r);
            received.push_back(std::move(fr.data));
            lastDecoded = id;
        }
    };

    std::thread ts(sendLoop), tr(recvLoop);
    ts.join(); tr.join();

    std::vector<Rec> all(sendRecs);
    all.insert(all.end(), recvRecs.begin(), recvRecs.end());
    WriteCsv(a.outDir + "/frames.csv", all, a);
    WriteAusAndMlvc(a.outDir + "/outgoing", outAus);
    WriteAusAndMlvc(a.outDir + "/received", received);
    {
        std::ofstream c(a.outDir + "/clock.csv");
        c << "t4_epoch_s,rtt_ms,offset_ms\n";
        c.precision(6);
        for (const auto& r : clockRows) c << std::fixed << r[0] << ',' << r[1] << ',' << r[2] << '\n';
    }
    double rttMed = NAN, offMed = NAN;
    if (!clockRows.empty()) {
        std::vector<double> v, o;
        for (const auto& r : clockRows) { v.push_back(r[1]); o.push_back(r[2]); }
        std::sort(v.begin(), v.end()); std::sort(o.begin(), o.end());
        rttMed = v[v.size() / 2]; offMed = o[o.size() / 2];
    }
    std::ofstream meta(a.outDir + "/run.txt");
    meta.precision(15);
    meta << "t0_epoch_ms=" << t0EpochMs << "\n";
    meta << "mode=call\nsize=" << a.width << "x" << a.height << "\nqp=" << a.qp << "\niframe_period=" << a.iframePeriod
         << "\nfps=" << a.fps << "\ndeadline_ms=" << a.deadlineMs << "\nseconds=" << a.seconds << "\nenc_cu=" << a.encCu
         << "\ndec_cu=" << a.decCu << "\nwarmup_frames=" << a.warmupFrames << "\nbundles=" << a.bundles << "\ninput=" << a.input
         << "\nincoming=udp://" << a.peer << ":" << a.port << "\nlisten_port=" << a.listenPort << "\nmtu=" << a.mtu
         << "\nencoder_dropped=" << dropped << "\ndecoder_failures=" << failures << "\nframes_sent=" << outAus.size()
         << "\nframes_received=" << received.size() << "\nframes_lost=" << lostFrames << "\nframes_incomplete=" << incomplete
         << "\nrtt_ms_median=" << rttMed << "\nclock_offset_ms_median=" << offMed << "\npeer_bye_seen=" << peerDone.load() << "\n";
    std::cerr << "done: sent " << outAus.size() << " frames, received " << received.size() << " (lost " << lostFrames
              << ", incomplete " << incomplete << ", decode failures " << failures << "), rtt median " << rttMed
              << " ms, clock offset " << offMed << " ms -> " << a.outDir << "\n";
    return 0;
}
