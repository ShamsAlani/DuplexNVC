#!/bin/bash
# Step 5 + A2: correctness of every encoder->decoder pair (NE/GPU/CPU) and drift bounds, all 7 settings,
# 20 evaluation clips x QP 16/24/32/40. One unattended, RESUMABLE run (Ctrl-C any time; ./drift_runs.sh again continues).
#   main  9 pairs per clip and QP with the B* structure (failures, drift by position, BD-rate change, determinism)
#   A2    the same with I-frame every 32 / 16 and LTR recovery every 32 / 16 frames
# Order: main for every setting first (priority 360p, MLVC-S 720p, MLVC-S 540p, full 540p, full 720p, MLVC-S 1080p,
# full 1080p), then A2 setting by setting. Results can be analysed at any time with ./an.
# Options: PHASE=main ./drift_runs.sh (only main) | PHASE=a2 ./drift_runs.sh | ONLY="mlvc_360p mlvcs_720p" ./drift_runs.sh
# Normal Mac use is fine (no quiet mode). Charger in, lid open. Output: ~/Downloads/duplexnvc-baseline/phase2/5/
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"
exec > >(tee -a "$D/out_drift_runs.txt") 2>&1
O="$WORK/phase2/5"; mkdir -p "$O"
echo; echo "== Step 5 START  $(date)   PHASE=${PHASE:-all} ONLY=${ONLY:-all settings}"
sw_vers | tr '\n' ' '; echo; echo "libmlvc $(cat "$WORK/LIBMLVC_COMMIT.txt" 2>/dev/null)"; pmset -g batt | head -1
{ date; sw_vers; echo "libmlvc $(cat "$WORK/LIBMLVC_COMMIT.txt" 2>/dev/null)"; } >> "$O/run.txt"

echo "== pre-flight"
bad=0
for f in "$MLVC" "$PY" "$WORK/data/split.json" "$WORK/bundles/mlvc" "$WORK"/bundles/{mlvc,mlvcs}_{540p,720p,1080p}; do
  [ -e "$f" ] && echo "   ok  $f" || { echo "   MISSING  $f"; bad=1; }
done
n=$("$PY" -c "import json,os;e=json.load(open('$WORK/data/split.json'))['evaluation'];print(sum(os.path.exists('$WORK/data/vcd_1080p/mp4/th/%s_1920x1080_30.mp4'%i) for i in e))")
echo "   evaluation MP4s present: $n of 20"; [ "$n" = 20 ] || bad=1
command -v ffmpeg >/dev/null && echo "   ok  ffmpeg" || { echo "   MISSING ffmpeg"; bad=1; }
"$MLVC" encode --help 2>&1 | grep -q -- "--ltr-recovery-period" && echo "   ok  mlvc encode has the LTR options" \
  || { echo "   mlvc encode has no --ltr-recovery-period"; bad=1; }
"$PY" -c "import numpy, scipy, matplotlib; print('   ok  python: numpy', numpy.__version__, 'scipy', scipy.__version__)" || bad=1
free=$(df -g "$WORK" | tail -1 | awk '{print $4}'); echo "   free disk: ${free} GB (need ~60)"; [ "$free" -ge 60 ] || bad=1
[ $bad = 0 ] || { echo "== PRE-FLIGHT FAILED: nothing was run. Fix the items above and run ./drift_runs.sh again."; exit 1; }

for pass in 1 2 3; do
  echo; echo "== pass $pass  $(date)"
  caffeinate -ims "$PY" -u "$D/drift_runner.py"
  echo "== after pass $pass  $(date)"
  "$PY" - "$O/r.csv" <<'P'
import csv, json, os, sys
p = sys.argv[1]
done = {(r["setting"], r["variant"], r["clip"], r["qp"]) for r in csv.DictReader(open(p))} if os.path.exists(p) else set()
ph, only = os.environ.get("PHASE", "all"), os.environ.get("ONLY", "").split()
S = [s for s in ["mlvc_360p", "mlvcs_720p", "mlvcs_540p", "mlvc_540p", "mlvc_720p", "mlvcs_1080p", "mlvc_1080p"] if not only or s in only]
V = (["main"] if ph in ("main", "all") else []) + (["i32", "l32", "i16", "l16"] if ph in ("a2", "all") else [])
need = len(S) * len(V) * 20 * 4
have = sum(1 for d in done if d[0] in S and d[1] in V)
print(f"   jobs done {have} of {need}")
open("/tmp/s5_left", "w").write(str(need - have))
P
  [ "$(cat /tmp/s5_left)" -le 0 ] && break
done

echo; echo "== analysis  $(date)"
"$PY" "$D/drift_tables.py"
cp "$D/out_drift_runs.txt" "$O/results/" 2>/dev/null
echo; echo "== Step 5 END  $(date)"
