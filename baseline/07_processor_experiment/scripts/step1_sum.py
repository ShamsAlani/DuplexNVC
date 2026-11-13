"""Step 1 summary: python3 step1_sum.py <phase2/step1 dir> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
base, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
import analyze_run as A

DEADLINE = 1000 / 30
rows, T = [], {}
for M in ("mlvc_360p", "mlvcs_540p"):
    for kind in ("U", "P"):
        for net, d in (("alone-enc", "E"), ("alone-dec", "D")):
            for cu in ("npu", "gpu", "cpu"):
                runs = sorted(r for r in glob.glob(f"{base}/{M}/{kind}_{net}_{cu}_r*") if os.path.isdir(r))
                ss, pw = [], []
                for r in runs:
                    try:
                        m, fr = A.load(r); s = A.direction_summary(m, fr, d)
                    except Exception:
                        s = None
                    if s: ss.append(s)
                    p = os.path.join(r, "power.txt")
                    if os.path.exists(p):
                        smp = A.parse_pm(p)
                        if smp: pw.append({k: A.mean_power(smp, k) for k in ("ane", "gpu", "cpu")})
                if not ss:
                    continue
                med = lambda k: st.median(x[k] for x in ss)
                row = dict(model=M, mode="unpaced" if kind == "U" else "paced30", network=net[6:], unit=cu,
                           runs=len(ss), call_ms=med("call_ms_mean"), call_min=min(x["call_ms_mean"] for x in ss),
                           call_max=max(x["call_ms_mean"] for x in ss), network_ms=med("infer_ms_mean"),
                           p99_call_ms=med("service_ms_p99"), fps=med("achieved_fps"),
                           late_pct=med("late_or_dropped_pct") if kind == "P" else "",
                           ne_mW=st.median(x["ane"] for x in pw) if pw else "",
                           gpu_mW=st.median(x["gpu"] for x in pw) if pw else "",
                           cpu_mW=st.median(x["cpu"] for x in pw) if pw else "")
                rows.append(row); T[(M, row["mode"], row["network"], cu)] = row
out = os.path.join(base, "step1_table.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
print(f"== Step 1 table -> {out}\n")
fmt = lambda v: f"{v:8.2f}" if isinstance(v, float) else f"{str(v):>8s}"
print(f"{'model':11s} {'mode':8s} {'net':4s} {'unit':4s} {'runs':>4s} {'call ms':>8s} {'net ms':>8s} {'p99':>8s} {'fps':>8s} {'late%':>8s} {'NE mW':>8s} {'GPU mW':>8s} {'CPU mW':>8s}")
for r in rows:
    print(f"{r['model']:11s} {r['mode']:8s} {r['network']:4s} {r['unit']:4s} {r['runs']:4d}" +
          "".join(fmt(r[k]) for k in ("call_ms", "network_ms", "p99_call_ms", "fps", "late_pct", "ne_mW", "gpu_mW", "cpu_mW")))

print("\n== slowdown ratios vs NE (g = t(GPU)/t(NE), c = t(CPU)/t(NE)), call time / network time")
for M in ("mlvc_360p", "mlvcs_540p"):
    for mode in ("unpaced", "paced30"):
        for net in ("enc", "dec"):
            ne = T.get((M, mode, net, "npu"))
            if not ne: continue
            parts = []
            for cu, lab in (("gpu", "g"), ("cpu", "c")):
                o = T.get((M, mode, net, cu))
                if o: parts.append(f"{lab} = {o['call_ms']/ne['call_ms']:.2f} / {o['network_ms']/ne['network_ms']:.2f}")
            if parts: print(f"  {M:11s} {mode:8s} {net}: " + "   ".join(parts))

print("\n== D5 rules (plan Step 1)")
for net in ("enc", "dec"):
    ne, gp = T.get(("mlvc_360p", "paced30", net, "npu")), T.get(("mlvc_360p", "paced30", net, "gpu"))
    cp = T.get(("mlvc_360p", "unpaced", net, "cpu")); neu = T.get(("mlvc_360p", "unpaced", net, "npu")); gpu = T.get(("mlvc_360p", "unpaced", net, "gpu"))
    if gp: print(f"  360p {net}: GPU paced call {gp['call_ms']:.1f} ms -> {'well under' if gp['call_ms'] < 0.6*DEADLINE else 'NOT well under'} 33.3 ms")
    if gpu and neu: print(f"  360p {net}: g (unpaced) = {gpu['call_ms']/neu['call_ms']:.2f} -> {'> 3x: keep GPU only for MLVC-S and 360-540p' if gpu['call_ms']/neu['call_ms'] > 3 else '<= 3x: keep GPU placements at all resolutions'}; 720p NE->GPU needs g <= 1.10")
    if cp: print(f"  360p {net}: CPU call {cp['call_ms']:.1f} ms -> {'drop CPU from timing table (keep for correctness)' if cp['call_ms'] > DEADLINE else 'CPU can stay in the timing table'}")
