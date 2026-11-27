# E6 — A2's drift bound on all VCD clips, with confidence intervals

**Question.** A2 chose LTR recovery every 32 frames as the drift bound for a decoder on another processor, from the 20 VCD evaluation clips. **Does its cost and its effect on the worst frame hold over the whole VCD set, and how precisely do we know them?** VCD has 160 clips in four groups of 40: `th` (talking head), `th-bb` (blurred background), `th-ob` (other background) and `th-m` (filmed on a phone, portrait).

## What was run

- **Where:** MacBook Pro 14-inch M4 Pro, macOS 26.6.2, libmlvc `eb5d60a`, normal use (quality only). 26 Nov 2026, 10:33 pm – 27 Nov, 5:29 am (+04): **1,920 jobs in 6.9 h** (about 13 s each).
- **Procedure:** baseline experiment 11's job (`drift_runner.py`), as A2: every clip's 1080p MP4 scaled to the setting's size (Lanczos, 300 frames), encoded with MLVC's default structure (an I-frame every 64 frames, `main`) and with A2's bound (`l32`: `--ltr-period 16 --ltr-recovery-period 2`), at QP 16/24/32/40.
- **Settings:** MLVC-S 540p (the bound's main use) and B\* (full MLVC 360p).
- **Processors:** encoder and decoder on the NE and the GPU (4 pairs). A2's case is a GPU decoder on the other side; the CPU, measured in A2, is left out to fit the whole set into one night.
- **Clips:** the 120 landscape clips of `th`, `th-bb` and `th-ob`, taken in turn from the groups so that a partial run covers all of them. The 40 `th-m` clips are portrait (1080 × 1920) and were not picked up by the first run; they are measured next (rotated by 90° to the same landscape sizes), and this page is updated then.
- **Measures**, as A2: **cost** = BD-rate (coded PSNR-Y) of NE → NE with the bound against NE → NE with the default structure, both of the mean curve over the clips (how A2 reports it) and per clip (mean with a 95 % confidence interval, and median); **worst frame** = the lowest PSNR-Y of the decode against the decode on the encoder's processor over the two mismatched pairs (NE → GPU, GPU → NE), per clip.
- **Download:** the clips come from VCD's public storage (`scripts/e6_download.sh`); clips on the Mac per group: `th` 40, `th-bb` 40, `th-m` 40, `th-ob` 40. The server cannot resume an interrupted download, so a failed clip is downloaded again from the start.

## Results

Failed runs: 0.

| Setting | Clips | Cost, mean curve (as A2) | Cost per clip: mean ± 95 % CI (median) | Worst frame per clip, default: mean ± CI (worst clip) | Worst frame per clip, LTR every 32: mean ± CI (worst clip) |
|---|---|---|---|---|---|
| MLVC-S 540p, `th` | 40 | +9.5 % | +9.0 ± 1.0 % (+8.8 %) | 44.3 ± 1.9 dB (25.9 dB) | 48.0 ± 1.2 dB (37.9 dB) |
| MLVC-S 540p, `th-bb` | 40 | +10.2 % | +10.1 ± 1.3 % (+9.2 %) | 43.2 ± 2.0 dB (30.1 dB) | 47.3 ± 1.3 dB (37.5 dB) |
| MLVC-S 540p, `th-ob` | 40 | +7.9 % | +7.5 ± 0.9 % (+7.5 %) | 45.2 ± 2.0 dB (28.4 dB) | 49.1 ± 1.3 dB (37.8 dB) |
| **MLVC-S 540p, all groups** | 120 | **+9.3 %** | +8.9 ± 0.7 % (+8.4 %) | 44.2 ± 1.1 dB (25.9 dB) | 48.1 ± 0.7 dB (37.5 dB) |
| Full MLVC 360p (B\*), `th` | 40 | +31.9 % | +31.6 ± 3.6 % (+31.7 %) | 39.4 ± 1.8 dB (25.8 dB) | 46.5 ± 1.7 dB (31.4 dB) |
| Full MLVC 360p (B\*), `th-bb` | 40 | +20.4 % | +20.8 ± 2.2 % (+19.2 %) | 41.2 ± 1.5 dB (32.5 dB) | 48.8 ± 1.2 dB (39.7 dB) |
| Full MLVC 360p (B\*), `th-ob` | 40 | +31.7 % | +33.4 ± 2.9 % (+32.5 %) | 41.6 ± 1.4 dB (31.9 dB) | 48.9 ± 1.2 dB (37.7 dB) |
| **Full MLVC 360p (B\*), all groups** | 120 | **+29.5 %** | +28.6 ± 1.9 % (+27.2 %) | 40.7 ± 0.9 dB (25.8 dB) | 48.1 ± 0.8 dB (31.4 dB) |

On the 20 evaluation clips (A2, all 6 mismatched pairs including the CPU) the bound cost +9.7 % on MLVC-S 540p and +36.9 % on B\*, and raised the worst frame from 21.2 to 38.0 dB and from 28.2 to 36.9 dB.

## Conclusion

On 120 clips the bound costs **+9.3 % on MLVC-S 540p** (per clip +8.9 ± 0.7 %) and **+29.5 % on B\*** (per clip +28.6 ± 1.9 %). The worst frame per clip rises from 44.2 ± 1.1 dB to 48.1 ± 0.7 dB on MLVC-S 540p and from 40.7 ± 0.9 dB to 48.1 ± 0.8 dB on B\* (mean ± 95 % CI over the clips).

## Files

| Path | Contents |
|---|---|
| `results/e6.csv`, `results/summary_e6.txt`, `results/summary_e6.md` | Cost and worst frame per setting and clip group, and over all groups |
| `results/e6_per_clip.csv` | Cost and worst frame of every clip |
| `raw_data/r.csv` | Per-run rows (setting × structure × clip × QP × encoder × decoder), experiment 11's columns plus the clip group |
| `raw_data/logs/` | Console logs of the runs and of the download |
| `scripts/` | `e6_download.sh` (the clips), `e6_runner.py` (the runs; imports experiment 11's `drift_runner.py`), `e6_runs.sh` (repeats the runner until every job is done, then the analysis), `e6_tables.py` (the analysis) |

## How to run

After the baseline setup ([`baseline/REPRODUCE.md`](../../baseline/REPRODUCE.md) §1–2), with experiment 11's scripts in `~/Downloads/d/5`:

```bash
mkdir -p ~/Downloads/d/e6 && cp <repo>/algorithm_enhancements/E6_all_vcd_clips/scripts/* ~/Downloads/d/e6/
chmod +x ~/Downloads/d/e6/*.sh && cd ~/Downloads/d/e6
./e6_download.sh                         # the 160 clips, about 3 GB
E6_PORTRAIT=rotate ./e6_runs.sh          # 2,560 jobs, about 9 h; resumable (Ctrl-C at any time)
```
