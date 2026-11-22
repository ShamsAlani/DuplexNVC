#!/usr/bin/env python3
"""Step 9 energy analysis: energy per frame pair (mJ) per condition from the chip's energy counters (IOReport).
Power of a run = energy / time over its last 49 s (steady state, after model loading and warm-up), minus the idle
power (mean of the 120 s idle recordings at the start and the end), divided by 30 frame pairs per second; median of
the runs. Channels are grouped as monitoring tools do (macmon): CPU = names ending 'CPU Energy', GPU = 'GPU Energy',
ANE = starting 'ANE', DRAM = starting 'DRAM', media = video encoder/decoder blocks (AVE, AVD, VENC, VDEC, ProRes, MSR);
every channel that changes by more than 5 mW is also listed, so the grouping can be checked.
usage: heana.py   reads phase2/he/, writes phase2/he/results/
"""
import csv, glob, os, re, statistics as st, sys
WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
E = f"{WORK}/phase2/he"; RES = f"{E}/results"
sys.path.insert(0, f"{WORK}/tools")
CONDS = ["hevc_360p", "mlvc_360p", "mlvcs_540p", "hevc_720p", "mlvcs_720p"]
DESC = {"hevc_360p": "HW HEVC 360p, 287 kbps", "mlvc_360p": "B* (full MLVC 360p, NE-NE)",
        "mlvcs_540p": "MLVC-S 540p (NE-NE)", "hevc_720p": "HW HEVC 720p, 847 kbps", "mlvcs_720p": "MLVC-S 720p (GPU-NE)"}
MEDIA = re.compile(r"AVE|AVD|VENC|VDEC|ProRes|PRORES|MSR|JPG|AV1", re.I)


def group(ch):
    if ch.endswith("CPU Energy"): return "CPU"
    if ch == "GPU Energy" or ch == "GPU": return "GPU"
    if ch.startswith("ANE"): return "ANE"
    if ch.startswith("DRAM"): return "DRAM"
    if MEDIA.search(ch): return "media"
    return None


def power(path, lo=None, hi=None):
    """mean power per channel (mW) over [lo, hi] (epoch s)"""
    e, t = {}, {}
    for r in csv.DictReader(open(path)):
        ts = float(r["t_epoch_s"])
        if (lo is not None and ts < lo) or (hi is not None and ts > hi):
            continue
        e[r["channel"]] = e.get(r["channel"], 0.0) + float(r["energy_mJ"])
        t[r["channel"]] = t.get(r["channel"], 0.0) + float(r["dt_s"])
    return {c: e[c] / t[c] for c in e if t[c] > 0}


def times(o):
    d = dict(l.strip().split("=") for l in open(f"{o}/t.txt") if "=" in l)
    return float(d["t_start"]), float(d["t_end"])


def main():
    os.makedirs(RES, exist_ok=True)
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    idles = []
    for nm in ("start", "end"):
        o = f"{E}/idle_{nm}"
        if os.path.exists(f"{o}/ioe.csv"):
            a, b = times(o); idles.append(power(f"{o}/ioe.csv", a + 5, b - 1))
    if not idles:
        sys.exit("no idle recording")
    chans = sorted(set().union(*idles))
    idle = {c: st.mean(i.get(c, 0.0) for i in idles) for c in chans}
    say("STEP 9 (energy): paced 30 fps two-way call, energy per frame pair from the chip's counters (IOReport)")
    say(f"idle power (mean of {len(idles)} recordings): total of grouped channels "
        f"{sum(v for c, v in idle.items() if group(c)):.0f} mW")
    rows, per_ch = [], {}
    for c in CONDS:
        runs = sorted(glob.glob(f"{E}/{c}/r*"))
        res = []
        for o in runs:
            if not os.path.exists(f"{o}/ioe.csv") or not os.path.exists(f"{o}/t.txt"):
                continue
            a, b = times(o)
            p = power(f"{o}/ioe.csv", b - 50, b - 1)
            res.append({ch: (p.get(ch, 0.0) - idle.get(ch, 0.0)) / 30.0 for ch in set(p) | set(idle)})  # mW/30 = mJ/pair
        if not res:
            continue
        allc = sorted(set().union(*res))
        med = {ch: st.median(r.get(ch, 0.0) for r in res) for ch in allc}
        tot_runs = [sum(v for ch, v in r.items() if group(ch)) for r in res]
        g = {k: sum(v for ch, v in med.items() if group(ch) == k) for k in ("CPU", "GPU", "ANE", "DRAM", "media")}
        row = dict(cond=c, desc=DESC[c], runs=len(res), total_mJ=st.median(tot_runs), total_min=min(tot_runs),
                   total_max=max(tot_runs), **{f"{k}_mJ": v for k, v in g.items()})
        late = ""
        if c.startswith("mlvc"):
            try:
                import analyze_run as A
                ls = []
                for o in runs:
                    m, fr = A.load(o)
                    for d in "ED":
                        s = A.direction_summary(m, fr, d)
                        if s: ls.append(s["late_or_dropped_pct"])
                late = max(ls) if ls else ""
            except Exception:
                pass
        row["late_max_pct"] = late
        rows.append(row); per_ch[c] = med
    say("\n== energy per frame pair (mJ, median of runs, idle subtracted)")
    say(f"   {'':<28} {'total':>7} {'(min-max)':>14} {'CPU':>6} {'GPU':>6} {'ANE':>6} {'DRAM':>6} {'media':>6}  late")
    for r in rows:
        say(f"   {r['desc']:<28} {r['total_mJ']:7.1f} ({r['total_min']:5.1f}-{r['total_max']:5.1f}) {r['CPU_mJ']:6.1f} "
            f"{r['GPU_mJ']:6.1f} {r['ANE_mJ']:6.1f} {r['DRAM_mJ']:6.1f} {r['media_mJ']:6.1f}  {r['late_max_pct']}")
    say("\n== every channel that changes by more than 0.17 mJ per pair (5 mW), for checking the grouping")
    for c, med in per_ch.items():
        big = sorted(((v, ch) for ch, v in med.items() if abs(v) > 5 / 30), reverse=True)
        say(f"   {DESC[c]}: " + "; ".join(f"{ch} [{group(ch) or '-'}] {v:.1f}" for v, ch in big))
    with open(f"{RES}/energy.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(f"{RES}/channels.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cond", "channel", "group", "mJ_per_pair", "idle_mW"])
        for c, med in per_ch.items():
            for ch, v in sorted(med.items()):
                w.writerow([c, ch, group(ch) or "", round(v, 4), round(idle.get(ch, 0.0), 2)])
    open(f"{RES}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== results in {RES}")


if __name__ == "__main__":
    main()
