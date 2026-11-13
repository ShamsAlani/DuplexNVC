# bl_energy/: E7, energy of B* on AC power

**Script:** `scripts/w` (quiet Mac, `sudo` for powermetrics).
**Log:** `../logs/out_w.txt`.
**Tool:** `sudo powermetrics --samplers cpu_power,gpu_power -i 100` (`-n 1200` for idle, `-n 800` per run). Samples were requested every 100 ms and arrived about every 125 ms. The `gpu_power` sampler also reports ANE (Neural Engine) power.

| Path | Contents |
|---|---|
| `idle/power.txt` | 120 s with the Mac idle under the same conditions (no codec running) |
| `W_r1..r5/` | Five paced B\* runs of 60 s (same settings as `bl_bstar/T_duplex30_*`). Each holds `frames.csv`, `run.txt`, `power.txt` (powermetrics during the run) and `energy.json` (result) |
| `W_r1..r5.log` | Program output |

**Method** (`code/analyze_run.py power`):
1. Align the power samples to the run using `t0_epoch_ms` in `run.txt`.
2. Keep the samples inside the steady window (after warm-up, 1 s inside each end): about 453 samples over about 56 s.
3. Compute the time-weighted mean power for the run and for idle.
4. Energy per frame pair = (P_run − P_idle) × window / frame pairs (1,737).

**Result** (`../../results/06`, `06a`):

| Processor | Run (mW) | Idle (mW) | mJ per frame pair |
|---|---|---|---|
| Neural Engine | 1903 | 0 | 63.4 |
| CPU | 415 | 358 | 1.9 |
| GPU | 0 | 0 | 0.0 |
| **Total** | 2318 | 358 | **65.3** (64.2–66.3) |
