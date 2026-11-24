#!/usr/bin/env python3
"""Lab GPU runs: training curves, run comparisons and training cost from the lab logs.

Reads the training log of every run (<run>.txt or <run>.txt.gz; UTF-8 or UTF-16) and pipeline.txt,
and writes to ../results:

  training_per_epoch.csv     per run and epoch: mean loss, bpp (latent + hyperprior), PSNR, seconds per 100 steps
  training_summary.csv       per run, end of training (last 40 epochs both runs have) and whole run, vs its control
  training_gap_by_block.csv  per run vs its control, in blocks of 20 epochs: how the difference develops
  training_parity.csv        per run: even vs odd epochs (detects replayed samples)
  training_cost.csv          seconds per step, minutes per epoch, hours per 200-epoch run
  training_curves.png        loss and PSNR per epoch, every run
  training_gap.png           each run minus its control, per epoch

Usage:  python3 analyze_training.py [log folder]   (default: ../raw_data/logs)
Needs Python 3.9+; numpy and matplotlib for the figures.
"""
import csv
import datetime as dt
import gzip
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "raw_data", "logs")
OUT = os.path.join(HERE, "..", "results")
RUNS = ["v1_control", "v1_b1", "control", "b1", "b1gate", "b2p25", "b2p75", "control_s2"]
STEPS_PER_EPOCH = 1000          # 2,000 samples per epoch / batch 2
WINDOWS = 10                    # MLVC logs every 100 steps
END = 40                        # "end of training" = the last 40 epochs both runs have
BLOCK = 20

LINE = re.compile(
    r"Epoch (\d+): \[(\d+)/(\d+).*?time: ([\d.]+)s,\s+loss: ([\d.]+) .*?bpp_y: ([\d.]+) .*?"
    r"bpp_z: ([\d.]+) .*?psnr: ([\d.]+)"
)


def ref_of(name):
    """Each run is compared with the control trained the same way."""
    return "v1_control" if name.startswith("v1_") else "control"


def open_log(path):
    raw = gzip.open(path, "rb").read() if path.endswith(".gz") else open(path, "rb").read()
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"   # PowerShell 5.1 writes UTF-16
    return raw.decode(enc, errors="ignore").splitlines()


def read_run(name):
    path = next((p for p in (os.path.join(LOGS, f"{name}.txt.gz"), os.path.join(LOGS, f"{name}.txt")) if os.path.exists(p)), None)
    if path is None:
        return None
    epochs = {}
    for line in open_log(path):
        m = LINE.search(line)
        if m:
            t, loss, by, bz, psnr = (float(x) for x in m.groups()[3:])
            epochs.setdefault(int(m[1]), {})[int(m[2])] = (loss, by + bz, psnr, t)   # by step: a resumed chunk rewrites it
    # epoch means of (loss, bpp, psnr, seconds per 100 steps); complete epochs only
    return {e: [st.mean(v[i] for v in w.values()) for i in range(4)]
            for e, w in epochs.items() if len(w) == WINDOWS}


def mean_over(d, es, i):
    return st.mean(d[e][i] for e in es)


def compare(d, ref, es):
    dl = [d[e][0] - ref[e][0] for e in es]
    return {"loss_minus_control": f"{st.mean(dl):+.4f}",
            "loss_diff_sd": f"{st.stdev(dl):.4f}" if len(dl) > 1 else "",
            "psnr_minus_control_db": f"{st.mean(d[e][2] - ref[e][2] for e in es):+.3f}",
            "bpp_vs_control_pct": f"{100 * st.mean(d[e][1] / ref[e][1] - 1 for e in es):+.2f}"}


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
                loss, bpp, psnr, t = d[e]
                w.writerow([n, e, f"{loss:.5f}", f"{bpp:.5f}", f"{psnr:.3f}", f"{t:.2f}"])

    rows, blocks = [], []
    for n, d in data.items():
        rn = ref_of(n)
        ref = data.get(rn) if rn != n else None
        common = sorted(set(d) & set(ref)) if ref else sorted(d)
        if not common:
            continue
        for label, es in (("end", common[-END:]), ("all", common)):
            row = {"run": n, "compared_with": rn if ref else "", "span": label, "epochs": f"{es[0]}-{es[-1]}",
                   "n_epochs": len(es), "loss": f"{mean_over(d, es, 0):.4f}", "bpp": f"{mean_over(d, es, 1):.4f}",
                   "psnr_db": f"{mean_over(d, es, 2):.3f}"}
            if ref:
                row.update(compare(d, ref, es))
            rows.append(row)
        if ref:
            for lo in range(0, common[-1] + 1, BLOCK):
                es = [e for e in common if lo <= e < lo + BLOCK]
                if es:
                    blocks.append({"run": n, "compared_with": rn, "epochs": f"{es[0]}-{es[-1]}",
                                   "control_psnr_db": f"{mean_over(ref, es, 2):.3f}", "run_psnr_db": f"{mean_over(d, es, 2):.3f}",
                                   **compare(d, ref, es)})
    keys = ["run", "compared_with", "span", "epochs", "n_epochs", "loss", "bpp", "psnr_db",
            "loss_minus_control", "loss_diff_sd", "psnr_minus_control_db", "bpp_vs_control_pct"]
    with open(os.path.join(OUT, "training_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, "training_gap_by_block.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, ["run", "compared_with", "epochs", "control_psnr_db", "run_psnr_db", "loss_minus_control",
                               "loss_diff_sd", "psnr_minus_control_db", "bpp_vs_control_pct"])
        w.writeheader(); w.writerows(blocks)

    # Replayed samples show up as a fixed difference between even and odd epochs.
    with open(os.path.join(OUT, "training_parity.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "epochs", "even_loss", "odd_loss", "odd_minus_even_loss", "even_psnr_db", "odd_psnr_db"])
        for n, d in data.items():
            ev = [e for e in d if e % 2 == 0]; od = [e for e in d if e % 2 == 1]
            if len(ev) >= 5 and len(od) >= 5:
                w.writerow([n, f"{min(d)}-{max(d)}", f"{mean_over(d, ev, 0):.4f}", f"{mean_over(d, od, 0):.4f}",
                            f"{mean_over(d, od, 0) - mean_over(d, ev, 0):+.4f}", f"{mean_over(d, ev, 2):.3f}", f"{mean_over(d, od, 2):.3f}"])

    # Training cost: step time from the logs; wall time per round (2 runs x 2 epochs) from pipeline.txt
    t100 = st.median(v[3] for n in ("control", "b1", "v1_control", "v1_b1") if n in data for v in data[n].values())
    rounds = []
    pp = os.path.join(LOGS, "pipeline.txt")
    if os.path.exists(pp):
        prev, failed = None, False
        for line in open_log(pp):
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
        w.writerow(["seconds_per_step", f"{t100 / 100:.3f}", "median over every logged 100-step window of control and B1; batch 2 x 4 frames, 256x256"])
        w.writerow(["minutes_per_epoch_compute", f"{t100 * STEPS_PER_EPOCH / 100 / 60:.2f}", f"{STEPS_PER_EPOCH} steps"])
        if rounds:
            per_epoch = st.median(rounds) / 4 / 60
            w.writerow(["minutes_per_epoch_wall", f"{per_epoch:.2f}", "median round time / (2 runs x 2 epochs); includes the restart every 2 epochs"])
            w.writerow(["hours_per_200_epoch_run", f"{per_epoch * 200 / 60:.1f}", "one fine-tune of 200 epochs (200,000 steps)"])
            w.writerow(["rounds_measured", len(rounds), "rounds without a failure, from pipeline.txt"])

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib/numpy not installed: CSVs written, figures skipped"); return

    def smooth(y, k=5):
        y = np.asarray(y, float)
        return np.convolve(np.pad(y, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid") if len(y) >= k else y

    style = {"v1_control": ("tab:blue", ":"), "v1_b1": ("tab:orange", ":"), "control": ("tab:blue", "-"), "b1": ("tab:orange", "-"),
             "b1gate": ("tab:green", "-"), "b2p25": ("tab:purple", "-"), "b2p75": ("tab:brown", "-"), "control_s2": ("tab:gray", "-")}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for n, d in data.items():
        es = sorted(d); c, ls = style.get(n, (None, "-"))
        ax[0].plot(es, smooth([d[e][0] for e in es]), color=c, ls=ls, label=n)
        ax[1].plot(es, smooth([d[e][2] for e in es]), color=c, ls=ls, label=n)
    ax[0].set_ylabel("training loss (epoch mean, 5-epoch moving average)"); ax[1].set_ylabel("training PSNR (dB, 5-epoch moving average)")
    for a in ax:
        a.set_xlabel("epoch (1,000 steps)"); a.grid(alpha=0.3); a.legend(fontsize=8)
    ax[0].set_ylim(top=0.185); ax[1].set_ylim(bottom=29.4)
    fig.suptitle("Fine-tuning MLVC on the lab GPU: training samples, not the test set (dotted: v1, replayed samples)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "training_curves.png"), dpi=150)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for n, d in data.items():
        rn = ref_of(n)
        if rn == n or rn not in data:
            continue
        es = sorted(set(d) & set(data[rn])); c, ls = style.get(n, (None, "-"))
        ax[0].plot(es, smooth([d[e][2] - data[rn][e][2] for e in es]), color=c, ls=ls, label=f"{n} - {rn}")
        ax[1].plot(es, smooth([100 * (d[e][1] / data[rn][e][1] - 1) for e in es]), color=c, ls=ls, label=f"{n} - {rn}")
    ax[0].set_ylabel("PSNR difference to control (dB)"); ax[1].set_ylabel("bitrate difference to control (%)")
    ax[0].set_ylim(-0.8, 0.1)
    for a in ax:
        a.axhline(0, color="k", lw=0.8); a.set_xlabel("epoch (1,000 steps)"); a.grid(alpha=0.3); a.legend(fontsize=8)
    fig.suptitle("Cost of each change against the control trained on the same samples (5-epoch moving average)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "training_gap.png"), dpi=150)
    print("written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
