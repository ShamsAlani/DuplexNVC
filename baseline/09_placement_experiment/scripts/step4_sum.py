"""Step 4 summary: python3 step4_sum.py <WORK> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
WORK, tools = sys.argv[1], sys.argv[2]; sys.path.insert(0, tools)
import analyze_run as A
S4, S2 = f"{WORK}/phase2/step4", f"{WORK}/phase2/step2"
ORDER = ["mlvc_720p", "mlvc_540p", "mlvcs_720p", "mlvcs_1080p", "mlvc_360p", "mlvc_1080p", "mlvcs_540p"]
DL30 = 1000 / 30

def summ(run, d):
    try:
        m, fr = A.load(run); return A.direction_summary(m, fr, d)
    except Exception:
        return None

def runs(pattern):
    return sorted(r for r in glob.glob(pattern) if os.path.isdir(r) and os.path.exists(os.path.join(r, "frames.csv")))

def med(vals):
    v = [x for x in vals if x is not None]
    return st.median(v) if v else None

def alone(s, net, cu):
    d = "E" if net == "alone-enc" else "D"
    return med([(summ(r, d) or {}).get("call_ms_mean") for r in runs(f"{S4}/alone/{s}/U_{net}_{cu}_r*")])

def period(pattern):  # T per frame pair = slower direction's frame time, median over rounds
    v = []
    for r in runs(pattern):
        e, d = summ(r, "E"), summ(r, "D")
        if e and d: v.append(max(e["frame_time_ms_mean"], d["frame_time_ms_mean"]))
    return med(v)

def dup_call(pattern, d):
    return med([(summ(r, d) or {}).get("call_ms_mean") for r in runs(pattern)])

def paced(pattern):
    out = {}
    for d, k in (("E", "send"), ("D", "recv")):
        ss = [s for s in (summ(r, d) for r in runs(pattern)) if s]
        if not ss: continue
        m = lambda key: st.median(x[key] for x in ss)
        out.update({f"fps_{k}": m("achieved_fps"), f"L_{k}": m("late_or_dropped_pct"), f"call_{k}": m("service_ms_mean"),
                    f"p99_{k}": m("latency_ms_p99"), f"p95_{k}": m("latency_ms_p95"), f"kbps_{k}": m("kbps")})
        sd = []
        for r in runs(pattern):
            fr = [x for x in csv.DictReader(open(os.path.join(r, "frames.csv"))) if x["dir"] == d and x["warmup"] == "0"]
            if fr: sd.append(st.mean(float(x["start_ms"]) - float(x["sched_ms"]) for x in fr))
        out[f"start_delay_{k}"] = med(sd)
        out["runs"] = len(ss)
    return out

def energy(pattern, idle_pm):
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
    return {f"mJ_{k}": med(v) for k, v in per.items()}

def mem(s, cu):
    p = f"{S2}/memory/{s}_{cu}.log"
    if not os.path.exists(p): return None
    m = re.search(r"(\d+)\s+peak memory footprint", open(p, errors="ignore").read())
    return round(int(m.group(1)) / 2**20) if m else None

turns_ne = {}
for s in ORDER:
    turns_ne[s] = period(f"{S4}/{s}_npu-npu/U_turns_r*") or (period(f"{WORK}/runs/bl_bstar/T_turns_r*") if s == "mlvc_360p" else None)

rows = []
for s in ORDER:
    idle_pm = next(iter(glob.glob(f"{S4}/idle/*/power.txt")), None)
    bt = None
    for P in sorted(glob.glob(f"{S4}/{s}_*-*")):
        ec, dc = os.path.basename(P)[len(s) + 1:].split("-")
        b = open(f"{P}/batch.txt").read().strip() if os.path.exists(f"{P}/batch.txt") else ""
        ip = f"{S4}/idle/{b}/power.txt" if b else idle_pm
        te, td = alone(s, "alone-enc", ec), alone(s, "alone-dec", dc)
        Tt, Ts = period(f"{P}/U_turns_r*"), period(f"{P}/U_duplex_r*")
        p30, p15 = paced(f"{P}/P30_r*"), paced(f"{P}/P15_r*")
        en = energy(f"{P}/P30_r*", ip)
        ok30 = p30 and p30.get("L_send", 100) < 1 and p30.get("L_recv", 100) < 1
        ok15 = p15 and p15.get("L_send", 100) < 1 and p15.get("L_recv", 100) < 1
        label = "30 fps" if ok30 else ("15 fps only" if ok15 else ("infeasible" if p30 else "not run"))
        ce, cd = dup_call(f"{P}/U_duplex_r*", "E"), dup_call(f"{P}/U_duplex_r*", "D")
        row = dict(model=s.split("_")[0], res=s.split("_")[1], enc=ec, dec=dc, batch=b,
                   t_enc_alone=te, t_dec_alone=td, T_turns=Tt, T_shared=Ts,
                   S=(Tt / Ts) if Tt and Ts else None,
                   S_max=((te + td) / max(te, td)) if te and td else None,
                   S_vs_NE_turns=(turns_ne[s] / Ts) if turns_ne.get(s) and Ts else None,
                   kappa_enc=(ce / te) if ce and te else None, kappa_dec=(cd / td) if cd and td else None,
                   **{f"p30_{k}": v for k, v in p30.items()}, **en,
                   **{f"p15_{k}": v for k, v in p15.items() if k in ("fps_send", "fps_recv", "L_send", "L_recv", "p99_send", "p99_recv")},
                   mem_ne_MB=mem(s, "npu"), mem_gpu_MB=mem(s, "gpu"), feasible=label)
        rows.append(row)
if not rows:
    print("no Step 4 runs yet"); sys.exit()
keys = []
for r in rows:
    for k in r:
        if k not in keys: keys.append(k)
out = f"{S4}/table_feasible.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
    for r in rows: w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
f = lambda v, w=6, p=2: (f"{v:{w}.{p}f}" if isinstance(v, (int, float)) and v is not None else f"{'-':>{w}s}")
print(f"== table of feasible settings -> {out}\n")
print(f"{'model':6s} {'res':5s} {'enc':4s} {'dec':4s} {'t_enc':>6s} {'t_dec':>6s} {'T_trn':>6s} {'T_shr':>6s} {'S':>5s} {'S_NE':>5s} "
      f"{'fps30 s/r':>11s} {'L% s/r':>11s} {'p99 s/r':>11s} {'mJ/pair':>7s} {'NE/GPU/CPU mJ':>16s} {'kbps s/r':>11s}  feasible")
for r in rows:
    g = r.get
    print(f"{r['model']:6s} {r['res']:5s} {r['enc']:4s} {r['dec']:4s} {f(g('t_enc_alone'))} {f(g('t_dec_alone'))} {f(g('T_turns'))} "
          f"{f(g('T_shared'))} {f(g('S'),5)} {f(g('S_vs_NE_turns'),5)} {f(g('p30_fps_send'),5,1)}/{f(g('p30_fps_recv'),5,1)} "
          f"{f(g('p30_L_send'),5,1)}/{f(g('p30_L_recv'),5,1)} {f(g('p30_p99_send'),5,1)}/{f(g('p30_p99_recv'),5,1)} "
          f"{f(g('mJ_combined'),7,1)} {f(g('mJ_ane'),5,1)}/{f(g('mJ_gpu'),5,1)}/{f(g('mJ_cpu'),4,1)} "
          f"{f(g('p30_kbps_send'),5,0)}/{f(g('p30_kbps_recv'),5,0)}  {r['feasible']}"
          + (f"  (15 fps: L {f(g('p15_L_send'),4,1)}/{f(g('p15_L_recv'),4,1)})" if g('p15_L_send') is not None else ""))
print("\n== 720p question: speedup over taking turns on the NE, S = T_turns(NE) / T per placement")
for r in rows:
    if r["res"] == "720p" and r.get("S_vs_NE_turns"):
        print(f"   {r['model']:6s} {r['enc']}/{r['dec']}: unpaced S = {r['S_vs_NE_turns']:.2f} (needed ~1.80 for 30 fps from 16.7)  -> {r['feasible']}")
cnt = {}
for r in rows: cnt[r["feasible"]] = cnt.get(r["feasible"], 0) + 1
print("\n== feasibility count:", ", ".join(f"{k}: {v}" for k, v in cnt.items()))
