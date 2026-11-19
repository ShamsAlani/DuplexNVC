#!/usr/bin/env python3
"""Step 4b analysis: rate-distortion per setting, BD-rate, equal-bitrate quality, energy-quality Pareto.

usage: ana.py   (reads ~/Downloads/duplexnvc-baseline/phase2/4b/q.csv, writes phase2/4b/results/)
Inputs
  phase2/4b/q.csv                     this step (one row per configuration x clip x QP)
  phase2/4b/faces.csv                 one row per scored face
  phase2/step4/table_feasible.csv     X3 energy and feasibility (QP 26)
  runs/quality_eval/rd_eval.csv       E6 (360p, VCD YUV input), cross-check only
Outputs (results/)
  rd_mean.csv      mean over clips per configuration x QP
  bd.csv           BD-rate (PCHIP on log rate, overlap only) and BD-quality for the planned comparisons
  eqrate.csv       quality of every configuration at fixed bitrates (interpolated along its curve, no extrapolation)
  pareto.csv       best placement per setting: energy (X3), label, quality at QP 26, Pareto flags
  unit.csv         GPU vs NE encoder: same setting, same clips
  e6check.csv      360p of this step vs E6
  facesize.csv     face PSNR-Y / LPIPS by face height group at QP 26
  fig_rd.png/pdf, fig_pareto.png/pdf, summary.txt
  with phase2/4b/energy/energy_qp.csv (from ./en and es.py) also:
  energy_qp.csv    energy per frame pair per setting (best placement) and QP
  pareto_eqrate.csv  energy and quality of every setting at equal bitrates (both interpolated along the QP curves)
  fig_energy.png/pdf  energy vs QP, energy vs bitrate, Pareto at 287 kbps
"""
import csv, math, os, statistics as st
import numpy as np
from scipy.interpolate import PchipInterpolator

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
OUT = f"{WORK}/phase2/4b"
RES = f"{OUT}/results"
X3 = f"{WORK}/phase2/step4/table_feasible.csv"
ENQ = f"{OUT}/energy/energy_qp.csv"
E6 = f"{WORK}/runs/quality_eval/rd_eval.csv"
QPS = [16, 24, 26, 32, 40]
CFGS = ["mlvc_360p_npu-npu", "mlvc_540p_npu-npu", "mlvc_540p_gpu-npu", "mlvcs_540p_npu-npu",
        "mlvc_720p_npu-npu", "mlvcs_720p_npu-npu", "mlvcs_720p_gpu-npu", "mlvc_1080p_npu-npu", "mlvcs_1080p_npu-npu"]
BSTAR = "mlvc_360p_npu-npu"
MET = ["kbps", "psnr_y", "psnr_yuv", "psnr_y_display", "face_psnr_y", "face_lpips"]
NAME = {"psnr_y": "coded PSNR-Y (dB)", "psnr_yuv": "coded PSNR-YUV (dB)", "psnr_y_display": "display PSNR-Y (dB)",
        "face_psnr_y": "face PSNR-Y (dB)", "face_lpips": "face LPIPS (lower is better)"}
LOWER_BETTER = {"face_lpips"}
B_STAR_MJ = 65.3   # B* (360p NE-NE) energy per frame pair at QP 26 from the B* report, not repeated in X3


def label(c):
    s, pl = c.rsplit("_", 1)
    m, r = s.split("_")
    return f"{'Full MLVC' if m == 'mlvc' else 'MLVC-S'} {r}" + ("" if pl == "npu-npu" else " (GPU enc)")


def f(x):
    try:
        v = float(x)
        return v if not math.isnan(v) else None
    except (TypeError, ValueError):
        return None


def mean(v):
    v = [x for x in v if x is not None]
    return st.mean(v) if v else None


def wcsv(name, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(f"{RES}/{name}", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else ("" if v is None else v)) for k, v in r.items()})


def curve(M, c, m):
    """(kbps, quality) points of the mean curve, sorted by rate."""
    pts = [(M[c][q]["kbps"], M[c][q][m]) for q in QPS if q in M[c] and M[c][q].get(m) is not None]
    return sorted(pts)


def bd(ref, test, lower_better=False):
    """BD-rate (%) of test vs ref at equal quality and BD-quality at equal rate; None if no overlap."""
    if len(ref) < 4 or len(test) < 4:
        return None, None
    sg = -1 if lower_better else 1
    r = sorted((sg * q, math.log10(k)) for k, q in ref); t = sorted((sg * q, math.log10(k)) for k, q in test)
    out = [None, None]
    lo, hi = max(r[0][0], t[0][0]), min(r[-1][0], t[-1][0])
    if hi > lo:
        fr = PchipInterpolator(*zip(*r)); ft = PchipInterpolator(*zip(*t))
        qq = np.linspace(lo, hi, 1000)
        out[0] = (10 ** (np.trapezoid(ft(qq) - fr(qq), qq) / (hi - lo)) - 1) * 100
    r2 = sorted((math.log10(k), sg * q) for k, q in ref); t2 = sorted((math.log10(k), sg * q) for k, q in test)
    lo, hi = max(r2[0][0], t2[0][0]), min(r2[-1][0], t2[-1][0])
    if hi > lo:
        fr = PchipInterpolator(*zip(*r2)); ft = PchipInterpolator(*zip(*t2))
        xx = np.linspace(lo, hi, 1000)
        out[1] = sg * float(np.trapezoid(ft(xx) - fr(xx), xx) / (hi - lo))
    return out[0], out[1]


def at_rate(pts, kbps):
    if len(pts) < 2 or not (pts[0][0] <= kbps <= pts[-1][0]):
        return None
    return float(PchipInterpolator([math.log10(k) for k, _ in pts], [q for _, q in pts])(math.log10(kbps)))


def main():
    os.makedirs(RES, exist_ok=True)
    rows = list(csv.DictReader(open(f"{OUT}/q.csv")))
    for r in rows:
        r["qp"] = int(r["qp"])
        for m in MET:
            r[m] = f(r[m])
    lines = []
    say = lambda s="": (print(s), lines.append(s))
    say("STEP 4b: quality per setting (20 evaluation clips, QP 16/24/26/32/40)")
    # ---------- coverage ----------
    say("\n== coverage (expect 20 clips per configuration and QP)")
    for c in CFGS:
        n = [sum(1 for r in rows if r["cfg"] == c and r["qp"] == q) for q in QPS]
        short = sum(1 for r in rows if r["cfg"] == c and int(r["decoded_frames"]) < int(r["source_frames"]))
        unit = sorted({r["enc_resolved"] for r in rows if r["cfg"] == c})
        say(f"   {label(c):<26} clips per QP {n}  short decodes {short}  encoder resolved {unit}")
    # ---------- means ----------
    M, rd = {}, []
    for c in CFGS:
        M[c] = {}
        for q in QPS:
            g = [r for r in rows if r["cfg"] == c and r["qp"] == q]
            if not g:
                continue
            M[c][q] = {m: mean(r[m] for r in g) for m in MET}
            M[c][q]["n"] = len(g)
            rd.append(dict(cfg=c, setting=label(c), qp=q, clips=len(g), **{m: M[c][q][m] for m in MET}))
    wcsv("rd_mean.csv", rd, ["cfg", "setting", "qp", "clips"] + MET)
    say("\n== mean over clips (kbps / coded Y / display Y / face Y / face LPIPS)")
    for c in CFGS:
        say(f"   {label(c)}")
        for q in QPS:
            if q in M[c]:
                v = M[c][q]
                fmt = lambda x, p=2: "  -  " if x is None else f"{x:.{p}f}"
                say(f"      QP {q:2d}: {fmt(v['kbps'], 1):>7} kbps  {fmt(v['psnr_y'])}  {fmt(v['psnr_y_display'])}"
                    f"  {fmt(v['face_psnr_y'])}  {fmt(v['face_lpips'], 3)}")
    # ---------- BD-rate ----------
    pairs = [(BSTAR, c, "vs B*") for c in CFGS if c != BSTAR]
    pairs += [(f"mlvc_{r}_npu-npu", f"mlvcs_{r}_npu-npu", "MLVC-S vs full, same res") for r in ("540p", "720p", "1080p")]
    pairs += [("mlvc_540p_npu-npu", "mlvc_540p_gpu-npu", "GPU vs NE encoder"),
              ("mlvcs_720p_npu-npu", "mlvcs_720p_gpu-npu", "GPU vs NE encoder")]
    bdr = []
    for ref, test, why in pairs:
        same_res = ref.split("_")[1] == test.split("_")[1]
        for m in ["psnr_y_display", "face_psnr_y", "face_lpips"] + (["psnr_y", "psnr_yuv"] if same_res else []):
            a, b = bd(curve(M, ref, m), curve(M, test, m), m in LOWER_BETTER)
            bdr.append(dict(ref=ref, test=test, comparison=why, metric=m, bd_rate_pct=a, bd_quality=b))
    wcsv("bd.csv", bdr)
    say("\n== BD-rate vs B* (negative = fewer bits for the same quality; '-' = curves do not overlap)")
    say(f"   {'':<26} {'display Y':>10} {'face Y':>10} {'face LPIPS':>11}   BD-quality: display dB / face dB / LPIPS")
    for c in CFGS[1:]:
        g = {r["metric"]: r for r in bdr if r["ref"] == BSTAR and r["test"] == c}
        p = lambda m: "      -   " if g[m]["bd_rate_pct"] is None else f"{g[m]['bd_rate_pct']:+9.1f}%"
        qd = lambda m, n=2: "-" if g[m]["bd_quality"] is None else f"{g[m]['bd_quality']:+.{n}f}"
        say(f"   {label(c):<26} {p('psnr_y_display'):>10} {p('face_psnr_y'):>10} {p('face_lpips'):>11}"
            f"   {qd('psnr_y_display')} / {qd('face_psnr_y')} / {qd('face_lpips', 3)}")
    # ---------- equal bitrate ----------
    targets = [100, 150, 200, 287, 400, 600, 800, 1000, 1500, 2000]
    eq = []
    for c in CFGS:
        for k in targets:
            eq.append(dict(cfg=c, setting=label(c), kbps=k,
                           **{m: at_rate(curve(M, c, m), k) for m in MET[1:]}))
    wcsv("eqrate.csv", eq)
    say("\n== at equal bitrate (interpolated along each curve, blank outside its range): display Y / face LPIPS")
    say("   " + f"{'':<26}" + "".join(f"{k:>14}" for k in targets[:7]))
    for c in CFGS:
        cell = lambda k: next(e for e in eq if e["cfg"] == c and e["kbps"] == k)
        txt = "".join(f"{'-':>14}" if cell(k)["psnr_y_display"] is None else
                      f"{cell(k)['psnr_y_display']:>7.2f}/{cell(k)['face_lpips']:.3f}" for k in targets[:7])
        say(f"   {label(c):<26}{txt}")
    # ---------- Pareto (energy from X3) ----------
    x3 = list(csv.DictReader(open(X3))) if os.path.exists(X3) else []
    rank = {"30 fps": 0, "15 fps only": 1, "infeasible": 2}
    par = []
    for s in ["mlvc_360p", "mlvc_540p", "mlvc_720p", "mlvc_1080p", "mlvcs_540p", "mlvcs_720p", "mlvcs_1080p"]:
        m_, r_ = s.split("_")
        if s == "mlvc_360p":
            best = dict(enc="npu", dec="npu", feasible="30 fps", mJ_combined=B_STAR_MJ)
        else:
            g = [dict(x, feasible=x.get("feasible") or x.get("label", ""),
                      mJ_combined=x.get("mJ_combined") or x.get("mJ_per_pair"))
                 for x in x3 if x["model"] == m_ and x["res"] == r_ and f(x.get("mJ_combined") or x.get("mJ_per_pair"))]
            if not g:
                continue
            best = min(g, key=lambda x: (rank.get(x["feasible"], 3), float(x["mJ_combined"])))
        c = f"{s}_{best['enc']}-{best['dec']}"
        qc = c if c in M and 26 in M[c] else f"{s}_npu-npu"
        v = M.get(qc, {}).get(26)
        if not v:
            continue
        par.append(dict(setting=s, placement=f"{best['enc']}-{best['dec']}", label=best["feasible"],
                        mJ=float(best["mJ_combined"]), quality_cfg=qc, kbps=v["kbps"], psnr_y=v["psnr_y"],
                        psnr_y_display=v["psnr_y_display"], face_psnr_y=v["face_psnr_y"], face_lpips=v["face_lpips"]))
    for p in par:
        dom = lambda o, key, lower: o is not p and o["mJ"] <= p["mJ"] and (
            (o[key] <= p[key]) if lower else (o[key] >= p[key])) and (o["mJ"] < p["mJ"] or o[key] != p[key])
        p["pareto_lpips_all"] = not any(dom(o, "face_lpips", True) for o in par)
        p["pareto_lpips_30fps"] = p["label"] == "30 fps" and not any(
            dom(o, "face_lpips", True) for o in par if o["label"] == "30 fps")
        p["pareto_display_all"] = not any(dom(o, "psnr_y_display", False) for o in par)
    wcsv("pareto.csv", par)
    say("\n== energy vs quality at QP 26 (best placement per setting; energy = X3 mJ per frame pair, idle subtracted)")
    for p in sorted(par, key=lambda x: x["mJ"]):
        say(f"   {p['setting']:<12} {p['placement']:<8} {p['label']:<12} {p['mJ']:7.1f} mJ  {p['kbps']:7.1f} kbps"
            f"  display {p['psnr_y_display']:.2f}  face {p['face_psnr_y']:.2f} / {p['face_lpips']:.3f}"
            f"  Pareto(LPIPS) all={'Y' if p['pareto_lpips_all'] else '-'} 30fps={'Y' if p['pareto_lpips_30fps'] else '-'}")
    # ---------- the two questions ----------
    P = {p["setting"]: p for p in par}
    say("\n== Q1: MLVC-S 540p (NE-NE) vs B* (full MLVC 360p NE-NE) at screen size")
    if "mlvcs_540p" in P and "mlvc_360p" in P:
        a, b = P["mlvc_360p"], P["mlvcs_540p"]
        say(f"   QP 26: B* {a['kbps']:.0f} kbps, display {a['psnr_y_display']:.2f}, face {a['face_psnr_y']:.2f} dB / "
            f"LPIPS {a['face_lpips']:.3f}, {a['mJ']:.1f} mJ")
        say(f"          S540 {b['kbps']:.0f} kbps, display {b['psnr_y_display']:.2f}, face {b['face_psnr_y']:.2f} dB / "
            f"LPIPS {b['face_lpips']:.3f}, {b['mJ']:.1f} mJ")
        g = {r["metric"]: r for r in bdr if r["ref"] == BSTAR and r["test"] == "mlvcs_540p_npu-npu"}
        for m in ("psnr_y_display", "face_psnr_y", "face_lpips"):
            br, bq = g[m]["bd_rate_pct"], g[m]["bd_quality"]
            say(f"   BD vs B* on {NAME[m]}: rate {'-' if br is None else f'{br:+.1f} %'}, "
                f"quality {'-' if bq is None else f'{bq:+.3f}'}")
        for k in (200, 287, 400):
            e1 = next(e for e in eq if e["cfg"] == BSTAR and e["kbps"] == k)
            e2 = next(e for e in eq if e["cfg"] == "mlvcs_540p_npu-npu" and e["kbps"] == k)
            if e1["psnr_y_display"] is not None and e2["psnr_y_display"] is not None:
                say(f"   at {k} kbps: display {e1['psnr_y_display']:.2f} -> {e2['psnr_y_display']:.2f} dB, "
                    f"face LPIPS {e1['face_lpips']:.3f} -> {e2['face_lpips']:.3f}")
    say("\n== Q2: full MLVC 540p (best placement) vs MLVC-S 540p and vs B*")
    if "mlvc_540p" in P:
        f5 = P["mlvc_540p"]
        for ref in ("mlvcs_540p", "mlvc_360p"):
            if ref in P:
                r = P[ref]
                say(f"   vs {ref}: energy x{f5['mJ'] / r['mJ']:.1f} ({r['mJ']:.1f} -> {f5['mJ']:.1f} mJ), "
                    f"kbps x{f5['kbps'] / r['kbps']:.2f}, display {f5['psnr_y_display'] - r['psnr_y_display']:+.2f} dB, "
                    f"face {f5['face_psnr_y'] - r['face_psnr_y']:+.2f} dB, LPIPS {f5['face_lpips'] - r['face_lpips']:+.3f}")
        g = {r["metric"]: r for r in bdr if r["ref"] == "mlvc_540p_npu-npu" and r["test"] == "mlvcs_540p_npu-npu"}
        for m in ("psnr_y_display", "face_lpips"):
            if m in g and g[m]["bd_rate_pct"] is not None:
                say(f"   BD-rate MLVC-S 540p vs full 540p on {NAME[m]}: {g[m]['bd_rate_pct']:+.1f} %")
    # ---------- GPU vs NE encoder ----------
    say("\n== encoder on GPU vs NE (same setting, same clips, decoder on NE)")
    un = []
    for s in ("mlvc_540p", "mlvcs_720p"):
        for q in QPS:
            a = {r["clip"]: r for r in rows if r["cfg"] == f"{s}_npu-npu" and r["qp"] == q}
            b = {r["clip"]: r for r in rows if r["cfg"] == f"{s}_gpu-npu" and r["qp"] == q}
            cl = sorted(set(a) & set(b))
            if not cl:
                continue
            dy = [b[c]["psnr_y"] - a[c]["psnr_y"] for c in cl]
            dk = [(b[c]["kbps"] / a[c]["kbps"] - 1) * 100 for c in cl]
            un.append(dict(setting=s, qp=q, clips=len(cl), d_psnr_y_mean=st.mean(dy), d_psnr_y_maxabs=max(map(abs, dy)),
                           d_kbps_pct_mean=st.mean(dk), d_kbps_pct_maxabs=max(map(abs, dk))))
            say(f"   {s} QP {q}: coded PSNR-Y {st.mean(dy):+.3f} dB (max |{max(map(abs, dy)):.3f}|), "
                f"bitrate {st.mean(dk):+.2f} % (max |{max(map(abs, dk)):.2f}|), {len(cl)} clips")
    wcsv("unit.csv", un)
    # ---------- E6 cross-check ----------
    if os.path.exists(E6):
        e6 = list(csv.DictReader(open(E6)))
        say("\n== 360p cross-check: this step (Lanczos from 1080p MP4) minus E6 (VCD 360p YUV), same 20 clips")
        ck = []
        for q in (16, 24, 32, 40):
            a = {r["clip"]: r for r in e6 if int(r["qp"]) == q}
            b = {r["clip"]: r for r in rows if r["cfg"] == BSTAR and r["qp"] == q}
            cl = sorted(set(a) & set(b))
            if not cl:
                continue
            d = {m: st.mean(b[c][m] - float(a[c][m]) for c in cl if b[c][m] is not None and f(a[c][m]) is not None)
                 for m in MET}
            ck.append(dict(qp=q, clips=len(cl), **{f"d_{m}": d[m] for m in MET}))
            say(f"   QP {q}: kbps {d['kbps']:+.1f}, coded Y {d['psnr_y']:+.3f}, display Y {d['psnr_y_display']:+.3f}, "
                f"face Y {d['face_psnr_y']:+.3f}, LPIPS {d['face_lpips']:+.4f}  ({len(cl)} clips)")
        wcsv("e6check.csv", ck)
    # ---------- face size groups ----------
    fp = f"{OUT}/faces.csv"
    if os.path.exists(fp):
        fr = [r for r in csv.DictReader(open(fp)) if int(r["qp"]) == 26]
        grp = [(0, 96), (96, 192), (192, 384), (384, 10_000)]   # display px = <32, 32-63, 64-127, >=128 px at 360p
        fs = []
        for c in CFGS:
            for lo, hi in grp:
                g = [r for r in fr if r["cfg"] == c and lo <= int(r["face_h_display"]) < hi]
                if g:
                    fs.append(dict(cfg=c, face_h_display=f"{lo}-{hi}", faces=len(g),
                                   face_psnr_y=mean(f(r["face_psnr_y"]) for r in g),
                                   face_lpips=mean(f(r["face_lpips"]) for r in g)))
        wcsv("facesize.csv", fs)
    eq = energy_eq(M, par, say)
    figures(M, par)
    if eq:
        figures_energy(M, *eq)
    open(f"{RES}/summary.txt", "w").write("\n".join(lines) + "\n")
    print(f"\n== results in {RES}")


def energy_eq(M, par, say):
    """Energy per QP (./en) -> energy and quality of each setting at equal bitrate, Pareto per target bitrate."""
    if not os.path.exists(ENQ):
        say("\n== energy per QP: not measured yet (./en); equal-bitrate Pareto skipped")
        return None
    en = {}
    for r in csv.DictReader(open(ENQ)):
        if f(r["mJ_combined"]) is not None:
            en.setdefault(r["cfg"], {})[int(r["qp"])] = {k: (f(v) if k not in ("cfg", "setting", "placement") else v)
                                                       for k, v in r.items()}
    lab = {p["setting"]: p["label"] for p in par}
    say("\n== energy per frame pair vs QP (best placement, paced 30 fps, idle subtracted; median of runs)")
    say("   " + f"{'':<22}" + "".join(f"{'QP ' + str(q):>10}" for q in QPS) + "   QP16/QP40")
    for c, g in en.items():
        v = [g[q]["mJ_combined"] if q in g else None for q in QPS]
        ratio = f"{v[0] / v[-1]:.2f}" if v[0] and v[-1] else "-"
        say(f"   {c:<22}" + "".join(f"{x:>10.1f}" if x is not None else f"{'-':>10}" for x in v) + f"   {ratio:>8}")
    targets = [170, 287, 400, 600, 1000]
    out = []
    for c, g in en.items():
        if c not in M:
            continue
        pts = sorted((M[c][q]["kbps"], g[q]["mJ_combined"]) for q in QPS if q in g and q in M[c])
        s_ = c.rsplit("_", 1)[0]
        for k in targets:
            e = at_rate(pts, k)
            if e is None:
                continue
            out.append(dict(cfg=c, setting=s_, label=lab.get(s_, ""), kbps=k, mJ=e,
                            psnr_y_display=at_rate(curve(M, c, "psnr_y_display"), k),
                            face_psnr_y=at_rate(curve(M, c, "face_psnr_y"), k),
                            face_lpips=at_rate(curve(M, c, "face_lpips"), k)))
    for p in out:
        same = [o for o in out if o["kbps"] == p["kbps"]]
        dom = lambda o, key, lower: o is not p and o["mJ"] <= p["mJ"] and (
            (o[key] <= p[key]) if lower else (o[key] >= p[key])) and (o["mJ"] < p["mJ"] or o[key] != p[key])
        p["pareto_lpips_all"] = not any(dom(o, "face_lpips", True) for o in same)
        p["pareto_lpips_30fps"] = p["label"] == "30 fps" and not any(
            dom(o, "face_lpips", True) for o in same if o["label"] == "30 fps")
        p["pareto_display_all"] = not any(dom(o, "psnr_y_display", False) for o in same)
    wcsv("pareto_eqrate.csv", out)
    wcsv("energy_qp.csv", [dict(cfg=c, qp=q, **{k: v for k, v in g[q].items() if k not in ("cfg", "qp")})
                           for c, g in en.items() for q in QPS if q in g])
    say("\n== energy vs quality at EQUAL BITRATE (energy and quality interpolated along each setting's QP curve)")
    for k in targets:
        g = sorted((o for o in out if o["kbps"] == k), key=lambda o: o["mJ"])
        if not g:
            continue
        say(f"   at {k} kbps:")
        for o in g:
            say(f"      {o['setting']:<12} {o['cfg'].rsplit('_', 1)[1]:<8} {o['label']:<12} {o['mJ']:7.1f} mJ"
                f"  display {o['psnr_y_display']:.2f}  face {o['face_psnr_y']:.2f} / {o['face_lpips']:.3f}"
                f"  Pareto(LPIPS) all={'Y' if o['pareto_lpips_all'] else '-'}"
                f" 30fps={'Y' if o['pareto_lpips_30fps'] else '-'}")
    return en, out


def figures_energy(M, en, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except Exception as ex:
        print("matplotlib unavailable, energy figure skipped:", ex)
        return
    INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3de"
    COL = {"360p": INK2, "540p": "#2a78d6", "720p": "#eb6834", "1080p": "#1baf7a"}
    MK = {"30 fps": "o", "15 fps only": "s", "infeasible": "X"}

    def st_(c):
        s, pl = c.rsplit("_", 1)
        m, r = s.split("_")
        return dict(color=COL[r], ls="-" if m == "mlvc" else "--", marker="o" if m == "mlvc" else "s",
                    mfc="white" if pl != "npu-npu" else COL[r], lw=1.6, ms=5, mew=1.4)

    fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))
    a = ax[0, 0]
    for c, g in en.items():
        q = [x for x in QPS if x in g]
        a.plot(q, [g[x]["mJ_combined"] for x in q], **st_(c))
    a.set_yscale("log"); a.set_xlabel("QP"); a.set_ylabel("energy per frame pair (mJ, log)"); a.set_xticks(QPS)
    a = ax[0, 1]
    for c, g in en.items():
        pts = sorted((M[c][q]["kbps"], g[q]["mJ_combined"]) for q in QPS if q in g and c in M and q in M[c])
        if pts:
            a.plot(*zip(*pts), **st_(c))
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("bitrate (kbps, log; 20 evaluation clips)")
    a.set_ylabel("energy per frame pair (mJ, log)")
    for a, m in ((ax[1, 0], "face_lpips"), (ax[1, 1], "psnr_y_display")):
        g = sorted((o for o in out if o["kbps"] == 287), key=lambda o: o["mJ"])
        key = "pareto_lpips_all" if m == "face_lpips" else "pareto_display_all"
        fr = [o for o in g if o[key]]
        if len(fr) > 1:
            a.step([o["mJ"] for o in fr], [o[m] for o in fr], where="post", color=GRID, lw=3, zorder=1)
        for o in g:
            r = o["setting"].split("_")[1]
            a.scatter(o["mJ"], o[m], s=60, marker=MK.get(o["label"], "o"), color=COL[r], edgecolor="white", lw=1.5,
                      zorder=3)
            a.annotate(f"{'F' if o['setting'].startswith('mlvc_') else 'S'} {r} {o['cfg'].rsplit('_', 1)[1]}",
                       (o["mJ"], o[m]), xytext=(6, 4), textcoords="offset points", fontsize=7.5, color=INK)
        a.set_xscale("log"); a.set_xlabel("energy per frame pair at 287 kbps (mJ, log)")
        a.set_ylabel(NAME[m] + " at 287 kbps")
    for a in ax.flat:
        a.grid(True, which="both", color=GRID, lw=0.6); a.set_axisbelow(True)
    h = [Line2D([], [], color=COL[r], lw=2, label=r) for r in COL]
    h += [Line2D([], [], color=INK2, ls="-", marker="o", label="full MLVC"),
          Line2D([], [], color=INK2, ls="--", marker="s", label="MLVC-S"),
          Line2D([], [], color=INK2, ls="", marker="o", mfc="white", label="encoder on GPU (hollow)")]
    h += [Line2D([], [], ls="", marker=MK[k], color=INK2, label=k) for k in MK]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=5, frameon=False, fontsize=8)
    fig.suptitle("Step 4b: energy per frame pair vs QP and bitrate; Pareto at equal bitrate (287 kbps)", y=0.995,
                 fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    for e in ("png", "pdf"):
        fig.savefig(f"{RES}/fig_energy.{e}", dpi=200)
    plt.close(fig)


def figures(M, par):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except Exception as ex:
        print("matplotlib unavailable, figures skipped:", ex)
        return
    INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3de"
    COL = {"360p": INK2, "540p": "#2a78d6", "720p": "#eb6834", "1080p": "#1baf7a"}   # 360p = B* reference (neutral)
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})

    def style(c):
        s, pl = c.rsplit("_", 1)
        m, r = s.split("_")
        return dict(color=COL[r], ls="-" if m == "mlvc" else "--", marker="o" if m == "mlvc" else "s",
                    mfc="white" if pl != "npu-npu" else COL[r], lw=1.6, ms=5, mew=1.4)

    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    for a, m in zip(ax.flat, ["psnr_y_display", "face_psnr_y", "face_lpips", "psnr_y"]):
        for c in CFGS:
            pts = curve(M, c, m)
            if len(pts) < 2:
                continue
            a.plot(*zip(*pts), **style(c))
        a.set_xscale("log"); a.set_xlabel("bitrate (kbps, log)"); a.set_ylabel(NAME[m])
        a.grid(True, which="both", color=GRID, lw=0.6); a.set_axisbelow(True)
        if m == "psnr_y":
            a.set_title("coded scale (not comparable across resolutions)", fontsize=8, color=INK2)
    h = [Line2D([], [], color=COL[r], lw=2, label=r + (" (B*, full MLVC)" if r == "360p" else "")) for r in COL]
    h += [Line2D([], [], color=INK2, ls="-", marker="o", label="full MLVC"),
          Line2D([], [], color=INK2, ls="--", marker="s", label="MLVC-S"),
          Line2D([], [], color=INK2, ls="", marker="o", mfc="white", label="encoder on GPU (hollow)")]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=7, frameon=False, fontsize=8)
    fig.suptitle("Step 4b: rate-distortion per setting, mean of 20 evaluation clips, QP 16/24/26/32/40", y=0.995,
                 fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    for e in ("png", "pdf"):
        fig.savefig(f"{RES}/fig_rd.{e}", dpi=200)
    plt.close(fig)

    if not par:
        return
    MK = {"30 fps": "o", "15 fps only": "s", "infeasible": "X"}
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    for a, m in zip(ax, ["face_lpips", "psnr_y_display"]):
        lower = m in LOWER_BETTER
        front = sorted((p for p in par if p[f"pareto_{'lpips' if lower else 'display'}_all"]), key=lambda p: p["mJ"])
        if len(front) > 1:
            a.step([p["mJ"] for p in front], [p[m] for p in front], where="post", color=GRID, lw=3, zorder=1)
        for p in par:
            r = p["setting"].split("_")[1]
            mod = p["setting"].split("_")[0]
            a.scatter(p["mJ"], p[m], s=60, marker=MK[p["label"]], color=COL[r], edgecolor="white", lw=1.5, zorder=3)
            a.annotate(f"{'F' if mod == 'mlvc' else 'S'} {r} {p['placement']}", (p["mJ"], p[m]), xytext=(6, 4),
                       textcoords="offset points", fontsize=7.5, color=INK)
        a.set_xscale("log"); a.set_xlabel("energy per frame pair at QP 26 (mJ, log; X3, idle subtracted)")
        a.set_ylabel(NAME[m] + " at QP 26"); a.grid(True, which="both", color=GRID, lw=0.6); a.set_axisbelow(True)
    h = [Line2D([], [], ls="", marker=MK[k], color=INK2, label=k) for k in MK]
    h += [Line2D([], [], color=GRID, lw=3, label="Pareto front (all settings)")]
    fig.legend(handles=h, loc="upper center", ncol=4, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    for e in ("png", "pdf"):
        fig.savefig(f"{RES}/fig_pareto.{e}", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
