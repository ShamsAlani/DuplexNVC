#!/usr/bin/env python3
"""Step 4b energy summary: energy per frame pair per setting and QP (paced duplex 30 fps, idle subtracted).

usage: energy_per_qp_table.py   (reads ~/Downloads/duplexnvc-baseline/phase2/4b/energy/, writes energy/energy_qp.csv)
Same calculation as X3 (step4_sum.py): mean power over the steady window of each run (after warm-up, 1 s trimmed
at both ends) minus the setting's 120 s idle power, times the window length, divided by the frame pairs; median of the
runs. Also the late share, frame rate, p99 and bitrate per direction (median of the runs), and a check of QP 26
against the X3 value.
"""
import csv, glob, os, statistics as st, sys

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
TOOLS = f"{WORK}/tools"
E = f"{WORK}/phase2/4b/energy"
X3 = f"{WORK}/phase2/step4/table_feasible.csv"
sys.path.insert(0, TOOLS)
import analyze_run as A

QPS = [16, 24, 26, 32, 40]
CFGS = ["mlvc_360p_npu-npu", "mlvcs_540p_npu-npu", "mlvc_540p_gpu-npu", "mlvcs_720p_gpu-npu",
        "mlvc_720p_npu-npu", "mlvcs_1080p_npu-npu", "mlvc_1080p_npu-npu"]
B_STAR_MJ = 65.3


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def run_energy(r, idle):
    meta, rows = A.load(r)
    smp = A.parse_pm(os.path.join(r, "power.txt"))
    t0 = float(meta["t0_epoch_ms"]) / 1000
    warm = t0 + max((x["end_ms"] for x in rows if x["warmup"]), default=0) / 1000
    tend = t0 + max(x["end_ms"] for x in rows) / 1000
    win = [s for s in smp if warm + 1 <= s[0] <= tend - 1]
    steady = [x for x in rows if not x["warmup"]]
    pairs = min(sum(x["dir"] == "E" for x in steady), sum(x["dir"] == "D" for x in steady))
    secs = (max(x["end_ms"] for x in steady) - min(x["sched_ms"] for x in steady)) / 1000
    if not win or not pairs:
        return None
    out = {}
    for k in ("combined", "ane", "gpu", "cpu"):
        pi = A.mean_power(idle, k) if idle else 0.0
        out[k] = (A.mean_power(win, k) - pi) / 1000 * secs * 1000 / pairs
    return out


def main():
    rows = []
    for c in CFGS:
        s = c.rsplit("_", 1)[0]
        ip = f"{E}/idle_{s}/power.txt"
        idle = A.parse_pm(ip) if os.path.exists(ip) else []
        for q in QPS:
            runs = sorted(r for r in glob.glob(f"{E}/{c}/qp{q}_r*")
                          if os.path.isdir(r) and os.path.exists(f"{r}/frames.csv") and os.path.exists(f"{r}/power.txt"))
            if not runs:
                continue
            en, summ = [], {"E": [], "D": []}
            for r in runs:
                try:
                    en.append(run_energy(r, idle))
                    m, fr = A.load(r)
                    for d in ("E", "D"):
                        summ[d].append(A.direction_summary(m, fr, d))
                except Exception as ex:
                    print(f"   skipped {r}: {ex}")
            en = [x for x in en if x]
            row = dict(cfg=c, setting=s, placement=c.rsplit("_", 1)[1], qp=q, runs=len(en),
                       **{f"mJ_{k}": med(x[k] for x in en) for k in ("combined", "ane", "gpu", "cpu")},
                       mJ_min=min((x["combined"] for x in en), default=None),
                       mJ_max=max((x["combined"] for x in en), default=None))
            for d, n in (("E", "send"), ("D", "recv")):
                ss = [x for x in summ[d] if x]
                for key, col in (("late_or_dropped_pct", "L"), ("achieved_fps", "fps"), ("latency_ms_p99", "p99"),
                                 ("kbps", "kbps")):
                    row[f"{col}_{n}"] = med(x[key] for x in ss)
            rows.append(row)
    if not rows:
        sys.exit("no energy runs found")
    fields = list(rows[0].keys())
    with open(f"{E}/energy_qp.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
    x3 = {}
    if os.path.exists(X3):
        for r in csv.DictReader(open(X3)):
            v = r.get("mJ_combined") or r.get("mJ_per_pair")
            if v:
                x3[f"{r['model']}_{r['res']}_{r['enc']}-{r['dec']}"] = float(v)
    x3["mlvc_360p_npu-npu"] = B_STAR_MJ
    print("mJ per frame pair (median of runs, min-max), late share send/recv %, camera kbps; QP 26 vs X3")
    for c in CFGS:
        g = {r["qp"]: r for r in rows if r["cfg"] == c}
        if not g:
            continue
        print(f"   {c}")
        for q in QPS:
            if q in g:
                r = g[q]
                f = lambda v, p=1: "-" if v is None else f"{v:.{p}f}"
                extra = ""
                if q == 26 and c in x3:
                    extra = f"   X3 {x3[c]:.1f} mJ ({(r['mJ_combined'] / x3[c] - 1) * 100:+.1f} %)"
                print(f"      QP {q:2d}: {f(r['mJ_combined']):>7} mJ ({f(r['mJ_min'])}-{f(r['mJ_max'])}, {r['runs']} runs)"
                      f"  NE/GPU/CPU {f(r['mJ_ane'])}/{f(r['mJ_gpu'])}/{f(r['mJ_cpu'])}"
                      f"  L {f(r['L_send'], 2)}/{f(r['L_recv'], 2)} %  {f(r['kbps_send'], 0)} kbps{extra}")
        if 16 in g and 40 in g and g[40]["mJ_combined"]:
            print(f"      QP 16 / QP 40 energy ratio: {g[16]['mJ_combined'] / g[40]['mJ_combined']:.2f}")
    print(f"-> {E}/energy_qp.csv")


if __name__ == "__main__":
    main()
