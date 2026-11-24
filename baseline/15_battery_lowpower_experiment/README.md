# 15 — Battery and Low Power Mode experiment: does B\* cost the same off the charger? (Step 6)

**Question.** Every energy figure so far (experiments 06, 09, 10, 14) was measured on AC power. A video call on a laptop often runs on battery, sometimes with Low Power Mode on, and possibly for an hour or more. This experiment asks four things:

1. Does a call cost the same chip energy on battery as on AC, and at high and at low charge?
2. What does Low Power Mode save, and does the call still keep its 33.3 ms deadline?
3. What does the **whole laptop** draw from the battery during a call (screen, memory, power conversion included), and how long would a call last on a full charge?
4. Does a long call (30 and 60 minutes) heat the chip enough to slow it down or raise its power?

The scene analyzer's cost (Step 7) was measured in the same run; it is reported separately in [`16_scene_analyzer_cost_experiment`](../16_scene_analyzer_cost_experiment/).

## What was run

Two calls, each a paced 30 fps two-way call (camera encoded and incoming stream decoded at the same time, same clips as experiments 03 and 09, first 64 frames of each direction excluded):

- **B\***: full MLVC 360p, encoder and decoder on the NE.
- **MLVC-S 720p**: encoder on the GPU, decoder on the NE (one of the two settings on the 30 fps energy–quality front of experiment 10).

**Blocks.** Each block is 120 s of idle followed by 5 interleaved rounds of the two calls (60 s each, 60 s rest after each call, the order alternates by round):

| Block | Power | Low Power Mode | When (+04) | Battery |
|---|---|---|---|---|
| `bat_high` | battery | off | 24 Nov, 1:47–2:19 am | 80 → 74 % |
| `bat_high_lpm` | battery | **on** | 2:19–2:52 am | 74 → 69 % |
| `drain60` | battery | off | 2:52–3:52 am: **one 60-min B\* call** | 69 → 59 % |
| `drain_more` | battery | off | 3:53–4:28 am: MLVC-S 720p calls of 5 min until the battery reached 30 % | 59 → 28 % |
| `bat_low` | battery | off | 4:28–5:00 am | 28 → 20 % |
| `bat_low_lpm` | battery | **on** | 5:00–5:33 am | 20 → 15 % |
| `ac` | AC | off | 24 Nov, 10:01–10:33 pm | 100 % |
| `ac_lpm` | AC | **on** | 10:33–11:06 pm | 100 % |
| `sustained30` | AC | off | 11:06–11:37 pm: **one 30-min B\* call** | 100 % |

**Measurements.**

- **Chip energy:** IOReport "Energy Model" counters read by `ioe` (as in experiment 14): CPU, GPU, NE, DRAM and the video blocks, every 100 ms in the blocks and every 1 s in the long calls. Energy per frame pair = (mean power over the last 49 s − the block's own idle power) / 30.
- **Whole-laptop power:** voltage × current of the battery, read once a second from the battery gauge (`bat.py`, `ioreg AppleSmartBattery`). On AC the battery side is not measured.
- **Timing:** late frames and p99 latency per direction from the measurement program (`run.txt`), as in experiments 03 and 09.
- **Low Power Mode** is switched with `pmset -a lowpowermode 1|0` (password once at the start).
- **Thermal state:** `pmset -g therm` after each run and `thermal_log` throughout.

**Quiet mode:** Wi-Fi and Bluetooth off, screen at maximum brightness with automatic brightness and True Tone off, no other apps, `caffeinate`.

**Runs, including the ones set aside.** The experiment was first run on 23 Nov 2026: the battery blocks from 4:26 to 8:31 pm (4.1 h), a wait for the charger until 9:45 pm, then the AC blocks, the scene-analyzer blocks of experiment 16 and the 30-min call until 12:23 am (2.6 h), about 8 hours in all. **That run is set aside:** the screen was at 75 % brightness instead of the quiet-mode maximum, which changes the battery-side power, and the scene analyzer's timing file was not written (experiment 16). Everything was run again at maximum brightness: the battery blocks on 24 Nov from 1:47 to 5:33 am (3.8 h), and the AC part, with the analyzer fixed, on 24 Nov from 8:59 to 11:37 pm (2.6 h). Every result below comes from the repeat. The first run's files are kept on the measurement laptop (`phase2/bt_75pct/`, `phase2/bt_ac_attempt1/`), not used.

**The battery started at 80 %, not 100 %:** macOS's Optimized Battery Charging held the charge at 80 % overnight. The "high battery" blocks therefore ran between 80 and 69 %.

## How to run

The scripts live in `~/Downloads/d/bt/` and use `../he/ioe.c` (experiment 14) and the shared settings in `../v` and `../s2cfg`.

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/all` | Part A on battery (asks you to unplug, runs the battery blocks, stops at 15 %, waits for the charger), then Part B on AC (the analyzer blocks of experiment 16, `ac`, `ac_lpm`, the 30-min call), then `btana.py` | ≈ 4 h on battery + ≈ 2.6 h on AC | **quiet**, password once; resumable (finished runs are skipped) |
| `scripts/bat.py` | Battery logger: time, %, mV, mA, W, external power, charging, temperature, Low Power Mode, once a second | — | — |
| `scripts/btana.py` | Chip energy per frame pair per block and call (over the last 49 s of the call itself), late frames and p99, long-call drift | — | — |
| `scripts/battery_side.py` | Whole-laptop power from `battery.csv` (idle from the rests between calls; steady values from the long calls) | — | — |

## Files

| Path | Contents |
|---|---|
| `raw_data/<block>/<call>/r1…r5/` | Per run: `t.txt` (start/end time, battery % at start and end, AC or not), `run.txt` (frames, late frames, p99 per direction), `frames.csv` (every frame: schedule, start, end, latency, late); `<call>/rN.log` and `.therm` (program log, thermal state) |
| `raw_data/<block>/idle/t.txt` | The block's idle recording |
| `raw_data/drain60/`, `drain_more/`, `sustained30/` | The long calls |
| `raw_data/battery.csv`, `thermal.csv` | Battery gauge once a second (24 Nov runs); thermal log |
| `raw_data/logs/out_all.txt`, `out_rq.txt` | Console of every run, the set-aside first run included |
| `results/summary.txt`, `energy.csv` | `btana.py` output (the "laptop mJ" column there uses 60 s windows and is superseded by `battery_side.csv`, see below) |
| `results/battery_side.csv` | Whole-laptop power, per block and for the long calls |

The 100 ms energy-counter samples (`ioe.csv`, ≈ 700 MB) and the outgoing bitstreams are kept on the measurement laptop.

## Results

### Chip energy per frame pair (mJ, idle subtracted, median of 5 rounds)

| Block | B\* | (min–max) | MLVC-S 720p | (min–max) | Late frames, MLVC-S 720p encoder |
|---|---|---|---|---|---|
| AC | 76.8 | 76.6–76.9 | 741.6 | 728.8–768.5 | 0.06 % |
| Battery, high (80–74 %) | 76.8 | 76.3–77.0 | 756.0 | 726.2–764.4 | 0.06 % |
| Battery, low (28–20 %) | 76.9 | 76.8–77.2 | 739.7 | 733.5–765.3 | 0.00 % |
| **AC, Low Power Mode** | **71.9** | 71.8–72.0 | **346.4** | 339.0–354.9 | **19.7 %** |
| **Battery high, Low Power Mode** | **71.7** | 71.7–71.9 | **346.1** | 340.4–357.3 | **18.0 %** |
| **Battery low, Low Power Mode** | **71.6** | 71.6–71.7 | **346.9** | 342.4–347.5 | 1.3 % |

B\* had no late frames in any block (at most 0.06 %, one frame), and its p99 latency stayed at 29.1–29.9 ms (encoder) and 28.8–29.4 ms (decoder) of 33.3 ms. Chip idle power was 371–379 mW in every block.

### Whole laptop, from the battery (`battery_side.csv`)

| Call | Battery power | Above idle (4.3 W) | Per frame pair | Battery use | Call time from full |
|---|---|---|---|---|---|
| B\*, 60-min call (steady, after 5 min) | **7.76 W** | 3.46 W | **115 mJ** (chip: 76.8) | **10 % per hour** | **≈ 10 h** |
| MLVC-S 720p, 5-min calls (steady, after 1 min) | **36.7 W** | 32.4 W | **1,080 mJ** (chip: 756) | **60 % per hour** | **≈ 1.7 h** |

- **Idle on battery** (screen at maximum brightness, Wi-Fi off) is 4.3 W, of which the chip is only 0.37 W: the screen and the rest of the laptop take the remaining 3.9 W.
- **The laptop pays 1.4–1.5× the chip's energy** for a call (115 vs 76.8 mJ for B\*, 1,080 vs 756 mJ for MLVC-S 720p): power conversion and the parts outside the chip's counters.
- The 60 s calls in the blocks read lower on the battery side (B\* 6.3–7.9 W over their last 30 s) because the battery gauge averages its current over tens of seconds and a 60 s call never reaches the steady value. They are kept in `battery_side.csv` as indicative only; the steady values above come from the long calls. Low Power Mode lowers the battery-side power in the same direction as the chip energy (MLVC-S 720p: 19–21 W instead of 34–35 W).

### Long calls

| Call | 0–5 min | last 5 min | Late frames |
|---|---|---|---|
| B\*, 60 min on battery | chip 2,653 mW, battery 7.42 W | chip 2,659 mW, battery 7.86 W | 0.00 % / 0.00 % |
| B\*, 30 min on AC | chip 2,650 mW | chip 2,656 mW (highest 5 min: 2,664) | 0.00 % / 0.00 % |

Chip power changed by less than 1 % over an hour; the thermal state stayed nominal (no speed limit reported).

## Conclusion

1. **Battery or AC, high or low charge: the same chip energy.** B\* costs 76.8–76.9 mJ per frame pair in every normal block; MLVC-S 720p 740–756 mJ. Every energy result of experiments 06–14 holds off the charger.
2. **Low Power Mode is free for B\* and fatal for the GPU encoder.** It saves 6.6 % of B\*'s chip energy (76.8 → 71.6–71.9 mJ) with no late frames and an unchanged p99. It halves MLVC-S 720p's energy (about 740–756 → 346 mJ) but makes up to 18–20 % of the GPU encoder's frames late: the setting no longer meets 30 fps. A controller that sees Low Power Mode should keep NE settings and move a GPU encoder back to the NE or lower the resolution.
3. **A B\* call lasts about 10 hours on battery** (7.8 W for the whole laptop, 10 % per hour at maximum brightness); MLVC-S 720p with its GPU encoder about 1.7 hours (36.7 W, 60 % per hour). The laptop as a whole pays 1.4–1.5× what the chip counters show.
4. **No thermal drift:** an hour-long B\* call keeps the same chip power (within 1 %) and no late frames; long calls do not change the baseline.
