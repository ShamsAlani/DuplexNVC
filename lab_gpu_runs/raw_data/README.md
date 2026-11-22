# Raw data

Everything here was recorded on the lab PC by [`../scripts/lab.ps1`](../scripts/) and pushed to GitHub during the runs. Nothing is edited by hand.

| Folder | Contents |
|---|---|
| [`logs/`](logs/) | Pipeline, data-preparation and training logs |

**What is not here, and why.** Model checkpoints (about 73 MB each, one per epoch and run) are too large for a repository; selected epochs are published as a GitHub release by `lab.ps1 upload`. The training logs here are the **last 5,000 lines** of each log, which is what the pipeline pushes during a run; the complete logs, from epoch 0, are in the same release (`logs_full.zip`).

**When it was recorded.**

| Period | What happened |
|---|---|
| 19 Nov 2026, 20:32 – 21:22 | First pipeline start: data downloaded and unzipped; training failed in every round (setting incompatible with Windows, fixed) |
| 20 Nov 2026, 13:09 – 13:30 | Three short restarts while fixing the data preparation (missing ffmpeg, removed ffmpeg option) |
| 20 Nov 2026, 13:30 – 21:21 | Frame extraction of the 5,411 training sequences |
| 20 Nov 2026, 21:21 – 21 Nov 2026, 23:40 | First control and B1 runs (`v1_control`, `v1_b1`), 200 epochs each |
