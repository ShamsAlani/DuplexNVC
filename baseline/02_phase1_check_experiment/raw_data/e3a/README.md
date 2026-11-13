# e3a/: E3a, Phase 1 re-check (MLVC-S 540p)

**Purpose:** re-measure the Phase 1 configuration with the new program, which validates the program. It also measures T_turns and S, which Phase 1 had only estimated.
**Scripts:** `scripts/e` (runs), then `scripts/r` (summary).
**Logs:** `../logs/out_e.txt`, `out_r.txt`.
**Settings:** MLVC-S, 960×540, QP 22, I-frame every 64 frames, NE/NE; quiet Mac.

| Runs | Mode | Paced |
|---|---|---|
| `T_alone-enc_r1..r5` | Encoder alone | No (60 s) |
| `T_alone-dec_r1..r5` | Decoder alone | No (60 s) |
| `T_turns_r1..r5` | Taking turns | No (60 s) |
| `T_duplex_r1..r5` | Sharing the NE | No (60 s) |
| `T_turns30_r1..r3` | Taking turns | 30 fps (60 s) |

**Order:** rounds 1–5 are interleaved (turns, alone-enc, alone-dec, duplex), with 60 s of rest after every run.

**Result** (`../../results/02*.csv`):
- t_enc 4.84 ms, t_dec 4.91 ms, T_turns 9.79 ms, switching cost 0.04 ms;
- T_shared 8.53 ms, **S = 1.15**, κ (network) 1.74 / 1.71;
- paced turns: 0 % late, p99 18.9 / 28.2 ms.

All Phase 1 values hold to within 4 %.
