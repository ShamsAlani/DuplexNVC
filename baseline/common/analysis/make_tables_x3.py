#!/usr/bin/env python3
"""Rebuild the X3 result tables from the X3 console logs.

Usage:  python3 make_tables_x3.py [console_dir] [tables_dir]
Defaults: ../../09_placement_experiment/raw_data/logs and ../../09_placement_experiment/results.
Reads out_4r.txt (table of feasible settings) and out_all.txt (NE sanity and memory table, CPU-alone times).
"""
import csv, os, re, sys

X3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "09_placement_experiment")
con = sys.argv[1] if len(sys.argv) > 1 else os.path.join(X3, "raw_data", "logs")
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(X3, "results")
os.makedirs(out, exist_ok=True)

# 1. table of feasible settings (from out_4r.txt) + B* row from the core baseline
rows = []
for line in open(os.path.join(con, "out_4r.txt")):
    m = re.match(r"\s*(mlvcs?)\s+(\d+p)\s+(npu|gpu|cpu)\s+(npu|gpu|cpu)\s+(.*)", line)
    if not m:
        continue
    rest = m.group(5)
    label = re.search(r"(infeasible|15 fps only|30 fps)", rest).group(1)
    f15 = re.search(r"15 fps: L\s*([\d.]+)/\s*([\d.]+)", rest)
    n = re.findall(r"-?[\d.]+", rest.split(label)[0])
    keys = ["t_enc_ms", "t_dec_ms", "T_turns_ms", "T_shared_ms", "S", "S_NE", "fps30_send", "fps30_recv",
            "L_send_pct", "L_recv_pct", "p99_send_ms", "p99_recv_ms", "mJ_per_pair", "mJ_NE", "mJ_GPU", "mJ_CPU",
            "kbps_send", "kbps_recv"]
    r = dict(model=m.group(1), res=m.group(2), enc=m.group(3), dec=m.group(4))
    r.update({k: v.replace("-0.0", "0.0") for k, v in zip(keys, n)})
    r.update(label=label, L15_send_pct=f15.group(1) if f15 else "", L15_recv_pct=f15.group(2) if f15 else "")
    rows.append(r)
rows.append(dict(model="mlvc", res="360p", enc="npu", dec="npu", t_enc_ms="5.86", t_dec_ms="5.94",
                 T_turns_ms="11.81", T_shared_ms="10.68", S="1.11", S_NE="1.11", fps30_send="30.01",
                 fps30_recv="30.01", L_send_pct="0.0", L_recv_pct="0.0", p99_send_ms="29.27", p99_recv_ms="28.93",
                 mJ_per_pair="65.3", mJ_NE="63.4", mJ_GPU="0.0", mJ_CPU="1.9", kbps_send="120.5",
                 kbps_recv="287.1", label="30 fps (B*, from 03_timing_experiment)", L15_send_pct="", L15_recv_pct=""))
with open(os.path.join(out, "table_feasible.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# 2. NE sanity and memory (from out_all.txt, Part A summary)
san = []
cpu = {}
for line in open(os.path.join(con, "out_all.txt")):
    m = re.match(r"(mlvcs?_\w+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+-[\d.]+)\s+" + r"([\d.]+)\s+" * 6 + r"(\d+)\s+(\d+)", line)
    if m:
        san.append(m.groups())
    m = re.match(r"\s+CPU alone-(enc|dec): ([\d.]+) ms", line)
    if m:
        cpu.setdefault("pending", []).append(m.group(2))
    m = re.match(r"\s+CPU (?:does not fit|fits) for (\S+)", line)
    if m:
        cpu[m.group(1)] = cpu.pop("pending")
with open(os.path.join(out, "ne_sanity_memory.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["setting", "enc_ms", "dec_ms", "enc_min_max", "enc_net_ms", "dec_net_ms", "M3_enc_ms", "M3_dec_ms",
                "M4_over_M3", "turns_fps", "mem_NE_NE_MB", "mem_GPU_GPU_MB"])
    w.writerows(san)

# 3. each network alone per unit
alone = {}
for r in rows:
    k = f"{r['model']}_{r['res']}"
    alone.setdefault((k, r["enc"]), {})["e"] = r["t_enc_ms"]
    alone.setdefault((k, r["dec"]), {})["d"] = r["t_dec_ms"]
with open(os.path.join(out, "alone_per_unit.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["setting", "unit", "enc_ms", "dec_ms", "cpu_placements_run"])
    for k in ["mlvc_360p", "mlvc_540p", "mlvc_720p", "mlvc_1080p", "mlvcs_540p", "mlvcs_720p", "mlvcs_1080p"]:
        for u in ["npu", "gpu", "cpu"]:
            v = alone.get((k, u), {})
            e, d = (v.get("e"), v.get("d")) if "e" in v and "d" in v else cpu.get(k, ["", ""])
            w.writerow([k, u, e, d, "yes" if (k, "cpu") in alone else "no"])
print(f"wrote {len(rows)} feasibility rows, {len(san)} sanity rows to {out}")
