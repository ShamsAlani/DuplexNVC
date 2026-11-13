# 02 — Phase 1 check experiment: MLVC-S at 540p (E3a)

**Question.** Phase 1 reported MLVC-S times of which two were estimates (taking turns assumed to cost the sum of both networks, and the speedup of sharing inferred). Does the new measurement program reproduce Phase 1, and are those estimates right?

**What was run.** MLVC-S at 540p, QP 22, on the NE: 5 interleaved rounds of 60 s runs of each mode (taking turns, encoder alone, decoder alone, sharing), with 60 s rest after each run, plus 3 paced runs of taking turns at 30 fps.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/e` | The 5 rounds and 3 paced runs | 45 min | Quiet mode (see [`../README.md`](../README.md#quiet-mode)): AC power, Wi-Fi and Bluetooth off, brightness at maximum with automatic brightness and True Tone off, no other apps, `./p` run first. |
| `scripts/r` | Summary and comparison with Phase 1 | 1 min | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/e3a/` | One folder per run (`T_<mode>_r<round>`, `T_turns30_r<n>`) with `frames.csv`, `run.txt`, `.log` |
| `raw_data/logs/out_e.txt`, `out_r.txt` | Console output |
| `results/02_E3a_MLVC-S_540p_unpaced.csv` | Unpaced metrics (rows below) |
| `results/02b_E3a_turns_paced_30fps.csv` | Paced taking-turns metrics |

### Rows of the unpaced tables

| Row | Meaning |
|---|---|
| `t_enc_call`, `t_dec_call` | Mean call time of each network alone (ms) |
| `t_enc_net`, `t_dec_net` | Mean network (Core ML) time alone (ms) |
| `fps_enc`, `fps_dec` | Throughput alone |
| `sum_alone` | t_enc + t_dec |
| `T_turns` | Time per frame pair, taking turns in one thread |
| `switching_cost` | T_turns − sum_alone |
| `T_shared`, `fps_shared` | Time per frame pair and fps per direction when sharing the NE |
| `S` | T_turns / T_shared |
| `S_max` | sum_alone / max(t_enc, t_dec): ideal speedup with perfect overlap |
| `kappa_*_call`, `kappa_*_net` | Slow-down of each network when sharing (call time / network time) |

## Results

| Metric | Phase 2 measured | Phase 1 |
|---|---|---|
| t_enc / t_dec alone (ms) | 4.84 (4.84–4.86) / 4.91 (4.91–4.92) | 5.0 / 5.0 |
| Sum alone (ms) | 9.75 | 10.0 (estimated) |
| T_turns (ms) | 9.79 (9.79–9.80) | not measured |
| Switching cost (ms) | 0.04 | assumed 0 |
| T_shared (ms), fps per direction | 8.53, 117.2 | 8.7, 115.5 |
| S | 1.15 | about 1.15 (estimated) |
| κ enc / dec (network) | 1.74 / 1.71 | about 1.8 |
| Paced turns: mean call, send / receive (ms) | 10.67 / 8.65 | not measured |
| Paced turns: p99 due-to-done, send / receive (ms) | 18.90 / 28.18 | not measured |
| Paced turns: late or dropped | 0 % / 0 % | not measured |

**Reading.**
- Every Phase 1 number holds to within 4 %, and both Phase 1 estimates are now measurements.
- The new program reproduces our earlier method, so it can be trusted for the baseline.

## Conclusion

Phase 1 holds: switching between the two models costs only 0.04 ms per pair, sharing the NE gives a speedup of 1.15, and each network runs about 1.7 times slower while the other is active. The new program reproduces the earlier method, so it can be trusted for the baseline.
