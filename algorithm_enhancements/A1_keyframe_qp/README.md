# A1 — More bits for key frames (QP offset on I-frames and LTR frames), with E4

**Question.** Every later frame is predicted from the I-frame (and, where they are used, from long-term reference frames, LTRs), so their quality carries forward. Classical codecs give these frames a lower QP. MLVC has a fixed built-in QP pattern that does not know which frames are I-frames or LTRs, and our own proposal assumed "the key frame is coded at full quality" without testing it. **Does a lower QP on I-frames and LTR frames save bits at the same quality?** This is the first codec-level mechanism (A1); it changes how MLVC spends bits, with no retraining and no change to the decoder (each frame header carries its QP).

Two rounds: round 1 tested offsets on B\*; round 2 went further on B\*, repeated the test on MLVC-S (which, unlike B\*, marks LTR frames), and combined A1 with A2's drift bound (**E4**: does a key-frame offset win back part of the bound's cost?).

## What was run (round 1)

**22 Nov 2026, 8:14–9:01 pm (+04)**, MacBook Pro 14-inch M4 Pro, macOS 26.6.2 (25G83), normal use (quality only).

- **Setting:** B\* (full MLVC 360p, encoder and decoder on the NE, an I-frame every 64 frames), the 20 evaluation clips, QP 16/24/26/32/40, with exactly the inputs and metrics of baseline experiment 10 (coded PSNR-Y/YUV on all frames; display PSNR-Y, face PSNR-Y and face LPIPS on every 10th frame).
- **Six configurations** (QP offset on I-frames / on the other LTR-marked frames): `o0` 0 / 0 (control); `b2`, `b4`, `b6` −2, −4, −6 on both; `i4` −4 on I-frames only; `l4` −4 on LTR frames only. 600 runs.
- **How:** the measurement program (`scripts/duplex_bench.cpp`, built separately as `harness_a1`, the baseline's program is not touched) sets the QP of every frame (`EncodeParams.qp`). Before each frame it asks libmlvc for the frame's type (`GetNextFrameInfo`) and works out whether libmlvc will mark it as an LTR with libmlvc's own internal marking rule. A per-frame log (`raw_data/flog/`) records index, type, LTR flag, QP and size.
- **Checks before the runs:** with no offset the bitstreams are byte-identical to baseline experiment 10's (**99 of 99**); every predicted frame type matched the type libmlvc produced (the program stops otherwise). libmlvc's trace log does not print LTR marking in this build, so the LTR prediction could not be checked against it; in B\* there are no LTRs to predict (below).

## What was run (round 2 and E4)

**24 Nov 2026, 4:43–5:57 pm (+04)**, same laptop, same inputs and metrics, 1,000 runs (10 configurations × 20 clips × 5 QPs). The measurement program was rebuilt with two more options (`--force-idr` for [A3](../A3_forced_keyframe/), and `--ltr-period` / `--ltr-recovery-period` / `--ltr-start-idx` to override the LTR structure); with no option set it is byte-identical to round 1 (check: MLVC-S 540p without offset gives baseline experiment 10's bitstreams, **99 of 99**).

| Model | Name | Offset on I-frames / LTR frames | LTR structure |
|---|---|---|---|
| B\* (full MLVC 360p) | `i8`, `i10` | −8 / 0, −10 / 0 (round 1 was still gaining at −6) | none (default) |
| MLVC-S 540p, NE–NE | `o0` | 0 / 0 (reference) | default: an LTR every 16 frames, never referenced before the next I-frame |
| | `i4`, `l4`, `b4`, `i8` | −4 / 0, 0 / −4, −4 / −4, −8 / 0 | default |
| | `r0` | 0 / 0 | **A2's drift bound:** LTR recovery every 32 frames (`--ltr-period 16 --ltr-recovery-period 2`) |
| | `rl4`, `rb4` | 0 / −4, −4 / −4 | the same bound |

B\*'s new offsets are compared with round 1's `o0`; MLVC-S's with its own `o0`; `rl4` and `rb4` with `r0` (what the offset wins back inside the bound) and with `o0` (the net cost of the bound).

## How to run

The scripts live in `~/Downloads/d/a1/` (they use baseline experiment 10's `quality_runner.py` and `quality_tables.py` from `../4b/`). Normal Mac, charger in, lid open; resumable.

| Script | What | Time |
|---|---|---|
| `scripts/a1_round1_runs.sh` | Builds `harness_a1` from `duplex_bench.cpp`, the checks, the 600 runs (2 passes), the analysis | ≈ 50 min |
| `scripts/a1.py` | The runs (`check` = first clip, QP 26, `o0` and `b4`) | — |
| `scripts/a1ana.py` | Mean rate–distortion, BD-rate against `o0` (mean curves and per clip), share of the bits per frame role | 1 min |
| `scripts/duplex_bench.cpp` | The measurement program with `--qp-i-offset`, `--qp-ltr-offset`, `--frame-log` (all modes), and since round 2 `--force-idr`, `--ltr-period`, `--ltr-recovery-period`, `--ltr-start-idx` | — |
| `scripts/a1_round2_runs.sh` | Round 2 and E4: check (MLVC-S `o0` identical to baseline experiment 10), the 1,000 runs (2 passes), the analysis | ≈ 75 min |
| `scripts/a1b.py`, `scripts/a1bana.py` | Round 2 runs; BD-rate of every comparison (mean curves and per clip) | — |

Output: `~/Downloads/duplexnvc-baseline/phase2/a1/` (round 1) and `phase2/a1b/` (round 2). Round 2 needs the program built by A3's `a3_runs.sh` (it rebuilds `harness_a1` when `duplex_bench.cpp` changes).

### Script names

The scripts were renamed from short names to descriptive ones after the runs; the code is unchanged apart from the names it calls and the log it writes. The console logs in `raw_data/` were recorded before the rename and keep the old names (`out_<old name>.txt`).

| Old name | New name | Console log written now |
|---|---|---|
| `scripts/all` | `scripts/a1_round1_runs.sh` | `out_a1_round1_runs.txt` |
| `scripts/allb` | `scripts/a1_round2_runs.sh` | `out_a1_round2_runs.txt` |

## Files

| Path | Contents |
|---|---|
| `raw_data/q.csv`, `raw_data/faces.csv` | One row per configuration × clip × QP (as baseline experiment 10), one row per scored face |
| `raw_data/flog/<cfg>/<clip>_qp<QP>.csv` | Per frame: index, type, LTR flag, QP used, bytes |
| `raw_data/frames/` | Per-frame PSNR of every run |
| `raw_data/logs/` | Console log, build log |
| `results/rd_mean.csv`, `bd.csv`, `summary.txt` | Round 1: mean rate–distortion per configuration and QP; BD-rate of every offset (4 metrics, mean curves and per clip) |
| `raw_data/round2/` | Round 2: `q.csv`, `faces.csv`, `flog/`, `frames/` as above; `logs/out_allb.txt` (console) |
| `results/round2/bd.csv`, `summary.txt` | Round 2 and E4: BD-rate of every comparison |

## Results (round 1)

**B\* has no LTR frames.** The default encoder configuration of every full MLVC model has LTR marking switched off (LTR period 0, see baseline experiment 11), so in B\* the only key frames are the I-frames (5 per 300-frame clip). The "LTR" part of A1 therefore had nothing to act on: `l4` is identical to `o0`, and `b4` is identical to `i4`.

**BD-rate against no offset** (negative = fewer bits for the same quality; in brackets the per-clip median and the clips that gain):

| Offset on I-frames | coded PSNR-Y | display PSNR-Y | face PSNR-Y | face LPIPS |
|---|---|---|---|---|
| −2 | −0.95 % (−0.74, 19/20) | −1.39 % (−1.27, 20/20) | −0.96 % (−0.72, 17/20) | −1.23 % (−1.28, 16/20) |
| −4 | −1.10 % (−0.66, 17/20) | −1.74 % (−1.46, 19/20) | −1.17 % (−0.95, 13/20) | −2.60 % (−2.49, 18/20) |
| −6 | −1.29 % (−0.62, 14/20) | −2.21 % (−1.87, 17/20) | −1.32 % (−0.65, 14/20) | −3.54 % (−3.07, 18/20) |
| LTR frames only, −4 | 0 | 0 | 0 | 0 |

**Where the bits go** (QP 26): I-frames take 20.8 % of the bits with no offset, 24.0 / 28.0 / 31.4 % at −2 / −4 / −6.

**At QP 16 every offset gives the same result as no offset**: QP 16 is already at the top of the model's QP table, so a lower QP on the I-frame changes nothing. The BD-rates come from QP 24–40.

## Results (round 2 and E4)

**BD-rate** (negative = fewer bits for the same quality; in brackets the per-clip median and the clips that gain):

| Comparison | coded PSNR-Y | display PSNR-Y | face PSNR-Y | face LPIPS |
|---|---|---|---|---|
| B\*: I-frames −6 (round 1) | −1.29 % (−0.62, 14/20) | −2.21 % (−1.87, 17/20) | −1.32 % (−0.65, 14/20) | −3.54 % (−3.07, 18/20) |
| B\*: I-frames −8 | −1.20 % (−0.36, 12/20) | −2.22 % (−1.60, 14/20) | −1.29 % (−0.14, 10/20) | **−5.91 %** (−5.10, 20/20) |
| B\*: I-frames −10 | −0.25 % (+0.54, 8/20) | −1.15 % (−0.45, 11/20) | −0.16 % (+1.69, 9/20) | −7.02 % (−6.02, 18/20) |
| MLVC-S 540p: I-frames −4 | −2.05 % (−2.08, 20/20) | −2.61 % (−2.73, 20/20) | −1.89 % (−1.79, 19/20) | −3.63 % (−3.28, 18/20) |
| MLVC-S 540p: **I-frames −8** | **−2.60 %** (−2.54, 17/20) | **−3.47 %** (−3.35, 18/20) | **−2.44 %** (−2.28, 19/20) | **−5.85 %** (−5.37, 20/20) |
| MLVC-S 540p: LTR frames −4 | +0.68 % (+0.89, 0/20) | +0.11 % (+0.59, 4/20) | +0.12 % (+0.33, 5/20) | +0.78 % (+0.93, 5/20) |
| MLVC-S 540p: both −4 | −1.61 % (−1.27, 17/20) | −2.82 % (−2.36, 20/20) | −1.86 % (−1.82, 17/20) | −3.39 % (−2.84, 18/20) |
| **E4:** the drift bound (`r0` vs `o0`) | +9.65 % (+8.21, 0/20) | +9.79 % (+7.83, 0/20) | +12.04 % (+11.06, 0/20) | +13.05 % (+11.80, 0/20) |
| E4: bound + LTR −4, vs the bound | +0.88 % (+1.17, 1/20) | +0.31 % (+0.79, 6/20) | +0.34 % (+0.80, 6/20) | +1.15 % (+1.50, 5/20) |
| E4: bound + both −4, vs the bound | −1.88 % (−1.52, 18/20) | −3.12 % (−2.63, 20/20) | −2.13 % (−2.06, 17/20) | −2.97 % (−2.45, 18/20) |
| E4: bound + both −4, vs `o0` (net) | +7.73 % (+7.18, 0/20) | +6.54 % (+5.91, 0/20) | +9.90 % (+10.24, 0/20) | +9.93 % (+10.56, 1/20) |

- **B\* peaks between −6 and −8.** Beyond −8 the coded and face PSNR gains fall away (−10: −0.25 %, and most clips lose on PSNR), while face LPIPS keeps improving; −8 keeps the PSNR gain of −6 and adds 2.4 points of LPIPS.
- **MLVC-S gains more than B\*** from the same offset (−2.6 % vs −1.2 % coded at −8), and almost every clip gains.
- **Lower QP on LTR frames does not pay,** not even inside the drift bound, where every second LTR is used as a reference: +0.7 % alone, +0.9 % inside the bound. The I-frame offset alone does better than both offsets together.
- **E4 cross-check:** the drift bound costs +9.65 %, the same as baseline experiment 11 measured independently for the same structure (+9.6 %).

## Conclusion (round 1)

1. **More bits for the I-frame pay off, a little.** At −6 the same quality needs 1.3 % fewer bits on coded PSNR, 2.2 % on display PSNR and 3.5 % on face LPIPS, and most clips gain. The gain grows with the offset and has not peaked at −6, so larger offsets are worth testing.
2. **The proposal's "key frame coded at full quality" is not what MLVC does,** and spending more on it is a small, real improvement, with no change to the decoder.
3. **The LTR half of A1 needs a structure that uses LTRs.** B\* has none, and MLVC-S marks LTRs but never predicts from them before the next I-frame (baseline experiment 11). A1 on LTR frames is therefore only meaningful together with LTR recovery (A2's drift bound) or content-adaptive LTRs (A4); that combination was tested in round 2 (E4, below).

## Conclusion (round 2 and E4)

1. **The I-frame offset is the useful half of A1:** −8 on I-frames saves 1.2 % (B\*) to 2.6 % (MLVC-S 540p) of the bits on coded PSNR and about 6 % on face LPIPS, with no decoder change. Offsets beyond −8 trade PSNR for LPIPS.
2. **The LTR half of A1 does not help MLVC,** with or without a structure that uses the LTRs. The extra bits on an LTR do not come back as better prediction.
3. **E4: A1 pays back about a fifth of A2's drift bound.** With the bound, an I-frame offset recovers 1.9–3.1 %, bringing the bound's net cost from +9.7 % to +7.7 % (coded PSNR). For the controller, the bound should always be paired with the I-frame offset.
