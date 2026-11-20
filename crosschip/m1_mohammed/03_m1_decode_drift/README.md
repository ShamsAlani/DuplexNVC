# 03 — Cross-chip decode: does an M4 Pro → M1 call drift? (Day 3)

**Question.** When the encoder runs on Shams's M4 Pro and the decoder on the M1 (a real call between the two laptops), does the M1's NE decode the same pictures as the M4 Pro's NE? And are the two chips' encoders bit-exact for the same input and settings?

**What is run.** `m1_decode`: Shams's B\* bitstream (`T_duplex30_r1/outgoing.mlvc`, 1,802 frames) decoded on the M1 with `mlvc decode` on the NE twice, the GPU and the CPU; drift (Y-PSNR between decodes, grouped by position after the I-frame, as in `baseline/04_correctness_experiment`) of M4-NE vs M1-NE, M4-NE vs M1-GPU/CPU, M1-NE vs M1-GPU/CPU; M1 NE determinism; the M1's own Day 2 stream decoded the same way; `au_cmp.py` on the two `outgoing.aus` files.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_decode` | The decodes, drift tables, bitstream comparison, files for Shams | 15 min | any; needs `from_m4/m4_outgoing.mlvc`, `m4_outgoing.aus`, `m4_dec_npu.nv12` and the Day 2 run |

## Files

| Path | Contents |
|---|---|
| `results/M1_drift.csv` | `pair, frames_after_I, mean_dB, min_dB`; pairs `M4NE_vs_M1NE`, `M4NE_vs_M1GPU`, `M4NE_vs_M1CPU`, `M4stream_M1NE_vs_M1GPU`, `M4stream_M1NE_vs_M1CPU`, `M1stream_M1NE_vs_M1GPU`, `M1stream_M1NE_vs_M1CPU` |
| `results/M1_encoder_vs_M4.txt` | Access units identical / first difference / sizes |
| `raw_data/m1_decode/*.log` | The `mlvc decode` logs (the decoded videos are too large to ship) |
| `raw_data/logs/out_m1_decode.txt` | Console output |

## Results

*(fill in on Day 3)*

| Pair | mean dB | worst frame dB | bit-identical frames |
|---|---|---|---|
| M4 NE vs M1 NE (cross-chip) | … | … | … |
| M1 NE vs M1 GPU | … | … | … |
| M1 NE vs M1 CPU | … | … | … |

Encoders bit-exact across chips: yes/no (first difference at access unit …).

M4 Pro reference (same chip): NE vs GPU 52.13 / 38.46; NE vs CPU 48.78 / 39.51 (mean / min dB).

## Conclusion

*(does a cross-chip call need a drift bound (A2), and which; what Shams found in the reverse direction)*
