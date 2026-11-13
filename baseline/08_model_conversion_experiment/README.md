# 08 — Model conversion experiment: new models and inputs (X2)

**Question.** Can full MLVC and MLVC-S be converted for every resolution of the survey, do all their operations run on the NE, and what do their input streams look like?

**What was run.**
- **Conversion** with `mlvc-tools` (`convert.py bundle`, Core ML, fp16), with the public PSNR weights: full MLVC (`mlvc-psnr-v1.ckpt`) at 540p, 720p and 1080p; MLVC-S (`mlvc-s-psnr-v1.ckpt`, SHA-256 starting `1b86b757`) at 540p, 720p and 1080p; plus one full-MLVC bundle holding all four sizes, to test whether a multi-size bundle is as fast. Model inputs are padded to a multiple of 16 (960×544, 1280×720, 1920×1088). MLVC-S uses PSNR weights in every row so full MLVC and MLVC-S share one training objective.
- **Placement trace** of every new network (as in `07_processor_experiment`).
- **Streams** at each resolution from the same four clips as B\* (Lanczos from the 1080p releases, 600 frames, NV12), and the incoming stream of each setting encoded once at QP 26 (I-frame every 64) on the NE and decoded again as a check.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/2a` | Downloads the MLVC-S PSNR weights, builds the converter's test clips, converts the 7 bundles, traces each network | 30–45 min | Wi-Fi **on** (one download) |
| `scripts/2b` | Camera and incoming streams per resolution, incoming at QP 26, decode check | 15 min, ≈ 7 GB | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/logs/out_2a.txt` | Conversion and trace log |
| `raw_data/logs/out_2b.txt` | Stream preparation, bitrate and PSNR of each incoming stream |

The bundles and streams themselves are rebuilt by the scripts (they are too large to ship).

## Results

| Setting | Bundle size | Incoming bitrate at QP 26 | Incoming PSNR-Y |
|---|---|---|---|
| Full MLVC 360p (B\*) | — | 287 kbps | 34.98 dB |
| Full MLVC 540p | 36 MB | 539 kbps | 36.48 dB |
| Full MLVC 720p | 37 MB | 794 kbps | 37.76 dB |
| Full MLVC 1080p | 41 MB | 1438 kbps | 38.90 dB |
| MLVC-S 540p | 11 MB | 561 kbps | 35.59 dB |
| MLVC-S 720p | 12 MB | 847 kbps | 37.07 dB |
| MLVC-S 1080p | 13 MB | 1538 kbps | 38.43 dB |
| Full MLVC multi-size (360p–1080p) | 41 MB | — | — |

Every new network runs 100.0 % of its estimated cost on the NE.

## Conclusion

All seven settings of the survey are available and run entirely on the NE. Bitrate roughly doubles from 540p to 1080p for 2–3 dB more PSNR; MLVC-S needs 4–7 % more bits than full MLVC for 0.5–0.9 dB lower PSNR, the price of its smaller networks.
