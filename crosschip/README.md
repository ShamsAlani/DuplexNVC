# crosschip/

The cross-chip study of the plan to 3 December: the key baseline measurements repeated on other Apple Silicon chips and compared with the M4 Pro baseline in [`../baseline/`](../baseline/), plus the real two-laptop call (E2).

| Folder | Chip | Owner | Contents |
|---|---|---|---|
| [`m1_mohammed/`](m1_mohammed/) | M1 | Mohammed Alawadhi | Setup, timing, decode drift, contention, energy (Days 1–5) and the E2 call program and runs. Every run, file and table is prefixed `M1_`. Step-by-step guide in its README |

Each step folder has the baseline's layout: `scripts/`, `raw_data/` (run records and console logs, no video), `results/` (tables) and a README with the question, what was run, the files and the results.

## Status

| Chip | Done | Headline so far |
|---|---|---|
| M1 (MacBook Air, 8 GB) | Days 1–5: setup, timing, decode drift, contention, energy (20–22 Nov) | 1.62× slower and 1.86× more energy per frame pair than the M4 Pro; the Neural Engine shares the two networks exactly as poorly (S = 1.11 on both chips) and memory bandwidth explains only 19 % of slowdown; the baseline B\* misses 30 fps on the M1 (4–7 % late sends), but taking turns or a light background load that keeps the clocks up brings it to 0 %; **no cross-chip drift**: both chips encode to identical bitstreams and decode on the NE to identical pictures |
