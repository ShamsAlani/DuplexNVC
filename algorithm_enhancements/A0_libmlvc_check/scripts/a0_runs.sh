#!/bin/bash
# A0: does libmlvc do what A1, A3 and A4 ask of it? Three checks on B* (full MLVC 360p, encoder on the NE), 120 frames
# of the camera clip: forced key frames, external LTR marking + recovery, a different QP on every frame. Each stream is
# decoded twice on the NE and once on the GPU and compared with the encoder frame by frame. ~5 min (first build ~3 min).
# Any Mac state (correctness only, nothing timed). Do NOT run during an energy run. Output: phase2/a0/, out_a0_runs.txt
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"; exec > >(tee -a "$D/out_a0_runs.txt") 2>&1
H="$WORK/harness_a0"; O="$WORK/phase2/a0"; mkdir -p "$O"
echo; echo "== A0 START  $(date)"
IN="$WORK/data/nv12/bl_camera_640x360.nv12"; BU="$WORK/bundles/mlvc"
for f in "$IN" "$BU" "$WORK/libmlvc/examples/minimal-fetchcontent"; do [ -e "$f" ] || { echo "MISSING $f"; exit 1; }; done
if ! cmp -s "$D/a0.cpp" "$H/main.cpp" || [ ! -x "$H/build/ninja-release/libmlvc_example" ]; then
  echo "== building the A0 program in $H"
  rm -rf "$H"; cp -R "$WORK/libmlvc/examples/minimal-fetchcontent" "$H"; cp "$D/a0.cpp" "$H/main.cpp"
  ( cd "$H" && cmake -S . -B build/ninja-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64 \
      -DBUILD_SHARED_LIBS=OFF -DFETCHCONTENT_SOURCE_DIR_LIBMLVC="$WORK/libmlvc" > "$O/build.log" 2>&1 \
    && cmake --build build/ninja-release >> "$O/build.log" 2>&1 ) || { echo "BUILD FAILED, see $O/build.log"; tail -25 "$O/build.log"; exit 1; }
fi
"$H/build/ninja-release/libmlvc_example" --bundles "$BU" --input "$IN" --size 640x360 --frames 120 --qp 26 --out "$O" 2> "$O/a0.log"
rc=$?
grep -E "^manager|^model|^== |frame " "$O/a0.log"
echo "== A0 END  $(date)  exit $rc   (results: $O/summary.txt and the three CSV files)"
