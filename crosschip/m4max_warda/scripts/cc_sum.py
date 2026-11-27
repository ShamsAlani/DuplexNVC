"""Cross-chip summary: python3 cc_sum.py <crosschip dir> <tools dir> <repo dir>

Computes every number exactly as the baseline does (analyze_run.py, the same medians and rules as
baseline/common/scripts/sum.py and baseline/09_placement_experiment/scripts/step4_sum.py) and puts it next to
Shams's reference M4 Pro (the CSVs in the repo) and, for the NE-alone times, the MLVC paper's M3 Pro.
Writes <crosschip>/summary/*.csv and summary.txt.
"""
import csv, glob, os, re, statistics as st, sys

CC, TOOLS, REPO = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, TOOLS)
import analyze_run as A

OUT = os.path.join(CC, "summary"); os.makedirs(OUT, exist_ok=True)
BL = os.path.join(REPO, "baseline")
PAIRS = ["mlvc_360p", "mlvc_540p", "mlvc_720p", "mlvc_1080p", "mlvcs_540p", "mlvcs_720p", "mlvcs_1080p"]
M3 = {"mlvc_360p": (129.5, 122.9), "mlvc_540p": (65.7, 62.3), "mlvc_720p": (33.8, 33.1), "mlvc_1080p": (15.6, 15.2),
      "mlvcs_540p": (152.0, 137.6), "mlvcs_720p": (83.8, 73.5), "mlvcs_1080p": (39.5, 34.6)}  # MLVC paper, fps alone
LINES = []


def say(s=""):
    print(s); LINES.append(s)


def summ(run, d):
    try:
        m, fr = A.load(run); return A.direction_summary(m, fr, d)
    except Exception:
        return None


def runs(pattern):
    return sorted(r for r in glob.glob(pattern) if os.path.isdir(r) and os.path.exists(os.path.join(r, "frames.csv")))


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def ratio(a, b):
    return a / b if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def rd(v, p=2):
    return round(v, p) if isinstance(v, float) else v


def read_csv(path):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def write(name, rows):
    if not rows: return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: rd(v, 3) for k, v in r.items()})


def fmt(v, w=8, p=2):
    return f"{v:{w}.{p}f}" if isinstance(v, (int, float)) else f"{'-':>{w}s}"


def energy(pattern, idle_pm):  # same as step4_sum.energy
    idle = A.parse_pm(idle_pm) if idle_pm and os.path.exists(idle_pm) else []
    per = {"ane": [], "gpu": [], "cpu": [], "combined": []}
    for r in runs(pattern):
        p = os.path.join(r, "power.txt")
        if not os.path.exists(p): continue
        meta, rows = A.load(r); smp = A.parse_pm(p)
        t0 = float(meta["t0_epoch_ms"]) / 1000
        warm = t0 + max((x["end_ms"] for x in rows if x["warmup"]), default=0) / 1000
        tend = t0 + max(x["end_ms"] for x in rows) / 1000
        win = [s for s in smp if warm + 1 <= s[0] <= tend - 1]
        steady = [x for x in rows if not x["warmup"]]
        pairs = min(sum(x["dir"] == "E" for x in steady), sum(x["dir"] == "D" for x in steady))
        secs = (max(x["end_ms"] for x in steady) - min(x["sched_ms"] for x in steady)) / 1000
        if not win or not pairs: continue
        for k in per:
            pi = A.mean_power(idle, k) if idle else 0.0
            per[k].append((A.mean_power(win, k) - pi) / 1000 * secs * 1000 / pairs)
    return {k: med(v) for k, v in per.items()}


def paced(pattern):  # same as step4_sum.paced (subset)
    out = {}
    for d, k in (("E", "send"), ("D", "recv")):
        ss = [s for s in (summ(r, d) for r in runs(pattern)) if s]
        if not ss: continue
        m = lambda key: st.median(x[key] for x in ss)
        out.update({f"fps_{k}": m("achieved_fps"), f"L_{k}": m("late_or_dropped_pct"), f"p99_{k}": m("latency_ms_p99"),
                    f"kbps_{k}": m("kbps")})
        out["runs"] = len(ss)
    return out


def period(pattern):
    v = []
    for r in runs(pattern):
        e, d = summ(r, "E"), summ(r, "D")
        if e and d: v.append(max(e["frame_time_ms_mean"], d["frame_time_ms_mean"]))
    return med(v)


say(f"== CROSS-CHIP SUMMARY   {CC}")
spec = sorted(glob.glob(os.path.expanduser("~/Downloads/specs_*.txt")), key=os.path.getmtime)
say("   this Mac: " + " ".join(open(spec[-1]).read().split("\n")[1:2]) if spec else "   (run cc_specs for this Mac's specs)")

# ---------- B* ----------
R = os.path.join(CC, "bl_bstar")
ref03 = {r["metric"]: num(r["median"]) for r in read_csv(f"{BL}/03_timing_experiment/results/03_E1_E3_E4_unpaced_full_MLVC_360p.csv")}
ref05 = {r["metric"]: num(r["median"]) for r in read_csv(f"{BL}/03_timing_experiment/results/05_Bstar_duplex_paced_30fps.csv")}
ref06 = {r["processor"]: num(r["mJ_per_pair_median"]) for r in read_csv(f"{BL}/06_energy_experiment/results/06_E7_energy_AC.csv")}
rounds = []
for r in range(1, 6):
    ae, ad = summ(f"{R}/T_alone-enc_r{r}", "E"), summ(f"{R}/T_alone-dec_r{r}", "D")
    te, td = summ(f"{R}/T_turns_r{r}", "E"), summ(f"{R}/T_turns_r{r}", "D")
    de, dd = summ(f"{R}/T_duplex_r{r}", "E"), summ(f"{R}/T_duplex_r{r}", "D")
    if None in (ae, ad, te, td, de, dd): continue
    tt = max(te["frame_time_ms_mean"], td["frame_time_ms_mean"]); ts = max(de["frame_time_ms_mean"], dd["frame_time_ms_mean"])
    rounds.append(dict(t_enc_call=ae["call_ms_mean"], t_dec_call=ad["call_ms_mean"], t_enc_net=ae["infer_ms_mean"],
                       t_dec_net=ad["infer_ms_mean"], T_turns=tt, T_shared=ts, S=tt / ts,
                       S_max=(ae["call_ms_mean"] + ad["call_ms_mean"]) / max(ae["call_ms_mean"], ad["call_ms_mean"]),
                       kappa_enc_call=de["call_ms_mean"] / ae["call_ms_mean"], kappa_dec_call=dd["call_ms_mean"] / ad["call_ms_mean"]))
rows = []
for k in ("t_enc_call", "t_dec_call", "t_enc_net", "t_dec_net", "T_turns", "T_shared", "S", "S_max", "kappa_enc_call", "kappa_dec_call"):
    v = med([x[k] for x in rounds])
    rows.append(dict(metric=k, this_mac=v, shams_m4pro=ref03.get(k), this_over_shams=ratio(v, ref03.get(k)), runs=len(rounds)))
for d, dn in (("E", "send"), ("D", "receive")):
    ss = [s for s in (summ(r, d) for r in runs(f"{R}/T_duplex30_r*")) if s]
    for key, lab in (("achieved_fps", "fps"), ("late_or_dropped_pct", "late_or_dropped_pct"), ("call_ms_mean", "mean_call_ms"),
                     ("latency_ms_p99", "due_to_done_p99_ms"), ("kbps", "kbps")):
        v = med([s[key] for s in ss]); rk = f"{dn}_{lab}"
        rows.append(dict(metric=rk, this_mac=v, shams_m4pro=ref05.get(rk), this_over_shams=ratio(v, ref05.get(rk)), runs=len(ss)))
E = os.path.join(CC, "bl_energy")
en = energy(f"{E}/W_r*", f"{E}/idle/power.txt")
for k, rk in (("ane", "neural_engine"), ("cpu", "cpu"), ("gpu", "gpu"), ("combined", "total")):
    rows.append(dict(metric=f"energy_mJ_per_pair_{rk}", this_mac=en[k], shams_m4pro=ref06.get(rk), this_over_shams=ratio(en[k], ref06.get(rk)),
                     runs=len(runs(f"{E}/W_r*"))))
write("bstar_compare.csv", rows)
say("\n== B* (full MLVC 360p, NE-NE, 30 fps)              this Mac   Shams M4 Pro   this/Shams")
for r in rows:
    say(f"   {r['metric']:36s} {fmt(r['this_mac'], 10)} {fmt(r['shams_m4pro'], 12)} {fmt(r['this_over_shams'], 10, 3)}")

# ---------- NE alone, GPU encoder alone, per setting ----------
S = os.path.join(CC, "settings")
refne = {r["setting"]: r for r in read_csv(f"{BL}/09_placement_experiment/results/ne_sanity_memory.csv")}
refunit = {(r["setting"], r["unit"]): r for r in read_csv(f"{BL}/09_placement_experiment/results/alone_per_unit.csv")}


def alone(s, net, cu):
    d = "E" if net == "alone-enc" else "D"
    v = [(summ(r, d) or {}).get("call_ms_mean") for r in runs(f"{S}/alone/{s}/U_{net}_{cu}_r*")]
    if s == "mlvc_360p" and cu == "npu" and not [x for x in v if x]:  # fall back to B* rounds
        v = [(summ(r, d) or {}).get("call_ms_mean") for r in runs(f"{R}/T_{net}_r*")]
    return med(v)


rows = []
for s in PAIRS:
    e, d, g = alone(s, "alone-enc", "npu"), alone(s, "alone-dec", "npu"), alone(s, "alone-enc", "gpu")
    rs, ru = refne.get(s, {}), refunit.get((s, "gpu"), {})
    m3e, m3d = 1000 / M3[s][0], 1000 / M3[s][1]
    rows.append(dict(setting=s, enc_NE_ms=e, dec_NE_ms=d, shams_enc_NE_ms=num(rs.get("enc_ms")), shams_dec_NE_ms=num(rs.get("dec_ms")),
                     this_over_shams=ratio((e or 0) + (d or 0), (num(rs.get("enc_ms")) or 0) + (num(rs.get("dec_ms")) or 0)) if e and d else None,
                     M3_enc_ms=m3e, M3_dec_ms=m3d, this_over_M3=ratio((e or 0) + (d or 0), m3e + m3d) if e and d else None,
                     enc_GPU_ms=g, shams_enc_GPU_ms=num(ru.get("enc_ms")), gpu_this_over_shams=ratio(g, num(ru.get("enc_ms")))))
write("alone_compare.csv", rows)
say("\n== Each network alone (ms per frame)   NE enc/dec here | Shams | here/Shams | M3 Pro | here/M3 || GPU enc here | Shams | here/Shams")
for r in rows:
    say(f"   {r['setting']:12s} {fmt(r['enc_NE_ms'],6)}/{fmt(r['dec_NE_ms'],6)} | {fmt(r['shams_enc_NE_ms'],6)}/{fmt(r['shams_dec_NE_ms'],6)} |"
        f" {fmt(r['this_over_shams'],5,3)} | {fmt(r['M3_enc_ms'],5)}/{fmt(r['M3_dec_ms'],5)} | {fmt(r['this_over_M3'],5,3)} ||"
        f" {fmt(r['enc_GPU_ms'],6)} | {fmt(r['shams_enc_GPU_ms'],6)} | {fmt(r['gpu_this_over_shams'],5,3)}")

# ---------- each network alone on the GPU and the CPU ----------
rows = []
for u in ("gpu", "cpu"):
    for s in PAIRS:
        e = med([(summ(r, "E") or {}).get("call_ms_mean") for r in runs(f"{S}/alone/{s}/U_alone-enc_{u}_r*")])
        d = med([(summ(r, "D") or {}).get("call_ms_mean") for r in runs(f"{S}/alone/{s}/U_alone-dec_{u}_r*")])
        if e is None and d is None: continue
        ru = refunit.get((s, u), {}); se, sd = num(ru.get("enc_ms")), num(ru.get("dec_ms"))
        ne = refunit.get((s, "npu"), {})
        rows.append(dict(setting=s, unit=u, enc_ms=e, dec_ms=d, shams_enc_ms=se, shams_dec_ms=sd,
                         this_over_shams=ratio((e or 0) + (d or 0), (se or 0) + (sd or 0)) if e and d and se and sd else None))
if rows:
    write("units_compare.csv", rows)
    say("\n== Each network alone on the GPU and the CPU (ms per frame)   enc/dec here | Shams M4 Pro | here/Shams")
    for r in rows:
        say(f"   {r['unit']}  {r['setting']:12s} {fmt(r['enc_ms'],7)}/{fmt(r['dec_ms'],7)} | {fmt(r['shams_enc_ms'],7)}/{fmt(r['shams_dec_ms'],7)} | {fmt(r['this_over_shams'],5,3)}")

# ---------- placements ----------
reft = {(r["model"], r["res"], r["enc"], r["dec"]): r for r in read_csv(f"{BL}/09_placement_experiment/results/table_feasible.csv")}
idle_pm = os.path.join(S, "idle", "power.txt")
rows = []
for s in PAIRS:
    for ec, dc in (("npu", "npu"), ("gpu", "npu")):
        model, res = s.split("_")
        P = os.path.join(S, f"{s}_{ec}-{dc}")
        if s == "mlvc_360p" and ec == "npu":
            p30 = paced(f"{R}/T_duplex30_r*"); en = energy(f"{E}/W_r*", f"{E}/idle/power.txt"); p15 = {}
            Tt = period(f"{R}/T_turns_r*"); Ts = period(f"{R}/T_duplex_r*")
        else:
            p30, p15 = paced(f"{P}/P30_r*"), paced(f"{P}/P15_r*"); en = energy(f"{P}/P30_r*", idle_pm)
            Tt, Ts = period(f"{P}/U_turns_r*"), period(f"{P}/U_duplex_r*")
        ok = lambda p: p and p.get("L_send", 100) < 1 and p.get("L_recv", 100) < 1
        label = "30 fps" if ok(p30) else ("15 fps only" if ok(p15) else ("infeasible" if p30 else "not run"))
        ref = reft.get((model, res, ec, dc), {})
        slab = (ref.get("label") or "").split(" (")[0] or None
        rows.append(dict(model=model, res=res, enc=ec, dec=dc, label=label, shams_label=slab,
                         same_label=(label == slab) if ref else None,
                         S=ratio(Tt, Ts), shams_S=num(ref.get("S")),
                         fps30_send=p30.get("fps_send"), fps30_recv=p30.get("fps_recv"),
                         shams_fps30_send=num(ref.get("fps30_send")), shams_fps30_recv=num(ref.get("fps30_recv")),
                         L_send_pct=p30.get("L_send"), L_recv_pct=p30.get("L_recv"),
                         shams_L_send_pct=num(ref.get("L_send_pct")), shams_L_recv_pct=num(ref.get("L_recv_pct")),
                         p99_send_ms=p30.get("p99_send"), p99_recv_ms=p30.get("p99_recv"),
                         shams_p99_send_ms=num(ref.get("p99_send_ms")), shams_p99_recv_ms=num(ref.get("p99_recv_ms")),
                         mJ_per_pair=en["combined"], shams_mJ_per_pair=num(ref.get("mJ_per_pair")),
                         mJ_this_over_shams=ratio(en["combined"], num(ref.get("mJ_per_pair"))),
                         mJ_NE=en["ane"], mJ_GPU=en["gpu"], mJ_CPU=en["cpu"], paced_runs=p30.get("runs")))
write("placements_compare.csv", rows)
say("\n== Placements at 30 fps            label here (Shams)          | S here/Shams | late % s/r here | p99 ms s/r here | mJ/pair here, Shams, ratio")
for r in rows:
    say(f"   {r['model']:5s} {r['res']:5s} {r['enc']}-{r['dec']}  {r['label']:11s} ({str(r['shams_label']):11s}) |"
        f" {fmt(r['S'],4)}/{fmt(r['shams_S'],4)} | {fmt(r['L_send_pct'],5,1)}/{fmt(r['L_recv_pct'],5,1)} |"
        f" {fmt(r['p99_send_ms'],6,1)}/{fmt(r['p99_recv_ms'],6,1)} | {fmt(r['mJ_per_pair'],7,1)} {fmt(r['shams_mJ_per_pair'],7,1)} {fmt(r['mJ_this_over_shams'],5,2)}")
best = {}
for r in rows:
    if r["label"] == "30 fps" and r["mJ_per_pair"] is not None:
        k = f"{r['model']}_{r['res']}"
        if k not in best or r["mJ_per_pair"] < best[k]["mJ_per_pair"]: best[k] = r
say("   best 30 fps placement here: " + ", ".join(f"{k} {v['enc']}-{v['dec']}" for k, v in best.items()))

# ---------- contention (baseline experiment 12 protocol) ----------
C12 = os.path.join(CC, "contention12", "M4Max_contention_curve.csv")
if os.path.exists(C12):
    here = {r["load_pct"]: r for r in read_csv(C12)}
    m4p = {r["load_pct"]: r for r in read_csv(f"{BL}/12_contention_experiment/results/M4_contention_curve.csv")}
    m1 = {r["load_pct"]: r for r in read_csv(f"{REPO}/crosschip/m1_mohammed/04_m1_contention/results/M1_contention_curve.csv")}
    pk = open(os.path.join(CC, "contention12", "M4Max_memstress_peak.txt")).read().strip() if os.path.exists(os.path.join(CC, "contention12", "M4Max_memstress_peak.txt")) else ""
    say(f"\n== Contention (experiment 12 protocol; peak here: {pk})")
    say("   load | memstress GB/s M4Max / M4Pro / M1 | encoder alone ms M4Max / M4Pro / M1 | B* send call ms M4Max / M4Pro / M1 | B* send late % M4Max / M4Pro / M1")
    rows = []
    for L in ("0", "25", "50", "75"):
        g = lambda d, k: num(d.get(L, {}).get(k))
        row = dict(load_pct=int(L))
        for nm, d in (("M4Max", here), ("M4Pro", m4p), ("M1", m1)):
            row[f"{nm}_GB_s"] = g(d, "alone-enc_memstress_GB_s"); row[f"{nm}_enc_alone_ms"] = g(d, "alone-enc_call_ms_mean")
            row[f"{nm}_Bstar_send_call_ms"] = g(d, "duplex30_send_call_ms_mean"); row[f"{nm}_Bstar_send_late_pct"] = g(d, "duplex30_send_late_or_dropped_pct")
            row[f"{nm}_Bstar_recv_call_ms"] = g(d, "duplex30_recv_call_ms_mean")
        rows.append(row)
        say(f"   {L:>3s}% | {fmt(row['M4Max_GB_s'],6,0)} {fmt(row['M4Pro_GB_s'],6,0)} {fmt(row['M1_GB_s'],6,0)} |"
            f" {fmt(row['M4Max_enc_alone_ms'],6)} {fmt(row['M4Pro_enc_alone_ms'],6)} {fmt(row['M1_enc_alone_ms'],6)} |"
            f" {fmt(row['M4Max_Bstar_send_call_ms'],6)} {fmt(row['M4Pro_Bstar_send_call_ms'],6)} {fmt(row['M1_Bstar_send_call_ms'],6)} |"
            f" {fmt(row['M4Max_Bstar_send_late_pct'],5,1)} {fmt(row['M4Pro_Bstar_send_late_pct'],5,1)} {fmt(row['M1_Bstar_send_late_pct'],5,1)}")
    for nm in ("M4Max", "M4Pro", "M1"):
        a0, a75 = rows[0][f"{nm}_enc_alone_ms"], rows[3][f"{nm}_enc_alone_ms"]
        if a0 and a75: say(f"   {nm}: encoder alone {a0:.2f} -> {a75:.2f} ms at 75 % load ({100*(a75-a0)/a0:+.1f} %)")
    write("contention_3chips.csv", rows)

# ---------- decode ----------
X = os.path.join(CC, "decode")
rows = []
if os.path.isdir(X):
    say("\n== Decode across Macs (Shams's bitstreams decoded here)")
    for f in sorted(glob.glob(f"{X}/*/result.txt")):
        t = open(f).read(); nm = os.path.basename(os.path.dirname(f))
        g = lambda pat: (re.search(pat, t).group(1) if re.search(pat, t) else None)
        mins = re.findall(r"min ([\d.]+) dB\n", t)
        row = dict(stream=nm, ne_identical_to_shams=g(r"identical to Shams's NE decode: (\d+ of \d+)"),
                   ne_deterministic_here=g(r"deterministic on this Mac: (\w+)"),
                   gpu_vs_ne_min_psnr=g(r"drift NE vs GPU.*?min ([\d.]+) dB"), cpu_vs_ne_min_psnr=g(r"drift NE vs CPU.*?min ([\d.]+) dB"),
                   same_bitstream_as_shams=g(r"same bitstream as Shams's Mac: (\w+)"), failures="FAILED" in t)
        if "drift" in t:
            row["gpu_vs_ne_min_psnr"] = g(r"-- drift NE vs GPU \(this Mac\)\n[^\n]*min ([\d.]+) dB")
            row["cpu_vs_ne_min_psnr"] = g(r"-- drift NE vs CPU \(this Mac\)\n[^\n]*min ([\d.]+) dB")
        rows.append(row)
        say(f"   {nm:24s} " + "  ".join(f"{k}={v}" for k, v in row.items() if k != "stream" and v not in (None, False)))
    write("decode.csv", rows)

# ---------- thermal ----------
T = os.path.join(CC, "thermal.csv")
if os.path.exists(T):
    states = {}
    for r in csv.DictReader(open(T)):
        if r.get("thermal_state") and r["thermal_state"] != "thermal_state": states[r["thermal_state"]] = states.get(r["thermal_state"], 0) + 1
    say(f"\n== Thermal state during the runs (seconds): {states}")

open(os.path.join(OUT, "summary.txt"), "w").write("\n".join(LINES) + "\n")
say(f"\n-> {OUT}/ (bstar_compare, alone_compare, placements_compare, contention, decode .csv + summary.txt)")
