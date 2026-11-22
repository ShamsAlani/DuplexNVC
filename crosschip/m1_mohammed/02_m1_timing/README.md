# 02 — M1 timing: the B\* protocol on the M1 (Day 2, night, quiet)

**Questions.** How fast is each network alone on the M1's NE, how much does sharing the NE help (S), and does a 30 fps two-way call meet every deadline on the M1, with how much margin? How does the M1 compare with the M4 Pro baseline and the MLVC paper's M3 Pro (cross-generation, contribution C3)?

**What is run.** Exactly `baseline/03_timing_experiment/scripts/x`, prefixed `M1_`: 5 interleaved rounds of turns / encoder alone / decoder alone / duplex, unpaced, 60 s each with 60 s rest; 5 paced B\* duplex runs; 3 paced turns runs; 3 `mlvc benchmark` cross-checks. Then MLVC-S 540p (`M1S_`): 3 unpaced rounds and 3 paced duplex runs. Thermal state and Low Power Mode logged every second.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_timing` | All of the above (46 runs); calls `m1_timing_sum` at the end | 92 min | quiet mode (`./m1_prep on`, `./m1_quiet` first) |
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

**Run:** Fri 20 Nov 2026, 16:55–18:28 (+04); a first attempt was stopped after a few minutes because Google Chrome was still open, and the run was restarted after quitting it (the stopped attempt is `m1_timing_old_165545` on the Mac, not used), quiet mode (`m1_prep on`, `m1_quiet`), MacBook Air M1, 8 GB, macOS 27.2.1, AC power. All 46 runs completed (the progress label said "of 61" by mistake, fixed); 5 of 5 unpaced rounds used, round-to-round spread ≤ 0.02 ms. Thermal state `nominal` for all 5,530 logged seconds: the fanless Air did not throttle.

### Full MLVC 360p (B\* setting): M1 against the M4 Pro baseline and the MLVC paper's M3 Pro

| Metric | M1 | M4 Pro | M3 Pro (paper) | M1 / M4 Pro |
|---|---|---|---|---|
| Encoder alone, call / network ms | 9.47 / 9.09 | 5.86 / 5.57 | 7.72 | 1.62 |
| Decoder alone, call / network ms | 9.72 / 9.30 | 5.94 / 5.66 | 8.14 | 1.64 |
| Encoder / decoder fps alone | 105.6 / 102.9 | 170.7 / 168.4 | 129.5 / 122.9 | 0.62 |
| Sum alone / T_turns ms | 19.19 / 19.19 | 11.80 / 11.81 | 15.86 | 1.63 |
| Switching cost ms | 0.00 | 0.01 | — | — |
| T_shared ms, fps per direction | 17.24, 58.0 | 10.68, 93.6 | — | 1.61 |
| **S** / S_max | **1.11** / 1.97 | **1.11** / 1.99 | — | 1.00 |
| kappa encoder / decoder (call) | 1.82 / 1.77 | 1.82 / 1.80 | — | 1.00 |
| `mlvc benchmark` (3 runs) | 17.5 ms total, 17.1 inference, 57.1 fps | 10.7 ms, 10.4, 93.6 fps | — | agrees with T_shared |

### Paced at 30 fps (5 B\* duplex runs, 3 taking-turns runs; medians)

| Metric | **M1 B\* (duplex)** | M4 Pro B\* | M1 turns | M4 Pro turns |
|---|---|---|---|---|
| fps, send / receive | 30.01 / 30.00 | 30.01 / 30.01 | 30.01 / 30.00 | 30.01 / 30.01 |
| **Late or dropped, send / receive** | **7.14 % / 1.32 %** (6.7–9.3 / 0.9–1.5) | 0 / 0 | **0 % / 0.75 %** | 0 / 0 |
| Mean call ms, send / receive | 17.71 / 19.49 | 12.44 / 13.32 | 13.90 / 13.14 | 10.66 / 8.44 |
| p99 call ms, send / receive | 27.36 / 27.27 | 20.03 / 20.91 | 15.71 / 14.67 | 13.15 / 9.99 |
| Due-to-done p95 ms, send / receive | 34.45 / 31.09 | 27.88 / 28.02 | 18.78 / 32.22 | 20.17 / 29.81 |
| **Due-to-done p99 ms, send / receive** | **37.18 / 33.47** | 29.27 / 28.93 | 19.44 / 33.21 | 21.30 / 31.06 |
| Start delay mean / p95 ms, send | 4.35 / 9.6 | 5.65 / 10.0 | 2.02 / 3.5 | 3.81 / 7.6 |
| Start delay mean / p95 ms, receive | 3.79 / 8.0 | 5.06 / 10.0 | 15.92 / 18.8 | 14.47 / 20.2 |
| Call ms I-frame / P-frame, send | 17.14 / 17.71 | 12.15 / 12.45 | 14.09 / 13.90 | 10.71 / 10.66 |
| Bitrate kbps, send / receive | 120.5 / 287.1 | 120.5 / 287.1 | same | same |

### MLVC-S 540p, QP 22 (Phase-1 setting; 3 unpaced rounds, 3 paced runs)

| Metric | M1 | M4 Pro |
|---|---|---|
| Encoder / decoder alone, call ms | 7.74 / 8.10 | 4.83 / 4.92 (experiment 09) |
| T_turns / T_shared ms, S | 15.95 / 13.58, 1.17 | — / —, 1.15 (E3a) |
| Paced 30 fps: late or dropped, send / receive | 4.95 % / 2.42 % (runs: 0.0, 6.1, 4.95 / 0.0, 3.05, 2.42) | 0 / 0 |
| Paced 30 fps: due-to-done p99 ms, send / receive | 36.25 / 34.28 | 26.9 / 26.1 |

**Reading.**
1. **The M1 is 1.62× slower than the M4 Pro, uniformly**: every network alone, taking turns and sharing all scale by 1.61–1.64, and the two tools agree (our program 17.24 ms per pair shared, Microsoft's benchmark 17.5 ms). Against the paper's M3 Pro the M1 is 1.23× slower, so the three chips line up M1 → M3 Pro → M4 Pro at 1.23 : 1 : 0.76 for full MLVC 360p.
2. **The NE finding transfers exactly.** S = 1.11 on both chips, kappa 1.82 / 1.77 against 1.82 / 1.80: sharing the Neural Engine between the two networks gains 11 % of a possible 97 % on the M1 as on the M4 Pro. The near-serial behaviour of the NE is a property of Core ML's scheduling of the NE, not of one chip.
3. **B\* is not real time on the M1.** By the feasibility rule (late or dropped < 1 % in both directions) full MLVC 360p NE–NE duplex **fails at 30 fps on the M1**: 7.1 % of sent frames are late and the slowest 1 % finish 3.9 ms after the 33.3 ms deadline. The 10 s smoke test (Day 1) showed 0 % late; only the 60 s runs show it. The paced call takes 1.87× the unpaced time on the M1 (17.7 vs 9.5 ms; M4 Pro 2.1×): the pacing penalty is somewhat smaller, but the M1 starts with half the headroom. The feasibility table is chip-specific (contribution C3).
4. **Taking turns beats duplex on the M1 at 30 fps.** Serialising encoder and decoder in one thread meets the deadline (0 % late sends, 0.75 % late receives, p99 33.2 ms, just inside), while running them in parallel does not. The two parallel streams are due at the same instant and slow each other by 1.8×, so each takes 17–19 ms with p99 27 ms; in turns each call takes 13–14 ms and the decoder's wait (start delay 15.9 ms) still fits. On the M4 Pro both scheduling choices worked; on a slower chip the serial schedule wins. **A controller on an M1-class chip should choose turns, 15 fps, or a lighter setting, not B\*.**
5. **MLVC-S 540p is borderline on the M1**: one paced run 0 % late, two runs 5–6 % late (p99 36 ms). The most efficient setting of the M4 Pro table is "sometimes feasible" on the M1 and needs the drift of this decision measured over more runs.

## Conclusion

The M1 runs every part of MLVC 1.62× slower than the M4 Pro and shares the NE identically (S = 1.11), so the baseline's central finding holds across chips. But the baseline setting B\* itself is no longer real time on the M1 (7 % late frames at 30 fps), while taking turns is: the feasible settings and the right schedule depend on the chip, which is exactly what the controller's hardware input (C3, C4) has to capture. Energy on the M1 (Day 5) and the contention curve (Day 4) complete the picture.
