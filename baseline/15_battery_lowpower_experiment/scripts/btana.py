#!/usr/bin/env python3
"""Step 6 + 7 analysis. Per block (battery high/low, Low Power Mode, AC) and condition: energy per frame pair from the
chip's counters (as Step 9: last 49 s of each call minus the block's idle, / 30 pairs per second, median of runs,
grouped CPU/GPU/ANE/DRAM/media) and, on battery, from the battery itself (V x I: whole laptop incl. display);
late frames and p99 of the call; battery % per hour. Step 7: the analyzer's time and what it adds to the call
(energy and timing vs V0; C4: <= 2 ms per frame pair and no late frames). Drain and sustained calls: power and
late frames in 5-min steps.
usage: btana.py   reads phase2/bt/, writes phase2/bt/results/
"""
import csv, glob, os, statistics as st, sys
WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
E = f"{WORK}/phase2/bt"; RES = f"{E}/results"
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "he")); sys.path.insert(0, f"{WORK}/tools")
import heana as H
try:
    import analyze_run as A
except Exception:
    A = None
BLOCKS = [("bat_high", "battery > 80 %"), ("bat_high_lpm", "battery > 80 %, Low Power Mode"), ("bat_low", "battery < 30 %"),
          ("bat_low_lpm", "battery < 30 %, Low Power Mode"), ("ac", "AC"), ("ac_lpm", "AC, Low Power Mode"), ("step7", "AC (Step 7)")]
DESC = {"bstar": "B* (NE-NE)", "s720": "MLVC-S 720p (GPU-NE)", "v0": "V0 analyzer off", "v1": "V1 every 15, default",
        "v2": "V2 every 15, CPU", "v3": "V3 every 30, CPU"}
BAT = []
if os.path.exists(f"{E}/battery.csv"):
    for r in csv.DictReader(open(f"{E}/battery.csv")):
        try: BAT.append((float(r["t_epoch_s"]), float(r["W"]), float(r["pct"]), r["external"]))
        except (ValueError, KeyError): pass


def batw(lo, hi):
    v = [-w for t, w, p, x in BAT if lo <= t <= hi]
    return st.mean(v) if v else None


def timing(o):
    if A is None: return None
    try:
        m, fr = A.load(o); out = {}
        for d in "ED":
            s = A.direction_summary(m, fr, d)
            if s: out[d] = s
        return out
    except Exception:
        return None


def main():
    os.makedirs(RES, exist_ok=True)
    L = []; say = lambda s="": (print(s), L.append(s))
    rows = []
    say("STEP 6 + 7: energy beyond AC power and the cost of the scene analyzer (paced 30 fps calls)")
    for tag, bdesc in BLOCKS:
        if not os.path.isdir(f"{E}/{tag}"): continue
        io = f"{E}/{tag}/idle"
        if not os.path.exists(f"{io}/ioe.csv"): continue
        a, b = H.times(io); idle = H.power(f"{io}/ioe.csv", a + 5, b - 1); ib = batw(a + 5, b - 1)
        say(f"\n== {bdesc}: idle {sum(v for c, v in idle.items() if H.group(c)):.0f} mW (chip)" + (f", {ib:.2f} W (battery)" if ib else ""))
        say(f"   {'':<24} {'chip mJ':>8} {'(min-max)':>13} {'CPU':>6} {'GPU':>6} {'ANE':>6} {'DRAM':>6}  {'laptop mJ':>9}  {'late E/D %':>10} {'p99 E/D ms':>12}  extra")
        for c in DESC:
            runs = sorted(glob.glob(f"{E}/{tag}/{c}/r*"))
            res, bres, late, p99, va = [], [], [], [], []
            for o in runs:
                if not os.path.exists(f"{o}/t.txt") or not os.path.exists(f"{o}/ioe.csv"): continue
                t = dict(l.strip().split("=") for l in open(f"{o}/t.txt") if "=" in l)
                if "t_end" not in t: continue
                tb = float(t["t_end"])
                try:   # end of the call itself (the analyzer of Step 7 runs 12 s longer, so t_end can be later)
                    kv = dict(l.strip().split("=", 1) for l in open(f"{o}/run.txt") if "=" in l)
                    fe = max(float(r["end_ms"]) for r in csv.DictReader(open(f"{o}/frames.csv")))
                    tb = min(tb, float(kv["t0_epoch_ms"]) / 1000 + fe / 1000 + 0.5)
                except Exception:
                    pass
                p = H.power(f"{o}/ioe.csv", tb - 50, tb - 1)
                res.append({ch: (p.get(ch, 0) - idle.get(ch, 0)) / 30 for ch in set(p) | set(idle)})
                bw = batw(tb - 50, tb - 1)
                if bw is not None and ib is not None and t.get("ac") == "0": bres.append((bw - ib) * 1000 / 30)
                tm = timing(o)
                if tm:
                    late.append(tuple(tm[d]["late_or_dropped_pct"] for d in "ED" if d in tm))
                    p99.append(tuple(tm[d]["latency_ms_p99"] for d in "ED" if d in tm))
                if os.path.exists(f"{o}/va.csv"):
                    v = [float(r["ms"]) for r in csv.DictReader(open(f"{o}/va.csv"))]
                    if v: va.append(st.median(v))
            if not res: continue
            tot = [sum(v for ch, v in r.items() if H.group(ch)) for r in res]
            g = {k: st.median(sum(v for ch, v in r.items() if H.group(ch) == k) for r in res) for k in ("CPU", "GPU", "ANE", "DRAM")}
            lt = "/".join(f"{max(x[i] for x in late):.2f}" for i in range(len(late[0]))) if late else "-"
            pp = "/".join(f"{st.median(x[i] for x in p99):.1f}" for i in range(len(p99[0]))) if p99 else "-"
            ex = f"analyzer {st.median(va):.2f} ms per analysis" if va else ""
            lap = f"{st.median(bres):9.1f}" if bres else f"{'-':>9}"
            say(f"   {DESC[c]:<24} {st.median(tot):8.1f} ({min(tot):5.1f}-{max(tot):5.1f}) {g['CPU']:6.1f} {g['GPU']:6.1f} {g['ANE']:6.1f} {g['DRAM']:6.1f}  {lap}  {lt:>10} {pp:>12}  {ex}")
            rows.append(dict(block=tag, block_desc=bdesc, cond=c, desc=DESC[c], runs=len(res), chip_mJ=st.median(tot),
                             chip_min=min(tot), chip_max=max(tot), **{f"{k}_mJ": v for k, v in g.items()},
                             laptop_mJ=st.median(bres) if bres else "", late_max=lt, p99_med=pp,
                             analyzer_ms=st.median(va) if va else ""))
    if rows:
        with open(f"{RES}/energy.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    s7 = {r["cond"]: r for r in rows if r["block"] == "step7"}
    if "v0" in s7:
        say("\n== Step 7: what the analyzer adds to the B* call (vs V0; C4 = at most 2 ms per frame pair and no late frames)")
        for c in ("v1", "v2", "v3"):
            if c in s7:
                r = s7[c]; n = 15 if c in ("v1", "v2") else 30
                per = r["analyzer_ms"] / n if r["analyzer_ms"] != "" else float("nan")
                say(f"   {DESC[c]:<24} +{r['chip_mJ'] - s7['v0']['chip_mJ']:.2f} mJ per pair, analyzer {r['analyzer_ms']} ms per analysis "
                    f"= {per:.3f} ms per frame pair, late {r['late_max']} %  -> C4 {'met' if per <= 2 and all(float(x) == 0 for x in r['late_max'].split('/') if x not in ('-', '')) else 'NOT met'}")
    for name in ("drain60/bstar", "sustained30/bstar"):
        o = f"{E}/{name}"
        if not os.path.exists(f"{o}/t.txt"): continue
        t = dict(l.strip().split("=") for l in open(f"{o}/t.txt") if "=" in l)
        a, b = float(t["t_start"]), float(t["t_end"])
        say(f"\n== {name}: {(b - a) / 60:.0f} min, battery {t.get('pct_start')} -> {t.get('pct_end')} %")
        for k in range(int((b - a) // 300)):
            lo, hi = a + 300 * k, a + 300 * (k + 1)
            p = H.power(f"{o}/ioe.csv", lo, hi); bw = batw(lo, hi)
            say(f"   {5 * k:3d}-{5 * k + 5:3d} min: chip {sum(v for c, v in p.items() if H.group(c)):6.0f} mW" + (f", battery {bw:.2f} W" if bw else ""))
        tm = timing(o)
        if tm: say("   late %: " + ", ".join(f"{d} {tm[d]['late_or_dropped_pct']:.2f}" for d in tm))
    if BAT:
        on = [(t, p) for t, w, p, x in BAT if x == "0"]
        if len(on) > 2:
            say(f"\n== on battery: {on[0][1]:.0f} % -> {on[-1][1]:.0f} % in {(on[-1][0] - on[0][0]) / 3600:.2f} h "
                f"({(on[0][1] - on[-1][1]) / ((on[-1][0] - on[0][0]) / 3600):.1f} % per hour, display at maximum brightness)")
    open(f"{RES}/summary.txt", "w").write("\n".join(L) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
