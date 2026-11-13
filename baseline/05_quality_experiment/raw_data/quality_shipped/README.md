# quality_shipped/: E6, BD-rate vs HEVC and R-D on the timing clips

**Script:** `scripts/q`.
**Log:** `../logs/out_q.txt`.

| File | Contents |
|---|---|
| `validate.log` | `mlvc validate` on libmlvc's validation set (VCD-640x360-s1-3s, 3 clips, QP 16/24/32/40) against the bundled Intel hardware HEVC (low-power) anchor. Gives BD-rate per plane |
| `rd_shipped.csv` | R-D of full MLVC 360p on the 4 clips used for timing (0380a3, 6587ae, 6c9c96, 9c02f6). One row per clip and QP: `bytes`, `kbps`, `psnr_y`, `psnr_yuv` |
| `clips.txt` | The clips used |

**Result:**
- BD-rate vs Intel HW HEVC: **−31.2 % (Y)**, −73.1 % (U), −72.2 % (V), **−41.0 % (YUV)**. Anchor 82–1,205 kbps, MLVC 50–507 kbps.
- Shipped clips, mean: 433.7 / 236.9 / 104.9 / 43.6 kbps at 40.26 / 38.46 / 35.33 / 31.48 dB PSNR-Y. This is in line with the evaluation set, so the timing streams are representative.
