#!/usr/bin/env python3
"""Lab GPU runs: training curves, run comparison and training cost (E5) from the lab logs.

Reads the training logs written by lab.ps1 (one per run, e.g. control.txt, b1.txt) and pipeline.txt,
and writes to ../results:
  training_per_epoch.csv   per run and epoch: mean loss, bpp (y + z), PSNR and seconds per 100 steps
  training_summary.csv     per run, over the epochs every run has completed: means and the difference to control
  training_cost.csv        E5: seconds per step, minutes per epoch, hours per 200-epoch run
  training_parity.csv      per run: even vs odd epochs, and first vs last five epochs of each (detects replayed samples, trend)
  training_curves.png      loss and PSNR per epoch for every run, and each run minus control

Usage:  python3 analyze_training.py [log folder]   (default: ../raw_data/logs)
Only the Python standard library and matplotlib are needed.
"""
import csv
import datetime as dt
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "raw_data", "logs")
OUT = os.path.join(HERE, "..", "results")
RUNS = ["control", "b1", "b1gate", "b2p25", "b2p75", "control_s2", "v1_control", "v1_b1"]


def ref_of(name):
    """Each run is compared with the control trained the same way (v1 runs with v1_control)."""
    return "v1_control" if name.startswith("v1_") else "control"
STEPS_PER_EPOCH = 1000          # train.dataset.desired_length 2000 / batch size 2
WINDOWS_PER_EPOCH = 10          # MLVC logs every 100 steps

LINE = re.compile(
    r"Epoch (\d+): \[(\d+)/(\d+).*?time: ([\d.]+)s,\s+loss: ([\d.]+) .*?bpp_y: ([\d.]+) .*?"
    r"bpp_z: ([\d.]+) .*?psnr: ([\d.]+)"
)


def read_run(name):
    path = os.path.join(LOGS, f"{name}.txt")
    if not os.path.exists(path):
        return None
    epochs = {}
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = LINE.search(line)
        if m:
            e = int(m[1])
            t, loss, by, bz, psnr = (float(x) for x in m.groups()[3:])
            epochs.setdefault(e, {})[int(m[2])] = (t, loss, by + bz, psnr)   # keyed by step: a restart rewrites it
    return {e: list(w.values()) for e, w in epochs.items() if len(w) == WINDOWS_PER_EPOCH}


def mean_cols(rows):
    return [st.mean(r[i] for r in rows) for i in range(4)]


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {n: d for n in RUNS if (d := read_run(n))}
    if not data:
        raise SystemExit(f"no training logs found in {LOGS}")

    with open(os.path.join(OUT, "training_per_epoch.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "epoch", "loss", "bpp", "psnr_db", "s_per_100_steps"])
        for n, d in data.items():
            for e in sorted(d):
                t, loss, bpp, psnr = mean_cols(d[e])
                w.writerow([n, e, f"{loss:.5f}", f"{bpp:.5f}", f"{psnr:.3f}", f"{t:.2f}"])

    rows = []
    for n, d in data.items():
        rn = ref_of(n)
        ref = data.get(rn) if rn != n else None
        common = sorted(set(d) & set(ref)) if ref else sorted(d)
        if not common:
            continue
        per = {e: mean_cols(d[e]) for e in common}
        row = {"run": n, "compared_with": rn if ref else "", "epochs": f"{common[0]}-{common[-1]}", "n_epochs": len(common),
               "loss": f"{st.mean(v[1] for v in per.values()):.4f}", "bpp": f"{st.mean(v[2] for v in per.values()):.4f}",
               "psnr_db": f"{st.mean(v[3] for v in per.values()):.3f}"}
        if ref:
            rv = {e: mean_cols(ref[e]) for e in common}
            dl = [per[e][1] - rv[e][1] for e in common]
            dp = [per[e][3] - rv[e][3] for e in common]
            db = [per[e][2] / rv[e][2] - 1 for e in common]
            row.update({"loss_minus_control": f"{st.mean(dl):+.4f}",
                        "loss_diff_sd_across_epochs": f"{st.stdev(dl):.4f}" if len(dl) > 1 else "",
                        "psnr_minus_control_db": f"{st.mean(dp):+.3f}",
                        "bpp_vs_control_pct": f"{100 * st.mean(db):+.2f}"})
        rows.append(row)
    keys = ["run", "compared_with", "epochs", "n_epochs", "loss", "bpp", "psnr_db", "loss_minus_control",
            "loss_diff_sd_across_epochs", "psnr_minus_control_db", "bpp_vs_control_pct"]
    with open(os.path.join(OUT, "training_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)

    # Parity and trend: with replayed samples, even and odd epochs are two fixed sample sets, so they differ
    # systematically; comparing first and last five epochs of the same parity shows whether training still improves.
    with open(os.path.join(OUT, "training_parity.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "parity", "epochs", "mean_loss", "mean_psnr_db", "first5_loss", "last5_loss", "first5_psnr_db", "last5_psnr_db"])
        for n, d in data.items():
            for par, name in ((0, "even"), (1, "odd")):
                es = sorted(e for e in d if e % 2 == par)
                if len(es) < 10:
                    continue
                v = {e: mean_cols(d[e]) for e in es}
                f5, l5 = es[:5], es[-5:]
                w.writerow([n, name, f"{es[0]}-{es[-1]}", f"{st.mean(v[e][1] for e in es):.4f}", f"{st.mean(v[e][3] for e in es):.3f}",
                            f"{st.mean(v[e][1] for e in f5):.4f}", f"{st.mean(v[e][1] for e in l5):.4f}",
                            f"{st.mean(v[e][3] for e in f5):.3f}", f"{st.mean(v[e][3] for e in l5):.3f}"])

    # E5: training cost. Step time from the logs; wall time per round (both runs advance 2 epochs) from pipeline.txt
    t100 = st.median(v[0] for d in data.values() for rows_ in d.values() for v in rows_)
    rounds = []
    pp = os.path.join(LOGS, "pipeline.txt")
    if os.path.exists(pp):
        prev, failed = None, False          # a round counts only if no run failed in it
        for line in open(pp, encoding="utf-8", errors="ignore"):
            if "FAILED" in line or line.startswith(("start", "STOPPED")):
                failed = True
                if line.startswith(("start", "STOPPED")):
                    prev = None
                continue
            m = re.match(r"(?:both|Queue A) at epoch (\d+)\s+(\d+/\d+/\d+ \d+:\d+:\d+)", line)
            if not m:
                continue
            e1, t1 = int(m[1]), dt.datetime.strptime(m[2], "%m/%d/%Y %H:%M:%S")
            if prev and not failed and e1 == prev[0] + 2:
                rounds.append((t1 - prev[1]).total_seconds())
            prev, failed = (e1, t1), False
    with open(os.path.join(OUT, "training_cost.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "value", "note"])
        w.writerow(["seconds_per_step", f"{t100 / 100:.3f}", "median over all logged 100-step windows; batch 2 x 4 frames, 256x256 patches"])
        w.writerow(["minutes_per_epoch_compute", f"{t100 * STEPS_PER_EPOCH / 100 / 60:.2f}", f"{STEPS_PER_EPOCH} steps"])
        if rounds:
            per_epoch = st.median(rounds) / (2 * 2) / 60   # control + B1 rounds: 2 runs x 2 epochs
            w.writerow(["minutes_per_epoch_wall", f"{per_epoch:.2f}", "median control+B1 round time / (2 runs x 2 epochs); includes the restart every 2 epochs"])
            w.writerow(["hours_per_200_epoch_run", f"{per_epoch * 200 / 60:.1f}", "one fine-tune of 200 epochs (200k steps)"])
            w.writerow(["rounds_measured", len(rounds), "from pipeline.txt"])

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: CSVs written, figure skipped"); return
    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for n, d in data.items():
        es = sorted(d); v = [mean_cols(d[e]) for e in es]
        ax[0][0].plot(es, [x[1] for x in v], label=n); ax[1][0].plot(es, [x[3] for x in v], label=n)
        rn = ref_of(n)
        if rn != n and rn in data:
            ce = [e for e in es if e in data[rn]]
            ax[0][1].plot(ce, [mean_cols(d[e])[1] - mean_cols(data[rn][e])[1] for e in ce], label=f"{n} - {rn}")
            ax[1][1].plot(ce, [mean_cols(d[e])[3] - mean_cols(data[rn][e])[3] for e in ce], label=f"{n} - {rn}")
    ax[0][0].set_ylabel("training loss (epoch mean)"); ax[1][0].set_ylabel("training PSNR (dB)")
    ax[0][1].set_ylabel("loss difference"); ax[1][1].set_ylabel("PSNR difference (dB)")
    for a in ax.flat:
        a.grid(alpha=0.3); a.legend(fontsize=8)
    for a in ax[1]:
        a.set_xlabel("epoch (1000 steps)")
    for a in ax[:, 1]:
        a.axhline(0, color="k", lw=0.8)
    fig.suptitle("Fine-tuning MLVC on the lab GPU (training clips, not the test set)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "training_curves.png"), dpi=150)
    print("written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
