# Raw data

Everything here was recorded on the lab PC by [`../scripts/lab.ps1`](../scripts/) and pushed to GitHub during the runs. Nothing is edited by hand.

| Folder | Contents |
|---|---|
| [`logs/`](logs/) | Pipeline, data-preparation and training logs |

**What is not here, and why.** Model checkpoints (about 73 MB each, one per epoch and run) are too large for a repository; selected epochs are published as GitHub releases by `lab.ps1 upload` (`models-20261122-1813`: v1; `models-20261123-2054`: Queue A control and B1). The training logs here are **complete** (every epoch from 0), compressed with gzip; [`logs/README.md`](logs/README.md) explains where each comes from.

**When it was recorded.**

| Period | What happened |
|---|---|
| 19 Nov 2026, 20:32 – 21:22 | First pipeline start: data downloaded and unzipped; training failed in every round (setting incompatible with Windows, fixed) |
| 20 Nov 2026, 13:09 – 13:30 | Three short restarts while fixing the data preparation (missing ffmpeg, removed ffmpeg option) |
| 20 Nov 2026, 13:30 – 21:21 | Frame extraction of the 5,411 training sequences |
| 20 Nov 2026, 21:21 – 21 Nov 2026, 23:40 | First control and B1 runs (`v1_control`, `v1_b1`), 200 epochs each |
| 22 Nov 2026, 18:02 – 18:04 | Restart stopped by a script error (fixed) |
| 22 Nov 2026, 18:08 – 23 Nov 2026, 20:47 | Queue A: `control`, `b1`, 200 epochs each, a seed per chunk |
| From 23 Nov 2026, 20:47 | Queue B+C running (`b1gate`, `b2p25`, `b2p75`, `control_s2`) |
