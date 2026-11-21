# Reproducing Tier B

Two parts: **training** on a Windows PC with an NVIDIA GPU (any CUDA GPU with 8 GB or more), and **rebuilding the tables and figure** from the logs on any computer.

## 1. Rebuild the results from the logs (any computer)

```bash
cd tier_b/scripts
python3 analyze_training.py                 # reads ../raw_data/logs, writes ../results
python3 analyze_training.py /path/to/logs   # or another log folder, e.g. the full logs from the release
```

Needs Python 3.9+ and matplotlib (`pip install matplotlib`); without matplotlib only the CSV files are written.

## 2. Train (Windows PC with an NVIDIA GPU)

No administrator rights are needed. About 150 GB of free disk; the first setup takes about 15 minutes plus about 8 hours of data preparation, then about 13 hours per run.

### One-time setup

1. Copy `scripts/lab.ps1` to the PC (e.g. into Downloads) and open PowerShell there:
   ```powershell
   cd $HOME\Downloads
   powershell -ExecutionPolicy Bypass -File .\lab.ps1 setup
   ```
   Expected: `torch 2.10.0+cu128 cuda True <your GPU>` and `SETUP DONE`.
2. Download the DMCI-6.0 I-frame model (`cvpr2025_image.pth.tar`, from the DCVC release on OneDrive linked in [microsoft/DCVC](https://github.com/microsoft/DCVC)), rename it and move it into place:
   ```powershell
   Move-Item $HOME\Downloads\cvpr2025_image.pth.tar $HOME\mlvc\job-outputs\pretrained\DMCI-6.0.pth.tar
   ```
3. Install ffmpeg (portable) and check it:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\lab.ps1 ffmpeg      # prints "ffmpeg version ..."
   ```
4. Optional, for progress on GitHub: create a fine-grained token with *Contents: read and write* on one repository, then
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\lab.ps1 github <owner>/<repo> "Your Name" your@email
   ```
   If pasting into the hidden prompt fails, write the token directly: `Set-Content $HOME\.gh\token "<token>"`.

### Run everything

```powershell
powershell -ExecutionPolicy Bypass -File .\lab.ps1 weekend
```

This opens a minimized window that runs the whole pipeline. **Do not close it, and lock the PC (Win+L) instead of logging out**; logging out stops it. Avoid clicking inside a PowerShell window while it runs: Windows pauses a console in selection mode ("Select" in the title; press Esc).

The pipeline, in order:

1. Downloads OpenVidHD part 10 (50 GB) from Hugging Face over 32 connections and unzips it.
2. Keeps the 5,411 sequences of MLVC's `openvidhd_60k64_frame_sequences.csv` that are in part 10 and extracts their frames with MLVC's `extract_frame_sequences.py` (about 8 hours), then keeps only fully extracted sequences.
3. Queue A: `control` and `b1`, 200 epochs each, taking turns 2 epochs at a time.
4. Queue B+C: `b1gate`, `b2p25`, `b2p75`, `control_s2`, the same way.
5. Run 6: `b1` continued to 400 epochs.

Every step resumes where it stopped: run `weekend` again after a crash or restart. Each run's settings are in `Write-FtYaml` (shared) and `$PHASES` (per run) in `lab.ps1`; the seed of each 2-epoch chunk is `base × 100000 + last epoch of the chunk`.

Check progress with
```powershell
powershell -ExecutionPolicy Bypass -File .\lab.ps1 status
Get-Content $HOME\mlvc\logs\pipeline.txt -Tail 5
```

### Outputs

| Where | What |
|---|---|
| `$HOME\mlvc\job-outputs\checkpoints\<run>\model_epo<N>.ckpt` | Model weights after epoch N (0-based: `model_epo199.ckpt` is the 200th epoch) |
| `$HOME\mlvc\job-outputs\checkpoints\<run>\optimizer_epo<N>.ckpt` | Optimizer state, used to resume |
| `$HOME\mlvc\logs\<run>.txt` | Training log of each run: loss, bpp, PSNR and time every 100 steps |
| `$HOME\mlvc\logs\pipeline.txt`, `prep.txt`, `patch.txt` | Pipeline steps, data preparation, source patches |

To publish selected checkpoints and the full logs as a GitHub release: `powershell -ExecutionPolicy Bypass -File .\lab.ps1 upload`.

### Running a single run by hand

From `$HOME\mlvc\code\video`, with the same settings file the pipeline writes (`$HOME\mlvc\ft.yaml`):

```powershell
uv run --no-sync train_video.py --config configs/train_video-mlvc.yaml `
  --data_mount $HOME\mlvc --checkpoints_mount $HOME\mlvc\job-outputs --save_dir checkpoints/b1 `
  --overrides_file $HOME\mlvc\ft.yaml `
  --overrides "{train.n_epoch: 2, train.dataset.batch_size: 2, model.p_frame.memory_activation: hard_tanh, model.p_frame.gate_activation: hard_sigmoid, seed: 2}"
```

Increase `train.n_epoch` by 2 and the seed accordingly for each following chunk, as the pipeline does.

## 3. Test the models (Mac)

Trained checkpoints are converted and measured on the M4 Pro Mac with the baseline's tools (see [`../baseline/REPRODUCE.md`](../baseline/REPRODUCE.md)): quality on the VCD clips, drift across NE/GPU/CPU, speed and energy. Those steps are added here when the tests are run.
