#!/usr/bin/env python3
"""Summarise duplex_bench runs: timing per direction, power/energy, and comparisons.

  python3 analyze_run.py timing RUN_DIR [RUN_DIR ...]
  python3 analyze_run.py power  RUN_DIR --pm RUN_DIR/power.txt --idle-pm idle/power.txt
  python3 analyze_run.py battery RUN_DIR
  python3 analyze_run.py compare --alone-enc A --alone-dec B --turns T --duplex D
"""
import argparse, csv, json, re, statistics, sys
from datetime import datetime
from pathlib import Path


def load(run):
    run = Path(run)
    meta = dict(l.strip().split("=", 1) for l in open(run / "run.txt") if "=" in l)
    rows = list(csv.DictReader(open(run / "frames.csv")))
    for r in rows:
        for k in ("slot", "late", "ok", "warmup", "frame_type", "bytes"):
            r[k] = int(r[k])
        for k in ("sched_ms", "start_ms", "end_ms", "service_ms", "latency_ms", "infer_ms", "call_ms"):
            r[k] = float(r[k])
    return meta, rows


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * p / 100
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def direction_summary(meta, rows, d):
    r = [x for x in rows if x["dir"] == d and not x["warmup"]]
    if not r:
        return None
    fps_target = float(meta["fps"])
    span_ms = max(x["end_ms"] for x in r) - min(x["sched_ms"] for x in r)
    done = len(r)
    dropped = int(meta["encoder_dropped"]) if d == "E" else 0
    # Scheduled slots in the steady window = encoded + dropped (sender) or decoded (receiver).
    scheduled = done + dropped
    late = sum(x["late"] for x in r)
    ends = sorted(x["end_ms"] for x in r)
    intervals = [b - a for a, b in zip(ends, ends[1:])]
    s = {
        "frames": done,
        "achieved_fps": 1000.0 * done / span_ms if span_ms > 0 else float("nan"),
        "frame_time_ms_mean": statistics.mean(intervals) if intervals else float("nan"),
        "service_ms_mean": statistics.mean(x["service_ms"] for x in r),
        "service_ms_p95": pct([x["service_ms"] for x in r], 95),
        "service_ms_p99": pct([x["service_ms"] for x in r], 99),
        "infer_ms_mean": statistics.mean(x["infer_ms"] for x in r),
        "call_ms_mean": statistics.mean(x["call_ms"] for x in r),
        "latency_ms_p95": pct([x["latency_ms"] for x in r], 95),
        "latency_ms_p99": pct([x["latency_ms"] for x in r], 99),
        "late": late,
        "dropped": dropped,
        "late_or_dropped_pct": 100.0 * (late + dropped) / scheduled if scheduled else float("nan"),
        "failures": sum(1 for x in r if not x["ok"]),
        # bitrate at the content frame rate (30 fps), whether or not the run was paced
        "kbps": (sum(x["bytes"] for x in r) * 8 / 1000) / (done / 30.0),
        "i_frames": sum(1 for x in r if x["frame_type"] == 0),
    }
    s["cpu_share_of_call_pct"] = 100.0 * (s["call_ms_mean"] - s["infer_ms_mean"]) / s["call_ms_mean"]
    return s


def cmd_timing(args):
    out = {}
    for run in args.runs:
        meta, rows = load(run)
        res = {d: direction_summary(meta, rows, d) for d in ("E", "D")}
        out[run] = {"meta": meta, "send(E)": res["E"], "recv(D)": res["D"]}
        print(f"\n== {run}  mode={meta['mode']} size={meta['size']} qp={meta['qp']} "
              f"enc={meta['enc_cu']} dec={meta['dec_cu']} fps={meta['fps']} deadline={meta['deadline_ms']} ms")
        for name, s in (("send", res["E"]), ("recv", res["D"])):
            if not s:
                continue
            print(f"  {name}: {s['achieved_fps']:.1f} fps | service mean {s['service_ms_mean']:.2f} ms "
                  f"p95 {s['service_ms_p95']:.2f} p99 {s['service_ms_p99']:.2f} | latency p95 {s['latency_ms_p95']:.2f} "
                  f"p99 {s['latency_ms_p99']:.2f} | late+dropped {s['late_or_dropped_pct']:.2f}% "
                  f"| infer {s['infer_ms_mean']:.2f} / call {s['call_ms_mean']:.2f} ms "
                  f"| fails {s['failures']} | {s['kbps']:.0f} kbps")
    if args.json:
        json.dump(out, open(args.json, "w"), indent=2)


# ---------- powermetrics ----------
HDR = re.compile(r"\*\*\* Sampled system activity \((.+?)\) \(([\d.]+)ms elapsed\) \*\*\*")
PWR = re.compile(r"^(CPU|GPU|ANE) Power: (\d+) mW", re.M)
COMB = re.compile(r"^Combined Power \(CPU \+ GPU \+ ANE\): (\d+) mW", re.M)


def parse_pm(path):
    """Return list of (end_epoch_s, elapsed_ms, {cpu,gpu,ane,combined} mW)."""
    text = open(path, errors="ignore").read()
    parts = HDR.split(text)
    samples = []
    for i in range(1, len(parts) - 2, 3):
        stamp, elapsed, body = parts[i], float(parts[i + 1]), parts[i + 2]
        try:
            t = datetime.strptime(stamp, "%a %b %d %H:%M:%S %Y %z").timestamp()
        except ValueError:
            t = float("nan")
        p = {k.lower(): float(v) for k, v in PWR.findall(body)}
        c = COMB.search(body)
        if c:
            p["combined"] = float(c.group(1))
        samples.append((t, elapsed, p))
    return samples


def mean_power(samples, key):
    tot_e = sum(s[1] * s[2].get(key, 0.0) for s in samples)
    tot_t = sum(s[1] for s in samples)
    return tot_e / tot_t if tot_t else float("nan")


def cmd_power(args):
    meta, rows = load(args.run)
    samples = parse_pm(args.pm)
    t0 = float(meta["t0_epoch_ms"]) / 1000.0
    warm_end = t0 + max((r["end_ms"] for r in rows if r["warmup"]), default=0) / 1000.0
    t_end = t0 + max(r["end_ms"] for r in rows) / 1000.0
    # powermetrics stamps have 1 s resolution; keep samples whose stamp lies inside the steady window.
    win = [s for s in samples if warm_end + 1 <= s[0] <= t_end - 1]
    idle = parse_pm(args.idle_pm) if args.idle_pm else []
    steady = [r for r in rows if not r["warmup"]]
    pairs = min(sum(r["dir"] == "E" for r in steady), sum(r["dir"] == "D" for r in steady)) or \
        max(sum(r["dir"] == "E" for r in steady), sum(r["dir"] == "D" for r in steady))
    secs = sum(s[1] for s in win) / 1000.0
    print(f"samples in window: {len(win)} ({secs:.1f} s); frames (pairs) in steady window: {pairs}")
    res = {}
    for k in ("cpu", "gpu", "ane", "combined"):
        p_run = mean_power(win, k)
        p_idle = mean_power(idle, k) if idle else 0.0
        steady_s = (max(r["end_ms"] for r in steady) - min(r["sched_ms"] for r in steady)) / 1000.0
        e_dyn = (p_run - p_idle) / 1000.0 * steady_s  # J above idle over the steady window
        res[k] = {"run_mW": p_run, "idle_mW": p_idle, "dynamic_mJ_per_pair": 1000.0 * e_dyn / pairs,
                  "dynamic_J_per_min": e_dyn / steady_s * 60.0}
        print(f"  {k:9s} run {p_run:8.0f} mW  idle {p_idle:7.0f} mW  -> "
              f"{res[k]['dynamic_mJ_per_pair']:7.1f} mJ per frame pair, {res[k]['dynamic_J_per_min']:6.1f} J/min")
    if args.json:
        json.dump(res, open(args.json, "w"), indent=2)


def cmd_battery(args):
    """Whole-system discharge power from ioreg (no root). Only valid on battery (ExternalConnected=No)."""
    meta, rows = load(args.run)
    t0 = float(meta["t0_epoch_ms"]) / 1000.0
    steady = [r for r in rows if not r["warmup"]]
    a_s = t0 + min(r["sched_ms"] for r in steady) / 1000.0
    b_s = t0 + max(r["end_ms"] for r in steady) / 1000.0
    watts, ext, caps = [], set(), []
    for line in open(f"{args.run}/battery.csv"):
        parts = line.strip().strip(",").split(",")
        try:
            t = float(parts[0])
        except ValueError:
            continue
        kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        if not (a_s <= t <= b_s) or "Voltage" not in kv:
            continue
        amp = int(kv.get("InstantAmperage", kv.get("Amperage", "0")))
        if amp >= 2 ** 63:  # ioreg prints negative currents as unsigned 64-bit
            amp -= 2 ** 64
        watts.append(abs(int(kv["Voltage"]) * amp) / 1e6)
        ext.add(kv.get("ExternalConnected"))
        caps.append(kv.get("CurrentCapacity"))
    if not watts:
        print("no battery samples in the steady window"); return
    print(f"ExternalConnected={ext} (must be No); capacity {caps[0]} -> {caps[-1]}")
    print(f"mean whole-system discharge power {statistics.mean(watts):.2f} W over {len(watts)} samples")


def cmd_compare(args):
    def s(run, d):
        meta, rows = load(run)
        if float(meta["fps"]) > 0:
            print(f"WARNING: {run} is paced (fps={meta['fps']}); speedup and kappa need unpaced runs (--fps 0)")
        return direction_summary(meta, rows, d)
    ae, ad = s(args.alone_enc, "E"), s(args.alone_dec, "D")
    te, td = s(args.turns, "E"), s(args.turns, "D")
    de, dd = s(args.duplex, "E"), s(args.duplex, "D")
    t_turns = max(te["frame_time_ms_mean"], td["frame_time_ms_mean"])
    for name, a, d in (("send", ae, de), ("recv", ad, dd)):
        kappa_call = d["call_ms_mean"] / a["call_ms_mean"]
        kappa_inf = d["infer_ms_mean"] / a["infer_ms_mean"]
        S = t_turns / d["frame_time_ms_mean"]
        print(f"{name}: alone call {a['call_ms_mean']:.2f} ms, duplex call {d['call_ms_mean']:.2f} ms -> "
              f"kappa(call) {kappa_call:.2f}, kappa(inference) {kappa_inf:.2f}; "
              f"T_turns {t_turns:.2f} ms, T {d['frame_time_ms_mean']:.2f} ms -> S {S:.2f}")
    ceiling = (ae["call_ms_mean"] + ad["call_ms_mean"]) / max(ae["call_ms_mean"], ad["call_ms_mean"])
    print(f"ceiling (t_enc + t_dec) / max(t_enc, t_dec) from alone runs: {ceiling:.2f}  "
          f"(30 fps from T_turns needs S >= {t_turns / 33.333:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("timing"); a.add_argument("runs", nargs="+"); a.add_argument("--json")
    b = sub.add_parser("power"); b.add_argument("run"); b.add_argument("--pm", required=True)
    b.add_argument("--idle-pm"); b.add_argument("--json")
    d = sub.add_parser("battery"); d.add_argument("run")
    c = sub.add_parser("compare")
    for k in ("--alone-enc", "--alone-dec", "--turns", "--duplex"):
        c.add_argument(k, required=True)
    args = ap.parse_args()
    {"timing": cmd_timing, "power": cmd_power, "battery": cmd_battery, "compare": cmd_compare}[args.cmd](args)
