#!/usr/bin/env python3
"""Recompute every result of the DuplexNVC core baseline from the raw data.

usage:  python3 recompute_all.py [<baseline_dir>]

<baseline_dir> is the baseline/ folder of this repository (default: two levels above this script).
Reads the raw_data/ folder of each experiment and writes each table into that experiment's results/
folder, then prints a summary.
Timing and energy are recomputed from every frames.csv and powermetrics log with
analyze_run.py (same code that produced the report). Quality means are recomputed from
rd_eval.csv. Drift and BD-rate are read from the logs of ./c and ./q, because their inputs
(decoded video) are too large to ship.
"""
import csv, glob, json, os, re, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
import analyze_run as A  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
# where each run folder and console log lives in the per-experiment layout
RUNS = {"smoke": "01_smoke_test_experiment", "bl_smoke": "01_smoke_test_experiment", "e3a": "02_phase1_check_experiment",
        "bl_bstar": "03_timing_experiment", "bl_energy": "06_energy_experiment",
        "quality_eval": "05_quality_experiment", "quality_shipped": "05_quality_experiment"}
LOGS = {"out_c.txt": "04_correctness_experiment", "out_q.txt": "05_quality_experiment"}
# which experiment folder each table belongs to (by file-name prefix)
TABLES = {"01": "01_smoke_test_experiment", "02": "02_phase1_check_experiment", "03": "03_timing_experiment",
          "04": "03_timing_experiment", "05": "03_timing_experiment", "06": "06_energy_experiment",
          "07": "04_correctness_experiment", "08": "05_quality_experiment", "09": "05_quality_experiment", "10": "05_quality_experiment"}


def R(kind, name, *rest):
    if kind == "runs":
        return os.path.join(BASE, RUNS[name], "raw_data", name, *rest)
    return os.path.join(BASE, LOGS[name], "raw_data", "logs", name)


def OUTDIR(name):
    d = os.path.join(BASE, TABLES[name[:2]], "results")
    os.makedirs(d, exist_ok=True)
    return d


def summ(run, d):
    if not os.path.isfile(os.path.join(run, "frames.csv")):
        return None
    m, rows = A.load(run)
    return A.direction_summary(m, rows, d)


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v), min(v), max(v)


def write(name, header, rows):
    with open(os.path.join(OUTDIR(name), name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name}")


def f2(x):
    return round(x, 2) if isinstance(x, float) else x


def unpaced(base, pre, rounds):
    res = []
    for r in rounds:
        sfx = f"_r{r}" if r else ""
        g = lambda m, d: summ(os.path.join(base, f"{pre}_{m}{sfx}"), d)
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


def unpaced_rows(res):
    rows = []
    for k in res[0]:
        a, b, c = med([x[k] for x in res])
        rows.append([k, f2(a), f2(b), f2(c)] + [f2(x[k]) for x in res])
    return rows


PACED_KEYS = [("achieved_fps", "fps"), ("late_or_dropped_pct", "late_or_dropped_pct"), ("dropped", "dropped_frames"),
              ("failures", "failures"), ("service_ms_mean", "mean_call_ms"), ("service_ms_p99", "p99_call_ms"),
              ("latency_ms_p95", "due_to_done_p95_ms"), ("latency_ms_p99", "due_to_done_p99_ms"),
              ("infer_ms_mean", "network_ms"), ("kbps", "kbps")]


def paced(base, pattern):
    runs = sorted(x for x in glob.glob(os.path.join(base, pattern)) if os.path.isdir(x))
    rows = []
    for d, dn in (("E", "send"), ("D", "receive")):
        ss = [summ(r, d) for r in runs]
        ss = [s for s in ss if s]
        for k, lab in PACED_KEYS:
            a, b, c = med([float(s[k]) for s in ss])
            rows.append([f"{dn}_{lab}", f2(a), f2(b), f2(c), len(ss)])
        # start delay and I/P frame times, median over runs
        sd_m, sd_p, iv, pv = [], [], [], []
        for r in runs:
            fr = [x for x in csv.DictReader(open(os.path.join(r, "frames.csv"))) if x["dir"] == d and x["warmup"] == "0"]
            w = [float(x["start_ms"]) - float(x["sched_ms"]) for x in fr]
            sd_m.append(st.mean(w)); sd_p.append(A.pct(w, 95))
            iv.append(st.mean([float(x["service_ms"]) for x in fr if x["frame_type"] == "0"] or [float("nan")]))
            pv.append(st.mean([float(x["service_ms"]) for x in fr if x["frame_type"] != "0"]))
        for lab, v in (("start_delay_mean_ms", sd_m), ("start_delay_p95_ms", sd_p), ("call_I_frame_ms", iv),
                       ("call_P_frame_ms", pv)):
            a, b, c = med(v)
            rows.append([f"{dn}_{lab}", f2(a), f2(b), f2(c), len(v)])
    return rows


HDR_UNPACED = ["metric", "median", "min", "max", "r1", "r2", "r3", "r4", "r5"]
HDR_PACED = ["metric", "median", "min", "max", "runs"]

print("== Baseline B*: full MLVC 360p, NE (runs/bl_bstar)")
bs = unpaced(R("runs", "bl_bstar"), "T", [1, 2, 3, 4, 5])
write("03_E1_E3_E4_unpaced_full_MLVC_360p.csv", HDR_UNPACED, unpaced_rows(bs))
write("05_Bstar_duplex_paced_30fps.csv", HDR_PACED, paced(R("runs", "bl_bstar"), "T_duplex30_r*"))
write("05b_turns_paced_30fps.csv", HDR_PACED, paced(R("runs", "bl_bstar"), "T_turns30_r*"))

print("== E2: libmlvc CLI cross-check")
cli = []
for log in sorted(glob.glob(R("runs", "bl_bstar", "T_cli_r*.log"))):
    for line in open(log, errors="ignore"):
        m = re.match(r"\|\s*((?:en|de)coder_\d+)\s*\|\s*\d+/(\d+).*?\|\s*([\d.]+)/[\d.]+\s*\|\s*([\d.]+)/[\d.]+\s*\|\s*([\d.]+)\s*\|", line)
        if m:
            cli.append([os.path.basename(log)[:-4], m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))])
write("04_E2_cli_crosscheck.csv", ["run", "stream", "frames", "inference_ms", "total_ms", "fps"], cli)

print("== E3a: MLVC-S 540p (runs/e3a)")
e3 = unpaced(R("runs", "e3a"), "T", [1, 2, 3, 4, 5])
write("02_E3a_MLVC-S_540p_unpaced.csv", HDR_UNPACED, unpaced_rows(e3))
write("02b_E3a_turns_paced_30fps.csv", HDR_PACED, paced(R("runs", "e3a"), "T_turns30_r*"))

print("== Smoke tests (runs/smoke = MLVC-S 540p, runs/bl_smoke = full MLVC 360p)")
sm = []
for name, base in (("S1_MLVC-S_540p", R("runs", "smoke")), ("S2_full_MLVC_360p", R("runs", "bl_smoke"))):
    u = unpaced(base, "S", [0])
    if u:
        for k, v in u[0].items():
            sm.append([name, k, f2(v)])
    for mode in ("duplex30", "turns30"):
        for d, dn in (("E", "send"), ("D", "receive")):
            s = summ(os.path.join(base, f"S_{mode}"), d)
            if s:
                sm.append([name, f"{mode}_{dn}_late_or_dropped_pct", f2(s["late_or_dropped_pct"])])
write("01_smoke_test_experiment.csv", ["test", "metric", "value"], sm)

print("== E7: energy on AC (runs/bl_energy)")
idle = A.parse_pm(R("runs", "bl_energy", "idle", "power.txt"))
er = []
per = {}
for run in sorted(glob.glob(R("runs", "bl_energy", "W_r*"))):
    if not os.path.isdir(run):
        continue
    meta, rows = A.load(run)
    smp = A.parse_pm(os.path.join(run, "power.txt"))
    t0 = float(meta["t0_epoch_ms"]) / 1000.0
    warm_end = t0 + max((r["end_ms"] for r in rows if r["warmup"]), default=0) / 1000.0
    t_end = t0 + max(r["end_ms"] for r in rows) / 1000.0
    win = [s for s in smp if warm_end + 1 <= s[0] <= t_end - 1]
    steady = [r for r in rows if not r["warmup"]]
    pairs = min(sum(r["dir"] == "E" for r in steady), sum(r["dir"] == "D" for r in steady))
    steady_s = (max(r["end_ms"] for r in steady) - min(r["sched_ms"] for r in steady)) / 1000.0
    for k in ("ane", "cpu", "gpu", "combined"):
        p_run, p_idle = A.mean_power(win, k), A.mean_power(idle, k)
        e = (p_run - p_idle) / 1000.0 * steady_s
        per.setdefault(k, []).append((p_run, p_idle, 1000 * e / pairs, e / steady_s * 60))
    er.append([os.path.basename(run), len(win), round(sum(s[1] for s in win) / 1000, 1), pairs] +
              [f2(per[k][-1][2]) for k in ("ane", "cpu", "gpu", "combined")])
write("06a_E7_energy_per_run.csv", ["run", "power_samples", "window_s", "frame_pairs",
                                    "ane_mJ_per_pair", "cpu_mJ_per_pair", "gpu_mJ_per_pair", "total_mJ_per_pair"], er)
rows = []
for k, lab in (("ane", "neural_engine"), ("cpu", "cpu"), ("gpu", "gpu"), ("combined", "total")):
    v = per[k]
    a, b, c = med([x[2] for x in v])
    rows.append([lab, f2(st.median([x[0] for x in v])), f2(st.median([x[1] for x in v])), f2(a), f2(b), f2(c),
                 f2(st.median([x[3] for x in v]))])
write("06_E7_energy_AC.csv", ["processor", "run_mW", "idle_mW", "mJ_per_pair_median", "mJ_min", "mJ_max", "J_per_minute"], rows)

print("== E5: drift (from out_c.txt)")
dr, cur = [], None
for line in open(R("logs", "out_c.txt"), errors="ignore"):
    m = re.match(r"-- drift NE vs (\w+)", line)
    if m:
        cur = m.group(1)
    m = re.search(r"frames\s+(\d+)-\s*(\d+) after an I-frame: mean\s+([\d.]+) dB\s+min\s+([\d.]+)", line)
    if m and cur:
        dr.append([cur, f"{m.group(1)}-{m.group(2)}", float(m.group(3)), float(m.group(4))])
    m = re.search(r"Y-PSNR between decodes: mean ([\d.]+) dB, min ([\d.]+)", line)
    if m and cur:
        dr.append([cur, "all", float(m.group(1)), float(m.group(2))])
write("07_E5_drift.csv", ["NE_vs", "frames_after_I", "mean_dB", "min_dB"], dr)

print("== E6: quality (runs/quality_eval/rd_eval.csv)")
q = list(csv.DictReader(open(R("runs", "quality_eval", "rd_eval.csv"))))
keys = ["kbps", "psnr_y", "psnr_yuv", "psnr_y_display", "face_psnr_y", "face_lpips"]
rows = []
for qp in sorted({int(x["qp"]) for x in q}):
    sel = [x for x in q if int(x["qp"]) == qp]
    rows.append([qp, len(sel)] + [round(st.mean(float(x[k]) for x in sel), 3) for k in keys])
write("09_E6_rd_evaluation_mean.csv", ["qp", "clips"] + keys, rows)
write("10_E6_rd_evaluation_per_clip.csv", ["clip", "qp", "frames", "faces_scored", "face_height_coded_px"] + keys,
      [[x["clip"], x["qp"], x["frames"], x["faces"], round(float(x["face_h_coded_mean"]), 1)] +
       [round(float(x[k]), 3) for k in keys] for x in q])
bd = [l.strip() for l in open(R("logs", "out_q.txt"), errors="ignore") if l.startswith("|")]
with open(os.path.join(OUTDIR("08"), "08_E6_bdrate_mlvc_validate.txt"), "w") as f:
    f.write("\n".join(bd) + "\n")
print("  wrote 08_E6_bdrate_mlvc_validate.txt")

summary = dict(
    E1_t_enc_ms=med([x["t_enc_call"] for x in bs])[0], E1_t_dec_ms=med([x["t_dec_call"] for x in bs])[0],
    T_turns_ms=med([x["T_turns"] for x in bs])[0], T_shared_ms=med([x["T_shared"] for x in bs])[0],
    S=med([x["S"] for x in bs])[0], S_max=med([x["S_max"] for x in bs])[0],
    kappa_enc=med([x["kappa_enc_call"] for x in bs])[0], kappa_dec=med([x["kappa_dec_call"] for x in bs])[0],
    E3a_S=med([x["S"] for x in e3])[0], energy_mJ_per_pair=med([x[2] for x in per["combined"]])[0])
json.dump({k: round(v, 3) for k, v in summary.items()}, open(os.path.join(HERE, "summary_baseline.json"), "w"), indent=1)
print("\n== headline:", json.dumps({k: round(v, 2) for k, v in summary.items()}))
