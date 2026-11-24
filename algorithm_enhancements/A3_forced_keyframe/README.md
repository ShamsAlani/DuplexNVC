# A3 — A forced key frame when the content changes

**Question.** MLVC sends an I-frame every 64 frames, whatever happens in the picture. When people join or leave a call, the frames the encoder predicts from no longer match the scene until the next scheduled I-frame. Classical encoders insert a key frame at a scene change, and our proposal planned the same for DuplexNVC's controller (mechanism A3), triggered by the scene analyzer. **Does a key frame forced at a content change save bits or improve the picture, and does it matter which trigger fires it?** Like A1, this changes how MLVC codes the stream, with no retraining and no change to the decoder.

## What was run

**24 Nov 2026, 4:14–4:43 pm (+04)**, MacBook Pro 14-inch M4 Pro, macOS 26.6.2 (25G83), normal use (quality only), 440 runs.

- **Clips:** the 11 stock multi-person clips of Step 8 ([`controller_data/`](../../controller_data/)): 3 HEVC Class E clips (720p masters) and 8 Pexels clips (1080p masters), 300 frames each. 4 of them contain real events (people entering or leaving, 8 events in all, marked by hand in Step 8); the other 7 have none.
- **Settings:** B\* (full MLVC 360p, NE–NE) and MLVC-S 540p (NE–NE), QP 16/24/26/32/40.
- **Four trigger policies:**

| Policy | When a key frame is forced |
|---|---|
| `none` | Never (MLVC's default: an I-frame every 64 frames) |
| `truth` | At every real event marked in Step 8 (`events_truth.csv`): an oracle, the best any trigger could do |
| `fused` | Step 8's best detector: people = max(participant faces, bodies) on every 10th frame; a new count that holds for 3 labelled frames (1 s) is an event, and the key frame is forced when it is confirmed |
| `diff` | Frame difference: mean absolute luma difference (360p, 0–255) between the frame and the last key frame above 6, at least 30 frames after it (a trigger with no detector) |

- **How:** the measurement program of [A1](../A1_keyframe_qp/) with a new option `--force-idr <file>`: before each listed frame it asks libmlvc for an I-frame (`EncodeParams.forceIdr`); the 64-frame period restarts from it. A per-frame log records type, QP, size and whether the frame was forced.
- **Metrics:** as baseline experiment 10 (coded PSNR-Y on every frame; display PSNR-Y, face PSNR-Y and face LPIPS on every 10th frame against the 1080p originals; the 720p Class E masters are upscaled losslessly to 1080p for the display metrics). BD-rate of each policy against `none`. **Cost of a switch** at QP 26: size of each forced I-frame against the mean of the 10 P-frames before it, and the coded PSNR-Y in the 30 frames after each real event compared with `none`.
- **Check before the runs:** one clip, QP 26, all 8 combinations; the `none` runs contain no forced frame.

## How to run

The scripts live in `~/Downloads/d/a3/`; they use baseline experiment 10's `q.py` and `ana.py` (`../4b/`), the measurement program source in `../a1/duplex_bench.cpp` (A1) and the Step 8 data in `data/`. Normal Mac, charger in, lid open; resumable.

| Script | What | Time |
|---|---|---|
| `scripts/all` | Rebuilds the measurement program if its source changed, finds the Step 8 masters in `~/Downloads`, the check, the 440 runs (2 passes), the analysis | ≈ 30 min |
| `scripts/a3.py` | Stages the masters, works out the triggers per clip, the runs (`a3.py <masters folder> [check]`) | — |
| `scripts/a3ana.py` | BD-rate per setting, clip group and policy; cost of a switch | 1 min |

Output: `~/Downloads/duplexnvc-baseline/phase2/a3/`.

## Files

| Path | Contents |
|---|---|
| `raw_data/data/` | The Step 8 inputs used (events marked by hand, faces and bodies per labelled frame); identical to the stock-clip rows in `controller_data/` |
| `raw_data/trig/<clip>_<policy>.txt` | Frames where a key frame was forced |
| `raw_data/q.csv`, `faces.csv`, `flog/`, `frames/` | One row per setting × policy × clip × QP; scored faces; per-frame log (type, QP, bytes, forced); per-frame PSNR |
| `raw_data/logs/` | Console log, build log |
| `results/bd.csv`, `switch_cost.csv`, `summary.txt` | BD-rate per setting × group × policy (4 metrics, mean curves and per clip); cost of a switch |

## Results

**Forced key frames per policy:** `truth` 8 (on the 4 clips with events), `fused` 11 (9 on the clips with events, at other frames than the marked ones because it fires when a new count is confirmed, and 2 on clips with no marked event), `diff` 80 (every 30 frames on clips with camera or crowd motion, including all 7 clips without events).

**BD-rate against no forced key frame** (positive = more bits for the same quality; in brackets the per-clip median and the clips that gain):

| Setting | Policy | coded PSNR-Y | display PSNR-Y | face PSNR-Y | face LPIPS |
|---|---|---|---|---|---|
| B\* | `truth` | +1.56 % (+0.00, 1/11) | +3.10 % (0/11) | +2.24 % (1/11) | +3.73 % (1/11) |
| | `fused` | +2.66 % (0/11) | +4.93 % (0/11) | +4.39 % (0/11) | +4.72 % (0/11) |
| | `diff` | **+29.28 %** (+31.87, 0/11) | +45.94 % (0/11) | +33.40 % (0/11) | +36.48 % (1/11) |
| MLVC-S 540p | `truth` | +1.83 % (0/11) | +3.18 % (0/11) | +2.17 % (1/11) | +4.60 % (1/11) |
| | `fused` | +2.88 % (0/11) | +4.60 % (0/11) | +2.88 % (0/11) | +5.18 % (0/11) |
| | `diff` | +26.60 % (+27.75, 0/11) | +40.71 % (0/11) | +30.91 % (0/11) | +31.27 % (0/11) |

On the 4 clips with real events alone, the oracle costs +3.6 % (B\*) and +4.1 % (MLVC-S) on coded PSNR and about +10 % on face LPIPS; on the 7 clips without events `truth` changes nothing and `fused` costs +1.3 %.

**Cost of a switch (QP 26):**

| Setting | Policy | Forced | Forced I-frame size (× a P-frame) | Coded PSNR-Y in the 30 frames after a real event |
|---|---|---|---|---|
| B\* | `truth` | 8 | 15.0× | −0.06 dB |
| | `fused` | 11 | 12.4× | +0.03 dB |
| | `diff` | 80 | 14.6× | −0.00 dB |
| MLVC-S 540p | `truth` | 8 | 11.9× | −0.08 dB |
| | `fused` | 11 | 10.6× | +0.02 dB |
| | `diff` | 80 | 11.2× | −0.00 dB |

## Conclusion

1. **A key frame at a content change does not pay in MLVC, even with a perfect trigger.** Each forced I-frame costs 11–15 P-frames' worth of bits, and the picture after the event is no better (within ±0.1 dB): MLVC's P-frames already handle people joining or leaving. The oracle costs +1.6–1.8 % overall and about +4 % on the clips with events.
2. **A naive trigger is expensive:** the frame-difference rule fires on ordinary motion and costs +27–29 %. The detector-based rule costs little more than the oracle (+2.7–2.9 %) because it fires rarely, but it brings nothing either.
3. **For the controller:** scene events should change the **setting** (resolution, placement, model), not force key frames. This drops A3 as a bit-saving mechanism; a forced key frame remains useful only where the stream must restart anyway (a setting switch, a lost packet). These clips are 10 s stock clips; the recorded call clips of Step 8 can repeat the test with real call events.
