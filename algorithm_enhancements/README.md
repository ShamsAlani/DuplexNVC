# Algorithm Enhancements (C5): changing how MLVC codes the video

The [`baseline/`](../baseline/) measures MLVC as Microsoft released it: which setting runs, where, how fast, at what energy and quality. This folder holds our **changes to MLVC's coding algorithm**: its reference structure (which frames later frames are predicted from), when it restarts from a key frame, and how many bits each frame gets. MLVC fixes all of these as content-blind defaults (an I-frame every 64 frames, LTRs on a fixed schedule or not at all, one QP for every frame) and its paper never compares them with alternatives. Our Algorithm Enhancements make them depend on the content, on the frame's role and on the hardware the other side decodes on.

They need no retraining and no change to the decoder: every control is already in MLVC's bitstream (a QP in each frame header, a key-frame flag, LTR marking and recovery), so any MLVC decoder plays our streams. This is the codec-level half of our algorithm change; the network-level half (fine-tuning MLVC itself) is in [`lab_gpu_runs/`](../lab_gpu_runs/).

Every enhancement is measured on the same MacBook Pro (M4 Pro) as the baseline, with the baseline's clips, metrics and analysis, against the baseline's own setting as control.

## The enhancements

| Folder | Enhancement | Question | Status | Answer so far |
|---|---|---|---|---|
| [`A0_libmlvc_check/`](A0_libmlvc_check/) | **A0:** libmlvc check | Do forced key frames, external LTR marking and recovery, and a per-frame QP do exactly what is asked, frame by frame? | Done (25 Nov) | **Yes, all three, on every frame**; the decoder sees the same structure on the NE and the GPU. One rule: recovering from an older LTR invalidates every newer one, so a slot must be re-marked after it |
| [`A1_keyframe_qp/`](A1_keyframe_qp/) | **A1:** more bits for key frames and LTR frames, **with E4** (A1 inside A2's bound, A1 on MLVC-S) | Does a lower QP on the frames every later frame depends on save bits? | Done (22 and 24 Nov) | **I-frames −8 saves 1.2 % (B\*) to 2.6 % (MLVC-S 540p)** on coded PSNR and ≈ 6 % on face LPIPS; a lower QP on LTR frames never helps; inside A2's bound the I-frame offset wins back a fifth of its cost |
| [`A2_drift_bounds/`](A2_drift_bounds/) | **A2:** bounding drift for a decoder on another processor | Shorter I-frame period or LTR recovery: which bound limits drift for the fewest bits? | Done for the 30 fps settings (20–22 Nov); the others on later nights | **LTR recovery every 32 frames**: the same worst frame (37–39 dB) as an I-frame every 32 for a quarter of the bits on MLVC-S (+9.6 %) |
| [`A3_forced_keyframe/`](A3_forced_keyframe/) | **A3:** a fresh key frame when people join or leave | Does a key frame forced at a content change save bits or improve the picture? | Done (24 Nov) | **No**: a forced I-frame costs 11–15 P-frames and the picture after the event is no better (+1.6 % with a perfect trigger, +29 % with frame difference) |
| A4 | Content-adaptive long-term references | Mark a new LTR once the content settles, instead of on a schedule? | Next (A0 done) | — |
| E3 | Recovery from packet loss | From the latest LTR, or wait for the next I-frame? | Next (A0 done) | — |
| E6 | A1 and A2 on all 160 VCD clips | Are the gains real (95 % confidence intervals)? | Planned | — |

## What this means for the controller so far

- **A2 is the central enhancement:** a decoder on another processor (or another laptop) needs a bound, and LTR recovery every 32 frames is the cheapest one on MLVC-S. At the start of a call the two laptops exchange their chip and decoder placement, and each sender uses the bound for that pairing (tested in the real calls, E2).
- **A1 is a free addition:** −8 on every I-frame, also inside the bound.
- **A3 is not used to save bits:** scene events change the setting (model, resolution, placement), and a key frame is forced only where the stream restarts anyway.

## How to run

After the baseline setup ([`baseline/REPRODUCE.md`](../baseline/REPRODUCE.md) §1–2, which builds the tools and the evaluation clips that every enhancement reuses):

```bash
mkdir -p ~/Downloads/d/{a0,a1,a3/data}
cp <repo>/algorithm_enhancements/A0_libmlvc_check/scripts/* ~/Downloads/d/a0/
cp <repo>/algorithm_enhancements/A1_keyframe_qp/scripts/* ~/Downloads/d/a1/
cp <repo>/algorithm_enhancements/A3_forced_keyframe/scripts/* ~/Downloads/d/a3/
cp <repo>/algorithm_enhancements/A3_forced_keyframe/raw_data/data/* ~/Downloads/d/a3/data/
chmod +x ~/Downloads/d/{a0,a1,a3}/*.sh
cd ~/Downloads/d/a0 && ./a0_runs.sh       # A0 (1 min; 3 min more for the first build)
cd ../a1 && ./a1_round1_runs.sh              # A1 round 1 (50 min)
cd ../a3 && ./a3_runs.sh                     # A3 (30 min; builds the program with --force-idr that A1 round 2 needs)
cd ../a1 && ./a1_round2_runs.sh              # A1 round 2 and E4 (75 min)
# A2: baseline experiment 11's scripts with PHASE=a2 (cd ~/Downloads/d/5 && PHASE=a2 ./drift_runs.sh)
```

All of these measure quality or correctness only (no timing), so the Mac can be in normal use; charger in, lid open. Every script is resumable.

## Script names

The scripts had short names during the runs; they now have descriptive ones (only the names changed, with the calls between scripts and the console-log names). Logs in `raw_data/` keep the old names.

| Folder | Old name | New name |
|---|---|---|
| A1 | `all` | `a1_round1_runs.sh` |
| A1 | `allb` | `a1_round2_runs.sh` |
| A3 | `all` | `a3_runs.sh` |
| A0 | `all` | `a0_runs.sh` |
