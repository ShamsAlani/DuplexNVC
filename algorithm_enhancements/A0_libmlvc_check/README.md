# A0 — Does libmlvc do exactly what our enhancements ask of it?

**Question.** A1, A3 and A4 (and E3, recovery from packet loss) steer MLVC frame by frame through three controls of libmlvc's encoder: a **forced key frame** (`EncodeParams.forceIdr`), **external long-term references** (`LtrMode::EXTERNAL`, `MarkNextFrameAsLtr(slot)` to mark a frame, `EncodeParams.useLtrSlotIdx` to predict a frame from a marked one), and a **QP for each frame** (`EncodeParams.qp`). Before results are built on them: does each control do what is asked, on exactly the frames it is asked for, and does the decoder see the same stream structure as the encoder, on the NE and on the GPU?

## What was run

**25 Nov 2026, 4:17–4:21 am (+04)**, MacBook Pro 14-inch M4 Pro, macOS 26.6.2 (25G83), libmlvc `eb5d60a`, normal use (correctness only, nothing timed).

- **Program:** `a0.cpp`, a small C++ program on libmlvc built from libmlvc's own `minimal-fetchcontent` example. B\*'s model and settings (full MLVC, 640×360, QP 26, encoder on the NE), the first 120 frames of the baseline camera clip.
- **Three tests:**

| Test | Structure asked for | What must come out |
|---|---|---|
| T1, forced key frames | I-frame period 64; `forceIdr` on frames 20, 45 and 100 | I-frames at 0, 20, 45 and 100 and nowhere else (the 64-frame period restarts from a forced I-frame, so frame 64 is a P-frame) |
| T2, external LTRs | No periodic I-frame after frame 0; mark frame 10 (slot 1), 40 (slot 2) and 95 (slot 2 again); recover from slot 1 at 30 and 90, from slot 2 at 70, 110 and 115 | Each recovery frame predicts from the marked frame and its prediction chain restarts from it; every other frame is a P-frame from the frame before |
| T3, per-frame QP | I-frame period 64; QP 18, 22, 26, 30, 34, 38, 42 in turn on every frame | Every frame header carries the QP asked for |

- **Checks on every frame of every test:** the frame type, reference frame and prediction-chain length the encoder reports (`FrameInfo`) match what was asked; the stream decodes; the decoder reports the same type, reference, chain length and QP as the encoder; two decodes on the NE are bit-identical; the decode on the GPU is compared with the NE's (PSNR).
- **Expected structure:** worked out by the program from what is asked, following libmlvc's rules; a test passes only if all 120 frames match.

**First run (4:17 am, repeated unchanged at 4:19 am): T1 and T3 passed, T2 failed on one frame.** The first T2 plan marked slot 2 only once (frame 40) and asked for it again at frame 110, after the recovery at 90 had gone back to slot 1 (frame 10). Frame 110 came out as a P-frame from frame 109, not a recovery frame. The decoder agreed with the encoder on every frame, so the stream was consistent; our expectation was wrong. **libmlvc's loss-recovery rule:** recovering from an older LTR makes every LTR newer than it invalid (the decoder that asked for the recovery may never have received them), so slot 2 (frame 40) no longer existed at frame 110, and libmlvc ignores a hint to an invalid slot. *Fix:* the expected structure in `a0.cpp` follows this rule, and the T2 plan marks slot 2 again at frame 95 so that the recoveries at 110 and 115 test a re-marked slot.

**Run after the fix (4:20 am), the one reported below:** all three tests pass. Each run took about a minute.

## How to run

The scripts live in `~/Downloads/d/a0/` (they read `../settings.sh`). Any Mac state (nothing is timed), but not during an energy run.

```bash
mkdir -p ~/Downloads/d/a0
cp <repo>/algorithm_enhancements/A0_libmlvc_check/scripts/* ~/Downloads/d/a0/
chmod +x ~/Downloads/d/a0/a0_runs.sh
cd ~/Downloads/d/a0 && ./a0_runs.sh
```

| Script | What | Time |
|---|---|---|
| `scripts/a0_runs.sh` | Builds the A0 program in `$WORK/harness_a0` (only when `a0.cpp` changed), runs the three tests, prints the summary | ≈ 1 min (+ 3 min for the first build) |
| `scripts/a0.cpp` | The program: the three tests, the expected structure, the frame-by-frame comparison | — |

Output: `~/Downloads/duplexnvc-baseline/phase2/a0/`; console log `out_a0_runs.txt`.

## Files

| Path | Contents |
|---|---|
| `raw_data/t1_forced_key_frames.csv`, `t2_external_ltr.csv`, `t3_per_frame_qp.csv` | One row per frame: what was asked, the encoder's type, reference, chain length, QP and size, the decoder's type, reference, chain length and QP, whether they match, whether the two NE decodes are identical, PSNR-Y of the NE and GPU decodes, and GPU vs NE in dB |
| `raw_data/logs/a0.log` | The program's log of the reported run (every frame that was asked for something, with the expected structure) |
| `raw_data/logs/build.log` | Build of the A0 program |
| `raw_data/logs/out_all.txt` | Console log of all three runs (recorded under the script's old name, `all`) |
| `results/summary.txt` | One line per test with every check |

## Results

| Test | I-frames | Recovery frames | Structure as asked | Decoded | Decoder = encoder | NE decode deterministic | Header QP = asked | Result |
|---|---|---|---|---|---|---|---|---|
| T1, forced key frames | 4 (0, 20, 45, 100) | 0 | 120/120 | 120/120 | 120/120 | 120/120 | 120/120 | **PASS** |
| T2, external LTRs | 1 (0) | 5 (30, 70, 90, 110, 115) | 120/120 | 120/120 | 120/120 | 120/120 | 120/120 | **PASS** |
| T3, per-frame QP | 2 (0, 64) | 0 | 120/120 | 120/120 | 120/120 | 120/120 | 120/120 | **PASS** |

- **T1:** each forced frame is an I-frame of 3.9–4.0 KB (a P-frame: median 0.2 KB), and the period restarts from it.
- **T2:** every recovery frame predicts from its marked frame: 30 and 90 from frame 10, 70 from frame 40, 110 and 115 from frame 95. The prediction chain restarts from the marked frame (chain 11 at frame 30, against 30 frames since the I-frame). A recovery frame costs 0.2–1.1 KB, at most 28 % of an I-frame (3.9 KB).
- **T3:** the QP changes the frame size as expected (P-frames: 1.3 KB at QP 18, 0.13 KB at QP 30, 0.04 KB at QP 42) and every header carries the QP asked for.
- **GPU vs NE:** the GPU decodes every stream without failure but not identically to the NE (median 51–55 dB between the two pictures, lowest frame 44 dB), the processor mismatch measured in baseline experiments 04 and 11.

## Conclusion

1. **All three controls do exactly what is asked, frame by frame, and the decoder sees the same structure on the NE and on the GPU.** A1 (per-frame QP), A3 (forced key frames) and A4 and E3 (external LTRs) can rely on them.
2. **One rule to design around:** recovering from an older LTR invalidates every newer LTR. A4's marking policy and E3's recovery must re-mark a slot after recovering past it; a hint to an invalidated slot gives an ordinary P-frame, not an error.
3. A recovery frame costs at most 28 % of an I-frame here, the saving A2 and E3 build on.
