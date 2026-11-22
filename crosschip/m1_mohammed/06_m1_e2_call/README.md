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
| `raw_data/m1_call/M1_call_<label>/run.txt` | Settings, peer, frames sent / received / lost (lost includes the frames that arrived incomplete), decode failures, median round trip and offset |
| `results/M1_call_<label>_summary.json` | Send and receive statistics, network and end-to-end delay percentiles, loss |
| `raw_data/logs/out_m1_call_build.txt`, `out_m1_call.txt` | Console output |

(`received.mlvc` and `outgoing.mlvc` stay on the laptop; they are too large to ship.)

## Tested before the Mac

On 22 Nov the call program was built in a Linux container against a fake codec (same interface as libmlvc) and run as two endpoints over 127.0.0.1 for 6 s: both sides sent and received 182 of 182 frames, round trip 0.09 ms, clock offset 0.01 ms, and both ended on the peer's hang-up message. With 3 % of the packets dropped on purpose, the receiver decoded 164 frames and counted 18 lost, and 164 + 18 = 182 sent: the loss accounting is exact. That test also fixed two bugs before any Mac run: the first key frame used the same number as the hang-up message (every call would have ended at once), and frames the sender drops on purpose were counted as network losses (frames are now numbered by sequence, not by camera slot). The first real loopback on the M1 (22 Nov, 17:08) then worked (584 and 583 frames sent, all received, none lost, no decode failure) but showed a 16 ms round trip over localhost: one thread both received and decoded, so packets waited in the socket during each 34 ms decode and were stamped late. The receiver now has two threads, one that reads and stamps packets on arrival and one that decodes. Re-tested with a fake decoder slower than the frame rate (encode 34 ms, decode 36 ms): the old program reported a 451 ms round trip and 290 ms of network time, the new one 0.12 ms and 0.08 ms, with the backlog correctly shown as waiting for the decoder (complete-to-decoded p99 488 ms); end-to-end delay is the same in both (325 ms). Not tested there: the real codec, and Wi-Fi.

## Results

*(fill in on Days 9, 11, 15)*

| Call | Sent / received / lost | Round trip ms | End-to-end p50 / p99 ms | Late % send / receive | Decode failures |
|---|---|---|---|---|---|
| Loopback 1 (M1 alone, old receiver), 22 Nov 17:08 | 584 / 583 / 0 and 583 / 584 / 0 | 16.5 (inflated, see above) | 43.0 / 43.7 | 100 / 98 % (expected) | 0 |
| **Loopback 2 (M1 alone, fixed receiver), 22 Nov 17:16** | 582 / 583 / 0 and 583 / 582 / 0 | **2.9** | 41.2 / 42.9 | 100 / 99 % (expected) | 0 |
| Shams's M4 Pro ↔ M1, B\*, r1–r3 | … | … | … | … | … |
| Warda's M4 ↔ M1, B\*, r1–r3 | … | … | … | … | … |
| With the controller / Tier B winner | … | … | … | … | … |

Loopback reading: both endpoints run on the M1, so four networks (two encoders, two decoders) share one Neural Engine. Each encode and decode took about 34.5 ms, above the 33.3 ms frame time, so nearly every frame is late and the camera rule dropped 19–20 frames per side (about 3 %); that is expected and is not what the loopback tests. What it tests passed: every frame sent arrived and decoded, none lost, no decode failure, both ends saw the other hang up. With the fixed receiver the network time is 1.5–1.75 ms mean (thread wake-up on a fully loaded Mac; no Wi-Fi involved) and the round trip 2.9 ms.

Offline drift of `received.mlvc` (decoded on the M1 NE vs the sender's NE decode): …

## Conclusion

*(the call works between different chips; delay budget; whether cross-chip drift shows up in a real call)*
