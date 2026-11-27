// E3 + A4: recovery from packet loss, and long-term references marked when the content settles.
// One clip, one setting, one QP per call. Encoder and decoder run in the same process on the NE (no drift), the
// channel between them loses frames, and the decoder's loss reports reach the encoder one round trip later.
//   E3 arms (what the encoder does when a loss report arrives):
//     wait  nothing: the decoder freezes until the next scheduled I-frame (every 64 frames)
//     idr   a forced I-frame (EncodeParams.forceIdr), the usual "picture loss" answer
//     ltr   a recovery frame from the newest long-term reference the decoder is known to hold
//           (EncodeParams.useLtrSlotIdx; libmlvc keeps the last I-frame in slot 0, so that one counts too);
//           an I-frame only if it holds none
//   A4 marking (which frames become long-term references; external LTR mode, slots 1-3 in turn):
//     fixed     the frame after each I-frame and then every 16 frames (MLVC's LTR period)
//     adaptive  the frame after each I-frame, then only once the content has changed (mean absolute luma difference
//               to the newest reference > 6) and settled again (frame-to-frame difference below max(2, 1.5 x its
//               median over the last 64 frames) for 8 frames)
//   Loss patterns (identical for every arm; frame 0 is never lost):
//     none, p1 / p5 (each 1200-byte packet lost with probability 1 % / 5 %: a frame is lost if any packet is),
//     burst (a burst starts with probability 0.6 % per frame and loses 3-8 frames in a row)
// The decoder shows the last frame it decoded while it cannot decode (freeze). Libmlvc refuses a frame whose
// reference it does not hold, so a lost frame breaks the chain until a recovery frame or an I-frame arrives.
// usage: e3a4 --bundles DIR --input FILE.nv12 --size WxH --qp Q --seed N --out FILE.csv [--frames 300] [--rtt 3] [--check]
#include <libmlvc/libmlvc.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <vector>

using namespace libmlvc;
using Bytes = std::vector<std::byte>;

struct Args {
    std::string bundles, input, out;
    int w = 640, h = 360, frames = 300, qp = 26, rtt = 3;
    uint32_t seed = 1;
    bool check = false;
};

static Args Parse(int argc, char** argv)
{
    Args a;
    for (int i = 1; i < argc; ++i) {
        std::string k = argv[i];
        auto v = [&]() { if (i + 1 >= argc) { std::cerr << "missing value for " << k << "\n"; std::exit(2); } return std::string(argv[++i]); };
        if (k == "--bundles") a.bundles = v();
        else if (k == "--input") a.input = v();
        else if (k == "--out") a.out = v();
        else if (k == "--size") { auto s = v(); auto x = s.find('x'); a.w = std::stoi(s.substr(0, x)); a.h = std::stoi(s.substr(x + 1)); }
        else if (k == "--frames") a.frames = std::stoi(v());
        else if (k == "--qp") a.qp = std::stoi(v());
        else if (k == "--rtt") a.rtt = std::stoi(v());
        else if (k == "--seed") a.seed = static_cast<uint32_t>(std::stoul(v()));
        else if (k == "--check") a.check = true;
        else { std::cerr << "unknown option " << k << "\n"; std::exit(2); }
    }
    if (a.bundles.empty() || a.input.empty() || a.out.empty()) { std::cerr << "need --bundles --input --out\n"; std::exit(2); }
    return a;
}

static std::vector<Bytes> LoadNv12(const std::string& p, int w, int h, int n)
{
    std::ifstream f(p, std::ios::binary);
    if (!f) { std::cerr << "cannot open " << p << "\n"; std::exit(1); }
    const size_t fb = static_cast<size_t>(w) * h * 3 / 2;
    std::vector<Bytes> v;
    while (static_cast<int>(v.size()) < n) {
        Bytes b(fb);
        if (!f.read(reinterpret_cast<char*>(b.data()), fb)) break;
        v.push_back(std::move(b));
    }
    if (static_cast<int>(v.size()) < n) { std::cerr << "input has only " << v.size() << " frames\n"; std::exit(1); }
    return v;
}

static double PsnrY(const std::byte* a, const std::byte* b, size_t n)
{
    double se = 0;
    for (size_t i = 0; i < n; ++i) { const double d = double(std::to_integer<int>(a[i])) - double(std::to_integer<int>(b[i])); se += d * d; }
    if (se == 0) return 99.0;
    return 10.0 * std::log10(255.0 * 255.0 / (se / double(n)));
}

static double Mad(const std::byte* a, const std::byte* b, size_t n)
{
    uint64_t s = 0;
    for (size_t i = 0; i < n; ++i) s += static_cast<uint64_t>(std::abs(std::to_integer<int>(a[i]) - std::to_integer<int>(b[i])));
    return double(s) / double(n);
}

// Deterministic uniform number in [0,1) from (seed, stream, frame, packet): the same draw for every arm.
static double U(uint32_t seed, uint32_t stream, uint32_t frame, uint32_t k)
{
    uint64_t x = (uint64_t(seed) << 40) ^ (uint64_t(stream) << 32) ^ (uint64_t(frame) << 12) ^ k;
    x += 0x9E3779B97F4A7C15ULL; x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL; x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL; x ^= x >> 31;
    return double(x >> 11) / double(1ULL << 53);
}

struct Combo { std::string pattern, arm, marking; };

static int NewestValid(const std::map<int, int>& slots)
{
    int n = -1;
    for (auto& [s, f] : slots) n = std::max(n, f);   // includes slot 0 (the I-frame)
    return n;
}

static const char* T(FrameType t) { return t == FrameType::I_FRAME ? "I" : t == FrameType::P_FRAME ? "P" : "R"; }

int main(int argc, char** argv)
{
    const Args a = Parse(argc, argv);
    const auto src = LoadNv12(a.input, a.w, a.h, a.frames);
    const size_t ny = static_cast<size_t>(a.w) * a.h;
    SetLogLevel(LogLevel::Error);

    ManagerParams mp{}; mp.computeUnit = ComputeUnit::NPU;
    auto mgr = MlvcManager::CreateFromDirectory(mp, a.bundles);
    if (!mgr) { std::cerr << "manager init failed: " << mgr.error().message() << "\n"; return 1; }
    const auto ver = mgr->GetAvailableVersions().front();
    auto base = mgr->GetDefaultEncoderConfig(ver);
    if (!base) { std::cerr << "no default config\n"; return 1; }
    base->SetSize(a.w, a.h);
    EncoderConfig cfg = *base;
    cfg.iframePeriod = 64; cfg.ltrMode = LtrMode::EXTERNAL; cfg.ltrPeriod = 0; cfg.ltrRecoveryPeriod = 0; cfg.ltrStartIdx = 0;
    cfg.ltrNumSlots = 4;

    // content measures for adaptive marking (encoder side, from the source frames)
    std::vector<double> ff(a.frames, 0.0);   // frame-to-frame mean absolute luma difference
    for (int i = 1; i < a.frames; ++i) ff[i] = Mad(src[i].data(), src[i - 1].data(), ny);
    // "settled": every frame-to-frame difference of the last 8 frames below max(2, 1.5 x the median of the last 64)
    std::vector<double> still(a.frames, 2.0);
    for (int i = 1; i < a.frames; ++i) {
        std::vector<double> w(ff.begin() + std::max(1, i - 63), ff.begin() + i + 1);
        std::nth_element(w.begin(), w.begin() + w.size() / 2, w.end());
        still[i] = std::max(2.0, 1.5 * w[w.size() / 2]);
    }

    // burst mask (same for every arm)
    std::vector<char> burst(a.frames, 0);
    for (int i = 1; i < a.frames;) {
        if (U(a.seed, 7, i, 0) < 0.006) { const int len = 3 + int(U(a.seed, 8, i, 0) * 6.0); for (int k = 0; k < len && i < a.frames; ++k, ++i) burst[i] = 1; }
        else ++i;
    }

    std::vector<Combo> combos;
    if (a.check) {
        combos = { { "none", "wait", "fixed" }, { "p5", "idr", "fixed" }, { "burst", "ltr", "fixed" }, { "burst", "ltr", "adaptive" } };
    } else {
        combos.push_back({ "none", "wait", "fixed" });
        for (const char* p : { "p1", "p5", "burst" })
            for (const char* arm : { "wait", "idr", "ltr" }) combos.push_back({ p, arm, "fixed" });
        for (const char* p : { "none", "p1", "p5", "burst" }) combos.push_back({ p, "ltr", "adaptive" });
    }

    std::ofstream csv(a.out + ".part");
    csv << "pattern,arm,marking,frame,lost,dec_ok,shown,enc_type,enc_ref,chain,bytes,mark_slot,request,psnr_shown,psnr_dec,ff_mad\n";
    std::ofstream sum(a.out + ".sum.part");
    sum << "pattern,arm,marking,frames,kbps,psnr_shown,psnr_decoded,frames_lost,frames_frozen,loss_events,longest_freeze,"
           "req_idr,req_ltr,ltr_fallback_idr,i_frames,recovery_frames,marks,recovery_bytes_mean,i_bytes_mean,p_bytes_mean,"
           "structure_errors,unexpected_decode_errors\n";
    int totalErr = 0;

    for (const auto& C : combos) {
        auto enc = mgr->CreateEncoder(cfg);
        if (!enc) { std::cerr << "encoder failed: " << enc.error().message() << "\n"; return 1; }
        auto dec = mgr->CreateDecoder();
        if (!dec) { std::cerr << "decoder failed: " << dec.error().message() << "\n"; return 1; }
        const uint32_t stream = C.pattern == "p1" ? 1 : C.pattern == "p5" ? 5 : C.pattern == "burst" ? 9 : 0;
        const double pp = C.pattern == "p1" ? 0.01 : C.pattern == "p5" ? 0.05 : 0.0;

        std::map<int, int> slotFrame;          // encoder's view: slot -> frame it holds
        std::vector<char> nack(a.frames, 0), decOk(a.frames, 0), lostv(a.frames, 0);
        Bytes shown(ny); bool haveShown = false;
        int lastI = 0, lastRecovery = -1, nextSlot = 1, pendingMark = 0;
        long long bytesTot = 0; double sumShown = 0, sumDec = 0; int nDec = 0, nLost = 0, nFrozen = 0, events = 0, curFreeze = 0, longest = 0;
        int reqIdr = 0, reqLtr = 0, fallback = 0, nI = 0, nR = 0, marks = 0, structErr = 0, decErr = 0;
        double rBytes = 0, iBytes = 0, pBytes = 0; int nP = 0;
        bool prevBad = false;

        for (int i = 0; i < a.frames; ++i) {
            // 1. loss report for frame i - rtt reaches the encoder
            EncodeParams p{}; p.qp = QpParams(a.qp);
            std::string request;
            int expectRef = -1;
            const int j = i - a.rtt;
            const bool scheduledI = i == 0 || i == lastI + 64;
            if (C.arm != "wait" && j >= 0 && nack[j] && j >= lastRecovery && scheduledI) { request = "scheduled_i"; lastRecovery = i; }
            else if (C.arm != "wait" && j >= 0 && nack[j] && j >= lastRecovery) {
                if (C.arm == "idr") { p.forceIdr = true; request = "idr"; ++reqIdr; }
                else {
                    int bestS = -1, bestF = -1;
                    for (auto& [s, f] : slotFrame) if (f <= j && decOk[f] && f > bestF) { bestF = f; bestS = s; }
                    if (bestS >= 0) { p.useLtrSlotIdx = bestS; expectRef = bestF; request = "ltr" + std::to_string(bestF); ++reqLtr; }
                    else { p.forceIdr = true; request = "idr_fallback"; ++fallback; }
                }
                lastRecovery = i;
            }
            const bool willBeI = p.forceIdr || scheduledI;
            // 2. marking (never on an I-frame or a recovery frame; postponed by one frame instead)
            int markSlot = -1;
            {
                bool want = pendingMark != 0;
                if (C.marking == "fixed") want = want || (i > lastI && (i - lastI) % 16 == 1);
                else {
                    if (i > lastI && slotFrame.size() <= 1) want = true;   // the frame after an I-frame (only slot 0 = the I-frame), or no valid reference left
                    else if (int nv = NewestValid(slotFrame); nv >= 0 && i >= 8 && Mad(src[i].data(), src[nv].data(), ny) > 6.0) {
                        bool settled = true;
                        for (int k = i - 7; k <= i; ++k) settled = settled && ff[k] < still[i];
                        want = want || settled;
                    }
                }
                if (want && !willBeI && !p.useLtrSlotIdx.has_value()) { markSlot = nextSlot; nextSlot = nextSlot % 3 + 1; pendingMark = 0; }
                else if (want) pendingMark = 1;   // never on an I-frame or a recovery frame: one frame later
            }
            if (markSlot >= 0) {
                if (auto r = enc->MarkNextFrameAsLtr(markSlot); !r) { std::cerr << "MarkNextFrameAsLtr failed at " << i << "\n"; return 1; }
            }
            // 3. encode
            auto r = enc->Encode(Nv12FrameView(a.w, a.h, src[i]), p);
            if (!r) { std::cerr << "encode failed at " << i << ": " << r.error().message() << "\n"; return 1; }
            const FrameInfo E = r->info;
            Bytes au(r->bitStream.begin(), r->bitStream.end());
            bytesTot += static_cast<long long>(au.size());
            if (E.frameType == FrameType::I_FRAME) { lastI = i; slotFrame.clear(); slotFrame[0] = i; ++nI; iBytes += double(au.size()); }
            else if (E.frameType == FrameType::LTR_RECOVERY) { ++nR; rBytes += double(au.size()); }
            else { ++nP; pBytes += double(au.size()); }
            if (p.forceIdr && E.frameType != FrameType::I_FRAME) ++structErr;
            if (expectRef >= 0) {
                // libmlvc numbers frames from the last I-frame (frameIdx 0 = the I-frame), so compare relative to it
                if (E.frameType != FrameType::LTR_RECOVERY || E.refFrameIdx != expectRef - lastI) ++structErr;
                for (auto it = slotFrame.begin(); it != slotFrame.end();) it = it->second > expectRef ? slotFrame.erase(it) : std::next(it);
            }
            if (markSlot >= 0) { slotFrame[markSlot] = i; ++marks; }
            // 4. channel
            bool lost = false;
            if (i > 0) {
                if (C.pattern == "burst") lost = burst[i];
                else if (pp > 0) {
                    const uint32_t np = static_cast<uint32_t>((au.size() + 1199) / 1200);
                    for (uint32_t k = 0; k < np && !lost; ++k) lost = U(a.seed, stream, i, k) < pp;
                }
            }
            lostv[i] = lost; nLost += lost;
            // 5. decoder
            bool ok = false; double pd = 0;
            if (!lost) {
                auto d = dec->Decode(au);
                if (d) {
                    ok = true;
                    const auto y = d->frame.YPlane(); const int st = d->frame.Stride();
                    for (int row = 0; row < a.h; ++row) std::memcpy(shown.data() + static_cast<size_t>(row) * a.w, y.data() + static_cast<size_t>(row) * st, a.w);
                    haveShown = true;
                } else if (!prevBad) ++decErr;   // a frame that arrived after good frames should always decode
            }
            decOk[i] = ok;
            if (!ok) nack[i] = 1;
            const bool bad = !ok;
            if (bad && !prevBad) ++events;
            if (bad) { ++nFrozen; ++curFreeze; longest = std::max(longest, curFreeze); } else curFreeze = 0;
            prevBad = bad;
            const double ps = haveShown ? PsnrY(shown.data(), src[i].data(), ny) : 0.0;
            if (ok) { pd = ps; sumDec += pd; ++nDec; }
            sumShown += ps;
            csv << C.pattern << "," << C.arm << "," << C.marking << "," << i << "," << lost << "," << ok << "," << (ok ? "new" : "frozen")
                << "," << T(E.frameType) << "," << E.refFrameIdx << "," << E.predictionChainLength << "," << au.size() << ","
                << markSlot << "," << request << "," << ps << "," << (ok ? std::to_string(pd) : "") << "," << ff[i] << "\n";
        }
        const double kbps = double(bytesTot) * 8.0 / 1000.0 / (a.frames / 30.0);
        sum << C.pattern << "," << C.arm << "," << C.marking << "," << a.frames << "," << kbps << "," << sumShown / a.frames << ","
            << (nDec ? sumDec / nDec : 0) << "," << nLost << "," << nFrozen << "," << events << "," << longest << ","
            << reqIdr << "," << reqLtr << "," << fallback << "," << nI << "," << nR << "," << marks << ","
            << (nR ? rBytes / nR : 0) << "," << (nI ? iBytes / nI : 0) << "," << (nP ? pBytes / nP : 0) << ","
            << structErr << "," << decErr << "\n";
        totalErr += structErr + decErr;
        std::cout << "   " << C.pattern << "/" << C.arm << "/" << C.marking << ": " << kbps << " kbps, shown " << sumShown / a.frames
                  << " dB, lost " << nLost << ", frozen " << nFrozen << ", events " << events << ", I " << nI << ", R " << nR
                  << ", marks " << marks << (structErr + decErr ? ", ERRORS " + std::to_string(structErr) + "/" + std::to_string(decErr) : "") << "\n";
    }
    csv.close(); sum.close();
    std::rename((a.out + ".part").c_str(), a.out.c_str());
    std::rename((a.out + ".sum.part").c_str(), (a.out.substr(0, a.out.size() - 4) + "_sum.csv").c_str());
    return totalErr ? 3 : 0;
}
