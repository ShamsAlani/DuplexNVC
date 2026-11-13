# 03 — Timing experiment: the core baseline B\* (E1–E4, B\*)

**The baseline B\*:** full MLVC (`dmc61sbr_reglu`, PSNR weights `psnr_v1`, Core ML fp16) at 640×360, encoder **and** decoder on the Neural Engine (NE), full duplex in one process, paced at 30 fps (33.3 ms deadline), QP 26, an I-frame every 64 frames. Camera stream: VCD clips 0380a3 + 6587ae; incoming stream: 6c9c96 + 9c02f6 (600 frames each, looped over 60 s).

**Questions.**
- **E1:** how fast is each network alone on the NE?
- **E2:** does our program agree with `libmlvc`'s own benchmark tool?
- **E3, E4:** how much faster is sharing the NE (both networks at once) than taking turns, and why?
- **B\*:** does a real 30 fps two-way call meet every deadline, and with how much margin?

**What was run.** 5 interleaved rounds of the four unpaced modes (60 s each, 60 s rest); 5 paced duplex runs of 60 s (= B\*); 3 paced taking-turns runs for reference; 3 runs of `mlvc benchmark` with one encoder and one decoder stream.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/x` | All of the above; calls `y` at the end | 65 min | Quiet mode (see [`../README.md`](../README.md#quiet-mode)): AC power, Wi-Fi and Bluetooth off, brightness at maximum with automatic brightness and True Tone off, no other apps, `./p` run first. |
| `scripts/y` | Summary (uses `common/scripts/sum.py`) | 1 min | any |

## Files

| Path | Contents |
|---|---|
| `raw_data/bl_bstar/` | One folder per run: `T_<mode>_r<round>` (unpaced), `T_duplex30_r<n>` (B\*), `T_turns30_r<n>`, `T_cli_r<n>.log`; each with `frames.csv`, `run.txt`, `.log`, and the outgoing stream for B\* |
| `raw_data/_superseded/` | Two stopped attempts, **not used** (see its README) |
| `raw_data/logs/out_x.txt`, `out_x4.txt`, `out_y.txt` | Console output |
| `results/03_E1_E3_E4_unpaced_full_MLVC_360p.csv` | E1, E3, E4 |
| `results/04_E2_cli_crosscheck.csv` | E2 |
| `results/05_Bstar_duplex_paced_30fps.csv` | **B\*** |
| `results/05b_turns_paced_30fps.csv` | Paced taking turns |
| `results/fig1_unpaced_times`, `fig2_speedup`, `fig3_paced_latency` (`.png`, `.pdf`) | Unpaced times of both models; measured vs ideal speedup; paced latency against the deadline |

### Rows of the unpaced tables

| Row | Meaning |
|---|---|
| `t_enc_call`, `t_dec_call` | Mean call time of each network alone (ms) |
| `t_enc_net`, `t_dec_net` | Mean network (Core ML) time alone (ms) |
| `fps_enc`, `fps_dec` | Throughput alone |
| `sum_alone` | t_enc + t_dec |
| `T_turns` | Time per frame pair, taking turns in one thread |
| `switching_cost` | T_turns − sum_alone |
| `T_shared`, `fps_shared` | Time per frame pair and fps per direction when sharing the NE |
| `S` | T_turns / T_shared |
| `S_max` | sum_alone / max(t_enc, t_dec): ideal speedup with perfect overlap |
| `kappa_*_call`, `kappa_*_net` | Slow-down of each network when sharing (call time / network time) |

### Rows of the paced tables

Each row is prefixed with `send_` (encoder) or `receive_` (decoder).

| Row | Meaning |
|---|---|
| `fps` | Achieved frame rate |
| `late_or_dropped_pct` | (late + dropped) / scheduled × 100 |
| `dropped_frames`, `failures` | Camera frames skipped; failed calls |
| `mean_call_ms`, `p99_call_ms` | Call duration (end − start) |
| `due_to_done_p95_ms`, `due_to_done_p99_ms` | Time from when the frame was due to when it was done |
| `network_ms` | Mean Core ML time |
| `kbps` | Bitrate of the stream |
| `start_delay_mean_ms`, `start_delay_p95_ms` | Time from when the frame was due to the start of its call |
| `call_I_frame_ms`, `call_P_frame_ms` | Mean call time of I-frames and P-frames |

## Results

### E1, E3, E4: unpaced

| Metric | Median (min–max), 5 rounds |
|---|---|
| Encoder alone: call / network (ms) | 5.86 (5.85–5.91) / 5.57 |
| Decoder alone: call / network (ms) | 5.94 (5.92–5.94) / 5.66 |
| Encoder / decoder fps | 170.7 / 168.4 |
| Sum alone (ms) | 11.80 |
| T_turns (ms) | 11.81 (11.81–11.81) |
| Switching cost (ms) | 0.01 (−0.02 to 0.02) |
| T_shared (ms), fps per direction | 10.68, 93.6 |
| **S** / S_max | **1.11** / 1.99 |
| κ enc / dec, call time | 1.82 / 1.80 |
| κ enc / dec, network time | 1.86 / 1.84 |

**Reading.**
- Our times are 24–27 % faster than the MLVC paper's M3 Pro figures, which shows our conversion of full MLVC is sound.
- Everything outside the networks takes only about 0.3 ms per call (5 %).
- Switching between the two models on the NE is free.
- Running both networks at once gains only 11 % of a possible 99 %, because the NE runs them almost one after the other.
- **Speedup therefore has to come from other processors, smaller models, or scheduling, not from parallelism on the NE.**

### E2: check against libmlvc's tool

| | 3 runs (about 5,600 frames each) |
|---|---|
| Encoder stream | 10.7 ms total, 10.4 ms inference, 93.6 fps |
| Decoder stream | 10.7 ms total, 10.4 ms inference, 93.6 fps |

**Reading.** The library's own tool gives the same numbers as our program (10.68 ms, 93.6 fps), so our program adds no cost or bias.

### B\*: duplex paced at 30 fps

| Metric | **B\* send** | **B\* receive** | Turns send | Turns receive |
|---|---|---|---|---|
| fps | 30.01 | 30.01 | 30.01 | 30.01 |
| Late or dropped | **0 %** | **0 %** | 0 % | 0 % |
| Mean call (ms) | 12.44 (12.39–12.47) | 13.32 (13.22–13.40) | 10.66 | 8.44 |
| p99 call (ms) | 20.03 | 20.91 | 13.15 | 9.99 |
| Due-to-done p95 (ms) | 27.88 | 28.02 | 20.17 | 29.81 |
| **Due-to-done p99 (ms)** | **29.27** (29.12–29.33) | **28.93** (28.66–29.16) | 21.30 | 31.06 |
| Start delay mean / p95 (ms) | 5.65 / 10.00 | 5.06 / 10.00 | 3.81 / 7.60 | 14.47 / 20.20 |
| Call time, I-frame / P-frame (ms) | 12.15 / 12.45 | 14.01 / 13.31 | 10.71 / 10.66 | 9.34 / 8.43 |
| Bitrate (kbps) | 120.5 | 287.1 | 120.5 | 287.1 |
| Runs | 5 | 5 | 3 | 3 |

**Reading.**
- The baseline meets real time, but the slowest 1 % of frames keep only about 4 ms (12 %) of slack.
- Two effects use up the 3× unpaced capacity:
  - **Paced calls take about twice as long as unpaced ones** (12.4 vs 5.9 ms). This is likely because the NE clock drops between frames; we have not measured that directly.
  - **Both streams are due at the same instant**, so one waits for the other (start delay up to 10 ms).
- Taking turns also meets 30 fps, but its decoder always waits for the encoder, which pushes the receive p99 to 31.1 ms.
- The two bitrates differ because the incoming clips have more motion and detail.

## Conclusion

B\* runs a two-way 360p call in real time with no late frame, but its slowest frames keep only about 4 ms of slack. The NE runs the two networks almost one after the other (S = 1.11 of an ideal 1.99), so the speedup DuplexNVC needs must come from other processors, smaller models, resolution, or scheduling the two directions so they compete less — which is what experiments 07–09 measure.
