#!/usr/bin/env python3
"""Battery-side power of the Step 6 calls, from battery.csv (V x I once a second, read from AppleSmartBattery).
The battery gauge reports a current averaged over tens of seconds, so a 60 s call never reaches its steady value:
the per-call figures read low and are only indicative. Steady values come from the 60-min B* call and the 5-min
MLVC-S 720p calls. Idle = the 60 s rests between calls (the start of the first idle recording reads 0 W while the
gauge catches up after unplugging).
usage: battery_side.py [phase2/bt folder]   writes results/battery_side.csv and prints a table
"""
import csv, glob, os, statistics as st, sys
E = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/duplexnvc-baseline/phase2/bt")
B = [(float(r["t_epoch_s"]), -float(r["W"]), float(r["pct"])) for r in csv.DictReader(open(f"{E}/battery.csv"))
     if r["W"] and r["external"] == "0"]


def w(a, b):
    v = [x for t, x, _ in B if a <= t <= b]
    return st.mean(v) if v else float("nan")


def tt(p):
    d = dict(l.strip().split("=", 1) for l in open(p) if "=" in l)
    return float(d["t_start"]), float(d["t_end"]), d.get("pct_start"), d.get("pct_end")


rows = []
for blk, lab in [("bat_high", "battery high, normal"), ("bat_high_lpm", "battery high, Low Power Mode"),
                 ("bat_low", "battery < 30 %, normal"), ("bat_low_lpm", "battery < 30 %, Low Power Mode")]:
    runs = sorted(glob.glob(f"{E}/{blk}/*/r*/t.txt"))
    if not runs:
        continue
    rest = st.median([w(tt(r)[1] + 60, tt(r)[1] + 100) for r in runs])
    for c in ("bstar", "s720"):
        v = [w(tt(r)[1] - 30, tt(r)[1]) for r in sorted(glob.glob(f"{E}/{blk}/{c}/r*/t.txt"))]
        if v:
            rows.append(dict(block=lab, cond=c, kind="60 s calls (indicative)", n=len(v), idle_W=round(rest, 2),
                             call_W=round(st.median(v), 2), extra_mJ_per_pair=round((st.median(v) - rest) / 30 * 1000, 1),
                             pct_per_h=""))
rest = st.median([w(tt(r)[1] + 60, tt(r)[1] + 100) for r in glob.glob(f"{E}/bat_*/*/r*/t.txt")])
a, b, p0, p1 = tt(f"{E}/drain60/bstar/t.txt")
rows.append(dict(block="60-min B* call", cond="bstar", kind="steady (after 5 min)", n=1, idle_W=round(rest, 2),
                 call_W=round(w(a + 300, b), 2), extra_mJ_per_pair=round((w(a + 300, b) - rest) / 30 * 1000, 1),
                 pct_per_h=round((float(p0) - float(p1)) / ((b - a) / 3600), 1)))
dm = sorted(glob.glob(f"{E}/drain_more/*/t.txt"))
if dm:
    W = st.median([w(tt(r)[0] + 60, tt(r)[1]) for r in dm])
    pph = st.median([(float(tt(r)[2]) - float(tt(r)[3])) / ((tt(r)[1] - tt(r)[0]) / 3600) for r in dm])
    rows.append(dict(block="5-min MLVC-S 720p calls", cond="s720", kind="steady (after 1 min)", n=len(dm), idle_W=round(rest, 2),
                     call_W=round(W, 2), extra_mJ_per_pair=round((W - rest) / 30 * 1000, 1), pct_per_h=round(pph, 1)))
os.makedirs(f"{E}/results", exist_ok=True)
with open(f"{E}/results/battery_side.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
for r in rows:
    print(f"{r['block']:<32} {r['cond']:<6} {r['kind']:<24} n={r['n']}  idle {r['idle_W']:.2f} W  call {r['call_W']:.2f} W  "
          f"+{r['extra_mJ_per_pair']} mJ/pair  {r['pct_per_h']} %/h")
