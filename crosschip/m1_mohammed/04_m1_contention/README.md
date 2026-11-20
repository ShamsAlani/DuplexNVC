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

*(fill in on Day 4)*

| Load | GB/s | Encoder alone, call ms | B\* send p99 ms | B\* receive p99 ms | late % |
|---|---|---|---|---|---|
| 0 % | … | … | … | … | … |
| 25 % | … | … | … | … | … |
| 50 % | … | … | … | … | … |
| 75 % | … | … | … | … | … |

## Conclusion

*(memory bandwidth or the NE itself; compare with Shams's M4 Pro curve)*
