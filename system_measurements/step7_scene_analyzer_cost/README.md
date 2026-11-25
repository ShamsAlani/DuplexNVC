# Step 7 (cost) — Scene analyzer: what does face and body detection cost inside the call?

**Question.** DuplexNVC's controller reacts to the people in the frame, so a scene analyzer (Apple Vision face and body detection) has to run on the camera frames during the call, on the same chip as the encoder and decoder. If the analyzer slows the codec or costs much energy, adapting is not worth it. The plan sets the limit (C4): **at most 2 ms per frame pair on average and no late frames**. Which way of running the analyzer stays inside it?

How small a face the analyzer can find at the call resolution is the other half of Step 7, measured on the Step 8 clips in [`detection_recall/`](../../detection_recall/).

## What was run

**24 Nov 2026, 8:59–10:01 pm (+04)**, MacBook Pro 14-inch M4 Pro, macOS 26.6.2 (25G83), AC power, quiet mode (Wi-Fi and Bluetooth off, screen at maximum brightness, no other apps), as the first block of the run of Step 6.

- **Call:** B\* (full MLVC 360p, encoder and decoder on the NE), paced at 30 fps for 60 s, as in baseline experiments 03 and 14.
- **Analyzer** (`scripts/va.swift`, a separate process started with the call): reads the 360p camera frames the encoder gets, at the call's pace, and runs `VNDetectFaceRectanglesRequest` and `VNDetectHumanRectanglesRequest` on every Nth frame. It logs the time of every analysis and the faces and bodies found.
- **Variants:** V0 no analyzer; V1 every 15 frames (2 per second), Vision's default processors; V2 every 15 frames, pinned to the CPU; V3 every 30 frames, pinned to the CPU.
- **Rounds:** 120 s of idle, then 5 interleaved rounds of the four variants, 60 s rest after each call.
- **Measured:** chip energy per frame pair (IOReport counters over the last 49 s of the call, idle subtracted, as Step 9 and Step 6); late frames and p99 latency per direction; the analyzer's time per analysis (median of the run), and per frame pair = time per analysis / N.

**Runs, including the ones set aside.** The variants were first run on 23 Nov 2026, 9:45–10:47 pm, as part of Step 6's first run. That run is set aside: the analyzer was stopped when the call ended, before it wrote its timing file, so the time per analysis was missing; and the screen was at 75 % brightness instead of the quiet-mode maximum. The analyzer was changed to finish on its own (12 s after the call) and always write its file, and the block was run again on 24 Nov. In the first analysis of the repeat, the energy window ended at the analyzer's end instead of the call's, so it took in about 10 s of quiet after the call and every variant came out cheaper than no analyzer; `btana.py` now ends the window with the call's last frame (`frames.csv`), and the numbers below come from that analysis of the same run.

## How to run

The analyzer is built and the variants are run by Step 6's `scripts/battery_lowpower_runs.sh` (`~/Downloads/d/bt/`), Part B; `btana.py` there writes the tables below.

| Script | What |
|---|---|
| `scripts/va.swift` | The analyzer: `va <camera.nv12> <w> <h> <every> <cpu 0/1> <seconds> <out.csv>`; paced at 30 fps, face and body requests, prints the median time per analysis |
| `../step6_battery_lowpower/scripts/battery_lowpower_runs.sh`, `btana.py` | Runs the variants with the call and the energy counters; the analysis |

## Files

| Path | Contents |
|---|---|
| `raw_data/step7/v0…v3/r1…r5/` | Per run: `t.txt`, `run.txt`, `frames.csv` (the call), `va.csv` (every analysis: frame, ms, faces, bodies), `va.txt` (median and p95 time) |
| `results/step7.csv`, `summary.txt` | Energy, late frames, p99 and analyzer time per variant; the cost against V0 and the C4 verdict |

## Results

| Variant | Chip energy per frame pair | Extra vs V0 | Analyzer time per analysis | Per frame pair | Late frames | p99 enc / dec | C4 |
|---|---|---|---|---|---|---|---|
| V0: no analyzer | 76.8 mJ (76.4–77.1) | — | — | — | 0 % | 29.6 / 29.0 ms | — |
| **V1: every 15, default** | **77.5 mJ** (77.3–77.7) | **+0.75 mJ (+1.0 %)** | 9.5 ms | **0.63 ms** | 0 % | 29.6 / 29.1 ms | **met** |
| V2: every 15, CPU | 80.6 mJ (80.5–82.0) | +3.86 mJ (+5.0 %) | 32.7 ms | 2.18 ms | 0 % | 29.5 / 29.1 ms | not met (time) |
| V3: every 30, CPU | 78.8 mJ (78.6–78.9) | +2.00 mJ (+2.6 %) | 33.2 ms | 1.11 ms | 0 % | 29.6 / 29.2 ms | met |

- **On its default processors, the analyzer costs 1 % of the call's energy and 0.63 ms per frame pair,** a third of the limit, and the call keeps every deadline: p99 is unchanged (29.6 / 29.1 ms against 29.6 / 29.0 ms).
- **Pinning it to the CPU makes it slower and dearer,** not cheaper: 32.7 ms per analysis (3.4× the default), 5× the extra energy at the same rate. Halving the rate (V3) brings the CPU inside the time limit but still costs 2.7× V1's energy.
- In V1 the NE energy rises by only 0.6 mJ: Vision's default work does not compete noticeably with MLVC on the NE at 2 analyses per second.

## Conclusion

1. **The scene analyzer fits inside the call: C4 is met** with Vision on its default processors at 2 analyses per second (0.63 ms and +0.75 mJ per frame pair, no late frames). Content-adaptive control is affordable on this chip.
2. **Leave Vision on its default processors.** Moving it to the CPU, to keep it away from the NE, costs more time and more energy and buys nothing, since the NE call is not slowed by it.
3. With detection recall (100 % of the call-distance faces at 360p, [`detection_recall/`](../../detection_recall/)), the controller can run the analyzer on the 360p frame every 15 frames.
