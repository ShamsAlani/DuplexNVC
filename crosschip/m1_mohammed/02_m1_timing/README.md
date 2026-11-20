# 02 — M1 timing: the B\* protocol on the M1 (Day 2, night, quiet)

**Questions.** How fast is each network alone on the M1's NE, how much does sharing the NE help (S), and does a 30 fps two-way call meet every deadline on the M1, with how much margin? How does the M1 compare with the M4 Pro baseline and the MLVC paper's M3 Pro (cross-generation, contribution C3)?

**What is run.** Exactly `baseline/03_timing_experiment/scripts/x`, prefixed `M1_`: 5 interleaved rounds of turns / encoder alone / decoder alone / duplex, unpaced, 60 s each with 60 s rest; 5 paced B\* duplex runs; 3 paced turns runs; 3 `mlvc benchmark` cross-checks. Then MLVC-S 540p (`M1S_`): 3 unpaced rounds and 3 paced duplex runs. Thermal state and Low Power Mode logged every second.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_timing` | All of the above; calls `m1_timing_sum` at the end | 95 min | quiet mode (`./m1_quiet` first), night |
| `scripts/m1_timing_sum` | Tables (`common/sum_m1.py`) and the chip comparison (`common/compare_chips.py`) | 1 min | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/m1_timing/M1_<mode>_r<n>`, `M1_duplex30_r<n>`, `M1_turns30_r<n>`, `M1_cli_r<n>.log`, `M1S_*` | One folder per run: `frames.csv`, `run.txt`, `.log`, `.therm` |
| `raw_data/m1_timing/thermal.csv` | Thermal state and Low Power Mode at 1 Hz |
| `results/M1_unpaced.csv` | E1, E3, E4 on the M1 (same metric names as `03_E1_E3_E4_unpaced_full_MLVC_360p.csv`) |
| `results/M1_duplex30.csv`, `M1_turns30.csv` | B\* paced on the M1 (same metric names as `05_Bstar_duplex_paced_30fps.csv`) |
| `results/M1_cli.csv` | `mlvc benchmark` cross-check |
| `results/M1S_unpaced.csv`, `M1S_duplex30.csv` | MLVC-S 540p on the M1 |
| `results/M1_vs_M4Pro.csv` | M1 / M4 Pro / M3 Pro side by side, with the M1-over-M4 ratio |
| `raw_data/logs/out_m1_timing.txt`, `out_m1_timing_sum.txt` | Console output |

## Results

*(fill in on Day 2)*

| Metric | M1 | M4 Pro | M3 Pro (paper) |
|---|---|---|---|
| Encoder / decoder alone, call ms | … | 5.86 / 5.94 | 7.72 / 8.14 |
| T_turns / T_shared ms, S | … | 11.81 / 10.68, 1.11 | — |
| B\* late or dropped %, send / receive | … | 0 / 0 | — |
| B\* due-to-done p99 ms, send / receive | … | 29.27 / 28.93 | — |
| MLVC-S 540p alone, encoder / decoder ms | … | 4.83 / 4.92 | — |

Thermal states seen during the night: …

## Conclusion

*(is the M1 real time at B\*; where it sits between M3 Pro and M4 Pro; whether the NE shares better or worse)*
