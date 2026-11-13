# 09 — Placement experiment: every setting × every encoder/decoder placement (X3, 22-hour run)

**Question.** For each of the seven model/resolution settings, and each assignment of the encoder and the decoder to the NE, GPU and CPU: does a two-way call meet 30 fps (or at least 15 fps), with how much margin, and at what energy?

**What was run.** One resumable script, **584 runs in 21.4 hours** (1,283 minutes, 13 Nov 01:07–22:31), in quiet mode:

| Part | Runs | What |
|---|---|---|
| A | 48 + 16 memory | Each network of the 8 bundles alone on the NE, 3 rounds of 60 s, compared with the survey's M3 Pro times; peak memory of a 20 s duplex run with both networks on the NE and on the GPU (`/usr/bin/time -l`) |
| B | 84 | Each network of the 7 settings alone on the GPU (60 s) and the CPU (20 s, 10 warm-up frames), 3 rounds |
| C | 452 | Per setting, 120 s idle; per placement: 3 unpaced rounds of taking turns and of sharing; 5 × 60 s paced duplex at 30 fps with `powermetrics`; if the median late share is ≥ 1 % in either direction, 3 × 60 s at 15 fps (deadline 66.7 ms) |

Placements: NE–NE, NE–GPU, GPU–NE, GPU–GPU for every setting; the five CPU placements only where both networks alone on the CPU take < 33.3 ms (decided automatically from Part B: full MLVC 360p and MLVC-S 540p). 360p NE–NE is B\* (`03_timing_experiment`) and was not repeated. Thermal state and Low Power Mode were logged once per second.

A setting is **feasible at 30 fps** if its median late or dropped share L is below 1 % in each direction; **15 fps** if that holds only at 15 fps; otherwise **infeasible**.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/all` | Parts A–C. **Resumable:** after any interruption run it again; finished runs are skipped | 21.4 h | Quiet mode (see [`../README.md`](../README.md#quiet-mode)), `./p` run first; asks for the password once (`powermetrics` needs `sudo`) |
| `scripts/2r` | NE sanity vs the survey, multi-size, memory (`step2_sum.py`); called by `all` | 1 min | any |
| `scripts/4r` | Table of feasible settings (`step4_sum.py`) | 1 min | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/logs/out_all.txt` | Full log: every run with time stamp and `requested=… resolved=…` (844 unit reports, 0 mismatches), the NE sanity and memory table, the CPU-fit decisions, the late share after each placement, and the final table |
| `raw_data/logs/out_4r.txt` | Table of feasible settings, the 720p question, the feasibility count |
| `raw_data/README.md` | Layout of the per-run records and how to pack them |
| `results/table_feasible.csv` | One row per setting × placement (38 rows, B\* included) |
| `results/ne_sanity_memory.csv` | NE time per bundle vs survey M3 Pro; peak memory |
| `results/alone_per_unit.csv` | Each network alone on NE, GPU, CPU per setting |

Columns of `table_feasible.csv`: `t_enc_ms`, `t_dec_ms` alone on the unit; `T_turns_ms`, `T_shared_ms` unpaced time per frame pair; `S` = T_turns / T_shared for this placement; `S_NE` = T_turns with both on the NE / T_shared of this placement; `fps30_*` delivered frame rate at 30 fps; `L_*_pct` late or dropped share at 30 fps; `p99_*_ms` due-to-done p99 (values of seconds are decoder backlogs: a decoder cannot drop frames); `mJ_*` energy per frame pair, idle subtracted, total and per processor; `kbps_*`; `label`; `L15_*` late share at 15 fps. Paced values are medians of 5 runs; `_send` = encoder, `_recv` = decoder. Rebuild with `python3 ../common/analysis/make_tables_x3.py`.

## Results

**NE sanity.** Every bundle runs at the expected speed: the M4 Pro needs 0.72–0.76 of the survey's M3 Pro time for full MLVC and 0.66–0.70 for MLVC-S; the three rounds, spread over 1.5 h, agree within 0.04 ms. Peak memory is 0.3–2.1 GB with both networks on the NE and 0.5–2.5 GB on the GPU. The multi-size bundle is as fast as the single-size one but uses more memory (306 vs 300 MB on the NE, 687 vs 487 MB on the GPU), so single-size bundles are kept.

**Each network alone (ms, encoder / decoder):**

| Setting | NE | GPU | CPU | CPU placements run |
|---|---|---|---|---|
| Full MLVC 360p | 5.86 / 5.94 | 13.33 / 13.18 | 19.78 / 20.74 | yes |
| Full MLVC 540p | 11.83 / 11.82 | 25.84 / 26.21 | 47.4 / 47.7 | no |
| Full MLVC 720p | 22.23 / 22.17 | 43.22 / 44.07 | 76.1 / 75.8 | no |
| Full MLVC 1080p | 46.36 / 47.56 | 93.73 / 97.13 | 173.0 / 174.5 | no |
| MLVC-S 540p | 4.83 / 4.92 | 10.34 / 10.68 | 19.73 / 21.31 | yes |
| MLVC-S 720p | 8.25 / 8.48 | 16.60 / 17.49 | 32.9 / 33.7 | no |
| MLVC-S 1080p | 18.01 / 18.42 | 35.06 / 37.36 | 71.6 / 74.3 | no |

**Feasibility: 23 of 38 combinations meet 30 fps, 9 only 15 fps, 6 neither.** Best placement of each setting (cheapest at the highest frame rate it reaches):

| Setting | Best (encoder–decoder) | Label | p99 send / receive (ms) | mJ per frame pair |
|---|---|---|---|---|
| Full MLVC 360p | NE–NE (= B\*) | 30 fps | 29.3 / 28.9 | 65.3 |
| Full MLVC 540p | **GPU–NE** (NE–NE: 6.0 % late) | 30 fps | 31.1 / 25.4 | 635.1 |
| Full MLVC 720p | NE–NE | 15 fps only | — | 404.8 |
| Full MLVC 1080p | none | infeasible | — | — |
| MLVC-S 540p | **NE–NE** | 30 fps | 26.9 / 26.1 | **45.0** |
| MLVC-S 720p | **GPU–NE** (NE–NE: 3.3 % late) | 30 fps | 25.8 / 24.3 | 333.4 |
| MLVC-S 1080p | NE–NE | 15 fps only | — | 291.6 |

**The 720p question.** Full MLVC at 720p needs 44.6 ms per pair when its networks take turns on the NE, so it would need a speedup of 44.6 / 33.3 ≈ 1.34 over taking turns; the best placement reaches 1.08 (NE–NE), and the splits only 0.97–0.99 because the GPU half is twice as slow. Full MLVC 720p is therefore 15 fps only. MLVC-S 720p meets 30 fps in three placements (NE–GPU, GPU–NE, GPU–GPU).

## Conclusion

1. **Both networks on the NE is the cheapest placement wherever it keeps up** — 3–7× cheaper than any placement using the GPU — **but it is the first to fail as the load grows:** full MLVC 540p (6.0 % late) and MLVC-S 720p (3.3 % late) miss 30 fps although their unpaced time per pair (21.7 and 15.1 ms) is well under the frame time. Paced calls take about twice as long and the two directions queue on one unit.
2. **Moving the encoder to the GPU fixes both,** at 3.1–3.6× the energy of NE–NE. Keep the **decoder** on the NE: off the NE it drifts (`04_correctness_experiment`).
3. **NE + GPU really run in parallel** (S 1.34–1.67), unlike two networks on one unit (S 1.05–1.22). Both networks on the GPU is never the best choice.
4. **At 30 fps every feasible setting keeps p99 within 24–31 ms:** higher quality is paid for in frame rate, energy or bitrate, not latency.
5. **For full MLVC:** 360p NE–NE is the best placement but 360p is too low a resolution (`05_quality_experiment`); at 540p NE–NE is no longer the best and GPU–NE becomes best, at ≈ 10× the energy of B\*; above 540p full MLVC does not reach 30 fps on this laptop.
6. **MLVC-S 540p with both networks on the NE is the most efficient setting measured:** faster than B\* (p99 ≈ 27 vs 29 ms), cheaper (45 vs 65 mJ), larger picture with higher PSNR, at about twice the bitrate.
