# crosschip/

The cross-chip study of the plan to 3 December: the key baseline measurements repeated on other Apple Silicon chips and compared with the M4 Pro baseline in [`../baseline/`](../baseline/), plus the real two-laptop call (E2).

| Folder | Chip | Owner | Contents |
|---|---|---|---|
| [`m1_mohammed/`](m1_mohammed/) | M1 | Mohammed Alawadhi | Setup, timing, decode drift, contention, energy (Days 1–5) and the E2 call program and runs. Every run, file and table is prefixed `M1_`. Step-by-step guide in its README |
| [`m4max_warda/`](m4max_warda/) | M4 Max | Warda | Generational comparison on a MacBook Pro 16-inch M4 Max: B\* (timing, sharing, 30 fps call, energy) and each network alone at all 7 settings, against the M4 Pro, the M3 Pro (paper) and the M1 |

Each step folder has the baseline's layout: `scripts/`, `raw_data/` (run records and console logs, no video), `results/` (tables) and a README with the question, what was run, the files and the results.

## Status

| Chip | Done | Headline so far |
|---|---|---|
| M4 Max (MacBook Pro 16-inch, 64 GB) | Generational comparison (27 Nov) | **Same speed as the M4 Pro** despite 2× memory bandwidth and 2× GPU cores: every network within 2.3 %, S = 1.11, 0 % late at 30 fps, 64.7 vs 65.3 mJ per frame pair. The Neural Engine alone sets MLVC's speed; the M4 generation is 1.3–1.5× faster than the M3 Pro and 1.6× faster than the M1 |
| M1 (MacBook Air, 8 GB) | Days 1–5: setup, timing, decode drift, contention, energy (20–22 Nov) | 1.62× slower and 1.86× more energy per frame pair than the M4 Pro; the Neural Engine shares the two networks exactly as poorly (S = 1.11 on both chips) and memory bandwidth explains only 19 % of slowdown; the baseline B\* misses 30 fps on the M1 (4–7 % late sends), but taking turns or a light background load that keeps the clocks up brings it to 0 %; **no cross-chip drift**: both chips encode to identical bitstreams and decode on the NE to identical pictures |
