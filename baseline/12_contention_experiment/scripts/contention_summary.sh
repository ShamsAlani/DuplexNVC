#!/bin/bash
# Contention curve of the M4 Pro. Any conditions, 1 min. Output: $WORK/phase2/ct/M4_contention_curve.csv ; console: out_contention_summary.txt
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"; exec > >(tee "$D/out_contention_summary.txt") 2>&1
"$PY" "$D/contention_sum.py" "$WORK/phase2/ct" M4 "$TOOLS"
echo "M1 for comparison (cross-chip study, 20 Nov): encoder alone 9.49 -> 11.27 ms at 0 -> 75 % (+18.8 %); B* send late 3.97 % at 0 %, 0 % at 25 %"
