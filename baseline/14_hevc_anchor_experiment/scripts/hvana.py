#!/usr/bin/env python3
"""Step 9 quality analysis: BD-rate of Apple's hardware HEVC against MLVC on the same clips, on 4 metrics
(coded PSNR-Y, display PSNR-Y, face PSNR-Y, face LPIPS), on the mean curves (as experiment 10) and per clip.
Negative = HEVC needs fewer bits than MLVC for the same quality. Also how close HEVC came to its target bitrate.
usage: hvana.py   reads phase2/hv/q.csv and phase2/4b/q.csv, writes phase2/hv/results/
"""
import csv, os, statistics as st, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import ana

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/hv"; RES = f"{OUT}/results"
QPS = [16, 24, 26, 32, 40]
MET = ["psnr_y", "psnr_y_display", "face_psnr_y", "face_lpips"]
NM = {"psnr_y": "coded Y", "psnr_y_display": "display Y", "face_psnr_y": "face Y", "face_lpips": "face LPIPS"}
PAIRS = [("hevc_360p", "mlvc_360p_npu-npu", "HEVC 360p vs B* (full MLVC 360p)"),
         ("hevc_720p", "mlvcs_720p_npu-npu", "HEVC 720p vs MLVC-S 720p"),
         ("hevc_720p", "mlvc_720p_npu-npu", "HEVC 720p vs full MLVC 720p")]


def load(path):
    G = {}
    for r in csv.DictReader(open(path)):
        G.setdefault(r["cfg"], {}).setdefault(r["clip"], {})[int(r["qp"])] = r
    return G


def pts(byq, m):
    return sorted((float(r["kbps"]), float(r[m])) for r in byq.values() if r[m] not in ("", "nan"))


def main():
    os.makedirs(RES, exist_ok=True)
    H, M = load(f"{OUT}/q.csv"), load(f"{WORK}/phase2/4b/q.csv")
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    say("STEP 9 (quality): Apple hardware HEVC (VideoToolbox, real time, no B-frames, I-frame every 64) vs MLVC")
    say("\n== mean of the clips per target (kbps / coded PSNR-Y / display PSNR-Y / face PSNR-Y / face LPIPS); target = MLVC's QP")
    rows = []
    for cfg in sorted(H):
        say(f"   {cfg}")
        for p in QPS:
            g = [H[cfg][c][p] for c in H[cfg] if p in H[cfg][c]]
            if not g:
                continue
            m = {k: st.mean(float(r[k]) for r in g if r[k] not in ("", "nan")) for k in ["kbps"] + MET}
            tg = st.mean(float(r["enc_resolved"].split("=")[1]) for r in g)
            rows.append(dict(cfg=cfg, target_qp=p, clips=len(g), target_kbps=tg, **m))
            say(f"     @QP{p}: target {tg:6.1f} -> {m['kbps']:6.1f} kbps ({100 * (m['kbps'] / tg - 1):+.1f} %)  "
                f"{m['psnr_y']:.2f} / {m['psnr_y_display']:.2f} / {m['face_psnr_y']:.2f} / {m['face_lpips']:.3f}")
    if rows:
        with open(f"{RES}/rd_mean.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    say("\n== BD-rate of HEVC vs MLVC (negative = HEVC needs fewer bits); mean curves, then per clip (median, clips where HEVC wins)")
    say(f"   {'':<34}" + "".join(f"{NM[m]:>26}" for m in MET))
    bdr = []
    for hc, mc, desc in PAIRS:
        if hc not in H or mc not in M:
            continue
        cells = []
        for m in MET:
            lb = m == "face_lpips"
            clips = sorted(set(H[hc]) & set(M[mc]))
            mean_c = lambda G, c_: sorted((st.mean(float(G[c_][x][p]["kbps"]) for x in clips if p in G[c_][x]),
                                           st.mean(float(G[c_][x][p][m]) for x in clips if p in G[c_][x] and G[c_][x][p][m] not in ("", "nan")))
                                          for p in QPS if all(p in G[c_][x] for x in clips))
            b, _ = ana.bd(mean_c(M, mc), mean_c(H, hc), lb)
            per = [x for x in (ana.bd(pts(M[mc][c], m), pts(H[hc][c], m), lb)[0] for c in clips) if x is not None]
            med = st.median(per) if per else None
            bdr.append(dict(pair=desc, metric=m, bd_rate_pct=b, clip_median_pct=med, clips_hevc_wins=sum(x < 0 for x in per), clips=len(per)))
            cells.append(f"{'-' if b is None else f'{b:+.1f} %'} ({'-' if med is None else f'{med:+.1f}'}, {sum(x < 0 for x in per)}/{len(per)})")
        say(f"   {desc:<34}" + "".join(f"{c:>26}" for c in cells))
    if bdr:
        with open(f"{RES}/bd.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(bdr[0].keys())); w.writeheader(); w.writerows(bdr)
    open(f"{RES}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
