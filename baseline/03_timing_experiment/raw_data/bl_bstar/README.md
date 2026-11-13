# bl_bstar/: the baseline B* (E1, E2, E3, E4, B*, E5)

**Script:** `scripts/x` (all timed runs, in the order below, 65 min, quiet Mac), then `scripts/c` (E5) and `scripts/y` (summary).
**Logs:** `../logs/out_x4.txt`, `out_y.txt`; the E5 log `out_c.txt` is in `../../../04_correctness_experiment/raw_data/logs/`.
**Settings:** full MLVC `dmc61sbr_reglu` with `psnr_v1` weights, 640×360, QP 26, I-frame every 64 frames, NE/NE.
**Streams:**
- camera: clips 0380a3 + 6587ae;
- incoming: clips 6c9c96 + 9c02f6, prepared at QP 26 (PSNR-Y 34.98 dB).

Each stream is 600 frames, looped.

| Runs | Experiment | Mode | Paced | Length |
|---|---|---|---|---|
| `T_alone-enc_r1..r5`, `T_alone-dec_r1..r5` | **E1** each network alone | alone-enc / alone-dec | No | 60 s each |
| `T_turns_r1..r5` | **E3** taking turns | turns | No | 60 s |
| `T_duplex_r1..r5` | **E4** sharing the NE | duplex | No | 60 s |
| `T_duplex30_r1..r5` | **B\*** the baseline | duplex | 30 fps | 60 s (1,802 frames per direction) |
| `T_turns30_r1..r3` | Reference: taking turns in real time | turns | 30 fps | 60 s |
| `T_cli_r1..r3` (+ `.log`) | **E2** libmlvc CLI cross-check: `mlvc benchmark --num-encoders 1 --num-decoders 1 --qp 26 --iframe-period 64 --duration-seconds 60` | — | No | 60 s |
| `T_duplex30_r1/dec_{npu,npu2,gpu,cpu}.log` | **E5** decodes of the B\* stream on NE (twice), GPU and CPU | — | — | 1,802 frames |

**Order:** 5 interleaved rounds (turns, alone-enc, alone-dec, duplex), then 5 paced duplex runs, 3 paced turns runs and 3 CLI runs, with 60 s of rest after each.

**Results:**
- `../../results/03` (E1, E3, E4): t_enc 5.86 ms, t_dec 5.94 ms, T_turns 11.81 ms, T_shared 10.68 ms, **S = 1.11** (ideal 1.99), κ 1.82 / 1.80.
- `../../results/04` (E2): 10.7 ms and 93.6 fps per stream, identical to our program.
- `../../results/05` (**B\***): 30.01 fps, **0 % late or dropped**, mean call 12.44 / 13.32 ms, **p99 due-to-done 29.27 / 28.93 ms**, 120.5 / 287.1 kbps.
- `../../results/05b` (paced turns): 0 % late, p99 21.30 / 31.06 ms.
- `04_correctness_experiment/results/07` (E5): no failures; NE decoding bit-identical across two runs; drift vs GPU mean 52.1 dB (worst 38.5 dB), vs CPU 48.8 dB (worst 39.5 dB).
