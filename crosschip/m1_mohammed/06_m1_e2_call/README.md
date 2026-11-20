# 06 — E2: a real call between two laptops (Days 9, 11, 15)

**Question.** Do the offline results hold in a real call between two different chips: end-to-end delay, late and lost frames, and the cross-chip drift measured offline on Day 3?

**What is run.** `duplex_call.cpp`: one endpoint of the call, built from `duplex_bench.cpp`. Each laptop encodes its clip paced at 30 fps on its NE, sends every access unit to the other laptop over UDP (fragments of at most `--mtu` bytes, default 1200), receives the other laptop's access units, reassembles and decodes them on its NE. Every packet carries a send time and echoes the last time stamp received, so each side measures the round trip and the clock offset (NTP-style) and `call_sum.py` corrects one-way delays with the median offset. Lost and incomplete frames are counted; a frame after a gap still goes to the decoder, so the log shows the decoder's own recovery (failures until the next I-frame). The received bitstream is saved for an offline decode and drift check with the Day 3 method.

Calls: Day 9 loopback on the M1 and a first call with Shams; Day 11 three 60 s calls Shams's M4 Pro ↔ M1 with B\* (and with the controller when Shams has it); Day 15 Warda's M4 ↔ M1 and the Tier B winner.

## How to run

| Script | What | Time | Conditions |
|---|---|---|---|
| `scripts/m1_call_build` | Build the call program in `$WORK/callharness` | 2 min | any |
| `scripts/m1_call loopback` | Two endpoints on one Mac over 127.0.0.1, 20 s | 1 min | any |
| `scripts/m1_call <label> <peer-ip> [seconds]` | A real call; the same command on both laptops within one minute | 1–2 min per call | Wi-Fi on, same network, charger in |
| `scripts/call_sum.py <run> <tools>` | Summary of one run (called by `m1_call`) | — | — |

## Files

| Path | Contents |
|---|---|
| `raw_data/m1_call/M1_call_<label>/frames.csv` | E rows: sent frames (due, encoded, sent); D rows: received frames (complete, decoded); plus `pkts, send_us, first_recv_us, complete_recv_us, lost_before` |
| `raw_data/m1_call/M1_call_<label>/clock.csv` | Round trip and clock offset over the call |
| `raw_data/m1_call/M1_call_<label>/run.txt` | Settings, peer, frames sent / received / lost / incomplete, decode failures, median round trip and offset |
| `results/M1_call_<label>_summary.json` | Send and receive statistics, network and end-to-end delay percentiles, loss |
| `raw_data/logs/out_m1_call_build.txt`, `out_m1_call.txt` | Console output |

(`received.mlvc` and `outgoing.mlvc` stay on the laptop; they are too large to ship.)

## Results

*(fill in on Days 9, 11, 15)*

| Call | Sent / received / lost | Round trip ms | End-to-end p50 / p99 ms | Late % send / receive | Decode failures |
|---|---|---|---|---|---|
| Loopback (M1 alone) | … | … | … | … | … |
| Shams's M4 Pro ↔ M1, B\*, r1–r3 | … | … | … | … | … |
| Warda's M4 ↔ M1, B\*, r1–r3 | … | … | … | … | … |
| With the controller / Tier B winner | … | … | … | … | … |

Offline drift of `received.mlvc` (decoded on the M1 NE vs the sender's NE decode): …

## Conclusion

*(the call works between different chips; delay budget; whether cross-chip drift shows up in a real call)*
