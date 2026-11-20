# 01 — M1 setup: does MLVC run on the M1? (Day 1)

**Question.** Does the full pipeline (libmlvc, the Core ML bundles, the measurement program, the B\* streams) run on the M1, on its Neural Engine, with the same files as the M4 Pro baseline?

**What is run.** `m1_setup`: copies the analysis tools, builds `duplex_bench` in `$WORK/harness`, records the machine (chip, cores, memory, macOS, libmlvc commit) and the SHA-256 of the bundles (must equal Shams's), makes the B\* camera and incoming streams from the same four VCD clips, prepares the incoming stream at QP 26 on the NE and checks it decodes, then runs the B\* smoke tests (four unpaced modes, paced duplex) and an MLVC-S 540p paced smoke run, 10 s each. `m1_trace`: the Core ML `MLComputePlan` of each bundle on this Mac (which operations run on the NE).

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_setup` | Build, machine record, bundle checksums, streams, smoke tests | 10 min | any; after the one-time setup (main README §2) |
| one-time setup | Homebrew, packages (incl. `pkg-config`), Python 3.12 environment, libmlvc `eb5d60a` built, full MLVC converted with `mlvc-tools` (main README §2) | about 1 h | Wi-Fi on |
| `scripts/m1_trace` | Placement trace of full MLVC and MLVC-S on the M1 | 5 min | any |
| `scripts/m1_prep on` / `off` | The by-hand part of quiet mode, automated where macOS allows: Low Power Mode off, Wi-Fi and Bluetooth off, brightness to maximum, every app quit; `off` turns Wi-Fi and Bluetooth back on | 1 min | password; the first run installs `blueutil` and `brightness` with Homebrew |
| `scripts/m1_quiet`, `scripts/m1_unquiet` | Quiet mode on / off (Spotlight, Time Machine, keep-awake, checks), used by Days 2, 4, 5 | 1 min | password |

## Files

| Path | Contents |
|---|---|
| `results/M1_machine.txt` | Chip, cores, memory, macOS build, libmlvc commit, power state |
| `results/M1_bundle_sha256.txt` | Checksums of the bundles used on the M1 (compare with Shams's) |
| `results/trace/M1_trace.txt` | Operations per device from `mlplan` |
| `raw_data/m1_smoke/` | The smoke runs `M1_smoke_<mode>`, `M1_smoke_duplex30`, `M1S_smoke_duplex30` |
| `raw_data/logs/out_m1_setup.txt`, `out_m1_trace.txt` | Console output |
| `raw_data/logs/out_m1_convert.txt` | Console output of the full MLVC conversion on the M1 (copied by `m1_collect`) |

## Results

**Day 1, Fri 20 Nov 2026 (the plan's Day 1 was Wed 18 Nov; setup done two days late).** Machine: MacBook Air (MacBookAir10,1, fanless), Apple M1, 8 cores (4 performance, 4 efficiency), **8 GB** memory, macOS 27.2.1 (build 26B131); Shams's reference Mac is an M4 Pro with 24 GB on macOS 26.6, so the macOS version is a second difference besides the chip. libmlvc commit `eb5d60a`, built from source; `mlvc-tools` cloned on 20 Nov (commit `785fb06`, newer than Shams's 10 Nov clone: the `onnxruntime` extra no longer exists, otherwise the same conversion command). The full MLVC bundle was converted on the M1 itself from `mlvc-psnr-v1.ckpt`: 37,048,320 bytes, the same size as Shams's; SHA-256 in `results/M1_bundle_sha256.txt`, to be compared with hers. MLVC-S bundle from libmlvc (13 MB).

- `fixed-version check (must be 13): 13`; the incoming stream (600 frames, QP 26, NE) decodes at PSNR-Y 34.98 dB, as on the M4 Pro.
- Every manager line `requested=npu resolved=npu`; no `FAILED`; every run ended. Encoder first frame (model load) and decoder first frame about 16 ms.
- Smoke runs (10 s each, not quiet mode, not data), full MLVC 360p QP 26 on the NE, against the M4 Pro baseline:

| Metric | M1 (smoke) | M4 Pro (baseline) | M1 / M4 Pro |
|---|---|---|---|
| Encoder alone, call ms (unpaced) | 9.55 | 5.86 | 1.63 |
| Decoder alone, call ms (unpaced) | 9.78 | 5.94 | 1.65 |
| T_turns, ms per frame pair | 19.49 | 11.81 | 1.65 |
| T_shared, ms per frame pair (both on the NE) | 17.25 | 10.68 | 1.62 |
| S = T_turns / T_shared | 1.13 | 1.11 | — |
| kappa encoder / decoder (call) | 1.81 / 1.76 | 1.82 / 1.80 | — |
| B\* paced 30 fps: late or dropped, send / receive | 0 % / 0 % | 0 % / 0 % | — |
| B\* paced 30 fps: mean call ms, send / receive | 18.12 / 19.69 | 12.44 / 13.32 | 1.46 / 1.48 |
| B\* paced 30 fps: due-to-done p99 ms, send / receive | 31.16 / 28.18 | 29.27 / 28.93 | slack 2.2 ms vs 4.1 ms |
| MLVC-S 540p QP 22 paced 30 fps: late or dropped | 0.37 % / 0.37 % | 0 % / 0 % | borderline on the M1 |

**Reading.** The M1 is about 1.6× slower than the M4 Pro for each network alone and for the pair, and its NE shares the two networks just as poorly (S 1.13 against 1.11 of a possible 1.98): the baseline's finding that the NE runs the two networks almost one after the other holds across the generation. B\* still meets 30 fps on the M1 with no late frame, but the slowest 1 % of frames keep only about 2 ms of slack instead of 4. MLVC-S 540p, the most efficient setting on the M4 Pro, already shows 0.37 % late frames on the M1 in a 10 s smoke run; the Day 2 run (quiet, 60 s, repeated) decides whether it stays feasible there.

## Conclusion

*(one or two sentences: MLVC runs / does not run on the M1 as on the M4 Pro, and what differs)*
