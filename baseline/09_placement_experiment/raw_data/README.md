# 09 — raw data

The per-run records of X3 are here as two archives (split so that each stays under GitHub's 100 MB file limit); X1's (experiment 07) are in [`../../07_processor_experiment/raw_data/`](../../07_processor_experiment/raw_data/).

| Path | Contents |
|---|---|
| `exp09_per_run_records_part1.zip` (54 MB) | `step4/` except the MLVC-S runs: `alone/`, `idle/`, every `mlvc_<size>_<enc>-<dec>/` folder, `table_feasible.csv`, `thermal.csv` |
| `exp09_per_run_records_part2.zip` (44 MB) | `step4/mlvcs_<size>_<enc>-<dec>/`: every MLVC-S run |
| `logs/` | Console logs (recorded under the scripts' old names: `out_all.txt`, `out_4r.txt`) |

Unzip both into the same folder to get the whole `step4/`. Part A of X3 (NE alone per bundle, peak memory; `step2/` on the laptop) is summarised in `logs/out_all.txt` and not archived.

Layout on the laptop (`~/Downloads/duplexnvc-baseline/phase2/`):

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
