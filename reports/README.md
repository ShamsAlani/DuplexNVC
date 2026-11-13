# reports/

The reports of the project, in their latest versions.

| File | Pages | What it is |
|---|---|---|
| `DuplexNVC_Literature_Review.pdf` | 7 | **Literature review, research gap and proposed innovation** (IEEE format). Reviews 25 peer-reviewed studies (2021–2026) in six methodological groups, compares the DCVC family on a common anchor, and identifies the gap: no learned codec has been run full duplex on a consumer device, and the effect of placing its parts on the CPU, GPU and NPU on throughput, latency, energy and decoding correctness is unknown. Proposes DuplexNVC, an energy-aware scheduler that pipelines both call directions across an Apple Silicon laptop's CPU, GPU and Neural Engine |
| `DuplexNVC_Survey.pdf` | 50 | **Survey and proposed research direction** (ACM format). Reviews 62 studies (2018–2026) in three parts: video codecs from the classical hybrid loop to MLVC together with systems that spread neural networks over a chip's processors; studies that measure and save the energy of video coding; and content- and face-aware coding. Concludes that every capability a full-duplex call needs exists somewhere but never together, and proposes DuplexNVC |
| `DuplexNVC_Phase2_Baseline_Report.pdf` | 38 | **Phase 2 baseline report** (ACM format), as submitted. Covers all nine experiments of the baseline ([`../baseline/`](../baseline/)), from the core baseline B\* to the placement experiment: method, every metric with its equation, quiet mode, all results tables and figures, the table of feasible settings, the latency–quality–energy balance, the data planned for the controller study, and the plan for the next phase |

## How the baseline report maps to this repository

| Report section | Repository |
|---|---|
| Measurement program, analysis, reproducibility, scripts table | `baseline/common/`, `baseline/REPRODUCE.md` |
| Smoke tests (S1, S2) | `baseline/01_smoke_test_experiment/` |
| Check of Phase 1 (E3a) | `baseline/02_phase1_check_experiment/` |
| E1, E2, E3/E4, B\* | `baseline/03_timing_experiment/` |
| E5: correctness and drift | `baseline/04_correctness_experiment/` |
| E6: compression quality | `baseline/05_quality_experiment/` |
| E7: energy | `baseline/06_energy_experiment/` |
| X1: placement trace, processors alone | `baseline/07_processor_experiment/` |
| X2: new models and inputs | `baseline/08_model_conversion_experiment/` |
| X3: table of feasible settings, 720p question, latency–quality–energy balance | `baseline/09_placement_experiment/` |
