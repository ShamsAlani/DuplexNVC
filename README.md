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
| Data | VCD video-conferencing dataset, scenario `s1` |

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

Full guide: [`baseline/REPRODUCE.md`](baseline/REPRODUCE.md) (summary in [`REPRODUCE.md`](REPRODUCE.md)). Setup takes a few hours of downloads and builds; the ten experiments take about 40 hours, the longest being the resumable 21.4-hour placement experiment. Without a Mac, every table and figure can be rebuilt from the raw data with the three scripts in [`baseline/common/analysis/`](baseline/common/analysis/).

## Next steps

The baseline is complete for timing and energy. Still to be measured, in order: correctness of every encoder/decoder pairing (experiment 10 already shows a GPU encoder with an NE decoder costs about 4 % in bitrate); energy on battery and in Low Power Mode (plus a check against an external power meter, if hardware is provided); the cost of face-based scene analysis; multi-person data (full VCD, HEVC Class E, Pexels); and an on-device HEVC anchor. DuplexNVC itself — a controller that chooses placement, schedule, resolution and model from the content and the energy state — will then be measured against B\* with exactly this protocol.
