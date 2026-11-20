#!/usr/bin/env python3
"""Side-by-side table: this chip (M1) against the M4 Pro baseline in the repository and the MLVC paper's M3 Pro.

  python3 compare_chips.py <M1 timing dir> <M1 energy dir> <repo baseline dir> <prefix> [<out csv>]

Reads <prefix>_unpaced.csv / <prefix>_duplex30.csv (sum_m1.py) and <prefix>_energy_summary.csv (m1_energy),
and the M4 Pro tables 03_E1_E3_E4_unpaced_full_MLVC_360p.csv, 05_Bstar_duplex_paced_30fps.csv, 06_E7_energy_AC.csv.
"""
import csv, os, sys

tdir, edir, base, pre = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(tdir, f"{pre}_vs_M4Pro.csv")


def table(path, key="metric", val="median"):
    if not os.path.isfile(path):
        return {}
    return {r[key]: r[val] for r in csv.DictReader(open(path))}


m1_u = table(os.path.join(tdir, f"{pre}_unpaced.csv"))
m1_p = table(os.path.join(tdir, f"{pre}_duplex30.csv"))
m4_u = table(os.path.join(base, "03_timing_experiment/results/03_E1_E3_E4_unpaced_full_MLVC_360p.csv"))
m4_p = table(os.path.join(base, "03_timing_experiment/results/05_Bstar_duplex_paced_30fps.csv"))
m1_e = table(os.path.join(edir, f"{pre}_energy_summary.csv"), key="processor", val="mJ_per_pair_median")
m4_e = table(os.path.join(base, "06_energy_experiment/results/06_E7_energy_AC.csv"), key="processor", val="mJ_per_pair_median")
# MLVC paper (arXiv 2606.28027), M3 Pro, full MLVC 360p: the same reference sum.py prints
M3 = {"t_enc_call": "7.72", "t_dec_call": "8.14", "sum_alone": "15.86"}

ROWS = [("t_enc_call", "encoder alone, call ms (unpaced)"), ("t_dec_call", "decoder alone, call ms (unpaced)"),
        ("t_enc_net", "encoder alone, network ms"), ("t_dec_net", "decoder alone, network ms"),
        ("sum_alone", "sum alone ms"), ("T_turns", "T_turns ms"), ("T_shared", "T_shared ms (duplex on NE)"),
        ("S", "S = T_turns / T_shared"), ("S_max", "S_max (ideal)"),
        ("kappa_enc_call", "kappa encoder"), ("kappa_dec_call", "kappa decoder")]
PROWS = [("send_fps", "B* send fps"), ("send_late_or_dropped_pct", "B* send late or dropped %"),
         ("send_mean_call_ms", "B* send mean call ms"), ("send_due_to_done_p99_ms", "B* send due-to-done p99 ms"),
         ("receive_fps", "B* receive fps"), ("receive_late_or_dropped_pct", "B* receive late or dropped %"),
         ("receive_mean_call_ms", "B* receive mean call ms"), ("receive_due_to_done_p99_ms", "B* receive due-to-done p99 ms"),
         ("send_kbps", "B* send kbps"), ("receive_kbps", "B* receive kbps")]
EROWS = [("total", "energy, mJ per frame pair (total)"), ("neural_engine", "energy, mJ per frame pair (NE)"),
         ("cpu", "energy, mJ per frame pair (CPU)"), ("gpu", "energy, mJ per frame pair (GPU)")]


def ratio(a, b):
    try:
        return f"{float(a) / float(b):.2f}"
    except (TypeError, ValueError, ZeroDivisionError):
        return ""


rows = []
for k, lab in ROWS:
    rows.append([lab, m1_u.get(k, ""), m4_u.get(k, ""), M3.get(k, ""), ratio(m1_u.get(k), m4_u.get(k))])
for k, lab in PROWS:
    rows.append([lab, m1_p.get(k, ""), m4_p.get(k, ""), "", ratio(m1_p.get(k), m4_p.get(k))])
for k, lab in EROWS:
    rows.append([lab, m1_e.get(k, ""), m4_e.get(k, ""), "", ratio(m1_e.get(k), m4_e.get(k))])
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["metric", pre, "M4_Pro", "M3_Pro_paper", f"{pre}_over_M4Pro"]); w.writerows(rows)
print(f"== {pre} vs M4 Pro (baseline) vs M3 Pro (MLVC paper) -> {out}")
print(f"  {'metric':38s} {pre:>9s} {'M4 Pro':>9s} {'M3 Pro':>9s} {'ratio':>7s}")
for r in rows:
    print(f"  {r[0]:38s} {str(r[1]):>9s} {str(r[2]):>9s} {str(r[3]):>9s} {str(r[4]):>7s}")
