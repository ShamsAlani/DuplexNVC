# 05 — Energy of B\* on the M1 (Day 5, night, quiet)

**Question.** How much energy does the B\* call cost per frame pair on the M1, on which processor, and how does that compare with the M4 Pro's 65.3 mJ?

**What is run.** `baseline/06_energy_experiment/scripts/w` with the `M1_` prefix: 120 s idle, then 5 paced B\* runs of 60 s with `powermetrics` (samplers `cpu_power`, `gpu_power`; the latter includes the NE) every 100 ms; run power averaged over the steady window, idle subtracted, divided by frame pairs.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_energy` | Idle recording, 5 runs, analysis, tables | 15 min | quiet mode (`./m1_quiet` first), password |

## Files

| Path | Contents |
|---|---|
| `raw_data/m1_energy/idle/power.txt` | Idle recording |
| `raw_data/m1_energy/M1_energy_r<n>/` | `frames.csv`, `run.txt`, `power.txt`, `energy.json` |
| `results/M1_energy_summary.csv` | `processor, run_mW, idle_mW, mJ_per_pair_median, mJ_min, mJ_max, J_per_minute` (as `06_E7_energy_AC.csv`) |
| `results/M1_energy_per_run.csv` | NE, CPU, GPU and total mJ per frame pair, each run |
| `raw_data/logs/out_m1_energy.txt` | Console output |

## Results

**Run:** Fri 20 Nov 2026, evening, after the Day 2 timing run and a rest; quiet mode (`m1_prep on`, `m1_quiet` still active), AC power, MacBook Air M1, 8 GB, macOS 27.2.1. 120 s idle, then 5 paced B\* runs of 60 s. Every idle sample has an ANE line (1,200 of 1,200); about 495 power samples per 56 s steady window; 1,737 frame pairs per run, the same count as on the M4 Pro (frames were late, not dropped). Thermal state `nominal` for all 895 logged seconds.

| Processor | M1 run (mW) | M1 idle (mW) | **M1 mJ per frame pair** | M1 J per minute | M4 Pro mJ per frame pair | M1 / M4 Pro |
|---|---|---|---|---|---|---|
| Neural Engine | 3594 | 0 | **119.8** (119.7–120.3) | 215.7 | 63.4 | 1.89 |
| CPU | 80 | 36 | 1.5 (1.4–1.7) | 2.7 | 1.9 | 0.79 |
| GPU | 0 | 2 | 0.0 (−0.1, idle subtracted) | 0.0 | 0.0 | — |
| **Total** | 3674 | 38 | **121.2** (121.2–121.9) | **218.1** | **65.3** | **1.86** |

Per run, the total was 121.1, 121.6, 121.2, 121.2 and 121.9 mJ per frame pair.

**Reading.**
- The same 30 fps call costs the M1 **1.86× the energy** of the M4 Pro, 99 % of it on the Neural Engine; the GPU stays idle on both chips.
- The M1's NE draws **3.6 W** during the call against 1.9 W on the M4 Pro: almost twice the power for the same work at the same frame rate, while also being 1.62× slower (Day 2). Energy per frame pair therefore improved about 1.9× from the M1 to the M4 Pro.
- The M1's CPU share is smaller (1.5 vs 1.9 mJ), within the noise of a quantity this small.
- Caveat: `powermetrics` reports Apple's internal power estimates; the estimator may differ between chip generations, so the cross-chip ratio carries that uncertainty. A check against an external power meter would remove it.

## Conclusion

B\* costs **121 mJ per frame pair (about 3.7 W) on the M1** against 65 mJ (2.3 W) on the M4 Pro, nearly all on the Neural Engine. An energy-aware controller therefore needs the chip as an input: the same setting costs almost twice as much on the older chip, on top of not meeting 30 fps there (Day 2).
