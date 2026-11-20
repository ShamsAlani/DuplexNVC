#!/usr/bin/env python3
"""Summary of the M1 timing runs, in the same tables as the M4 Pro baseline (03_timing_experiment/results).

  python3 sum_m1.py <runs dir> <prefix> <tools dir> [<out dir>]

Reads <runs dir>/<prefix>_<mode>_r<n> (unpaced rounds), <prefix>_duplex30_r<n>, <prefix>_turns30_r<n>,
<prefix>_cli_r<n>.log and writes <out dir>/<prefix>_unpaced.csv, <prefix>_duplex30.csv, <prefix>_turns30.csv,
<prefix>_cli.csv with exactly the metric names of the baseline tables, so compare_chips.py can join them.
"""
import csv, glob, os, re, statistics as st, sys

base, pre, tools = sys.argv[1], sys.argv[2], sys.argv[3]
out = sys.argv[4] if len(sys.argv) > 4 else base
sys.path.insert(0, tools)
import analyze_run as A  # noqa: E402


def summ(run, d):
    if not os.path.isfile(os.path.join(run, "frames.csv")):
        return None
    m, rows = A.load(run)
    return A.direction_summary(m, rows, d)


def med(v):
    v = [x for x in v if x is not None]
    return (st.median(v), min(v), max(v)) if v else (float("nan"),) * 3


def f2(x):
    return round(x, 2) if isinstance(x, float) else x


def write(name, header, rows):
    p = os.path.join(out, name)
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"  wrote {p}")


def unpaced(rounds):
    res = []
    for r in rounds:
        g = lambda m, d: summ(os.path.join(base, f"{pre}_{m}_r{r}"), d)
        ae, ad, te, td, de, dd = g("alone-enc", "E"), g("alone-dec", "D"), g("turns", "E"), g("turns", "D"), \
            g("duplex", "E"), g("duplex", "D")
        if None in (ae, ad, te, td, de, dd):
            continue
        tt = max(te["frame_time_ms_mean"], td["frame_time_ms_mean"])
        ts = max(de["frame_time_ms_mean"], dd["frame_time_ms_mean"])
        s = ae["call_ms_mean"] + ad["call_ms_mean"]
        res.append(dict(
            t_enc_call=ae["call_ms_mean"], t_dec_call=ad["call_ms_mean"],
            t_enc_net=ae["infer_ms_mean"], t_dec_net=ad["infer_ms_mean"],
            fps_enc=1000 / ae["frame_time_ms_mean"], fps_dec=1000 / ad["frame_time_ms_mean"],
            sum_alone=s, T_turns=tt, switching_cost=tt - s, T_shared=ts, fps_shared=1000 / ts, S=tt / ts,
            S_max=s / max(ae["call_ms_mean"], ad["call_ms_mean"]),
            kappa_enc_call=de["call_ms_mean"] / ae["call_ms_mean"], kappa_dec_call=dd["call_ms_mean"] / ad["call_ms_mean"],
            kappa_enc_net=de["infer_ms_mean"] / ae["infer_ms_mean"], kappa_dec_net=dd["infer_ms_mean"] / ad["infer_ms_mean"]))
    return res


PACED_KEYS = [("achieved_fps", "fps"), ("late_or_dropped_pct", "late_or_dropped_pct"), ("dropped", "dropped_frames"),
              ("failures", "failures"), ("service_ms_mean", "mean_call_ms"), ("service_ms_p99", "p99_call_ms"),
              ("latency_ms_p95", "due_to_done_p95_ms"), ("latency_ms_p99", "due_to_done_p99_ms"),
              ("infer_ms_mean", "network_ms"), ("kbps", "kbps")]


def paced(pattern):
    runs = sorted(x for x in glob.glob(os.path.join(base, pattern)) if os.path.isdir(x))
    rows = []
    for d, dn in (("E", "send"), ("D", "receive")):
        ss = [s for s in (summ(r, d) for r in runs) if s]
        if not ss:
            continue
        for k, lab in PACED_KEYS:
            a, b, c = med([float(s[k]) for s in ss])
            rows.append([f"{dn}_{lab}", f2(a), f2(b), f2(c), len(ss)])
        sd_m, sd_p, iv, pv = [], [], [], []
        for r in runs:
            fr = [x for x in csv.DictReader(open(os.path.join(r, "frames.csv"))) if x["dir"] == d and x["warmup"] == "0"]
            if not fr:
                continue
            w = [float(x["start_ms"]) - float(x["sched_ms"]) for x in fr]
            sd_m.append(st.mean(w)); sd_p.append(A.pct(w, 95))
            iv.append(st.mean([float(x["service_ms"]) for x in fr if x["frame_type"] == "0"] or [float("nan")]))
            pv.append(st.mean([float(x["service_ms"]) for x in fr if x["frame_type"] != "0"]))
        for lab, v in (("start_delay_mean_ms", sd_m), ("start_delay_p95_ms", sd_p), ("call_I_frame_ms", iv),
                       ("call_P_frame_ms", pv)):
            a, b, c = med(v)
            rows.append([f"{dn}_{lab}", f2(a), f2(b), f2(c), len(v)])
    return rows


print(f"== {pre} timing summary of {base}")
u = unpaced([1, 2, 3, 4, 5])
if u:
    rows = []
    for k in u[0]:
        a, b, c = med([x[k] for x in u])
        rows.append([k, f2(a), f2(b), f2(c)] + [f2(x[k]) for x in u])
    write(f"{pre}_unpaced.csv", ["metric", "median", "min", "max"] + [f"r{i + 1}" for i in range(len(u))], rows)
    print(f"  unpaced rounds used: {len(u)}")
    for r in rows:
        print(f"  {r[0]:18s} {r[1]:9} {r[2]:9} {r[3]:9}")
else:
    print("  no complete unpaced round found")
for pat, name in ((f"{pre}_duplex30_r*", f"{pre}_duplex30.csv"), (f"{pre}_turns30_r*", f"{pre}_turns30.csv")):
    rows = paced(pat)
    if rows:
        write(name, ["metric", "median", "min", "max", "runs"], rows)
        for r in rows:
            print(f"  {r[0]:32s} {r[1]:9} {r[2]:9} {r[3]:9}  runs {r[4]}")
cli = []
for log in sorted(glob.glob(os.path.join(base, f"{pre}_cli_r*.log"))):
    for line in open(log, errors="ignore"):
        m = re.match(r"\|\s*(encoder_\d|decoder_\d)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)", line)
        if m:
            cli.append([os.path.basename(log)[:-4], m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))])
if cli:
    write(f"{pre}_cli.csv", ["run", "stream", "frames", "inference_ms", "total_ms", "fps"], cli)
