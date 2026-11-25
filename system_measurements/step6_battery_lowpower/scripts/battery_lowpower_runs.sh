#!/bin/bash
# STEP 6 (energy beyond AC) + STEP 7 (cost of the scene analyzer), one unattended run.
#  A. ON BATTERY (start it, then unplug the charger): idle + B* + MLVC-S 720p (GPU-NE) calls at high battery, the same
#     with Low Power Mode, a 60-min continuous B* call, calls until the battery reaches 30 %, the same blocks at low
#     battery (normal and Low Power Mode). Stops at about 20 % (never below 15 %) and waits for the charger.
#  B. ON AC (as soon as the charger is back): Step 7 = B* call with the Vision analyzer V0 off / V1 every 15 frames /
#     V2 every 15 on the CPU / V3 every 30 on the CPU (5 rounds); Step 6 on AC = normal and Low Power Mode blocks and a
#     30-min sustained B* call.
# Every call is paced 30 fps, 60 s, 60 s rest; energy from the chip's counters (ioe) and from the battery (V x I, 1 Hz).
# QUIET MAC (../quiet_mode_on.sh first), Wi-Fi + Bluetooth off, brightness max, lid open. Password once (Low Power Mode via pmset).
# Output: ~/Downloads/duplexnvc-baseline/phase2/bt/ ; console: out_battery_lowpower_runs.txt
D=$(cd "$(dirname "$0")" && pwd); P=$(dirname "$D"); . "$P/settings.sh"; . "$P/settings_phase2.sh"; exec > >(tee -a "$D/out_battery_lowpower_runs.txt") 2>&1
E="$WORK/phase2/bt"; mkdir -p "$E"; RUNS=${RUNS:-5}; REST=${REST:-60}
echo; echo "== STEP 6 + 7 START  $(date)"; sw_vers | tr '\n' ' '; echo
echo "-- password for Low Power Mode (pmset), asked once:"; sudo -v || exit 1
( while true; do sudo -n -v 2>/dev/null; sleep 50; done ) & KEEP=$!
pct () { pmset -g batt | grep -oE '[0-9]+%' | head -1 | tr -d %; }
onac () { pmset -g batt | head -1 | grep -q "AC Power"; }
lpm () { sudo -n pmset -a lowpowermode $1 >/dev/null 2>&1 && echo "   Low Power Mode $1  ($(pmset -g | grep lowpowermode | awk '{print $2}'))"; }
now () { "$PY" -c 'import time; print(f"{time.time():.3f}")'; }
for f in "$BENCH" "$PY" "$CAM" "$TOOLS/thermal_log" "$WORK/bundles/mlvc" "$WORK/bundles/mlvcs_720p" "$P/he/ioe.c" "$P/he/heana.py"; do
  [ -e "$f" ] || { echo "MISSING $f"; exit 1; }; done
[ -x "$TOOLS/ioe" ] || cc -O2 -o "$TOOLS/ioe" "$P/he/ioe.c" -framework CoreFoundation || exit 1
VA=1; [ -x "$TOOLS/va" ] && [ "$TOOLS/va" -nt "$D/va.swift" ] || swiftc -O -o "$TOOLS/va" "$D/va.swift" 2> "$E/va_build.log" || { VA=0; echo "   va (Vision analyzer) did NOT build: Step 7 will be skipped (see va_build.log)"; }
"$PY" "$D/bat.py" "$E/battery.csv" & BAT=$!
"$TOOLS/thermal_log" >> "$E/thermal.csv" & THERM=$!
caffeinate -dim -w $$ & 
cleanup () { lpm 0; kill $BAT $THERM $KEEP 2>/dev/null; }
trap 'cleanup; echo "== stopped $(date) - run ./battery_lowpower_runs.sh again to continue"; exit 1' INT TERM
lpm 0
# one call: $1 cond, $2 folder, $3 seconds, $4 ioe interval ms
call () {
  local c=$1 O=$2 S=${3:-60} I=${4:-100}; rm -rf "$O"; mkdir -p "$O"
  "$TOOLS/ioe" $I $(( (S + 45) * 1000 / I )) "$O/ioe.csv" & IO=$!; sleep 3
  echo "t_start=$(now)" > "$O/t.txt"; echo "pct_start=$(pct)" >> "$O/t.txt"
  case $c in
    bstar)  "$BENCH" duplex $BL --enc-cu npu --dec-cu npu --fps 30 --seconds $S --warmup-frames 64 --out-dir "$O" 2> "$O.log";;
    s720)   cfg mlvcs_720p; "$BENCH" duplex --input "$(camf mlvcs_720p)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund mlvcs_720p)" \
              --incoming "$(incf mlvcs_720p)" --enc-cu gpu --dec-cu npu --fps 30 --seconds $S --warmup-frames 64 --out-dir "$O" 2> "$O.log";;
    v1|v2|v3) case $c in v1) ev=15; cp=0;; v2) ev=15; cp=1;; v3) ev=30; cp=1;; esac
            "$TOOLS/va" "$CAM" 640 360 $ev $cp $((S + 12)) "$O/va.csv" > "$O/va.txt" 2>&1 & VP=$!
            "$BENCH" duplex $BL --enc-cu npu --dec-cu npu --fps 30 --seconds $S --warmup-frames 64 --out-dir "$O" 2> "$O.log"
            wait $VP 2>/dev/null;;   # va ends by itself (S + 12 s) and writes va.csv at the end: never killed
    v0)     "$BENCH" duplex $BL --enc-cu npu --dec-cu npu --fps 30 --seconds $S --warmup-frames 64 --out-dir "$O" 2> "$O.log";;
  esac
  echo "t_end=$(now)" >> "$O/t.txt"; echo "pct_end=$(pct)" >> "$O/t.txt"; onac && echo "ac=1" >> "$O/t.txt" || echo "ac=0" >> "$O/t.txt"
  wait $IO 2>/dev/null   # ioe stops by itself 45 s after the call time; never killed (it would lose its last samples)
  echo "$(grep -oE "requested=[a-z]+ resolved=[a-z]+" "$O.log" | sort -u | tr '\n' ' ')$(cat "$O/va.txt" 2>/dev/null)  battery $(pct) %"
}
idle () { local O=$1; [ -s "$O/ioe.csv" ] && return; mkdir -p "$O"; echo "   $(date +%H:%M:%S) idle 120 s"
  echo "t_start=$(now)" > "$O/t.txt"; "$TOOLS/ioe" 100 1200 "$O/ioe.csv"; echo "t_end=$(now)" >> "$O/t.txt"; }
done_run () { [ -s "$1/ioe.csv" ] && grep -q t_end "$1/t.txt" 2>/dev/null; }
# block: $1 tag, $2 low-power 0/1, $3.. conditions; stops early if the battery state no longer fits (need: bat/ac)
block () {
  local tag=$1 lp=$2; shift 2; local conds=("$@") k=${#conds[@]}
  echo; echo "== block $tag (Low Power Mode $lp)  $(date +%H:%M)  battery $(pct) %"; lpm $lp
  idle "$E/$tag/idle"
  for r in $(seq 1 $RUNS); do for ((i = 0; i < k; i++)); do c=${conds[$(( (i + r - 1) % k ))]}; O="$E/$tag/$c/r$r"
    done_run "$O" && { echo "   skip (done) $tag $c r$r"; continue; }
    if [ "$NEED" = bat ] && { onac || [ "$(pct)" -le 15 ]; }; then echo "   battery block stopped: charger back or battery <= 15 %"; lpm 0; return 1; fi
    if [ "$NEED" = ac ] && ! onac; then echo "   AC block paused: waiting for the charger"; until onac; do sleep 30; done; fi
    echo -n "   [$tag r$r] $(date +%H:%M:%S) $c  "; call $c "$O"; sleep $REST
  done; done
  lpm 0
}
# ---------------- A. battery ----------------
NEED=bat
if [ ! -f "$E/battery_done" ]; then
  if onac; then echo; echo "== on AC power: UNPLUG THE CHARGER now (waiting up to 15 min)"; for i in $(seq 1 90); do onac || break; sleep 10; done; fi
  if onac; then echo "== still on AC: battery part skipped"; else
    echo "== on battery: $(pct) %"
    [ "$(pct)" -ge 80 ] && { block bat_high 0 bstar s720; block bat_high_lpm 1 bstar s720; } || echo "   battery below 80 %: high-battery blocks skipped"
    if ! onac && ! done_run "$E/drain60/bstar" && [ "$(pct)" -gt 35 ]; then
      echo; echo "== 60-min continuous B* call  $(date +%H:%M)  battery $(pct) %"; echo -n "   "; call bstar "$E/drain60/bstar" 3600 1000; fi
    n=0; while ! onac && [ "$(pct)" -gt 30 ]; do n=$((n + 1))
      echo -n "   [drain $n] $(date +%H:%M:%S) s720 300 s  "; call s720 "$E/drain_more/s720_$n" 300 1000; done
    if ! onac && [ "$(pct)" -gt 15 ]; then block bat_low 0 bstar s720; block bat_low_lpm 1 bstar s720; fi
    touch "$E/battery_done"
  fi
fi
lpm 0
if ! onac; then echo; echo "== battery part done at $(pct) %: waiting for the charger  $(date +%H:%M)"; until onac; do sleep 30; done
  echo "== charger connected $(date +%H:%M); 5 min to settle"; sleep 300; fi
# ---------------- B. AC ----------------
NEED=ac
[ $VA = 1 ] && block step7 0 v0 v1 v2 v3
block ac 0 bstar s720
block ac_lpm 1 bstar s720
if ! done_run "$E/sustained30/bstar"; then echo; echo "== 30-min sustained B* call on AC  $(date +%H:%M)"; echo -n "   "; call bstar "$E/sustained30/bstar" 1800 1000; fi
cleanup
echo; echo "== runs END  $(date)"
"$PY" "$D/btana.py"
mkdir -p "$E/results"; cp "$D/out_battery_lowpower_runs.txt" "$E/results/" 2>/dev/null
echo "== STEP 6 + 7 END  $(date)"
