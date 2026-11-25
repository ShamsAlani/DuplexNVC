// A0: check libmlvc's per-frame controls before A1, A3 and A4 rely on them.
//   T1 forced key frames : forceIdr on chosen frames -> those frames, and only those, are I-frames; the stream decodes.
//   T2 external LTRs     : ltrMode EXTERNAL; MarkNextFrameAsLtr(slot) on chosen frames, useLtrSlotIdx on others ->
//                          the recovery frames reference the marked frame, the prediction chain restarts from it,
//                          and the decoder reports the same structure.
//   T3 per-frame QP      : a different QP on every frame -> the decoder reads the same QP from each frame header.
// Every stream is decoded twice on the NE (must be bit-identical) and once on the GPU; the decoder's frame info
// (type, reference, chain length, QP) is compared with the encoder's, frame by frame.
// usage: a0 --bundles DIR --input FILE.nv12 --size WxH [--frames 120] [--qp 26] --out DIR
#include <libmlvc/libmlvc.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <vector>

using namespace libmlvc;
using Bytes = std::vector<std::byte>;

struct Args {
    std::string bundles, input, out;
    int w = 640, h = 360, frames = 120, qp = 26;
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

static MlvcManager MakeManager(const std::string& bundles, ComputeUnit cu)
{
    ManagerParams p{};
    p.computeUnit = cu;
    auto m = MlvcManager::CreateFromDirectory(p, bundles);
    if (!m) { std::cerr << "manager init failed: " << m.error().message() << "\n"; std::exit(1); }
    std::cerr << "manager: requested=" << ComputeUnitToString(cu) << " resolved=" << ComputeUnitToString(m->GetInfo().computeUnit) << "\n";
    return m.value();
}

static const char* T(FrameType t) { return t == FrameType::I_FRAME ? "I" : t == FrameType::P_FRAME ? "P" : "R"; }

struct EncRec { int idx, ref, chain, qpReq; FrameType type; size_t bytes; };
struct DecRec { bool ok = false; int idx = 0, ref = 0, chain = 0, qp = 0; FrameType type{}; Bytes y; };

// Decodes every access unit; keeps the luma plane (tightly packed) of every frame.
static std::vector<DecRec> DecodeAll(const MlvcManager& m, const std::vector<Bytes>& aus, int w, int h)
{
    auto d = m.CreateDecoder();
    if (!d) { std::cerr << "decoder failed: " << d.error().message() << "\n"; std::exit(1); }
    std::vector<DecRec> out(aus.size());
    for (size_t i = 0; i < aus.size(); ++i) {
        auto r = d->Decode(aus[i]);
        if (!r) { std::cerr << "   decode error at AU " << i << ": " << r.error().message() << "\n"; continue; }
        auto& o = out[i];
        o.ok = true; o.idx = r->info.frameIdx; o.ref = r->info.refFrameIdx; o.chain = r->info.predictionChainLength;
        o.qp = r->qp; o.type = r->info.frameType;
        const auto y = r->frame.YPlane(); const int s = r->frame.Stride();
        o.y.resize(static_cast<size_t>(w) * h);
        for (int row = 0; row < h; ++row) std::memcpy(o.y.data() + static_cast<size_t>(row) * w, y.data() + static_cast<size_t>(row) * s, w);
    }
    return out;
}

static double PsnrY(const Bytes& a, const std::byte* b, size_t n)
{
    double se = 0;
    for (size_t i = 0; i < n; ++i) { const double d = double(std::to_integer<int>(a[i])) - double(std::to_integer<int>(b[i])); se += d * d; }
    if (se == 0) return 99.0;
    return 10.0 * std::log10(255.0 * 255.0 / (se / double(n)));
}

struct Plan {  // per-frame controls of one test
    std::set<int> forceIdr;
    std::map<int, int> markSlot;     // frame -> slot to store it in
    std::map<int, int> useSlot;      // frame -> slot to recover from
    std::map<int, int> qp;           // frame -> QP (else base)
};

static int RunTest(const std::string& name, const Args& a, const MlvcManager& ne, const MlvcManager& gpu,
                   const std::vector<Bytes>& frames, EncoderConfig cfg, const Plan& plan, std::ostream& summary)
{
    std::cerr << "\n== " << name << "\n";
    auto e = ne.CreateEncoder(cfg);
    if (!e) { std::cerr << "encoder failed: " << e.error().message() << "\n"; std::exit(1); }
    std::vector<Bytes> aus; std::vector<EncRec> enc;
    for (int i = 0; i < a.frames; ++i) {
        if (auto it = plan.markSlot.find(i); it != plan.markSlot.end()) {
            if (auto r = e->MarkNextFrameAsLtr(it->second); !r) { std::cerr << "MarkNextFrameAsLtr failed at " << i << "\n"; std::exit(1); }
        }
        EncodeParams p{};
        const int q = plan.qp.count(i) ? plan.qp.at(i) : a.qp;
        p.qp = QpParams(q);
        p.forceIdr = plan.forceIdr.count(i) > 0;
        if (auto it = plan.useSlot.find(i); it != plan.useSlot.end()) p.useLtrSlotIdx = it->second;
        auto r = e->Encode(Nv12FrameView(a.w, a.h, frames[i]), p);
        if (!r) { std::cerr << "encode failed at " << i << ": " << r.error().message() << "\n"; std::exit(1); }
        aus.emplace_back(r->bitStream.begin(), r->bitStream.end());
        enc.push_back({ r->info.frameIdx, r->info.refFrameIdx, r->info.predictionChainLength, q, r->info.frameType, r->bitStream.size() });
    }
    {   // the bitstream as `mlvc decode` reads it
        std::ofstream f(a.out + "/" + name + ".mlvc", std::ios::binary);
        for (auto& au : aus) f.write(reinterpret_cast<const char*>(au.data()), au.size());
    }
    auto d1 = DecodeAll(ne, aus, a.w, a.h), d2 = DecodeAll(ne, aus, a.w, a.h), dg = DecodeAll(gpu, aus, a.w, a.h);
    const size_t n = static_cast<size_t>(a.w) * a.h;
    std::ofstream c(a.out + "/" + name + ".csv");
    c << "frame,requested,enc_type,enc_ref,enc_chain,qp_requested,bytes,dec_ok,dec_type,dec_ref,dec_chain,dec_qp,"
         "info_match,ne_ne_identical,psnr_y_ne,psnr_y_gpu,gpu_vs_ne_db\n";
    int bad = 0, decFail = 0, infoMis = 0, nonDet = 0, qpMis = 0, typeMis = 0;
    std::map<int, int> slotFrame;   // slot -> frame it holds (slot 0 = frame 0 in external mode)
    if (cfg.ltrMode == LtrMode::EXTERNAL) slotFrame[0] = 0;
    for (int i = 0; i < a.frames; ++i) {
        const auto& E = enc[i]; const auto& D = d1[i];
        std::string req = plan.forceIdr.count(i) ? "force_idr" : plan.useSlot.count(i) ? "recover_slot" + std::to_string(plan.useSlot.at(i)) : "";
        if (plan.markSlot.count(i)) req += std::string(req.empty() ? "" : "+") + "mark_slot" + std::to_string(plan.markSlot.at(i));
        const bool ok = D.ok && d2[i].ok;
        const bool info = ok && D.type == E.type && D.idx == E.idx && (E.type == FrameType::I_FRAME || (D.ref == E.ref && D.chain == E.chain));
        const bool det = ok && D.y == d2[i].y;
        const bool qpOk = ok && D.qp == E.qpReq;
        bool typeOk = true;   // the requested structure actually happened
        if (plan.forceIdr.count(i)) typeOk = E.type == FrameType::I_FRAME;
        std::string expect;
        if (plan.useSlot.count(i)) {
            const int s = plan.useSlot.at(i);
            if (slotFrame.count(s)) {   // valid LTR: a recovery frame from it; newer LTRs become invalid
                typeOk = E.type == FrameType::LTR_RECOVERY && E.ref == slotFrame[s];
                const int f = slotFrame[s];
                for (auto it = slotFrame.begin(); it != slotFrame.end();) it = it->second > f ? slotFrame.erase(it) : std::next(it);
                expect = "R from " + std::to_string(f);
            } else {                    // the slot was invalidated by an earlier recovery: libmlvc ignores the hint
                typeOk = E.type == FrameType::P_FRAME;
                expect = "P (slot invalidated)";
            }
        }
        if (plan.markSlot.count(i)) slotFrame[plan.markSlot.at(i)] = i;
        decFail += !D.ok;
        infoMis += !info;
        nonDet += !det;
        qpMis += !qpOk;
        typeMis += !typeOk;
        const double pn = D.ok ? PsnrY(D.y, frames[i].data(), n) : 0, pg = dg[i].ok ? PsnrY(dg[i].y, frames[i].data(), n) : 0;
        const double gv = (D.ok && dg[i].ok) ? PsnrY(dg[i].y, D.y.data(), n) : 0;
        c << i << "," << req << "," << T(E.type) << "," << E.ref << "," << E.chain << "," << E.qpReq << "," << E.bytes << ","
          << ok << "," << (D.ok ? T(D.type) : "-") << "," << D.ref << "," << D.chain << "," << D.qp << "," << info << "," << det << ","
          << pn << "," << pg << "," << gv << "\n";
        if (!req.empty() || E.type != FrameType::P_FRAME)
            std::cerr << "   frame " << i << " " << (req.empty() ? "(scheduled)" : req) << (expect.empty() ? "" : " [expected " + expect + "]")
                      << (typeOk ? "" : " MISMATCH") << ": enc " << T(E.type) << " ref " << E.ref
                      << " chain " << E.chain << " qp " << E.qpReq << " | dec " << (D.ok ? T(D.type) : "FAIL") << " ref " << D.ref
                      << " chain " << D.chain << " qp " << D.qp << " | psnr " << pn << " dB\n";
    }
    int nI = 0, nR = 0, maxChain = 0;
    for (auto& E : enc) { nI += E.type == FrameType::I_FRAME; nR += E.type == FrameType::LTR_RECOVERY; maxChain = std::max(maxChain, E.chain); }
    bad = decFail + infoMis + nonDet + typeMis + qpMis;
    summary << name << ": frames " << a.frames << ", I " << nI << ", recovery " << nR << ", longest chain " << maxChain
            << " | requested structure applied: " << (a.frames - typeMis) << "/" << a.frames
            << " | decoded: " << (a.frames - decFail) << "/" << a.frames
            << " | decoder info = encoder info: " << (a.frames - infoMis) << "/" << a.frames
            << " | NE decode deterministic: " << (a.frames - nonDet) << "/" << a.frames
            << " | header QP = requested: " << (a.frames - qpMis) << "/" << a.frames
            << " -> " << (bad == 0 ? "PASS" : "FAIL") << "\n";
    return bad;
}

int main(int argc, char** argv)
{
    const Args a = Parse(argc, argv);
    std::filesystem::create_directories(a.out);
    auto frames = LoadNv12(a.input, a.w, a.h, a.frames);
    auto ne = MakeManager(a.bundles, ComputeUnit::NPU), gpu = MakeManager(a.bundles, ComputeUnit::GPU);
    const auto ver = ne.GetAvailableVersions().front();
    auto base = ne.GetDefaultEncoderConfig(ver);
    if (!base) { std::cerr << "no default config\n"; return 1; }
    base->SetSize(a.w, a.h);
    auto caps = ne.GetCapabilities(ver);
    std::cerr << "model " << ver.ToString() << ": default iframe_period " << base->iframePeriod << ", ltr mode "
              << LtrModeToString(base->ltrMode) << ", ltr period " << base->ltrPeriod << ", slots " << base->ltrNumSlots
              << ", max LTR slots " << (caps ? caps->maxNumOfLtrFrames : -1) << "\n";
    std::ofstream summary(a.out + "/summary.txt");
    int bad = 0;

    // T1: forced key frames on frames 20, 45 and 100 (periodic I-frames every 64 as B*: 0 and 64 scheduled)
    {
        EncoderConfig c = *base; c.iframePeriod = 64;
        Plan p; p.forceIdr = { 20, 45, 100 };
        bad += RunTest("t1_forced_key_frames", a, ne, gpu, frames, c, p, summary);
    }
    // T2: external LTRs, no periodic I-frame after frame 0: mark 10 (slot 1), 40 (slot 2) and 95 (slot 2 again);
    //     recover from slot 1 at 30, slot 2 at 70, slot 1 at 90 (older LTR), slot 2 at 110 and 115
    {
        EncoderConfig c = *base; c.iframePeriod = 0; c.ltrMode = LtrMode::EXTERNAL; c.ltrPeriod = 0; c.ltrRecoveryPeriod = 0;
        c.ltrStartIdx = 0; c.ltrNumSlots = std::max(3, std::min(4, caps ? caps->maxNumOfLtrFrames : 4));
        // The recovery at 90 goes back to frame 10: libmlvc then treats every LTR newer than frame 10 as invalid
        // (loss-recovery rule), so slot 2 (frame 40) is gone; slot 2 is marked again at 95, and 110 and 115 recover from 95
        Plan p; p.markSlot = { { 10, 1 }, { 40, 2 }, { 95, 2 } }; p.useSlot = { { 30, 1 }, { 70, 2 }, { 90, 1 }, { 110, 2 }, { 115, 2 } };
        bad += RunTest("t2_external_ltr", a, ne, gpu, frames, c, p, summary);
    }
    // T3: per-frame QP: 18, 22, 26, 30, 34, 38, 42 in turn, B* structure
    {
        EncoderConfig c = *base; c.iframePeriod = 64;
        Plan p; const int qs[] = { 18, 22, 26, 30, 34, 38, 42 };
        for (int i = 0; i < a.frames; ++i) p.qp[i] = qs[i % 7];
        bad += RunTest("t3_per_frame_qp", a, ne, gpu, frames, c, p, summary);
    }
    summary.close();
    std::ifstream s(a.out + "/summary.txt"); std::cout << "\n" << s.rdbuf();
    std::cout << (bad == 0 ? "A0: ALL PASS\n" : "A0: SOME CHECKS FAILED (see the lines above and the CSV files)\n");
    return bad == 0 ? 0 : 3;
}
