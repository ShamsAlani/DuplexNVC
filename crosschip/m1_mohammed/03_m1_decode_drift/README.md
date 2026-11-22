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
| `results/M1_decode_vs_M4.txt` | SHA-256 of the M1 NE decode of her stream against hers, and the verdict |
| `raw_data/m1_decode/*.log` | The `mlvc decode` logs (the decoded videos are too large to ship) |
| `raw_data/logs/out_m1_decode.txt` | Console output |

## Results

**Run:** Sun 22 Nov 2026, 16:31–16:39 (+04), MacBook Air M1, 8 GB, macOS 27.2.1; Shams's files from her M4 Pro (macOS 26.6), B\* run `runs/bl_bstar/T_duplex30_r1`: `m4_outgoing.mlvc` (895,964 bytes, 1,802 frames, 119 kbps), `m4_outgoing.aus` (1,802 access units, contents identical to the `.mlvc`) and `m4_hashes.txt` (SHA-256 of her NE decode `dec_npu.nv12` and of her full MLVC bundle). Her 623 MB `dec_npu.nv12` itself was not needed: the fingerprints match (below).

**1. Cross-chip NE decode: bit-identical.** Her M4 Pro bitstream decoded on the M1's Neural Engine gives exactly her NE decode:

```
M1 NE decode of her stream: 0f8cf98d052a57e4301553827b418c69782632289dc12ce85ad71f2ea0a47f40
her M4 Pro NE decode:       0f8cf98d052a57e4301553827b418c69782632289dc12ce85ad71f2ea0a47f40
```

All 1,802 frames, every byte. Drift M4 NE → M1 NE: **none**.

**2. Cross-chip encoding: bit-identical.** The M1's own B\* bitstream (Day 2, `M1_duplex30_r1`, same clips, QP 26, I-frame period 64) equals hers access unit by access unit: 1,802 of 1,802 identical, 895,964 bytes on both chips (`results/M1_encoder_vs_M4.txt`). This also shows that the full MLVC bundle converted on the M1 and Shams's bundle are the same model in effect: their `.tar` fingerprints differ (`d241a006…` vs `9a6ed5fe…`, both 37,048,320 bytes), which is packaging (archive metadata), not weights.

**3. The M1 NE decode is deterministic** (two NE decodes identical), and every decode, on NE, GPU and CPU, completed all 1,802 frames with no failure.

**4. Decoding on another processor of the M1 drifts exactly as on the M4 Pro.** Y-PSNR between the M1 NE decode and the M1 GPU or CPU decode of the same stream, mean / worst frame (dB):

| Frames after the I-frame | M1: NE vs GPU | M4 Pro: NE vs GPU | M1: NE vs CPU | M4 Pro: NE vs CPU |
|---|---|---|---|---|
| 0 | 60.58 / 59.60 | 60.58 / 59.58 | 52.64 / 51.39 | 52.64 / 51.39 |
| 1–15 | 57.62 / 52.07 | 57.63 / 51.90 | 51.74 / 48.92 | 51.74 / 48.92 |
| 16–31 | 52.86 / 42.84 | 52.86 / 42.73 | 49.63 / 44.70 | 49.63 / 44.70 |
| 32–47 | 49.94 / 39.65 | 49.93 / 39.52 | 47.57 / 40.42 | 47.57 / 40.42 |
| 48–63 | 47.81 / 38.51 | 47.80 / 38.46 | 46.07 / 39.51 | 46.07 / 39.51 |
| All | **52.13 / 38.51** | **52.13 / 38.46** | **48.78 / 39.51** | **48.78 / 39.51** |

The CPU rows equal the M4 Pro's in every value, so with the NE decodes identical, the CPU decodes are almost certainly identical across the two chips too. The GPU rows differ in the second decimal (worst frame 38.51 vs 38.46 dB): the two GPU generations round slightly differently. The M1's own stream gives the same table as hers, as it must, since the two bitstreams are identical.

**Reverse direction (M1 → M4).** Because the M1's bitstream equals the M4 Pro's and both NE decoders give the same pictures, the reverse direction is the same comparison; the files in `to_m4/` do not need to be sent.

**Scope.** One stream and one setting (full MLVC 360p, QP 26, B\* clips), two chips (M1, M4 Pro) on two macOS versions (27.2.1, 26.6). MLVC-S and other resolutions were not tested across chips.

## Conclusion

**An M4 Pro → M1 call does not drift.** With both networks on the Neural Engine, the two chips encode to identical bitstreams and decode to identical pictures, across two chip generations and two macOS versions. Cross-chip calls therefore need no drift bound as long as both sides decode on the NE; drift appears only when a decoder runs on the GPU or CPU, and then it is the same on both chips (the CPU exactly, the GPU to 0.1 dB). For A2 and the controller, the other laptop's chip is not a drift input for NE–NE placements; the decoder's processor is. MLVC's goal of identical decoding across devices holds here across Apple generations.
