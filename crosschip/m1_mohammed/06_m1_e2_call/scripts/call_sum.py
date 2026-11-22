#!/usr/bin/env python3
"""Summary of one E2 call run (duplex_call): frames sent and received, loss, delay, late frames, bitrate.

  python3 call_sum.py <run dir> <tools dir>

Delays: encode-to-decode delay of each received frame = (decode end on this Mac) - (peer's send time), corrected by
the median clock offset measured in-band (clock.csv); also arrival-to-decoded time and the network time alone
(complete arrival - send), both offset-corrected. Writes <run dir>/summary.json.
"""
import csv, json, os, statistics as st, sys

run, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
import analyze_run as A  # noqa: E402

meta, rows = A.load(run)
t0 = float(meta["t0_epoch_ms"])
E = A.direction_summary(meta, rows, "E")
D = A.direction_summary(meta, rows, "D")
off = float(meta.get("clock_offset_ms_median", "nan"))  # peer clock - my clock
rtt = float(meta.get("rtt_ms_median", "nan"))
rx = [r for r in rows if r["dir"] == "D" and not r["warmup"]]
net, e2e, reass, pkts = [], [], [], []
for r in rx:
    try:
        send = float(r["send_us"]) / 1000.0 - off          # peer send time, in my clock, epoch ms
        first = float(r["first_recv_us"]) / 1000.0
        done = float(r["complete_recv_us"]) / 1000.0
        dec_end = t0 + r["end_ms"]
        if send > 0 and first > 0:
            net.append(done - send); e2e.append(dec_end - send); reass.append(done - first); pkts.append(int(r["pkts"]))
    except (KeyError, ValueError):
        pass
summary = {
    "sent_frames": int(meta.get("frames_sent", 0)), "received_frames": int(meta.get("frames_received", 0)),
    "lost_frames": int(meta.get("frames_lost", 0)), "incomplete_frames": int(meta.get("frames_incomplete", 0)),
    "decode_failures": int(meta.get("decoder_failures", 0)), "encoder_dropped": int(meta.get("encoder_dropped", 0)),
    "rtt_ms_median": rtt, "clock_offset_ms_median": off, "peer_bye_seen": meta.get("peer_bye_seen"),
    "send": E, "recv": D,
}
if net:
    summary["network_ms"] = {"mean": st.mean(net), "p50": A.pct(net, 50), "p95": A.pct(net, 95), "p99": A.pct(net, 99)}
    summary["send_to_decoded_ms"] = {"mean": st.mean(e2e), "p50": A.pct(e2e, 50), "p95": A.pct(e2e, 95), "p99": A.pct(e2e, 99)}
    summary["reassembly_ms"] = {"mean": st.mean(reass), "p99": A.pct(reass, 99)}
    summary["packets_per_frame_mean"] = st.mean(pkts)
json.dump(summary, open(os.path.join(run, "summary.json"), "w"), indent=2)
print(f"== call run {run}: peer {meta.get('incoming')}  rtt median {rtt:.2f} ms  clock offset {off:.2f} ms  peer bye seen: {meta.get('peer_bye_seen')}")
print(f"  sent {summary['sent_frames']} frames (dropped by camera rule {summary['encoder_dropped']}); "
      f"received {summary['received_frames']}, lost {summary['lost_frames']} (of which {summary['incomplete_frames']} arrived incomplete), decode failures {summary['decode_failures']}")
if E:
    print(f"  send: {E['achieved_fps']:.2f} fps | encode+send mean {E['service_ms_mean']:.2f} ms p99 {E['service_ms_p99']:.2f} | due-to-sent p99 {E['latency_ms_p99']:.2f} ms | late+dropped {E['late_or_dropped_pct']:.2f} % | {E['kbps']:.0f} kbps")
if D:
    print(f"  recv: {D['achieved_fps']:.2f} fps | decode mean {D['service_ms_mean']:.2f} ms p99 {D['service_ms_p99']:.2f} | complete-to-decoded p99 {D['latency_ms_p99']:.2f} ms | late {D['late_or_dropped_pct']:.2f} % | {D['kbps']:.0f} kbps")
if net:
    n, e = summary["network_ms"], summary["send_to_decoded_ms"]
    print(f"  network (send -> complete, offset-corrected): mean {n['mean']:.2f} ms  p50 {n['p50']:.2f}  p95 {n['p95']:.2f}  p99 {n['p99']:.2f}")
    print(f"  end-to-end (peer send -> decoded here):       mean {e['mean']:.2f} ms  p50 {e['p50']:.2f}  p95 {e['p95']:.2f}  p99 {e['p99']:.2f}   ({summary['packets_per_frame_mean']:.1f} packets per frame)")
