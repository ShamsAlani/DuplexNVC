# 07 — raw data

| Path | Contents |
|---|---|
| `exp07_per_run_records.zip` (12 MB) | Every run of X1 as it was written on the measurement laptop under `~/Downloads/duplexnvc-baseline/phase2/step1/` |
| `logs/out_1.txt`, `logs/out_1r.txt` | Console logs of the runs and of the summary (recorded under the scripts' old names, `1` and `1r`) |

Inside the archive (`step1/`):

| Folder | Contents |
|---|---|
| `mlvc_360p/`, `mlvcs_540p/` | One folder per run, `<P or U>_alone-<enc or dec>_<unit>_r<n>/` (P = paced at 30 fps, U = unpaced; unit = npu, gpu or cpu), with its `.log` and `.therm` files next to it |
| `trace/<bundle>/metadata*.json` | The model bundles' metadata used by the placement trace, for each model input size |
| `step1_table.csv` | The table the summary script builds from the runs |

Each run folder holds `frames.csv` (one row per frame: direction, frame, due/start/end times, call and network time, frame type, bytes, success, warm-up flag), `run.txt` (settings, t0, dropped/failed counts) and, for paced runs, `power.txt` from `powermetrics`.

Left out to keep the archive small: the copies of the Core ML model bundles that the trace wrote next to the metadata (`bundled_model.mlpackage.tar` and its unpacked folder, 98 MB; the same files as the converted bundles of experiment 08), and the coded video streams.
