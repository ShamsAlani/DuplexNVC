# 09 — raw data

The per-run records of X1 (experiment 07) and X3 (experiment 09) are on the measurement laptop under `~/Downloads/duplexnvc-baseline/phase2/` and are added here as a compressed archive.

Layout on the laptop:

| Folder | Contents |
|---|---|
| `step1/` | X1 runs: `<setting>/<mode>_<unit>_r<n>/` |
| `step2/sanity/<bundle>/U_alone-<enc|dec>_npu_r<n>/` | X3 part A: NE alone |
| `step2/memory/<bundle>_<unit>.log` | X3 part A: peak memory (`/usr/bin/time -l`) |
| `step4/alone/<setting>/U_alone-<enc|dec>_<unit>_r<n>/` | X3 part B: GPU and CPU alone |
| `step4/<setting>_<enc>-<dec>/U_turns_r<n>`, `U_duplex_r<n>`, `P30_r<n>`, `P15_r<n>` | X3 part C: unpaced, paced 30 fps, paced 15 fps |
| `step4/idle/<batch>/power.txt` | 120 s idle recording before each batch |
| `step4/thermal.csv` | Thermal state and Low Power Mode at 1 Hz |

Each run folder holds `frames.csv` (one row per frame: direction, frame, due/start/end times, call and network time, frame type, bytes, success, warm-up flag), `run.txt` (settings, t0, dropped/failed counts), the `.log` and `.therm` files, and for paced runs `power.txt` from `powermetrics`.

To pack it (on the Mac, from `~/Downloads`), keeping records and logs but not the large outgoing streams:

```
cd ~/Downloads/duplexnvc-baseline && \
zip -r -9 ~/Downloads/DuplexNVC_phase2_raw.zip phase2 -x '*.aus' -x '*.nv12' -x '*.yuv' -x '*.mlpackage/*' -x '*.tar'
```
