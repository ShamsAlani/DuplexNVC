# quality_eval/: E6, rate-distortion, display and face quality

**Script:** `scripts/g`, which uses `scripts/rd.py`.
**Log:** `../logs/out_g.txt`.
**Clips:** the 20 evaluation clips of `../split.json` (VCD s1, 640×360 raw YUV, 300 frames each). The 1080p MP4 releases serve as the display reference (downloaded by `scripts/f`).

**Method**, per clip and QP (16, 24, 32, 40):
1. Encode with `libmlvc_example prepare` on the NE; decode with `mlvc decode` on the NE.
2. Coded scale: PSNR-Y and PSNR-YUV (6:1:1) against the 360p input.
3. Display scale: upscale the decoded frame to 1920×1080 with Lanczos (OpenCV) and compare PSNR-Y with the 1080p original.
4. Faces: on every 10th frame, Apple Vision face boxes on the original; face PSNR-Y and LPIPS (AlexNet) inside the boxes.

| File | Contents |
|---|---|
| `rd_eval.csv` | One row per clip and QP: `bytes`, `kbps`, `frames`, `psnr_y`, `psnr_yuv`, `psnr_y_display`, `face_psnr_y`, `face_lpips`, `faces` (face boxes scored), `face_h_coded_mean` (mean face height in 360p pixels) |
| `clips.txt` | Clip ID, 360p input and 1080p reference used for each clip |

**Result** (`../../results/09`, `10`), mean of the 20 clips:

| QP | kbps | PSNR-Y | Display PSNR-Y | Face PSNR-Y | Face LPIPS |
|---|---|---|---|---|---|
| 16 | 391.5 | 40.94 | 34.54 | 35.28 | 0.223 |
| 24 | 207.9 | 39.23 | 33.82 | 34.13 | 0.245 |
| 32 | 92.9 | 36.06 | 32.15 | 31.86 | 0.292 |
| 40 | 39.7 | 31.97 | 29.38 | 28.76 | 0.373 |
