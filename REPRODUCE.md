# Reproducing everything

All baseline measurements are in [`baseline/`](baseline/), in the twelve experiment folders of the baseline report. The measurements made after it are in [`system_measurements/`](system_measurements/) and our Algorithm Enhancements (A1–A4) in [`algorithm_enhancements/`](algorithm_enhancements/); each folder's README says how to run them. The Lab GPU Runs (fine-tuning MLVC on a GPU) have their own guide: **[`lab_gpu_runs/REPRODUCE.md`](lab_gpu_runs/REPRODUCE.md)**. The complete guide — tools, downloads, builds, quiet mode, the run order of every script, expected values and known problems — is **[`baseline/REPRODUCE.md`](baseline/REPRODUCE.md)**.

## In short

```bash
# one-time setup: see baseline/REPRODUCE.md §1–2, then install every script:
mkdir -p ~/Downloads/d
find <repo>/baseline -path '*/scripts/*' ! -path '*/1[0-2]_*_experiment/*' ! -path '*/installers/*' -type f ! -name README.md -exec cp {} ~/Downloads/d/ \;
mkdir -p ~/Downloads/d/{4b,5,ct}
cp <repo>/baseline/10_quality_per_setting_experiment/scripts/* ~/Downloads/d/4b/
cp <repo>/baseline/11_correctness_drift_experiment/scripts/* ~/Downloads/d/5/
cp <repo>/baseline/12_contention_experiment/scripts/* ~/Downloads/d/ct/
cp <repo>/baseline/common/code/{mlplan.swift,thermal_log.swift} ~/Downloads/d/ && chmod +x ~/Downloads/d/* ~/Downloads/d/{4b,5,ct}/*
cd ~/Downloads/d

./smoke_test_mlvcs_540p.sh; ./make_baseline_streams.sh; ./smoke_test_mlvc_360p.sh                  # 01 smoke tests, streams
./make_1080p_references.sh; ./bdrate_vs_hevc.sh; ./quality_rd_faces.sh                  # 05 quality (Wi-Fi on for ./make_1080p_references.sh)
./quiet_mode_on.sh                            # quiet mode on
./phase1_check_runs.sh; ./phase1_check_summary.sh; ./energy_runs.sh; ./timing_runs.sh             # 02 Phase 1 check, 06 energy, 03 timing
./correctness_check.sh                            # 04 correctness
./processor_placement_trace.sh; ./processor_runs.sh; ./processor_summary.sh                # 07 processor experiment
./quiet_mode_off.sh                            # quiet mode off
./convert_models.sh; ./make_streams_per_setting.sh                     # 08 model conversion (Wi-Fi on for ./convert_models.sh)
./quiet_mode_on.sh
./placement_runs.sh; ./placement_summary.sh       # 09 placement experiment (21.4 h, resumable)
./quiet_mode_off.sh
cd 4b && ./quality_per_setting_runs.sh  # 10 Part A: quality per setting (3 h, any conditions, resumable)
cd .. && ./quiet_mode_on.sh && cd 4b && ./energy_per_qp_runs.sh  # 10 Part B: energy at every QP (7.7 h, quiet, resumable)
cd .. && ./quiet_mode_off.sh
cd 5 && ./drift_runs.sh && ./multi_person_runs.sh && cd ..  # 11 correctness and drift (≈ 33 h, any conditions, resumable)
./quiet_mode_on.sh                            # quiet mode on
cd ct && ./contention_runs.sh && cd ..  # 12 contention (55 min)
./quiet_mode_off.sh
```

## Quiet mode (all timed runs)

AC power; Wi-Fi and Bluetooth off; brightness at maximum with automatic brightness and True Tone off; Low Power Mode off; no other apps; `./quiet_mode_on.sh` (keep-awake, Spotlight paused); the Mac left alone. Idle power is recorded under the same conditions and subtracted.

## Rebuilding the results without a Mac

```bash
cd baseline/common/analysis
python3 recompute_all.py      # tables of experiments 01–06
python3 make_figures.py       # figures of 03–06
python3 make_tables_x3.py     # tables of experiment 09
```
Experiment 10's tables and figures are rebuilt on the Mac by its `scripts/quality_tables.py`.

## Expected agreement

On an M4 Pro: timing within about 2 %, energy within about 5 %, quality identical. On another chip the milliseconds differ, but the conclusions (the NE runs two networks almost serially; NE–NE is cheapest but fails first as load grows; move the encoder, not the decoder, off the NE) should hold.
