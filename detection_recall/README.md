# Step 7: detection recall (smallest face the scene analyzer detects)

**Owner:** Warda · **Machine:** MacBook Pro 13-inch, Apple M1 (the same Mac as Step 8, so every label and every test detection comes from one Mac)

**Question:** the scene analyzer runs Apple Vision face detection on the camera frame the encoder gets, at the call resolution (360p, 540p or 720p), not on the display-size original. How small can a face be and still be found at each resolution? This sets the smallest face the controller can react to, and so how far a resolution switch can be driven by face size.

## What was run

- **Clips and reference faces:** the 11 Step 8 clips ([`../controller_data/`](../controller_data/)). The reference is the Step 8 face labels: the same detector (`facebox`, `VNDetectFaceRectanglesRequest`) on the display-size masters (1080p, or 720p for the three HEVC Class E clips), every 10th frame. Only participants count; the poster faces excluded in Step 8 (`exclude.csv`) are left out. 560 reference faces.
- **Test:** every labelled frame of each master scaled down with Lanczos, as the encoder input is made, to 360p, 540p and 720p (and 1080p for the 1080p masters, as a check: it should find every reference face), then `facebox` on it. No resolution above the master is tested.
- **Detected:** a box at the lower resolution, scaled back to the master size, overlaps the reference face with IoU ≥ 0.5 (one-to-one, best overlap first). IoU ≥ 0.3 is reported as well.
- **Face size:** face height scaled to 360p, in the Step 8 groups (<32, 32–63, 64–127, ≥128 px at 360p) and in 4-px bins.

Recall here is relative to the same detector at full resolution: it measures what is lost by detecting at the call resolution.

## How to run

```bash
bash ~/DuplexNVC/detection_recall/scripts/s7_run
```
On the Mac that made Step 8 (needs `~/Downloads/duplexnvc-baseline/phase2/step8` and the `facebox` tool). About 5 minutes. It writes the results, copies them here and pushes.

## Files

| File | What |
|---|---|
| `scripts/s7_recall.py` | Scales the frames, runs the detector, matches boxes, writes the tables |
| `scripts/s7_run` | Runs it, copies the results here, pushes |
| `results/recall_by_size.csv` | Recall per resolution and face-size group |
| `results/recall_curve.csv` | Recall per resolution in 4-px face-size bins |
| `results/smallest_face.csv` | Per resolution: smallest face detected; the size from which every bin is found at ≥ 50 %, ≥ 90 % and 100 % |
| `results/recall_by_clip.csv` | Recall per clip and resolution, and extra boxes |
| `results/extra_boxes.csv` | Boxes at the lower resolution that match no participant (poster faces, or no one) |
| `results/faces_step7.csv` | One row per reference face per resolution: size, detected, IoU |
| `results/check/<clip>_360p.jpg` | The 360p frame with the most misses: green = detected, red = missed |
| `raw_data/faces/<clip>_<res>.json` | Every box the detector found at each resolution |
| `raw_data/machine.txt`, `raw_data/out_s7.txt` | Machine and console output |

## Results

(filled in after the run)
