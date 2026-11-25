#!/bin/bash
# check_quality_inputs.sh: read-only inventory of the E6 quality pipeline, inputs and X3 table before Step 4b.
# Writes nothing except out_check_quality_inputs.txt next to this script.
cd "$(dirname "$0")"
exec > >(tee out_check_quality_inputs.txt) 2>&1
D=~/Downloads/d
. "$D/settings.sh"
. "$D/settings_phase2.sh"
sec(){ echo; echo "===== $* ====="; }
show(){ for f in "$@"; do [ -f "$f" ] && { echo "--- $f ($(wc -l <"$f") lines)"; cat "$f"; }; done; }
fnd(){ find "$D" "$WORK" -maxdepth 5 \( -path '*/.venv' -o -path '*/mlvc-tools' -o -path '*/phase2/step4/*_*' \) -prune -o -name "$1" -print 2>/dev/null; }

sec env
date; sw_vers | tr '\n' ' '; echo
echo "WORK=$WORK"; echo "TOOLS=$TOOLS"; echo "BENCH=$BENCH"; echo "MLVC=$MLVC"; echo "PY=$PY"
ffmpeg -version 2>/dev/null | head -1
"$PY" -c "import torch,lpips,cv2,numpy,scipy;print('torch',torch.__version__,'cv2',cv2.__version__,'numpy',numpy.__version__,'scipy',scipy.__version__,'mps',torch.backends.mps.is_available())"
df -h "$WORK" | tail -1

sec "settings.sh and settings_phase2.sh"
show "$D/settings.sh" "$D/settings_phase2.sh"

sec "E6 scripts"
show "$D/quality_rd_faces.sh"
for n in rd_points.py quality_tools.py face_metrics.py; do for f in $(fnd "$n"); do show "$f"; done; done
for f in $(fnd facebox.swift); do echo "--- $f"; head -80 "$f"; done
ls -la "$(dirname "$(fnd facebox.swift | head -1)")" 2>/dev/null

sec "scripts in d that call prepare / decode"
grep -l -E 'prepare|mlvc.* decode|\$MLVC' "$D"/* 2>/dev/null | grep -v '/out_' | while read f; do echo "--- $f"; head -120 "$f"; done

sec "tool help"
"$BENCH" --help 2>&1 | head -60
echo "--- prepare"; "$BENCH" prepare --help 2>&1 | head -60
echo "--- mlvc"; "$MLVC" --help 2>&1 | head -40
echo "--- mlvc decode"; "$MLVC" decode --help 2>&1 | head -60

sec "E6 outputs"
for f in $(fnd rd_eval.csv); do
  echo "--- $f"; wc -l "$f"; head -3 "$f"
  d=$(dirname "$f"); echo "dir $d:"; ls "$d" | head -40; du -sh "$d"
done
echo "face-box caches:"; find "$WORK" -maxdepth 6 -path '*/.venv' -prune -o \( -iname '*face*' -a \( -name '*.json' -o -name '*.csv' -o -name '*.npy' -o -type d \) \) -print 2>/dev/null | head -20

sec "split"
"$PY" - "$WORK/data/split.json" <<'P'
import json,sys
s=json.load(open(sys.argv[1])); print({k:(len(v) if isinstance(v,list) else v) for k,v in s.items()})
for k,v in s.items():
    if isinstance(v,list): print(k, v)
P

sec "data"
M="$WORK/data/vcd_1080p/mp4/th"; echo "1080p mp4: $(ls "$M" | wc -l) files"; ls "$M" | head -3
f=$(ls "$M"/*.mp4 | head -1)
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=width,height,pix_fmt,r_frame_rate,nb_read_frames,codec_name -of csv=p=0 "$f"
Y=~/mlvc/data/VCD/yuv/640x360_30fps/s1; echo "360p yuv: $(ls "$Y" | wc -l) files"; ls -l "$Y" | head -4
f=$(ls "$Y"/* | head -1); echo "frames in first 360p yuv: $(( $(stat -f%z "$f") / (640*360*3/2) ))"

sec bundles
ls -d "$WORK"/bundles/*; for b in "$WORK"/bundles/*; do echo "--- $b"; ls "$b"; done

sec "X3 table_feasible.csv"
cat "$WORK/phase2/step4/table_feasible.csv" 2>/dev/null || echo missing
