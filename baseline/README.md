# DuplexNVC Baseline

The baseline is the fixed reference against which every later DuplexNVC change is measured. It was built in twelve experiments, the ones in our submitted baseline report, each in its own folder with its scripts, raw data, results and a README that explains what was run, what it shows and what we concluded.

**The core baseline B\*:** full MLVC (`dmc61sbr_reglu`, PSNR weights, Core ML fp16) at 640×360, encoder **and** decoder on the Apple Neural Engine (NE), full duplex at 30 fps (33.3 ms deadline), QP 26, an I-frame every 64 frames, VCD talking-head content. Experiments 07–09 then extend it to the GPU and CPU, to the seven model/resolution settings of our survey, and to every placement of the encoder and the decoder; experiment 10 measures the quality of every setting and its energy at every QP; experiment 11 the correctness and drift of every encoder/decoder pair; experiment 12 whether memory bandwidth limits the NE. Later measurements and our own changes to MLVC are outside this folder (see below).

**Device:** MacBook Pro 14-inch, Apple M4 Pro, 24 GB, macOS 26.6 · **Codec:** `libmlvc` 0.1.0, commit `eb5d60a`.

## Experiments

| Folder | Experiment | Question | Runs | Time |
|---|---|---|---|---|
| [`01_smoke_test_experiment`](01_smoke_test_experiment/) | Smoke tests S1, S2 | Does the pipeline work before collecting data? | 10 s per mode | 6 min |
| [`02_phase1_check_experiment`](02_phase1_check_experiment/) | E3a | Does the new program reproduce Phase 1 (MLVC-S 540p)? | 23 | 45 min |
| [`03_timing_experiment`](03_timing_experiment/) | E1–E4, **B\*** | How fast is each network, how much does sharing the NE help, does a 30 fps call meet every deadline? | 31 | 65 min |
| [`04_correctness_experiment`](04_correctness_experiment/) | E5 | Is decoding correct, and does the GPU/CPU decoder drift from the NE? | 4 decodes | 5 min |
| [`05_quality_experiment`](05_quality_experiment/) | E6 | BD-rate vs hardware HEVC; quality at the coded size, at screen size and on faces | 3 + 24 clips × 4 QPs | 35 min |
| [`06_energy_experiment`](06_energy_experiment/) | E7 | Energy of B\* per frame pair, per processor | idle + 5 | 15 min |
| [`07_processor_experiment`](07_processor_experiment/) | X1 | Do the networks run where we ask? How do GPU and CPU compare with the NE? | 72 | 2.3 h |
| [`08_model_conversion_experiment`](08_model_conversion_experiment/) | X2 | Full MLVC and MLVC-S at 540p/720p/1080p: conversion, placement, input streams | 7 bundles | 0.5 h |
| [`09_placement_experiment`](09_placement_experiment/) | X3 | Every setting × every encoder/decoder placement: which meet 30 fps, at what energy? | 584 | 21.4 h |
| [`10_quality_per_setting_experiment`](10_quality_per_setting_experiment/) | Step 4b | Quality of every setting at screen size and on faces; energy at every QP; which settings are on the energy–quality Pareto front at equal bitrate? | 900 + 175 | 3.0 h + 7.7 h |
| [`11_correctness_drift_experiment`](11_correctness_drift_experiment/) | Step 5 | All 9 encoder→decoder pairs on every setting: failures, determinism, drift, BD-rate (H4); multi-person content (the A2 drift bounds of the same run are in [`algorithm_enhancements/`](../algorithm_enhancements/)) | 2,212 jobs × 9 pairs | ≈ 33 h (with A2) |
| [`12_contention_experiment`](12_contention_experiment/) | Contention | Is the NE limited by memory bandwidth? Why does a paced call take twice the unpaced time per frame? | 24 + peak | 55 min |
| [`common`](common/) | — | Measurement program, analysis tools, shared scripts, rebuild scripts, setup logs | — | — |

In total about **74 hours** of measurement that the results come from (including the A2 runs that shared experiment 11's run), plus about 2 hours of runs that were set aside and repeated (experiments 02, 06 and 11 say which, why, and what was fixed); every timed and energy run in quiet mode (quality runs do not depend on timing). Everything measured after the report is ours and kept apart: further measurements of the duplex system (Steps 6, 7 and 9) in [`system_measurements/`](../system_measurements/), our changes to MLVC's coding algorithm (the Algorithm Enhancements A1–A4, with the A2 drift bounds measured alongside experiment 11) in [`algorithm_enhancements/`](../algorithm_enhancements/), and the network-level changes in [`lab_gpu_runs/`](../lab_gpu_runs/).

## Headline results

| Question | Answer | Experiment |
|---|---|---|
| Does B\* run a two-way call in real time? | **Yes**: 30.01 fps both ways, 0 % late; slowest 1 % of frames at 29.3 / 28.9 ms of 33.3 ms | 03 |
| Does the NE run both networks in parallel? | **Barely**: sharing is 1.11× faster than taking turns (ideal 1.99); each network 1.8× slower | 03 |
| Energy of B\* | **65.3 mJ per frame pair** (≈ 2 W), 97 % on the NE; GPU idle | 06 |
| Correctness | No failures; NE decoding deterministic; GPU/CPU decoders drift (worst 38.5 dB) | 04 |
| Compression | **−31 %** bits vs Intel hardware HEVC (luma); 360p upscaled to a 1080p screen loses 4–6 dB | 05 |
| CPU fallback? | **None**: 100 % of every network's cost runs on the requested processor | 07, 08 |
| GPU / CPU vs NE | GPU 2–2.3× slower at several times the power; CPU 3.4–4.3× slower | 07, 09 |
| Feasible at 30 fps | **23 of 38** setting × placement combinations; 9 only at 15 fps; 6 neither | 09 |
| Best placements | Keep both networks on the NE while they keep up; then move the **encoder** to the GPU (full MLVC 540p, MLVC-S 720p); full MLVC above 540p does not reach 30 fps | 09 |
| Most efficient setting | **MLVC-S 540p, NE–NE**: 30 fps, p99 ≈ 27 ms, 45 mJ per frame pair | 09 |
| Energy vs bitrate | Energy per frame pair changes by only 1–2 % from QP 16 to QP 40 on the NE: it is set by model, size and placement | 10 |
| MLVC-S 540p vs B\* at screen size | **Better at every bitrate** (+1.25 dB display PSNR-Y, face LPIPS 0.202 vs 0.233 at 287 kbps) with 32 % less energy; B\* is dominated | 10 |
| Full MLVC 540p | **Not worth its energy**: 14–15× MLVC-S 540p for +0.4–0.6 dB; MLVC-S 720p (GPU–NE) matches it at half the energy | 10 |
| 30 fps energy–quality front | **MLVC-S 540p (NE–NE)** and **MLVC-S 720p (GPU–NE)**; a GPU encoder with an NE decoder costs ≈ 4 % in bitrate | 10 |
| Correctness on every processor pair (H4) | **Deterministic, no failures, but H4 fails for every mismatched pair**: +3–7 % bitrate GPU/NE, +7–20 % with the CPU; about twice that on multi-person clips | 11 |
| Is the NE limited by memory bandwidth? | **No**: 217 GB/s of competing traffic slows the encoder by only 4.4 % (M1: 18.8 %); the NE itself limits sharing | 12 |
| Why are paced calls slow? | **Clocks drop between frames**: a background memory load cuts the paced B\* call from 12.6 to 7.4 ms per frame | 12 |

## Quiet mode

Every timed run used the same state: AC power and Low Power Mode off; **Wi-Fi and Bluetooth off**; screen brightness fixed at **maximum** with automatic brightness and True Tone off; `caffeinate -dims`; no other apps; 60 s rest after every 60 s run; modes interleaved in rounds; first 64 frames of each direction discarded; medians over repeated runs. The idle power recordings, which are subtracted, use the same state.

## Folder layout of each experiment

```
NN_<name>_experiment/
├── README.md     question, what was run, how to run it, files, results, conclusion
├── scripts/      the scripts that ran it (run from ~/Downloads/d; experiment 10's from ~/Downloads/d/4b, 11's from d/5, 12's from d/ct)
├── raw_data/     per-run records (frames.csv, run.txt, power.txt) and console logs (logs/)
└── results/      result tables (CSV) and figures (PNG, PDF)
```

## Reproduce

Step by step, with setup, run order, conditions, expected values and known problems: **[`REPRODUCE.md`](REPRODUCE.md)**. To only rebuild the results from the raw data (no Mac needed): see [`common/README.md`](common/README.md).
