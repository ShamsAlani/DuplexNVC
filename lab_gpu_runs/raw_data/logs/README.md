# Logs

| File | Written by | What it records |
|---|---|---|
| [`pipeline.txt`](pipeline.txt) | `lab.ps1` | Every pipeline start, data step, finished round and failure, with date and time |
| [`prep.txt`](prep.txt) | `lab.ps1` and MLVC's data scripts | Download, unzip, sequence selection and frame extraction (including the errors of the failed attempts) |
| [`v1_control.txt`](v1_control.txt) | MLVC's `train_video.py` | Training log of the first control run (last 5,000 lines: epochs ≈ 155–199) |
| [`v1_b1.txt`](v1_b1.txt) | MLVC's `train_video.py` | Training log of the first B1 run (last 5,000 lines: epochs ≈ 155–199) |

Logs of later runs are added under their run names (`control.txt`, `b1.txt`, `b1gate.txt`, `b2p25.txt`, `b2p75.txt`, `control_s2.txt`).

## `pipeline.txt`

One line per event, times in the lab PC's local time (UTC+4):

| Line | Meaning |
|---|---|
| `start <time>` | The pipeline was started (`lab.ps1 weekend`) |
| `data ready <time>` | Download and extraction are done |
| `sequences listed N, fully extracted M` | Of the N sequences in the dataset description, M have all 64 frames on disk; only those are used |
| `both at epoch E <time>` / `Queue A at epoch E <time>` | Every run of the queue has finished epoch E (counting from 1); the time between two such lines is one round of 2 epochs per run |
| `<run> FAILED at E` | That run crashed three times in that round |
| `STOPPED: ...` | The pipeline stopped itself (every run crashed, or no usable data) |
| `ALL DONE <time>` | Every planned epoch finished |

The `FAILED` lines of 19 Nov (epochs 2–200 in about an hour) are the first start, when every training start was rejected by a setting MLVC does not support without `torch.compile`; nothing was trained then. The real training starts after `data ready 11/20/2026 21:21:00`.

## `prep.txt`

Output of the data preparation, in order: the parallel download of `OpenVidHD_part_10.zip`, the unzip, the sequence selection (`videos found 10710 sequences kept 5411`) and MLVC's frame extraction. The Python errors in it are the failed attempts of 19–20 Nov: `WinError 2` (ffmpeg not installed) and ffmpeg exit code 2880417800 (= −1414549496, ffmpeg's "option not found": the removed `-vsync`).

## Training logs (`<run>.txt`)

Mostly MLVC's own log lines. Each 2-epoch chunk is a new process, so every chunk starts with a block of setup lines (the full configuration, the model's layers and parameter count, `pretrained weights loaded from ...` or `train state loaded at epoch ...`). Then, every 100 steps:

```
2026-11-21 22:30:20,074 P02616 I: Epoch 191: [1000/1000 (100%)] time: 20.3s, loss: 0.149 (0.092/0.240) | bpp_y: 0.108 (0.082/0.145) | bpp_z: 0.00447 (0.00205/0.00710) | mse: 0.00166 (0.00382/0.00029) | psnr: 30.5 (25.0/36.4) | lr: 0.000010
```

| Field | Meaning |
|---|---|
| `Epoch 191` | Epoch index, counting from 0 (epoch 191 is the 192nd) |
| `[1000/1000]` | Step within the epoch (1,000 steps of 2 samples) |
| `time` | Seconds for these 100 steps |
| `loss` | MLVC's rate–distortion loss over the last 100 steps; in brackets the values at the lowest and highest quality levels (each step trains a random quality level) |
| `bpp_y`, `bpp_z` | Bits per pixel of the latent and of the hyperprior; their sum is the bitrate |
| `mse`, `psnr` | Distortion of the decoded frames (PSNR in dB) |
| `lr` | Learning rate (constant 1·10⁻⁵) |
| `checkpoint at epoch N saved` | The weights after that epoch were written |
| `Unable to get AzureML/MLflow run context` | Harmless: MLVC cannot report to Microsoft's AzureML service, which is not used |

All numbers are on **training** samples, not the test clips.
