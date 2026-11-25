#!/bin/bash
D=$(cd "$(dirname "$0")" && pwd); . "$D/settings.sh"
exec > >(tee "$D/out_timing_summary.txt") 2>&1
R="$WORK/runs/bl_bstar"
echo "== B* results (full MLVC, 360p, NE)  $(date)"
"$PY" "$D/sum.py" "$R" T
echo "== libmlvc CLI cross-check (last summary lines per run)"
for f in "$R"/T_cli_r*.log; do echo "-- $f"; grep "^|" "$f"; done
echo "Saved to $D/out_timing_summary.txt."
