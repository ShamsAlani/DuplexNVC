# common/code/

The measurement program and the analysis tools shared by every experiment. During setup, copy them into `~/Downloads/duplexnvc-baseline/tools` (`$TOOLS`); see [`../../REPRODUCE.md`](../../REPRODUCE.md).

| File | Language | Purpose |
|---|---|---|
| `duplex_bench.cpp` | C++17 | The measurement program (one call endpoint) |
| `analyze_run.py` | Python 3 | Timing, latency, speedup, κ and energy from a run folder |
| `quality_tools.py` | Python 3 (NumPy) | PSNR, PSNR-YUV, drift between two decodes, BD-rate |
| `face_metrics.py` | Python 3 (NumPy, OpenCV, lpips, torch) | Display-scale and face PSNR / LPIPS |
| `facebox.swift` | Swift (Apple Vision) | Face boxes on the original 1080p frames |
| `mlplan.swift` | Swift (Core ML) | Placement trace: loads a model's `MLComputePlan` for `cpuAndNeuralEngine`, `cpuAndGPU` and `cpuOnly` and prints, per device, the number of operations and their share of the estimated cost (X1, X2) |
| `thermal_log.swift` | Swift | Logs `ProcessInfo.thermalState` and Low Power Mode once per second (X3) |

## duplex_bench.cpp

It links statically to `libmlvc` and is built as libmlvc's `examples/minimal-fetchcontent` project with this file as `main.cpp`:

```bash
cp -R $WORK/libmlvc/examples/minimal-fetchcontent $WORK/harness
cp duplex_bench.cpp $WORK/harness/main.cpp
cd $WORK/harness
cmake -S . -B build/ninja-release -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_OSX_ARCHITECTURES=arm64 -DBUILD_SHARED_LIBS=OFF \
      -DFETCHCONTENT_SOURCE_DIR_LIBMLVC=$WORK/libmlvc
cmake --build build/ninja-release      # binary: build/ninja-release/libmlvc_example
grep -c "Clock::now()" main.cpp        # must print 13 (fixed version)
```

**Usage:** `libmlvc_example <mode> [options]`

| Mode | What it does | Gives |
|---|---|---|
| `prepare` | Encodes `--input` once, untimed, and writes `incoming.aus` + `incoming.mlvc` (the "remote participant") | Incoming stream |
| `alone-enc` | Encoder only | t_enc |
| `alone-dec` | Decoder only (decodes `--incoming`) | t_dec |
| `turns` | One thread: encode frame k, then decode frame k | T_turns |
| `duplex` | Encoder thread and decoder thread at the same time | T_shared, and B\* when paced |

| Option | Default | Meaning |
|---|---|---|
| `--input` | — | Raw NV12 camera clip (loaded fully into memory) |
| `--size` | 640x360 | Frame size |
| `--incoming` | — | `.aus` file written by `prepare` |
| `--bundles` | — | Model bundle folder (one model per folder) |
| `--enc-cu`, `--dec-cu` | npu | Processor for each network: `npu`, `gpu`, `cpu` |
| `--qp` | 26 | Quality index |
| `--iframe-period` | 64 | Frames between I-frames |
| `--fps` | 30 | Pacing; **0 = unpaced** (as fast as possible) |
| `--deadline-ms` | 1000/fps | Late-frame threshold |
| `--seconds` | 60 | Run length |
| `--warmup-frames` | 64 | Frames flagged as warm-up (excluded from statistics) |
| `--out-dir` | run | Output folder |

**How it measures:**
- The camera clip is read into memory before timing, so there is no disk I/O inside a timed call.
- One `MlvcManager` is created per processor in use (model cache on, sessions preloaded at initialisation).
- **Warm-up:** one encode and one decode run before the clock starts, because the first call loads the model and takes 7–16 ms. The warm-up I-frame is kept as slot −1 so the outgoing stream stays decodable.
- **Common start:** all modes start at t0 = now + 200 ms (`sleep_until`).
- **Paced:** frame k is due at t0 + k/fps. The thread sleeps until then.
  - The encoder skips frames it is more than one period behind on and counts them as **dropped**, as a real camera would.
  - The decoder never skips, because each frame depends on the previous one.
- **Unpaced:** each frame is scheduled at the moment it starts.
- **Clock:** `std::chrono::steady_clock`, which is monotonic.

**Outputs in `--out-dir`:**
- `frames.csv`, one row per frame:
  - `dir`: E = encode, D = decode;
  - `slot`, `src`;
  - `sched_ms`, `start_ms`, `end_ms`, relative to t0;
  - `service_ms` = end − start;
  - `latency_ms` = end − due;
  - `late`: 1 if latency > deadline;
  - `infer_ms`: network time, from libmlvc;
  - `call_ms`: whole call, from libmlvc;
  - `frame_type`: 0 = I, 1 = P;
  - `bytes`, `ok`, `warmup`.
- `run.txt`: every setting, `t0_epoch_ms` (to align power logs), `encoder_dropped`, `decoder_failures`.
- `outgoing.aus` / `outgoing.mlvc`: the encoded stream, written after the run.

## analyze_run.py

```bash
python3 analyze_run.py timing RUN_DIR [RUN_DIR ...]          # per-direction summary
python3 analyze_run.py compare --alone-enc A --alone-dec B --turns T --duplex D   # S, ceiling, kappa
python3 analyze_run.py power RUN_DIR --pm RUN_DIR/power.txt --idle-pm idle/power.txt [--json out.json]
```

- **Statistics:** warm-up frames are excluded. Percentiles use linear interpolation.
- **Late or dropped %** = (late + dropped) / scheduled.
- **Energy per frame pair** = (P_run − P_idle) × steady window / frame pairs. Power is the time-weighted mean of the `powermetrics` samples inside the steady window (1 s inside each end).

## quality_tools.py

```bash
python3 quality_tools.py psnr decoded.nv12 original.nv12 640x360
python3 quality_tools.py drift dec_npu.nv12 dec_gpu.nv12 64        # grouped by position after the I-frame
python3 quality_tools.py bdrate --ref R1:P1,R2:P2,... --test R1:P1,...
```

- PSNR-YUV = (6·Y + U + V) / 8.
- BD-rate uses the Bjøntegaard method: piecewise-cubic fit of log-rate against PSNR.

## face_metrics.py and facebox.swift

```bash
swiftc -O facebox.swift -o facebox
./facebox <png_dir> faces.json
python3 face_metrics.py --run RUN --decoded dec.nv12 --coded cod.nv12 --display disp.nv12 --faces faces.json
```

- **Coded scale:** decoded vs encoder input, at 360p.
- **Display scale:** decoded frame upscaled to 1920×1080 with Lanczos (OpenCV), compared with the original 1080p frame.
- **Face metrics:** face PSNR-Y and LPIPS (AlexNet) are computed inside the Apple Vision face boxes.
