# 08 — Controller data: multi-person clips, face labels and face-size groups (Step 8)

**Owner:** Warda · **Machine:** Warda's M1. Step 8 does not depend on the chip, and all face labels come from this one Mac.

**Questions.**
1. Which multi-person clips, with people entering and leaving, will the controller, A3, A4 and E1 be tested on?
2. How many faces fall in each face-size group at 360p, and does every group have enough faces?
3. Where in each clip does the number of people actually change (the scene changes A3 and A4 react to), and does Apple Vision see those changes?

The baseline's 20 evaluation clips are single VCD talking heads: every face is at least 32 px tall at 360p, and only 6 faces fall in 96–191 px at 1080p (experiment 10). Face-size groups and scene changes need new content.

## Clips (11, run on 20 Nov 2026)

The set has three roles: **entries with faces toward the camera** (the face trigger should react), **people entering or leaving with their faces away from the camera** (only a frame-difference trigger can react; this happens often in real calls: someone walks off, or enters with their back turned), and **controls** where nobody enters or leaves (no trigger should fire).

| id | Source file | Source size, fps, length | Master | What happens | Role |
|---|---|---|---|---|---|
| `ce4peo` | `FourPeople_1280x720_60.y4m` | 1280×720, 60 fps, 10.0 s | 300 frames | 4 people seated | control |
| `cejohn` | `Johnny_1280x720_60.y4m` | 1280×720, 60 fps, 10.0 s | 300 frames | 1 person, poster behind him | control |
| `cekris` | `KristenAndSara_1280x720_60.y4m` | 1280×720, 60 fps, 10.0 s | 300 frames | 2 people, poster behind them | control |
| `px2ent` | `2_people_entering_room.mp4` | 4096×2160, 25 fps, 29.9 s | 300 frames from 2 s | a man and a boy enter far from the camera; a woman enters close to the camera, back turned | entries (faces away / far) |
| `pxentr` | `people_entering_room.mp4` | 3840×2160, 25 fps, 15.3 s | 300 frames | a family of 3 enters through a door | entry (faces toward) |
| `px4ppl` | `4_people.mp4` | 4096×2160, 25 fps, 30.6 s | 300 frames | 4 people enter an empty meeting room one by one | entries (faces toward) |
| `px5ppl` | `5_people.mp4` | 1920×1080, 25 fps, 33.4 s | 300 frames | 5 people seated in a meeting | control |
| `px7ppl` | `7_people.mp4` | 1920×1080, 25 fps, 20.8 s | 300 frames | 7 people in a meeting | control |
| `pxcrwd` | `people_entering.mp4` | 3840×2160, 30 fps, 8.8 s | 265 frames | a crowd walks out of arrival doors toward the camera | entries (many people) |
| `pxleav` | `people_leaving.mp4` | 3840×2160, 25 fps, 6.0 s | 148 frames | people walk away from the camera into a café | leaving (faces away) |
| `pxdown` | `people_leaving_going_downstairs.mp4` | 3840×2160, 25 fps, 7.3 s | 182 frames | 3 people walk away toward a door and stairs | leaving (faces away) |

- **HEVC Class E** (`ce…`): Xiph derf collection (`https://media.xiph.org/video/derf/y4m/`), public domain, 600 frames.
- **Pexels** (`px…`): Pexels licence, free to use.
- **VCD** is not part of this step: all 160 VCD clips (`th`, `th-ob`, `th-bb`, `th-m`) show one person throughout (VCD README), so VCD contributes to the controller data through the baseline's 20 evaluation clips, which give the large-face groups. VCD's data licence is CDLA-Permissive 2.0.

## What was run

- **Master clip** (`scripts/s8_prep.py`): up to 300 frames (10 s) at 30 fps from `start_s`; the three short sources give masters of their full length (148–265 frames), recorded in `meta.json`. ffmpeg is told the exact number of output frames for every clip.
  - 60 fps sources (Class E) keep every 2nd frame. 25 fps sources keep every frame and are relabelled to 30 fps (`setpts`), as the baseline did, so no frame is duplicated or interpolated.
  - Sources that are not 16:9 (4096×2160) are first cropped in the centre to 16:9, so faces are not squashed (`cropped_to_16x9` in `meta.json`).
  - Sources of 1080p or more are scaled to 1920×1080 with ffmpeg's Lanczos filter. Class E stays 1280×720, so its display-scale reference is 720p and its 720p setting is the original.
  - x264 CRF 10. The master plays the role of VCD's 1080p MP4 in the baseline.
- **Encoder inputs** (360p/540p/720p NV12) are made from the master on the Mac that runs the codec, with the baseline's command (`scale=W:H:flags=lanczos`, NV12).
- **Face labels:** every 10th master frame, Apple Vision `VNDetectFaceRectanglesRequest` with the baseline's `common/code/facebox.swift`. JSON as in the baseline's face cache (`i` = JPG index), plus `frame` = master frame index.
- **Face-size groups:** face height scaled to 360p: <32, 32–63, 64–127, ≥128 px (= <96, 96–191, 192–383, ≥384 px at 1080p, the bins of experiment 10's `facesize.csv`).
- **Poster faces** (`raw_data/exclude.csv`): in `cejohn` and `cekris` a poster with printed faces stands behind the speakers; faces under 45 px at 360p there are not participants (the real faces are 66–115 px, the printed ones 21–32 px). They stay in `faces_step8.csv` with `participant = 0` and are left out of people counts, groups and events.
- **Automatic events** (`scripts/s8_table.py`): a change in the number of participant faces that holds for 3 labelled frames (1 s).
- **Visual check:** check images with the boxes (first, middle and last labelled frame of each clip), contact sheets of every 10th master frame, and contact sheets of one frame per second over each full source clip.

## How to run

```bash
conda deactivate                                             # if Anaconda is installed
./s8_setup <path-to-repo>                                    # tools, folders, facebox (once)
# put the clips in ~/Downloads/duplexnvc-baseline/phase2/step8/src, list them in clips.csv,
# poster faces in exclude.csv (optional)
~/Downloads/duplexnvc-baseline/.venv/bin/python s8_prep.py   # masters + face labels (resumable)
~/Downloads/duplexnvc-baseline/.venv/bin/python s8_table.py  # tables, groups, events, check images
```

Software versions are in `machine.txt` (ffmpeg 9.0.2, Python 3.12.16, NumPy 2.5.5, OpenCV 5.1.0, Swift 6.1.2).

## Files

| Path | Contents |
|---|---|
| `raw_data/clips.csv` | Clip list: id, source, file, start, licence, URL, notes |
| `raw_data/exclude.csv` | Clips with poster faces and the size limit used |
| `raw_data/meta.json` | Per clip: source size, fps, frames kept, crop, master size |
| `raw_data/faces/<id>.json` | Apple Vision face boxes on every 10th master frame |
| `raw_data/events_truth.csv` | Real entries and leaving, marked by eye |
| `raw_data/events_checked.csv` | Each automatic event, confirmed or not, with what actually happens |
| `results/dataset_table.csv` | One row per clip: sizes, length, people (max, median), background faces, events, faces per group, smallest and largest face |
| `results/faces_step8.csv` | One row per labelled face, with its group and `participant` |
| `results/groups.csv` | Participant faces and clips per size group |
| `results/events.csv` | Automatic events (rewritten by every run of `s8_table.py`) |
| `machine.txt` | Hardware, macOS, ffmpeg and Python of the labelling Mac |

## Where the videos are

The videos are not in git (the repo ignores `.mp4`, `.y4m` and `.nv12`). They are in the team's Google Drive folder: https://drive.google.com/drive/folders/1oWpQzQQ0RcG-FsGjj5eCvFNP4mEe8kJ0

| In the Drive folder | Contents |
|---|---|
| the 11 source files (names as in the clip table) | the original clips the masters were made from |
| `step8_masters/` | the 11 masters (`<id>_<width>x<height>_30.mp4`) and `meta.json` |

**Use the masters, not the sources, for every codec run.** All frame numbers in `raw_data/` and `results/` (face boxes, events) refer to the master frames. Download them into `~/Downloads/duplexnvc-baseline/phase2/step8/master/`; the encoder inputs at 360p/540p/720p are made from these files with the baseline's command.

## Results

**Faces.** 628 faces in 301 labelled frames: 560 participants and 68 poster faces (53 in `cejohn`, 15 in `cekris`).

| Face height at 360p | Participant faces | Clips | Baseline (20 VCD clips) |
|---|---|---|---|
| < 32 px | 246 | 9 | none |
| 32–63 px | 236 | 7 | 6 faces |
| 64–127 px | 78 | 2 | 400 faces |
| ≥ 128 px | 0 | 0 | 198 faces |

**People per clip** (participant faces, every 10th frame, max / median): `ce4peo` 4 / 4, `cejohn` 1 / 1, `cekris` 2 / 2, `px2ent` 2 / 0, `pxentr` 4 / 2.5, `px4ppl` 4 / 2, `px5ppl` 4 / 3 (5 present), `px7ppl` 4 / 3 (7 present), `pxcrwd` 3 / 1, `pxleav` 1 / 0, `pxdown` 1 / 0.

**Real events** (`events_truth.csv`): 8 entries in 4 clips and 2 leaving clips.

| Clip | Event (master frame) |
|---|---|
| `px4ppl` | one person enters at 20, 70, 80 and 110 |
| `pxentr` | a family of 3 enters at 90 |
| `px2ent` | a man and a boy enter at 20 (far); a woman enters at 250 (close, back turned) |
| `pxcrwd` | a crowd enters from 60 to the end |
| `pxleav`, `pxdown` | people walk away from the camera through the whole clip |

**Automatic events against the real ones** (`events_checked.csv`):

| | Count |
|---|---|
| Automatic events | 11 |
| Real (confirmed) | 4: `px2ent` 250, `pxentr` 190, `px4ppl` 90, `pxcrwd` 220 |
| Not real (heads turning, someone leaning into view, a man turning to the camera) | 7 |
| Delay after the first person enters | `px2ent` (woman) 0, `px4ppl` 70 frames (2.3 s), `pxentr` 100 (3.3 s), `pxcrwd` 160 (5.3 s) |
| Real events with no automatic event | the distant entry in `px2ent` (frame 20); both leaving clips (faces never toward the camera) |

## Conclusion

1. **Every face-size group is covered** by this step and the baseline together: the new clips give the small groups (246 faces under 32 px in 9 clips, 236 in 32–63 px in 7 clips), which the baseline lacks; the baseline's talking heads give the large ones. This supports the controller rule "a face of this size needs at least this resolution".
2. **Faces found are not people present.** In group clips Apple Vision finds about half of the people (median 3 of 7 in `px7ppl`, 3 of 5 in `px5ppl`), because faces turn away, look down or are hidden, and it also finds printed faces on a poster (68 boxes in two clips). The controller has to treat the face count as a lower bound and ignore faces that never move.
3. **A face-count trigger alone is late and blind to faces turned away.** Of 11 automatic events, 4 are real, arriving 0–5.3 s after the first person enters; the distant entry and both leaving clips produce no face event at all. The controller needs persistence (a change must last 1 s before it acts), and A3 should pair the face trigger with a frame-difference trigger, which reacts to movement whether or not a face is visible.
4. **Clips for the next steps:** `px4ppl`, `pxentr`, `px2ent` and `pxcrwd` for entries; `pxleav` and `pxdown` for leaving; `ce4peo`, `cejohn`, `cekris`, `px5ppl` and `px7ppl` as controls, where nothing should trigger.
