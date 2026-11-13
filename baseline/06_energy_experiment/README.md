# 06 — Energy experiment: B\* on AC power (E7)

**Question.** How much energy does the B\* call cost per frame pair, and on which processor?

**What was run.** 120 s of idle recording, then 5 paced B\* runs of 60 s, each with `powermetrics` (samplers `cpu_power` and `gpu_power`; the latter includes the NE) sampling about every 125 ms. Run power is averaged over a 56 s steady window (1 s inside each end of the timed part), idle power is subtracted, and the result is divided by the frame pairs completed.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/w` | Idle recording, 5 paced runs with `powermetrics`, energy analysis | 15 min | Quiet mode (see [`../README.md`](../README.md#quiet-mode)): AC power, Wi-Fi and Bluetooth off, brightness at maximum with automatic brightness and True Tone off, no other apps, `./p` run first. Asks for the password (`powermetrics` needs `sudo`). The idle recording must use the same conditions, because it is subtracted |

## Files

| Path | Contents |
|---|---|
| `raw_data/bl_energy/idle/power.txt` | Idle recording |
| `raw_data/bl_energy/W_r<n>/` | Each run: `frames.csv`, `run.txt`, `power.txt` |
| `raw_data/logs/out_w.txt` | Console output |
| `results/06_E7_energy_AC.csv` | `processor, run_mW, idle_mW, mJ_per_pair_median, mJ_min, mJ_max, J_per_minute` |
| `results/06a_E7_energy_per_run.csv` | Per run: samples, window, frame pairs, mJ per pair for NE, CPU, GPU, total |
| `results/fig4_energy_per_run` (`.png`, `.pdf`) | Energy per frame pair, each run |

## Results

| Processor | Run (mW) | Idle (mW) | mJ per frame pair | J per minute |
|---|---|---|---|---|
| Neural Engine | 1903 | 0 | 63.4 (62.5–63.6) | 114.2 |
| CPU | 415 | 358 | 1.9 (1.8–2.9) | 3.4 |
| GPU | 0 | 0 | 0.0 | 0.0 |
| **Total** | 2318 | 358 | **65.3 (64.2–66.3)** | **117.6** |

Per run, the total was 64.24, 66.34, 65.23, 65.46 and 65.32 mJ. Each run had about 453 power samples over a 56 s steady window and 1,737 frame pairs.

**Reading.**
- 97 % of the call's energy is NE time, and the GPU is completely idle.
- This is the budget that any change of placement must be compared against.

## Conclusion

B\* costs 65.3 mJ per frame pair (about 2 W), 97 % of it on the NE, while the GPU is idle. This is the budget every other placement in `09_placement_experiment` is compared against. The values come from `powermetrics`, which reports the chip's internal power estimates; a check against an external power meter is planned if the hardware is provided.
