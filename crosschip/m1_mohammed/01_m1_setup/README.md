# 01 — M1 setup: does MLVC run on the M1? (Day 1)

**Question.** Does the full pipeline (libmlvc, the Core ML bundles, the measurement program, the B\* streams) run on the M1, on its Neural Engine, with the same files as the M4 Pro baseline?

**What is run.** `m1_setup`: copies the analysis tools, builds `duplex_bench` in `$WORK/harness`, records the machine (chip, cores, memory, macOS, libmlvc commit) and the SHA-256 of the bundles (must equal Shams's), makes the B\* camera and incoming streams from the same four VCD clips, prepares the incoming stream at QP 26 on the NE and checks it decodes, then runs the B\* smoke tests (four unpaced modes, paced duplex) and an MLVC-S 540p paced smoke run, 10 s each. `m1_trace`: the Core ML `MLComputePlan` of each bundle on this Mac (which operations run on the NE).

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_setup` | Build, machine record, bundle checksums, streams, smoke tests | 10 min | any; after the one-time setup (main README §2) |
| `scripts/m1_trace` | Placement trace of full MLVC and MLVC-S on the M1 | 5 min | any |
| `scripts/m1_quiet`, `scripts/m1_unquiet` | Quiet mode on / off, used by Days 2, 4, 5 | 1 min | password |

## Files

| Path | Contents |
|---|---|
| `results/M1_machine.txt` | Chip, cores, memory, macOS build, libmlvc commit, power state |
| `results/M1_bundle_sha256.txt` | Checksums of the bundles used on the M1 (compare with Shams's) |
| `results/trace/M1_trace.txt` | Operations per device from `mlplan` |
| `raw_data/m1_smoke/` | The smoke runs `M1_smoke_<mode>`, `M1_smoke_duplex30`, `M1S_smoke_duplex30` |
| `raw_data/logs/out_m1_setup.txt`, `out_m1_trace.txt` | Console output |

## Results

*(fill in on Day 1)* Machine: … · Bundle checksums equal to Shams's: yes/no · Every manager `resolved=npu`: … · Smoke B\* paced 30 fps late %: … · Trace: … of … operations on the NE.

M4 Pro reference: full MLVC 313 of 316 operations on the NE (100.0 % of cost); smoke duplex 30 fps 0 % late.

## Conclusion

*(one or two sentences: MLVC runs / does not run on the M1 as on the M4 Pro, and what differs)*
