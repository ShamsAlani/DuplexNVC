#!/bin/bash
cat <<'X'
DuplexNVC core baseline: run from ~/Downloads/d (see README.md for one-time setup)
 one-time: ./build_measurement_program.sh  rebuild the measurement program (after setup steps 1-6 in README)
 Phase-1 check (MLVC-S 540p):    ./smoke_test_mlvcs_540p.sh smoke test   ./phase1_check_runs.sh E3a (~45 min)   ./phase1_check_summary.sh E3a summary
 Baseline streams + smoke test:  ./make_baseline_streams.sh make 360p camera/incoming streams   ./smoke_test_mlvc_360p.sh smoke test
 Data + quality (Wi-Fi ON):      ./make_1080p_references.sh 1080p references   ./bdrate_vs_hevc.sh BD-rate vs HEVC   ./quality_rd_faces.sh R-D + face quality
 QUIET MAC (Wi-Fi + Bluetooth off, brightness MAX, auto-brightness/True Tone off, apps closed, charger in):
   ./quiet_mode_on.sh prepare   ./energy_runs.sh energy E7 (~15 min, password at start)   ./timing_runs.sh B* timing E1-E4 (~65 min)
 Afterwards:  ./correctness_check.sh correctness E5   ./timing_summary.sh B* summary   ./quiet_mode_off.sh undo preparation   ./collect_raw_results.sh collect raw results
Every script writes out_<script name>.txt next to it.
X
