# System measurements: what we measured after the baseline report

The [`baseline/`](../baseline/) holds the twelve experiments of our submitted baseline report. This folder holds the measurements of the duplex system that we made after it, following the plan to 3 December. They measure MLVC as released (nothing in the codec is changed here), on the same MacBook Pro (M4 Pro, 24 GB, macOS 26.6.2, libmlvc `eb5d60a`), with the baseline's program, clips, metrics and [quiet mode](../baseline/README.md#quiet-mode). Our changes to MLVC are elsewhere: its coding algorithm in [`algorithm_enhancements/`](../algorithm_enhancements/), its network in [`lab_gpu_runs/`](../lab_gpu_runs/).

## Measurements

| Folder | Plan step | Question | Runs | Time |
|---|---|---|---|---|
| [`step6_battery_lowpower`](step6_battery_lowpower/) | Step 6 | Does a call cost the same on battery, at low charge and in Low Power Mode? Whole-laptop power, call time on a charge, 30- and 60-min calls | 80 + 3 long calls | 3.8 h + 1.6 h |
| [`step7_scene_analyzer_cost`](step7_scene_analyzer_cost/) | Step 7 (cost) | Does face and body detection fit inside the B\* call (≤ 2 ms per frame pair, no late frames)? | 20 | 1 h |
| [`step9_hevc_anchor`](step9_hevc_anchor/) | Step 9 | The Mac's real-time hardware HEVC at MLVC's bitrates: quality, and the energy of a two-way call measured over the same chip blocks | 200 + 25 | 10 min + 1.2 h |

Detection recall (the other half of Step 7) and the controller data (Step 8) are in [`detection_recall/`](../detection_recall/) and [`controller_data/`](../controller_data/); the cross-chip study in [`crosschip/`](../crosschip/).

In total about **7.8 hours** of measurement that the results come from, plus about 25 hours of runs that were set aside and repeated (Steps 6, 7 and 9 say which, why, and what was fixed).

## Headline results

| Question | Answer | Where |
|---|---|---|
| Mac's real-time hardware HEVC vs B\* | **HEVC needs +69 % more bits** (coded PSNR-Y); matches MLVC-S 720p only on face LPIPS | [Step 9](step9_hevc_anchor/) |
| Energy of a call: hardware HEVC vs MLVC (Step 9) | **HEVC costs 1.6 mJ per frame pair at 360p and 2.6 mJ at 720p; B\* 76.7 mJ (48×), MLVC-S 540p 52.5 mJ (33×), MLVC-S 720p 739 mJ (284×)**. MLVC's bit saving is paid for in energy | [Step 9](step9_hevc_anchor/) |
| Battery, Low Power Mode (Step 6) | **Same chip energy on battery and AC**, at high and low charge (B\* 76.8 mJ); Low Power Mode saves 6.6 % for B\* with no late frames but makes 18–20 % of a GPU encoder's frames late; a B\* call lasts ≈ 10 h on battery (7.8 W for the whole laptop), MLVC-S 720p ≈ 1.7 h; no thermal drift in 60 min | [Step 6](step6_battery_lowpower/) |
| Scene-analyzer cost (Step 7) | **Fits**: Vision every 15 frames on its default processors costs 0.63 ms and +0.75 mJ (+1 %) per frame pair, no late frames; pinning it to the CPU is slower and dearer | [Step 7](step7_scene_analyzer_cost/) |

## How to run

After the baseline setup ([`baseline/REPRODUCE.md`](../baseline/REPRODUCE.md) §1–2):

```bash
mkdir -p ~/Downloads/d/{hv,he,bt}
cp <repo>/system_measurements/step9_hevc_anchor/scripts/{all,hv.py,hvana.py} ~/Downloads/d/hv/
cp <repo>/system_measurements/step9_hevc_anchor/scripts/energy/* ~/Downloads/d/he/
cp <repo>/system_measurements/step6_battery_lowpower/scripts/* <repo>/system_measurements/step7_scene_analyzer_cost/scripts/* ~/Downloads/d/bt/
chmod +x ~/Downloads/d/{hv,he,bt}/*
```

| Order | Command (from `~/Downloads/d`) | Folder | What | Time | Conditions |
|---|---|---|---|---|---|
| 1 | `cd hv && ./hevc_quality_runs.sh` | `step9_hevc_anchor` | Hardware HEVC at MLVC's bitrates (200 runs), BD-rate | 10 min | any; **resumable** |
| 2 | `./quiet_mode_on.sh` | `baseline/common` | Quiet mode on | 1 min | see [baseline quiet mode](../baseline/README.md#quiet-mode) |
| 3 | `cd he && ./hevc_energy_runs.sh` | `step9_hevc_anchor` | Energy of hardware HEVC and MLVC calls from the chip's energy counters (25 runs) | 70 min | **quiet**; **resumable** |
| 4 | `./quiet_mode_off.sh` | `baseline/common` | Quiet mode off | 1 min | — |
| 5 | `./quiet_mode_on.sh`, then `cd bt && ./battery_lowpower_runs.sh` | `step6_battery_lowpower`, `step7_scene_analyzer_cost` | Battery blocks (unplug when asked; stops at 15 %, waits for the charger), then on AC: the analyzer variants, AC and AC + Low Power Mode blocks, the 30-min call; `btana.py`, then ``battery_side.py`` | ≈ 4 h + 2.6 h | **quiet**, password; start fully charged with Optimized Battery Charging off; **resumable** |
| 6 | `./quiet_mode_off.sh` | `baseline/common` | Quiet mode off | 1 min | — |

Every `*_runs.sh` here can be interrupted and run again; it continues where it stopped.

## Problems we hit and how they are fixed

| Problem | Fix |
|---|---|
| Step 6 run at 75 % screen brightness | Repeated at maximum (quiet mode); the battery-side power depends on the screen |
| Step 6's battery blocks started at 80 % | macOS's Optimized Battery Charging held the charge at 80 %; turn it off the day before (System Settings → Battery) |
| The analyzer's timing file was missing (Step 7) | `va` is no longer stopped with the call; it finishes 12 s later and writes `va.csv` |
| The analyzer looked cheaper than no analyzer | `btana.py` ends the energy window with the call's last frame (`frames.csv`), not when the analyzer ends |
| Battery-side power of 60 s calls reads low | The battery gauge averages its current over tens of seconds; `battery_side.py` takes steady values from the 60-min and 5-min calls |
| Step 9 energy: the incoming HEVC stream did not loop, and a variable clash ran empty conditions (14.3 h lost) | Local variables and a separate loop counter in the script; a guard stops on an empty condition |
| Step 9 energy: the looped incoming MP4 had about 350 fps timestamps, so the decoder ran far faster than 30 fps | The incoming stream is encoded straight to an MP4 of 1800 frames at 30 fps, checked with `ffprobe`; a call must decode 1700–1900 frames |
| Step 9 energy: the display slept during the run and the Mac stalled twice | The script keeps the display and the system awake (`caffeinate -dims`); the analysis prints both idle recordings and excludes stalled runs |
