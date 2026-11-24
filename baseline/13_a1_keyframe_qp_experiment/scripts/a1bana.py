#!/usr/bin/env python3
"""A1 round 2 + E4 analysis: BD-rate (4 metrics, mean curves and per clip) for
  B*: I-frame offsets -8 and -10 against A1's no-offset control (phase2/a1, o0), next to round 1's -2/-4/-6
  MLVC-S 540p: I-frame, LTR and both offsets against no offset
  E4: LTR recovery every 32 against the default structure (A2's cost, cross-check with experiment 11), and the LTR/both
      offsets on top of it, against the bound without offset and against the default structure
usage: a1bana.py   reads phase2/a1b/ and phase2/a1/, writes phase2/a1b/results/
"""
import csv, os, statistics as st, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import ana

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/a1b"; RES = f"{OUT}/results"
QPS = [16, 24, 26, 32, 40]
MET = ["psnr_y", "psnr_y_display", "face_psnr_y", "face_lpips"]
NM = {"psnr_y": "coded Y", "psnr_y_display": "display Y", "face_psnr_y": "face Y", "face_lpips": "face LPIPS"}
PAIRS = [("B*: I -6 (round 1)", "a1_o0", "a1_b6"), ("B*: I -8", "a1_o0", "a1b_mlvc_360p_i8"), ("B*: I -10", "a1_o0", "a1b_mlvc_360p_i10"),
         ("MLVC-S 540p: I -4", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_i4"), ("MLVC-S 540p: LTR -4", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_l4"),
         ("MLVC-S 540p: I and LTR -4", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_b4"), ("MLVC-S 540p: I -8", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_i8"),
         ("E4: LTR recovery every 32 (A2 cost)", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_r0"),
         ("E4: + LTR -4, vs the bound", "a1b_mlvcs_540p_r0", "a1b_mlvcs_540p_rl4"),
         ("E4: + I and LTR -4, vs the bound", "a1b_mlvcs_540p_r0", "a1b_mlvcs_540p_rb4"),
         ("E4: bound + LTR -4, vs default", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_rl4"),
         ("E4: bound + I and LTR -4, vs default", "a1b_mlvcs_540p_o0", "a1b_mlvcs_540p_rb4")]


def load():
    R = {}
    for p in (f"{WORK}/phase2/a1/q.csv", f"{OUT}/q.csv"):
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                R.setdefault(r["cfg"], {}).setdefault(r["clip"], {})[int(r["qp"])] = r
    return R


def main():
    os.makedirs(RES, exist_ok=True)
    R = load()
    L = []; say = lambda s="": (print(s), L.append(s))
    say("A1 round 2 + E4: BD-rate (negative = fewer bits for the same quality); per clip: median, clips that gain")
    say(f"   {'':<40}" + "".join(f"{NM[m]:>26}" for m in MET))
    rows = []
    for desc, a, b in PAIRS:
        if a not in R or b not in R:
            continue
        cl = [c for c in R[b] if c in R[a] and all(p in R[a][c] and p in R[b][c] for p in QPS)]
        cells = []
        for m in MET:
            lb = m == "face_lpips"
            mean = lambda cf: [(st.mean(float(R[cf][c][p]["kbps"]) for c in cl),
                                st.mean(float(R[cf][c][p][m]) for c in cl if R[cf][c][p][m] not in ("", "nan"))) for p in QPS]
            bd, _ = ana.bd(mean(a), mean(b), lb)
            per = [x for x in (ana.bd([(float(R[a][c][p]["kbps"]), float(R[a][c][p][m])) for p in QPS],
                                      [(float(R[b][c][p]["kbps"]), float(R[b][c][p][m])) for p in QPS], lb)[0] for c in cl) if x is not None]
            med = st.median(per) if per else None
            rows.append(dict(comparison=desc, reference=a, test=b, metric=m, bd_rate_pct=bd, clip_median_pct=med,
                             clips_gain=sum(x < 0 for x in per), clips=len(per)))
            cells.append(f"{'-' if bd is None else f'{bd:+.2f} %'} ({'-' if med is None else f'{med:+.2f}'}, {sum(x < 0 for x in per)}/{len(per)})")
        say(f"   {desc:<40}" + "".join(f"{c:>26}" for c in cells))
    if rows:
        with open(f"{RES}/bd.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    open(f"{RES}/summary.txt", "w").write("\n".join(L) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
