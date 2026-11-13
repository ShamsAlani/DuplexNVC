# DuplexNVC Baseline

The baseline is the fixed reference against which every later DuplexNVC change is measured. It was built in nine experiments, each in its own folder with its scripts, raw data, results and a README that explains what was run, what it shows and what we concluded.

**The core baseline B\*:** full MLVC (`dmc61sbr_reglu`, PSNR weights, Core ML fp16) at 640×360, encoder **and** decoder on the Apple Neural Engine (NE), full duplex at 30 fps (33.3 ms deadline), QP 26, an I-frame every 64 frames, VCD talking-head content. Experiments 07–09 then extend it to the GPU and CPU, to the seven model/resolution settings of our survey, and to every placement of the encoder and the decoder.

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
| [`common`](common/) | — | Measurement program, analysis tools, shared scripts, rebuild scripts, setup logs | — | — |

In total about **29 hours** of measurement, almost all of it in quiet mode.

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

## Quiet mode

Every timed run used the same state: AC power and Low Power Mode off; **Wi-Fi and Bluetooth off**; screen brightness fixed at **maximum** with automatic brightness and True Tone off; `caffeinate -dims`; no other apps; 60 s rest after every 60 s run; modes interleaved in rounds; first 64 frames of each direction discarded; medians over repeated runs. The idle power recordings, which are subtracted, use the same state.

## Folder layout of each experiment

```
NN_<name>_experiment/
├── README.md     question, what was run, how to run it, files, results, conclusion
├── scripts/      the scripts that ran it (all are run from ~/Downloads/d)
├── raw_data/     per-run records (frames.csv, run.txt, power.txt) and console logs (logs/)
└── results/      result tables (CSV) and figures (PNG, PDF)
```

## Reproduce

Step by step, with setup, run order, conditions, expected values and known problems: **[`REPRODUCE.md`](REPRODUCE.md)**. To only rebuild the results from the raw data (no Mac needed): see [`common/README.md`](common/README.md).
