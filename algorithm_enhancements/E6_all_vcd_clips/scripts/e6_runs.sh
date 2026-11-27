#!/bin/bash
# E6, A2 part: A2's drift bound (LTR recovery every 32 frames) against MLVC's default structure on all 160 VCD clips,
# MLVC-S 540p and B*, QP 16/24/32/40, encoder and decoder on the NE and the GPU. 2,560 jobs, about 25-30 h in all:
# it fills the nights until it is done. RESUMABLE: stop it with Ctrl-C whenever the Mac is needed; ./e6_runs.sh continues.
# th-m clips are portrait: E6_PORTRAIT=rotate runs them turned 90 degrees, skip (default) leaves them out.
# Quality only: no quiet mode needed. Charger in, lid open. Needs the clips from ./e6_download.sh. Output: phase2/e6/
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"
exec > >(tee -a "$D/out_e6_runs.txt") 2>&1
echo; echo "== E6 (A2 on 160 clips) START  $(date '+%a %d %b %I:%M %p')"
bad=0
for f in "$MLVC" "$WORK/bundles/mlvc" "$WORK/bundles/mlvcs_540p" "$VCD1080/VCD/download/mp4_list.txt"; do
  [ -e "$f" ] && echo "   ok  $f" || { echo "   MISSING  $f"; bad=1; }
done
free=$(df -g "$WORK" | tail -1 | awk '{print $4}'); echo "   free disk: ${free} GB (need ~20)"; [ "$free" -ge 20 ] || bad=1
[ $bad = 0 ] || { echo "== PRE-FLIGHT FAILED: nothing was run"; exit 1; }
[ -e "$VCD1080/.e6_downloading" ] && echo "   the download is still running: each pass starts with the clips already here"
for pass in 1 2 3 4 5 6; do
  echo; echo "== pass $pass  $(date '+%I:%M %p')"
  caffeinate -ims "$PY" -u "$D/e6_runner.py"
  "$PY" - "$WORK/phase2/e6/r.csv" <<'P' && break
import csv, os, sys
p = sys.argv[1]
n = len({(r["setting"], r["variant"], r["clip"], r["qp"]) for r in csv.DictReader(open(p))}) if os.path.exists(p) else 0
print(f"   jobs done: {n} of 2560"); sys.exit(0 if n >= 2560 else 1)
P
done
"$PY" "$D/e6_tables.py"
echo "== E6 END  $(date '+%a %d %b %I:%M %p')"
