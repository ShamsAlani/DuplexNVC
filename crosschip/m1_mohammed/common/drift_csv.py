#!/usr/bin/env python3
"""Drift between two decodes of the same bitstream, as a CSV row set in the format of 04_correctness_experiment.

  python3 drift_csv.py <tools dir> <label> <a.nv12> <b.nv12> <WxH> <out.csv> [--iframe-period 64]

Appends rows "<label>,<frames_after_I>,<mean_dB>,<min_dB>" (groups all, 0-0, 1-15, 16-31, 32-47, 48-63) to out.csv
and prints them. <label> names the pair, e.g. M4NE_vs_M1NE, M1NE_vs_M1GPU.
"""
import csv, os, sys
import numpy as np

tools, label, pa, pb, size, out = sys.argv[1:7]
period = int(sys.argv[sys.argv.index("--iframe-period") + 1]) if "--iframe-period" in sys.argv else 64
sys.path.insert(0, tools)
import quality_tools as Q  # noqa: E402

w, h = map(int, size.split("x"))
A, _ = Q.frames(pa, w, h)
B, _ = Q.frames(pb, w, h)
n = min(len(A), len(B))
if len(A) != len(B):
    print(f"  frame counts differ: {len(A)} vs {len(B)} (comparing the first {n})")
ys = np.array([Q.psnr_planes(A[i], B[i], w, h)[0] for i in range(n)])
pos = np.arange(n) % period
rows = [[label, "all", round(float(ys.mean()), 2), round(float(ys.min()), 2)]]
for lo, hi in ((0, 1), (1, 16), (16, 32), (32, 48), (48, period)):
    sel = ys[(pos >= lo) & (pos < hi)]
    if len(sel):
        rows.append([label, f"{lo}-{hi - 1}", round(float(sel.mean()), 2), round(float(sel.min()), 2)])
new = not os.path.isfile(out)
with open(out, "a", newline="") as f:
    wtr = csv.writer(f)
    if new:
        wtr.writerow(["pair", "frames_after_I", "mean_dB", "min_dB"])
    wtr.writerows(rows)
ident = int((ys >= 100.0).sum())
print(f"  {label}: {n} frames, bit-identical {ident}, Y-PSNR between decodes mean {ys.mean():.2f} dB, min {ys.min():.2f} dB")
for r in rows[1:]:
    print(f"    frames {r[1]:>5s} after an I-frame: mean {r[2]:6.2f} dB  min {r[3]:6.2f} dB")
