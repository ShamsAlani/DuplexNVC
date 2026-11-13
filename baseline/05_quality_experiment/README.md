# 05 — Quality experiment: compression and viewed quality (E6)

**Questions.**
- How many bits does full MLVC at 360p save against the hardware HEVC encoder in today's laptops (BD-rate)?
- What quality does it reach at QP 16, 24, 32 and 40, measured at the coded size, at the size the viewer sees (upscaled to a 1080p screen), and on faces?

**What was run.**
- **BD-rate set:** `mlvc validate` on `libmlvc`'s three 3 s VCD `s1` validation clips, against the bundled Intel hardware HEVC anchor.
- **Evaluation set:** 40 VCD `s1` talking-head clips split at random (seed 694) into 20 calibration and 20 evaluation clips, the four timing clips forced into calibration; every evaluation clip encoded and decoded at QP 16/24/32/40 on the NE. Coded PSNR against the 360p input; display PSNR after Lanczos upscaling to 1920×1080 against the 1080p original; face PSNR and LPIPS (AlexNet) inside Apple Vision face boxes on every 10th frame.
- **Timing clips:** the same rate–distortion procedure on the four clips used for the timing streams.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/f` | Downloads the 40 talking-head clips at 1080p (MP4) | 10 min | Wi-Fi on |
| `scripts/q` | `mlvc validate` (BD-rate) and rate–distortion on the timing clips | 5 min | any |
| `scripts/g` | Split, then rate–distortion, display and face quality on the 20 evaluation clips (uses `rd.py`) | 20 min | 360p VCD archive downloaded |
| `scripts/rd.py` | Per clip and QP: encode (NE), decode (NE), coded PSNR, 1080p frames, face boxes, display/face PSNR and LPIPS → `rd_eval.csv` | — | — |

## Files

| Path | Contents |
|---|---|
| `raw_data/split.json` | The calibration / evaluation split |
| `raw_data/quality_eval/` | `rd_eval.csv`: every evaluation clip × QP |
| `raw_data/quality_shipped/` | Rate–distortion of the four timing clips |
| `raw_data/logs/out_f.txt`, `out_g.txt`, `out_q.txt` | Console output |
| `results/08_E6_bdrate_mlvc_validate.txt` | BD-rate table |
| `results/09_E6_rd_evaluation_mean.csv` | Per QP, mean of 20 clips: `kbps, psnr_y, psnr_yuv, psnr_y_display, face_psnr_y, face_lpips` |
| `results/10_E6_rd_evaluation_per_clip.csv` | Per clip and QP, plus `frames, faces_scored, face_height_coded_px` |
| `results/fig6_rate_distortion`, `fig7_per_clip_qp24` (`.png`, `.pdf`) | PSNR (coded, display, face) and face LPIPS vs bitrate; every clip at QP 24 |

## Results

**BD-rate vs Intel hardware HEVC.** 3 clips; anchor 82–1,205 kbps, MLVC 50–507 kbps:

| Y | U | V | YUV |
|---|---|---|---|
| **−31.2 %** | −73.1 % | −72.2 % | **−41.0 %** |

**Evaluation set.** Mean of 20 clips. "Display" means the decoded frame upscaled to 1080p with Lanczos and compared with the 1080p original. "Face" is the same comparison restricted to the Apple Vision face boxes, on every 10th frame.

| QP | kbps | PSNR-Y | PSNR-YUV | Display PSNR-Y | Face PSNR-Y | Face LPIPS |
|---|---|---|---|---|---|---|
| 16 | 391.5 | 40.94 | 42.09 | 34.54 | 35.28 | 0.223 |
| 24 | 207.9 | 39.23 | 40.62 | 33.82 | 34.13 | 0.245 |
| 32 | 92.9 | 36.06 | 37.92 | 32.15 | 31.86 | 0.292 |
| 40 | 39.7 | 31.97 | 34.33 | 29.38 | 28.76 | 0.373 |

**Shipped clips** (the 4 used for timing): 433.7, 236.9, 104.9 and 43.6 kbps at 40.26, 38.46, 35.33 and 31.48 dB PSNR-Y. These are in line with the evaluation set.

**Reading.**
- MLVC compresses far better than hardware HEVC.
- At the size the viewer sees, the 360p resolution costs 4–6 dB, more than the coding does.
- Going from QP 24 to 32 at the display size costs only 1.7 dB, so extra bits buy little and resolution is the stronger lever.
- Clips `1e8830` and `4d8ffe` stay at about 25 dB on the display at every QP, most likely because of fine texture that 360p cannot represent. `10_E6_rd_evaluation_per_clip.csv` has every clip, together with the number of faces scored and the face height.

## Conclusion

Full MLVC needs 31 % fewer bits than hardware HEVC for the same luma quality, which is the reason to use a learned codec at all. At the size a viewer actually sees, however, the 360p resolution costs 4–6 dB — more than the coding — so resolution is the stronger lever. Raising it costs processing time on the NE, which `09_placement_experiment` measures.
