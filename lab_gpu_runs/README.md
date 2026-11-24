# Lab GPU Runs: changing the MLVC network

This folder holds DuplexNVC's **network-level** experiments: small changes to MLVC's neural network, made by fine-tuning MLVC on a GPU in the university lab, then tested on the M4 Pro Mac like everything else in this repository.

## Why

The baseline found that MLVC **drifts** when encoder and decoder run on different processors: every pairing decodes correctly, but no two processors decode alike, and the difference grows until the next I-frame (worst frames 21–38 dB). Mixing the GPU and the Neural Engine costs 3–7 % in bitrate, the CPU 7–20 % ([`baseline/11_correctness_drift_experiment`](../baseline/11_correctness_drift_experiment/); first seen in [`04_correctness_experiment`](../baseline/04_correctness_experiment/)). The codec-level mechanisms work around this without touching the network. These runs ask whether **changing the network itself**, in ways the MLVC paper never tested, removes the cause.

A changed network has to be retrained, and training needs a CUDA GPU, which the Mac does not have. So the work is split:

- **Lab PC (this folder):** trains the models and records training logs. It produces models, not final results.
- **M4 Pro Mac:** converts every trained model and measures quality on the VCD test clips, drift across NE/GPU/CPU, speed and energy, with the baseline's tools.

## The runs

Every run fine-tunes MLVC from its released PSNR checkpoint (`mlvc-psnr-v1.ckpt`) on the same data with the same settings and changes **one** thing.

| Run | Name | What changes | What we expect, and why |
|---|---|---|---|
| 1 | `control` | Nothing | The reference. Fine-tuning alone changes a model slightly, so each change is compared with a control trained the same way, not with the released model |
| 2 | `b1` | The decoder memory's functions become piecewise-linear: `hard_tanh` for the memory, `hard_sigmoid` for the gates (options already in MLVC's code) | **Less drift.** Smooth functions (tanh, sigmoid) are computed slightly differently on the NE, GPU and CPU, and the memory carries those differences from frame to frame. Straight-line pieces are computed the same way everywhere |
| 3 | `b1gate` | B1 plus a **separate input gate** (added by [`scripts/patch_input_gate.py`](scripts/)) | MLVC's memory has one knob, `m = f·m + (1 − f)·s`. With an input gate, `m = f·m + i·s` as in a standard LSTM, so keeping the old state and adding new information are controlled separately. This may control drift better than B1 alone |
| 4 | `b2p25` | I-frame dropout 0.25 instead of 0.5 | How often training runs without an I-frame decides how the P-frame model copes without a key frame: affects recovery after packet loss and long-term references |
| 5 | `b2p75` | I-frame dropout 0.75 | The other side of the same trade-off |
| 7 | `control_s2` | Control with other random seeds | **Training noise.** A change counts only if its effect is larger than the difference between two identical controls |
| 6 | `b1` continued | B1 trained twice as long (epochs 200–399) | Does B1's small quality cost shrink with more training? |

`v1_control` and `v1_b1` are the first runs of 1 and 2. They replayed the same training samples in every 2-epoch chunk (explained below and in [`results/`](results/)), so they are kept for reference only; runs 1 and 2 were trained again (Queue A).

## Setup

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3060 Ti, 8 GB, driver 560.94 (CUDA 12.6) |
| Computer | University lab PC, Windows, PowerShell 5.1, no administrator rights |
| Code | [microsoft/mlvc](https://github.com/microsoft/mlvc) `main`, downloaded 19 Nov 2026 (`main` was then commit `f597bf7`) |
| Python / PyTorch | Python 3.12.16, PyTorch 2.10.0+cu128, installed by `uv` 0.13.9 from MLVC's `pyproject.toml` |
| ffmpeg | Portable build N-129130 (19 Nov 2026), installed by the script |
| Starting weights | P-frame model `mlvc-psnr-v1.ckpt`; I-frame model DMCI-6.0 |
| Training data | OpenVidHD part 10 (10,710 videos) with MLVC's own list of 64-frame training sequences: the **5,411** sequences of that list that are in part 10, all extracted |

### Training settings (all runs)

| Setting | Value | Why |
|---|---|---|
| Training patches | 256 × 256 pixels, 4 frames per sequence, batch 2 | Fits the 8 GB GPU (MLVC was trained on 32 GB GPUs) |
| Resolution | Content rescaled to 360p | Our core setting |
| Learning rate | 1·10⁻⁵, constant | Fine-tuning an already trained model; close to the end of MLVC's own schedule |
| Loss | MLVC's rate–distortion loss (`total_rdc_psnr`), cascaded over frames, distortion weights [0.52, 1.33, 0.83] | MLVC's own late-stage settings |
| I-frame dropout | 0.5 (runs 4–5: 0.25 / 0.75) | MLVC's value |
| Length | 200 epochs of 1,000 steps (2,000 samples) per run; a checkpoint every epoch | About 13 hours per run on this GPU |
| Memory and speed | Backprop checkpoints on; `torch.compile` and `flat_parameters` off | Compiling is unreliable on Windows, and MLVC's flat parameters require it |
| Validation during training | Off | The test clips downloaded too slowly in the lab; every model is tested on the Mac instead |
| Scheduling | The runs of a queue take turns, 2 epochs each; every 2-epoch chunk is a new process that resumes from the last checkpoint | All runs of a queue are always equally far along, and a crash loses at most one epoch |
| Random seed | Different for every chunk: `seed = base × 100000 + last epoch of the chunk` | MLVC does not save its random state in checkpoints, so a fixed seed replays the same samples in every chunk (what happened in v1). Runs of a queue share the seed schedule, so they see the same samples in the same order and can be compared pair by pair; `control_s2` uses another base |

### Problems met while setting up, and their fixes

| Problem | Cause | Fix |
|---|---|---|
| Downloads at 100–300 kB/s (the VCD test clips would have taken 43 h) | One slow connection to the storage server | Large files downloaded over 32 connections; VCD not downloaded in the lab |
| Every training start failed within a second | MLVC's `flat_parameters` requires `torch.compile`, which we turn off | `flat_parameters` off |
| Training failed on a missing frame | Frame extraction had failed, but MLVC builds its dataset list from the CSV, not from the files on disk | Only fully extracted sequences are kept; the pipeline stops if there are none |
| Extraction failed (`WinError 2`) | ffmpeg not installed on the lab PC | Portable ffmpeg installed by the script |
| Extraction failed (ffmpeg "option not found") | Current ffmpeg builds removed `-vsync` | MLVC's call changed to `-fps_mode passthrough` |
| First runs saw only ≈ 4,000 different samples | Fixed seed, a restart every 2 epochs, and MLVC not saving its random state | A seed per chunk; control and B1 trained again |

## Results so far

Full analysis: [`results/README.md`](results/README.md).

| Question | Answer |
|---|---|
| What does it cost to fine-tune MLVC? | **0.23 s per step; 4.0 min per epoch; 13.2 h for a 200-epoch run** on one RTX 3060 Ti; data preparation once, about 8 h |
| Does the fix for replayed samples work? | **Yes.** The fixed even/odd gap of the first runs (0.003 in loss) is gone in Queue A |
| What does fine-tuning do to the control? | **Very little.** With fresh samples the control's loss is flat after about 20 epochs (30.2–30.3 dB), so it stays close to the released MLVC. The first runs kept "improving" only by memorising their ≈ 4,000 samples, so they are not used |
| What does B1 cost in quality? | **−0.06 dB PSNR at +0.23 % bitrate** (loss +1.0 %) after 200 epochs, against a control trained on the same samples. B1 starts 3.4 dB worse (new functions under trained weights) and recovers almost all of it; the gap still closes slowly (about 0.03 dB per 100 epochs) |
| Does B1 reduce drift? | To be measured on the Mac |

## Status, including the runs set aside

Lab PC time (+04), from the pipeline log ([`raw_data/README.md`](raw_data/README.md)):

| Step | When | Time | Status |
|---|---|---|---|
| First pipeline start | 19 Nov 2026, 8:32–9:22 pm | 0.8 h | Data downloaded and unpacked (kept). **Every training start then failed:** MLVC's `flat_parameters` needs `torch.compile`, which we turn off. Fixed (`flat_parameters` off); no training happened |
| Fixing the frame extraction | 20 Nov 2026, 1:09–1:30 pm | 0.35 h | Three short restarts: ffmpeg missing, then an option removed from current ffmpeg. Fixed |
| Frame extraction, 5,411 training sequences | 20 Nov 2026, 1:30–9:21 pm | 7.9 h | Done, used by every run |
| First control and B1 runs (`v1_control`, `v1_b1`), 200 epochs each | 20 Nov 2026, 9:21 pm – 21 Nov, 11:40 pm | 26.3 h | **Set aside as models.** A fixed seed with a restart every 2 epochs replayed the same ≈ 4,000 samples in every chunk, so both runs memorised them (see Results). Kept for reference; the seed is now set per chunk and control and B1 were trained again |
| Restart with the fix | 22 Nov 2026, 6:02–6:04 pm | 2 min | Stopped by a script error, fixed |
| **Queue A: control and B1 with a seed per chunk** | 22 Nov 2026, 6:08 pm – 23 Nov, 8:47 pm | 26.7 h | **Done, used**; models in release `models-20261123-2054` |
| Queue B+C: B1 + input gate, I-frame dropout 0.25 and 0.75, control with other seeds | 23 Nov 2026, 8:47 pm – about 26 Nov, 1:00 am | ≈ 53 h | Running |
| Run 6: B1 to 400 epochs | About 26 Nov, 1:00 am – 2:00 pm | ≈ 13 h | Waiting |
| Tests on the Mac (quality on VCD, drift across processors, speed, energy) and choice of the best model for the controller | After each queue | — | — |

Up to Queue A, the lab ran about 62 GPU-hours: about 35 h are in the results, about 27 h were set aside (almost all of it the first control and B1 runs). Not counted: the lab visits to set the PC up, when downloads ran at 100–300 kB/s before the pipeline used 32 parallel connections.

The success criterion is fixed before the Mac tests: a change helps only if it reduces drift by more than the difference between `control` and `control_s2`, at a quality cost on the VCD clips below about 0.2 dB. Earlier checkpoints (epochs 50–150) are tested too, in case later ones over-fit.

## Folder contents

| Folder | What is in it | README |
|---|---|---|
| [`scripts/`](scripts/) | The lab pipeline (`lab.ps1`), the input-gate change to MLVC (`patch_input_gate.py`) and the analysis (`analyze_training.py`) | What each script does, why, when and how to run it |
| [`raw_data/`](raw_data/) | Everything recorded on the lab PC: pipeline, data preparation and training logs | What each log records and how to read it |
| [`results/`](results/) | Tables and figure built from the logs | Every file explained, with the analysis |
| [`REPRODUCE.md`](REPRODUCE.md) | How to rerun the training and rebuild the results | — |

Model checkpoints (about 73 MB each, 200 per run) are too large for this repository; `lab.ps1 upload` publishes selected epochs and the complete logs as a GitHub release.
