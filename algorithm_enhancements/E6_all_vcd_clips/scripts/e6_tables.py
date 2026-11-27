#!/usr/bin/env python3
"""E6 analysis: A2's bound (LTR recovery every 32 frames, l32) against MLVC's default structure (main) on all VCD
clips measured so far, per clip group and over all groups, with 95 % confidence intervals.
Cost: BD-rate (coded PSNR-Y, QP 16/24/32/40) of NE -> NE with l32 against NE -> NE with main, (a) of the mean curve
over the clips, as A2 reports it, and (b) per clip, mean with 95 % CI and median.
Drift: worst frame (PSNR-Y of the decode against the encoder-side decode) over the two mismatched pairs
(NE -> GPU, GPU -> NE): per clip, then mean with 95 % CI, and the worst clip.
Usage: e6_tables.py [r.csv] [output folder]    Writes e6.csv, e6_per_clip.csv, summary_e6.txt, summary_e6.md
"""
import csv, math, os, statistics as st, sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy import stats

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
RC = sys.argv[1] if len(sys.argv) > 1 else f"{WORK}/phase2/e6/r.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{WORK}/phase2/e6/results"
QPS = [16, 24, 32, 40]
GROUPS = ["th", "th-bb", "th-m", "th-ob"]
GNAME = {"th": "talking head", "th-bb": "talking head, blurred background", "th-m": "talking head, mobile (portrait, rotated)",
         "th-ob": "talking head, other background"}
SETS = [("mlvcs_540p", "MLVC-S 540p"), ("mlvc_360p", "Full MLVC 360p (B*)")]
CROSS = [("npu", "gpu"), ("gpu", "npu")]


def bd(ref, test):
    if len(ref) < 4 or len(test) < 4:
        return None
    r = sorted((q, math.log10(k)) for k, q in ref); t = sorted((q, math.log10(k)) for k, q in test)
    lo, hi = max(r[0][0], t[0][0]), min(r[-1][0], t[-1][0])
    if hi <= lo:
        return None
    fr = PchipInterpolator(*zip(*r)); ft = PchipInterpolator(*zip(*t)); qq = np.linspace(lo, hi, 1000)
    tr = getattr(np, "trapezoid", None) or np.trapz
    return float((10 ** (tr(ft(qq) - fr(qq), qq) / (hi - lo)) - 1) * 100)


def ci(x):
    if len(x) < 2:
        return float("nan")
    return float(stats.t.ppf(0.975, len(x) - 1) * st.stdev(x) / math.sqrt(len(x)))


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(RC)))
    fails = sum(1 for r in rows if r["dec_ok"] != "1" or r.get("enc_ok", "1") != "1")
    per = []      # per (setting, group, clip)
    for s, _ in SETS:
        R = [r for r in rows if r["setting"] == s]
        for g in GROUPS:
            for k in sorted({r["clip"] for r in R if r["group"] == g}):
                x = [r for r in R if r["group"] == g and r["clip"] == k]
                ne = {(r["variant"], int(r["qp"])): r for r in x if r["enc"] == "npu" and r["dec"] == "npu" and r["dec_ok"] == "1"}
                if not all((v, q) in ne for v in ("main", "l32") for q in QPS):
                    continue
                cur = {v: [(float(ne[(v, q)]["kbps"]), float(ne[(v, q)]["psnr_y"])) for q in QPS] for v in ("main", "l32")}
                wf = {}
                for v in ("main", "l32"):
                    w = [float(r["drift_min_db"]) for r in x if r["variant"] == v and (r["enc"], r["dec"]) in CROSS
                         and r["dec_ok"] == "1" and r["drift_min_db"] not in ("", None)]
                    wf[v] = min(w) if w else None
                b = bd(cur["main"], cur["l32"])
                if b is None or None in wf.values():
                    continue
                per.append(dict(setting=s, group=g, clip=k, bd_l32_vs_main_pct=round(b, 2),
                                worst_main_db=round(wf["main"], 2), worst_l32_db=round(wf["l32"], 2), curves=cur))
    with open(f"{OUT}/e6_per_clip.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["setting", "group", "clip", "bd_l32_vs_main_pct", "worst_main_db", "worst_l32_db"],
                           extrasaction="ignore")
        w.writeheader(); w.writerows(per)
    T, txt, md = [], [], []
    txt.append(f"E6: A2's bound (LTR recovery every 32 frames) against the default structure, VCD clips; failed runs: {fails}")
    md.append("| Setting | Clips | Cost, mean curve (as A2) | Cost per clip: mean ± 95 % CI (median) | Worst frame per clip, default: mean ± CI (worst clip) | Worst frame per clip, LTR every 32: mean ± CI (worst clip) |")
    md.append("|---|---|---|---|---|---|")
    for s, sname in SETS:
        for g in GROUPS + ["all"]:
            P = [p for p in per if p["setting"] == s and (g == "all" or p["group"] == g)]
            if not P:
                continue
            mc = {v: [(st.mean(p["curves"][v][i][0] for p in P), st.mean(p["curves"][v][i][1] for p in P)) for i in range(4)]
                  for v in ("main", "l32")}
            b = [p["bd_l32_vs_main_pct"] for p in P]; wm = [p["worst_main_db"] for p in P]; wl = [p["worst_l32_db"] for p in P]
            row = dict(setting=s, group=g, clips=len(P), bd_mean_curve_pct=round(bd(mc["main"], mc["l32"]), 2),
                       bd_per_clip_mean_pct=round(st.mean(b), 2), bd_per_clip_ci95=round(ci(b), 2), bd_per_clip_median_pct=round(st.median(b), 2),
                       worst_main_mean_db=round(st.mean(wm), 2), worst_main_ci95=round(ci(wm), 2), worst_main_min_db=round(min(wm), 2),
                       worst_l32_mean_db=round(st.mean(wl), 2), worst_l32_ci95=round(ci(wl), 2), worst_l32_min_db=round(min(wl), 2))
            T.append(row)
            lab = "all groups" if g == "all" else f"{g} ({GNAME[g]})"
            txt.append(f"{sname:<22} {lab:<45} n={len(P):>3}  cost {row['bd_mean_curve_pct']:+.2f} % (mean curve); per clip "
                       f"{row['bd_per_clip_mean_pct']:+.2f} ± {row['bd_per_clip_ci95']:.2f} % (median {row['bd_per_clip_median_pct']:+.2f});"
                       f"  worst frame default {row['worst_main_mean_db']:.1f} ± {row['worst_main_ci95']:.1f} dB (min {row['worst_main_min_db']:.1f}),"
                       f" LTR-32 {row['worst_l32_mean_db']:.1f} ± {row['worst_l32_ci95']:.1f} dB (min {row['worst_l32_min_db']:.1f})")
            bold = "**" if g == "all" else ""
            mname = sname.replace("*", "\\*")
            md.append(f"| {bold}{mname}, {'all groups' if g == 'all' else '`' + g + '`'}{bold} | {len(P)} | {bold}{row['bd_mean_curve_pct']:+.1f} %{bold} | "
                      f"{row['bd_per_clip_mean_pct']:+.1f} ± {row['bd_per_clip_ci95']:.1f} % ({row['bd_per_clip_median_pct']:+.1f} %) | "
                      f"{row['worst_main_mean_db']:.1f} ± {row['worst_main_ci95']:.1f} dB ({row['worst_main_min_db']:.1f} dB) | "
                      f"{row['worst_l32_mean_db']:.1f} ± {row['worst_l32_ci95']:.1f} dB ({row['worst_l32_min_db']:.1f} dB) |")
    with open(f"{OUT}/e6.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(T[0])); w.writeheader(); w.writerows(T)
    open(f"{OUT}/summary_e6.txt", "w").write("\n".join(txt) + "\n")
    open(f"{OUT}/summary_e6.md", "w").write("\n".join(md) + "\n")
    print("\n".join(txt)); print(f"\n== written: {OUT}/e6.csv, e6_per_clip.csv, summary_e6.txt, summary_e6.md")


if __name__ == "__main__":
    main()
