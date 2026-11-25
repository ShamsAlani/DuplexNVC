#!/bin/bash
# 4b energy: energy per frame pair at QP 16/24/26/32/40 for the best placement of each of the 7 settings,
# so that settings can be compared at EQUAL BITRATE (X3 measured energy at QP 26 only).
#   1. incoming streams at each QP (same source clips as X3, encoder on the NE), 35 prepares, ~10 min
#   2. per setting: 120 s idle; then RUNS rounds; in each round every QP once (order rotates per round):
#      paced duplex 30 fps, 60 s, powermetrics -i 100 (the X3 protocol), then REST s rest
#   3. energy_per_qp_table.py (energy table) and quality_tables.py (adds energy vs QP and the equal-bitrate Pareto to results/)
# QUIET MAC as in X3: charger in, Wi-Fi + Bluetooth OFF, brightness MAX (auto-brightness + True Tone off), every other
# app closed, lid open. Run ../quiet_mode_on.sh first (keep-awake, Spotlight paused); ../quiet_mode_off.sh afterwards.
# Asks for the password once (powermetrics needs sudo). RESUMABLE: Ctrl-C any time, ./energy_per_qp_runs.sh again continues.
# Time: ~7.5 h with RUNS=5 REST=60 (the protocol). RUNS=3 ./energy_per_qp_runs.sh ~4.5 h; REST=30 ./energy_per_qp_runs.sh ~5.5 h (both deviate; logged).
D=$(cd "$(dirname "$0")" && pwd); P=$(dirname "$D"); . "$P/settings.sh"; . "$P/settings_phase2.sh"
E="$WORK/phase2/4b/energy"; INQ="$WORK/phase2/4b/inc"; mkdir -p "$E" "$INQ"
exec > >(tee -a "$D/out_energy_per_qp_runs.txt") 2>&1
REST=${REST:-60}; RUNS=${RUNS:-5}
QPS=(16 24 26 32 40)
CFGS="mlvc_360p:npu-npu mlvcs_540p:npu-npu mlvc_540p:gpu-npu mlvcs_720p:gpu-npu mlvc_720p:npu-npu mlvcs_1080p:npu-npu mlvc_1080p:npu-npu"
echo; echo "== 4b ENERGY START  $(date)   runs=$RUNS rest=${REST}s"
sw_vers | tr '\n' ' '; echo; pmset -g batt | head -1; echo "libmlvc $(cat "$WORK/LIBMLVC_COMMIT.txt" 2>/dev/null)"

echo "== pre-flight"
bad=0
for f in "$BENCH" "$PY" "$TOOLS/analyze_run.py" "$TOOLS/thermal_log" "$CAM" "$INCSRC" "$NV"/{cam,incsrc}_{540p,720p,1080p}.nv12 \
         "$WORK/bundles/mlvc" "$WORK"/bundles/{mlvc,mlvcs}_{540p,720p,1080p} "$WORK/phase2/4b/q.csv"; do
  [ -e "$f" ] && echo "   ok  $f" || { echo "   MISSING  $f"; bad=1; }
done
pmset -g batt | grep -q "AC Power" || { echo "   NOT ON AC POWER"; bad=1; }
networksetup -getairportpower en0 2>/dev/null | grep -q " On" && echo "   WARNING: Wi-Fi is on (quiet mode wants it off)"
[ $bad = 0 ] || { echo "== PRE-FLIGHT FAILED: nothing was run. Fix the items above and run ./energy_per_qp_runs.sh again."; exit 1; }

sudo -v || exit 1
( while true; do sudo -n true 2>/dev/null; sleep 50; done ) & KEEP=$!
"$TOOLS/thermal_log" >> "$E/thermal.csv" & THERM=$!
trap 'kill $KEEP $THERM 2>/dev/null; echo "== stopped $(date) - run ./energy_per_qp_runs.sh again to continue"; exit 1' INT TERM
T0=$(date +%s); n=0; total=$(( 7 * RUNS * ${#QPS[@]} ))

echo "== incoming streams at each QP (encoder on the NE)"
for c in $CFGS; do
  s=${c%%:*}; cfg $s; B=$(bund $s)
  [ $RES = 360p ] && src="$INCSRC" || src="$NV/incsrc_$RES.nv12"
  for q in "${QPS[@]}"; do
    O="$INQ/$s-qp$q"; [ -s "$O/incoming.aus" ] && continue; mkdir -p "$O"
    "$BENCH" prepare --input "$src" --size $VSIZE --qp $q --iframe-period 64 --bundles "$B" --enc-cu npu --out-dir "$O" \
      2> "$O/prepare.log" || echo "   PREPARE FAILED $s QP $q"
    echo "   $s QP $q: $(( $(stat -f %z "$O/incoming.mlvc") * 8 * 30 / 600 / 1000 )) kbps"
  done
done

rot () {  # QP order of round r: rotate the list by r-1
  local r=$1 k=${#QPS[@]} i; for ((i = 0; i < k; i++)); do echo -n "${QPS[$(( (i + r - 1) % k ))]} "; done
}
for c in $CFGS; do
  s=${c%%:*}; p=${c#*:}; ec=${p%-*}; dc=${p#*-}; cfg $s
  I="$E/idle_$s"
  if [ ! -s "$I/power.txt" ]; then
    mkdir -p "$I"; echo "   $(date +%H:%M:%S) idle 120 s ($s)"
    sudo powermetrics --samplers cpu_power,gpu_power -i 100 -n 1200 -o "$I/power.txt" >/dev/null 2>&1
  fi
  echo "-- $s  enc $ec  dec $dc"
  for r in $(seq 1 $RUNS); do for q in $(rot $r); do
    n=$((n + 1)); O="$E/${s}_$p/qp${q}_r$r"
    if [ -s "$O/frames.csv" ] && [ -s "$O/run.txt" ] && [ -s "$O/power.txt" ]; then echo "   skip (done) ${O#$E/}"; continue; fi
    rm -rf "$O"; mkdir -p "$O"
    echo "[$n/$total] $(date +%H:%M:%S) +$(( ($(date +%s) - T0) / 60 ))min  ${O#$E/}"
    sudo powermetrics --samplers cpu_power,gpu_power -i 100 -n 700 -o "$O/power.txt" >/dev/null 2>&1 & PM=$!
    sleep 3
    "$BENCH" duplex --input "$(camf $s)" --size $VSIZE --qp $q --iframe-period 64 --bundles "$(bund $s)" \
      --incoming "$INQ/$s-qp$q/incoming.aus" --enc-cu $ec --dec-cu $dc --fps 30 --seconds 60 --warmup-frames 64 \
      --out-dir "$O" 2> "$O.log"
    wait $PM
    pmset -g therm 2>/dev/null | grep -iE "speed_limit|warning" | tr -s ' \n' ' ' > "$O.therm"
    grep -oE "requested=[a-z]+ resolved=[a-z]+|FAILED|rror[^.]*" "$O.log" | sort -u | tr '\n' ' '; echo
    sleep $REST
  done; done
done
kill $KEEP $THERM 2>/dev/null
echo "== 4b ENERGY END  $(date)  ($(( ($(date +%s) - T0) / 60 )) min)"
echo; echo "== energy table"; "$PY" "$D/energy_per_qp_table.py"
echo; echo "== analysis with energy per QP"; "$PY" "$D/quality_tables.py"
cp "$D/out_energy_per_qp_runs.txt" "$WORK/phase2/4b/results/" 2>/dev/null
echo; echo "Done. Run ../quiet_mode_off.sh (quiet mode off), then zip and send the results (see the instructions)."
