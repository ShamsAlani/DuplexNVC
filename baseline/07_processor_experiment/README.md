# 07 — Processor experiment: where the networks run, and each network alone on NE, GPU and CPU (X1)

**Questions.**
- Does Core ML really run the networks on the processor we ask for, or do some operations silently fall back to the CPU?
- How fast is each network alone on the GPU and on the CPU, compared with the NE, unpaced and in a paced call? How much power does each draw?

**What was run.**
- **Placement trace:** the Swift tool `mlplan.swift` loads each compiled model's Core ML `MLComputePlan` for `cpuAndNeuralEngine`, `cpuAndGPU` and `cpuOnly`, and counts on which device each operation runs and what share of the estimated cost it carries.
- **72 runs:** each network alone, unpaced, on NE, GPU and CPU (full MLVC 360p in 5 interleaved rounds; MLVC-S 540p in 3 rounds; CPU runs 20 s, others 60 s; 60 s rest); and paced at 30 fps on the NE and the GPU, 3 × 60 s per network, with `powermetrics` on every paced run.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/1t` | Placement trace of full MLVC 360p and MLVC-S 540p (compiles `common/code/mlplan.swift`) | 2 min | any |
| `scripts/1` | The 72 runs | 2 h 20 min | Quiet mode (see [`../README.md`](../README.md#quiet-mode)), `./p` run first; asks for the password once (`powermetrics` needs `sudo`) |
| `scripts/1r` | Summary (`step1_sum.py`) | 1 min | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/logs/out_1.txt` | Console log of the 72 runs, each with the processor Core ML actually used (`requested=… resolved=…`), and the trace |
| `raw_data/logs/out_1r.txt` | Summary: median time per network and processor, paced vs unpaced, power |
| `scripts/step1_sum.py` | The summary code |

The per-run records are on the measurement laptop under `phase2/step1/` (see [`../09_placement_experiment/raw_data/README.md`](../09_placement_experiment/raw_data/README.md) for how they are packed).

## Results

**Placement trace.** With the NE requested, full MLVC runs 313 of 316 operations on the NE, carrying **100.0 %** of the estimated cost; MLVC-S runs 214 of 217 (99.9 %). The remaining operations are tiny input/output conversions on the CPU. With the GPU or the CPU requested, every operation runs on that processor. Every run of X1 and X3 also reported `resolved` equal to `requested`.

**Each network alone, median call time in ms (encoder / decoder).** MLVC-S uses the shipped perceptual bundle, as in Phase 1.

| Model | NE unpaced | GPU unpaced | CPU unpaced | NE paced 30 fps | GPU paced 30 fps |
|---|---|---|---|---|---|
| Full MLVC 360p | 5.85 / 5.94 | 13.34 / 13.16 | 20.00 / 20.68 | 12.36 / 12.53 | 15.11 / 14.90 |
| MLVC-S 540p | 4.84 / 4.91 | 10.36 / 10.65 | 19.73 / 20.95 | 10.61 / 10.66 | 12.48 / 12.63 |

**Power (paced, rough).** A network on the GPU drew roughly 3.2–4.6 W on the GPU; the same network on the NE roughly 0.5 W on the NE.

## Conclusion

1. **Nothing falls back to the CPU:** the NE times of the baseline are real NE times.
2. **The GPU is 2.2–2.3× slower than the NE unpaced, but only 1.2× slower in a paced call**, and draws several times the power. **The CPU is 3.4–4.3× slower** but still under the 33.3 ms frame time at these sizes, so both are real candidates for one of the two networks.
3. A single paced network on the NE takes 12.4 ms, the same as the B\* encoder in full duplex (12.44 ms): **the doubled call time in B\* comes from pacing, not from the two networks competing.**
