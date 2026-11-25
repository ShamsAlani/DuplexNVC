#!/bin/bash
# A1 round 2 + E4: B* I-frame offsets -8/-10; MLVC-S 540p (which does mark LTRs) I / LTR / both offsets; and E4 =
# the offsets on top of A2's drift bound (LTR recovery every 32 frames). 20 evaluation clips x QP 16/24/26/32/40 x
# 10 configurations = 1000 runs (~2.5-3 h). Normal Mac use is fine; charger in, lid open. RESUMABLE.
#   check: MLVC-S 540p offset 0 must give bitstreams identical to experiment 10's (proves the rebuilt program
#   changes nothing when no option is used)
# Output: ~/Downloads/duplexnvc-baseline/phase2/a1b/ ; console: out_a1_round2_runs.txt
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"; exec > >(tee -a "$D/out_a1_round2_runs.txt") 2>&1
H="$WORK/harness_a1"; O="$WORK/phase2/a1b"; mkdir -p "$O"
echo; echo "== A1b START  $(date)"; pmset -g batt | head -1
for f in "$D/../4b/quality_runner.py" "$WORK/phase2/4b/bits/mlvcs_540p_npu-npu" "$WORK/phase2/a1/q.csv" "$H/build/ninja-release/libmlvc_example"; do
  [ -e "$f" ] || { echo "MISSING $f"; exit 1; }; done
cmp -s "$D/duplex_bench.cpp" "$H/main.cpp" || { echo "the program in $H is not the current one: run ../a3/a3_runs.sh first (it rebuilds)"; exit 1; }
echo; echo "== check (first clip, QP 26, o0 and r0)"
set -o pipefail; caffeinate -ims "$PY" -u "$D/a1b.py" check | tee /tmp/a1b_chk.txt || exit 1; set +o pipefail
grep -q "identical to experiment 10's bitstreams: 1 of 1" /tmp/a1b_chk.txt || { echo "== CHECK FAILED: offset 0 does not reproduce experiment 10 (nothing else run)"; exit 1; }
grep -E "r0 .*recovery [1-9]" /tmp/a1b_chk.txt >/dev/null || echo "   NOTE: r0 shows no recovery frames in the frame log; E4 results will say so"
for pass in 1 2; do echo; echo "== runs, pass $pass  $(date)"; caffeinate -ims "$PY" -u "$D/a1b.py"; done
echo; echo "== analysis  $(date)"
"$PY" "$D/a1bana.py"
cp "$D/out_a1_round2_runs.txt" "$O/results/" 2>/dev/null
echo "== A1b END  $(date)"
