# 13 — A1 experiment: more bits for key frames (QP offset on I-frames and LTR frames)

**Question.** Every later frame is predicted from the I-frame (and, where they are used, from long-term reference frames, LTRs), so their quality carries forward. Classical codecs give these frames a lower QP. MLVC has a fixed built-in QP pattern that does not know which frames are I-frames or LTRs, and our own proposal assumed "the key frame is coded at full quality" without testing it. **Does a lower QP on I-frames and LTR frames save bits at the same quality?** This is the first codec-level mechanism (A1); it changes how MLVC spends bits, with no retraining and no change to the decoder (each frame header carries its QP).

## What was run

**22 Nov 2026, 20:14–21:01 (+04)**, MacBook Pro 14-inch M4 Pro, macOS 26.6.2 (25G83), normal use (quality only).

- **Setting:** B\* (full MLVC 360p, encoder and decoder on the NE, an I-frame every 64 frames), the 20 evaluation clips, QP 16/24/26/32/40, with exactly the inputs and metrics of experiment 10 (coded PSNR-Y/YUV on all frames; display PSNR-Y, face PSNR-Y and face LPIPS on every 10th frame).
- **Six configurations** (QP offset on I-frames / on the other LTR-marked frames): `o0` 0 / 0 (control); `b2`, `b4`, `b6` −2, −4, −6 on both; `i4` −4 on I-frames only; `l4` −4 on LTR frames only. 600 runs.
- **How:** the measurement program (`scripts/duplex_bench.cpp`, built separately as `harness_a1`, the baseline's program is not touched) sets the QP of every frame (`EncodeParams.qp`). Before each frame it asks libmlvc for the frame's type (`GetNextFrameInfo`) and works out whether libmlvc will mark it as an LTR with libmlvc's own internal marking rule. A per-frame log (`raw_data/flog/`) records index, type, LTR flag, QP and size.
- **Checks before the runs:** with no offset the bitstreams are byte-identical to experiment 10's (**99 of 99**); every predicted frame type matched the type libmlvc produced (the program stops otherwise). libmlvc's trace log does not print LTR marking in this build, so the LTR prediction could not be checked against it; in B\* there are no LTRs to predict (below).

## How to run

The scripts live in `~/Downloads/d/a1/` (they use experiment 10's `q.py` and `ana.py` from `../4b/`). Normal Mac, charger in, lid open; resumable.

| Script | What | Time |
|---|---|---|
| `scripts/all` | Builds `harness_a1` from `duplex_bench.cpp`, the checks, the 600 runs (2 passes), the analysis | ≈ 50 min |
| `scripts/a1.py` | The runs (`check` = first clip, QP 26, `o0` and `b4`) | — |
| `scripts/a1ana.py` | Mean rate–distortion, BD-rate against `o0` (mean curves and per clip), share of the bits per frame role | 1 min |
| `scripts/duplex_bench.cpp` | The measurement program with `--qp-i-offset`, `--qp-ltr-offset` and `--frame-log` (all modes) | — |

Output: `~/Downloads/duplexnvc-baseline/phase2/a1/`.

## Files

| Path | Contents |
|---|---|
| `raw_data/q.csv`, `raw_data/faces.csv` | One row per configuration × clip × QP (as experiment 10), one row per scored face |
| `raw_data/flog/<cfg>/<clip>_qp<QP>.csv` | Per frame: index, type, LTR flag, QP used, bytes |
| `raw_data/frames/` | Per-frame PSNR of every run |
| `raw_data/logs/` | Console log, build log |
| `results/rd_mean.csv`, `bd.csv`, `summary.txt` | Mean rate–distortion per configuration and QP; BD-rate of every offset (4 metrics, mean curves and per clip) |

## Results

**B\* has no LTR frames.** The default encoder configuration of every full MLVC model has LTR marking switched off (LTR period 0, see experiment 11), so in B\* the only key frames are the I-frames (5 per 300-frame clip). The "LTR" part of A1 therefore had nothing to act on: `l4` is identical to `o0`, and `b4` is identical to `i4`.

**BD-rate against no offset** (negative = fewer bits for the same quality; in brackets the per-clip median and the clips that gain):

| Offset on I-frames | coded PSNR-Y | display PSNR-Y | face PSNR-Y | face LPIPS |
|---|---|---|---|---|
| −2 | −0.95 % (−0.74, 19/20) | −1.39 % (−1.27, 20/20) | −0.96 % (−0.72, 17/20) | −1.23 % (−1.28, 16/20) |
| −4 | −1.10 % (−0.66, 17/20) | −1.74 % (−1.46, 19/20) | −1.17 % (−0.95, 13/20) | −2.60 % (−2.49, 18/20) |
| −6 | −1.29 % (−0.62, 14/20) | −2.21 % (−1.87, 17/20) | −1.32 % (−0.65, 14/20) | −3.54 % (−3.07, 18/20) |
| LTR frames only, −4 | 0 | 0 | 0 | 0 |

**Where the bits go** (QP 26): I-frames take 20.8 % of the bits with no offset, 24.0 / 28.0 / 31.4 % at −2 / −4 / −6.

**At QP 16 every offset gives the same result as no offset**: QP 16 is already at the top of the model's QP table, so a lower QP on the I-frame changes nothing. The BD-rates come from QP 24–40.

## Conclusion

1. **More bits for the I-frame pay off, a little.** At −6 the same quality needs 1.3 % fewer bits on coded PSNR, 2.2 % on display PSNR and 3.5 % on face LPIPS, and most clips gain. The gain grows with the offset and has not peaked at −6, so larger offsets are worth testing.
2. **The proposal's "key frame coded at full quality" is not what MLVC does,** and spending more on it is a small, real improvement, with no change to the decoder.
3. **The LTR half of A1 needs a structure that uses LTRs.** B\* has none, and MLVC-S marks LTRs but never predicts from them before the next I-frame (experiment 11). A1 on LTR frames is therefore only meaningful together with LTR recovery (A2's drift bound) or content-adaptive LTRs (A4); that combination is the next test (E4).
