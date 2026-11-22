#!/usr/bin/env python3
"""Contention curve: network time on the NE against the memory bandwidth taken by memstress.

  python3 contention_sum.py <runs dir> <prefix> <tools dir>

Reads <prefix>_load<L>_alone-enc_r<n> (unpaced encoder alone on the NE) and <prefix>_load<L>_duplex30_r<n>
(B* paced), each with memstress.txt, and writes <runs dir>/<prefix>_contention_curve.csv.
"""
import csv, glob, os, re, statistics as st, sys

base, pre, tools = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
import analyze_run as A  # noqa: E402

peak = None
pk = os.path.join(base, f"{pre}_memstress_peak.txt")
if os.path.isfile(pk):
    m = re.search(r"GB_s=([\d.]+)", open(pk).read())
    peak = float(m.group(1)) if m else None
rows = []
for load in (0, 25, 50, 75):
    row = {"load_pct": load}
    for kind, d, keys in (("alone-enc", "E", ("call_ms_mean", "infer_ms_mean", "service_ms_p99")),
                          ("duplex30", "E", ("call_ms_mean", "latency_ms_p99", "late_or_dropped_pct")),
                          ("duplex30", "D", ("call_ms_mean", "latency_ms_p99", "late_or_dropped_pct"))):
        runs = sorted(r for r in glob.glob(os.path.join(base, f"{pre}_load{load}_{kind}_r*")) if os.path.isdir(r))
        ss, gb = [], []
        for r in runs:
            try:
                m, fr = A.load(r); s = A.direction_summary(m, fr, d)
                if s: ss.append(s)
            except Exception:
                pass
            p = os.path.join(r, "memstress.txt")
            if os.path.isfile(p):
                mm = re.search(r"GB_s=([\d.]+)", open(p).read())
                if mm: gb.append(float(mm.group(1)))
        tag = kind if d == "E" else kind + "_recv"
        if kind == "duplex30" and d == "E": tag = "duplex30_send"
        row[f"{tag}_runs"] = len(ss)
        for k in keys:
            row[f"{tag}_{k}"] = round(st.median(x[k] for x in ss), 2) if ss else ""
        if d == "E":
            row[f"{tag}_memstress_GB_s"] = round(st.median(gb), 2) if gb else ""
    rows.append(row)
out = os.path.join(base, f"{pre}_contention_curve.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"== {pre} contention curve -> {out}" + (f"   (memstress alone at 100 %: {peak} GB/s)" if peak else ""))
print(f"  {'load':>5s} {'GB/s':>6s} | {'enc alone call ms':>18s} {'net ms':>7s} {'p99':>7s} | {'B* send call':>12s} {'p99 due-done':>12s} {'late%':>6s} | {'B* recv call':>12s} {'p99':>7s} {'late%':>6s}")
for r in rows:
    print(f"  {r['load_pct']:>4d}% {str(r.get('alone-enc_memstress_GB_s', '')):>6s} | {str(r.get('alone-enc_call_ms_mean', '')):>18s} "
          f"{str(r.get('alone-enc_infer_ms_mean', '')):>7s} {str(r.get('alone-enc_service_ms_p99', '')):>7s} | "
          f"{str(r.get('duplex30_send_call_ms_mean', '')):>12s} {str(r.get('duplex30_send_latency_ms_p99', '')):>12s} {str(r.get('duplex30_send_late_or_dropped_pct', '')):>6s} | "
          f"{str(r.get('duplex30_recv_call_ms_mean', '')):>12s} {str(r.get('duplex30_recv_latency_ms_p99', '')):>7s} {str(r.get('duplex30_recv_late_or_dropped_pct', '')):>6s}")
try:
    a0, a75 = rows[0]["alone-enc_call_ms_mean"], rows[3]["alone-enc_call_ms_mean"]
    print(f"\n  encoder alone on the NE: {a0} ms at 0 % -> {a75} ms at 75 % ({100 * (a75 - a0) / a0:+.1f} %). "
          + ("Memory bandwidth is a limit for the NE on this chip." if (a75 - a0) / a0 > 0.05 else "Within 5 %: the NE itself, not memory speed, is the limit."))
except (TypeError, KeyError, ZeroDivisionError):
    pass
