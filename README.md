# DuplexNVC

**Full-duplex learned video coding on a laptop chip.**

In a video call, every laptop does two jobs at once: it **encodes** its own camera and **decodes** the video of the other person, and it must finish both within **33.3 ms per frame** at 30 fps. Learned video codecs such as MLVC now run in real time on a laptop's Neural Engine, but every published speed was measured for the encoder *or* the decoder alone, on one processor, and none reports energy. DuplexNVC studies what it costs to run **both directions of a call on one Apple Silicon chip at the same time**, and how to place and schedule them across the **CPU, GPU and Neural Engine (NE)**.

**Team:** Shams Al-Ani, Warda Ul Hasan, Mohammed Alawadhi — American University of Sharjah, COE 694-07 Parallel Computing.

**Reports:** [Literature review](reports/DuplexNVC_Literature_Review.pdf) · [Survey](reports/DuplexNVC_Survey.pdf) · [Phase 2 baseline report](reports/DuplexNVC_Phase2_Baseline_Report.pdf) · [Demo video](demo/) · [How to reproduce](REPRODUCE.md)

---

## What this repository contains

| Folder | Contents |
|---|---|
| [`baseline/`](baseline/) | The Phase 2 **baseline**, in ten experiments: smoke tests, Phase 1 check, timing of the core baseline B\*, correctness, quality, energy, processor, model conversion, placement and quality-per-setting experiments. Each experiment folder has its scripts, raw data, results and a README with what it shows and what we concluded |
| [`tier_b/`](tier_b/) | **Tier B: changes to the MLVC network**, fine-tuned on a lab GPU (control, piecewise-linear memory gates B1, B1 + input gate, I-frame dropout B2, a second control for training noise). Scripts of the whole training pipeline, the input-gate patch, training logs, the measured cost of training and the first results |
| [`controller_data/`](controller_data/) | **Step 8: controller data.** 11 multi-person clips (HEVC Class E, Pexels) with people entering and leaving, face labels and face-size groups, real events annotated manually, and a comparison of Apple Vision's face and body detectors (and their combinations) as scene-change triggers. Scripts, raw data, results and a README |
| [`reports/`](reports/) | Literature review, survey and Phase 2 baseline report (PDF) |
| [`demo/`](demo/) | Demo video: MLVC-S encoding and decoding a talking-head clip, original and decoded side by side |
| [`REPRODUCE.md`](REPRODUCE.md) | How to rerun everything and rebuild every result |

The baseline took about **40 hours** of measurement (≈ 5.3 h for the core baseline B\*, ≈ 24 h for the processor, model conversion and placement experiments, including one run of 21.4 hours, and ≈ 10.7 h for quality and energy at every setting and QP), every timed run in the same fixed **quiet mode** (below).

## Key results

### Core baseline B\* (full MLVC, 360p, encoder and decoder on the NE, 30 fps)

| Question | Answer |
|---|---|
| Real time? | **Yes**: 30.01 fps both ways, 0 % late or dropped (5 × 60 s) |
| Margin | Slowest 1 % of frames finish at **29.3 / 28.9 ms** of 33.3 ms |
| Does the NE run both networks in parallel? | **Barely**: sharing is only **1.11×** faster than taking turns (ideal 1.99); each network runs 1.8× slower |
| Energy | **65.3 mJ per frame pair** (≈ 2 W), 97 % on the NE; GPU idle |
| Correctness | No failures; NE decoding is deterministic; GPU/CPU decoding drifts within each I-frame period (worst 38.5 dB) |
| Compression | **−31 %** bits vs Intel hardware HEVC for equal luma PSNR (−41 % YUV) |
| Quality limit | Upscaling 360p to a 1080p screen costs **4–6 dB**, more than the coding itself |

### Placement experiment (7 settings × every encoder/decoder placement)

| Setting | Best placement (encoder–decoder) | Frame rate | p99 (ms) | Energy (mJ / pair) |
|---|---|---|---|---|
| Full MLVC 360p | NE–NE (= B\*) | 30 fps | 29.3 / 28.9 | 65.3 |
| Full MLVC 540p | **GPU–NE** (NE–NE fails: 6 % late) | 30 fps | 31.1 / 25.4 | 635.1 |
| Full MLVC 720p | NE–NE | 15 fps only | — | 404.8 |
| Full MLVC 1080p | none | infeasible | — | — |
| MLVC-S 540p | **NE–NE** (most efficient setting measured) | 30 fps | 26.9 / 26.1 | **45.0** |
| MLVC-S 720p | GPU–NE (NE–NE fails: 3.3 % late) | 30 fps | 25.8 / 24.3 | 333.4 |
| MLVC-S 1080p | NE–NE | 15 fps only | — | 291.6 |

- **23 of 38** combinations meet 30 fps, 9 only 15 fps, 6 neither.
- **No CPU fallback:** every operation of every network runs on the processor it is given.
- **Keep both networks on the NE while they keep up** — it is 3–7× cheaper than any placement using the GPU. When they stop keeping up, move the **encoder** to the GPU and keep the **decoder** on the NE (a decoder off the NE drifts).
- At 30 fps every feasible setting keeps its slowest frames within 24–31 ms: **higher quality is paid for in frame rate, energy or bitrate, not latency.**

### Quality per setting and energy vs quality (7 settings × 5 QPs, 20 evaluation clips)

| Setting | Label | Energy (mJ / pair) | Display PSNR-Y at 287 kbps | Face LPIPS at 287 kbps |
|---|---|---|---|---|
| Full MLVC 360p (B\*) | 30 fps | 63 | 34.25 dB | 0.233 |
| **MLVC-S 540p, NE–NE** | 30 fps | **43** | 35.50 dB | 0.202 |
| MLVC-S 720p, GPU–NE | 30 fps | 339 | 35.98 dB | 0.192 |
| Full MLVC 540p, GPU–NE | 30 fps | 667 | 35.98 dB | 0.190 |
| MLVC-S 1080p, NE–NE | 15 fps only | 291 | 35.76 dB | 0.202 |
| Full MLVC 720p, NE–NE | 15 fps only | 404 | 36.84 dB | 0.179 |
| Full MLVC 1080p, NE–NE | infeasible | 1554 | 36.69 dB | 0.190 |

Energy at 287 kbps from experiment 10 (re-measured at five QPs; B\* 63 mJ, 3 % below the 65.3 mJ of experiment 06).

- **Energy does not depend on the bitrate:** on the NE it changes by 1–2 % from QP 16 to QP 40, so each setting's energy is fixed by its model, size and placement.
- **MLVC-S 540p beats B\*** at screen size at every bitrate where both exist (+0.5 dB at B\*'s 170 kbps, +1.25 dB at 287 kbps; better face LPIPS) **with 32 % less energy**. B\* is dominated.
- **Full MLVC 540p is not worth its energy:** 14–15× MLVC-S 540p for +0.4–0.6 dB; MLVC-S 720p (encoder on the GPU) matches it at half the energy.
- The 30 fps energy–quality front is **MLVC-S 540p (NE–NE)** and **MLVC-S 720p (GPU–NE)**. Moving the encoder to the GPU costs about 4 % in bitrate (encoder–decoder drift).

### Tier B: network-level changes (in progress)

| Question | Answer so far |
|---|---|
| What does a fine-tune of MLVC cost? (E5) | **0.22 s per step; ≈ 13 h for 200 epochs (200,000 steps)** on one RTX 3060 Ti (8 GB) |
| What does B1 (hard_tanh / hard_sigmoid gates) cost in quality? | **−0.07 dB PSNR** at +0.7 % bpp on training clips, vs a control trained the same way (first runs; being retrained, see [`tier_b/`](tier_b/)) |
| Does B1 reduce drift on the GPU/CPU? | To be measured on the Mac |

### Step 8: controller data (multi-person clips)

| Question | Answer |
|---|---|
| Data | **11 clips**: 3 HEVC Class E (seated, controls) and 8 Pexels (people entering, walking away, groups of 5 and 7, a crowd); 628 faces labelled with Apple Vision on every 10th frame |
| Face sizes | The new clips cover the **small faces** the baseline lacks (246 faces under 32 px and 236 at 32–63 px at 360p); the baseline's talking heads cover the large ones |
| Faces as a people count | Face detection measures **visible faces, not people present**: about half the people in group scenes, plus faces printed on a poster (68, excluded) |
| Best scene-change trigger | The **larger of the face and body counts**: 4 of 10 real events caught, 7 not real (faces alone 3 and 8, bodies alone 4 and 9); median 2.0 s late |
| What it means for the controller | Faces for **face size** (the resolution rule), the combined count for **how many people** and when that changes, a frame-difference trigger as backup; a change must last 1 s before acting |

Details: [`controller_data/`](controller_data/). Next: six video-conferencing clips of our own (joining, leaving, stepping away and two false-alarm cases) to evaluate the detectors in call scenes.

## Platform

| | |
|---|---|
| Device | MacBook Pro 14-inch, Apple M4 Pro, 24 GB unified memory |
| OS | macOS 26.6 (build 25G83) |
| Codec | `libmlvc` 0.1.0, commit `eb5d60a`, Core ML back end |
| Models | Full MLVC `dmc61sbr_reglu` and MLVC-S `dmc61sbr_mini_reglu`, public PSNR weights, converted to Core ML fp16 with `mlvc-tools` |
| Measurement program | `duplex_bench`, C++17 on `libmlvc` (alone, turns and duplex modes; unpaced or paced; per-frame timestamps) |
| Power | `powermetrics` (`cpu_power`, `gpu_power`; NE included), idle subtracted |
| Analysis | Python 3 (NumPy, OpenCV, `lpips`), Swift (Core ML `MLComputePlan`, Vision) |
| Step 8 labelling | MacBook Pro 13-inch, Apple M1 (face and body detection do not depend on the chip; every label from the same Mac) |
| Data | VCD video-conferencing dataset, scenario `s1`; Step 8: HEVC Class E (Xiph, public domain) and Pexels multi-person clips |

## Quiet mode

Every timed and energy run used the same state:

- AC power connected, Low Power Mode off;
- Wi-Fi and Bluetooth off (on only between experiments to copy data);
- screen brightness fixed at maximum, automatic brightness and True Tone off;
- `caffeinate -dims` on, no other apps open;
- 60 s rest after every 60 s run; modes interleaved in rounds;
- first 64 frames of each direction discarded as warm-up; medians over repeated runs;
- placement experiment: thermal state and Low Power Mode logged once per second.

## Repository layout

```
DuplexNVC/
├── README.md                          this file
├── REPRODUCE.md                       how to rerun everything and rebuild every result
├── reports/                           literature review, survey and Phase 2 baseline report (PDF)
├── demo/                              demo video: MLVC-S encoding and decoding on the M4 Pro
├── controller_data/                   Step 8: multi-person clips, face and body labels, events, detector comparison
│   ├── README.md                      clips, method, results, next step (our own call clips)
│   ├── scripts/                       s8_setup, s8_prep.py, s8_table.py, bodybox.swift, s8_bodies.py, s8_fusion.py
│   ├── raw_data/                      clip list, face boxes, real events, poster rule
│   └── results/                       dataset table, face-size groups, events, faces vs bodies, fusion
├── tier_b/                            network-level changes: lab GPU training pipeline, logs, results
│   ├── README.md                      the runs, settings, problems met, results so far
│   ├── REPRODUCE.md                   how to rerun the training and rebuild the results
│   ├── scripts/                       lab.ps1 (pipeline), patch_input_gate.py, analyze_training.py
│   ├── raw_data/logs/                 training and pipeline logs
│   └── results/                       per-epoch tables, run comparison, training cost, figure
└── baseline/
    ├── README.md                      overview of the ten experiments and headline results
    ├── REPRODUCE.md                   setup, run order, conditions, expected values
    ├── common/                        measurement program, analysis tools, shared scripts, rebuild scripts
    ├── 01_smoke_test_experiment/      S1, S2: does the pipeline work?
    ├── 02_phase1_check_experiment/    E3a: does the new program reproduce Phase 1?
    ├── 03_timing_experiment/          E1–E4, B*: speed, sharing the NE, real time at 30 fps
    ├── 04_correctness_experiment/     E5: decoding correctness and drift across processors
    ├── 05_quality_experiment/         E6: BD-rate, rate–distortion, display and face quality
    ├── 06_energy_experiment/          E7: energy of B* per frame pair
    ├── 07_processor_experiment/       X1: placement trace; each network alone on NE, GPU, CPU
    ├── 08_model_conversion_experiment/ X2: full MLVC and MLVC-S at 540p/720p/1080p
    ├── 09_placement_experiment/       X3: every setting × placement, table of feasible settings
    └── 10_quality_per_setting_experiment/ quality of all 7 settings, energy at every QP, energy–quality Pareto
```

Each experiment folder holds `scripts/`, `raw_data/`, `results/` and a README.

## Reproducing

Full guide: [`baseline/REPRODUCE.md`](baseline/REPRODUCE.md) (summary in [`REPRODUCE.md`](REPRODUCE.md)). Setup takes a few hours of downloads and builds; the ten experiments take about 40 hours, the longest being the resumable 21.4-hour placement experiment. Without a Mac, every table and figure can be rebuilt from the raw data with the three scripts in [`baseline/common/analysis/`](baseline/common/analysis/). Tier B training (Windows PC with an NVIDIA GPU) and its analysis: [`tier_b/REPRODUCE.md`](tier_b/REPRODUCE.md).

## Next steps

The baseline is complete for timing and energy. Still to be measured, in order: correctness of every encoder/decoder pairing (experiment 10 already shows a GPU encoder with an NE decoder costs about 4 % in bitrate); energy on battery and in Low Power Mode (plus a check against an external power meter, if hardware is provided); the cost of face-based scene analysis; and an on-device HEVC anchor. Multi-person data is done (Step 8, [`controller_data/`](controller_data/)); its next step is a small set of video-conferencing clips of our own to test the scene-change triggers in call scenes. DuplexNVC itself — a controller that chooses placement, schedule, resolution and model from the content and the energy state — will then be measured against B\* with exactly this protocol.
