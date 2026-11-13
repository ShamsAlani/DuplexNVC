# common/scripts/

Shared settings and helper scripts. The scripts of each experiment are in that experiment's own `scripts/` folder; on the Mac **all scripts run from one folder, `~/Downloads/d`**. To install every script of every experiment:

```bash
mkdir -p ~/Downloads/d
find <repo>/baseline -path '*/scripts/*' -type f ! -name README.md -exec cp {} ~/Downloads/d/ \;
cp <repo>/baseline/common/code/{mlplan.swift,thermal_log.swift} ~/Downloads/d/
chmod +x ~/Downloads/d/*
```

Every script saves its console output as `out_<name>.txt` next to it in `~/Downloads/d`.

## Settings: `v`

Every script reads `v`. Edit it if your folders differ:

| Variable | Value | Meaning |
|---|---|---|
| `WORK` | `~/Downloads/duplexnvc-baseline` | Work folder |
| `TOOLS` | `$WORK/tools` | Copied from `../code` |
| `BENCH` | `$WORK/harness/build/ninja-release/libmlvc_example` | Measurement program |
| `MLVC` | `$WORK/libmlvc/install/mac-arm64-ninja-release/bin/mlvc` | libmlvc CLI |
| `PY` | `$WORK/.venv/bin/python3` | Python with NumPy, OpenCV, lpips, torch |
| `P1` | MLVC-S, 960×540, QP 22 | Phase 1 check settings |
| `BL` | full MLVC, 640×360, QP 26, I-period 64, bundle `$WORK/bundles/mlvc` | Baseline B\* settings |
| `VCD360`, `VCD1080` | `~/mlvc/data/VCD/yuv`, `$WORK/data/vcd_1080p` | Dataset locations |

`s2cfg` adds the settings of experiments 07–09: the seven model/resolution settings (full MLVC 360p/540p/720p/1080p, MLVC-S 540p/720p/1080p), their checkpoints, model input and video sizes, the clip IDs of the camera (0380a3 + 6587ae) and incoming (6c9c96 + 9c02f6) streams, and the helpers `cfg`, `bund`, `camf`, `incf` that return the bundle, camera stream and incoming stream of a setting.

## Shared scripts

| Script | Purpose | Time | Conditions |
|---|---|---|---|
| `v` | Paths and settings read by every script (table above) | — | — |
| `s2cfg` | Settings of experiments 07–09 | — | — |
| `b` | Rebuilds the measurement program from `main.cpp` and checks it is the fixed version (13 × `Clock::now()`) | 1 min | any |
| `m` | Builds the 360p camera stream (clips 0380a3 + 6587ae) and incoming stream (6c9c96 + 9c02f6), 600 frames each; prepares the incoming stream at QP 26 and checks it decodes | 2 min | any |
| `p` | Puts the Mac in quiet mode: pauses Spotlight, tries to pause Time Machine (needs Full Disk Access), starts `caffeinate`, checks AC power and the tools | 1 min | password |
| `u` | Undoes `p` | 1 min | password |
| `h` | Prints the run order | — | — |
| `z` | Zips all raw results (no video) into `~/Downloads/DuplexNVC_raw_results.zip` | 1 min | any |
| `main.cpp` | Same as `../code/duplex_bench.cpp`, the source `b` builds | — | — |
| `sum.py` | Medians over rounds (E1, T_turns, T_shared, S, κ) and paced statistics; used by `t` and `y` | — | — |
| `installers/d5.sh`, `d6.sh`, `d7.sh` | Alternative installers that write the scripts of experiments 07, 08 and 09 into `~/Downloads/d` | — | — |

Setup logs (`out_b.txt`, `out_p.txt`, `out_m.txt`, the full setup and conversion terminal log, and the pinned `libmlvc` commit) are in [`../setup/`](../setup/).
