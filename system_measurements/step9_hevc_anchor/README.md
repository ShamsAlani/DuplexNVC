# Step 9 — HEVC anchor: is a learned codec worth it against the Mac's own hardware HEVC?

**Question.** Every Mac has a hardware HEVC encoder and decoder (Apple VideoToolbox, in dedicated video blocks of the chip). A learned codec on the NE only makes sense for calls if it beats that at equal bitrate, or costs little enough energy to justify itself. Experiment 05 compared B\* with Intel's hardware HEVC encoder in an offline file mode; this experiment uses the real-time hardware encoder on the measurement laptop itself, at MLVC's own bitrates, with the same metrics as baseline experiment 10 and, in a second part, the energy of a two-way call measured over the same chip blocks.

## What was run

### Part A — quality (22 Nov 2026, 9:01–9:06 pm (+04), normal use)

- **Encoder:** `hevc_videotoolbox` through ffmpeg 9.0.2, **hardware only** (`-allow_sw 0`), real-time mode (`-realtime 1`), no B-frames (`-bf 0`), an I-frame every 64 frames (`-g 64`, as B\*), average bitrate (`-b:v`). Decoder: ffmpeg's HEVC decoder (bit-exact by the standard).
- **Targets:** for each clip, MLVC's own bitrates for that clip at QP 16/24/26/32/40 from baseline experiment 10: at 360p those of B\*, at 720p those of MLVC-S 720p. 20 evaluation clips × 2 sizes × 5 targets = 200 runs.
- **Inputs and metrics:** exactly baseline experiment 10's (Lanczos input from the 1080p MP4; coded PSNR-Y on all frames; display PSNR-Y, face PSNR-Y and face LPIPS on every 10th frame), through the same code (`quality_runner.py`), with the MLVC encode and decode replaced. BD-rate (PCHIP on log rate, overlapping range only) of HEVC against B\* at 360p, and against MLVC-S 720p and full MLVC 720p at 720p.

### Part B — energy (quiet mode; final run 25 Nov 2026, 2:37–3:50 am (+04))

A paced 30 fps two-way call for 60 s (camera encoded and incoming stream decoded at the same time, same clips as baseline experiments 03 and 09): hardware HEVC at 360p (287 kbps, B\*'s rate) and 720p (847 kbps, MLVC-S 720p's rate), B\*, MLVC-S 540p (NE–NE) and MLVC-S 720p (GPU–NE), 5 interleaved rounds (25 runs, 60 s rest after each), 120 s idle at the start and the end. Energy is read from the chip's own counters (IOReport "Energy Model": CPU, GPU, NE, DRAM and the video encoder/decoder blocks, which `powermetrics` does not report), so the HEVC and MLVC calls are measured over the same parts of the chip. Energy per frame pair = (mean power over the last 49 s of the call − idle power) / 30.

- **HEVC call:** the camera stream is encoded by `hevc_videotoolbox` (real time, `-bf 0`, `-g 64`, hardware only) while `ffmpeg -re -hwaccel videotoolbox` decodes the incoming stream at 30 fps. The incoming stream is an MP4 of 1800 frames (60 s) with 30 fps timestamps, encoded by the same hardware encoder from the incoming clips; the script checks with `ffprobe` that it holds 1800 frames at 30/1 and that every call decodes 1700–1900 frames.
- **MLVC calls:** the measurement program in duplex mode, paced at 30 fps, as baseline experiment 09.
- **Checks in the analysis (`heana.py`):** both idle recordings are printed by chip block; a run is excluded if it took more than 75 s or dropped more than 500 frames (the Mac stalled).

**How we got there (about 18 h of runs, three set aside).** The energy runs needed four attempts; only the fourth is used.

1. **23 Nov, 2:02 am – 4:17 pm (14.3 h).** The incoming stream was a raw `.hevc` file that ffmpeg did not loop: the decoder finished its 600 frames in 2 s instead of decoding for 60 s. A variable clash in the script (the loop counter `k` was overwritten inside the run function) then made the loop run empty conditions until it was stopped. *Fix:* local variables in the run function, a separate loop counter, and a guard that stops on an empty condition.
2. **24 Nov, 12:23 – 1:36 am (1.2 h).** The incoming stream was looped into an MP4 by remuxing the raw stream; its timestamps came out at about 350 fps, so the decoder decoded 21,050 frames in 60 s instead of 1800. *Fix:* the incoming stream is encoded straight to an MP4 of 1800 frames at 30 fps, checked with `ffprobe`, and every call must decode 1700–1900 frames or the run stops.
3. **24 Nov, 11:38 pm – 25 Nov, 1:22 am (1.7 h).** Calls were paced correctly, but no keep-awake was running after the preceding Step 6 run ended: the display went to sleep, background tasks ran on the CPU, GPU and NE (the closing idle recording read 1.6 W against 0.4 W at the start), and the Mac stalled for about 15 minutes twice (one B\* run took 955 s). *Fix:* the script keeps the display and the system awake for its whole run (`caffeinate -dims`), and the analysis prints both idle recordings and excludes stalled runs.
4. **25 Nov, 2:37 – 3:50 am (1.2 h): clean.** Both idle recordings agree (346 and 340 mW over the grouped blocks), every HEVC call decoded exactly 1800 frames at 30 fps, every MLVC run had no dropped frames and at most 0.03 % late frames, and no run was excluded.

The earlier attempts' folders are kept on the measurement laptop (`phase2/he_attempt1_failed`, `he_attempt2_unpaced`, `he_attempt3_display_sleep`); the console log of all four is in `raw_data/logs/energy/out_all.txt`.

## How to run

The scripts live in `~/Downloads/d/hv/` (Part A; they use baseline experiment 10's `quality_runner.py` and `quality_tables.py` from `../4b/`) and `~/Downloads/d/he/` (Part B, from `scripts/energy/`).

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/hevc_quality_runs.sh` | Hardware-encoder test, a 2-run check, the 200 runs, then `hvana.py` | ≈ 10 min | any; resumable |
| `scripts/hv.py`, `scripts/hvana.py` | The runs; BD-rate on 4 metrics, mean curves and per clip, bitrate accuracy | — | — |
| `scripts/energy/hevc_energy_runs.sh` | Builds `ioe` (energy counters, no password), the 30 fps incoming HEVC streams (checked with `ffprobe`), 25 runs + 2 idle recordings with the display kept awake, then `heana.py` | ≈ 75 min | **quiet**; resumable |
| `scripts/energy/ioe.c`, `heana.py` | Energy-counter logger; energy per frame pair per chip block, with both idle recordings printed and stalled runs excluded (`IDLE=start\|end\|mean` chooses the idle) | — | — |

### Script names

The scripts were renamed from short names to descriptive ones after the runs; the code is unchanged apart from the names it calls and the log it writes. The console logs in `raw_data/` were recorded before the rename and keep the old names (`out_<old name>.txt`).

| Old name | New name | Console log written now |
|---|---|---|
| `scripts/all` | `scripts/hevc_quality_runs.sh` | `out_hevc_quality_runs.txt` |
| `scripts/energy/all` | `scripts/energy/hevc_energy_runs.sh` | `out_hevc_energy_runs.txt` |

## Files

| Path | Contents |
|---|---|
| `raw_data/q.csv`, `raw_data/faces.csv`, `raw_data/frames/` | As baseline experiment 10, one row per size × clip × target (column `qp` = the MLVC QP whose bitrate was the target; `enc_resolved` holds the target in kbps) |
| `raw_data/ffmpeg_version.txt`, `raw_data/logs/out_all.txt` | ffmpeg version; console log of Part A |
| `raw_data/energy/<condition>/r1–r5/` | Part B, per run: `t.txt` (start and end time), `enc.log` and `dec.log` (HEVC: ffmpeg's frame counts), `frames.csv` and `run.txt` (MLVC: every frame's timing, dropped frames), `r<n>.log`, `r<n>.therm` (thermal state); `idle_start/`, `idle_end/`, `thermal.csv`. The video streams are left out |
| `raw_data/logs/energy/out_all.txt` | Console log of all four Part B attempts (the per-second energy-counter files stay on the measurement laptop) |
| `results/energy/energy.csv`, `summary.txt`, `channels.csv` | Energy per frame pair by condition and chip block (median and range of 5 runs); every counter channel, for checking the grouping |
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

## Results (Part B, energy)

**Energy per frame pair** (mJ, idle subtracted, median of 5 runs; range in brackets; 30 frame pairs per second, so 1 mJ per pair = 30 mW):

| Call | Total | CPU | GPU | NE | DRAM | Video blocks | Late frames |
|---|---|---|---|---|---|---|---|
| Hardware HEVC 360p, 287 kbps | **1.6** (1.4–1.7) | 0.4 | 0.0 | 0.0 | 0.6 | 0.6 | 0 (1800 of 1800 decoded) |
| B\* (full MLVC 360p, NE–NE) | **76.7** (76.6–76.8) | 1.0 | 0.0 | 62.9 | 12.8 | 0.0 | ≤ 0.03 % |
| MLVC-S 540p (NE–NE) | **52.5** (52.3–52.8) | 1.1 | 0.0 | 43.6 | 7.8 | 0.0 | 0 |
| Hardware HEVC 720p, 847 kbps | **2.6** (2.6–2.8) | 0.5 | 0.0 | 0.0 | 1.3 | 0.8 | 0 (1800 of 1800 decoded) |
| MLVC-S 720p (GPU–NE) | **739.2** (731.6–743.6) | 2.8 | 672.3 | 37.3 | 25.0 | 0.1 | ≤ 0.03 % |

- **B\* uses 48× the energy of hardware HEVC at 360p; MLVC-S 720p uses 284× hardware HEVC at 720p.** MLVC-S 540p, which beats B\* in quality (baseline experiment 10), uses 33× hardware HEVC at 360p.
- The runs are very repeatable (every range within 1 % for MLVC, 0.3 mJ for HEVC).
- **The meters agree with the baseline.** B\*'s NE energy here (62.9 mJ) matches the 63–65 mJ of baseline experiments 06 and 10, measured with `powermetrics`; the IOReport total is higher because it also counts the memory (12.8 mJ), which `powermetrics` does not report. On battery (Step 6, same counters) B\* used 76.8 mJ, the same as here.

## Conclusion

1. **In a real-time call setting, MLVC needs far fewer bits than the Mac's hardware HEVC**: B\* saves about 40 % of the bits on coded PSNR (HEVC +69 %) and about half on display and face PSNR. Full MLVC 720p needs less than half of HEVC's bits. This is a larger margin than baseline experiment 05's −31 % against Intel's offline hardware HEVC, most likely because a call needs the real-time mode without B-frames, the least efficient way to run a hardware encoder.
2. **On perceptual face quality the gap closes for MLVC-S:** at 720p hardware HEVC matches MLVC-S on face LPIPS (−1.2 %, 11 of 20 clips), while full MLVC 720p keeps a 19 % lead.
3. **Hardware HEVC cannot go as low as MLVC:** below about 115 kbps (360p) it overshoots its target, so for very low-bitrate calls MLVC is the only option of the two.
4. **The bit saving costs 33 to 284 times the energy.** The Mac's video blocks run a call for 1.6 mJ (360p) to 2.6 mJ (720p) per frame pair, about 50–80 mW; B\* needs 76.7 mJ (2.3 W) and MLVC-S 720p with its GPU encoder 739 mJ (22 W). MLVC-S 540p on the NE, the cheapest learned setting at 30 fps, still needs 52.5 mJ (1.6 W). On a laptop the learned codec is worth it only where bits matter far more than power: on a poor link, or below the roughly 115 kbps the hardware encoder cannot reach.
