#!/usr/bin/env python3
"""Step 5 + A2 analysis: failures, determinism, drift by position, BD-rate per encoder->decoder pair, drift bounds.

usage: drift_tables.py   (reads ~/Downloads/duplexnvc-baseline/phase2/5/r.csv and frames/, writes phase2/5/results/)
Can be run at any time, also while drift_runner.py is still running (uses whatever is finished).
Outputs (results/)
  coverage.csv   jobs done per setting x variant; encode / decode failures and short decodes per pair
  det.csv        determinism: same decode twice on the same processor (main, first clip); encoder identical to exp. 10
  drift.csv      main: drift per setting x pair (worst frame, mean, bit-identical share) and by frames after the I-frame
  bd.csv         BD-rate (coded PSNR-Y) of every setting x variant x pair vs the same setting's main NE->NE,
                 and the change vs the same variant's NE->NE (= cost of the mismatch alone); H4 verdict (< 1 point)
  a2.csv         per setting x variant: compression cost of the bound (NE->NE vs main NE->NE) and worst drift
  fig_drift.png/pdf, fig_a2.png/pdf, summary.txt
"""
import csv, glob, math, os, statistics as st
import numpy as np
from scipy.interpolate import PchipInterpolator

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = os.environ.get("S5OUT", f"{WORK}/phase2/5")
RES = f"{OUT}/results"
UNITS = ["npu", "gpu", "cpu"]
U = {"npu": "NE", "gpu": "GPU", "cpu": "CPU"}
QPS = [16, 24, 32, 40]
SETTINGS = ["mlvc_360p", "mlvcs_720p", "mlvcs_540p", "mlvc_540p", "mlvc_720p", "mlvcs_1080p", "mlvc_1080p"]
VARIANTS = ["main", "i32", "l32", "i16", "l16"]
BOUND = {"main": 64, "i32": 32, "l32": 32, "i16": 16, "l16": 16}
VNAME = {"main": "default structure (I-frame every 64)", "i32": "I-frame every 32", "l32": "LTR recovery every 32",
         "i16": "I-frame every 16", "l16": "LTR recovery every 16"}
PAIRS = [(e, d) for e in UNITS for d in UNITS]
BINS = [(0, 0), (1, 15), (16, 31), (32, 47), (48, 63)]


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def label(s):
    m, r = s.split("_")
    return f"{'Full MLVC' if m == 'mlvc' else 'MLVC-S'} {r}"


def pn(e, d):
    return f"{U[e]}>{U[d]}"


def db_of_mse(m):
    return 100.0 if m <= 0 else min(100.0, 10 * math.log10(255.0 ** 2 / m))


def mse_of_db(x):
    return 0.0 if x >= 100 else 255.0 ** 2 / 10 ** (x / 10)


def wcsv(name, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(f"{RES}/{name}", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval="")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else ("" if v is None else v)) for k, v in r.items()})


def bd_rate(ref, test):
    """BD-rate (%) of test vs ref, PCHIP on log rate, overlap only; None if < 4 points or no overlap."""
    if len(ref) < 4 or len(test) < 4:
        return None
    r = sorted((q, math.log10(k)) for k, q in ref)
    t = sorted((q, math.log10(k)) for k, q in test)
    lo, hi = max(r[0][0], t[0][0]), min(r[-1][0], t[-1][0])
    if hi <= lo:
        return None
    fr, ft = PchipInterpolator(*zip(*r)), PchipInterpolator(*zip(*t))
    qq = np.linspace(lo, hi, 1000)
    return (10 ** (np.trapezoid(ft(qq) - fr(qq), qq) / (hi - lo)) - 1) * 100


def main():
    os.makedirs(RES, exist_ok=True)
    R = list(csv.DictReader(open(f"{OUT}/r.csv")))
    for r in R:
        r["qp"] = int(r["qp"])
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    say("STEP 5 + A2: correctness of every encoder->decoder pair and drift bounds")
    sets = [s for s in SETTINGS if any(r["setting"] == s for r in R)]

    # ---------------- coverage and failures ----------------
    cov = []
    say("\n== coverage and failures (jobs = clip x QP; each job has 9 pairs)")
    for s in sets:
        for v in VARIANTS:
            g = [r for r in R if r["setting"] == s and r["variant"] == v]
            if not g:
                continue
            jobs = len({(r["clip"], r["qp"]) for r in g})
            row = dict(setting=s, variant=v, jobs=jobs)
            msgs = []
            for e, d in PAIRS:
                p = [r for r in g if r["enc"] == e and r["dec"] == d]
                ef = sum(r["enc_ok"] != "1" for r in p)
                df = sum(r["enc_ok"] == "1" and r["dec_ok"] != "1" for r in p)
                sh = sum(r["dec_ok"] == "1" and int(r["frames"]) < int(r["src_frames"]) for r in p)
                row[f"{pn(e, d)}_enc_fail"], row[f"{pn(e, d)}_dec_fail"], row[f"{pn(e, d)}_short"] = ef, df, sh
                if ef or df or sh:
                    msgs.append(f"{pn(e, d)}: enc fail {ef}, dec fail {df}, short {sh}")
            cov.append(row)
            say(f"   {label(s):<16} {v:<5} {jobs:3d} jobs  " + ("; ".join(msgs) if msgs else "no failures, no short decodes"))
    wcsv("coverage.csv", cov)

    # ---------------- determinism ----------------
    det = []
    say("\n== determinism (main, first clip, 4 QPs): same bitstream decoded twice on the same processor")
    for s in sets:
        g = [r for r in R if r["setting"] == s and r["variant"] == "main"]
        row = dict(setting=s)
        txt = []
        for e, d in PAIRS:
            x = [r["det"] for r in g if r["enc"] == e and r["dec"] == d and r["det"] != ""]
            row[pn(e, d)] = f"{x.count('1')}/{len(x)}" if x else ""
            if x:
                txt.append(f"{pn(e, d)} {x.count('1')}/{len(x)}")
        for e in UNITS:
            x = [r["same_as_4b"] for r in g if r["enc"] == e and r["dec"] == e and r["same_as_4b"] != ""]
            row[f"enc_{U[e]}_same_as_exp10"] = f"{x.count('1')}/{len(x)}" if x else ""
        det.append(row)
        same10 = "; ".join(f"{U[e]} encoder identical to exp. 10: {row[f'enc_{U[e]}_same_as_exp10']}"
                           for e in UNITS if row[f"enc_{U[e]}_same_as_exp10"])
        say(f"   {label(s):<16} " + (", ".join(txt) if txt else "-") + (f"   [{same10}]" if same10 else ""))
    wcsv("det.csv", det)

    # ---------------- drift (main) ----------------
    dr = []
    say("\n== drift = PSNR-Y of the decode against the decode on the encoder's own processor (main)")
    say("   worst frame dB / mean dB (MSE-averaged) / bit-identical frames; then mean dB by frames after the I-frame")
    say("   " + f"{'':<16} {'pair':<8} {'worst':>6} {'mean':>6} {'ident.':>7}  " + "  ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in BINS))
    curves = {}
    for s in sets:
        files = glob.glob(f"{OUT}/frames/{s}/main/*.csv")
        acc = {(e, d): [[] for _ in range(64)] for e, d in PAIRS if e != d}
        for fp in files:
            rows = list(csv.DictReader(open(fp)))
            for e, d in acc:
                col = f"drift_{e}_{d}"
                if rows and col in rows[0]:
                    for r in rows:
                        x = f(r[col])
                        if x is not None:
                            acc[(e, d)][int(r["i"]) % 64].append(mse_of_db(x))
        for e, d in acc:
            g = [r for r in R if r["setting"] == s and r["variant"] == "main" and r["enc"] == e and r["dec"] == d
                 and r["dec_ok"] == "1" and r["drift_db"] != ""]
            if not g:
                continue
            worst = min(float(r["drift_min_db"]) for r in g)
            mean = db_of_mse(st.mean(mse_of_db(float(r["drift_db"])) for r in g))
            ident = sum(int(r["identical_frames"]) for r in g) / max(1, sum(int(r["frames"]) for r in g)) * 100
            pos = [db_of_mse(st.mean(acc[(e, d)][i])) if acc[(e, d)][i] else None for i in range(64)]
            curves[(s, e, d)] = pos
            binv = []
            for a, b in BINS:
                v = [x for i in range(a, b + 1) for x in acc[(e, d)][i]]
                binv.append(db_of_mse(st.mean(v)) if v else None)
            row = dict(setting=s, pair=pn(e, d), jobs=len(g), worst_db=worst, mean_db=mean, identical_pct=ident,
                       **{f"mean_db_{a}-{b}": x for (a, b), x in zip(BINS, binv)})
            dr.append(row)
            say(f"   {label(s):<16} {pn(e, d):<8} {worst:6.1f} {mean:6.1f} {ident:6.1f}%  "
                + "  ".join("  -  " if x is None else f"{x:5.1f}" for x in binv))
    wcsv("drift.csv", dr)

    # ---------------- BD-rate per pair ----------------
    def curve(s, v, e, d):
        pts = []
        for q in QPS:
            g = [r for r in R if r["setting"] == s and r["variant"] == v and r["enc"] == e and r["dec"] == d
                 and r["qp"] == q and r["dec_ok"] == "1" and r["psnr_y"] != ""]
            if g:
                pts.append((st.mean(float(r["kbps"]) for r in g), st.mean(float(r["psnr_y"]) for r in g)))
        return pts

    bdr = []
    for s in sets:
        ref = curve(s, "main", "npu", "npu")
        for v in VARIANTS:
            own = curve(s, v, "npu", "npu")
            for e, d in PAIRS:
                c = curve(s, v, e, d)
                a, b = bd_rate(ref, c), bd_rate(own, c)
                bdr.append(dict(setting=s, variant=v, pair=pn(e, d), points=len(c), bd_vs_main_NE_NE=a,
                                bd_vs_same_variant_NE_NE=b,
                                h4_pass="" if b is None else ("yes" if abs(b) < 1 else "no")))
    wcsv("bd.csv", bdr)
    say("\n== BD-rate (coded PSNR-Y) of each pair vs NE>NE of the same setting, main structure (H4: |change| < 1 point)")
    say("   " + f"{'':<16}" + "".join(f"{pn(e, d):>9}" for e, d in PAIRS))
    for s in sets:
        g = {r["pair"]: r for r in bdr if r["setting"] == s and r["variant"] == "main"}
        say(f"   {label(s):<16}" + "".join(
            f"{'-':>9}" if g.get(pn(e, d), {}).get("bd_vs_same_variant_NE_NE") is None
            else f"{g[pn(e, d)]['bd_vs_same_variant_NE_NE']:+8.2f}%" for e, d in PAIRS))
    fails = [r for r in bdr if r["variant"] == "main" and r["h4_pass"] == "no"]
    say(f"   H4 fails (|change| >= 1 point): " + (", ".join(f"{label(r['setting'])} {r['pair']}" for r in fails) or "none"))

    # ---------------- A2 ----------------
    a2 = []
    say("\n== A2: drift bounds. Cost = BD-rate of NE>NE vs the main structure; worst drift over the 6 mismatched pairs;")
    say("   worst mismatch BD-rate = largest BD-rate of a mismatched pair vs the main NE>NE")
    for s in sets:
        for v in VARIANTS:
            g = [r for r in R if r["setting"] == s and r["variant"] == v and r["enc"] != r["dec"]
                 and r["dec_ok"] == "1" and r["drift_min_db"] != ""]
            if not g:
                continue
            cost = next((r["bd_vs_main_NE_NE"] for r in bdr if r["setting"] == s and r["variant"] == v
                         and r["pair"] == "NE>NE"), None)
            worst = min(float(r["drift_min_db"]) for r in g)
            wpair = min(g, key=lambda r: float(r["drift_min_db"]))
            perpair = {pn(e, d): min((float(r["drift_min_db"]) for r in g if r["enc"] == e and r["dec"] == d),
                                     default=None) for e, d in PAIRS if e != d}
            bdm = [r["bd_vs_main_NE_NE"] for r in bdr if r["setting"] == s and r["variant"] == v
                   and r["pair"] != "NE>NE" and r["pair"].split(">")[0] != r["pair"].split(">")[1]
                   and r["bd_vs_main_NE_NE"] is not None]
            a2.append(dict(setting=s, variant=v, bound_frames=BOUND[v], cost_bd_pct=cost, worst_drift_db=worst,
                           worst_pair=pn(wpair["enc"], wpair["dec"]),
                           worst_mismatch_bd_pct=max(bdm) if bdm else None,
                           **{f"worst_{k}": x for k, x in perpair.items()}))
            say(f"   {label(s):<16} {VNAME[v]:<32} cost {'-' if cost is None else f'{cost:+6.2f} %'}  "
                f"worst drift {worst:5.1f} dB ({pn(wpair['enc'], wpair['dec'])})  "
                f"worst mismatch BD {'-' if not bdm else f'{max(bdm):+6.2f} %'}")
    wcsv("a2.csv", a2)
    figures(sets, curves, a2)
    open(f"{RES}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== results in {RES}")


def figures(sets, curves, a2):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except Exception as ex:
        print("matplotlib unavailable, figures skipped:", ex)
        return
    INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3de"
    COL = {"npu": INK2, "gpu": "#2a78d6", "cpu": "#eb6834"}     # colour = decoder
    LS = {"npu": "-", "gpu": "--", "cpu": ":"}                   # line style = encoder
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
    if curves:
        fig, ax = plt.subplots(2, 4, figsize=(13, 6.4), sharey=True)
        for a, s in zip(ax.flat, sets):
            for e in UNITS:
                for d in UNITS:
                    y = curves.get((s, e, d))
                    if y:
                        a.plot(range(64), [100 if v is None else min(v, 70) for v in y], color=COL[d], ls=LS[e], lw=1.4)
            a.set_title(label(s), fontsize=9, color=INK); a.set_xlabel("frames after the I-frame")
            a.grid(True, color=GRID, lw=0.6); a.set_axisbelow(True); a.set_ylim(30, 72)
        for a in ax.flat[len(sets):]:
            a.axis("off")
        ax[0, 0].set_ylabel("drift: PSNR-Y vs encoder's own decode (dB)"); ax[1, 0].set_ylabel("drift (dB)")
        h = [Line2D([], [], color=COL[d], lw=2, label=f"decoder {U[d]}") for d in UNITS]
        h += [Line2D([], [], color=INK2, ls=LS[e], lw=1.4, label=f"encoder {U[e]}") for e in UNITS]
        fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=6, frameon=False, fontsize=8)
        fig.suptitle("Step 5: drift of every mismatched encoder>decoder pair through the I-frame period "
                     "(mean of 20 clips x 4 QPs; capped at 70 dB)", y=0.995, fontsize=9.5)
        fig.tight_layout(rect=(0, 0, 1, 0.90))
        for x in ("png", "pdf"):
            fig.savefig(f"{RES}/fig_drift.{x}", dpi=200)
        plt.close(fig)
    if a2:
        MK = {"main": "o", "i32": "s", "i16": "s", "l32": "^", "l16": "^"}
        CV = {"main": INK2, "i32": "#2a78d6", "i16": "#2a78d6", "l32": "#eb6834", "l16": "#eb6834"}
        fig, ax = plt.subplots(2, 4, figsize=(13, 6.4))
        for a, s in zip(ax.flat, sets):
            g = [r for r in a2 if r["setting"] == s and r["cost_bd_pct"] is not None]
            for r in g:
                v = r["variant"]
                a.scatter(r["cost_bd_pct"], r["worst_drift_db"], marker=MK[v], s=55, color=CV[v],
                          facecolor=CV[v] if BOUND[v] != 16 else "white", lw=1.5, zorder=3)
                a.annotate(v, (r["cost_bd_pct"], r["worst_drift_db"]), xytext=(5, 3), textcoords="offset points",
                           fontsize=7.5, color=INK)
            a.set_title(label(s), fontsize=9); a.set_xlabel("compression cost: BD-rate vs the default structure (%)")
            a.grid(True, color=GRID, lw=0.6); a.set_axisbelow(True)
        for a in ax.flat[len(sets):]:
            a.axis("off")
        ax[0, 0].set_ylabel("worst-frame drift, any mismatched pair (dB)"); ax[1, 0].set_ylabel("worst drift (dB)")
        h = [Line2D([], [], ls="", marker="o", color=INK2, label="default (I-frame every 64)"),
             Line2D([], [], ls="", marker="s", color="#2a78d6", label="shorter I-period (filled 32, hollow 16)"),
             Line2D([], [], ls="", marker="^", color="#eb6834", label="LTR recovery (filled 32, hollow 16)")]
        fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=3, frameon=False, fontsize=8)
        fig.suptitle("A2: compression cost vs worst drift of each drift bound", y=0.995, fontsize=9.5)
        fig.tight_layout(rect=(0, 0, 1, 0.90))
        for x in ("png", "pdf"):
            fig.savefig(f"{RES}/fig_a2.{x}", dpi=200)
        plt.close(fig)


if __name__ == "__main__":
    main()
