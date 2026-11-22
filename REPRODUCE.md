# Reproducing everything

All baseline measurements are in [`baseline/`](baseline/), in fourteen experiment folders. The Lab GPU Runs (fine-tuning MLVC on a GPU) have their own guide: **[`lab_gpu_runs/REPRODUCE.md`](lab_gpu_runs/REPRODUCE.md)**. The complete guide — tools, downloads, builds, quiet mode, the run order of every script, expected values and known problems — is **[`baseline/REPRODUCE.md`](baseline/REPRODUCE.md)**.

## In short

```bash
# one-time setup: see baseline/REPRODUCE.md §1–2, then install every script:
mkdir -p ~/Downloads/d
find <repo>/baseline -path '*/scripts/*' ! -path '*/1[0-4]_*_experiment/*' -type f ! -name README.md -exec cp {} ~/Downloads/d/ \;
mkdir -p ~/Downloads/d/{4b,5,ct,a1,hv,he}
cp <repo>/baseline/10_quality_per_setting_experiment/scripts/* ~/Downloads/d/4b/
cp <repo>/baseline/11_correctness_drift_experiment/scripts/* ~/Downloads/d/5/
cp <repo>/baseline/12_contention_experiment/scripts/* ~/Downloads/d/ct/
cp <repo>/baseline/13_a1_keyframe_qp_experiment/scripts/* ~/Downloads/d/a1/
cp <repo>/baseline/14_hevc_anchor_experiment/scripts/{all,hv.py,hvana.py} ~/Downloads/d/hv/
cp <repo>/baseline/14_hevc_anchor_experiment/scripts/energy/* ~/Downloads/d/he/
cp <repo>/baseline/common/code/{mlplan.swift,thermal_log.swift} ~/Downloads/d/ && chmod +x ~/Downloads/d/* ~/Downloads/d/{4b,5,ct,a1,hv,he}/*
cd ~/Downloads/d

./s; ./m; ./t                  # 01 smoke tests, streams
./f; ./q; ./g                  # 05 quality (Wi-Fi on for ./f)
./p                            # quiet mode on
./e; ./r; ./w; ./x             # 02 Phase 1 check, 06 energy, 03 timing
./c                            # 04 correctness
./1t; ./1; ./1r                # 07 processor experiment
./u                            # quiet mode off
./2a; ./2b                     # 08 model conversion (Wi-Fi on for ./2a)
./p
./all; ./4r                    # 09 placement experiment (21.4 h, resumable)
./u
cd 4b && ./all                 # 10 Part A: quality per setting (3 h, any conditions, resumable)
cd .. && ./p && cd 4b && ./en  # 10 Part B: energy at every QP (7.7 h, quiet, resumable)
cd .. && ./u
```

## Quiet mode (all timed runs)

AC power; Wi-Fi and Bluetooth off; brightness at maximum with automatic brightness and True Tone off; Low Power Mode off; no other apps; `./p` (keep-awake, Spotlight paused); the Mac left alone. Idle power is recorded under the same conditions and subtracted.

## Rebuilding the results without a Mac

```bash
cd baseline/common/analysis
python3 recompute_all.py      # tables of experiments 01–06
python3 make_figures.py       # figures of 03–06
python3 make_tables_x3.py     # tables of experiment 09
```
Experiment 10's tables and figures are rebuilt on the Mac by its `scripts/ana.py`.

## Expected agreement

On an M4 Pro: timing within about 2 %, energy within about 5 %, quality identical. On another chip the milliseconds differ, but the conclusions (the NE runs two networks almost serially; NE–NE is cheapest but fails first as load grows; move the encoder, not the decoder, off the NE) should hold.
