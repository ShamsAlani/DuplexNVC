#!/usr/bin/env python3
"""Draw the report figures from the recomputed tables (run recompute_all.py first).

usage:  python3 make_figures.py [<baseline_dir>]
Reads the tables in each experiment's results/ folder (run recompute_all.py first) and writes each
figure, as PNG (for slides and documents) and PDF (for LaTeX), next to its tables.
"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
TABLES = {"01": "01_smoke_test_experiment", "02": "02_phase1_check_experiment", "03": "03_timing_experiment",
          "04": "03_timing_experiment", "05": "03_timing_experiment", "06": "06_energy_experiment",
          "07": "04_correctness_experiment", "08": "05_quality_experiment", "09": "05_quality_experiment", "10": "05_quality_experiment"}
FIGS = {"fig1": "03_timing_experiment", "fig2": "03_timing_experiment", "fig3": "03_timing_experiment",
        "fig4": "06_energy_experiment", "fig5": "04_correctness_experiment", "fig6": "05_quality_experiment", "fig7": "05_quality_experiment"}
BLUE, ORANGE, AQUA, YELLOW, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#d03b3b"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "legend.frameon": False,
                     "savefig.dpi": 200, "savefig.bbox": "tight"})


def rows(name):
    return list(csv.DictReader(open(os.path.join(BASE, TABLES[name[:2]], "results", name))))


def kv(name, col="median"):
    return {r["metric"]: float(r[col]) for r in rows(name)}


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(BASE, FIGS[name[:4]], "results", f"{name}.{ext}"))
    plt.close(fig)
    print("  wrote", name)


def bar_labels(ax, bars, fmt="{:.2f}"):
    for b in bars:
        ax.annotate(fmt.format(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=7, color=INK2)


# 1. unpaced timings, both models
s, b = kv("02_E3a_MLVC-S_540p_unpaced.csv"), kv("03_E1_E3_E4_unpaced_full_MLVC_360p.csv")
keys = ["t_enc_call", "t_dec_call", "sum_alone", "T_turns", "T_shared"]
labs = ["Encoder\nalone", "Decoder\nalone", "Sum of\nboth", "Taking\nturns", "Shared\nNE"]
fig, ax = plt.subplots(figsize=(6.4, 3.0))
x = range(len(keys)); w = 0.36
b1 = ax.bar([i - w / 2 - 0.01 for i in x], [s[k] for k in keys], w, color=YELLOW, label="MLVC-S 540p (E3a)")
b2 = ax.bar([i + w / 2 + 0.01 for i in x], [b[k] for k in keys], w, color=BLUE, label="Full MLVC 360p (baseline)")
bar_labels(ax, b1); bar_labels(ax, b2)
ax.set_xticks(list(x), labs); ax.set_ylabel("ms per frame or frame pair"); ax.grid(axis="x", visible=False)
ax.legend(loc="upper left", ncol=2); ax.set_ylim(0, 14.5)
ax.set_title("Unpaced times on the Neural Engine", loc="left", fontsize=10, color=INK)
save(fig, "fig1_unpaced_times")

# 2. speedup vs ideal
fig, ax = plt.subplots(figsize=(6.4, 1.9))
names = ["Full MLVC 360p", "MLVC-S 540p"]
meas, ideal = [b["S"], s["S"]], [b["S_max"], s["S_max"]]
ax.barh([0.19, 1.19], ideal, 0.36, color="#cfcdc6", label="Ideal $S_{max}$")
ax.barh([-0.19, 0.81], meas, 0.36, color=BLUE, label="Measured $S$")
for y, v in zip([-0.19, 0.81, 0.19, 1.19], meas + ideal):
    ax.annotate(f"{v:.2f}", (v, y), xytext=(3, 0), textcoords="offset points", va="center", fontsize=7, color=INK2)
ax.set_yticks([0, 1], names); ax.set_xlim(0, 2.3); ax.set_xlabel("Speedup over taking turns")
ax.grid(axis="y", visible=False); ax.legend(loc="lower right", ncol=2, bbox_to_anchor=(1, 1))
save(fig, "fig2_speedup")

# 3. paced latency vs deadline
d, t = kv("05_Bstar_duplex_paced_30fps.csv"), kv("05b_turns_paced_30fps.csv")
groups = [("B* send", d, "send"), ("B* receive", d, "receive"), ("Turns send", t, "send"), ("Turns receive", t, "receive")]
fig, ax = plt.subplots(figsize=(6.4, 3.0)); w = 0.26
for j, (k, c, lab) in enumerate([("mean_call_ms", AQUA, "Mean call time"), ("due_to_done_p95_ms", YELLOW, "Due-to-done p95"),
                                 ("due_to_done_p99_ms", BLUE, "Due-to-done p99")]):
    bars = ax.bar([i + (j - 1) * (w + 0.01) for i in range(4)], [g[1][f"{g[2]}_{k}"] for g in groups], w, color=c, label=lab)
    bar_labels(ax, bars, "{:.1f}")
ax.axhline(1000 / 30, color=RED, lw=1.2, ls="--")
ax.annotate("deadline 33.3 ms", (3.45, 1000 / 30), xytext=(0, 3), textcoords="offset points", ha="right", fontsize=7, color=RED)
ax.set_xticks(range(4), [g[0] for g in groups]); ax.set_ylabel("ms"); ax.set_ylim(0, 38)
ax.grid(axis="x", visible=False); ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, 1.13))
save(fig, "fig3_paced_latency")

# 4. energy per run
er = rows("06a_E7_energy_per_run.csv")
fig, ax = plt.subplots(figsize=(6.4, 2.6))
xs = range(len(er))
ane = [float(r["ane_mJ_per_pair"]) for r in er]; cpu = [float(r["cpu_mJ_per_pair"]) for r in er]
ax.bar(xs, ane, 0.55, color=BLUE, label="Neural Engine")
ax.bar(xs, cpu, 0.55, bottom=[a + 0.6 for a in ane], color=ORANGE, label="CPU")
for i, r in enumerate(er):
    ax.annotate(f"{float(r['total_mJ_per_pair']):.1f}", (i, ane[i] + cpu[i] + 0.6), xytext=(0, 2),
                textcoords="offset points", ha="center", fontsize=7, color=INK2)
ax.set_xticks(list(xs), [r["run"].replace("W_r", "Run ") for r in er]); ax.set_ylabel("mJ per frame pair (above idle)")
ax.set_ylim(0, 75); ax.grid(axis="x", visible=False); ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.15))
save(fig, "fig4_energy_per_run")

# 5. drift
dr = rows("07_E5_drift.csv")
bins = ["0-0", "1-15", "16-31", "32-47", "48-63"]; pos = [0, 8, 23.5, 39.5, 55.5]
fig, ax = plt.subplots(figsize=(6.4, 2.8))
for unit, c in (("GPU", BLUE), ("CPU", ORANGE)):
    v = {r["frames_after_I"]: r for r in dr if r["NE_vs"] == unit}
    ax.plot(pos, [float(v[k]["mean_dB"]) for k in bins], color=c, lw=2, marker="o", ms=5, label=f"{unit} mean")
    ax.plot(pos, [float(v[k]["min_dB"]) for k in bins], color=c, lw=2, ls="--", marker="o", ms=5, mfc=SURF, label=f"{unit} minimum")
ax.set_xticks(pos, ["0", "1-15", "16-31", "32-47", "48-63"]); ax.set_xlabel("Frames after the I-frame")
ax.set_ylabel("Y-PSNR vs NE decode (dB)"); ax.set_ylim(35, 63); ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, 1.15))
save(fig, "fig5_drift")

# 6. rate-distortion
q = rows("09_E6_rd_evaluation_mean.csv")
k = [float(r["kbps"]) for r in q]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.8))
for col, c, lab in (("psnr_y", BLUE, "Coded 360p"), ("psnr_y_display", ORANGE, "Display 1080p"), ("face_psnr_y", AQUA, "Face")):
    a1.plot(k, [float(r[col]) for r in q], color=c, lw=2, marker="o", ms=5, label=lab)
a1.set_xlabel("Bitrate (kbps)"); a1.set_ylabel("PSNR-Y (dB)"); a1.legend(loc="lower right")
a2.plot(k, [float(r["face_lpips"]) for r in q], color=BLUE, lw=2, marker="o", ms=5)
a2.set_xlabel("Bitrate (kbps)"); a2.set_ylabel("Face LPIPS (lower is better)")
fig.tight_layout(); save(fig, "fig6_rate_distortion")

# 7. per clip at QP 24
pc = [r for r in rows("10_E6_rd_evaluation_per_clip.csv") if r["qp"] == "24"]
fig, ax = plt.subplots(figsize=(6.6, 2.9)); w = 0.27
for j, (col, c, lab) in enumerate((("psnr_y", BLUE, "Coded 360p"), ("psnr_y_display", ORANGE, "Display 1080p"),
                                   ("face_psnr_y", AQUA, "Face"))):
    ax.bar([i + (j - 1) * (w + 0.02) for i in range(len(pc))], [float(r[col]) for r in pc], w, color=c, label=lab)
ax.set_xticks(range(len(pc)), [r["clip"] for r in pc], rotation=60, fontsize=7, family="monospace")
ax.set_ylim(20, 45); ax.set_ylabel("PSNR-Y at QP 24 (dB)"); ax.grid(axis="x", visible=False)
ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, 1.14))
save(fig, "fig7_per_clip_qp24")
