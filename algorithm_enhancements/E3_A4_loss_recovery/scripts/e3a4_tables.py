#!/usr/bin/env python3
"""E3 + A4 analysis: reads phase2/e3a4/runs/*/*_sum.csv and writes phase2/e3a4/results/.

E3 (fixed marking): per setting x clip group x loss pattern x arm: kbps, PSNR-Y of the frames shown (a frozen frame
counts against the current source frame), frames frozen (%), freeze events, mean and longest freeze, recovery and
I-frame sizes. Paired differences between arms over clip x QP (mean and 95 % confidence interval).
A4 (ltr arm): adaptive vs fixed marking, same measures, marks per run; call clips (people entering or leaving) and
VCD clips separately.
usage: e3a4_tables.py
"""
import csv, glob, math, os, statistics as st

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/e3a4"
R = f"{OUT}/results"
CALL = {"ce4peo", "cejohn", "cekris", "px2ent", "px4ppl", "px5ppl", "px7ppl", "pxcrwd", "pxdown", "pxentr", "pxleav"}
try:
    from scipy.stats import t as tdist
except Exception:
    tdist = None


def ci(v):
    if len(v) < 2:
        return (st.mean(v) if v else float("nan")), float("nan")
    m, s = st.mean(v), st.stdev(v)
    k = tdist.ppf(0.975, len(v) - 1) if tdist else 1.96
    return m, k * s / math.sqrt(len(v))


def load():
    rows = []
    for p in glob.glob(f"{OUT}/runs/*/*_sum.csv"):
        s = p.split("/")[-2]
        b = os.path.basename(p)[:-8]
        c6, q = b.rsplit("_qp", 1)
        for r in csv.DictReader(open(p)):
            r = dict(r, setting=s, clip=c6, qp=int(q), group="call" if c6 in CALL else "vcd")
            for k in list(r):
                if k not in ("pattern", "arm", "marking", "setting", "clip", "group"):
                    r[k] = float(r[k]) if r[k] not in ("", None) else float("nan")
            rows.append(r)
    return rows


def main():
    os.makedirs(R, exist_ok=True)
    rows = load()
    if not rows:
        print("no runs yet"); return
    lines = []
    say = lambda x="": (print(x), lines.append(x))
    n_runs = len({(r["setting"], r["clip"], r["qp"]) for r in rows})
    errs = sum(r["structure_errors"] + r["unexpected_decode_errors"] for r in rows)
    say(f"E3 + A4: {n_runs} runs (clip x setting x QP), {len(rows)} combinations; structure or decode errors: {int(errs)}")
    # --- table per setting x group x pattern x arm x marking ------------------------------------------------------
    T = []
    key = lambda r: (r["setting"], r["group"], r["pattern"], r["arm"], r["marking"])
    groups = {}
    for r in rows:
        groups.setdefault(key(r), []).append(r)
    for k in sorted(groups):
        g = groups[k]
        ev = sum(r["loss_events"] for r in g)
        T.append(dict(setting=k[0], group=k[1], pattern=k[2], arm=k[3], marking=k[4], runs=len(g),
                      kbps=round(st.mean(r["kbps"] for r in g), 1), psnr_shown=round(st.mean(r["psnr_shown"] for r in g), 3),
                      frozen_pct=round(100 * sum(r["frames_frozen"] for r in g) / sum(r["frames"] for r in g), 2),
                      lost_pct=round(100 * sum(r["frames_lost"] for r in g) / sum(r["frames"] for r in g), 2),
                      events=int(ev), mean_freeze=round(sum(r["frames_frozen"] for r in g) / ev, 2) if ev else "",
                      longest_freeze=int(max(r["longest_freeze"] for r in g)),
                      i_frames=round(st.mean(r["i_frames"] for r in g), 2), recovery_frames=round(st.mean(r["recovery_frames"] for r in g), 2),
                      marks=round(st.mean(r["marks"] for r in g), 2),
                      recovery_bytes=round(st.mean([r["recovery_bytes_mean"] for r in g if r["recovery_frames"] > 0] or [float("nan")]), 0),
                      i_bytes=round(st.mean([r["i_bytes_mean"] for r in g if r["i_frames"] > 0] or [float("nan")]), 0)))
    with open(f"{R}/table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(T[0])); w.writeheader(); w.writerows(T)
    say("\nPer setting, clip group, loss pattern and arm (fixed marking unless noted):")
    say(f"{'setting':<11} {'group':<5} {'loss':<6} {'arm':<5} {'mark':<8} {'kbps':>7} {'shown dB':>9} {'lost %':>7} {'frozen %':>9} {'events':>7} {'freeze':>7} {'longest':>8} {'I/run':>6} {'R/run':>6} {'R bytes':>8} {'I bytes':>8}")
    for t in T:
        say(f"{t['setting']:<11} {t['group']:<5} {t['pattern']:<6} {t['arm']:<5} {t['marking']:<8} {t['kbps']:>7} {t['psnr_shown']:>9} {t['lost_pct']:>7} "
            f"{t['frozen_pct']:>9} {t['events']:>7} {str(t['mean_freeze']):>7} {t['longest_freeze']:>8} {t['i_frames']:>6} {t['recovery_frames']:>6} "
            f"{t['recovery_bytes']:>8} {t['i_bytes']:>8}")
    # --- paired differences ---------------------------------------------------------------------------------------
    idx = {(r["setting"], r["clip"], r["qp"], r["pattern"], r["arm"], r["marking"]): r for r in rows}
    P = []

    def paired(setting, group, pattern, a, b, label):
        ka = [k for k in idx if k[0] == setting and k[3] == pattern and k[4:] == a and (group == "all" or idx[k]["group"] == group)]
        d = {m: [] for m in ("psnr_shown", "kbps", "frames_frozen")}
        for k in ka:
            kb = k[:4] + b
            if kb in idx:
                for m in d:
                    d[m].append(idx[k][m] - idx[kb][m])
        if not d["kbps"]:
            return
        out = dict(setting=setting, group=group, pattern=pattern, comparison=label, pairs=len(d["kbps"]))
        for m in d:
            mu, h = ci(d[m]); out[f"d_{m}"] = round(mu, 3); out[f"ci_{m}"] = round(h, 3)
        P.append(out)

    for s in sorted({r["setting"] for r in rows}):
        for g in ("all", "vcd", "call"):
            for p in ("p1", "p5", "burst"):
                paired(s, g, p, ("ltr", "fixed"), ("wait", "fixed"), "ltr - wait")
                paired(s, g, p, ("idr", "fixed"), ("wait", "fixed"), "idr - wait")
                paired(s, g, p, ("ltr", "fixed"), ("idr", "fixed"), "ltr - idr")
            for p in ("none", "p1", "p5", "burst"):
                paired(s, g, p, ("ltr", "adaptive"), ("ltr", "fixed"), "A4 adaptive - fixed (ltr arm)")
    if P:
        with open(f"{R}/paired.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(P[0])); w.writeheader(); w.writerows(P)
        say("\nPaired differences over clip x QP (mean ± 95 % CI): shown PSNR-Y (dB), kbps, frozen frames per 300")
        for x in P:
            say(f"{x['setting']:<11} {x['group']:<5} {x['pattern']:<6} {x['comparison']:<30} n={x['pairs']:<3} "
                f"dPSNR {x['d_psnr_shown']:+.3f} ± {x['ci_psnr_shown']:.3f}   dkbps {x['d_kbps']:+.2f} ± {x['ci_kbps']:.2f}   "
                f"dfrozen {x['d_frames_frozen']:+.1f} ± {x['ci_frames_frozen']:.1f}")
    open(f"{R}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== written: {R}/table.csv, paired.csv, summary.txt")


if __name__ == "__main__":
    main()
