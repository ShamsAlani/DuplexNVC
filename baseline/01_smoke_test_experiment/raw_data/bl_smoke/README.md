# bl_smoke/: S2 smoke test, full MLVC 360p

**Purpose:** check the baseline pipeline before the long runs.
**Script:** `scripts/t`.
**Log:** `../logs/out_t.txt`.
**Settings:** B\* settings (full MLVC `psnr_v1`, 640×360, QP 26, I-frame every 64 frames, NE/NE), 10 s per run.

| Run | Mode |
|---|---|
| `S_alone-enc`, `S_alone-dec` | Each network alone, unpaced |
| `S_turns`, `S_duplex` | Taking turns / sharing, unpaced |
| `S_turns30`, `S_duplex30` | Paced at 30 fps |
| `S_cli` | `mlvc benchmark` with 1 encoder + 1 decoder (`S_cli.log`) |

**Result:**
- encoder alone 5.90 ms, decoder alone 5.96 ms, T_turns 11.86 ms, T_shared 10.68 ms, S = 1.11;
- paced duplex: 0.37 % late on send (1 frame of about 300, a start-up effect that never recurred in the 60 s runs), 0 % on receive;
- paced turns: 0 % late.
