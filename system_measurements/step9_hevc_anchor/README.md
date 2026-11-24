# Step 9 — HEVC anchor: is a learned codec worth it against the Mac's own hardware HEVC?

**Question.** Every Mac has a hardware HEVC encoder and decoder (Apple VideoToolbox, in dedicated video blocks of the chip). A learned codec on the NE only makes sense for calls if it beats that at equal bitrate, or costs little enough energy to justify itself. Experiment 05 compared B\* with Intel's hardware HEVC encoder in an offline file mode; this experiment uses the real-time hardware encoder on the measurement laptop itself, at MLVC's own bitrates, with the same metrics as baseline experiment 10 and, in a second part, the energy of a two-way call measured over the same chip blocks.

## What was run

### Part A — quality (22 Nov 2026, 21:01–21:06 (+04), normal use)

- **Encoder:** `hevc_videotoolbox` through ffmpeg 9.0.2, **hardware only** (`-allow_sw 0`), real-time mode (`-realtime 1`), no B-frames (`-bf 0`), an I-frame every 64 frames (`-g 64`, as B\*), average bitrate (`-b:v`). Decoder: ffmpeg's HEVC decoder (bit-exact by the standard).
- **Targets:** for each clip, MLVC's own bitrates for that clip at QP 16/24/26/32/40 from baseline experiment 10: at 360p those of B\*, at 720p those of MLVC-S 720p. 20 evaluation clips × 2 sizes × 5 targets = 200 runs.
- **Inputs and metrics:** exactly baseline experiment 10's (Lanczos input from the 1080p MP4; coded PSNR-Y on all frames; display PSNR-Y, face PSNR-Y and face LPIPS on every 10th frame), through the same code (`q.py`), with the MLVC encode and decode replaced. BD-rate (PCHIP on log rate, overlapping range only) of HEVC against B\* at 360p, and against MLVC-S 720p and full MLVC 720p at 720p.

### Part B — energy (quiet mode, scheduled for the night of 22–23 Nov)

A paced 30 fps two-way call for 60 s (camera encoded and incoming stream decoded at the same time, same clips as baseline experiments 03 and 09): hardware HEVC at 360p (287 kbps, B\*'s rate) and 720p (847 kbps, MLVC-S 720p's rate), B\*, MLVC-S 540p (NE–NE) and MLVC-S 720p (GPU–NE), 5 interleaved rounds, 120 s idle at the start and the end. Energy is read from the chip's own counters (IOReport "Energy Model": CPU, GPU, NE, DRAM and the video encoder/decoder blocks, which powermetrics does not report), so the HEVC and MLVC calls are measured over the same parts of the chip. Results will be added here.

## How to run

The scripts live in `~/Downloads/d/hv/` (Part A; they use baseline experiment 10's `q.py` and `ana.py` from `../4b/`) and `~/Downloads/d/he/` (Part B, from `scripts/energy/`).

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/all` | Hardware-encoder test, a 2-run check, the 200 runs, then `hvana.py` | ≈ 10 min | any; resumable |
| `scripts/hv.py`, `scripts/hvana.py` | The runs; BD-rate on 4 metrics, mean curves and per clip, bitrate accuracy | — | — |
| `scripts/energy/all` | Builds `ioe` (energy counters, no password), the hardware HEVC streams, 25 runs + 2 idle recordings, then `heana.py` | ≈ 70 min | **quiet**; resumable |
| `scripts/energy/ioe.c`, `heana.py` | Energy-counter logger; energy per frame pair per chip block | — | — |

## Files

| Path | Contents |
|---|---|
| `raw_data/q.csv`, `raw_data/faces.csv`, `raw_data/frames/` | As baseline experiment 10, one row per size × clip × target (column `qp` = the MLVC QP whose bitrate was the target; `enc_resolved` holds the target in kbps) |
| `raw_data/ffmpeg_version.txt`, `raw_data/logs/` | ffmpeg version; console log |
| `results/rd_mean.csv`, `bd.csv`, `summary.txt` | Mean rate–distortion per size and target; BD-rate of HEVC against MLVC |

## Results (Part A, quality)

**The hardware encoder cannot reach MLVC's lowest bitrates.** It stays close at the higher targets (+5–8 % at MLVC's QP 16, +10–20 % at QP 24–26) but has a floor of about 115 kbps at 360p and 350 kbps at 720p, overshooting MLVC's QP 40 rate by 2–3×. The BD-rates use only the range where the curves overlap.

**BD-rate of hardware HEVC against MLVC** (positive = HEVC needs more bits for the same quality; in brackets the per-clip median and the clips where HEVC wins):

| Comparison | coded PSNR-Y | display PSNR-Y | face PSNR-Y | face LPIPS |
|---|---|---|---|---|
| HEVC 360p vs B\* (full MLVC 360p) | **+68.9 %** (+91.6, 2/20) | +98.1 % (+105.2, 1/20) | +102.9 % (+103.2, 0/20) | +70.7 % (+69.0, 1/20) |
| HEVC 720p vs MLVC-S 720p | +62.1 % (+68.1, 2/20) | +78.3 % (+82.1, 2/20) | +81.3 % (+77.4, 0/20) | **−1.2 %** (−6.7, 11/20) |
| HEVC 720p vs full MLVC 720p | +113.6 % (+120.4, 0/20) | +135.7 % (+140.3, 0/20) | +131.0 % (+136.4, 0/20) | +19.0 % (+13.7, 7/20) |

At B\*'s QP 26 rate (170 kbps target) HEVC delivers 204 kbps at 37.20 dB coded PSNR-Y, against B\*'s 38.64 dB at 170 kbps.

## Conclusion (Part A)

1. **In a real-time call setting, MLVC needs far fewer bits than the Mac's hardware HEVC**: B\* saves about 40 % of the bits on coded PSNR (HEVC +69 %) and about half on display and face PSNR. Full MLVC 720p needs less than half of HEVC's bits. This is a larger margin than baseline experiment 05's −31 % against Intel's offline hardware HEVC, most likely because a call needs the real-time mode without B-frames, the least efficient way to run a hardware encoder.
2. **On perceptual face quality the gap closes for MLVC-S:** at 720p hardware HEVC matches MLVC-S on face LPIPS (−1.2 %, 11 of 20 clips), while full MLVC 720p keeps a 19 % lead.
3. **Hardware HEVC cannot go as low as MLVC:** below about 115 kbps (360p) it overshoots its target, so for very low-bitrate calls MLVC is the only option of the two.
4. Whether MLVC's bit saving is worth its energy is Part B's question (pending).
