"""Step 2 summary: python3 step2_sum.py <phase2/step2 dir> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
S2, tools = sys.argv[1], sys.argv[2]; sys.path.insert(0, tools)
import analyze_run as A
# survey Table 11, MLVC paper, M3 Pro NE, measured alone (fps)
M3 = {"mlvc_360p": (129.5, 122.9), "mlvc_540p": (65.7, 62.3), "mlvc_720p": (33.8, 33.1), "mlvc_1080p": (15.6, 15.2),
      "mlvcs_540p": (152.0, 137.6), "mlvcs_720p": (83.8, 73.5), "mlvcs_1080p": (39.5, 34.6)}
order = ["mlvc_360p", "mlvc_multi", "mlvc_540p", "mlvc_720p", "mlvc_1080p", "mlvcs_540p", "mlvcs_720p", "mlvcs_1080p"]
rows = []
def med(s, net, d):
    v = []
    for r in sorted(glob.glob(f"{S2}/sanity/{s}/U_{net}_npu_r*")):
        if not os.path.isdir(r): continue
        try:
            m, fr = A.load(r); x = A.direction_summary(m, fr, d)
            if x: v.append(x)
        except Exception: pass
    if not v: return None
    return dict(n=len(v), call=st.median(x["call_ms_mean"] for x in v), net=st.median(x["infer_ms_mean"] for x in v),
                lo=min(x["call_ms_mean"] for x in v), hi=max(x["call_ms_mean"] for x in v))
def mem(s, cu):
    p = f"{S2}/memory/{s}_{cu}.log"
    if not os.path.exists(p): return ""
    t = open(p, errors="ignore").read()
    m = re.search(r"(\d+)\s+peak memory footprint", t) or re.search(r"(\d+)\s+maximum resident set size", t)
    return round(int(m.group(1)) / 2**20) if m else ""
print(f"{'setting':12s} {'enc ms':>7s} {'dec ms':>7s} {'(min-max enc)':>14s} {'enc net':>7s} {'dec net':>7s} {'M3 enc':>7s} {'M3 dec':>7s} {'M4/M3':>6s} {'turns fps':>9s} {'mem NE MB':>9s} {'mem GPU MB':>10s}  note")
for s in order:
    e, d = med(s, "alone-enc", "E"), med(s, "alone-dec", "D")
    if not e or not d:
        print(f"{s:12s} no runs"); continue
    m3 = M3.get(s if s != "mlvc_multi" else "mlvc_360p")
    m3e, m3d = (1000 / m3[0], 1000 / m3[1]) if m3 else (None, None)
    ratio = ((e["call"] + d["call"]) / (m3e + m3d)) if m3 else None
    turns = 1000 / (e["call"] + d["call"])
    note = ""
    if ratio and ratio > 0.9: note = "SLOWER than expected (B* was ~0.75): check trace for CPU ops"
    row = dict(setting=s, enc_ms=e["call"], dec_ms=d["call"], enc_min=e["lo"], enc_max=e["hi"], enc_net_ms=e["net"],
               dec_net_ms=d["net"], m3_enc_ms=m3e or "", m3_dec_ms=m3d or "", m4_over_m3=ratio or "",
               turns_fps_each_way=turns, mem_duplex_ne_MB=mem(s, "npu"), mem_duplex_gpu_MB=mem(s, "gpu"), note=note)
    rows.append(row)
    f = lambda v, w=7: f"{v:{w}.2f}" if isinstance(v, float) else f"{str(v):>{w}s}"
    print(f"{s:12s} {f(e['call'])} {f(d['call'])} {e['lo']:6.2f}-{e['hi']:<7.2f} {f(e['net'])} {f(d['net'])} {f(m3e or '')} {f(m3d or '')} {f(ratio or '',6)} {f(turns,9)} {f(row['mem_duplex_ne_MB'],9)} {f(row['mem_duplex_gpu_MB'],10)}  {note}")
if rows:
    with open(f"{S2}/step2_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
        for r in rows: w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"\n-> {S2}/step2_table.csv")
r = {x["setting"]: x for x in rows}
if "mlvc_multi" in r and "mlvc_360p" in r:
    a, b = r["mlvc_360p"], r["mlvc_multi"]
    print(f"\nmulti-size bundle at 360p vs single-size: enc {b['enc_ms']:.2f} vs {a['enc_ms']:.2f} ms, dec {b['dec_ms']:.2f} vs {a['dec_ms']:.2f} ms"
          f" -> keep {'multi-size' if b['enc_ms'] + b['dec_ms'] < a['enc_ms'] + a['dec_ms'] else 'single-size'} bundles")
