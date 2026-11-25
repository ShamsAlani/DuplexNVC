#!/bin/bash
# Analyse whatever Step 5 has finished so far (safe to run while ./drift_runs.sh is running). Output: phase2/5/results/
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"
exec > >(tee "$D/out_drift_analysis.txt") 2>&1
"$PY" "$D/drift_tables.py"
