#!/bin/bash
# PHASE 2 STEP 2 results: NE speed per bundle vs survey Table 11 (M3 Pro), multi-size vs single, memory
D=$(cd "$(dirname "$0")" && pwd); . "$D/settings.sh"; . "$D/settings_phase2.sh"
exec > >(tee "$D/out_conversion_summary.txt") 2>&1
"$PY" "$D/step2_sum.py" "$S2" "$TOOLS"
