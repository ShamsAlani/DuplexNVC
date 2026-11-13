"""Summary of baseline runs: python3 sum.py RUN_DIR PREFIX (T = experiment, S = smoke)."""
import sys, glob, os, csv, statistics as st
base, pre = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.expanduser("~/Downloads/duplexnvc-baseline/tools"))
import analyze_run as A

def S(run, d):
    p = os.path.join(base, run)
    if not os.path.isfile(os.path.join(p, "frames.csv")):
        return None
    m, rows = A.load(p)
    return A.direction_summary(m, rows, d)

def runs(name):
    return sorted(os.path.basename(x) for x in glob.glob(os.path.join(base, f"{pre}_{name}")) if os.path.isdir(x))

def med(v):
    v = [x for x in v if x is not None]
    return (st.median(v), min(v), max(v)) if v else (float("nan"),) * 3

def line(label, v, ref=""):
    a, b, c = med(v)
    print(f"  {label:40s} {a:9.2f} {b:9.2f} {c:9.2f}   {ref}")

hdr = f"  {'metric':40s} {'median':>9s} {'min':>9s} {'max':>9s}"
# ---- unpaced: alone, turns, duplex (rounds) ----
res = []
for r in range(1, 6):
    sfx = f"_r{r}" if pre == "T" else ""
    ae, ad = S(f"{pre}_alone-enc{sfx}", "E"), S(f"{pre}_alone-dec{sfx}", "D")
    te, td = S(f"{pre}_turns{sfx}", "E"), S(f"{pre}_turns{sfx}", "D")
    de, dd = S(f"{pre}_duplex{sfx}", "E"), S(f"{pre}_duplex{sfx}", "D")
    if None in (ae, ad, te, td, de, dd):
        continue
    tt = max(te["frame_time_ms_mean"], td["frame_time_ms_mean"])
    ts = max(de["frame_time_ms_mean"], dd["frame_time_ms_mean"])
    res.append(dict(te_call=ae["call_ms_mean"], td_call=ad["call_ms_mean"], te_net=ae["infer_ms_mean"],
                    td_net=ad["infer_ms_mean"], fe=1000 / ae["frame_time_ms_mean"], fd=1000 / ad["frame_time_ms_mean"],
                    sum=ae["call_ms_mean"] + ad["call_ms_mean"], tt=tt, sw=tt - ae["call_ms_mean"] - ad["call_ms_mean"],
                    ts=ts, fs=1000 / ts, S=tt / ts,
                    ceil=(ae["call_ms_mean"] + ad["call_ms_mean"]) / max(ae["call_ms_mean"], ad["call_ms_mean"]),
                    ke=de["call_ms_mean"] / ae["call_ms_mean"], kd=dd["call_ms_mean"] / ad["call_ms_mean"],
                    kne=de["infer_ms_mean"] / ae["infer_ms_mean"], knd=dd["infer_ms_mean"] / ad["infer_ms_mean"]))
    if pre == "S":
        break
print(f"\n== UNPACED (E1 alone, E3 turns, E4 duplex): rounds used {len(res)}")
print(hdr + "   MLVC paper, M3 Pro 360p")
if res:
    g = lambda k: [x[k] for x in res]
    line("encode alone, call ms", g("te_call"), "7.72 (129.5 fps)")
    line("decode alone, call ms", g("td_call"), "8.14 (122.9 fps)")
    line("encode alone, network ms", g("te_net"))
    line("decode alone, network ms", g("td_net"))
    line("encode alone fps", g("fe"))
    line("decode alone fps", g("fd"))
    line("sum alone ms", g("sum"), "15.86 (estimate)")
    line("T_turns ms (measured)", g("tt"))
    line("switching cost ms", g("sw"))
    line("T_shared ms (duplex, NE)", g("ts"))
    line("fps per direction, shared", g("fs"))
    line("S = T_turns / T_shared", g("S"))
    line("ceiling (t_enc+t_dec)/max", g("ceil"))
    line("kappa enc (call)", g("ke")); line("kappa dec (call)", g("kd"))
    line("kappa enc (network)", g("kne")); line("kappa dec (network)", g("knd"))

# ---- paced 30 fps ----
for name, title in (("duplex30*", "B* = DUPLEX PACED 30 fps (the baseline)"), ("turns30*", "TURNS PACED 30 fps")):
    rs = runs(name)
    if not rs:
        continue
    print(f"\n== {title}: runs {len(rs)}")
    print(hdr)
    for d, dn in (("E", "send"), ("D", "recv")):
        ss = [S(r, d) for r in rs]
        ss = [s for s in ss if s]
        if not ss:
            continue
        for k, lab in (("achieved_fps", "fps"), ("late_or_dropped_pct", "late+dropped %"), ("dropped", "dropped frames"),
                       ("service_ms_mean", "service mean ms"), ("service_ms_p99", "service p99 ms"),
                       ("latency_ms_p95", "due->done p95 ms"), ("latency_ms_p99", "due->done p99 ms"),
                       ("infer_ms_mean", "network ms"), ("call_ms_mean", "call ms"), ("failures", "failures"),
                       ("kbps", "kbps")):
            line(f"{dn}: {lab}", [s[k] for s in ss])
        # wake-up delay (start - scheduled) and I vs P frames, first run
        rows = [x for x in csv.DictReader(open(os.path.join(base, rs[0], "frames.csv"))) if x["dir"] == d and x["warmup"] == "0"]
        wake = [float(x["start_ms"]) - float(x["sched_ms"]) for x in rows]
        iv = [float(x["service_ms"]) for x in rows if x["frame_type"] == "0"]
        pv = [float(x["service_ms"]) for x in rows if x["frame_type"] != "0"]
        print(f"  {dn}: run1 start delay mean {st.mean(wake):.2f} ms p95 {A.pct(wake,95):.2f} | "
              f"I-frames {len(iv)} mean {st.mean(iv) if iv else float('nan'):.2f} ms | P-frames mean {st.mean(pv):.2f} ms")
