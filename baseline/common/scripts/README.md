# common/scripts/

Shared settings and helper scripts. The scripts of each experiment are in that experiment's own `scripts/` folder; on the Mac **all scripts run from one folder, `~/Downloads/d`**. To install every script of every experiment:

```bash
mkdir -p ~/Downloads/d
find <repo>/baseline -path '*/scripts/*' ! -path '*/1[0-2]_*_experiment/*' ! -path '*/installers/*' -type f ! -name README.md -exec cp {} ~/Downloads/d/ \;
mkdir -p ~/Downloads/d/{4b,5,ct}
cp <repo>/baseline/10_quality_per_setting_experiment/scripts/* ~/Downloads/d/4b/
cp <repo>/baseline/11_correctness_drift_experiment/scripts/* ~/Downloads/d/5/
cp <repo>/baseline/12_contention_experiment/scripts/* ~/Downloads/d/ct/
cp <repo>/baseline/common/code/{mlplan.swift,thermal_log.swift} ~/Downloads/d/
chmod +x ~/Downloads/d/*.sh ~/Downloads/d/{4b,5,ct}/*.sh
```

Experiments 10–12 run from their own subfolders (`4b`, `5`, `ct`) and read the settings one level up.

Every script saves its console output as `out_<script name>.txt` next to it (for example `quiet_mode_on.sh` writes `out_quiet_mode_on.txt`).

## Settings: `settings.sh`

Every script reads `settings.sh`. Edit it if your folders differ:

| Variable | Value | Meaning |
|---|---|---|
| `WORK` | `~/Downloads/duplexnvc-baseline` | Work folder |
| `TOOLS` | `$WORK/tools` | Copied from `../code` |
| `BENCH` | `$WORK/harness/build/ninja-release/libmlvc_example` | Measurement program |
| `MLVC` | `$WORK/libmlvc/install/mac-arm64-ninja-release/bin/mlvc` | libmlvc CLI |
| `PY` | `$WORK/.venv/bin/python3` | Python with NumPy, OpenCV, lpips, torch |
| `P1` | MLVC-S, 960×540, QP 22 | Phase 1 check settings |
| `BL` | full MLVC, 640×360, QP 26, I-period 64, bundle `$WORK/bundles/mlvc` | Baseline B\* settings |
| `VCD360`, `VCD1080` | `~/mlvc/data/VCD/yuv`, `$WORK/data/vcd_1080p` | Dataset locations |

`settings_phase2.sh` adds the settings of experiments 07–09: the seven model/resolution settings (full MLVC 360p/540p/720p/1080p, MLVC-S 540p/720p/1080p), their checkpoints, model input and video sizes, the clip IDs of the camera (0380a3 + 6587ae) and incoming (6c9c96 + 9c02f6) streams, and the helpers `cfg`, `bund`, `camf`, `incf` that return the bundle, camera stream and incoming stream of a setting.

## Shared scripts

| Script | Purpose | Time | Conditions |
|---|---|---|---|
| `settings.sh` | Paths and settings read by every script (table above) | — | — |
| `settings_phase2.sh` | Settings of experiments 07–09 | — | — |
| `build_measurement_program.sh` | Rebuilds the measurement program from `main.cpp` and checks it is the fixed version (13 × `Clock::now()`) | 1 min | any |
| `make_baseline_streams.sh` | Builds the 360p camera stream (clips 0380a3 + 6587ae) and incoming stream (6c9c96 + 9c02f6), 600 frames each; prepares the incoming stream at QP 26 and checks it decodes | 2 min | any |
| `quiet_mode_on.sh` | Puts the Mac in quiet mode: pauses Spotlight, tries to pause Time Machine (needs Full Disk Access), starts `caffeinate`, checks AC power and the tools | 1 min | password |
| `quiet_mode_off.sh` | Undoes `quiet_mode_on.sh` | 1 min | password |
| `show_run_order.sh` | Prints the run order | — | — |
| `collect_raw_results.sh` | Zips all raw results (no video) into `~/Downloads/DuplexNVC_raw_results.zip` | 1 min | any |
| `main.cpp` | Same as `../code/duplex_bench.cpp`, the source `build_measurement_program.sh` builds | — | — |
| `sum.py` | Medians over rounds (E1, T_turns, T_shared, S, κ) and paced statistics; used by `smoke_test_mlvc_360p.sh` and `timing_summary.sh` | — | — |
| `installers/d5.sh`, `d6.sh`, `d7.sh` | The installers that were used to write the scripts of experiments 07, 08 and 09 into `~/Downloads/d`. Kept as the record of what was installed; they write the **old** short names, so use the copy commands above instead | — | — |

Setup logs (`out_b.txt`, `out_p.txt`, `out_m.txt`, the full setup and conversion terminal log, and the pinned `libmlvc` commit) are in [`../setup/`](../setup/).

## Old and new script names

All scripts had short names during the runs (`./s`, `./x`, `./all`, …). They now have descriptive names; only the names changed, together with the calls between scripts and the name of each console log. The console logs kept in each experiment's `raw_data/` were recorded under the old names (for example `out_x4.txt` from `x`, `out_all.txt` from `all`), and `common/analysis/` reads them under those names.

| Folder | Old name | New name |
|---|---|---|
| common | `b` | `build_measurement_program.sh` |
| common | `h` | `show_run_order.sh` |
| common | `m` | `make_baseline_streams.sh` |
| common | `p` | `quiet_mode_on.sh` |
| common | `u` | `quiet_mode_off.sh` |
| common | `v` | `settings.sh` |
| common | `s2cfg` | `settings_phase2.sh` |
| common | `z` | `collect_raw_results.sh` |
| 01_smoke_test_experiment | `s` | `smoke_test_mlvcs_540p.sh` |
| 01_smoke_test_experiment | `t` | `smoke_test_mlvc_360p.sh` |
| 02_phase1_check_experiment | `e` | `phase1_check_runs.sh` |
| 02_phase1_check_experiment | `r` | `phase1_check_summary.sh` |
| 03_timing_experiment | `x` | `timing_runs.sh` |
| 03_timing_experiment | `y` | `timing_summary.sh` |
| 04_correctness_experiment | `c` | `correctness_check.sh` |
| 05_quality_experiment | `f` | `make_1080p_references.sh` |
| 05_quality_experiment | `q` | `bdrate_vs_hevc.sh` |
| 05_quality_experiment | `g` | `quality_rd_faces.sh` |
| 05_quality_experiment | `rd.py` | `rd_points.py` |
| 06_energy_experiment | `w` | `energy_runs.sh` |
| 07_processor_experiment | `1` | `processor_runs.sh` |
| 07_processor_experiment | `1r` | `processor_summary.sh` |
| 07_processor_experiment | `1t` | `processor_placement_trace.sh` |
| 08_model_conversion_experiment | `2a` | `convert_models.sh` |
| 08_model_conversion_experiment | `2b` | `make_streams_per_setting.sh` |
| 09_placement_experiment | `all` | `placement_runs.sh` |
| 09_placement_experiment | `2r` | `conversion_summary.sh` |
| 09_placement_experiment | `4r` | `placement_summary.sh` |
| 10_quality_per_setting_experiment | `all` | `quality_per_setting_runs.sh` |
| 10_quality_per_setting_experiment | `en` | `energy_per_qp_runs.sh` |
| 10_quality_per_setting_experiment | `chk` | `check_quality_inputs.sh` |
| 10_quality_per_setting_experiment | `q.py` | `quality_runner.py` |
| 10_quality_per_setting_experiment | `ana.py` | `quality_tables.py` |
| 10_quality_per_setting_experiment | `es.py` | `energy_per_qp_table.py` |
| 11_correctness_drift_experiment | `all` | `drift_runs.sh` |
| 11_correctness_drift_experiment | `an` | `drift_analysis.sh` |
| 11_correctness_drift_experiment | `mp` | `multi_person_runs.sh` |
| 11_correctness_drift_experiment | `c.py` | `drift_runner.py` |
| 11_correctness_drift_experiment | `m.py` | `multi_person_runner.py` |
| 11_correctness_drift_experiment | `ana.py` | `drift_tables.py` |
| 12_contention_experiment | `all` | `contention_runs.sh` |
| 12_contention_experiment | `sum` | `contention_summary.sh` |
| system_measurements/step6_battery_lowpower | `all` | `battery_lowpower_runs.sh` |
| system_measurements/step9_hevc_anchor | `all` | `hevc_quality_runs.sh` |
| system_measurements/step9_hevc_anchor (energy) | `all` | `hevc_energy_runs.sh` |
| algorithm_enhancements/A1_keyframe_qp | `all` | `a1_round1_runs.sh` |
| algorithm_enhancements/A1_keyframe_qp | `allb` | `a1_round2_runs.sh` |
| algorithm_enhancements/A3_forced_keyframe | `all` | `a3_runs.sh` |
