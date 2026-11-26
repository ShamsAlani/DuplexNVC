# M4 Max: same Neural Engine, same speed

**Question.** Does a bigger chip of the same generation run MLVC faster? The M4 Max has twice the M4 Pro's memory bandwidth, twice its GPU cores, more CPU cores and a larger 16-inch chassis, but the same 16-core Neural Engine. Comparing the two separates what the NE sets from what the rest of the chip sets. With Mohammed's M1 and the MLVC paper's M3 Pro, it also gives the generational comparison: M1 → M3 → M4.

**Answer.** No. On the M4 Max every MLVC network runs within 0.5–2.3 % of the M4 Pro, at every resolution and for both models. Sharing the NE, meeting 30 fps and energy per frame pair are the same too. **The Neural Engine alone sets MLVC's speed, and each NE generation is what makes it faster:** the M4 is 1.3–1.5× faster than the M3 Pro and 1.6× faster than the M1.

## The two M4 chips

| | M4 Pro (Shams, the baseline) | **M4 Max (Warda)** | M4 Max / M4 Pro |
|---|---|---|---|
| Machine | MacBook Pro 14-inch (Mac16,8) | MacBook Pro 16-inch (Mac16,5) | larger chassis, more cooling |
| CPU cores | 14 (10 P + 4 E) | 16 (12 P + 4 E) | 1.2× P-cores |
| GPU cores | 20 | 40 | 2× |
| **Neural Engine** | **16 cores, 38 TOPS** | **16 cores, 38 TOPS** | **same** |
| Unified memory | 24 GB | 64 GB | 2.7× |
| Memory bandwidth (Apple) | 273 GB/s | 546 GB/s | 2× |
| macOS | 26.6 | 26.3 | |

Full specs: [`results/M4Max_specs.txt`](results/M4Max_specs.txt), [`results/M4Pro_specs.txt`](results/M4Pro_specs.txt).

## Results

### 1. B\* (full MLVC 360p, encoder and decoder on the NE): the M4 Max matches the M4 Pro

| Metric | M4 Max | M4 Pro | M4 Max / M4 Pro |
|---|---|---|---|
| Encoder alone, ms per frame | 5.90 | 5.86 | 1.006 |
| Decoder alone, ms per frame | 5.96 | 5.94 | 1.003 |
| Taking turns, ms per frame pair (T_turns) | 11.86 | 11.81 | 1.005 |
| Both on the NE at once, ms per frame pair (T_shared) | 10.66 | 10.68 | 0.999 |
| Sharing speedup S (ideal 1.99) | **1.11** | **1.11** | 1.002 |
| 30 fps call: late or dropped frames, send / receive | 0 % / 0 % | 0 % / 0 % | |
| 30 fps call: slowest 1 % of frames done within, send / receive | 30.2 / 29.2 ms | 29.3 / 28.9 ms | 1.03 / 1.01 |
| Energy per frame pair (NE + CPU) | **64.7 mJ** | **65.3 mJ** | 0.99 |

### 2. Every setting, each network alone on the NE: M4 Max = M4 Pro, both well ahead of the M3 Pro

| Setting | M4 Max enc / dec ms | M4 Pro enc / dec ms | M4 Max / M4 Pro | M3 Pro enc / dec ms (paper) | M4 Max / M3 Pro |
|---|---|---|---|---|---|
| Full MLVC 360p | 5.90 / 5.96 | 5.86 / 5.94 | 1.005 | 7.72 / 8.14 | 0.75 |
| Full MLVC 540p | 11.86 / 12.02 | 11.83 / 11.82 | 1.010 | 15.22 / 16.05 | 0.76 |
| Full MLVC 720p | 22.38 / 22.63 | 22.23 / 22.17 | 1.014 | 29.59 / 30.21 | 0.75 |
| Full MLVC 1080p | 46.96 / 49.06 | 46.36 / 47.56 | 1.022 | 64.10 / 65.79 | 0.74 |
| MLVC-S 540p | 4.91 / 5.01 | 4.83 / 4.92 | 1.017 | 6.58 / 7.27 | 0.72 |
| MLVC-S 720p | 8.41 / 8.72 | 8.25 / 8.48 | 1.023 | 11.93 / 13.61 | 0.67 |
| MLVC-S 1080p | 18.18 / 18.58 | 18.01 / 18.42 | 1.009 | 25.32 / 28.90 | 0.68 |

### 3. Across generations (B\*)

| Metric | M1 (Mohammed) | M3 Pro (paper) | M4 Pro | M4 Max |
|---|---|---|---|---|
| Encoder / decoder alone, ms | 9.47 / 9.72 | 7.72 / 8.14 | 5.86 / 5.94 | 5.90 / 5.96 |
| Time relative to the M4 Pro | 1.63× | 1.34× | 1 | 1.00× |
| Sharing speedup S | 1.11 | — | 1.11 | 1.11 |
| 30 fps call, late sends | 7.1 % | — | 0 % | 0 % |
| Energy per frame pair | 121.2 mJ | — | 65.3 mJ | 64.7 mJ |

## Why

1. **Memory bandwidth does not limit MLVC on the NE.** Doubling bandwidth (273 → 546 GB/s) changed no network's time by more than 2.3 %. If memory were the limit, the M4 Max would be faster. This agrees with Mohammed's contention test on the M1, where 46 GB/s of extra memory traffic slowed the NE by only 19 %. The NE's own compute sets the time.
2. **The extra GPU and CPU cores are idle.** In B\* both networks run on the NE. The CPU only does the arithmetic coding (1.9 mJ of the 65 per frame pair on both chips), and the GPU does nothing (0 mJ on both).
3. **Poor sharing is a property of the NE design, not of the chip.** S = 1.11 of an ideal 1.99 on the M1, the M4 Pro and the M4 Max alike: on every chip the two networks mostly take turns on the NE instead of running side by side.
4. **Same NE, same energy.** 64.7 against 65.3 mJ per frame pair, 97 % of it on the NE. At 30 fps that is about 2 W, far below what either chassis can cool. The thermal state stayed `nominal` for all 2,470 s of runs, so the 16-inch chassis brings no advantage here.
5. **What does make MLVC faster is the NE generation.** M1 → M3 → M4 takes the B\* networks from about 9.6 to 7.9 to 5.9 ms. Within a generation, Pro against Max makes no difference.
6. **MLVC-S gains more from M3 → M4 than full MLVC** (0.67–0.72 of the M3 Pro's time, against 0.74–0.76). The M3 Pro numbers come from the paper's own measurement, so we cannot yet say which layers account for the difference.

The M4 Max is 1–2 % slower than the M4 Pro at the higher resolutions. This is within the run-to-run spread of a single round and may also reflect macOS 26.3 against 26.6, so we report the two chips as equal (within 2.3 %).

**What this means for the controller.** One table of NE times per chip generation is enough: Pro or Max within a generation needs no separate entry. A switch to a GPU placement is the only decision that would depend on the tier, because only the GPU differs.

## What was run

The baseline's own protocol and analysis (experiments 03, 06 and 09), with the same Core ML models and incoming bitstreams copied from Shams's Mac. Each network alone, taking turns and both at once, 2 rounds of 60 s runs. Three paced 30 fps two-way calls of 60 s with `powermetrics`, plus 120 s idle for subtraction. The six other settings, each network alone, once. Quiet mode: AC power, maximum brightness, Wi-Fi and Bluetooth off, no other apps. Run on 27 Nov 2026, 01:56–02:42.

Not measured on the M4 Max: GPU placements, the contention curve and decoding across chips (the M1 shows no cross-chip drift).

## Files

| Path | Contents |
|---|---|
| `results/M4Max_Bstar_vs_M4Pro.csv` | Table 1, every B\* metric with both chips and the ratio |
| `results/M4Max_alone_vs_M4Pro_M3Pro.csv` | Table 2 |
| `results/generations_Bstar.csv` | Table 3 |
| `results/M4Max_summary.txt` | The run's printed summary |
| `results/M4Max_specs.txt`, `results/M4Pro_specs.txt` | Machine specs |
| `raw_data/` | Every run (`frames.csv`, `run.txt`, `power.txt`, logs), the thermal log and the console output |
| `scripts/` | The scripts used (`cc_gen` runs this measurement; they read the baseline's settings and tools) |
