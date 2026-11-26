"""Every Mac side by side: python3 cc_compare.py <repo>
Reads cross_chip/results/<tag>/*.csv of every Mac that has pushed, adds Shams's baseline (the reference M4 Pro,
from baseline/) and the MLVC paper's M3 Pro, and writes cross_chip/results/all_macs.csv (one row per metric)."""
import csv, glob, os, sys

REPO = sys.argv[1]; RES = os.path.join(REPO, "cross_chip", "results"); BL = os.path.join(REPO, "baseline")
M3 = {"mlvc_360p": (129.5, 122.9), "mlvc_540p": (65.7, 62.3), "mlvc_720p": (33.8, 33.1), "mlvc_1080p": (15.6, 15.2),
      "mlvcs_540p": (152.0, 137.6), "mlvcs_720p": (83.8, 73.5), "mlvcs_1080p": (39.5, 34.6)}


def rows(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


tags = sorted(os.path.basename(d) for d in glob.glob(f"{RES}/*") if os.path.isdir(d))
cols = ["metric", "shams_m4pro_baseline"] + tags + ["m3pro_mlvc_paper"]
table = {}


def put(metric, col, v):
    if v in (None, ""): return
    table.setdefault(metric, {"metric": metric})[col] = v


# Shams's baseline (reference M4 Pro)
for r in rows(f"{BL}/03_timing_experiment/results/03_E1_E3_E4_unpaced_full_MLVC_360p.csv"):
    put(f"B* {r['metric']}", "shams_m4pro_baseline", r["median"])
for r in rows(f"{BL}/03_timing_experiment/results/05_Bstar_duplex_paced_30fps.csv"):
    put(f"B* {r['metric']}", "shams_m4pro_baseline", r["median"])
for r in rows(f"{BL}/06_energy_experiment/results/06_E7_energy_AC.csv"):
    put(f"B* energy_mJ_per_pair_{r['processor']}", "shams_m4pro_baseline", r["mJ_per_pair_median"])
for r in rows(f"{BL}/09_placement_experiment/results/ne_sanity_memory.csv"):
    put(f"{r['setting']} encoder alone NE ms", "shams_m4pro_baseline", r["enc_ms"])
    put(f"{r['setting']} decoder alone NE ms", "shams_m4pro_baseline", r["dec_ms"])
for r in rows(f"{BL}/09_placement_experiment/results/alone_per_unit.csv"):
    if r["unit"] == "gpu": put(f"{r['setting']} encoder alone GPU ms", "shams_m4pro_baseline", r["enc_ms"])
for r in rows(f"{BL}/09_placement_experiment/results/table_feasible.csv"):
    if r["dec"] == "npu" and r["enc"] in ("npu", "gpu"):
        k = f"{r['model']}_{r['res']} {r['enc']}-{r['dec']}"
        put(f"{k} feasible", "shams_m4pro_baseline", r["label"].split(" (")[0])
        put(f"{k} mJ per pair", "shams_m4pro_baseline", r["mJ_per_pair"])
        put(f"{k} p99 send/recv ms", "shams_m4pro_baseline", f"{r['p99_send_ms']}/{r['p99_recv_ms']}")
for s, (e, d) in M3.items():
    put(f"{s} encoder alone NE ms", "m3pro_mlvc_paper", round(1000 / e, 2)); put(f"{s} decoder alone NE ms", "m3pro_mlvc_paper", round(1000 / d, 2))

# every Mac that has run cc_all
for t in tags:
    for r in rows(f"{RES}/{t}/bstar_compare.csv"):
        put(f"B* {r['metric']}".replace("B* energy_mJ_per_pair_", "B* energy_mJ_per_pair_"), t, r["this_mac"])
    for r in rows(f"{RES}/{t}/alone_compare.csv"):
        put(f"{r['setting']} encoder alone NE ms", t, r["enc_NE_ms"]); put(f"{r['setting']} decoder alone NE ms", t, r["dec_NE_ms"])
        put(f"{r['setting']} encoder alone GPU ms", t, r["enc_GPU_ms"])
    for r in rows(f"{RES}/{t}/placements_compare.csv"):
        k = f"{r['model']}_{r['res']} {r['enc']}-{r['dec']}"
        put(f"{k} feasible", t, r["label"]); put(f"{k} mJ per pair", t, r["mJ_per_pair"])
        if r["p99_send_ms"]: put(f"{k} p99 send/recv ms", t, f"{r['p99_send_ms']}/{r['p99_recv_ms']}")
    for r in rows(f"{RES}/{t}/contention.csv"):
        put(f"contention {r['setting']} {r['network']} load {r['load_pct']} % slowdown", t, r["slowdown"])
    for r in rows(f"{RES}/{t}/decode.csv"):
        put(f"decode {r['stream']} NE identical to Shams", t, r.get("ne_identical_to_shams"))
        put(f"decode {r['stream']} same bitstream as Shams", t, r.get("same_bitstream_as_shams"))
    spec = f"{RES}/{t}/specs.txt"
    if os.path.exists(spec):
        for line in open(spec):
            for key in ("Model Identifier", "Chip", "Total Number of Cores", "GPU cores", "unified memory", "memory bandwidth", "Energy Mode", "Screen size"):
                if key in line: put(f"spec {line.split(':')[0].strip()}", t, line.split(":", 1)[1].strip())

with open(f"{RES}/all_macs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for k in table: w.writerow(table[k])
print(f"-> {RES}/all_macs.csv ({len(table)} metrics, Macs: {', '.join(tags) or 'none yet'})")
