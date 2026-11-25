#!/bin/bash
# STEP 4 results: table of feasible settings (timing, real-time, energy, memory) -> phase2/step4/table_feasible.csv
D=$(cd "$(dirname "$0")" && pwd); . "$D/settings.sh"; . "$D/settings_phase2.sh"
exec > >(tee "$D/out_placement_summary.txt") 2>&1
"$PY" "$D/step4_sum.py" "$WORK" "$TOOLS"
