# Step 7: detection recall (smallest face the scene analyzer detects)

**Owner:** Warda · **Machine:** MacBook Pro 13-inch, Apple M1 (the same Mac as Step 8, so every label and every test detection comes from one Mac)

**Question:** the scene analyzer runs Apple Vision face detection on the camera frame the encoder gets, at the call resolution (360p, 540p or 720p), not on the display-size original. How small can a face be and still be found at each resolution? This sets the smallest face the controller can react to, and so how far a resolution switch can be driven by face size.

## What was run

- **Clips and reference faces:** all Step 8 clips ([`../controller_data/`](../controller_data/)): the 11 stock clips (22 Nov) and our 7 recorded call-clip windows (24 Nov), reported separately and together. The reference is the Step 8 face labels: the same detector (`facebox`, `VNDetectFaceRectanglesRequest`) on the display-size masters (1080p, or 720p for the three HEVC Class E clips), every 10th frame. Only participants count; the poster faces excluded in Step 8 (`exclude.csv`) are left out. 560 reference faces in the stock clips and 257 in the call clips (817 in all).
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
| `results/recall_by_size.csv` | Recall per resolution and face-size group, for the stock clips, the call clips and all clips |
| `results/recall_curve.csv` | Recall per resolution in 4-px face-size bins |
| `results/smallest_face.csv` | Per resolution: smallest face detected; the size from which every bin is found at ≥ 50 %, ≥ 90 % and 100 % |
| `results/recall_by_clip.csv` | Recall per clip and resolution, and extra boxes |
| `results/extra_boxes.csv` | Boxes at the lower resolution that match no participant (poster faces, or no one) |
| `results/faces_step7.csv` | One row per reference face per resolution: size, detected, IoU |
| `results/check/<clip>_360p.jpg` | The 360p frame with the most misses: green = detected, red = missed |
| `raw_data/faces/<clip>_<res>.json` | Every box the detector found at each resolution |
| `raw_data/machine.txt`, `raw_data/out_s7.txt` | Machine and console output |

## Results: our recorded call clips

Run on 24 Nov 2026 on the same M1. 257 faces in 7 windows (masters 720p, so tested at 360p, 540p and 720p). At call distance almost every face is large: 124 at 64–127 px and 129 at ≥ 128 px at 360p, the sizes the stock clips do not have.

| Analysis resolution | <32 px | 32–63 px | 64–127 px | ≥128 px | All |
|---|---|---|---|---|---|
| **360p** | 2 of 2 | 2 of 2 | 124 of 124 | 129 of 129 | **100 % (257 of 257)** |
| 540p | 2 of 2 | 2 of 2 | 124 of 124 | 129 of 129 | 100 % (257 of 257) |
| 720p | 1 of 2 | 2 of 2 | 124 of 124 | 129 of 129 | 99.6 % (256 of 257) |

- **Every face is found at the call resolution.** The one miss is at 720p: the person walking past in `rcwalk`, a 28 px face (at 360p) in one frame, found at 360p and 540p; a small face near the limit that comes and goes, as in the stock clips.
- **Faces turned away are found at 360p.** In `rclook` she talks in profile; her face (67–126 px at 360p) is found in all 30 labelled frames at every resolution. So the "looking away is not a false alarm" result of Step 8 also holds on the small frame the analyzer gets.
- **The person walking past is found at 360p too** (all 4 of her face boxes, 28–37 px). So the analyzer does see her, and Step 8's participant rule (a face counts if it is ≥ 30 % of the largest face, or in view for 2 s) is what keeps her from being counted.
- **The large-face group** (≥ 128 px at 360p), empty in the stock clips, is now covered: 129 of 129 found.

## Results: stock clips

Run on 22 Nov 2026 on the M1 (MacBook Pro 13-inch, macOS as in `raw_data/machine.txt`). 560 participant faces in 11 clips; 355 of them in the 1080p masters, where 1080p is also tested.

### Recall by face size (IoU ≥ 0.5)

| Analysis resolution | <32 px | 32–63 px | 64–127 px | ≥128 px | All |
|---|---|---|---|---|---|
| 360p | 96.3 % of 246 | 100.0 % of 236 | 100.0 % of 78 | (none in the clips) | **98.4 %** of 560 |
| 540p | 95.5 % of 246 | 100.0 % of 236 | 100.0 % of 78 | – | 98.0 % of 560 |
| 720p | 95.1 % of 246 | 99.6 % of 236 | 100.0 % of 78 | – | 97.7 % of 560 |
| 1080p (same size as the reference) | 95.4 % of 241 | 100.0 % of 114 | – | – | 96.9 % of 355 |

Face height at 360p. Loosening the match to IoU ≥ 0.3 finds none of the missed faces, so every miss is a face the detector did not report, not a box in a slightly different place.

### Smallest face

| Analysis resolution | Smallest face found | Every 4-px size bin found at ≥ 90 % from | All faces found from | Largest face missed |
|---|---|---|---|---|
| 360p | 14.3 px (14 px in the 360p frame) | 16 px | 32 px | 29.7 px |
| 540p | 14.3 px (21 px in the 540p frame) | 12 px | 32 px | 29.7 px |
| 720p | 14.3 px (29 px in the 720p frame) | 12 px | 40 px | 37.0 px |
| 1080p | 14.3 px (43 px in the 1080p frame) | 12 px | 32 px | 29.7 px |

Sizes are face heights at 360p unless a frame size is named. 14.3 px is the smallest face in the clips, and it was found at every resolution. The detector's limit is therefore **below 14 px at 360p** (below 43 px at 1080p); these clips have no smaller faces to show where it lies.

### Per clip

Every clip is at 96–100 % at every resolution except two. **pxcrwd** (a crowd entering, small faces in profile and partly hidden) is at 74–85 %. **pxleav** has only 2 faces (people walking away), so one miss is 50 %. 5 of the 9 misses at 360p are in pxcrwd (`results/recall_by_clip.csv`).

### Extra boxes

Boxes at the lower resolution that match no participant: 18 at 360p, 14 at 540p, 12 at 720p, 3 at 1080p. The poster faces excluded in Step 8 are still found at every resolution (46 at 360p, 57 at 540p, 58 at 720p).

## Conclusion

0. **On our call clips the detector finds every face at 360p (257 of 257)**, including faces in profile and the person walking past; the only miss in 771 tests is that passer-by's 28 px face once at 720p. Together with the stock clips, every face of 32 px or more at 360p is found, across all four size groups (817 faces).
1. **Detecting at the call resolution loses nothing.** At 360p the detector finds 98.4 % of the faces it finds at full size, and that is no lower than at 540p, 720p or 1080p. Re-running it at the reference's own 1080p size (only the image format differs, PNG instead of JPEG) also misses 11 of 355 faces, against 9 of 560 at 360p. So the misses are small, hard faces near the detector's limit that come and go from one run to the next, not a loss from scaling down. The scene analyzer can therefore work on the camera frame the encoder already has. It needs no extra full-size copy, which also keeps its cost low (Step 7 cost, Shams).
2. **Every face of 32 px or more at 360p is found** (≥ 96 px at 1080p), at every resolution except one face of 37 px at 720p. Every face-size group the controller uses from 32 px up is reliable.
3. **Below 32 px at 360p, about 1 face in 20 is missed** (95–96 %), with no clear trend with size down to 16 px. The smallest face in the clips, 14 px at 360p, is still found, so the detector's limit lies below that. The controller should treat a single missing small face as noise. Step 8's 1-second persistence rule does this already.
4. **Crowds are the hard case** (pxcrwd, 74–85 %): small faces in profile and partly hidden. That matches Step 8, where the body detector counted the crowd far better than faces.
5. **Poster faces are found at every resolution**, so the analyzer needs Step 8's size rule (`exclude.csv`) or the body detector to ignore them in a call as well.
