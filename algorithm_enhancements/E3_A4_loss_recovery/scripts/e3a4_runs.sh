#!/bin/bash
# E3 + A4: recovery from packet loss (wait for the next I-frame / forced I-frame / recovery from a long-term reference)
# and long-term references marked when the content settles (A4), on B* and MLVC-S 540p, 31 clips, QP 24 and 32.
# Builds the e3a4 program (only when e3a4.cpp changed), a 1-minute check, the 124 runs (RESUMABLE), the analysis.
# Quality only: normal Mac, no quiet mode needed. Charger in, lid open. ~4 h. Output: phase2/e3a4/
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"
exec > >(tee -a "$D/out_e3a4_runs.txt") 2>&1
H="$WORK/harness_e3a4"; O="$WORK/phase2/e3a4"; mkdir -p "$O/logs"
echo; echo "== E3 + A4 START  $(date '+%a %d %b %I:%M %p')"
bad=0
for f in "$WORK/bundles/mlvc" "$WORK/bundles/mlvcs_540p" "$WORK/data/split.json" "$WORK/libmlvc/examples/minimal-fetchcontent" "$WORK/phase2/a3/m1080"; do
  [ -e "$f" ] && echo "   ok  $f" || { echo "   MISSING  $f"; bad=1; }
done
command -v ffmpeg >/dev/null || { echo "   MISSING ffmpeg"; bad=1; }
[ $bad = 0 ] || { echo "== PRE-FLIGHT FAILED: nothing was run"; exit 1; }
if ! cmp -s "$D/e3a4.cpp" "$H/main.cpp" || [ ! -x "$H/build/ninja-release/libmlvc_example" ]; then
  echo "== building the e3a4 program in $H  ($(date '+%I:%M %p'))"
  rm -rf "$H"; cp -R "$WORK/libmlvc/examples/minimal-fetchcontent" "$H"; cp "$D/e3a4.cpp" "$H/main.cpp"
  BO=""; BS=$(ls -d "$WORK"/harness_a0/build/ninja-release/_deps/boost-src "$WORK"/harness*/build/ninja-release/_deps/boost-src 2>/dev/null | head -1)
  [ -n "$BS" ] && BO="-DFETCHCONTENT_SOURCE_DIR_BOOST=$BS" && echo "   using the Boost sources already downloaded: $BS"
  ( cd "$H" && cmake -S . -B build/ninja-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64 \
      -DBUILD_SHARED_LIBS=OFF -DFETCHCONTENT_SOURCE_DIR_LIBMLVC="$WORK/libmlvc" $BO > "$O/logs/build.log" 2>&1 \
    && cmake --build build/ninja-release >> "$O/logs/build.log" 2>&1 ) || { echo "== BUILD FAILED, see $O/logs/build.log"; tail -25 "$O/logs/build.log"; exit 1; }
  echo "   built"
fi
echo "== check: one clip, 120 frames, 4 combinations"
"$PY" -u "$D/e3a4_runner.py" check || { echo "== CHECK FAILED: the runs were not started (see $O/logs/check.log)"; exit 1; }
for pass in 1 2; do
  echo; echo "== pass $pass  $(date '+%I:%M %p')"
  caffeinate -ims "$PY" -u "$D/e3a4_runner.py"
done
echo; echo "== analysis  $(date '+%I:%M %p')"
"$PY" "$D/e3a4_tables.py"
cp "$D/out_e3a4_runs.txt" "$O/results/" 2>/dev/null
echo "== E3 + A4 END  $(date '+%a %d %b %I:%M %p')"
