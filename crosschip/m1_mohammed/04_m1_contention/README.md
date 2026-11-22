# 04 — Contention test on the M1 (Day 4, evening, quiet)

**Question.** Why do the two networks barely overlap on the NE (S = 1.11 of 1.99 on the M4 Pro)? If loading the unified memory on purpose slows the NE, memory bandwidth is the limit; if not, the NE itself is. Does the M1, with its smaller memory system, behave differently?

**What is run.** `memstress` (`common/memstress.c`: 4 threads, each copying between two 256 MB buffers at a duty cycle of 0 / 25 / 50 / 75 %, reporting the GB/s it pulled) runs while (a) the encoder alone runs unpaced on the NE for 60 s and (b) the B\* call runs paced at 30 fps for 60 s; 3 interleaved rounds, 60 s rest; a 10 s run at 100 % gives the peak bandwidth. Thermal state logged.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_contention` | The 24 runs and the peak run; resumable; calls `m1_contention_sum` | 55 min | quiet mode (`./m1_quiet` first) |
| `scripts/m1_contention_sum` | The curve (`common/contention_sum.py`) | 1 min | any |

`THREADS=8 ./m1_contention` for a chip with more performance cores (Shams's M4 Pro: 10). The buffers are 128 MB per thread on a Mac with less than 16 GB (1 GB in all on the 8 GB M1 Air), 256 MB otherwise; `MB=64 ./m1_contention` overrides.

## Files

| Path | Contents |
|---|---|
| `raw_data/m1_contention/M1_load<L>_<alone-enc|duplex30>_r<n>/` | `frames.csv`, `run.txt`, `memstress.txt` (GB/s during the run), `.log`, `.therm` |
| `results/M1_memstress_peak.txt` | memstress alone at 100 % |
| `results/M1_contention_curve.csv` | Per load: GB/s, encoder-alone call and network ms and p99, B\* send and receive call ms, due-to-done p99 and late share |
| `raw_data/logs/out_m1_contention.txt` | Console output |

## Results

**Run:** Fri 20 Nov 2026, about 20:18–21:12 (+04), quiet mode, AC power, MacBook Air M1, 8 GB. memstress with 4 threads (the M1's performance cores) and 128 MB buffers; 3 interleaved rounds × 4 loads × 2 modes = 24 runs, all `requested=npu resolved=npu`. Thermal state `nominal` for all 3,253 logged seconds. memstress alone at 100 %: **58.3 GB/s** (the M1's LPDDR4X peak is about 68 GB/s).

| Load | memstress GB/s | Encoder alone: call / network / p99 ms | B\* send: mean call / due-to-done p99 ms, late % | B\* receive: mean call / p99 ms, late % |
|---|---|---|---|---|
| 0 % | 0.0 | 9.49 / 9.11 / 9.59 | 17.55 / 35.97, **3.97 %** | 19.52 / 33.24, 0.86 % |
| 25 % | 24.7 | 10.12 / 9.71 / 10.71 | **11.34** / 25.46, **0 %** | 18.72 / 26.85, 0 % |
| 50 % | 45.4 | 10.84 / 10.41 / 11.16 | 13.97 / 24.12, 0 % | 16.81 / 23.87, 0 % |
| 75 % | 46.1 | 11.27 / 10.79 / 11.81 | 15.14 / 26.44, 0 % | 14.90 / 25.88, 0 % |

**Reading.**
1. **Memory bandwidth slows the NE, but only moderately.** With 46 GB/s of competing traffic (about two thirds of the chip's peak) the encoder alone slows from 9.49 to 11.27 ms (**+18.8 %**), and the network (NE) time itself rises by the same share (9.11 → 10.79 ms, +18.4 %), so it is the NE inference that slows, not the CPU part of the call. Above 50 % duty memstress cannot pull more (45 → 46 GB/s): the bus is saturated.
2. **Memory contention does not explain the poor NE sharing.** When the two networks share the NE (Day 2), each slows by 1.77–1.82× (kappa). Here, far more competing memory traffic than a second MLVC network can generate slows a network by only 1.19×. So the near-serial sharing (S = 1.11) comes mainly from the NE executing the two networks largely one after the other, not from memory bandwidth. Memory is a secondary limit.
3. **A light background load makes the paced call faster, not slower.** At 0 % load B\* is late (3.97 % of sent frames, p99 36 ms, as in Day 2); at 25 % load the mean send call drops from 17.55 to **11.34 ms**, the p99 from 36.0 to 25.5 ms, and **no frame is late in either direction**. Heavier load then slows the calls again (13.97, 15.14 ms) through contention. This is direct evidence for the explanation the baseline proposed but could not test: a paced call takes about twice the unpaced time because the chip lowers its clocks (memory, fabric or NE) in the idle gaps between frames. Keeping the memory system busy keeps those clocks up, and the pacing penalty largely disappears (11.3 ms paced against 9.5 ms unpaced).
4. The 0 % condition is not fully idle: memstress threads wake every 20 ms even with no copying. That may be why B\* is late 3.97 % here against 7.14 % in Day 2.

## Conclusion

On the M1, memory bandwidth slows the Neural Engine by up to 19 %, which is real but far too small to explain why the two networks barely overlap; the NE itself is the main limit. The more important finding is the third: **the paced call's slowness is a power-management effect, and a light background load removes it, turning B\* on the M1 from 4–7 % late frames into 0 %.** A controller could exploit this with a "keep-warm" load, but it costs energy (memstress at 25 % keeps the CPU cores and memory busy). The next measurements are (a) energy of B\* with a light keep-warm load, to price the trick, and (b) the same contention run on Shams's M4 Pro (`TAG=M4 THREADS=10 MB=256`), to see whether the effect holds there.
