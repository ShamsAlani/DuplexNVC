# Mohammed's M1 steps, 18 November – 3 December

This folder holds everything Mohammed Alawadhi runs on his **M1** Mac for the plan *DuplexNVC: Plan to 3 December*: the cross-chip study (setup, timing, decode drift, contention, energy, Days 1–5) and the real call between two laptops (E2, Days 9, 11 and 15). The scripts are the baseline's own scripts (`baseline/`) with two changes: they read their settings from `vm1` instead of `v`, and **every folder, run and file they write starts with `M1_`**, so nothing on the M1 can be mixed up with Shams's M4 Pro baseline.

The one rule of the plan applies: whoever runs a step owns it: codes it, runs it, analyzes it and writes it up the same day.

| Day | Date | Step (Mohammed, his M1) | Result the plan asks for | Script |
|---|---|---|---|---|
| 1 | Wed 18 Nov | Cross-chip setup | MLVC runs on the M1 | `m1_setup`, `m1_trace` |
| 2 | Thu 19 Nov | Cross-chip timing (night, quiet) | M1 timing table | `m1_timing` → `m1_timing_sum` |
| 3 | Fri 20 Nov | Decode Shams's bitstreams | Does an M4 → M1 call drift? | `m1_decode` |
| 4 | Sat 21 Nov | Contention (evening, quiet) | M1 contention curve | `m1_contention` → `m1_contention_sum` |
| 5 | Sun 22 Nov | Energy (night, quiet) | M1 energy per frame pair | `m1_energy` |
| 9 | Thu 26 Nov | E2: call test on Wi-Fi | Call works between two laptops | `m1_call_build`, `m1_call loopback`, `m1_call` |
| 11 | Sat 28 Nov | E2: real call, all three laptops | Delay, lost frames and drift in a real call | `m1_call` |
| 15 | Wed 2 Dec | E2: extra call, Warda's M4 ↔ M1 | A call between two non-reference chips | `m1_call` |

If the plan falls behind, the drop order is A4, then **the M1 energy run (Day 5)**, then B2 (p = 0.75). Days 1–4 and E2 always run.

### Progress and headline results

| Step | Status | Headline result | Details |
|---|---|---|---|
| Day 1 · Setup | **done** Fri 20 Nov | MLVC runs on the M1's Neural Engine: every network `resolved=npu`, no failure. Full MLVC bundle converted on the M1, 37,048,320 bytes, same size as Shams's | [`01_m1_setup/README.md`](01_m1_setup/README.md) |
| Day 2 · Timing | **done** Fri 20 Nov, 16:55–18:28 | M1 is **1.62× slower** than the M4 Pro, uniformly; NE sharing identical (**S = 1.11** on both). **B\* misses 30 fps on the M1** (7.1 % late sends, p99 37.2 ms); taking turns meets it. MLVC-S 540p borderline (0–6 % late) | [`02_m1_timing/README.md`](02_m1_timing/README.md) |
| Day 3 · Decode drift | to do | needs Shams's three files in `from_m4/` | [`03_m1_decode_drift/README.md`](03_m1_decode_drift/README.md) |
| Day 4 · Contention | **done** Fri 20 Nov, about 20:18–21:12 | 46 GB/s of memory traffic slows the NE by only **19 %**: the NE itself, not memory, limits sharing. A light background load **removes the pacing penalty**: B\* send call 17.6 → 11.3 ms, late frames 4 % → **0 %** | [`04_m1_contention/README.md`](04_m1_contention/README.md) |
| Day 5 · Energy | **done** Fri 20 Nov, evening | B\* costs **121.2 mJ per frame pair** on the M1 against 65.3 on the M4 Pro (**1.86×**), 99 % on the NE (3.6 W vs 1.9 W) | [`05_m1_energy/README.md`](05_m1_energy/README.md) |
| E2 · Real call | to do (Days 9, 11, 15) | — | [`06_m1_e2_call/README.md`](06_m1_e2_call/README.md) |

Machine: MacBook Air (MacBookAir10,1, fanless), Apple M1, 4 performance + 4 efficiency cores, 8 GB, macOS 27.2.1 (26B131). Reference: Shams's MacBook Pro, M4 Pro, 24 GB, macOS 26.6.

---

## 0. Naming: how your results stay apart from Shams's

| | Shams (M4 Pro, the baseline) | **You (M1)** |
|---|---|---|
| Work folder on the Mac | `~/Downloads/duplexnvc-baseline` | `~/Downloads/duplexnvc-m1` |
| Scripts folder | `~/Downloads/d` | `~/Downloads/dm1` |
| Settings file | `v` | `vm1` (`TAG=M1`) |
| Run folders | `runs/bl_bstar/T_duplex30_r1`, `runs/bl_energy/W_r1` | `runs/m1_timing/M1_duplex30_r1`, `runs/m1_energy/M1_energy_r1` |
| MLVC-S 540p runs | `phase2/step1/mlvcs_540p/…` | `runs/m1_timing/M1S_duplex30_r1` |
| Console logs | `~/Downloads/d/out_x.txt` | `~/Downloads/dm1/out_m1_timing.txt` |
| Result tables | `baseline/03_timing_experiment/results/05_Bstar_duplex_paced_30fps.csv` | `crosschip/m1_mohammed/02_m1_timing/results/M1_duplex30.csv` |
| Repository folder | `baseline/<experiment>/` | `crosschip/m1_mohammed/<step>/` |
| Files exchanged with Shams | — | in: `~/Downloads/duplexnvc-m1/from_m4/m4_*`; out: `~/Downloads/duplexnvc-m1/to_m4/m1_*` |

Every run folder has the baseline's layout (`frames.csv`, `run.txt`, `.log`, `.therm`, and `power.txt` for energy runs), so the baseline's analysis tools read M1 runs unchanged. On the Mac everything is under `~/Downloads/duplexnvc-m1/runs/`:

```
runs/
├── m1_setup/        M1_machine.txt, M1_bundle_sha256.txt, trace/          (Day 1)
├── m1_smoke/        M1_smoke_<mode>, M1S_smoke_duplex30                   (Day 1, not data)
├── m1_timing/       M1_<mode>_r<n>, M1_duplex30_r<n>, M1_turns30_r<n>, M1_cli_r<n>, M1S_<mode>_r<n>,
│                    thermal.csv, M1_unpaced.csv, M1_duplex30.csv, M1_turns30.csv, M1_cli.csv, M1S_*.csv, M1_vs_M4Pro.csv  (Day 2)
├── m1_decode/       M4stream_dec_npu.nv12, M1stream_dec_npu.nv12, M1_drift.csv, M1_encoder_vs_M4.txt  (Day 3)
├── m1_contention/   M1_load<0|25|50|75>_<alone-enc|duplex30>_r<n>, M1_memstress_peak.txt, M1_contention_curve.csv (Day 4)
├── m1_energy/       idle/, M1_energy_r<n>, M1_energy_summary.csv, M1_energy_per_run.csv   (Day 5)
└── m1_call/         M1_call_loopback_a|b, M1_call_<label>  (frames.csv, clock.csv, received.mlvc, summary.json)  (E2)
```

In the repository, `./m1_collect` copies each of these into `crosschip/m1_mohammed/0N_<step>/raw_data/` (run records and logs, no video or bitstreams) and the tables into `0N_<step>/results/`. Commit on your own branch, never into `baseline/`.

---

## 1. Get the scripts onto your Mac (once)

Open Terminal and turn on `#` comments: `setopt interactivecomments`.

```bash
cd ~/Downloads
git clone https://github.com/ShamsAlani/DuplexNVC.git        # or: cd DuplexNVC && git pull
cd DuplexNVC && git checkout claude/wizardly-knuth-botxcy     # the branch that holds crosschip/
mkdir -p ~/Downloads/dm1
find ~/Downloads/DuplexNVC/crosschip/m1_mohammed \( -path '*/scripts/*' -o -path '*/common/*' \) -type f ! -name README.md -exec cp {} ~/Downloads/dm1/ \;
chmod +x ~/Downloads/dm1/*
```

If your clone or work folder lives elsewhere, edit the two lines `WORK=` and `REPO=` in `~/Downloads/dm1/vm1`. Every script reads `vm1`; the baseline's `v` is never used.

---

## 2. Day 1 · Setup: does MLVC run on the M1?

**One-time setup** (same as `baseline/REPRODUCE.md` §2, with the M1 work folder; about 1–2 hours of downloads and builds, Wi-Fi on):

```bash
setopt interactivecomments             # zsh only; bash accepts # comments already
export WORK=~/Downloads/duplexnvc-m1 TOOLS=~/Downloads/duplexnvc-m1/tools
mkdir -p "$WORK"/{tools,bundles/mlvc,bundles/mlvc-s,data,runs,from_m4,to_m4}
```

Step 1, tools. On a fresh Mac, install Homebrew first (it also installs the Xcode Command Line Tools), then add it to the shell:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```
Then the packages. `pkg-config` is needed by libmlvc's vcpkg build (without it the `benchmark` port fails and cmake reports "Ninja not found"); the virtual environment uses Homebrew's Python 3.12, not the system Python:
```bash
brew install cmake ninja git-lfs ffmpeg python@3.12 uv pkg-config
git lfs install
/opt/homebrew/bin/python3.12 -m venv "$WORK/.venv"
"$WORK/.venv/bin/pip" install numpy scipy opencv-python-headless lpips torch torchvision
"$WORK/.venv/bin/python3" -c "import numpy, cv2, lpips, torch; print('python packages ok', torch.__version__)"
```

Step 2, libmlvc at the pinned commit `eb5d60a` (the MLVC-S bundle comes with it):
```bash
cd "$WORK"
git clone https://github.com/microsoft/libmlvc.git && cd libmlvc
git checkout eb5d60a && git lfs pull
git rev-parse --short HEAD > "$WORK/LIBMLVC_COMMIT.txt"
ls -lh data/model_bundles               # the coreml-apple .tar must be ~13 MB, not 133 bytes
cmake --preset mac-arm64-ninja-release
cmake --build --preset mac-arm64-ninja-release
cmake --install build/mac-arm64-ninja-release
cp data/model_bundles/*coreml-apple*.tar "$WORK/bundles/mlvc-s/"
```

Step 3, the full MLVC bundle. Microsoft publishes full MLVC only as a PyTorch checkpoint; the Core ML bundle has to be converted, and model bundles are not in the repository (`.gitignore` excludes `*.tar`). Two ways:

- **Convert it on the M1 (what was done on 20 Nov):**
```bash
mkdir -p "$WORK/mlvc-home" && ln -s "$WORK/mlvc-home" ~/mlvc
mkdir -p ~/mlvc/job-outputs/pretrained ~/mlvc/data/VCD/yuv/640x360_30fps/s1
curl -L -o ~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt https://mlvideopub.blob.core.windows.net/mlvc/models/mlvc-psnr-v1.ckpt
gunzip -c "$WORK/libmlvc/data/test_data/clips/VCD_s1_0380a3_640x360_30fps.nv12.gz" > /tmp/c360.nv12
ffmpeg -v error -f rawvideo -pix_fmt nv12 -s 640x360 -i /tmp/c360.nv12 -f rawvideo -pix_fmt yuv420p \
  ~/mlvc/data/VCD/yuv/640x360_30fps/s1/0380a333cb0fef69001fb4260e2a705f_640x360_30fps.yuv
cd "$WORK" && git clone https://github.com/microsoft/mlvc.git mlvc-tools && cd mlvc-tools
git log -1 --format='%h %ad' --date=short > "$WORK/MLVC_TOOLS_COMMIT.txt"
uv sync && uv pip install packages/msrtc_rans          # since Nov 2026 there is no "--extra onnxruntime"
cp video/conversion/_full_model/model_configs_example.yaml video/conversion/_full_model/model_configs.yaml
cd video
uv run convert.py bundle --model-version dmc61sbr_reglu --weights-path ~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt \
  --weights-version psnr_v1 --model-input-sizes 640x368 --mlvc-version v0.1 --model-type coreml --target-device apple \
  2>&1 | tee ~/Downloads/dm1/out_m1_convert.txt
cp output/model_bundles/dmc61sbr_reglu-psnr_v1-coreml-apple-v0.1.tar "$WORK/bundles/mlvc/"
```
  The result on the M1 was 37,048,320 bytes, the same size as Shams's. `mlvc-tools` was at commit `785fb06` (20 Nov), newer than her 10 Nov clone.
- **Or take Shams's copy** (`~/Downloads/duplexnvc-baseline/bundles/mlvc/*.tar`, 35 MB, AirDrop) for byte-identical model files.

Either way, compare `shasum -a 256` of the bundle with Shams's line (`m1_setup` records yours in `runs/m1_setup/M1_bundle_sha256.txt`). The `.tar` holds file timestamps, so equal hashes prove identical files but different hashes do not prove different models; then compare the model files inside the archives.

The 360p VCD archive (Step 5 of the baseline) is **not needed** for your steps: the four timing clips ship with libmlvc.

**Then run:**
```bash
cd ~/Downloads/dm1
./m1_setup          # ~10 min: tools, harness build, bundle checksums, B* streams, smoke tests on the M1
./m1_trace          # optional, 5 min: which operations run on the M1's Neural Engine
```

Check in `out_m1_setup.txt`: `fixed-version check (must be 13): 13`, every `requested=npu resolved=npu`, no `FAILED`, and all smoke runs end. If the paced B\* smoke run shows late frames on the M1, that is not an error: it is the first cross-chip finding, and Day 2 measures it properly.

**Results pointed to:** `runs/m1_setup/M1_machine.txt` (chip, cores, memory, macOS, libmlvc commit), `runs/m1_setup/M1_bundle_sha256.txt`, `runs/m1_smoke/`, `runs/m1_setup/trace/M1_trace.txt`; in the repository `01_m1_setup/results/` and `01_m1_setup/raw_data/`.

---

## 3. Day 2 · Timing (night, quiet): the M1 timing table

Quiet mode exactly as the baseline: charger in, Low Power Mode off, **Wi-Fi and Bluetooth off**, brightness at maximum with automatic brightness and True Tone off, every app closed but Terminal, Mac left alone. A fanless MacBook Air M1 must lie flat on a hard surface; the thermal state is logged every second because the M1 may throttle where the M4 Pro did not.

```bash
cd ~/Downloads/dm1
./m1_prep on               # Low Power Mode off, Wi-Fi and Bluetooth off, brightness max, apps quit; opens Displays settings
./m1_quiet                 # password; Spotlight and Time Machine paused, keep-awake on, checks (must say AC Power)
./m1_timing                # 46 runs, ~92 min, do not press Ctrl-C; calls ./m1_timing_sum at the end
./m1_unquiet
./m1_prep off              # Wi-Fi and Bluetooth back on
```

`m1_prep` does what the command line can; auto-brightness and True Tone (System Settings, Displays), the charger, the lid and the surface stay by hand, and it prints that list.

Run `./m1_status` before starting: it must show `AC Power`, Wi-Fi `Off`, Bluetooth `0`, and only Terminal and Finder as apps. If an app such as Chrome turns out to be open after the run has started, press Ctrl-C, quit the app, and run `./m1_timing` again: the stopped attempt is moved aside as `m1_timing_old_<time>` and not used (this happened on 20 Nov). Follow this chat on a phone, not on the Mac being measured.

What runs: the exact B\* protocol of `baseline/03_timing_experiment/scripts/x` (5 interleaved rounds of turns / encoder alone / decoder alone / duplex unpaced, 5 paced B\* calls, 3 paced turns, 3 `mlvc benchmark` cross-checks), then MLVC-S 540p (3 rounds unpaced, 3 paced calls) for the cross-generation table. Same clips, same QP, same I-frame period, same bundle; only the chip changes.

**Results pointed to:** `runs/m1_timing/M1_unpaced.csv`, `M1_duplex30.csv`, `M1_turns30.csv`, `M1_cli.csv`, `M1S_unpaced.csv`, `M1S_duplex30.csv` (the baseline's metric names, so the tables join), and **`M1_vs_M4Pro.csv`**: M1 against the M4 Pro baseline and the MLVC paper's M3 Pro, with the M1/M4 ratio per metric. In the repository `02_m1_timing/results/`. Write the numbers into `02_m1_timing/README.md` the same night.

What to look at: is the M1 still real time at 30 fps (late or dropped under 1 % in both directions)? Its p99 slack? Does the NE share the two networks better or worse (S against 1.11)? The M4 Pro is 24–34 % faster than the paper's M3 Pro; where does the M1 sit?

---

## 4. Day 3 · Decode Shams's bitstreams: does an M4 → M1 call drift?

In a real call Shams's M4 Pro encodes and your M1 decodes. Day 3 does exactly that offline, with the same tool as `baseline/04_correctness_experiment/scripts/c`.

**Get from Shams** (AirDrop or a USB stick, about 650 MB) into `~/Downloads/duplexnvc-m1/from_m4/`, renamed as shown:

| Her file (`~/Downloads/duplexnvc-baseline/runs/bl_bstar/T_duplex30_r1/`) | Your copy in `from_m4/` |
|---|---|
| `outgoing.mlvc` (the B\* bitstream her M4 Pro encoded, 1,802 frames) | `m4_outgoing.mlvc` |
| `outgoing.aus` (the same, with lengths) | `m4_outgoing.aus` |
| `dec_npu.nv12` (her NE decode of it, from `./c`; 623 MB) | `m4_dec_npu.nv12` |

```bash
cd ~/Downloads/dm1 && ./m1_decode     # ~15 min, any conditions
```

What runs: her stream decoded on the M1's NE (twice), GPU and CPU; **drift M4-NE vs M1-NE** (the cross-chip answer), M1 NE determinism, M1 NE vs GPU/CPU; your own Day 2 B\* stream decoded on the M1 the same way; and an access-unit-by-access-unit comparison of your encoder's bitstream with hers (same clips, same settings: are the two chips' encoders bit-exact?).

**Results pointed to:** `runs/m1_decode/M1_drift.csv` (same columns as `07_E5_drift.csv` plus a `pair` column: `M4NE_vs_M1NE`, `M4NE_vs_M1GPU`, `M1stream_M1NE_vs_M1GPU`, …), `runs/m1_decode/M1_encoder_vs_M4.txt`; repository `03_m1_decode_drift/results/`.

**Send to Shams** for the reverse direction (M1 → M4): `~/Downloads/duplexnvc-m1/to_m4/m1_outgoing.mlvc`, `m1_outgoing.aus`, `m1_dec_npu.nv12` (she decodes them with her `./c` logic and compares with `m1_dec_npu.nv12`).

M4 Pro reference, same chip: NE vs GPU 52.13 dB mean / 38.46 dB worst frame; NE vs CPU 48.78 / 39.51. If M4-NE vs M1-NE is bit-identical, a cross-chip call needs no drift bound; if it drifts, the controller's table (A2) gets a cross-chip row.

---

## 5. Day 4 · Contention (evening, quiet): the M1 contention curve

The baseline found that the NE runs the two networks almost one after the other (S = 1.11 of a possible 1.99). The contention test asks why: is the NE itself the limit, or the unified memory's bandwidth? `memstress` (in `common/memstress.c`) loads the memory at 0 / 25 / 50 / 75 % duty on the performance cores while the encoder alone runs on the NE (unpaced) and while the B\* call runs paced at 30 fps. Shams runs the same script on the M4 Pro.

```bash
cd ~/Downloads/dm1
./m1_quiet
./m1_contention            # ~55 min; resumable (Ctrl-C, run again, it continues)
./m1_unquiet
```

**Results pointed to:** `runs/m1_contention/M1_contention_curve.csv` (per load: memstress GB/s actually pulled, encoder-alone call and network time, B\* send and receive p99 and late share) and `M1_memstress_peak.txt`; repository `04_m1_contention/results/`. The script's last line says whether the NE slowed by more than 5 % at 75 % load.

---

## 6. Day 5 · Energy (night, quiet): M1 energy per frame pair

The same protocol as `baseline/06_energy_experiment/scripts/w`: 120 s idle, then 5 paced B\* calls of 60 s with `powermetrics` every 100 ms, idle subtracted, divided by the frame pairs.

```bash
cd ~/Downloads/dm1
./m1_quiet
./m1_energy                # ~15 min; password at the start; do not press Ctrl-C
./m1_unquiet
./m1_timing_sum            # refreshes M1_vs_M4Pro.csv with the energy rows
```

**Results pointed to:** `runs/m1_energy/M1_energy_summary.csv` (`processor, run_mW, idle_mW, mJ_per_pair_median, mJ_min, mJ_max, J_per_minute`, as `06_E7_energy_AC.csv`) and `M1_energy_per_run.csv`; repository `05_m1_energy/results/`. M4 Pro reference: 65.3 mJ per frame pair, 97 % on the NE, GPU idle. This is the step dropped second if the plan slips.

---

## 7. Days 9, 11, 15 · E2: a real call between two laptops

Everything before this simulates the other side on one laptop. E2 runs the real thing: two laptops on the same Wi-Fi, each encoding its own clip and decoding the other's, bitstreams over UDP. `duplex_call.cpp` (in `06_m1_e2_call/scripts/`) is `duplex_bench.cpp` with the network added: same codec calls, same pacing and dropped-frame rule, same `frames.csv`, plus packet fragmentation, loss counting, and an in-band round-trip and clock-offset measurement so one-way delays can be corrected. It was written without a Mac, so **Day 9 starts with a build and a loopback test**.

```bash
cd ~/Downloads/dm1
./m1_call_build            # builds the call program next to the measurement program
./m1_call loopback         # two endpoints on this Mac over 127.0.0.1, 20 s: must show lost 0, decode failures 0
```

Then the call test with Shams, Wi-Fi on (not quiet mode; energy is not compared here). Both laptops on the same Wi-Fi, clocks on *Set time automatically*, charger in. Each side finds its address with `ipconfig getifaddr en0`. **Type the same command on both laptops within the same minute**; both start at the second-next full minute:

```bash
./m1_call shams_m4_r1 <Shams's IP> 60          # on the M1; Shams runs her copy with the M1's IP
```

By default the M1 sends the B\* *incoming* clips (6c9c96 + 9c02f6) so Shams's laptop receives exactly what it received in B\*, and her laptop sends the *camera* clips (0380a3 + 6587ae). Three calls of 60 s with B\* on Day 11 (`shams_m4_r1`, `_r2`, `_r3`), the same with Warda's M4 on Day 15 (`warda_m4_r1`, …), and with the controller or the Tier B winner once Shams has them (she passes the setting on her side; label them `shams_ctrl_r1`, `shams_tierb_r1`).

**Results pointed to:** `runs/m1_call/M1_call_<label>/` with `frames.csv` (E rows = sent frames, D rows = received and decoded frames), `clock.csv` (round trip and clock offset over time), `received.mlvc` (what arrived, for an offline decode and drift check with the Day 3 method), `outgoing.mlvc`, `run.txt` and `summary.json` (frames sent, received, lost, incomplete, decode failures, round trip, end-to-end delay percentiles from the peer's send to decoded here, late frames, bitrate). Repository `06_m1_e2_call/results/M1_call_<label>_summary.json` and `raw_data/m1_call/`.

Shams needs the same program on her side: she copies `vm1` as `vm4` with `TAG=M4` and `WORK=~/Downloads/duplexnvc-baseline`, builds with `m1_call_build` (edit its first line to source `vm4`), and runs `m1_call` the same way.

---

## 8. After every step: write up, collect, commit

Each step is written up the day it finishes. Put the numbers and the reading into that step's `README.md` (every one has a *Results* section to fill), then:

```bash
cd ~/Downloads/dm1 && ./m1_collect          # copies runs and tables into the repository (no video)
cd ~/Downloads/DuplexNVC
git add crosschip && git commit -m "M1 cross-chip: Day 2 timing" && git push
```

Commit on the branch you checked out in §1 (or your own `mohammed/m1-crosschip`); never into `baseline/`.

---

## 9. Files to exchange with Shams

| When | From Shams to you | From you to Shams |
|---|---|---|
| Day 1 | `bundles/mlvc/*.tar` (the converted full MLVC bundle, identical bytes) | `runs/m1_setup/M1_bundle_sha256.txt` to confirm |
| Day 3 | `runs/bl_bstar/T_duplex30_r1/{outgoing.mlvc, outgoing.aus, dec_npu.nv12}` | `to_m4/{m1_outgoing.mlvc, m1_outgoing.aus, m1_dec_npu.nv12}` |
| Day 4 | — | `memstress.c` and `m1_contention` run the same on her Mac with `TAG=M4` |
| Day 9 | her Wi-Fi address | your Wi-Fi address; `duplex_call.cpp`, `m1_call_build`, `m1_call`, `call_sum.py` |

---

## 10. If something goes wrong

| Problem | What to do |
|---|---|
| `m1_setup` says MISSING for the bench or `mlvc` | §2 Step 2 or 4 did not finish; rerun that step, then `./m1_setup` again |
| `cmake --preset` fails with "vcpkg install failed", then "unable to find ... Ninja" | Look at the end of `build/mac-arm64-ninja-release/vcpkg-manifest-install.log`; on 20 Nov it was "Could not find pkg-config": `brew install pkg-config`, `rm -rf build/mac-arm64-ninja-release`, configure again |
| `uv sync --extra onnxruntime` says the extra is not defined | Microsoft's `mlvc` repo made onnxruntime a normal dependency; run `uv sync` without the extra |
| `brew: command not found` | Homebrew not installed or not on the PATH; see §2 Step 1 |
| `zsh: unknown sort specifier` or `command not found: home@MacBookAir` | The prompt text was pasted along with the command; paste only the command lines |
| `fixed-version check` is not 13 | `$TOOLS/duplex_bench.cpp` is not the repository's; copy `baseline/common/code/duplex_bench.cpp` to `$TOOLS` and rerun |
| `resolved=cpu` where `npu` was requested | Core ML did not take the NE: check macOS version and that the bundle is the Core ML one; report it, it is a finding |
| Late frames in the M1 B\* smoke test | Not an error: a slower chip; Day 2 measures it. If late > 1 % at 30 fps, also note the paced turns result |
| Thermal state `serious`/`critical` in `thermal.csv` | A fanless M1 throttled; note the time, let it cool 10 min, rerun the affected rounds (the summary uses medians) |
| `powermetrics` gives no `ANE Power` line | Run `sudo powermetrics --samplers gpu_power -n 1`; if the line is missing on this macOS, energy is CPU + GPU only; say so |
| `m1_call_build` fails to compile | The program was written without a Mac. Fix the line the compiler names (the codec calls are copied from `duplex_bench.cpp`, so errors will be in the socket or record code) and rerun |
| `m1_call` loopback loses frames | Raise `--mtu` no higher than 1400; check nothing else uses ports 5600/5601 |
| macOS asks to allow incoming connections | Allow; or System Settings → Network → Firewall → add the program |
| `m1_contention` interrupted | Run it again; finished runs are skipped |

---

## Time budget on the M1

| Day | Step | Laptop time | Conditions |
|---|---|---|---|
| 1 | one-time setup (Homebrew, packages, libmlvc, conversion) + `m1_setup` | about 1 h on 20 Nov, `m1_setup` 3 min | Wi-Fi on |
| 2 | `m1_timing` | 92 min (46 runs of 60 s + 60 s rest) | quiet |
| 3 | `m1_decode` | 15 min | any |
| 4 | `m1_contention` | 55 min | quiet, evening |
| 5 | `m1_energy` | 15 min | quiet, night, password |
| 9 | `m1_call_build`, loopback, first call | 30 min | Wi-Fi on |
| 11, 15 | real calls, 3 × 60 s each pairing | 20 min each | Wi-Fi on |

---

## 11. Where the code for each step is

Paths are inside the repository (`crosschip/m1_mohammed/`). On the Mac every one of these files is copied into `~/Downloads/dm1/` by the install command in §1, and that is where you run them.

| Day | Step | Script you run | Repository path | Built from (baseline) | Helpers it uses |
|---|---|---|---|---|---|
| all | Settings (paths, `TAG=M1`, B\* setting) | — | `common/vm1` | `baseline/common/scripts/v` | — |
| 1 | Setup, build, streams, smoke tests | `./m1_setup` | `01_m1_setup/scripts/m1_setup` | `common/scripts/b`, `m`; `01_smoke_test_experiment/scripts/t` | `baseline/common/code/duplex_bench.cpp` (the measurement program), `analyze_run.py`, `quality_tools.py` |
| 1 | Placement trace on the M1 | `./m1_trace` | `01_m1_setup/scripts/m1_trace` | `07_processor_experiment/scripts/1t` | `baseline/common/code/mlplan.swift` |
| 2, 4, 5 | Quiet mode by hand (Wi-Fi, Bluetooth, Low Power Mode, brightness, apps) | `./m1_prep on`, `./m1_prep off` | `01_m1_setup/scripts/m1_prep` | new | `blueutil`, `brightness` (Homebrew) |
| 2, 4, 5 | Quiet mode on / off | `./m1_quiet`, `./m1_unquiet` | `01_m1_setup/scripts/m1_quiet`, `m1_unquiet` | `common/scripts/p`, `u` | — |
| 2 | Timing (B\* protocol + MLVC-S) | `./m1_timing` | `02_m1_timing/scripts/m1_timing` | `03_timing_experiment/scripts/x` | `baseline/common/code/thermal_log.swift` |
| 2 | Timing tables and chip comparison | `./m1_timing_sum` | `02_m1_timing/scripts/m1_timing_sum` | `03_timing_experiment/scripts/y`, `common/scripts/sum.py` | `common/sum_m1.py`, `common/compare_chips.py` |
| 3 | Cross-chip decode and drift | `./m1_decode` | `03_m1_decode_drift/scripts/m1_decode` | `04_correctness_experiment/scripts/c` | `common/drift_csv.py`, `common/au_cmp.py` (new) |
| 4 | Contention test | `./m1_contention` | `04_m1_contention/scripts/m1_contention` | new (protocol of `09_placement_experiment/scripts/all`) | `common/memstress.c` (new, compiled by `m1_setup` into `$TOOLS/memstress`) |
| 4 | Contention curve | `./m1_contention_sum` | `04_m1_contention/scripts/m1_contention_sum` | new | `common/contention_sum.py` (new) |
| 5 | Energy | `./m1_energy` | `05_m1_energy/scripts/m1_energy` | `06_energy_experiment/scripts/w` | `analyze_run.py power` |
| 9 | Build the call program | `./m1_call_build` | `06_m1_e2_call/scripts/m1_call_build` | the harness build of `baseline/REPRODUCE.md` §2 Step 4 | `06_m1_e2_call/scripts/duplex_call.cpp` (new: `duplex_bench.cpp` + UDP) |
| 9, 11, 15 | Loopback test and real calls | `./m1_call loopback`, `./m1_call <label> <ip>` | `06_m1_e2_call/scripts/m1_call` | new | `06_m1_e2_call/scripts/call_sum.py` (new) |
| before each | Read-only status check (git, power, radios, quiet mode, apps, thermal, memory) | `./m1_status` | `common/m1_status` | new | — |
| after each | Copy results into the repository | `./m1_collect` | `common/m1_collect` | new | `rsync` |

Each step folder also has a `README.md` with the question, the files it produces and a *Results* table to fill in the day the step finishes.
