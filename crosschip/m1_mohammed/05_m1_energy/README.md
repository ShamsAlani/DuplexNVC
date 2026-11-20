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

*(fill in on Day 5)*

| Processor | M1 mJ per frame pair | M4 Pro |
|---|---|---|
| Neural Engine | … | 63.4 |
| CPU | … | 1.9 |
| GPU | … | 0.0 |
| **Total** | … | **65.3** |

## Conclusion

*(energy per frame pair on the M1 against the M4 Pro; what it means for a controller that knows the chip)*
