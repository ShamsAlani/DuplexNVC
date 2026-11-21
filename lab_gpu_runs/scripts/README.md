# Scripts

Three scripts: one runs everything on the lab PC, one adds the input gate to MLVC, one turns the logs into results.

| Script | Runs on | When | Purpose |
|---|---|---|---|
| [`lab.ps1`](lab.ps1) | Lab PC (Windows, PowerShell) | Every lab visit | Installs everything, prepares the data, trains every run, pushes progress, uploads models |
| [`patch_input_gate.py`](patch_input_gate.py) | Lab PC (called by `lab.ps1`) | Automatically, at every start | Adds an optional separate input gate to MLVC's decoder memory (run 3) |
| [`analyze_training.py`](analyze_training.py) | Any computer | After a run | Builds the tables and figure in [`../results/`](../results/) from the logs in [`../raw_data/logs/`](../raw_data/logs/) |

## `lab.ps1`: the lab pipeline

**Why one script.** The lab PC is shared, has no administrator rights and is visited only for short stretches. Everything needed, from installation to the last training run, is therefore one script that can be started in a minute, runs unattended for days, resumes after any interruption and reports its progress to GitHub, so it can be followed without being in the lab.

**How to run it.** In PowerShell, from the folder that holds the script:

```powershell
powershell -ExecutionPolicy Bypass -File .\lab.ps1 <command>
```

| Command | What it does | When |
|---|---|---|
| `setup` | Installs `uv`; downloads MLVC (as a zip if `git` is missing); installs MLVC's Python environment; checks that PyTorch sees the GPU; downloads the starting checkpoint `mlvc-psnr-v1.ckpt` and MLVC's list of training sequences | Once |
| `ffmpeg` | Downloads a portable ffmpeg (no administrator rights needed) and prints its version | Once; also done automatically |
| `github <owner>/<repo> "Name" email` | Stores a GitHub token so the pipeline can push its progress | Once |
| `weekend` | Starts the whole pipeline in its own minimized window (below) | Every visit |
| `status` | GPU use, free disk, last lines of every log | Any time |
| `upload` | Publishes checkpoints of epochs 10, 25, 50, 100, 150, 200, 300 and 400 of every run (model weights only, about 73 MB each) and the complete logs as a GitHub release | After a queue |
| `push` | Pushes the logs to GitHub now | When needed |
| `fixdata` | Rebuilds the list of usable training sequences | When needed |
| `smoke` | Validates the released model on the VCD clips (needs the VCD download, which was skipped in the lab) | Not used |

**What `weekend` does, in order.** Every step checks whether it is already done, so running `weekend` again simply continues.

1. **Keeps the PC awake** while its window is open (Windows `SetThreadExecutionState`).
2. **Downloads OpenVidHD part 10** (50 GB) from Hugging Face over 32 parallel connections (a single connection to the storage servers ran at 100–300 kB/s), and unzips it.
3. **Selects and extracts the training sequences.** Keeps the 5,411 sequences of MLVC's `openvidhd_60k64_frame_sequences.csv` that come from the downloaded videos, extracts their frames with MLVC's `extract_frame_sequences.py` (about 8 hours), builds MLVC's dataset description, and keeps only sequences whose 64 frames all exist.
4. **Writes the shared training settings** (`ft.yaml`, see the main README).
5. **Queue A:** `control` and `b1`, 200 epochs each, taking turns 2 epochs at a time.
6. **Queue B+C:** `b1gate`, `b2p25`, `b2p75`, `control_s2`, the same way.
7. **Run 6:** `b1` continued from epoch 200 to 400.
8. After every round it writes a line to `pipeline.txt` and pushes the logs to GitHub.

**Safeguards.** A run that crashes is retried with a smaller batch; if every run of a round crashes, the pipeline stops and pushes a `STOPPED` message instead of looping. The first runs of `control` and `b1` are moved to `v1_control` and `v1_b1` before they are trained again, so nothing is overwritten.

**Changes it makes to its copy of MLVC** (on every start, only if not yet applied):
- `-vsync 0` → `-fps_mode passthrough` in MLVC's ffmpeg call: current ffmpeg builds removed `-vsync`, which made every extraction fail.
- The input gate, by running `patch_input_gate.py` (inactive unless a run turns it on).

## `patch_input_gate.py`: the input gate

**What it changes.** MLVC's decoder (model `DMC-6.1sb`) keeps a memory between frames. Its last layer produces three parts: a new state `s`, a forget gate `f` and an output gate `o`, and the memory is updated as `m = f·m + (1 − f)·s`. With the option `model.p_frame.input_gate: true`, the layer produces a fourth part, an input gate `i`, and the update becomes `m = f·m + i·s`.

**Edits** (in `src/models/dmc_6/dmc_61sb.py` and `src/utils/model_factory.py`):
- a new option `input_gate`, off by default, so every other run is unchanged;
- the decoder's last convolution outputs 4 instead of 3 groups of channels when it is on;
- when a checkpoint without the input gate is loaded, the new channels are set to the **negated forget-gate weights**. Because `hard_sigmoid(−x) = 1 − hard_sigmoid(x)`, the model then starts **exactly equal** to the loaded one, and training learns to separate the two gates.

**Checked before use** (on a copy of MLVC): the patched model loads the released weights; its outputs match the unpatched model to 10⁻⁷ over five frames; the input-gate channels receive gradients; its own checkpoints reload; the patch works with Windows line endings and can be applied more than once.

**Run by hand:** `python patch_input_gate.py <path to mlvc/video>`.

## `analyze_training.py`: from logs to results

**What it reads.** The training log of each run (`<run>.txt`: one line every 100 steps with loss, bpp, PSNR and time) and `pipeline.txt` (the time of every round).

**What it writes** to [`../results/`](../results/): per-epoch means, a comparison of each run with its control, an even/odd-epoch and trend table, the training cost, and a figure. Each file is described in the results README.

**How it computes.** A step's numbers are averaged over the 10 log lines of an epoch; an epoch counts only if all 10 are present. Each run is compared with the control trained the same way (`v1_b1` with `v1_control`, later runs with `control`), over the epochs both have. The training cost uses only rounds in which no run failed.

**Run:**
```bash
python3 analyze_training.py                  # logs in ../raw_data/logs
python3 analyze_training.py /path/to/logs    # e.g. the complete logs from the release
```
Needs Python 3.9 or later; matplotlib for the figure (`pip install matplotlib`).
