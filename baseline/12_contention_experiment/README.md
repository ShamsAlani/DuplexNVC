# 12 — Contention experiment: is the Neural Engine limited by memory bandwidth?

**Question.**
1. Why do the two networks barely run in parallel on the NE (sharing is only 1.11× faster than taking turns, experiment 03)? If loading the unified memory on purpose slows a network on the NE, memory bandwidth is the limit; if it does not, the NE itself is.
2. Why does a paced 30 fps call take about twice the unpaced time per frame (12.4 ms against 5.9 ms, experiments 03 and 07)? Experiment 03 proposed that the chip lowers its clocks in the idle gaps between paced frames but could not test it. If a background memory load shortens the paced calls, the clocks are the cause.

The test is the same as on the M1 laptop of the cross-chip study (`crosschip/m1_mohammed/04_m1_contention/`), with the same script, so the two chips compare directly.

## What was run

**21 Nov 2026, 21:46–22:40 (+04), quiet mode** (see [`../README.md`](../README.md#quiet-mode)), AC power, MacBook Pro 14-inch M4 Pro, 24 GB, macOS 26.6.2 (25G83).

- **Memory load** (`scripts/memstress.c`): 10 threads (one per performance core of the M4 Pro; the M1 used its 4), each copying between two 256 MB buffers. Within every 20 ms period a thread copies for 0 / 25 / 50 / 75 % of the time and sleeps for the rest. memstress reports the bandwidth it actually pulled (read + write), which is the x-axis of the curve. It starts 5 s before each run and stops 10 s after it.
- **Workloads**, B\* setting (full MLVC 360p, NE, QP 26, I-frame every 64, the camera and incoming streams of experiment 03):
  - (a) the encoder alone on the NE, unpaced, 60 s;
  - (b) the B\* call (encoder and decoder on the NE), paced at 30 fps, 60 s.
- **Protocol:** 3 interleaved rounds × 4 loads × 2 workloads = 24 runs, 60 s rest after each; a 10 s run of memstress alone at 100 % gives the peak bandwidth. First 64 frames per direction discarded; medians of the 3 runs, computed with the baseline's `analyze_run.py`. Thermal state logged once a second.

## How to run

These scripts live in `~/Downloads/d/ct/` (one level below the other scripts; they read `../settings.sh`).

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/contention_runs.sh` | Builds memstress, the peak run, the 24 runs, then `contention_summary.sh`. **Resumable** | 55 min | **quiet mode**, `../quiet_mode_on.sh` first, `../quiet_mode_off.sh` afterwards |
| `scripts/contention_summary.sh` | The contention curve (`contention_sum.py`) | 1 min | any |
| `scripts/memstress.c` | The memory load (built by `contention_runs.sh` into `$TOOLS/memstress`) | — | — |
| `scripts/contention_sum.py` | Medians per load from the run folders | — | — |

`THREADS=n` and `MB=n` override the number of memstress threads and the buffer size. Results go to `~/Downloads/duplexnvc-baseline/phase2/ct/`.

### Script names

The scripts were renamed from short names to descriptive ones after the runs; the code is unchanged apart from the names it calls and the log it writes. The console logs in `raw_data/` were recorded before the rename and keep the old names (`out_<old name>.txt`).

| Old name | New name | Console log written now |
|---|---|---|
| `scripts/all` | `scripts/contention_runs.sh` | `out_contention_runs.txt` |
| `scripts/sum` | `scripts/contention_summary.sh` | `out_contention_summary.txt` |

## Files

| Path | Contents |
|---|---|
| `raw_data/M4_load<L>_<alone-enc\|duplex30>_r<n>/` | Per run: `frames.csv`, `run.txt`, `memstress.txt` (GB/s during the run); `.log` and `.therm` next to each folder (the outgoing bitstreams stay on the measurement laptop) |
| `raw_data/thermal.csv` | Thermal state and Low Power Mode once a second |
| `raw_data/logs/out_all.txt` | Console log |
| `results/M4_memstress_peak.txt` | memstress alone at 100 % |
| `results/M4_contention_curve.csv` | Per load: GB/s, encoder alone (call, network and p99 ms), B\* send and receive (call ms, due-to-done p99, late share) |

## Results

**Every run completed:** 24 of 24, every one `requested=npu resolved=npu`; thermal state *nominal* for all 3,251 logged seconds. memstress alone at 100 %: **237 GB/s** (Apple's figure for the M4 Pro: 273 GB/s). At 50 % duty and above the bus is close to saturated (205–217 GB/s).

| Load | memstress GB/s | Encoder alone: call / network / p99 ms | B\* send: call ms / due-to-done p99 ms / late | B\* receive: call ms / p99 ms / late |
|---|---|---|---|---|
| 0 % | 0 | 5.86 / 5.57 / 6.00 | **12.64** / 29.18 / 0 % | **13.65** / 29.02 / 0 % |
| 25 % | 136 | 6.00 / 5.69 / 6.15 | 8.25 / 23.61 / 0 % | 9.45 / 24.49 / 0 % |
| 50 % | 205 | 6.05 / 5.74 / 6.16 | 7.62 / 20.66 / 0 % | 9.23 / 20.94 / 0 % |
| 75 % | 217 | 6.12 / 5.79 / 6.34 | **7.37** / 21.11 / 0 % | **8.65** / 21.05 / 0 % |

Cross-checks: the encoder alone at 0 % (5.86 ms) matches experiment 07 (5.85 ms); the B\* send call at 0 % (12.64 ms) is within 2 % of experiment 03 (12.44 ms).

**Same test on the M1** (cross-chip study, 20 Nov, 4 threads, peak 58 GB/s): encoder alone 9.49 → 11.27 ms at 0 → 75 % (+18.8 %); B\* send call 17.55 → 11.34 ms at 25 % load, late frames 3.97 % → 0 %.

## Conclusion

1. **Memory bandwidth does not limit the NE on the M4 Pro.** With 217 GB/s of competing traffic (80 % of the chip's peak), the encoder alone slows by only **4.4 %** (network time 5.57 → 5.79 ms). On the M1 the same test slows it by 18.8 %: the older chip's smaller memory system matters more, but on both chips memory is at most a secondary limit. The near-serial sharing of the NE (S = 1.11) therefore comes from the NE running the two networks largely one after the other, not from memory. A faster NE, not more bandwidth, is what would let two networks overlap.
2. **A background memory load removes most of the pacing penalty.** At 25 % load the paced B\* send call drops from 12.64 to 8.25 ms, and at 75 % to 7.37 ms (−42 %), close to the unpaced 5.86 ms; the slowest 1 % of frames drop from 29.2 to 21 ms. The receive side behaves the same. The M1 shows the same effect. This is direct evidence for the explanation experiment 03 proposed: in the idle gaps of a paced call the chip lowers its clocks, and keeping the memory system busy keeps them up.
3. **What this means for DuplexNVC.** Paced calls have about 40 % headroom that the chip's power management hides. Keeping the clocks up (a small keep-warm load, or encoding the next frame sooner) could make heavier settings meet 30 fps, but it costs power, which this test did not measure. Its energy cost needs the protocol of experiment 06 before it can be used.
