#!/bin/bash
# Installs the overnight script (./all) and the Step 4 summary (./4r) into ~/Downloads/d. Needs the Step 2 scripts (d6.sh) installed.
mkdir -p ~/Downloads/d
[ -f ~/Downloads/d/s2cfg ] || { echo "install d6.sh first"; exit 1; }
cat > ~/Downloads/d/all <<'ZZEND'
#!/bin/bash
# OVERNIGHT RUN: Phase 2 Step 2c (NE sanity + memory) and Step 4 (table of feasible settings), unattended and RESUMABLE.
#   Part A  NE alone, 3 rounds, all 8 bundles (= Step 2c sanity; reused as the NE-alone rows of Step 4) + peak memory
#   Part B  GPU and CPU alone, 3 rounds, all 7 model/resolution pairs (CPU runs 20 s)
#   Part C  every placement, in the plan's batch order: unpaced turns + duplex (3 rounds), paced duplex 30 fps 5 x 60 s
#           with powermetrics; if late/dropped >= 1 % in a direction: paced duplex 15 fps 3 x 60 s. Idle power before each batch.
#   Placements (D5): NE/GPU everywhere; CPU placements only where every network alone on the CPU is < 33.3 ms.
#   Thermal state + Low Power Mode logged every second for the whole night (thermal.csv).
# QUIET MAC: charger, Wi-Fi + Bluetooth off, brightness MAX (auto-brightness + True Tone off), apps closed. Run ./p first.
# Interrupt any time with Ctrl-C; run ./all again later and it continues where it stopped (finished runs are skipped).
# REST=30 ./all  uses 30 s instead of 60 s rest between runs (shorter night, deviates from the B* protocol; noted in out_all.txt).
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
S4="$WORK/phase2/step4"; mkdir -p "$S4" "$S2"
exec > >(tee -a "$D/out_all.txt") 2>&1
REST=${REST:-60}
echo; echo "== OVERNIGHT START  $(date)   rest=${REST}s"; sw_vers | tr '\n' ' '; echo; pmset -g batt | head -1
cat "$WORK/LIBMLVC_COMMIT.txt" 2>/dev/null
sudo -v || exit 1
( while true; do sudo -n true 2>/dev/null; sleep 50; done ) & KEEP=$!
[ -x "$TOOLS/thermal_log" ] || swiftc -O "$D/thermal_log.swift" -o "$TOOLS/thermal_log"
"$TOOLS/thermal_log" >> "$S4/thermal.csv" & THERM=$!
trap 'kill $KEEP $THERM 2>/dev/null; echo "== stopped $(date) - run ./all again to continue"; exit 1' INT TERM
PAIRS="mlvc_360p mlvc_540p mlvc_720p mlvc_1080p mlvcs_540p mlvcs_720p mlvcs_1080p"
T0=$(date +%s); n=0
done_run () { [ -s "$1/frames.csv" ] && [ -s "$1/run.txt" ]; }
bench () {  # bench <outdir> <setting> <mode> <enc_cu> <dec_cu> <fps> <seconds> [extra...]
  local O=$1 s=$2 mode=$3 ec=$4 dc=$5 fps=$6 sec=$7; shift 7
  n=$((n+1))
  if done_run "$O"; then echo "   skip (done) ${O#$WORK/phase2/}"; return 1; fi
  cfg $s; mkdir -p "$(dirname "$O")"; local wu=64; [ "$ec" = cpu ] || [ "$dc" = cpu ] && wu=10
  [ "$fps" = 15 ] && extra="--deadline-ms 66.7" || extra=""
  echo "[$n] $(date +%H:%M:%S) +$(( ($(date +%s)-T0)/60 ))min  ${O#$WORK/phase2/}"
  "$BENCH" $mode --input "$(camf $s)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund $s)" --incoming "$(incf $s)" \
     --enc-cu $ec --dec-cu $dc --fps $fps --seconds $sec --warmup-frames $wu $extra "$@" --out-dir "$O" 2> "$O.log"
  pmset -g therm 2>/dev/null | grep -iE "speed_limit|warning" | tr -s ' \n' ' ' > "$O.therm"
  grep -oE "requested=[a-z]+ resolved=[a-z]+|FAILED|rror[^.]*" "$O.log" | sort -u | tr '\n' ' '; echo
  return 0
}
late_any () {  # late_any <dir pattern> -> exit 0 if median late/dropped >= 1 % in either direction
  "$PY" - "$TOOLS" "$@" <<'PY'
import sys, glob, statistics as st; sys.path.insert(0, sys.argv[1]); import analyze_run as A
runs = sorted(glob.glob(sys.argv[2])); worst = 0
for d in ("E", "D"):
    v = []
    for r in runs:
        try:
            m, fr = A.load(r); s = A.direction_summary(m, fr, d)
            if s: v.append(s["late_or_dropped_pct"])
        except Exception: pass
    if v: worst = max(worst, st.median(v))
print(f"   median late/dropped worst direction: {worst:.2f} %"); sys.exit(0 if worst >= 1.0 else 1)
PY
}
cpu_fits () {  # cpu_fits <setting> -> exit 0 if encoder AND decoder alone on CPU are < 33.3 ms (median)
  "$PY" - "$TOOLS" "$S4/alone/$1" <<'PY'
import sys, glob, statistics as st; sys.path.insert(0, sys.argv[1]); import analyze_run as A
ok = True
for net, d in (("alone-enc", "E"), ("alone-dec", "D")):
    v = []
    for r in glob.glob(f"{sys.argv[2]}/U_{net}_cpu_r*"):
        try:
            m, fr = A.load(r); s = A.direction_summary(m, fr, d)
            if s: v.append(s["call_ms_mean"])
        except Exception: pass
    if not v or st.median(v) >= 1000 / 30: ok = False
    print(f"   CPU {net}: {st.median(v):.1f} ms" if v else f"   CPU {net}: no data")
sys.exit(0 if ok else 1)
PY
}
rest () { sleep $REST; }

echo "== PART A: NE alone (3 rounds) for all bundles + peak memory"
for r in 1 2 3; do for s in mlvc_360p mlvc_multi $NEW; do for m in alone-enc alone-dec; do
  bench "$S2/sanity/$s/U_${m}_npu_r$r" $s $m npu npu 0 60 && rest
done; done; done
for s in mlvc_360p mlvc_multi $NEW; do for cu in npu gpu; do
  O="$S2/memory/${s}_$cu"
  if grep -q "peak memory footprint" "$O.log" 2>/dev/null; then echo "   skip (done) memory $s $cu"; continue; fi
  cfg $s; mkdir -p "$(dirname "$O")"; echo "   $(date +%H:%M:%S) memory $s duplex $cu/$cu"
  /usr/bin/time -l "$BENCH" duplex --input "$(camf $s)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund $s)" \
     --incoming "$(incf $s)" --enc-cu $cu --dec-cu $cu --fps 0 --seconds 20 --warmup-frames 10 --out-dir "$O" 2> "$O.log"
  grep -E "peak memory footprint" "$O.log" | sed 's/^ */   /'; sleep 30
done; done
"$D/2r"

echo "== PART B: GPU and CPU alone (3 rounds) for all 7 pairs"
for r in 1 2 3; do for s in $PAIRS; do for cu in gpu cpu; do for m in alone-enc alone-dec; do
  sec=60; [ $cu = cpu ] && sec=20
  [ $m = alone-enc ] && { ec=$cu; dc=npu; } || { ec=npu; dc=$cu; }
  bench "$S4/alone/$s/U_${m}_${cu}_r$r" $s $m $ec $dc 0 $sec && rest
done; done; done; done
# NE alone for Step 4 = Part A runs (link them in so the table finds everything under step4/alone)
for s in $PAIRS; do for r in 1 2 3; do for m in alone-enc alone-dec; do
  [ -e "$S4/alone/$s/U_${m}_npu_r$r" ] || ln -s "$S2/sanity/$s/U_${m}_npu_r$r" "$S4/alone/$s/U_${m}_npu_r$r"
done; done; done

echo "== PART C: placements, batch order of the plan"
idle () {  # 120 s idle power before a batch
  local I="$S4/idle/$1"; [ -s "$I/power.txt" ] && return; mkdir -p "$I"
  echo "   $(date +%H:%M:%S) idle 120 s ($1)"; sudo powermetrics --samplers cpu_power,gpu_power -i 100 -n 1200 -o "$I/power.txt" >/dev/null 2>&1
}
placement () {  # placement <setting> <enc_cu> <dec_cu> <batch>
  local s=$1 ec=$2 dc=$3 b=$4 P="$S4/$1_$2-$3"
  echo "-- $s  enc $ec  dec $dc   (batch $b)"
  for r in 1 2 3; do for m in turns duplex; do bench "$P/U_${m}_r$r" $s $m $ec $dc 0 60 && rest; done; done
  for r in 1 2 3 4 5; do
    O="$P/P30_r$r"
    if done_run "$O"; then n=$((n+1)); echo "   skip (done) ${O#$WORK/phase2/}"; continue; fi
    mkdir -p "$O"; sudo powermetrics --samplers cpu_power,gpu_power -i 100 -n 700 -o "$O/power.txt" >/dev/null 2>&1 & PM=$!
    sleep 3; bench "$O" $s duplex $ec $dc 30 60; wait $PM; rest
  done
  if late_any "$P/P30_r*"; then
    echo "   fails 30 fps -> 15 fps runs"
    for r in 1 2 3; do bench "$P/P15_r$r" $s duplex $ec $dc 15 60 && rest; done
  fi
  echo "$b" > "$P/batch.txt"
}
batch () {  # batch <name> <settings...>
  local b=$1; shift; idle "$b"
  for s in "$@"; do
    for p in npu-npu npu-gpu gpu-npu gpu-gpu; do
      [ "$s-$p" = "mlvc_360p-npu-npu" ] && { echo "-- mlvc_360p npu/npu = B* (Phase 2 report), not repeated"; continue; }
      placement $s ${p%-*} ${p#*-} $b
    done
    if cpu_fits $s; then
      echo "   CPU fits for $s -> CPU placements included"
      for p in npu-cpu cpu-npu gpu-cpu cpu-gpu cpu-cpu; do placement $s ${p%-*} ${p#*-} $b; done
    else echo "   CPU does not fit for $s -> no CPU placements (D5)"; fi
  done
}
batch b1_mlvc_720p   mlvc_720p
batch b2_mlvc_540p   mlvc_540p
batch b3_mlvcs_hi    mlvcs_720p mlvcs_1080p
batch b4_mlvc_360p   mlvc_360p
batch b5_mlvc_1080p  mlvc_1080p
batch b6_mlvcs_540p  mlvcs_540p
kill $KEEP $THERM 2>/dev/null
echo "== OVERNIGHT END  $(date)  ($(( ($(date +%s)-T0)/60 )) min)"
"$D/4r"
ZZEND
cat > ~/Downloads/d/4r <<'ZZEND'
#!/bin/bash
# STEP 4 results: table of feasible settings (timing, real-time, energy, memory) -> phase2/step4/table_feasible.csv
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
exec > >(tee "$D/out_4r.txt") 2>&1
"$PY" "$D/step4_sum.py" "$WORK" "$TOOLS"
ZZEND
cat > ~/Downloads/d/step4_sum.py <<'ZZEND'
"""Step 4 summary: python3 step4_sum.py <WORK> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
WORK, tools = sys.argv[1], sys.argv[2]; sys.path.insert(0, tools)
import analyze_run as A
S4, S2 = f"{WORK}/phase2/step4", f"{WORK}/phase2/step2"
ORDER = ["mlvc_720p", "mlvc_540p", "mlvcs_720p", "mlvcs_1080p", "mlvc_360p", "mlvc_1080p", "mlvcs_540p"]
DL30 = 1000 / 30

def summ(run, d):
    try:
        m, fr = A.load(run); return A.direction_summary(m, fr, d)
    except Exception:
        return None

def runs(pattern):
    return sorted(r for r in glob.glob(pattern) if os.path.isdir(r) and os.path.exists(os.path.join(r, "frames.csv")))

def med(vals):
    v = [x for x in vals if x is not None]
    return st.median(v) if v else None

def alone(s, net, cu):
    d = "E" if net == "alone-enc" else "D"
    return med([(summ(r, d) or {}).get("call_ms_mean") for r in runs(f"{S4}/alone/{s}/U_{net}_{cu}_r*")])

def period(pattern):  # T per frame pair = slower direction's frame time, median over rounds
    v = []
    for r in runs(pattern):
        e, d = summ(r, "E"), summ(r, "D")
        if e and d: v.append(max(e["frame_time_ms_mean"], d["frame_time_ms_mean"]))
    return med(v)

def dup_call(pattern, d):
    return med([(summ(r, d) or {}).get("call_ms_mean") for r in runs(pattern)])

def paced(pattern):
    out = {}
    for d, k in (("E", "send"), ("D", "recv")):
        ss = [s for s in (summ(r, d) for r in runs(pattern)) if s]
        if not ss: continue
        m = lambda key: st.median(x[key] for x in ss)
        out.update({f"fps_{k}": m("achieved_fps"), f"L_{k}": m("late_or_dropped_pct"), f"call_{k}": m("service_ms_mean"),
                    f"p99_{k}": m("latency_ms_p99"), f"p95_{k}": m("latency_ms_p95"), f"kbps_{k}": m("kbps")})
        sd = []
        for r in runs(pattern):
            fr = [x for x in csv.DictReader(open(os.path.join(r, "frames.csv"))) if x["dir"] == d and x["warmup"] == "0"]
            if fr: sd.append(st.mean(float(x["start_ms"]) - float(x["sched_ms"]) for x in fr))
        out[f"start_delay_{k}"] = med(sd)
        out["runs"] = len(ss)
    return out

def energy(pattern, idle_pm):
    idle = A.parse_pm(idle_pm) if idle_pm and os.path.exists(idle_pm) else []
    per = {"ane": [], "gpu": [], "cpu": [], "combined": []}
    for r in runs(pattern):
        p = os.path.join(r, "power.txt")
        if not os.path.exists(p): continue
        meta, rows = A.load(r); smp = A.parse_pm(p)
        t0 = float(meta["t0_epoch_ms"]) / 1000
        warm = t0 + max((x["end_ms"] for x in rows if x["warmup"]), default=0) / 1000
        tend = t0 + max(x["end_ms"] for x in rows) / 1000
        win = [s for s in smp if warm + 1 <= s[0] <= tend - 1]
        steady = [x for x in rows if not x["warmup"]]
        pairs = min(sum(x["dir"] == "E" for x in steady), sum(x["dir"] == "D" for x in steady))
        secs = (max(x["end_ms"] for x in steady) - min(x["sched_ms"] for x in steady)) / 1000
        if not win or not pairs: continue
        for k in per:
            pi = A.mean_power(idle, k) if idle else 0.0
            per[k].append((A.mean_power(win, k) - pi) / 1000 * secs * 1000 / pairs)
    return {f"mJ_{k}": med(v) for k, v in per.items()}

def mem(s, cu):
    p = f"{S2}/memory/{s}_{cu}.log"
    if not os.path.exists(p): return None
    m = re.search(r"(\d+)\s+peak memory footprint", open(p, errors="ignore").read())
    return round(int(m.group(1)) / 2**20) if m else None

turns_ne = {}
for s in ORDER:
    turns_ne[s] = period(f"{S4}/{s}_npu-npu/U_turns_r*") or (period(f"{WORK}/runs/bl_bstar/T_turns_r*") if s == "mlvc_360p" else None)

rows = []
for s in ORDER:
    idle_pm = next(iter(glob.glob(f"{S4}/idle/*/power.txt")), None)
    bt = None
    for P in sorted(glob.glob(f"{S4}/{s}_*-*")):
        ec, dc = os.path.basename(P)[len(s) + 1:].split("-")
        b = open(f"{P}/batch.txt").read().strip() if os.path.exists(f"{P}/batch.txt") else ""
        ip = f"{S4}/idle/{b}/power.txt" if b else idle_pm
        te, td = alone(s, "alone-enc", ec), alone(s, "alone-dec", dc)
        Tt, Ts = period(f"{P}/U_turns_r*"), period(f"{P}/U_duplex_r*")
        p30, p15 = paced(f"{P}/P30_r*"), paced(f"{P}/P15_r*")
        en = energy(f"{P}/P30_r*", ip)
        ok30 = p30 and p30.get("L_send", 100) < 1 and p30.get("L_recv", 100) < 1
        ok15 = p15 and p15.get("L_send", 100) < 1 and p15.get("L_recv", 100) < 1
        label = "30 fps" if ok30 else ("15 fps only" if ok15 else ("infeasible" if p30 else "not run"))
        ce, cd = dup_call(f"{P}/U_duplex_r*", "E"), dup_call(f"{P}/U_duplex_r*", "D")
        row = dict(model=s.split("_")[0], res=s.split("_")[1], enc=ec, dec=dc, batch=b,
                   t_enc_alone=te, t_dec_alone=td, T_turns=Tt, T_shared=Ts,
                   S=(Tt / Ts) if Tt and Ts else None,
                   S_max=((te + td) / max(te, td)) if te and td else None,
                   S_vs_NE_turns=(turns_ne[s] / Ts) if turns_ne.get(s) and Ts else None,
                   kappa_enc=(ce / te) if ce and te else None, kappa_dec=(cd / td) if cd and td else None,
                   **{f"p30_{k}": v for k, v in p30.items()}, **en,
                   **{f"p15_{k}": v for k, v in p15.items() if k in ("fps_send", "fps_recv", "L_send", "L_recv", "p99_send", "p99_recv")},
                   mem_ne_MB=mem(s, "npu"), mem_gpu_MB=mem(s, "gpu"), feasible=label)
        rows.append(row)
if not rows:
    print("no Step 4 runs yet"); sys.exit()
keys = []
for r in rows:
    for k in r:
        if k not in keys: keys.append(k)
out = f"{S4}/table_feasible.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
    for r in rows: w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
f = lambda v, w=6, p=2: (f"{v:{w}.{p}f}" if isinstance(v, (int, float)) and v is not None else f"{'-':>{w}s}")
print(f"== table of feasible settings -> {out}\n")
print(f"{'model':6s} {'res':5s} {'enc':4s} {'dec':4s} {'t_enc':>6s} {'t_dec':>6s} {'T_trn':>6s} {'T_shr':>6s} {'S':>5s} {'S_NE':>5s} "
      f"{'fps30 s/r':>11s} {'L% s/r':>11s} {'p99 s/r':>11s} {'mJ/pair':>7s} {'NE/GPU/CPU mJ':>16s} {'kbps s/r':>11s}  feasible")
for r in rows:
    g = r.get
    print(f"{r['model']:6s} {r['res']:5s} {r['enc']:4s} {r['dec']:4s} {f(g('t_enc_alone'))} {f(g('t_dec_alone'))} {f(g('T_turns'))} "
          f"{f(g('T_shared'))} {f(g('S'),5)} {f(g('S_vs_NE_turns'),5)} {f(g('p30_fps_send'),5,1)}/{f(g('p30_fps_recv'),5,1)} "
          f"{f(g('p30_L_send'),5,1)}/{f(g('p30_L_recv'),5,1)} {f(g('p30_p99_send'),5,1)}/{f(g('p30_p99_recv'),5,1)} "
          f"{f(g('mJ_combined'),7,1)} {f(g('mJ_ane'),5,1)}/{f(g('mJ_gpu'),5,1)}/{f(g('mJ_cpu'),4,1)} "
          f"{f(g('p30_kbps_send'),5,0)}/{f(g('p30_kbps_recv'),5,0)}  {r['feasible']}"
          + (f"  (15 fps: L {f(g('p15_L_send'),4,1)}/{f(g('p15_L_recv'),4,1)})" if g('p15_L_send') is not None else ""))
print("\n== 720p question: speedup over taking turns on the NE, S = T_turns(NE) / T per placement")
for r in rows:
    if r["res"] == "720p" and r.get("S_vs_NE_turns"):
        print(f"   {r['model']:6s} {r['enc']}/{r['dec']}: unpaced S = {r['S_vs_NE_turns']:.2f} (needed ~1.80 for 30 fps from 16.7)  -> {r['feasible']}")
cnt = {}
for r in rows: cnt[r["feasible"]] = cnt.get(r["feasible"], 0) + 1
print("\n== feasibility count:", ", ".join(f"{k}: {v}" for k, v in cnt.items()))
ZZEND
cat > ~/Downloads/d/thermal_log.swift <<'ZZEND'
// Logs the signals the Phase-2 energy monitor will read, once per second:
// epoch seconds, ProcessInfo.thermalState, Low Power Mode.
import Foundation
setvbuf(stdout, nil, _IOLBF, 0)
let names = ["nominal", "fair", "serious", "critical"]
print("epoch_s,thermal_state,low_power_mode")
while true {
    let p = ProcessInfo.processInfo
    print("\(Date().timeIntervalSince1970),\(names[p.thermalState.rawValue]),\(p.isLowPowerModeEnabled)")
    Thread.sleep(forTimeInterval: 1.0)
}
ZZEND
chmod +x ~/Downloads/d/all ~/Downloads/d/4r
echo "Installed in ~/Downloads/d: ./all (overnight, resumable) and ./4r (table)"
