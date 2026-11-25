# 10 — Quality per setting experiment: rate–distortion of all seven settings and energy vs quality (Step 4b)

**Question.**
1. What quality does each of the seven model/resolution settings give, at screen size and on faces, along its rate–distortion curve?
2. Does MLVC-S 540p beat B\* (full MLVC 360p) at screen size?
3. Is full MLVC 540p, at about 10× the energy of B\*, worth its quality?
4. Which settings are on the energy–quality Pareto front, at equal bitrate, and which of those meet 30 fps?

Experiment 05 measured quality at 360p only; experiment 09 measured timing and energy of every setting at QP 26 only. This experiment adds quality for the other six settings (Part A) and energy at every QP (Part B), so that settings can be compared at **equal bitrate**. libmlvc has no target-bitrate mode, only a QP per frame, so equal bitrate is reached by interpolating quality and energy along each setting's QP curve (decision D3).

## What was run

**Part A — quality (14 Nov 2026, 01:23–04:26, 900 runs, 0 failures, 3.0 h).** `scripts/quality_per_setting_runs.sh`, normal Mac use (quality does not depend on timing):

- **Clips:** the 20 evaluation clips of experiment 05 (VCD talking heads, scenario s1, seed 694), 300 frames each.
- **Input:** each clip's 1080p MP4 scaled with ffmpeg's Lanczos filter to the setting's size (640×360, 960×540, 1280×720, 1920×1080), as the streams of experiment 08. 360p was rerun from the MP4 as well; experiment 05 used the VCD 360p YUV files, kept as a cross-check.
- **Configurations (9):** all seven settings with encoder and decoder on the NE, plus full MLVC 540p and MLVC-S 720p with the encoder on the GPU and the decoder on the NE (their best placements in experiment 09).
- **QPs:** 16, 24, 26, 32, 40. QP 26 was added to the four QPs of experiment 05 because B\* and the energy of experiment 09 are at QP 26.
- **Per run:** encode with `libmlvc_example prepare` (I-frame every 64, `--enc-cu`), decode with `mlvc decode` (`--compute-unit`).
- **Metrics (same as experiment 05):**
  - coded PSNR-Y and PSNR-YUV ((6Y+U+V)/8) on all frames, against the encoder input;
  - display PSNR-Y on every 10th frame: decode upscaled with Lanczos (OpenCV) to 1920×1080, against the 1080p original (no resize at 1080p);
  - face PSNR-Y (faces ≥ 8 px) and LPIPS (AlexNet, faces ≥ 32 px) inside the Apple Vision face boxes found on the original, every 10th frame.
- **Equal bitrate:** PCHIP on log bitrate (the BD-rate convention), only where curves overlap, no extrapolation. BD-rate against B\* on display PSNR-Y, face PSNR-Y and face LPIPS.

**Part B — energy at every QP (19 Nov 2026, 01:20–09:03, 175 runs, 7.7 h).** `scripts/energy_per_qp_runs.sh`, quiet mode:

- **Configurations:** the best placement of each setting from experiment 09 (the points of the Pareto plot): full MLVC 360p NE–NE (B\*), MLVC-S 540p NE–NE, full MLVC 540p GPU–NE, MLVC-S 720p GPU–NE, full MLVC 720p NE–NE, MLVC-S 1080p NE–NE, full MLVC 1080p NE–NE.
- **Streams:** incoming streams at QP 16/24/26/32/40, made from the same source clips as experiment 09 (encoder on the NE).
- **Protocol of experiment 09:** paced duplex at 30 fps, 60 s per run with `powermetrics -i 100`, 60 s rest, first 64 frames per direction discarded, 5 rounds per QP with the QP order rotated each round, a 120 s idle recording before each setting, energy = (run power − idle power) × time / frame pairs, median of the 5 runs. As in experiment 09, the settings that cannot keep 30 fps (full MLVC 720p and 1080p, MLVC-S 1080p) were measured at 30 fps too, so their numbers are comparable with that table.
- **Equal bitrate:** energy and quality of each setting are interpolated at the same bitrate along its QP curve (bitrate of each QP from Part A).

## How to run

These scripts live in `~/Downloads/d/4b/` (one level below the other scripts; they read `../settings.sh` and `../settings_phase2.sh`).

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/check_quality_inputs.sh` | Read-only inventory of the experiment 05 pipeline, inputs and the table of experiment 09 | 1 min | any |
| `scripts/quality_per_setting_runs.sh` | Part A: pre-flight, `quality_runner.py` (up to 3 passes, so failed runs are retried), then `quality_tables.py`. **Resumable** | 3 h | any; charger in, lid open |
| `scripts/quality_runner.py` | The 900 quality runs (called by `quality_per_setting_runs.sh`) | — | — |
| `scripts/energy_per_qp_runs.sh` | Part B: incoming streams at each QP, 175 paced runs with `powermetrics`, then `energy_per_qp_table.py` and `quality_tables.py`. **Resumable** | 7.7 h | **quiet mode** (see [`../README.md`](../README.md#quiet-mode)), `../quiet_mode_on.sh` first, `../quiet_mode_off.sh` afterwards; password once |
| `scripts/energy_per_qp_table.py` | Energy per setting and QP (same calculation as experiment 09) | 1 min | any |
| `scripts/quality_tables.py` | All tables and figures (adds the Part B ones when `energy_qp.csv` exists) | 1 min | any |

Order: `cd ~/Downloads/d/4b && ./quality_per_setting_runs.sh`, then `cd ~/Downloads/d && ./quiet_mode_on.sh`, `cd 4b && ./energy_per_qp_runs.sh`, `cd .. && ./quiet_mode_off.sh`. Results go to `~/Downloads/duplexnvc-baseline/phase2/4b/`.

### Script names

The scripts were renamed from short names to descriptive ones after the runs; the code is unchanged apart from the names it calls and the log it writes. The console logs in `raw_data/` were recorded before the rename and keep the old names (`out_<old name>.txt`).

| Old name | New name | Console log written now |
|---|---|---|
| `scripts/all` | `scripts/quality_per_setting_runs.sh` | `out_quality_per_setting_runs.txt` |
| `scripts/en` | `scripts/energy_per_qp_runs.sh` | `out_energy_per_qp_runs.txt` |
| `scripts/chk` | `scripts/check_quality_inputs.sh` | `out_check_quality_inputs.txt` |
| `scripts/q.py` | `scripts/quality_runner.py` | — |
| `scripts/ana.py` | `scripts/quality_tables.py` | — |
| `scripts/es.py` | `scripts/energy_per_qp_table.py` | — |

## Files

| Path | Contents |
|---|---|
| `raw_data/` | `q.csv` (900 runs), `faces.csv` (27,180 scored faces), `run.txt`, `energy/energy_qp.csv` (35 setting × QP rows), `energy/thermal.csv` (thermal state and Low Power Mode at 1 Hz during Part B), `logs/out_all.txt`, `logs/out_en.txt`; see [`raw_data/README.md`](raw_data/README.md) |
| `results/rd_mean.csv` | Mean of the 20 clips per configuration × QP: kbps, coded PSNR-Y and PSNR-YUV, display PSNR-Y, face PSNR-Y, face LPIPS |
| `results/bd.csv` | BD-rate (%) and BD-quality for every setting vs B\*, MLVC-S vs full MLVC at the same resolution, and GPU vs NE encoder |
| `results/eqrate.csv` | Quality of every configuration at 100–2000 kbps, interpolated along its curve (blank outside it) |
| `results/pareto.csv` | Best placement per setting: label, energy (experiment 09), quality at QP 26, Pareto flags |
| `results/energy_qp.csv` | Energy per frame pair per setting and QP (Part B): total and per processor, min–max of the runs, late share, frame rate, p99, bitrate per direction |
| `results/pareto_eqrate.csv` | Energy and quality of every setting at 170, 287, 400, 600 and 1000 kbps, with Pareto flags (all settings; 30 fps settings only) |
| `results/unit.csv` | Encoder on GPU vs NE: change in coded PSNR-Y and bitrate per QP, same clips |
| `results/e6check.csv` | 360p of this experiment minus experiment 05, per QP |
| `results/facesize.csv` | Face PSNR-Y and LPIPS by face height at QP 26 |
| `results/fig_rd.png/pdf` | Rate–distortion curves: display PSNR-Y, face PSNR-Y, face LPIPS, coded PSNR-Y |
| `results/fig_pareto.png/pdf` | Energy vs face LPIPS and vs display PSNR-Y at QP 26 |
| `results/fig_energy.png/pdf` | Energy vs QP, energy vs bitrate, and the Pareto front at equal bitrate (287 kbps) |
| `results/summary.txt` | The analysis printout, including the answers to questions 2–4 |

## Results

**Every run completed.** Part A: 900 of 900, no failures, no short decodes; every GPU-encoder run resolved to the GPU, every other run to the NE. Part B: 175 of 175 runs, 5 per setting and QP; 225 unit reports, 0 mismatches; thermal state *nominal* and Low Power Mode off for the whole run.

### Quality (Part A)

**Mean of the 20 evaluation clips** (kbps / display PSNR-Y dB / face PSNR-Y dB / face LPIPS):

| Setting | QP 16 | QP 26 | QP 40 |
|---|---|---|---|
| Full MLVC 360p (B\*) | 384 / 34.55 / 35.28 / 0.224 | 170 / 33.51 / 33.67 / 0.254 | 40 / 29.38 / 28.77 / 0.373 |
| Full MLVC 540p | 784 / 37.69 / 37.81 / 0.152 | 315 / 36.32 / 35.91 / 0.186 | 71 / 31.48 / 30.66 / 0.301 |
| Full MLVC 540p, GPU encoder | 780 / 37.52 / 37.59 / 0.152 | 313 / 36.17 / 35.72 / 0.186 | 70 / 31.40 / 30.58 / 0.302 |
| MLVC-S 540p | 843 / 37.26 / 37.42 / 0.157 | 335 / 35.85 / 35.49 / 0.194 | 74 / 30.72 / 29.88 / 0.322 |
| Full MLVC 720p | 1304 / 39.71 / 39.45 / 0.118 | 480 / 38.08 / 37.34 / 0.152 | 100 / 33.02 / 31.93 / 0.261 |
| MLVC-S 720p | 1416 / 39.32 / 39.09 / 0.120 | 523 / 37.64 / 36.92 / 0.158 | 108 / 32.20 / 31.12 / 0.279 |
| MLVC-S 720p, GPU encoder | 1412 / 39.18 / 38.91 / 0.120 | 522 / 37.54 / 36.80 / 0.158 | 108 / 32.15 / 31.08 / 0.280 |
| Full MLVC 1080p | 2825 / 42.26 / 41.37 / 0.092 | 989 / 40.05 / 38.95 / 0.129 | 181 / 34.86 / 33.60 / 0.223 |
| MLVC-S 1080p | 3033 / 41.84 / 41.01 / 0.093 | 1087 / 39.63 / 38.57 / 0.132 | 191 / 33.96 / 32.79 / 0.237 |

All five QPs are in `results/rd_mean.csv`. On the evaluation clips B\* at QP 26 is 170 kbps; the 287 kbps of experiments 03–09 is on the four timing clips.

**BD-rate against B\*** (negative = fewer bits for the same quality; – = the curves do not overlap):

| Setting | Display PSNR-Y | Face PSNR-Y | Face LPIPS |
|---|---|---|---|
| Full MLVC 540p | −27.7 % | −7.7 % | −31.9 % |
| Full MLVC 540p, GPU encoder | −25.9 % | −5.0 % | −32.6 % |
| MLVC-S 540p | −4.3 % | +15.7 % | −11.8 % |
| Full MLVC 720p | −44.0 % | −13.2 % | −47.1 % |
| MLVC-S 720p | −18.1 % | +15.4 % | −26.6 % |
| MLVC-S 720p, GPU encoder | −16.4 % | +17.7 % | −25.7 % |
| Full MLVC 1080p | – | −9.2 % | – |
| MLVC-S 1080p | −31.1 % | +23.0 % | −35.9 % |

**Encoder on the GPU, decoder on the NE.** Coded PSNR-Y drops by 0.15–0.30 dB on average (up to 1.2 dB on single clips) and bitrate by 0.2–1.3 %: BD-rate on coded PSNR-Y +4.4 % for full MLVC 540p and +4.0 % for MLVC-S 720p. The GPU encoder's reconstruction differs from the NE decoder's, so the two drift apart.

**Cross-check with experiment 05 (360p):** coded PSNR-Y within 0.11 dB, display PSNR-Y within 0.006 dB, face LPIPS within 0.001, bitrate up to 2 % lower at QP 16. The input (VCD 360p YUV vs Lanczos from the 1080p MP4) does not change the results.

**Face sizes.** Every face in the 20 clips is at least 96 px tall at 1080p (32 px at 360p); only 6 faces fall in 96–191 px. Face-size groups need the multi-person content of a later step.

### Energy at every QP (Part B)

**Energy per frame pair** (mJ, median of 5 runs, idle subtracted):

| Setting | Placement | QP 16 | QP 24 | QP 26 | QP 32 | QP 40 | Experiment 09 (QP 26) |
|---|---|---|---|---|---|---|---|
| Full MLVC 360p (B\*) | NE–NE | 63.6 | 63.4 | 63.3 | 63.1 | 62.9 | 65.3 |
| MLVC-S 540p | NE–NE | 43.7 | 43.3 | 43.3 | 43.1 | 42.8 | 45.0 |
| Full MLVC 540p | GPU–NE | 625.7 | 672.0 | 670.2 | 614.6 | 592.0 | 635.1 |
| MLVC-S 720p | GPU–NE | 315.1 | 375.7 | 356.3 | 335.9 | 323.3 | 333.4 |
| Full MLVC 720p | NE–NE | 407.2 | 405.4 | 405.2 | 404.0 | 402.5 | 404.8 |
| MLVC-S 1080p | NE–NE | 295.0 | 293.0 | 292.6 | 291.3 | 290.2 | 291.6 |
| Full MLVC 1080p | NE–NE | 1574.5 | 1564.9 | 1563.6 | 1556.8 | 1551.0 | 1562.9 |

- **On the NE, energy does not depend on QP:** from QP 16 to QP 40 (a 9–12× change in bitrate) it changes by 1–2 %. The 5 runs of one QP agree within 4 % (most within 1 %). Almost all of it is the NE (e.g. 62.0 of 63.6 mJ for B\*); the CPU, which also does the entropy coding, adds 1.3–1.6 mJ for B\* and MLVC-S 540p, 4–9 mJ for the larger settings and 81–88 mJ for full MLVC 1080p.
- **With the encoder on the GPU, energy varies from run to run, not with QP:** full MLVC 540p 535–683 mJ and MLVC-S 720p 307–395 mJ across runs of the same QP; the medians go up and down with QP without a trend (QP 16 / QP 40 = 1.06 and 0.97).
- **QP 26 against experiment 09:** within −3.7 % to +0.3 % on the NE settings and +5.5 % / +6.9 % for the two GPU-encoder settings, which is inside their run-to-run spread.

### Energy vs quality at equal bitrate

(Energy mJ per frame pair / display PSNR-Y dB / face LPIPS; **bold** = on the 30 fps Pareto front for face LPIPS.)

| Setting | Label | 170 kbps (B\* at QP 26) | 287 kbps | 600 kbps |
|---|---|---|---|---|
| Full MLVC 360p (B\*) | 30 fps | 63 / 33.50 / 0.254 | 63 / 34.25 / 0.233 | – |
| MLVC-S 540p NE–NE | 30 fps | **43 / 34.03 / 0.238** | **43 / 35.50 / 0.202** | **43 / 36.84 / 0.168** |
| MLVC-S 720p GPU–NE | 30 fps | **329 / 34.15 / 0.233** | **339 / 35.98 / 0.192** | **369 / 37.81 / 0.151** |
| Full MLVC 540p GPU–NE | 30 fps | **616 / 34.64 / 0.222** | **667 / 35.98 / 0.190** | 653 / 37.21 / 0.159 |
| MLVC-S 1080p NE–NE | 15 fps only | – | 291 / 35.76 / 0.202 | 292 / 38.22 / 0.157 |
| Full MLVC 720p NE–NE | 15 fps only | 403 / 35.18 / 0.215 | 404 / 36.84 / 0.179 | 405 / 38.50 / 0.143 |
| Full MLVC 1080p NE–NE | infeasible | – | 1554 / 36.69 / 0.190 | 1559 / 38.91 / 0.149 |

400 and 1000 kbps, face PSNR-Y and the flags for all settings are in `results/pareto_eqrate.csv`. Among all settings, including those that only reach 15 fps, full MLVC 720p gives the best face LPIPS up to 600 kbps (at 404 mJ), and MLVC-S 1080p is on the front from 287 kbps.

## Conclusion

1. **Energy is a property of the setting and placement, not of the bitrate.** On the NE it changes by 1–2 % from QP 16 to QP 40; with the encoder on the GPU it varies more between runs than between QPs. So the energy of experiment 09 holds at every bitrate, and the energy–quality comparison is decided by quality at equal bitrate.
2. **MLVC-S 540p beats B\* at screen size, at every bitrate where both exist, with 32 % less energy** (43 vs 63 mJ per frame pair, 30 fps both). At B\*'s own operating point (170 kbps): +0.53 dB display PSNR-Y and face LPIPS 0.238 vs 0.254; at 287 kbps: +1.25 dB and 0.202 vs 0.233. BD-rate −4.3 % (display) and −11.8 % (LPIPS). Only face PSNR-Y is slightly worse below about 250 kbps (BD-rate +15.7 %). **B\* is dominated** and is not on any Pareto front.
3. **Full MLVC 540p is not worth its energy.** It costs 14–15× the energy of MLVC-S 540p (616–672 vs 43 mJ) for +0.4–0.6 dB display PSNR-Y and −0.009 to −0.016 face LPIPS at equal bitrate (170–600 kbps). It stays on the 30 fps front only up to about 300 kbps, by a margin of ≤ 0.011 LPIPS over MLVC-S 720p with the encoder on the GPU, which uses half the energy (329–339 mJ) and gives the same display PSNR-Y at 287 kbps (35.98 dB). From 400 kbps MLVC-S 720p is better in both quality metrics.
4. **The 30 fps Pareto front at equal bitrate is MLVC-S 540p (NE–NE) and MLVC-S 720p (GPU–NE)**, the same two settings as at QP 26, with full MLVC 540p as a costly end point below ~300 kbps. Above them in quality are only settings that reach 15 fps (full MLVC 720p, MLVC-S 1080p).
5. **Resolution matters more than model size, above the lowest bitrates.** At the same resolution MLVC-S needs 17–32 % more bits than full MLVC. MLVC-S one resolution step higher matches full MLVC at 287 kbps and beats it from about 400 kbps (MLVC-S 720p vs full MLVC 540p: 37.00 vs 36.76 dB at 400 kbps). Full MLVC 1080p beats 720p on display PSNR-Y only above about 350 kbps, and not on face LPIPS anywhere up to 1000 kbps (0.129 vs 0.126 at 1000 kbps).
6. **Moving the encoder to the GPU has a quality price** (BD-rate +4 %, above the 1-point threshold of H4) as well as an energy price (3.1× NE–NE for MLVC-S 720p and 3.4× for full MLVC 540p at QP 26, experiment 09). This qualifies the rule of experiment 09 ("move the encoder to the GPU when NE–NE cannot keep up") and is followed up in the correctness step.
