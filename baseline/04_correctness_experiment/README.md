# 04 — Correctness experiment: decoding and drift across processors (E5)

**Question.** Is decoding correct and repeatable, and does a decoder on the GPU or CPU give the same pictures as one on the NE? This decides whether the decoder can be moved off the NE.

**What was run.** The outgoing stream of the first B\* run (1,802 frames, from `03_timing_experiment/raw_data/bl_bstar/T_duplex30_r1/`) was decoded with the `mlvc` tool twice on the NE and once each on the GPU and the CPU; the decodes were compared frame by frame (Y-PSNR), grouped by position after the last I-frame (every 64 frames).

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/c` | The four decodes, determinism check and drift | 5 min | any (after `03_timing_experiment`) |

## Files

| Path | Contents |
|---|---|
| `raw_data/logs/out_c.txt` | Console output with the drift table (the decoded videos are too large to ship; the per-decode logs are next to the stream in `03_timing_experiment/raw_data/bl_bstar/T_duplex30_r1/`) |
| `results/07_E5_drift.csv` | `NE_vs` (GPU/CPU), `frames_after_I`, `mean_dB`, `min_dB` |
| `results/fig5_drift` (`.png`, `.pdf`) | Drift through the group of pictures |

## Results

- **Correctness:** the B\* stream of 1,802 frames decoded with no failure on the NE (twice), the GPU and the CPU.
- **NE determinism:** the two NE decodes are bit-identical.

Drift is the Y-PSNR between the NE decode and a decode on another processor, as mean / minimum in dB:

| Frames after the I-frame | NE vs GPU | NE vs CPU |
|---|---|---|
| 0 | 60.58 / 59.58 | 52.64 / 51.39 |
| 1–15 | 57.63 / 51.90 | 51.74 / 48.92 |
| 16–31 | 52.86 / 42.73 | 49.63 / 44.70 |
| 32–47 | 49.93 / 39.52 | 47.57 / 40.42 |
| 48–63 | 47.80 / 38.46 | 46.07 / 39.51 |
| All | 52.13 / 38.46 | 48.78 / 39.51 |

**Reading.**
- Decoding on another processor is possible, but the error builds up until the next I-frame, down to 38.5 dB in the worst frame.
- Moving the decoder to the GPU therefore needs a bound on drift, such as a shorter I-frame period.

## Conclusion

Decoding is correct on every processor and bit-for-bit deterministic on the NE. A decoder on the GPU or CPU drifts away from the NE picture until the next I-frame, down to 38.5 dB in the worst frame. Moving the **decoder** off the NE therefore needs a drift bound (for example a shorter I-frame period); moving the **encoder** does not cause drift. This is why the best split placements in `09_placement_experiment` keep the decoder on the NE.
