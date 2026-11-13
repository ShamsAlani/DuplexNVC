# 01 — Smoke test experiment (S1, S2)

**Question.** Does the whole pipeline work before any data is collected: no call fails, Core ML places both networks on the Neural Engine (NE), every run ends on its own, and paced runs keep 30 fps?

**What was run.** Every mode of the measurement program (`alone-enc`, `alone-dec`, `turns`, `duplex`, unpaced and paced) once for 10 s:
- **S1:** MLVC-S at 540p, QP 22 (the Phase 1 configuration);
- **S2:** full MLVC at 360p, QP 26 (the baseline B\* configuration).

These runs only check the pipeline; they are not used as results.

## How to run

| Script | Test | Time | Conditions |
|---|---|---|---|
| `scripts/s` | S1 | 3 min | any |
| `scripts/t` | S2 (needs the 360p streams from `common/scripts/m`) | 3 min | any |

Run from `~/Downloads/d` as `./s` and `./t` (see [`../common/scripts/README.md`](../common/scripts/README.md) for installing).

## Files

| Path | Contents |
|---|---|
| `raw_data/smoke/`, `raw_data/bl_smoke/` | One folder per run with `frames.csv` and `run.txt`, plus its `.log` |
| `raw_data/logs/out_s.txt`, `out_t.txt` | Console output |
| `results/01_smoke_test_experiment.csv` | `test, metric, value` for both tests |

## Results

These are single 10 s runs per mode and only check that the pipeline works.

| | S1: MLVC-S 540p | S2: full MLVC 360p |
|---|---|---|
| Encoder / decoder alone (ms) | 4.86 / 4.92 | 5.90 / 5.96 |
| T_turns / T_shared (ms) | 9.82 / 8.53 | 11.86 / 10.68 |
| S | 1.15 | 1.11 |
| Late or dropped, paced duplex (send / receive) | not run | 0.37 % / 0 % |
| Late or dropped, paced turns | 0 % / 0 % | 0 % / 0 % |

**Reading.**
- Both pipelines work, every network runs on the NE, and no call fails.
- In the short S2 run, 1 frame out of about 300 was late. That did not happen in any of the five 60 s B\* runs, so it is a start-up effect.

## Conclusion

The pipeline works for both models and every run used the NE. The first encode and decode took 7–16 ms, two to three times a normal frame, which confirmed that the program must warm up before its clock starts. Bring-up also exposed a bug (unpaced runs never ended), fixed in the program used for every later experiment.
