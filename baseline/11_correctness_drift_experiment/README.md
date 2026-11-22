# 11 — Correctness and drift experiment: every encoder → decoder pair, and two ways to bound drift (Step 5 + A2)

**Question.**
1. **Correctness (H4).** When the encoder runs on one processor (NE, GPU or CPU) and the decoder on another, does decoding fail, is it deterministic, how far does the decoder drift from the encoder's own reconstruction, and what does the drift cost in bitrate? H4 holds if every pair stays within 1 BD-rate point of NE → NE.
2. **Drift bounds (A2).** Drift grows until the next I-frame. Two ways to stop it sooner: (a) a shorter I-frame period (32 or 16 instead of 64), or (b) libmlvc's *LTR proactive recovery*, which predicts a frame from an older long-term reference (LTR) every 32 or 16 frames. Which limits the worst drift for fewer bits?
3. **Content.** Does drift behave the same on moving multi-person content as on the single-person VCD clips?

Experiment 04 tested decoding correctness on one clip at 360p; experiment 10 found that a GPU encoder with an NE decoder costs about 4 % in bitrate. This experiment covers all 9 pairs, all 7 settings, the 20 evaluation clips and 4 QPs.

## What was run

MacBook Pro 14-inch M4 Pro, 24 GB, macOS 26.6.2 (25G83), libmlvc `eb5d60a`, normal use (quality only; nothing is timed).

- **Pairs:** each bitstream is encoded on the NE, the GPU and the CPU (three encodes in parallel, one Core ML cache per processor), and each bitstream is decoded on all three → 9 encoder → decoder pairs per job. Encode: `mlvc encode`; decode: `mlvc decode`.
- **Settings and content:** all 7 settings (full MLVC 360/540/720/1080p, MLVC-S 540/720/1080p) on the 20 evaluation clips (Lanczos from the 1080p MP4, 300 frames, as experiment 10) at QP 16/24/32/40.
- **Structures:** the default structure (an I-frame every 64 frames, as B\*) for all 7 settings; the four A2 bounds — I-frame every 32 (`i32`) and every 16 (`i16`), LTR recovery every 32 (`l32`: LTR period 16, recovery period 2) and every 16 (`l16`: LTR period 8, recovery period 2, LTR start index 0) — for full MLVC 360p, the two 30 fps settings MLVC-S 540p (NE–NE) and MLVC-S 720p (GPU–NE), and full MLVC 540p.
- **Measured per pair:** decode failures and short decodes; PSNR-Y and PSNR-YUV against the encoder input; **drift** = PSNR-Y of the decode against the decode on the encoder's own processor, per frame, also by position after the I-frame; **determinism** = the same bitstream decoded twice on the same processor (main structure, first clip, 4 QPs); BD-rate (coded PSNR-Y, PCHIP) of each pair against NE → NE. The NE and GPU bitstreams of the default structure are compared byte for byte with experiment 10's.
- **Multi-person check:** the default structure for full MLVC 360p (B\*), MLVC-S 540p and MLVC-S 720p on the 11 multi-person clips of Step 8 (`controller_data/`: 3 HEVC Class E clips at 720p, 8 Pexels clips at 1080p, 148–300 frames, people entering and leaving).

**When:** main structure and A2 for full MLVC 360p / MLVC-S 720p 20 Nov 00:31–23:00 (1,120 jobs); A2 for the 30 fps settings 21 Nov 22:40 – 22 Nov 08:01 (960 jobs); multi-person 22 Nov 18:52–20:14 (132 jobs). Every job has 9 pairs: 2,212 jobs, 19,908 encoder → decoder pairs.

**The default encoder configuration differs by model** (printed by `mlvc encode`, `raw_data/cfg/`): full MLVC uses **no LTRs** (LTR period 0); MLVC-S marks an LTR every 16 frames from frame 8 with recovery every 64 frames, which the I-frame every 64 frames always comes first. So in the default structure no frame is ever predicted from an LTR, for any setting. The first attempt of `l16` on MLVC-S stopped because libmlvc requires the LTR start index (MLVC-S default 8) to be smaller than the LTR period (8): `l16` therefore sets the start index to 0, which is also full MLVC's default (see the log).

## How to run

The scripts live in `~/Downloads/d/5/` (they read `../v`). Normal Mac use is fine; charger in, lid open; resumable.

| Script | What | Time |
|---|---|---|
| `scripts/all` | Pre-flight, then `c.py` (up to 3 passes), then `ana.py`. `PHASE=main\|a2\|all`, `ONLY="<settings>"` | main ≈ 17 h for all 7 settings; A2 ≈ 10 h for the three 30 fps settings, ≈ 43 h for the other three |
| `scripts/c.py` | One job = setting × structure × clip × QP: 3 encodes, 9 decodes, per-frame PSNR and drift | — |
| `scripts/ana.py` | Coverage, determinism, drift by position, BD-rate per pair, A2 cost vs drift, figures (`S5OUT=<folder>` analyses another output folder) | 1 min |
| `scripts/an` | `ana.py` on whatever is finished | 1 min |
| `scripts/mp`, `scripts/m.py` | Multi-person check (finds the Step 8 masters under `~/Downloads`) | 1.4 h |

Output: `~/Downloads/duplexnvc-baseline/phase2/5/` and `phase2/5m/` (multi-person).

## Files

| Path | Contents |
|---|---|
| `raw_data/r.csv` | One row per job and pair (VCD clips): sizes, failures, PSNR-Y/YUV, drift (mean, worst, by position), determinism, same-as-experiment-10 flags |
| `raw_data/r_multi_person.csv` | The same for the multi-person clips |
| `raw_data/cfg/` | Encoder configuration printed by `mlvc encode` per setting and structure |
| `raw_data/logs/` | Console logs (`out_all.txt` includes the `l16` start-index failure and its fix; `out_mp.txt`) |
| `results/` | `coverage`, `det`, `drift`, `bd`, `a2` (CSV), `fig_drift`, `fig_a2`, `summary.txt`; `multi_person/` the same for the multi-person clips. In the figures, "main (I 64, LTR rec. 64)" means the default structure |

The per-frame files (`frames/`, one per job and pair) and the bitstreams stay on the measurement laptop.

## Results

**Coverage and determinism.** 2,212 of 2,212 jobs, **no decode failure, no short decode**. Decoding is **deterministic** on every processor (4 of 4 repeats bit-identical for every pair and setting). The NE and GPU bitstreams of the default structure are byte-identical to experiment 10's (80 of 80 per setting).

**No two different processors decode alike.** On every mismatched pair, **0 % of frames are bit-identical** to the decode on the encoder's processor. Drift grows through each 64-frame group (mean PSNR-Y of the decode against the encoder's processor, VCD clips):

| Pair (example: MLVC-S 720p) | worst frame | mean | frame 0 | 1–15 | 16–31 | 32–47 | 48–63 |
|---|---|---|---|---|---|---|---|
| NE → GPU | 29.4 | 51.6 | 58.8 | 56.5 | 53.8 | 51.2 | 48.0 |
| NE → CPU | 21.3 | 46.2 | 52.6 | 51.9 | 50.1 | 46.4 | 41.9 |
| GPU → NE | 34.2 | 51.9 | 58.8 | 56.5 | 53.8 | 51.4 | 48.6 |
| CPU → GPU | 34.3 | 50.5 | 52.8 | 52.6 | 51.6 | 50.2 | 48.2 |

All settings: worst frames 21–38 dB; means 46–52 dB (`results/drift.csv`).

**BD-rate (coded PSNR-Y) of each pair against NE → NE, default structure (H4: |change| < 1 point):**

| Setting | NE→GPU | NE→CPU | GPU→NE | GPU→GPU | GPU→CPU | CPU→NE | CPU→GPU | CPU→CPU |
|---|---|---|---|---|---|---|---|---|
| Full MLVC 360p (B\*) | +3.74 | +7.90 | +3.64 | −0.31 | +3.72 | +7.12 | +3.04 | +2.47 |
| MLVC-S 540p | +2.95 | +8.19 | +3.08 | −0.07 | +5.15 | +6.66 | +2.95 | +1.96 |
| Full MLVC 540p | +4.95 | +10.91 | +4.41 | −0.39 | +5.13 | +8.87 | +3.60 | +3.45 |
| MLVC-S 720p | +4.27 | +12.36 | +3.98 | −0.15 | +7.69 | +8.85 | +3.97 | +2.59 |
| Full MLVC 720p | +6.15 | +14.40 | +5.07 | −0.59 | +6.61 | +10.86 | +4.35 | +4.58 |
| MLVC-S 1080p | +5.60 | +17.55 | +5.46 | −0.14 | +9.47 | +12.14 | +4.86 | +3.69 |
| Full MLVC 1080p | +7.50 | +19.63 | +6.37 | −0.56 | +9.30 | +14.28 | +5.17 | +6.39 |

**H4 fails for every mismatched pair of every setting.** GPU → GPU stays within 0.6 points; CPU → CPU costs 2–6 % because the CPU encoder itself codes slightly less efficiently.

**A2: drift bounds** (cost = BD-rate of NE → NE against the default structure; worst frame over the 6 mismatched pairs):

| Setting | Default | LTR recovery every 32 | I-frame every 32 | LTR recovery every 16 | I-frame every 16 |
|---|---|---|---|---|---|
| Full MLVC 360p (B\*) | 0 % → 28.2 dB | +36.9 % → 36.9 dB | +51.4 % → 37.4 dB | +78.8 % → 40.8 dB | +149.8 % → 42.0 dB |
| MLVC-S 540p | 0 % → 21.2 dB | **+9.7 % → 38.0 dB** | +44.1 % → 38.0 dB | +70.7 % → 45.3 dB | +130.8 % → 44.2 dB |
| MLVC-S 720p | 0 % → 21.3 dB | **+9.5 % → 37.0 dB** | +39.1 % → 37.0 dB | +62.0 % → 45.5 dB | +114.7 % → 43.6 dB |
| Full MLVC 540p | 0 % → 31.6 dB | +33.3 % → 39.3 dB | +46.8 % → 39.3 dB | +71.6 % → 42.2 dB | +135.0 % → 44.4 dB |

A2 for full MLVC 720p, MLVC-S 1080p and full MLVC 1080p is running on later nights; this folder will be updated when it finishes.

**Multi-person clips** (11 clips, default structure; `results/multi_person/`): deterministic and without failures as on VCD, but drift is larger. Mean drift is 2–5 dB lower (worse) from frame 16 on, and the mismatched pairs cost about **twice the bitrate**:

| Setting | NE→GPU | NE→CPU | GPU→NE | GPU→CPU | CPU→NE | CPU→GPU | CPU→CPU |
|---|---|---|---|---|---|---|---|
| Full MLVC 360p (B\*), VCD → multi-person | +3.7 → **+8.9** | +7.9 → **+15.9** | +3.6 → +9.2 | +3.7 → +5.9 | +7.1 → +15.8 | +3.0 → +6.4 | +2.5 → +2.1 |
| MLVC-S 540p | +3.0 → +8.7 | +8.2 → +16.9 | +3.1 → +8.9 | +5.2 → +8.6 | +6.7 → +15.8 | +3.0 → +6.9 | +2.0 → +1.6 |
| MLVC-S 720p | +4.3 → +10.0 | +12.4 → +19.7 | +4.0 → +10.3 | +7.7 → +10.3 | +8.9 → +18.5 | +4.0 → +8.2 | +2.6 → +2.0 |

## Conclusion

1. **Decoding is correct and deterministic on every processor, but no two processors agree.** Every mismatched pair drifts from the first P-frame on, and the drift grows until the next I-frame (about 59 dB just after it, 42–49 dB at the end of a 64-frame group on VCD).
2. **H4 fails: running the decoder on a different processor than the encoder always costs bits.** About +3–7 % when GPU and NE are mixed, +7–20 % when the CPU is involved; the cost grows with resolution and model size (full MLVC 1080p worst). The encoder and decoder must run on the same kind of processor, or the codec must bound the drift. A GPU encoder with an NE decoder, the best placement of two 30 fps settings (experiment 09), pays +4.0–4.4 %.
3. **LTR recovery bounds drift as well as an I-frame does, for far fewer bits.** At every 32 frames both raise the worst frame to the same 37–39 dB; LTR recovery costs a quarter of the bits on MLVC-S (+9.6 % against +39–44 %) and about 70 % on full MLVC (+33–37 % against +47–51 %). Every 16 frames, LTR recovery costs about half of an I-frame for a worst frame within 2 dB of it. On MLVC-S, LTR recovery every 32 frames is the cheapest bound measured.
4. **Drift depends on the content.** On moving multi-person clips the same pairs cost about twice the bitrate. A controller that places the decoder away from the encoder should therefore use the content as well as the hardware to decide when a drift bound is needed.
5. **The default structure uses no LTR prediction at all** (full MLVC: no LTRs; MLVC-S: recovery never reached before the next I-frame). The LTR machinery is only used when a bound or a mechanism (A1, A3, A4) switches it on.
