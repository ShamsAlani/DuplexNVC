# E3 and A4 — Recovering from packet loss, and long-term references chosen from the content

**Questions.**
- **E3:** when the network loses part of a frame, MLVC's decoder cannot decode the following frames (each is predicted from the one before), so the picture freezes. What should the sender do when the receiver reports the loss: **wait** for the next scheduled I-frame, send a **forced I-frame** at once (the usual "picture loss" answer), or send a **recovery frame** predicted from a long-term reference (LTR) the receiver still holds?
- **A4:** MLVC marks LTRs on a fixed schedule (every 16 frames). Is it better to mark a new LTR **once the content has changed and settled again**, so the reference shows the current scene?

Both use libmlvc's per-frame controls checked in [`A0_libmlvc_check`](../A0_libmlvc_check/) (forced I-frame, external LTR marking, recovery from a chosen LTR slot), so the streams play on any MLVC decoder.

## What was run

- **Where:** MacBook Pro 14-inch M4 Pro, macOS 26.6.2, libmlvc `eb5d60a`; encoder and decoder both on the NE, in one program, so there is no drift and every difference comes from the losses and the recovery. Normal use (quality only). 26 Nov 2026, 9:09 – 10:33 pm (+04), 1.4 h.
- **Program:** `scripts/e3a4.cpp`, built against libmlvc as baseline experiment 01's program is. Each frame is encoded, passes through a lossy channel and is decoded; the receiver's loss reports reach the sender **3 frames later** (a 100 ms round trip at 30 fps). The receiver shows the last frame it decoded while it cannot decode (freeze); libmlvc refuses a frame whose reference it does not hold, so a loss breaks the chain until a recovery frame or an I-frame arrives.
- **E3 arms** (what the sender does on a loss report): `wait` (nothing; the picture freezes until the next scheduled I-frame, every 64 frames), `idr` (a forced I-frame), `ltr` (a recovery frame from the newest LTR the receiver is known to hold, including the last I-frame, which libmlvc keeps in slot 0; an I-frame only if it holds none).
- **A4 marking** (external LTR mode, slots 1–3 in turn): `fixed` (the frame after each I-frame, then every 16 frames, MLVC's schedule) or `adaptive` (the frame after each I-frame, then only once the content has changed, mean absolute luma difference to the newest reference above 6, and settled again, frame-to-frame difference below max(2, 1.5 × its median over the last 64 frames) for 8 frames).
- **Loss patterns**, identical for every arm and marking of a run (frame 0 is never lost): `none`; `p1` and `p5` (each 1,200-byte packet lost with probability 1 % or 5 %; a frame is lost if any of its packets is); `burst` (a burst starts with probability 0.6 % per frame and loses 3–8 frames in a row).
- **Content and settings:** the 20 VCD evaluation clips (talking heads, as experiments 10 and 11) and 8 of the 11 multi-person call clips of Step 8 and A3 (`ce4peo`, `cejohn`, `cekris`, `px2ent`, `px4ppl`, `px5ppl`, `px7ppl`, `pxentr`; the inputs of `pxcrwd`, `pxdown` and `pxleav` were missing on the Mac, so they were skipped); 300 frames each; B\* (full MLVC 360p) and MLVC-S 540p; QP 24 and 32. **112 runs** (clip × setting × QP), each trying all **14 combinations** of loss pattern × arm × marking on the same frames: 1,568 combinations.
- **Measures:** bitrate; PSNR-Y of the frame **shown** against the current source frame (a frozen frame counts with its stale picture); frames frozen; freeze events and lengths; number and size of I-frames and recovery frames. Arms are compared **pair by pair** over clip × QP (mean difference with a 95 % confidence interval).
- **Check before the runs:** the program verifies, on every frame, that a recovery frame is coded from exactly the LTR it asked for and that every frame the receiver accepts decodes; **0 structure or decode errors** in all 1,568 combinations.
- **Repeated run:** the first start (8:34 pm) stopped at that check: the program compared reference indices counted from the start of the clip, while libmlvc counts them from the last I-frame (A0). The comparison was corrected and the runs started at 9:09 pm; nothing had been measured before.

## Results

**E3: the three answers to a loss** (fixed marking; mean over clips and QPs; kbps with no loss for comparison):

| Setting, clips | Loss | No loss | Wait for the I-frame | Forced I-frame | Recovery from an LTR |
|---|---|---|---|---|---|
| B\*, VCD | 1 % packets | 150 kbps, 37.71 dB | 150 kbps, 34.17 dB, **24.3 % frozen** | 190 kbps, 37.44 dB, 3.4 % frozen | **165 kbps, 37.49 dB, 3.2 % frozen** |
| B\*, VCD | 5 % packets | | 150 kbps, 26.44 dB, **77.4 % frozen** | 445 kbps, 35.86 dB, 19.4 % frozen | **256 kbps, 36.42 dB, 16.8 % frozen** |
| B\*, VCD | bursts | | 150 kbps, 34.28 dB, 18.6 % frozen | 182 kbps, 37.36 dB, 3.6 % frozen | **164 kbps, 37.39 dB, 4.1 % frozen** |
| MLVC-S 540p, VCD | 1 % packets | 293 kbps, 38.31 dB | 293 kbps, 33.38 dB, **31.8 % frozen** | 374 kbps, 37.89 dB, 4.5 % frozen | **332 kbps, 37.97 dB, 4.2 % frozen** |
| MLVC-S 540p, VCD | 5 % packets | | 293 kbps, 25.19 dB, **81.8 % frozen** | 831 kbps, 35.34 dB, 25.3 % frozen | **526 kbps, 36.21 dB, 23.3 % frozen** |
| MLVC-S 540p, VCD | bursts | | 293 kbps, 34.75 dB, 18.6 % frozen | 338 kbps, 37.94 dB, 3.6 % frozen | **313 kbps, 37.96 dB, 4.1 % frozen** |

The call clips give the same picture (`results/summary.txt`, `results/table.csv`).

**Paired differences, all 28 clips** (56 clip × QP pairs; mean ± 95 % CI):

| Setting | Loss | LTR recovery − wait | LTR recovery − forced I-frame |
|---|---|---|---|
| B\* | 1 % | **+3.46 ± 0.84 dB**, 65 fewer frozen frames per 300 | +0.02 ± 0.06 dB, **−19 ± 12 kbps** |
| B\* | 5 % | **+10.00 ± 1.02 dB**, 178 fewer frozen | **+0.55 ± 0.18 dB, −171 ± 52 kbps** |
| B\* | bursts | **+2.68 ± 0.72 dB**, 40 fewer frozen | +0.02 ± 0.01 dB, **−17 ± 5 kbps**, 1.5 ± 0.4 more frozen |
| MLVC-S 540p | 1 % | **+4.79 ± 0.98 dB**, 87 fewer frozen | +0.03 ± 0.06 dB, **−33 ± 15 kbps** |
| MLVC-S 540p | 5 % | **+10.96 ± 1.07 dB**, 173 fewer frozen | **+0.85 ± 0.22 dB, −283 ± 73 kbps** |
| MLVC-S 540p | bursts | **+2.77 ± 0.74 dB**, 40 fewer frozen | +0.02 ± 0.01 dB, **−24 ± 6 kbps**, 1.5 ± 0.4 more frozen |

**A4: adaptive against fixed marking** (LTR recovery; mean ± 95 % CI over clip × QP):

| Setting | Clips | 1 % packets | 5 % packets | Bursts |
|---|---|---|---|---|
| B\* | VCD | −0.005 dB, +6 kbps | −0.07 ± 0.05 dB, +13 kbps | −0.006 dB, +5 kbps |
| B\* | call | +0.003 dB, −2 kbps | +0.07 ± 0.05 dB, −5 kbps | −0.003 dB, +1 kbps |
| MLVC-S 540p | VCD | −0.009 dB, +12 kbps | −0.14 ± 0.12 dB, +27 kbps | −0.003 dB, +8 kbps |
| MLVC-S 540p | call | +0.02 dB, −6 kbps | +0.20 ± 0.18 dB, −33 kbps | −0.005 dB, +1 kbps |

## Conclusion

1. **Waiting for the next I-frame is not an option for MLVC.** One lost frame freezes the picture until the next I-frame, up to 2 seconds later: with 1 % packet loss a quarter to a third of the frames are frozen, with 5 % three quarters. Answering the loss report gains 3–5 dB of shown quality at 1 % loss and 10–11 dB at 5 %.
2. **Recovery from an LTR is the right answer: the quality of a forced I-frame for far fewer bits.** A recovery frame costs about a quarter of an I-frame (1.1–3.9 kB against 6–11 kB), so the extra bitrate caused by losses falls to 36–53 % of a forced I-frame's (paired over all clips; at 5 % loss on VCD: +70 % instead of +196 % on B\*, +79 % instead of +184 % on MLVC-S 540p), and at 5 % loss the picture is also 0.5–0.9 dB better: a large I-frame spans more packets, so it is lost more often itself (9.9 % of frames lost against 7.2 % on B\*, VCD). In bursts it freezes 1.5 frames per 300 longer than a forced I-frame, for 17–24 kbps less.
3. **A4 does not help: MLVC's fixed schedule stays.** Marking LTRs when the content settles changes the shown quality by less than 0.2 dB in every case, costs a few kbps more on the VCD clips and saves a few on the call clips; no difference is large enough to matter. With an LTR every 16 frames, the newest reference is always recent enough.
4. **For the controller:** the same mechanism serves two purposes. LTR recovery bounds drift for a decoder on another processor ([`A2_drift_bounds`](../A2_drift_bounds/)) and answers every loss report; marking stays on MLVC's schedule (every 16 frames), and a forced I-frame is sent only when the receiver holds no LTR.

## Files

| Path | Contents |
|---|---|
| `results/summary.txt` | Both tables as printed by `e3a4_tables.py` (per setting, clip group, loss pattern, arm and marking; paired differences) |
| `results/table.csv` | Mean per setting × clip group × loss pattern × arm × marking: kbps, shown PSNR-Y, frames lost and frozen, freeze events and lengths, I-frames and recovery frames per run and their sizes |
| `results/paired.csv` | Paired differences between arms and between markings (mean and 95 % CI) |
| `raw_data/runs/<setting>/<clip>_qp<q>_sum.csv` | One row per combination of each run |
| `raw_data/runs/<setting>/<clip>_qp<q>.csv.gz` | One row per frame and combination: lost, decoded, shown frame, frame type and reference, bytes, LTR marked, request sent, shown and decoded PSNR-Y, frame difference |
| `raw_data/logs/` | Console log of the runs and the check |
| `scripts/` | `e3a4.cpp` (the program), `e3a4_runner.py` (all runs, resumable), `e3a4_tables.py` (the analysis; called `e3a4ana.py` during the runs), `e3a4_runs.sh` (build, check, runs, analysis) |

## How to run

After the baseline setup ([`baseline/REPRODUCE.md`](../../baseline/REPRODUCE.md) §1–2) and A3 (whose script prepares the call clips in `phase2/a3/m1080/`):

```bash
mkdir -p ~/Downloads/d/e3 && cp <repo>/algorithm_enhancements/E3_A4_loss_recovery/scripts/* ~/Downloads/d/e3/
chmod +x ~/Downloads/d/e3/*.sh && cd ~/Downloads/d/e3 && ./e3a4_runs.sh     # about 1.5 h; resumable
```
