# demo/

`demo.mov` (9 s) shows **MLVC-S**, the smaller MLVC model, compressing a talking-head video on the project laptop (MacBook Pro, Apple M4 Pro) and rebuilding it, with the original and the decoded video played side by side.

## What it shows

| Side | Content |
|---|---|
| **Left** | The original clip: VCD scenario `s1`, clip `0380a3`, 960×540, 30 fps, 300 frames (10 s), uncompressed NV12 — **222 MB** |
| **Right** | The same clip after encoding with MLVC-S into a **543 KB** bitstream and decoding it again |

The window title reads `LEFT: original (222 MB) | RIGHT: MLVC-S decoded (543 KB)`: the right side is rebuilt from those 543 KB. The bitstream is about **420 times smaller** than the raw video (about **445 kbit/s**, 0.029 bits per pixel), yet the decoded picture stays very close to the original.

| Measure (decoded vs original, all 300 frames) | Value |
|---|---|
| Bitstream size / bitrate | 543 KB / ≈ 445 kbit/s |
| Compression | ≈ 420× |
| PSNR, luma (Y) | 37.30 dB |
| PSNR, chroma U / V | 51.87 / 49.45 dB |
| PSNR, all planes | 38.96 dB on average (lowest frame 24.22 dB, highest 46.85 dB) |
| SSIM, Y / overall | 0.9858 / 0.9888 |

Most of the clip codes at high quality. The lowest-scoring frames fall in a fast-motion segment near the end of the clip, where the perceptual model blurs motion slightly; this is expected of a model trained to look good to people rather than to maximise PSNR.

## Setup

| Item | Value |
|---|---|
| Device | MacBook Pro 14-inch, Apple M4 Pro (Mac16,8), 24 GB, macOS 26.6 |
| Codec | `libmlvc` 0.1.0 (commit `c504aaa`), command-line tool `mlvc` |
| Model | MLVC-S `dmc61sbr_mini_reglu`, perceptual weights `perceptual_v1`, the Core ML bundle shipped with `libmlvc` |
| Processor | Apple Neural Engine (`Manager: coreml/npu`), model input 960×544 |
| Coding | QP 22, I-frame period 1024 (library default), long-term references on |
| Input | `data/test_data/clips/VCD_s1_0380a3_960x540_30fps.nv12.gz` from `libmlvc` |

This is the Phase 1 MLVC-S configuration (540p, QP 22, perceptual weights). It predates the pinned commit `eb5d60a` used for all measurements in [`../baseline/`](../baseline/), which use QP 26 and PSNR weights.

## How it was made

All commands run in Terminal from `~/Desktop/PVB`, where `libmlvc` is cloned and built and `mlvc` is on the path.

**1. Encode (the sender's job: camera frames → bits), on the Neural Engine:**
```bash
cd ~/Desktop/PVB/libmlvc
mlvc encode --input ./data/test_data/clips/VCD_s1_0380a3_960x540_30fps.nv12.gz \
  --input-width 960 --input-height 540 --output ~/Desktop/PVB/results/test.mlvc --qp 22
```

**2. Decode (the receiver's job: bits → frames):**
```bash
mlvc decode --input ~/Desktop/PVB/results/test.mlvc --output ~/Desktop/PVB/results/test.mkv
```
`test.mlvc` is the 543 KB bitstream; `test.mkv` holds the rebuilt frames, uncompressed (again about 222 MB).

**3. Unpack the original raw clip** (raw NV12 has no header, so size and format are given explicitly):
```bash
mkdir -p ~/Desktop/PVB/clips
gunzip -c ~/Desktop/PVB/libmlvc/data/test_data/clips/VCD_s1_0380a3_960x540_30fps.nv12.gz \
  > ~/Desktop/PVB/clips/vcd_960x540.nv12
```

**4. Build the side-by-side video**, original left and decoded right, stored losslessly (FFV1) so that no extra blur is added:
```bash
cd ~/Desktop/PVB
ffmpeg -y -loglevel error \
  -f rawvideo -pixel_format nv12 -video_size 960x540 -framerate 30 -i clips/vcd_960x540.nv12 \
  -i results/test.mkv \
  -filter_complex "[0:v][1:v]hstack=inputs=2" \
  -c:v ffv1 results/demo_side_by_side.mkv
```

**5. Play it in a loop** with a window title that labels both sides:
```bash
cat > ~/Desktop/PVB/play_demo.sh <<'EOS'
#!/bin/bash
ffplay -loglevel error -loop 0 -window_title "LEFT: original (222 MB)  |  RIGHT: MLVC-S decoded (543 KB)" \
  ~/Desktop/PVB/results/demo_side_by_side.mkv
EOS
chmod +x ~/Desktop/PVB/play_demo.sh
~/Desktop/PVB/play_demo.sh
```
Keys: `space` pause/play, `f` fullscreen, `q` close.

**6. Measure quality** (the numbers in the table above):
```bash
cd ~/Desktop/PVB
ffmpeg -i results/test.mkv -f rawvideo -pixel_format nv12 -video_size 960x540 -framerate 30 \
  -i clips/vcd_960x540.nv12 \
  -lavfi "[0:v]format=yuv420p[d];[1:v]format=yuv420p[r];[d][r]psnr" -f null - 2>&1 | grep PSNR
# replace psnr with ssim for SSIM
```

Optional, to see where detail is lost (difference amplified 8×; black means identical):
```bash
ffmpeg -loglevel error \
  -f rawvideo -pixel_format nv12 -video_size 960x540 -framerate 30 -i clips/vcd_960x540.nv12 \
  -i results/test.mkv \
  -filter_complex "[0:v]format=yuv420p[a];[1:v]format=yuv420p[b];[a][b]blend=all_mode=difference,lutyuv=y='val*8':u=128:v=128" \
  -c:v rawvideo -f nut - | ffplay -loglevel error -window_title "Difference x8" -
```

## How it relates to the measurements

- Here the encode and the decode run **one after the other**. A real call needs both **at the same time** on the same chip, which is exactly what `duplex_bench` measures in [`../baseline/`](../baseline/).
- With both directions at once, MLVC-S at 540p with both networks on the Neural Engine is the most efficient setting we measured (PSNR weights, QP 26): 30 fps both ways with no late frame, slowest frames within about 27 ms of the 33.3 ms deadline, about 45 mJ per frame pair (see [`../baseline/09_placement_experiment/`](../baseline/09_placement_experiment/)).
