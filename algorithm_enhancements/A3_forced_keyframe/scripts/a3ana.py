#!/usr/bin/env python3
"""A3 analysis: BD-rate of each trigger policy against no forced I-frame (4 metrics; all 11 clips, the 4 clips with
real entries, the 7 without), how many I-frames each policy forced and how many of them came without a real event,
the size of a forced I-frame against the P-frames before it, and the quality right after each real event.
usage: a3ana.py   reads phase2/a3/, writes phase2/a3/results/
"""
import csv, os, statistics as st, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import ana

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/a3"; RES = f"{OUT}/results"
SETS = {"mlvc_360p": "B* (full MLVC 360p)", "mlvcs_540p": "MLVC-S 540p"}
TRIGS = ["truth", "fused", "diff"]
QPS = [16, 24, 26, 32, 40]
MET = ["psnr_y", "psnr_y_display", "face_psnr_y", "face_lpips"]
NM = {"psnr_y": "coded Y", "psnr_y_display": "display Y", "face_psnr_y": "face Y", "face_lpips": "face LPIPS"}


def main():
    os.makedirs(RES, exist_ok=True)
    R = {}
    for r in csv.DictReader(open(f"{OUT}/q.csv")):
        R.setdefault(r["cfg"], {}).setdefault(r["clip"], {})[int(r["qp"])] = r
    truth = {}
    for r in csv.DictReader(open(f"{D}/data/events_truth.csv")):
        if int(r["frame"]) > 0:
            truth.setdefault(r["clip"], []).append(int(r["frame"]))
    clips = sorted({c for g in R.values() for c in g})
    groups = {"all 11 clips": clips, "4 clips with real entries": [c for c in clips if c in truth],
              f"{len([c for c in clips if c not in truth])} clips without": [c for c in clips if c not in truth]}
    L = []; say = lambda s="": (print(s), L.append(s))
    say("A3: forced I-frame when the content changes (Step 8 multi-person clips)")
    say("\n== forced I-frames per policy (clip: frames); real events from Step 8 in brackets")
    for c in clips:
        tr = {t: open(f"{OUT}/trig/{c}_{t}.txt").read().split() if os.path.exists(f"{OUT}/trig/{c}_{t}.txt") else [] for t in TRIGS}
        say(f"   {c}: truth {tr['truth']}  fused {tr['fused']}  diff {tr['diff']}")
    bdrows = []
    for s, sd in SETS.items():
        base = f"a3_none_{s}"
        if base not in R:
            continue
        say(f"\n== {sd}: BD-rate vs no forced I-frame (negative = fewer bits for the same quality); per clip: median, clips that gain")
        for gname, gcl in groups.items():
            say(f"   {gname}")
            for t in TRIGS:
                cfg = f"a3_{t}_{s}"
                if cfg not in R:
                    continue
                cells = []
                for m in MET:
                    lb = m == "face_lpips"
                    cl = [c for c in gcl if c in R[cfg] and c in R[base] and all(p in R[cfg][c] and p in R[base][c] for p in QPS)]
                    if not cl:
                        cells.append("-"); continue
                    mean = lambda cf: [(st.mean(float(R[cf][c][p]["kbps"]) for c in cl),
                                        st.mean(float(R[cf][c][p][m]) for c in cl if R[cf][c][p][m] not in ("", "nan"))) for p in QPS]
                    b, _ = ana.bd(mean(base), mean(cfg), lb)
                    per = [x for x in (ana.bd([(float(R[base][c][p]["kbps"]), float(R[base][c][p][m])) for p in QPS if R[base][c][p][m] not in ("", "nan")],
                                              [(float(R[cfg][c][p]["kbps"]), float(R[cfg][c][p][m])) for p in QPS if R[cfg][c][p][m] not in ("", "nan")], lb)[0]
                                       for c in cl) if x is not None]
                    med = st.median(per) if per else None
                    bdrows.append(dict(setting=s, group=gname, trigger=t, metric=m, bd_rate_pct=b, clip_median_pct=med,
                                       clips_gain=sum(x < 0 for x in per), clips=len(per)))
                    cells.append(f"{'-' if b is None else f'{b:+.2f} %'} ({'-' if med is None else f'{med:+.2f}'}, {sum(x < 0 for x in per)}/{len(per)})")
                say(f"     {t:<6}" + "".join(f"{NM[m]:>12}: {c:<24}" for m, c in zip(MET, cells)))
    if bdrows:
        with open(f"{RES}/bd.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(bdrows[0].keys())); w.writeheader(); w.writerows(bdrows)
    say("\n== cost of a switch (QP 26): forced I-frame size / mean of the 10 P-frames before it; coded PSNR-Y in the "
        "30 frames after each real event (truth) vs no forced I-frame")
    rows = []
    for s, sd in SETS.items():
        for t in TRIGS:
            ratios, gains = [], []
            for c in clips:
                fl = f"{OUT}/flog/a3_{t}_{s}/{c}_qp26.csv"
                if not os.path.exists(fl):
                    continue
                F = list(csv.DictReader(open(fl)))
                for k, r in enumerate(F):
                    if r["forced"] == "1":
                        prev = [int(x["bytes"]) for x in F[max(0, k - 10):k] if x["type"] != "0"]
                        if prev:
                            ratios.append(int(r["bytes"]) / st.mean(prev))
                fa, fb = f"{OUT}/frames/a3_{t}_{s}/{c}_qp26.csv", f"{OUT}/frames/a3_none_{s}/{c}_qp26.csv"
                if os.path.exists(fa) and os.path.exists(fb):
                    A = [float(x["psnr_y"]) for x in csv.DictReader(open(fa))]
                    B = [float(x["psnr_y"]) for x in csv.DictReader(open(fb))]
                    for e in truth.get(c, []):
                        w = range(e, min(e + 30, len(A), len(B)))
                        if len(w):
                            gains.append(st.mean(A[i] for i in w) - st.mean(B[i] for i in w))
            rows.append(dict(setting=s, trigger=t, forced=len(ratios), size_ratio_median=st.median(ratios) if ratios else "",
                             psnr_gain_after_event_db=st.mean(gains) if gains else ""))
            say(f"   {sd:<20} {t:<6} forced {len(ratios):3d}  I-frame size {st.median(ratios) if ratios else float('nan'):5.1f}x a P-frame  "
                f"PSNR-Y after real events {st.mean(gains) if gains else float('nan'):+.2f} dB")
    with open(f"{RES}/switch_cost.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    open(f"{RES}/summary.txt", "w").write("\n".join(L) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
