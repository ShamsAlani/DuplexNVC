#!/bin/bash
# STEP 9, energy part: energy per frame pair of a paced 30 fps two-way call with Apple's hardware HEVC (VideoToolbox)
# against MLVC, measured in the same session with the chip's own energy counters (IOReport "Energy Model": CPU, GPU,
# ANE, DRAM and the video encoder/decoder blocks, which powermetrics does not report). No password needed.
#   conditions (60 s, paced 30 fps, both directions at once, same camera and incoming clips as experiment 03/09):
#     hevc_360p  hardware HEVC encode of the camera + hardware HEVC decode of the incoming stream, 287 kbps (B*'s rate)
#     hevc_720p  the same at 720p, 847 kbps (MLVC-S 720p's rate)
#     mlvc_360p  B* (full MLVC 360p, NE-NE)      mlvcs_540p  MLVC-S 540p NE-NE      mlvcs_720p  MLVC-S 720p GPU-NE
#   5 interleaved rounds, 60 s rest after each run, 120 s idle at the start and at the end. ~60 min.
# QUIET MAC (../quiet_mode_on.sh first): charger in, Wi-Fi + Bluetooth off, brightness max, other apps closed. RESUMABLE.
# Output: ~/Downloads/duplexnvc-baseline/phase2/he/ ; console: out_hevc_energy_runs.txt
D=$(cd "$(dirname "$0")" && pwd); P=$(dirname "$D"); . "$P/settings.sh"; . "$P/settings_phase2.sh"; exec > >(tee -a "$D/out_hevc_energy_runs.txt") 2>&1
E="$WORK/phase2/he"
# v4: earlier attempts are set aside (1: the raw .hevc stream did not loop and a variable clash ran empty conditions;
# 2: the incoming MP4 carried ~350 fps timestamps, so the decoder ran far faster than 30 fps; 3: no keep-awake, so the
# display slept, background tasks ran on the CPU/GPU/NE and the Mac stalled twice for ~15 min)
if [ -d "$E" ] && [ ! -f "$E/v4" ]; then
  if [ -f "$E/v3" ]; then mv "$E" "$WORK/phase2/he_attempt3_display_sleep"
  elif [ -f "$E/v2" ]; then mv "$E" "$WORK/phase2/he_attempt2_unpaced"; else mv "$E" "$WORK/phase2/he_attempt1_failed"; fi; fi
mkdir -p "$E/inc"; touch "$E/v4"; caffeinate -dims -w $$ &   # display and system stay awake for the whole run
 REST=${REST:-60}; RUNS=${RUNS:-5}
echo; echo "== STEP 9 (energy) START  $(date)"; sw_vers | tr '\n' ' '; echo; pmset -g batt | head -1
pmset -g batt | grep -q "AC Power" || { echo "   NOT ON AC POWER: plug in the charger"; exit 1; }
networksetup -getairportpower en0 2>/dev/null | grep -q " On" && echo "   WARNING: Wi-Fi is on (quiet mode wants it off)"
for f in "$BENCH" "$PY" "$TOOLS/thermal_log" "$CAM" "$INCSRC" "$NV/cam_720p.nv12" "$NV/incsrc_720p.nv12" "$NV/cam_540p.nv12" \
         "$WORK/bundles/mlvc" "$WORK/bundles/mlvcs_540p" "$WORK/bundles/mlvcs_720p"; do [ -e "$f" ] || { echo "MISSING $f"; exit 1; }; done
[ -x "$TOOLS/ioe" ] || cc -O2 -o "$TOOLS/ioe" "$D/ioe.c" -framework CoreFoundation || exit 1
"$TOOLS/ioe" 200 2 /tmp/ioe_test.csv || exit 1
echo "-- energy counters on this chip (channel, unit):"; tail -n +2 /tmp/ioe_test.csv | cut -d, -f3,4 | sort -u | tr '\n' ';'; echo
now () { "$PY" -c 'import time; print(f"{time.time():.3f}")'; }
VT="-c:v hevc_videotoolbox -allow_sw 0 -realtime 1 -bf 0 -g 64"
echo "-- incoming HEVC streams (hardware encoder, 1800 frames = 60 s at 30 fps, MP4 with 30 fps timestamps)"
for x in 360p:640x360:287:"$INCSRC" 720p:1280x720:847:"$NV/incsrc_720p.nv12"; do
  IFS=: read r sz k src <<< "$x"; o="$E/inc/hevc_$r.mp4"
  [ -s "$o" ] || ffmpeg -v error -y -f rawvideo -pix_fmt nv12 -s $sz -framerate 30 -stream_loop 2 -i "$src" -frames:v 1800 $VT -b:v ${k}000 -tag:v hvc1 "$o" || exit 1
  n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=r_frame_rate,nb_read_frames -of csv=p=0 "$o")
  echo "   $r: target $k kbps -> $(( $(stat -f %z "$o") * 8 * 30 / 1800 / 1000 )) kbps; frame rate, frames: $n"
  case "$n" in 30/1,1800) ;; *) echo "   WRONG incoming stream ($n): stopping"; exit 1;; esac
done
"$TOOLS/thermal_log" >> "$E/thermal.csv" & THERM=$!
trap 'kill $THERM 2>/dev/null; echo "== stopped $(date) - run ./hevc_energy_runs.sh again to continue"; exit 1' INT TERM
idle () { local O="$E/idle_$1"; [ -s "$O/ioe.csv" ] && return; mkdir -p "$O"; echo "   $(date +%H:%M:%S) idle 120 s ($1)"
  echo "t_start=$(now)" > "$O/t.txt"; "$TOOLS/ioe" 100 1200 "$O/ioe.csv"; echo "t_end=$(now)" >> "$O/t.txt"; }
runone () {  # $1 condition $2 run folder
  local c=$1 O=$2 sz k cam s ec e1 e2 EN DE IO; rm -rf "$O"; mkdir -p "$O"
  "$TOOLS/ioe" 100 900 "$O/ioe.csv" & IO=$!; sleep 3
  echo "t_start=$(now)" > "$O/t.txt"
  case $c in
    hevc_360p|hevc_720p)
      [ $c = hevc_360p ] && { sz=640x360; k=287; cam="$CAM"; } || { sz=1280x720; k=847; cam="$NV/cam_720p.nv12"; }
      ffmpeg -v error -stats -y -re -f rawvideo -pix_fmt nv12 -s $sz -framerate 30 -stream_loop -1 -i "$cam" -t 60 \
        $VT -b:v ${k}000 -f hevc "$O/outgoing.hevc" 2> "$O/enc.log" & EN=$!
      ffmpeg -v error -stats -y -re -hwaccel videotoolbox -i "$E/inc/$c.mp4" -t 60 \
        -f null - 2> "$O/dec.log" & DE=$!
      wait $EN; e1=$?; wait $DE; e2=$?; [ $e1 = 0 ] && [ $e2 = 0 ] || echo "   FFMPEG FAILED ($e1/$e2): $(tail -c 200 "$O/enc.log" "$O/dec.log" | tr '\n' ' ')";;
    mlvc_360p)  "$BENCH" duplex $BL --enc-cu npu --dec-cu npu --fps 30 --seconds 60 --warmup-frames 64 --out-dir "$O" 2> "$O.log";;
    mlvcs_540p|mlvcs_720p)
      s=$c; cfg $s; [ $s = mlvcs_720p ] && ec=gpu || ec=npu
      "$BENCH" duplex --input "$(camf $s)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund $s)" --incoming "$(incf $s)" \
        --enc-cu $ec --dec-cu npu --fps 30 --seconds 60 --warmup-frames 64 --out-dir "$O" 2> "$O.log";;
  esac
  echo "t_end=$(now)" >> "$O/t.txt"; wait $IO
  pmset -g therm 2>/dev/null | grep -iE "speed_limit|warning" | tr -s ' \n' ' ' > "$O.therm"
  [ -f "$O.log" ] && grep -oE "requested=[a-z]+ resolved=[a-z]+|FAILED" "$O.log" | sort -u | tr '\n' ' '
  [ -f "$O/dec.log" ] && echo -n "frames out $(grep -oE 'frame= *[0-9]+' "$O/enc.log" | tail -1 | tr -d ' '), in $(grep -oE 'frame= *[0-9]+' "$O/dec.log" | tail -1 | tr -d ' ')"
  echo
}
CONDS=(hevc_360p mlvc_360p hevc_720p mlvcs_720p mlvcs_540p)
idle start
n=0; N=$(( RUNS * ${#CONDS[@]} ))
for r in $(seq 1 $RUNS); do
  K=${#CONDS[@]}
  for ((i = 0; i < K; i++)); do c=${CONDS[$(( (i + r - 1) % K ))]}; n=$((n + 1)); O="$E/$c/r$r"
    if [ -s "$O/ioe.csv" ] && grep -q t_end "$O/t.txt" 2>/dev/null; then echo "[$n/$N] skip (done) $c r$r"; continue; fi
    [ -n "$c" ] || { echo "== internal error: empty condition, stopping"; exit 1; }
    echo -n "[$n/$N] $(date +%H:%M:%S) $c r$r  "; runone $c "$O"
    if [ -f "$O/dec.log" ]; then f=$(grep -oE 'frame= *[0-9]+' "$O/dec.log" | tail -1 | grep -oE '[0-9]+')
      [ "${f:-0}" -ge 1700 ] && [ "${f:-0}" -le 1900 ] || { echo "== HEVC decode gave ${f:-0} frames (need 1700-1900, i.e. 30 fps): stopping Step 9 energy"; mv "$O" "$O.bad"; kill $THERM 2>/dev/null; exit 1; }; fi
    sleep $REST
  done
done
idle end
kill $THERM 2>/dev/null
echo "== runs END  $(date)"
"$PY" "$D/heana.py"
cp "$D/out_hevc_energy_runs.txt" "$E/results/" 2>/dev/null
echo "== STEP 9 (energy) END  $(date)"
