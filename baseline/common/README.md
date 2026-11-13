# common/

Everything shared by the nine experiments.

| Folder | Contents |
|---|---|
| [`code/`](code/) | The measurement program `duplex_bench.cpp` (C++17 on `libmlvc`) and the analysis tools: `analyze_run.py` (timing, latency, speedup, κ, energy), `quality_tools.py` (PSNR, drift, BD-rate), `face_metrics.py` and `facebox.swift` (display-scale and face quality), `mlplan.swift` (placement trace), `thermal_log.swift` (thermal state) |
| [`scripts/`](scripts/) | Shared settings (`v`, `s2cfg`), build (`b`), stream preparation (`m`), quiet mode on/off (`p`, `u`), helpers, and the install command for every experiment's scripts |
| [`analysis/`](analysis/) | Rebuild every result from the raw data: `recompute_all.py` (tables of experiments 01–06), `make_figures.py` (their figures), `make_tables_x3.py` (tables of experiment 09); `summary_baseline.json` holds the headline numbers |
| [`setup/`](setup/) | Logs of the one-time setup: build check, quiet-mode check, stream preparation, the full setup and model-conversion terminal log, and the pinned `libmlvc` commit (`eb5d60a`) |

## Rebuilding the results

Needs Python 3 and matplotlib only:

```bash
cd baseline/common/analysis
python3 recompute_all.py        # tables of 01–06, written into each experiment's results/
python3 make_figures.py         # figures of 03–06, written next to their tables
python3 make_tables_x3.py       # tables of 09 from its console logs
```

`recompute_all.py` ends with:
```
== headline: {"E1_t_enc_ms": 5.86, "E1_t_dec_ms": 5.94, "T_turns_ms": 11.81, "T_shared_ms": 10.68, "S": 1.11, "S_max": 1.99, "kappa_enc": 1.82, "kappa_dec": 1.8, "E3a_S": 1.15, "energy_mJ_per_pair": 65.32}
```
