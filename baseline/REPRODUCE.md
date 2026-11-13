# Reproducing the baseline

This guide reruns all nine experiments from scratch on an Apple Silicon Mac and rebuilds every result. Paths assume the scripts live in `~/Downloads/d` and the work folder is `~/Downloads/duplexnvc-baseline` (`$WORK`). Change both in `common/scripts/v` if yours differ.

Total laptop time: about **29 hours** of runs (experiments 01–06 ≈ 5.3 h, 07 ≈ 2.3 h, 08 ≈ 0.5 h, 09 ≈ 21.4 h), plus downloads.

---

## 1. What you need

**Hardware.** An Apple Silicon Mac. To reproduce our numbers exactly, use an M4 Pro. Another chip will give different milliseconds, but the same conclusions should hold.

**Software.**
- macOS 26.x and the Xcode Command Line Tools (`xcode-select --install`). Full Xcode is not needed.
- Homebrew packages: `cmake` (version 3.30 or later), `ninja`, `git-lfs`, `ffmpeg`, `python@3.12`, `uv`.
- Python packages, in a virtual environment: `numpy`, `scipy`, `opencv-python-headless`, `lpips`, `torch`, `torchvision`.
- About 25 GB of free disk space: several GB for the 360p VCD archive, 450 MB for the 1080p references, the builds, the models, and about 10 GB for the bundles, streams and records of experiments 07–09.
- Internet access for the downloads only. Every measurement runs offline.

**Sources and downloads.**

| What | From | Used for |
|---|---|---|
| libmlvc, commit `eb5d60a` | `github.com/microsoft/libmlvc` (Git LFS) | Codec runtime, MLVC-S bundle, 4 test clips, HEVC anchor for BD-rate |
| mlvc-tools | `github.com/microsoft/mlvc` (cloned as `mlvc-tools`) | Converting full MLVC to Core ML |
| Full MLVC PSNR weights | `https://mlvideopub.blob.core.windows.net/mlvc/models/mlvc-psnr-v1.ckpt` (70 MB) | The baseline model |
| MLVC-S PSNR weights | `https://mlvideopub.blob.core.windows.net/mlvc/models/mlvc-s-psnr-v1.ckpt` (downloaded by `2a`) | MLVC-S rows of experiments 08–09 |
| VCD 360p raw YUV | `https://mlvideopub.blob.core.windows.net/mlvc/datasets/VCD/640x360_30fps.tar` | Quality evaluation clips (scenario s1) |
| VCD 1080p MP4 | `github.com/microsoft/VCD` list, `vcdpublic.blob.core.windows.net` (script `./f`) | Display-scale reference |
| LPIPS AlexNet weights | `https://download.pytorch.org/models/alexnet-owt-7be5be79.pth` | Face LPIPS |

---

## 2. One-time setup

Every command below runs in Terminal. Turn on `#` comments in zsh first with `setopt interactivecomments`. Everything lives in `~/Downloads/duplexnvc-baseline` (called `$WORK`), and the scripts live in `~/Downloads/d`.

```bash
setopt interactivecomments
export WORK=~/Downloads/duplexnvc-baseline TOOLS=~/Downloads/duplexnvc-baseline/tools
mkdir -p "$WORK"/{tools,bundles/mlvc,bundles/mlvc-s,data,runs} ~/Downloads/d
```

**Step 1. Tools.**
```bash
xcode-select --install                  # skip if already installed
brew install cmake ninja git-lfs ffmpeg python@3.12 uv
git lfs install
python3 -m venv "$WORK/.venv"
"$WORK/.venv/bin/pip" install numpy scipy opencv-python-headless lpips torch torchvision
mkdir -p ~/.cache/torch/hub/checkpoints
curl -L -o ~/.cache/torch/hub/checkpoints/alexnet-owt-7be5be79.pth \
     https://download.pytorch.org/models/alexnet-owt-7be5be79.pth
```

**Step 2. libmlvc at the pinned commit.**

If a clone is interrupted, delete the folder and clone again with `GIT_LFS_SKIP_SMUDGE=1`, then run `git lfs pull`.
```bash
cd "$WORK"
git clone https://github.com/microsoft/libmlvc.git && cd libmlvc
git checkout eb5d60a && git lfs pull
git rev-parse --short HEAD > "$WORK/LIBMLVC_COMMIT.txt"
ls -lh data/model_bundles               # the coreml-apple .tar must be ~13 MB, not 133 bytes
cmake --preset mac-arm64-ninja-release
cmake --build --preset mac-arm64-ninja-release
cmake --install build/mac-arm64-ninja-release
cp data/model_bundles/*coreml-apple*.tar "$WORK/bundles/mlvc-s/"    # MLVC-S (Phase 1 check)
```

**Step 3. Convert full MLVC (PSNR) to Core ML.**

The converter checks the model on a VCD clip, so first create that clip from libmlvc's NV12 test clip. We created it through `~/mlvc` linked to `$WORK/mlvc-home`.
```bash
mkdir -p "$WORK/mlvc-home" && ln -s "$WORK/mlvc-home" ~/mlvc
mkdir -p ~/mlvc/job-outputs/pretrained ~/mlvc/data/VCD/yuv/640x360_30fps/s1
curl -L -o ~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt \
     https://mlvideopub.blob.core.windows.net/mlvc/models/mlvc-psnr-v1.ckpt
gunzip -c "$WORK/libmlvc/data/test_data/clips/VCD_s1_0380a3_640x360_30fps.nv12.gz" > /tmp/c360.nv12
ffmpeg -v error -f rawvideo -pix_fmt nv12 -s 640x360 -i /tmp/c360.nv12 -f rawvideo -pix_fmt yuv420p \
  ~/mlvc/data/VCD/yuv/640x360_30fps/s1/0380a333cb0fef69001fb4260e2a705f_640x360_30fps.yuv
cd "$WORK" && git clone https://github.com/microsoft/mlvc.git mlvc-tools && cd mlvc-tools
uv sync --extra onnxruntime && uv pip install packages/msrtc_rans
cp video/conversion/_full_model/model_configs_example.yaml video/conversion/_full_model/model_configs.yaml
cd video
uv run convert.py bundle --model-version dmc61sbr_reglu \
  --weights-path ~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt --weights-version psnr_v1 \
  --model-input-sizes 640x368 --mlvc-version v0.1 --model-type coreml --target-device apple
# copy the produced coreml bundle .tar into $WORK/bundles/mlvc/
```

**Step 4. The measurement program and tools.**
```bash
cp <repo>/baseline/common/code/* "$TOOLS/"
find <repo>/baseline -path '*/scripts/*' -type f ! -name README.md -exec cp {} ~/Downloads/d/ \;
cp <repo>/baseline/common/code/{mlplan.swift,thermal_log.swift} ~/Downloads/d/
chmod +x ~/Downloads/d/*
cp -R "$WORK/libmlvc/examples/minimal-fetchcontent" "$WORK/harness"
cp "$TOOLS/duplex_bench.cpp" "$WORK/harness/main.cpp"
cd "$WORK/harness"
cmake -S . -B build/ninja-release -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_OSX_ARCHITECTURES=arm64 -DBUILD_SHARED_LIBS=OFF \
      -DFETCHCONTENT_SOURCE_DIR_LIBMLVC="$WORK/libmlvc"
cmake --build build/ninja-release
swiftc -O "$TOOLS/facebox.swift" -o "$TOOLS/facebox"
cd ~/Downloads/d && ./b                 # must print "fixed-version check (must be 13): 13"
```

**Step 5. 360p VCD clips** (Wi-Fi on). This takes a while; `-C -` resumes an interrupted download.
```bash
cd ~/mlvc/data/VCD/yuv
curl -C - -L -o 640x360_30fps.tar https://mlvideopub.blob.core.windows.net/mlvc/datasets/VCD/640x360_30fps.tar
```

All paths the scripts use are set in `~/Downloads/d/v` (from `baseline/common/scripts/v`). Change them there if your folders differ.

---


## 3. Quiet mode

Every **timed** experiment (02, 03, 06, 07, 09) runs in quiet mode, because the operating system easily disturbs timing and energy, and idle power is subtracted from run power:

1. Charger plugged in (`pmset -g batt` says `AC Power`); Low Power Mode off.
2. **Wi-Fi off** and **Bluetooth off** (on only between experiments, to download data or copy results).
3. System Settings → Displays: **automatic brightness off**, **True Tone off**, brightness at **maximum**.
4. Quit every app except Terminal, and leave the Mac alone during the runs.
5. `cd ~/Downloads/d && ./p` (keep-awake, Spotlight paused); `./u` afterwards undoes it.

Every timed run is followed by a rest of equal length (60 s), modes are interleaved in rounds, and the first 64 frames of each direction are discarded.

## 4. Running the experiments

Run everything from `~/Downloads/d`, in this order. Each script saves its console output as `out_<name>.txt` next to it.

| Order | Command | Experiment folder | What | Time | Conditions |
|---|---|---|---|---|---|
| 1 | `./s` | `01_smoke_test_experiment` | S1: smoke test, MLVC-S 540p | 3 min | any |
| 2 | `./m` | `common` | 360p camera and incoming streams; incoming at QP 26 | 2 min | any |
| 3 | `./t` | `01_smoke_test_experiment` | S2: smoke test, full MLVC 360p | 3 min | any |
| 4 | `./f` | `05_quality_experiment` | Download 40 talking-head clips at 1080p | 10 min | Wi-Fi on |
| 5 | `./q` | `05_quality_experiment` | BD-rate vs Intel HW HEVC; R-D on the 4 timing clips | 5 min | any |
| 6 | `./g` | `05_quality_experiment` | Split (seed 694); R-D, display and face quality on 20 evaluation clips | 20 min | 360p archive downloaded |
| 7 | `./p` | `common` | Quiet mode on | 1 min | see §3 |
| 8 | `./e` then `./r` | `02_phase1_check_experiment` | E3a: MLVC-S 540p, 5 rounds + 3 paced, comparison with Phase 1 | 45 min | **quiet** |
| 9 | `./w` | `06_energy_experiment` | E7: 120 s idle + 5 paced B\* runs with `powermetrics` | 15 min | **quiet**, password |
| 10 | `./x` | `03_timing_experiment` | E1–E4 and B\*: 5 unpaced rounds, 5 paced duplex, 3 paced turns, 3 CLI; summary `./y` | 65 min | **quiet** |
| 11 | `./c` | `04_correctness_experiment` | E5: decode B\*'s stream on NE (×2), GPU, CPU; drift | 5 min | any |
| 12 | `./1t` | `07_processor_experiment` | Core ML placement trace | 2 min | any |
| 13 | `./1` then `./1r` | `07_processor_experiment` | X1: 72 runs, each network alone on NE, GPU, CPU, unpaced and paced | 2 h 20 min | **quiet**, password |
| 14 | `./u` | `common` | Quiet mode off (Wi-Fi on for the next step) | 1 min | — |
| 15 | `./2a` | `08_model_conversion_experiment` | X2: convert 6 new bundles + multi-size, trace | 30–45 min | Wi-Fi on |
| 16 | `./2b` | `08_model_conversion_experiment` | X2: streams per resolution; incoming at QP 26 | 15 min | any |
| 17 | `./p` | `common` | Quiet mode on | 1 min | see §3 |
| 18 | `./all` | `09_placement_experiment` | X3: 584 runs, every setting × placement (calls `./2r`) | 21.4 h | **quiet**, password; **resumable** |
| 19 | `./4r` | `09_placement_experiment` | Table of feasible settings | 1 min | any |
| 20 | `./u`, `./z` | `common` | Quiet mode off; collect raw results | 2 min | any |

Do not press Ctrl-C during `./x`, `./w` or `./1`; a rerun moves the old folder aside. `./all` is the exception: interrupt it at any time and run it again, and it continues where it stopped.

Check that every run used the processor it asked for:
```bash
python3 -c "import re; t=open('$HOME/Downloads/d/out_all.txt').read(); p=re.findall(r'requested=(\w+) resolved=(\w+)', t); print(len(p), 'unit reports,', sum(a!=b for a,b in p), 'mismatches')"
```
Our run: `844 unit reports, 0 mismatches`.

## 5. Getting the results

1. Copy each experiment's run folders and logs from `$WORK` and `~/Downloads/d` into its `raw_data/` (see each experiment's README for the folder names), or use the packing commands in `09_placement_experiment/raw_data/README.md`.
2. Rebuild every table and figure (Python 3 and matplotlib):
   ```bash
   cd baseline/common/analysis
   python3 recompute_all.py        # tables of 01–06, into each experiment's results/
   python3 make_figures.py         # figures of 03–06
   python3 make_tables_x3.py       # tables of 09
   ```
3. Compare with each experiment's README. On an M4 Pro (24 GB, macOS 26.6), timing should agree within about 2 % and energy within about 5 %; quality values should be identical. On another Apple Silicon chip the milliseconds differ, but the conclusions should hold.

Key values to check:

| Check | Expected |
|---|---|
| B\* (03): late frames; p99 send / receive | 0 %; 29.3 / 28.9 ms |
| Sharing speedup S (03) | 1.11 (ideal 1.99) |
| Energy per frame pair (06) | 65.3 mJ |
| BD-rate vs Intel HW HEVC (05) | −31.2 % (Y) |
| Placement trace (07) | full MLVC 313 / 316 ops on the NE, 100.0 % of cost |
| NE alone, full MLVC 360p / 540p / 720p / 1080p (09) | 5.86 / 11.83 / 22.23 / 46.36 ms (encoder) |
| Feasibility count (09) | 30 fps: 22 (23 with B\*); 15 fps only: 9; infeasible: 6 |

## 6. Problems we hit and how they are fixed

| Problem | Fix (already in this package) |
|---|---|
| Unpaced runs never ended | `duplex_bench.cpp` schedules unpaced frames at the current time; `./b` checks the fixed version (13 occurrences of `Clock::now()`) |
| First frame slow (model load) | The program warms up before t0; the first 64 frames are excluded from statistics |
| Xcode generator missing | The harness is built with Ninja (Step 4) |
| Interrupted git clone | Clone with `GIT_LFS_SKIP_SMUDGE=1`, then `git lfs pull` |
| Full-MLVC conversion needs a VCD clip | Created from libmlvc's NV12 clip (Step 3) |
| LPIPS weights SSL error | Weights downloaded into the torch cache (Step 1) |
| `./w` hung after the runs | `wait $!` instead of `wait` (fixed in `scripts/w`) |
| zsh treats `#` as text | `setopt interactivecomments` |
| Model conversion (`2a`) failed for every size | The 1080p MP4s are in `vcd_1080p/mp4/th/`, and the converter names the 1080p test clip `<id>_1920x1080_30.yuv`; `s2cfg` and `2a` use both |
| A 22-hour run can be interrupted | `all` skips finished runs and appends to its log |
| `sudo` expiring during long runs | `1` and `all` refresh `sudo` every 50 s in the background |
