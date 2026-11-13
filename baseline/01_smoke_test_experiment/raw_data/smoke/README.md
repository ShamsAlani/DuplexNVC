# smoke/: S1 smoke test, MLVC-S 540p

**Purpose:** check that every mode runs, that the networks are placed on the NE, and that paced runs keep up. This is not data for the report's conclusions.
**Script:** `scripts/s`.
**Log:** `../logs/out_s.txt`.
**Settings:** MLVC-S (`dmc61sbr_mini_reglu`, perceptual), 960×540, QP 22, I-frame every 64 frames, NE/NE, 10 s per run. The clip is libmlvc's `VCD_s1_0380a3_960x540`.

| Run | Mode |
|---|---|
| `S_alone-enc`, `S_alone-dec` | Each network alone, unpaced |
| `S_turns` | Taking turns, unpaced |
| `S_duplex` | Sharing the NE, unpaced |
| `S_turns30` | Taking turns, paced at 30 fps |

**Result** (`../../results/01_smoke_test_experiment.csv`): encoder alone 4.86 ms, decoder alone 4.92 ms, T_turns 9.82 ms, T_shared 8.53 ms, S = 1.15. Paced turns had 0 % late frames.
