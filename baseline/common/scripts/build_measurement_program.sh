#!/bin/bash
D=$(cd "$(dirname "$0")" && pwd); . "$D/settings.sh"
exec > >(tee "$D/out_build_measurement_program.txt") 2>&1
echo "== rebuilding the measurement program with the fixed code"
cp "$D/main.cpp" "$WORK/harness/main.cpp"
cp "$D/main.cpp" "$TOOLS/duplex_bench.cpp"
cmake --build "$WORK/harness/build/ninja-release" 2>&1 | tail -5
echo "fixed-version check (must be 13): $(grep -c 'Clock::now()' "$WORK/harness/main.cpp")"
"$BENCH" 2>&1 | head -1
echo "Next: ./smoke_test_mlvcs_540p.sh"
