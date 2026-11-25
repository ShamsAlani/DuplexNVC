# 10 — raw data

| File | Contents |
|---|---|
| `q.csv` | One row per configuration × clip × QP (900 rows): bitrate, coded PSNR-Y and PSNR-YUV, display PSNR-Y, face PSNR-Y and LPIPS, number of scored faces, mean face height at the coded size, decoded and source frame count, the unit the encoder resolved to, and the time of the encode, decode and metrics |
| `faces.csv` | One row per scored face (27,180 rows): configuration, clip, QP, frame, face height at 1080p and at the coded size, face PSNR-Y, face LPIPS (blank when the face is under 32 px) |
| `run.txt` | Date, macOS version and build, libmlvc commit of Part A |
| `energy/energy_qp.csv` | Part B: one row per setting × QP (35 rows): energy per frame pair (median, min, max of 5 runs; total, NE, GPU, CPU), late share, frame rate, p99 and bitrate per direction |
| `energy/thermal.csv` | Part B: thermal state and Low Power Mode once a second (27,565 rows; *nominal* and off throughout) |
| `logs/out_all.txt` | Full console log of Part A (`scripts/quality_per_setting_runs.sh`): pre-flight checks, every run with its result and the unit the encoder used, and the analysis printout |
| `logs/out_en.txt` | Full console log of Part B (`scripts/energy_per_qp_runs.sh`): pre-flight, the bitrate of each incoming stream, every run with the units it resolved to, the energy table (`energy_per_qp_table.py`) and the analysis printout |

Columns of `q.csv`: `cfg` = `<setting>_<encoder unit>-<decoder unit>`; `kbps` at 30 fps over the 300 frames; `psnr_y`, `psnr_yuv` = (6Y+U+V)/8 at the coded size against the encoder input; `psnr_y_display` = decode upscaled with Lanczos to 1920×1080 against the 1080p original, every 10th frame; `face_psnr_y`, `face_lpips` inside the Apple Vision face boxes of the original, every 10th frame.

Also on the measurement laptop under `~/Downloads/duplexnvc-baseline/phase2/4b/`, not copied here because of size:

| Folder | Contents |
|---|---|
| `frames/<cfg>/<clip>_qp<QP>.csv` | Per-frame coded PSNR-Y and PSNR-UV (300 rows) and display PSNR-Y (every 10th frame) |
| `bits/<cfg>/<clip>_qp<QP>.mlvc` | The 900 bitstreams |
| `cache/<clip>_orig.nv12`, `cache/<clip>_faces.json` | Every 10th original 1080p frame and its face boxes |
| `inc/<setting>-qp<QP>/` | Part B incoming streams (600 frames) at each QP |
| `energy/<cfg>/qp<QP>_r<round>/` | Part B per-run records: `frames.csv`, `run.txt`, `power.txt` (`powermetrics`), plus `.log` and `.therm` next to each folder |
| `energy/idle_<setting>/power.txt` | Part B 120 s idle recording before each setting |

The decoded videos were deleted after their metrics were computed.

To pack them (on the Mac):

```
cd ~/Downloads/duplexnvc-baseline/phase2/4b && zip -r -9 ~/Downloads/DuplexNVC_4b_raw.zip frames bits cache/*_faces.json energy -x 'energy/*/*/power.txt'
# power.txt files are large; add them separately if needed: zip -r -9 ~/Downloads/DuplexNVC_4b_power.zip energy -i '*/power.txt'
```
