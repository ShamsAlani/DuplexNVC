# M4 Max: same Neural Engine, bigger GPU

**Question.** Does a bigger chip of the same generation change how MLVC runs? The M4 Max has twice the M4 Pro's memory bandwidth, twice its GPU cores, more CPU cores and a larger 16-inch chassis, but the same 16-core Neural Engine. Comparing the two separates what the NE sets from what the rest of the chip sets. With Mohammed's M1 and the MLVC paper's M3 Pro, it also gives the generational comparison M1 → M3 → M4.

**Answer.**
1. **On the Neural Engine, nothing changes.** Every MLVC network runs within 0.5–2.3 % of the M4 Pro, at every resolution, for both models. Sharing the NE, meeting 30 fps and energy per frame pair are the same too. Doubling the bandwidth makes no difference, and a memory load larger than the M4 Pro can even produce slows the NE by only 4 %. **The NE alone sets MLVC's speed, and the NE generation is what makes it faster:** the M4 is 1.3–1.5× faster than the M3 Pro and 1.6× faster than the M1.
2. **On the GPU, the bigger chip matters.** The M4 Max's GPU runs every network 1.6–1.75× faster. That turns two settings that reached only 15 fps on the M4 Pro into **30 fps calls**: full MLVC 720p and MLVC-S 1080p, with the encoder on the GPU and the decoder on the NE. They cost 13–18 times the energy of B\*.
3. **Decoding is identical across the two chips.** Every frame of the M4 Pro's streams decodes bit-identically on the M4 Max's NE, and encoding on the M4 Max gives the same bitstream. An M4 Pro ↔ M4 Max call does not drift when both decode on the NE.

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

### 4. The GPU is 1.6–1.75× faster; the CPU is the same

Each network alone, ms per frame (encoder / decoder):

| Setting | GPU: M4 Max | GPU: M4 Pro | GPU: M4 Max / M4 Pro | CPU: M4 Max | CPU: M4 Pro | CPU: M4 Max / M4 Pro |
|---|---|---|---|---|---|---|
| Full MLVC 360p | 8.50 / 8.11 | 13.33 / 13.18 | 0.63 | 19.96 / 20.33 | 19.78 / 20.74 | 0.99 |
| Full MLVC 540p | 15.23 / 15.18 | 25.84 / 26.21 | 0.58 | 46.08 / 46.35 | 47.40 / 47.70 | 0.97 |
| Full MLVC 720p | 27.19 / 25.71 | 43.22 / 44.07 | 0.61 | 74.11 / 74.66 | 76.10 / 75.80 | 0.98 |
| Full MLVC 1080p | 54.90 / 54.89 | 93.73 / 97.13 | 0.58 | 168.42 / 170.47 | 173.00 / 174.50 | 0.98 |
| MLVC-S 540p | 6.48 / 6.51 | 10.34 / 10.68 | 0.62 | 19.72 / 20.95 | 19.73 / 21.31 | 0.99 |
| MLVC-S 720p | 9.80 / 10.14 | 16.60 / 17.49 | 0.59 | 32.81 / 33.49 | 32.90 / 33.70 | 1.00 |
| MLVC-S 1080p | 20.02 / 21.16 | 35.06 / 37.36 | 0.57 | 68.73 / 71.72 | 71.60 / 74.30 | 0.96 |

The NE is still the fastest processor on the M4 Max (5.90 ms against 8.50 ms on its GPU at 360p).

### 5. The bigger GPU turns two 15 fps settings into 30 fps calls

Encoder on the GPU, decoder on the NE, paced 30 fps call, 3 runs of 60 s:

| Setting | M4 Max | M4 Pro | Late or dropped, send / receive (M4 Max) | Slowest 1 % done within, send / receive | Energy per frame pair, M4 Max (M4 Pro) |
|---|---|---|---|---|---|
| Full MLVC 720p | **30 fps** | 15 fps only | 0.1 % / 0.3 % | 29.9 / 32.3 ms | 1,146 mJ (1,242 mJ) |
| MLVC-S 1080p | **30 fps** | 15 fps only | 0.0 % / 0.5 % | 27.4 / 32.3 ms | 869 mJ (991 mJ) |

On the M4 Pro the 720p encoder takes 43 ms on the GPU, more than the 33 ms a 30 fps frame allows. On the M4 Max it takes 27 ms. The receive side's slowest frames finish at 32.3 ms, close to the 33.3 ms limit, so the headroom is small.

### 6. Contention: memory barely slows the NE (same test as the M4 Pro and the M1)

Baseline experiment 12's script on all three chips: memory loaded at 0–75 % duty while the encoder runs alone on the NE, and while the B\* call runs at 30 fps.

| Load | Memory traffic, GB/s: M4 Max / M4 Pro / M1 | Encoder alone, ms: M4 Max / M4 Pro / M1 | B\* send call, ms: M4 Max / M4 Pro / M1 | B\* late sends: M4 Max / M4 Pro / M1 |
|---|---|---|---|---|
| 0 % | 0 / 0 / 0 | 5.90 / 5.86 / 9.49 | 12.63 / 12.64 / 17.55 | 0 / 0 / 4.0 % |
| 25 % | 228 / 136 / 25 | 6.01 / 6.00 / 10.12 | 8.10 / 8.25 / 11.34 | 0 / 0 / 0 % |
| 50 % | 319 / 205 / 45 | 6.07 / 6.05 / 10.84 | 7.49 / 7.62 / 13.97 | 0 / 0 / 0 % |
| 75 % | 337 / 217 / 46 | 6.14 / 6.12 / 11.27 | 7.44 / 7.37 / 15.14 | 0.1 / 0 / 0 % |
| **Encoder slowdown at 75 %** | | **+4.1 % / +4.4 % / +18.8 %** | | |

### 7. Decoding across the two chips is identical

| Stream (from the M4 Pro) | Frames | NE frames identical to the M4 Pro's NE decode | Worst frame, GPU / CPU decode against the NE decode |
|---|---|---|---|
| B\* outgoing (full MLVC 360p) | 1,802 | **1,802** | 38.54 / 39.51 dB |
| Incoming, the 7 settings | 600 each | **600 each** | 36.3–44.6 / 36.4–42.9 dB |

The NE decode is deterministic on the M4 Max, and re-encoding the B\* incoming video on the M4 Max's NE gives a **byte-identical bitstream** to the M4 Pro's. GPU and CPU decodes drift exactly as on the M4 Pro (worst frame 38.5 dB) and the M1 (38.51 dB). Per stream: [`results/M4Max_decode_vs_M4Pro.csv`](results/M4Max_decode_vs_M4Pro.csv).

## Why

1. **The NE's own compute sets MLVC's speed, not memory.** Doubling bandwidth (273 → 546 GB/s) changed no network's NE time by more than 2.3 %. Loading the memory with 337 GB/s, more than the M4 Pro can move at all, slowed the encoder by only 4.1 %, as on the M4 Pro (4.4 %). Only the M1, with 68 GB/s, is held back by memory (18.8 %).
2. **Poor sharing is a property of the NE design, not of the chip.** S = 1.11 of an ideal 1.99 on the M1, the M4 Pro and the M4 Max alike: the two networks mostly take turns on the NE.
3. **Same NE, same energy.** 64.7 against 65.3 mJ per frame pair, 97 % of it on the NE. At 30 fps that is about 2 W, far below what either chassis can cool; the thermal state stayed `nominal` for all 12,334 s of runs, so the 16-inch chassis brings no advantage.
4. **The GPU scales with its size, the CPU does not.** Twice the GPU cores gives 1.6–1.75× the speed. Two more performance cores give the CPU almost nothing (1–4 %).
5. **The pacing penalty is the same on every chip.** A paced 30 fps call takes about twice the unpaced time per frame (12.6 against 5.9 ms), and a background memory load removes most of it (7.4 ms at 75 %) on the M4 Max as on the M4 Pro. The chip lowers its clocks in the idle gaps between paced frames, whatever its size.
6. **The NE generation is what makes MLVC faster:** M1 → M3 → M4 takes the B\* networks from about 9.6 to 7.9 to 5.9 ms. MLVC-S gains more from M3 to M4 (0.67–0.72 of the M3 Pro's time) than full MLVC (0.74–0.76); the M3 Pro numbers come from the paper's own measurement, so we cannot yet say which layers account for the difference.

The M4 Max is 1–2 % slower than the M4 Pro on the NE at the higher resolutions. This is within the spread of a single round and may also reflect macOS 26.3 against 26.6, so we report the two chips as equal.

**What this means for the controller.**
- For NE placements, one table of times per chip generation is enough; Pro or Max needs no separate entry.
- For GPU placements, the controller must also know the GPU size: on the M4 Max, full MLVC 720p and MLVC-S 1080p become 30 fps options, but at about 26–34 W (869–1,146 mJ per frame pair), 13–18 times B\*'s energy. They suit a plugged-in call that needs the higher resolution.
- Between M4 Pro and M4 Max, drift needs no bound when both decode on the NE.

## What was run

The baseline's own protocols and analysis (experiments 03, 04, 06, 09 and 12), with the same Core ML models and bitstreams copied from Shams's Mac. Quiet mode throughout: AC power, maximum brightness, Wi-Fi and Bluetooth off, no other apps. Thermal state `nominal` in every logged second.

| Date (+04) | Time | Duration | What |
|---|---|---|---|
| Fri 27 Nov 2026 | 02:00–02:42 | 41 min | B\*: each network alone, taking turns and both at once (2 rounds of 60 s); three paced 30 fps calls with `powermetrics` and 120 s idle; the other six settings, each network alone on the NE (1 round) |
| Fri 27 Nov 2026 | 03:08–04:44 | 96 min | Decoding of the M4 Pro's 8 streams on the NE (twice), GPU and CPU, and the B\* incoming video re-encoded on the NE; each network alone on the GPU and on the CPU, all 7 settings (40 s runs) |
| Fri 27 Nov 2026 | 04:52–06:00 | 68 min | Experiment 12 contention (12 memstress threads, 3 rounds × 4 loads × 2 workloads, 60 s runs, 60 s rests); encoder-GPU / decoder-NE 30 fps calls for full MLVC 720p and MLVC-S 1080p (3 × 60 s each, with `powermetrics`) |

The rests were 30 s (20 s in the GPU and CPU runs) instead of the baseline's 60 s, and the six other settings ran once each, to fit the M4 Max's limited availability. Not measured on the M4 Max: the full placement sweep of experiment 09.

## Files

| Path | Contents |
|---|---|
| `results/M4Max_Bstar_vs_M4Pro.csv` | Table 1, every B\* metric with both chips and the ratio |
| `results/M4Max_alone_vs_M4Pro_M3Pro.csv` | Table 2 |
| `results/generations_Bstar.csv` | Table 3 |
| `results/M4Max_GPU_CPU_alone_vs_M4Pro.csv` | Table 4 |
| `results/M4Max_GPU_NE_30fps.csv` | Table 5 |
| `results/contention_3chips.csv` | Table 6 |
| `results/M4Max_decode_vs_M4Pro.csv` | Table 7, per stream |
| `results/M4Max_summary.txt` | The printed summary of all runs |
| `results/M4Max_specs.txt`, `results/M4Pro_specs.txt` | Machine specs |
| `raw_data/` | Every run (`frames.csv`, `run.txt`, `power.txt`, `memstress.txt`, logs), the decode results, the thermal log and the console output |
| `scripts/` | The scripts used; they read the baseline's settings and tools |
