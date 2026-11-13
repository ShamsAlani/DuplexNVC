// duplex_bench.cpp: one call endpoint for the DuplexNVC baseline (libmlvc, macOS).
// Modes:
//   prepare   encode a clip once and store it as the "incoming" stream (.aus + .mlvc)
//   alone-enc encoder only            alone-dec decoder only
//   turns     encoder then decoder on ONE thread, frame by frame (best serial baseline)
//   duplex    encoder thread + decoder thread at the same time (the call)
// Every timed frame is written to a CSV. The outgoing bitstream of a timed run is kept in
// memory and written to disk after the run, so disk I/O never enters the timed loop.
#include <libmlvc/libmlvc.hpp>

#include <algorithm>
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
#include <optional>
#include <string>
#include <thread>
#include <vector>

using namespace libmlvc;
using Clock = std::chrono::steady_clock;
namespace fs = std::filesystem;

struct Args {
    std::string mode;
    std::string input;           // raw NV12 file (not .gz)
    int width = 640, height = 360;
    std::string incoming;        // .aus file written by "prepare"
    std::string outDir = "run";
    std::string bundles;         // model bundle dir (one model per dir!)
    std::string encCu = "npu", decCu = "npu";
    int qp = 26;
    int iframePeriod = 64;
    double fps = 30.0;           // 0 = unpaced (as fast as possible)
    double deadlineMs = 0.0;     // 0 = 1000/fps
    int seconds = 60;
    int warmupFrames = 64;       // dropped from statistics (model init, caches, clocks)
};

static ComputeUnit ParseCu(const std::string& s)
{
    if (s == "npu") return ComputeUnit::NPU;
    if (s == "gpu") return ComputeUnit::GPU;
    if (s == "cpu") return ComputeUnit::CPU;
    return ComputeUnit::AUTO;
}

static Args ParseArgs(int argc, char** argv)
{
    Args a;
    if (argc < 2) {
        std::cerr << "usage: duplex_bench <prepare|alone-enc|alone-dec|turns|duplex> [options]\n";
        std::exit(2);
    }
    a.mode = argv[1];
    for (int i = 2; i + 1 < argc; i += 2) {
        std::string k = argv[i], v = argv[i + 1];
        if (k == "--input") a.input = v;
        else if (k == "--size") std::sscanf(v.c_str(), "%dx%d", &a.width, &a.height);
        else if (k == "--incoming") a.incoming = v;
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
        else { std::cerr << "unknown option " << k << "\n"; std::exit(2); }
    }
    if (a.deadlineMs <= 0.0) a.deadlineMs = a.fps > 0 ? 1000.0 / a.fps : 33.333;
    return a;
}

// ---------- I/O helpers ----------
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

// .aus = sequence of [uint32 little-endian length][access unit bytes]
static std::vector<std::vector<std::byte>> LoadAus(const std::string& path)
{
    std::ifstream f(path, std::ios::binary);
    if (!f) { std::cerr << "cannot open " << path << "\n"; std::exit(1); }
    std::vector<std::vector<std::byte>> aus;
    uint32_t n = 0;
    while (f.read(reinterpret_cast<char*>(&n), 4)) {
        std::vector<std::byte> au(n);
        f.read(reinterpret_cast<char*>(au.data()), n);
        aus.push_back(std::move(au));
    }
    return aus;
}

static void WriteAusAndMlvc(const std::string& stem, const std::vector<std::vector<std::byte>>& aus)
{
    std::ofstream a(stem + ".aus", std::ios::binary), m(stem + ".mlvc", std::ios::binary);
    for (const auto& au : aus) {
        uint32_t n = static_cast<uint32_t>(au.size());
        a.write(reinterpret_cast<const char*>(&n), 4);
        a.write(reinterpret_cast<const char*>(au.data()), n);
        m.write(reinterpret_cast<const char*>(au.data()), n);  // raw concatenation = what `mlvc decode` reads
    }
}

static MlvcManager MakeManager(const Args& a, ComputeUnit cu)
{
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

// ---------- per-frame record ----------
struct Rec {
    char dir;            // 'E' or 'D'
    long k;              // schedule slot (frame number on the 30 fps clock)
    long src;            // source frame index (E) or incoming AU index (D)
    double schedMs, startMs, endMs;  // relative to t0
    double inferMs;      // network inference only (libmlvc stats)
    double totalMs;      // whole Encode()/Decode() call (incl. entropy coding)
    int frameType;       // 0 I, 1 P, 2 LTR recovery
    size_t bytes;
    int ok;
};

static void WriteCsv(const std::string& path, const std::vector<Rec>& recs, const Args& a)
{
    std::ofstream f(path);
    f << "dir,slot,src,sched_ms,start_ms,end_ms,service_ms,latency_ms,late,infer_ms,call_ms,frame_type,bytes,ok,warmup\n";
    for (const auto& r : recs) {
        const double latency = r.endMs - r.schedMs;  // includes any queueing behind the previous frame
        const bool late = latency > a.deadlineMs;
        f << r.dir << ',' << r.k << ',' << r.src << ',' << r.schedMs << ',' << r.startMs << ',' << r.endMs << ','
          << (r.endMs - r.startMs) << ',' << latency << ',' << late << ',' << r.inferMs << ',' << r.totalMs << ','
          << r.frameType << ',' << r.bytes << ',' << r.ok << ',' << (r.k < a.warmupFrames) << '\n';
    }
}

static double Ms(Clock::time_point t, Clock::time_point t0)
{
    return std::chrono::duration<double, std::milli>(t - t0).count();
}

// ---------- the two directions ----------
struct Sender {
    const Args& a;
    MlvcEncoder enc;
    const std::vector<std::vector<std::byte>>& frames;
    std::vector<Rec> recs;
    std::vector<std::vector<std::byte>> outAus;
    long dropped = 0;

    Rec EncodeOne(long k, long src, Clock::time_point t0, Clock::time_point sched)
    {
        Rec r{ 'E', k, src, Ms(sched, t0), 0, 0, 0, 0, 0, 0, 0 };
        const auto s = Clock::now();
        Nv12FrameView view(a.width, a.height, frames[src]);
        auto res = enc.Encode(view, EncodeParams{ .qp = QpParams(a.qp) });
        const auto e = Clock::now();
        r.startMs = Ms(s, t0);
        r.endMs = Ms(e, t0);
        r.ok = static_cast<bool>(res);
        if (res) {
            r.frameType = static_cast<int>(res->info.frameType);
            r.bytes = res->bitStream.size();
            outAus.emplace_back(res->bitStream.begin(), res->bitStream.end());  // copy before next Encode()
        }
        r.inferMs = enc.GetStats().inference.LatestMs();
        r.totalMs = enc.GetStats().total.LatestMs();
        return r;
    }
};

struct Receiver {
    const Args& a;
    MlvcDecoder dec;
    const std::vector<std::vector<std::byte>>& aus;
    std::vector<Rec> recs;
    long failures = 0;

    Rec DecodeOne(long k, Clock::time_point t0, Clock::time_point sched)
    {
        const long src = k % static_cast<long>(aus.size());
        Rec r{ 'D', k, src, Ms(sched, t0), 0, 0, 0, 0, 0, 0, 0 };
        const auto s = Clock::now();
        auto res = dec.Decode(aus[src]);
        const auto e = Clock::now();
        r.startMs = Ms(s, t0);
        r.endMs = Ms(e, t0);
        r.ok = static_cast<bool>(res);
        if (res) {
            r.frameType = static_cast<int>(res->info.frameType);
        } else {
            ++failures;
        }
        r.bytes = aus[src].size();
        r.inferMs = dec.GetStats().inference.LatestMs();
        r.totalMs = dec.GetStats().total.LatestMs();
        return r;
    }
};

int main(int argc, char** argv)
{
    const Args a = ParseArgs(argc, argv);
    fs::create_directories(a.outDir);
    const bool paced = a.fps > 0;
    const auto period = std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double, std::milli>(paced ? 1000.0 / a.fps : 0.0));

    // ---- prepare: encode the incoming stream once, untimed ----
    if (a.mode == "prepare") {
        auto frames = LoadNv12(a.input, a.width, a.height);
        auto m = MakeManager(a, ParseCu(a.encCu));
        auto enc = MakeEncoder(m, a);
        std::vector<std::vector<std::byte>> aus;
        for (const auto& fr : frames) {
            auto res = enc.Encode(Nv12FrameView(a.width, a.height, fr), EncodeParams{ .qp = QpParams(a.qp) });
            if (!res) { std::cerr << "encode failed\n"; return 1; }
            aus.emplace_back(res->bitStream.begin(), res->bitStream.end());
        }
        WriteAusAndMlvc(a.outDir + "/incoming", aus);
        std::cerr << "wrote " << aus.size() << " access units to " << a.outDir << "/incoming.{aus,mlvc}\n";
        return 0;
    }

    const bool needEnc = a.mode != "alone-dec";
    const bool needDec = a.mode != "alone-enc";
    std::vector<std::vector<std::byte>> frames, aus;
    if (needEnc) frames = LoadNv12(a.input, a.width, a.height);
    if (needDec) aus = LoadAus(a.incoming);

    // One manager per compute unit; a placement such as "encoder on NE, decoder on GPU"
    // needs two managers, each holding its own loaded model instances.
    std::map<std::string, MlvcManager> managers;
    auto getManager = [&](const std::string& cu) -> MlvcManager& {
        auto it = managers.find(cu);
        if (it == managers.end()) it = managers.emplace(cu, MakeManager(a, ParseCu(cu))).first;
        return it->second;
    };

    std::optional<Sender> snd;
    std::optional<Receiver> rcv;
    if (needEnc) snd.emplace(Sender{ a, MakeEncoder(getManager(a.encCu), a), frames, {}, {}, 0 });
    if (needDec) {
        auto d = getManager(a.decCu).CreateDecoder();
        if (!d) { std::cerr << "decoder failed\n"; return 1; }
        rcv.emplace(Receiver{ a, std::move(d.value()), aus, {}, 0 });
    }

    // Pre-warm: the first Encode()/Decode() initialises the model (can take seconds). Do it before
    // t0 so start-up cost is reported separately and never shows up as a backlog of late frames.
    if (snd) {
        const auto s = Clock::now();
        auto r = snd->enc.Encode(Nv12FrameView(a.width, a.height, frames[0]), EncodeParams{ .qp = QpParams(a.qp) });
        std::cerr << "encoder first-frame (init) ms: " << Ms(Clock::now(), s) << (r ? "" : " FAILED") << "\n";
        if (r) {
            // Keep this IDR: every later frame of the outgoing stream depends on it. It is logged
            // as slot -1 (always warm-up) so that offline decoding stays aligned with frames.csv.
            snd->outAus.emplace_back(r->bitStream.begin(), r->bitStream.end());
            snd->recs.push_back(Rec{ 'E', -1, 0, 0, 0, 0, 0, 0, static_cast<int>(r->info.frameType),
                                     r->bitStream.size(), 1 });
        }
    }
    if (rcv) {
        const auto s = Clock::now();
        auto r = rcv->dec.Decode(aus[0]);  // aus[0] is an IDR; the timed loop starts again from it
        std::cerr << "decoder first-frame (init) ms: " << Ms(Clock::now(), s) << (r ? "" : " FAILED") << "\n";
    }

    const auto t0 = Clock::now() + std::chrono::milliseconds(200);
    const auto tEnd = t0 + std::chrono::seconds(a.seconds);
    // Wall-clock time of t0, used to align the power log (powermetrics) with this run.
    const double t0EpochMs = std::chrono::duration<double, std::milli>(
        (std::chrono::system_clock::now() + std::chrono::milliseconds(200)).time_since_epoch()).count();

    std::this_thread::sleep_until(t0);  // every mode starts timing at t0

    if (a.mode == "turns") {
        // Best serial program: one thread, encode frame k then decode frame k.
        for (long k = 0;; ++k) {
            // Unpaced (--fps 0): a frame is "scheduled" when it starts, so latency = service time.
            const auto sched = paced ? t0 + k * period : Clock::now();
            if (sched >= tEnd) break;
            if (paced) std::this_thread::sleep_until(sched);
            snd->recs.push_back(snd->EncodeOne(k, k % static_cast<long>(frames.size()), t0, sched));
            rcv->recs.push_back(rcv->DecodeOne(k, t0, sched));
        }
    } else {
        // Sender: a camera delivers frame k at t0 + k*period. If the encoder is more than one
        // period behind, the frames it missed are DROPPED (a real camera does not wait).
        auto sendLoop = [&] {
            long k = 0;
            while (true) {
                auto now = Clock::now();
                if (paced && now > t0 + period) {
                    const long newest = static_cast<long>((now - t0) / period);
                    if (newest > k) { snd->dropped += newest - k; k = newest; }
                }
                const auto sched = paced ? t0 + k * period : Clock::now();
                if (sched >= tEnd) break;
                if (paced) std::this_thread::sleep_until(sched);
                snd->recs.push_back(snd->EncodeOne(k, k % static_cast<long>(frames.size()), t0, sched));
                ++k;
            }
        };
        // Receiver: incoming frames depend on each other, so none can be skipped;
        // a slow decoder therefore shows up as growing latency and late frames.
        auto recvLoop = [&] {
            for (long k = 0;; ++k) {
                const auto sched = paced ? t0 + k * period : Clock::now();
                if (sched >= tEnd) break;
                if (paced) std::this_thread::sleep_until(sched);
                rcv->recs.push_back(rcv->DecodeOne(k, t0, sched));
            }
        };
        std::thread ts, tr;
        if (needEnc) ts = std::thread(sendLoop);
        if (needDec) tr = std::thread(recvLoop);
        if (ts.joinable()) ts.join();
        if (tr.joinable()) tr.join();
    }

    std::vector<Rec> all;
    if (snd) all.insert(all.end(), snd->recs.begin(), snd->recs.end());
    if (rcv) all.insert(all.end(), rcv->recs.begin(), rcv->recs.end());
    WriteCsv(a.outDir + "/frames.csv", all, a);
    if (snd) WriteAusAndMlvc(a.outDir + "/outgoing", snd->outAus);

    std::ofstream meta(a.outDir + "/run.txt");
    meta.precision(15);
    meta << "t0_epoch_ms=" << t0EpochMs << "\n";
    meta << "mode=" << a.mode << "\nsize=" << a.width << "x" << a.height << "\nqp=" << a.qp
         << "\niframe_period=" << a.iframePeriod << "\nfps=" << a.fps << "\ndeadline_ms=" << a.deadlineMs
         << "\nseconds=" << a.seconds << "\nenc_cu=" << a.encCu << "\ndec_cu=" << a.decCu
         << "\nwarmup_frames=" << a.warmupFrames << "\nbundles=" << a.bundles << "\ninput=" << a.input
         << "\nincoming=" << a.incoming << "\nencoder_dropped=" << (snd ? snd->dropped : 0)
         << "\ndecoder_failures=" << (rcv ? rcv->failures : 0) << "\n";
    std::cerr << "done: " << all.size() << " frame records in " << a.outDir << "\n";
    return 0;
}
