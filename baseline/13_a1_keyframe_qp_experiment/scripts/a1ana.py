#!/usr/bin/env python3
"""A1 analysis: mean rate-distortion per configuration and BD-rate of every offset against no offset (o0),
on the mean curves (as experiment 10) and per clip (median and clips that gain), plus where the bits went.
usage: a1ana.py   reads phase2/a1/q.csv and flog/, writes phase2/a1/results/
"""
import csv, os, statistics as st, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import ana  # experiment 10's analysis (bd, PCHIP)

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/a1"; RES = f"{OUT}/results"
TAGS = ["o0", "b2", "b4", "b6", "i4", "l4"]
DESC = {"o0": "no offset (B*)", "b2": "I and LTR -2", "b4": "I and LTR -4", "b6": "I and LTR -6",
        "i4": "I only -4", "l4": "LTR only -4"}
QPS = [16, 24, 26, 32, 40]
MET = ["psnr_y", "psnr_y_display", "face_psnr_y", "face_lpips"]
NM = {"psnr_y": "coded Y", "psnr_y_display": "display Y", "face_psnr_y": "face Y", "face_lpips": "face LPIPS"}


def main():
    os.makedirs(RES, exist_ok=True)
    R = list(csv.DictReader(open(f"{OUT}/q.csv")))
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    G = {}
    for r in R:
        G.setdefault(r["cfg"][3:], {}).setdefault(int(r["qp"]), []).append(r)
    tags = [t for t in TAGS if t in G]
    say("A1: QP offset on I-frames and LTR frames, B* (full MLVC 360p, NE-NE), 20 evaluation clips")
    say("\n== mean of the clips (kbps / coded PSNR-Y / display PSNR-Y / face PSNR-Y / face LPIPS)")
    M, rows = {}, []
    for t in tags:
        M[t] = {}
        for qp in QPS:
            g = G[t].get(qp, [])
            if not g:
                continue
            m = {k: st.mean(float(r[k]) for r in g if r[k] not in ("", "nan")) for k in ["kbps"] + MET}
            m["clips"] = len(g); M[t][qp] = m
            rows.append(dict(cfg=t, desc=DESC[t], qp=qp, **m))
        say(f"   {DESC[t]:<16} " + "  ".join(f"QP{qp} {M[t][qp]['kbps']:.0f}/{M[t][qp]['psnr_y']:.2f}/"
                                             f"{M[t][qp]['psnr_y_display']:.2f}/{M[t][qp]['face_psnr_y']:.2f}/"
                                             f"{M[t][qp]['face_lpips']:.3f}" for qp in QPS if qp in M[t]))
    with open(f"{RES}/rd_mean.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    say("\n== BD-rate vs no offset (negative = fewer bits for the same quality); per clip: median, clips that gain")
    say(f"   {'':<16} " + "".join(f"{NM[m]:>26}" for m in MET))
    bdrows = []
    clips = sorted({r["clip"] for r in R})
    for t in tags:
        if t == "o0":
            continue
        cells = []
        for m in MET:
            lb = m == "face_lpips"
            ref = [(M["o0"][qp]["kbps"], M["o0"][qp][m]) for qp in QPS if qp in M["o0"]]
            tst = [(M[t][qp]["kbps"], M[t][qp][m]) for qp in QPS if qp in M[t]]
            b, _ = ana.bd(ref, tst, lb)
            per = []
            for c in clips:
                rr = [(float(r["kbps"]), float(r[m])) for qp in QPS for r in G["o0"].get(qp, []) if r["clip"] == c and r[m] not in ("", "nan")]
                tt = [(float(r["kbps"]), float(r[m])) for qp in QPS for r in G[t].get(qp, []) if r["clip"] == c and r[m] not in ("", "nan")]
                x, _ = ana.bd(rr, tt, lb)
                if x is not None:
                    per.append(x)
            med = st.median(per) if per else None
            gain = sum(x < 0 for x in per)
            bdrows.append(dict(cfg=t, desc=DESC[t], metric=m, bd_rate_pct=b, clip_median_pct=med, clips_gain=gain,
                               clips=len(per)))
            cells.append(f"{'-' if b is None else f'{b:+.2f} %'} ({'-' if med is None else f'{med:+.2f}'}, {gain}/{len(per)})")
        say(f"   {DESC[t]:<16} " + "".join(f"{c:>26}" for c in cells))
    with open(f"{RES}/bd.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bdrows[0].keys())); w.writeheader(); w.writerows(bdrows)
    # where the bits went (frame logs)
    say("\n== share of the bits in I-frames / LTR frames / other frames (mean over clips, QP 26)")
    for t in tags:
        d = f"{OUT}/flog/{t}"
        tot = [0, 0, 0]
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith("_qp26.csv"):
                    for r in csv.DictReader(open(f"{d}/{fn}")):
                        k = 0 if r["type"] == "0" else (1 if r["ltr"] == "1" else 2)
                        tot[k] += int(r["bytes"])
        s = sum(tot)
        if s:
            say(f"   {DESC[t]:<16} I {100 * tot[0] / s:5.1f} %   LTR {100 * tot[1] / s:5.1f} %   other {100 * tot[2] / s:5.1f} %")
    open(f"{RES}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
