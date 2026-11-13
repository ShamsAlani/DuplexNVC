#!/bin/bash
# Installs the Phase 2 Step 1 scripts into ~/Downloads/d (./1t trace, ./1 timing, ./1r results)
mkdir -p ~/Downloads/d
cat > ~/Downloads/d/1 <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 1: each network alone on NE, GPU and CPU (the gate for placements, decision D5)
#   unpaced: full MLVC 360p 5 interleaved rounds, MLVC-S 540p 3 rounds; CPU runs 20 s, others 60 s; 60 s rest
#   paced 30 fps: NE and GPU, 3 x 60 s per network, powermetrics on every paced run (cross-check of where it ran)
# Quiet Mac: charger in, Wi-Fi + Bluetooth off, brightness MAX, apps closed. ~2 h 20 min. Password once at start.
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"
exec > >(tee "$D/out_1.txt") 2>&1
S1="$WORK/phase2/step1"; mkdir -p "$S1"
echo "== PHASE 2 STEP 1 START  $(date)"; sw_vers | tr '\n' ' '; echo; pmset -g batt | head -1
cat "$WORK/LIBMLVC_COMMIT.txt" 2>/dev/null
sudo -v || exit 1
( while true; do sudo -n true 2>/dev/null; sleep 50; done ) & KEEP=$!
n=0; N=72
run () {  # run <folder> <mode> <settings> <cu> <fps> <seconds>
  local dir=$1 mode=$2 set=$3 cu=$4 fps=$5 sec=$6 wu=64 cuflag
  [ "$cu" = cpu ] && wu=10
  [ "$mode" = alone-enc ] && cuflag="--enc-cu $cu" || cuflag="--dec-cu $cu"
  n=$((n+1)); echo "[$n/$N] $(date +%H:%M:%S) $(basename "$(dirname "$dir")")/$(basename "$dir")"
  "$BENCH" $mode $set $cuflag --fps $fps --seconds $sec --warmup-frames $wu --out-dir "$dir" 2> "$dir.log"
  grep -oE "requested=[a-z]+ resolved=[a-z]+|FAILED|rror.*" "$dir.log" | sort -u | tr '\n' ' '; echo
}
for M in mlvc_360p mlvcs_540p; do
  if [ $M = mlvc_360p ]; then SET="$BL"; RN="1 2 3 4 5"; else SET="$P1"; RN="1 2 3"; fi
  mkdir -p "$S1/$M"
  echo "== $M unpaced"
  for r in $RN; do
    for cu in npu gpu cpu; do
      for m in alone-enc alone-dec; do
        sec=60; [ $cu = cpu ] && sec=20
        run "$S1/$M/U_${m}_${cu}_r$r" $m "$SET" $cu 0 $sec; sleep 60
      done
    done
  done
  echo "== $M paced 30 fps (with powermetrics)"
  for r in 1 2 3; do
    for cu in npu gpu; do
      for m in alone-enc alone-dec; do
        dir="$S1/$M/P_${m}_${cu}_r$r"; mkdir -p "$dir"
        sudo powermetrics --samplers cpu_power,gpu_power -i 100 -n 700 -o "$dir/power.txt" >/dev/null 2>&1 &
        PM=$!; sleep 3
        run "$dir" $m "$SET" $cu 30 60
        wait $PM; sleep 40
      done
    done
  done
done
kill $KEEP 2>/dev/null
echo "== PHASE 2 STEP 1 END  $(date)"
"$D/1r"
ZZEND
cat > ~/Downloads/d/1t <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 1, part 3: where does each network run? MLComputePlan per operation (macOS 14.4+), no sudo, ~5 min
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"
exec > >(tee "$D/out_1t.txt") 2>&1
T="$WORK/phase2/step1/trace"; mkdir -p "$T"
echo "== MLComputePlan trace  $(date)"; sw_vers | tr '\n' ' '; echo
swiftc -O -parse-as-library "$D/mlplan.swift" -o "$TOOLS/mlplan" || { echo "BUILD FAILED"; exit 1; }
for B in mlvc mlvc-s; do
  for tarf in "$WORK/bundles/$B"/*.tar; do
    name=$(basename "$tarf" .tar); X="$T/$name"; rm -rf "$X"; mkdir -p "$X"
    echo "-- $name: contents"; tar -tf "$tarf" | head -40
    tar -xf "$tarf" -C "$X"
    for z in $(find "$X" -name "*.tar" -o -name "*.zip"); do
      mkdir -p "$z.d"; case "$z" in *.zip) unzip -q "$z" -d "$z.d";; *) tar -xf "$z" -C "$z.d";; esac
    done
    models=$(find "$X" \( -name "*.mlpackage" -o -name "*.mlmodelc" -o -name "*.mlmodel" \) -prune -print | sort)
    [ -z "$models" ] && echo "   no Core ML model found inside; check out_1t.txt"
    for m in $models; do "$TOOLS/mlplan" "$m" "$name/$(basename "$m")"; done
  done
done
echo "== done  $(date)"
ZZEND
cat > ~/Downloads/d/1r <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 1 results: table per network x unit, g ratios, power cross-check, D5 suggestion
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"
exec > >(tee "$D/out_1r.txt") 2>&1
"$PY" "$D/step1_sum.py" "$WORK/phase2/step1" "$TOOLS"
ZZEND
cat > ~/Downloads/d/mlplan.swift <<'ZZEND'
// Where does each operation of a Core ML model run? (MLComputePlan, macOS 14.4+)
// usage: mlplan <model.mlpackage | .mlmodel | .mlmodelc> [label]
// Prints, per compute-unit setting, the number of operations and the share of estimated cost
// whose PREFERRED device is the Neural Engine, the GPU or the CPU.
import CoreML
import Foundation

@main
struct MLPlan {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count >= 2 else { print("usage: mlplan <model> [label]"); exit(2) }
        var url = URL(fileURLWithPath: args[1])
        let label = args.count > 2 ? args[2] : url.lastPathComponent
        if url.pathExtension != "mlmodelc" {
            do { url = try await MLModel.compileModel(at: url) }
            catch { print("\(label) | compile failed: \(error)"); return }
        }
        let settings: [(String, MLComputeUnits)] = [("cpuAndNeuralEngine", .cpuAndNeuralEngine),
                                                    ("cpuAndGPU", .cpuAndGPU), ("cpuOnly", .cpuOnly)]
        for (name, units) in settings {
            let config = MLModelConfiguration()
            config.computeUnits = units
            do {
                let plan = try await MLComputePlan.load(contentsOf: url, configuration: config)
                var ops = [String: Int](), cost = [String: Double]()
                var total = 0, totalCost = 0.0
                func device(_ d: MLComputeDevice) -> String {
                    switch d {
                    case .cpu: return "CPU"
                    case .gpu: return "GPU"
                    case .neuralEngine: return "NE"
                    @unknown default: return "other"
                    }
                }
                func walk(_ list: [MLModelStructure.Program.Operation]) {
                    for op in list {
                        if let usage = plan.deviceUsage(for: op) {
                            let d = device(usage.preferred)
                            let w = plan.estimatedCost(of: op)?.weight ?? 0
                            ops[d, default: 0] += 1; cost[d, default: 0] += w
                            total += 1; totalCost += w
                        }
                        for b in op.blocks { walk(b.operations) }
                    }
                }
                switch plan.modelStructure {
                case .program(let program):
                    for (_, f) in program.functions { walk(f.block.operations) }
                default:
                    print("\(label) | \(name) | not an ML program: per-operation plan unavailable"); continue
                }
                let parts = ["NE", "GPU", "CPU"].map { d -> String in
                    let share = totalCost > 0 ? 100 * cost[d, default: 0] / totalCost : 0
                    return "\(d) \(ops[d, default: 0]) ops \(String(format: "%.1f", share))% cost"
                }
                print("\(label) | \(name) | \(total) ops | " + parts.joined(separator: " | "))
            } catch {
                print("\(label) | \(name) | plan failed: \(error)")
            }
        }
    }
}
ZZEND
cat > ~/Downloads/d/step1_sum.py <<'ZZEND'
"""Step 1 summary: python3 step1_sum.py <phase2/step1 dir> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
base, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
import analyze_run as A

DEADLINE = 1000 / 30
rows, T = [], {}
for M in ("mlvc_360p", "mlvcs_540p"):
    for kind in ("U", "P"):
        for net, d in (("alone-enc", "E"), ("alone-dec", "D")):
            for cu in ("npu", "gpu", "cpu"):
                runs = sorted(r for r in glob.glob(f"{base}/{M}/{kind}_{net}_{cu}_r*") if os.path.isdir(r))
                ss, pw = [], []
                for r in runs:
                    try:
                        m, fr = A.load(r); s = A.direction_summary(m, fr, d)
                    except Exception:
                        s = None
                    if s: ss.append(s)
                    p = os.path.join(r, "power.txt")
                    if os.path.exists(p):
                        smp = A.parse_pm(p)
                        if smp: pw.append({k: A.mean_power(smp, k) for k in ("ane", "gpu", "cpu")})
                if not ss:
                    continue
                med = lambda k: st.median(x[k] for x in ss)
                row = dict(model=M, mode="unpaced" if kind == "U" else "paced30", network=net[6:], unit=cu,
                           runs=len(ss), call_ms=med("call_ms_mean"), call_min=min(x["call_ms_mean"] for x in ss),
                           call_max=max(x["call_ms_mean"] for x in ss), network_ms=med("infer_ms_mean"),
                           p99_call_ms=med("service_ms_p99"), fps=med("achieved_fps"),
                           late_pct=med("late_or_dropped_pct") if kind == "P" else "",
                           ne_mW=st.median(x["ane"] for x in pw) if pw else "",
                           gpu_mW=st.median(x["gpu"] for x in pw) if pw else "",
                           cpu_mW=st.median(x["cpu"] for x in pw) if pw else "")
                rows.append(row); T[(M, row["mode"], row["network"], cu)] = row
out = os.path.join(base, "step1_table.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
print(f"== Step 1 table -> {out}\n")
fmt = lambda v: f"{v:8.2f}" if isinstance(v, float) else f"{str(v):>8s}"
print(f"{'model':11s} {'mode':8s} {'net':4s} {'unit':4s} {'runs':>4s} {'call ms':>8s} {'net ms':>8s} {'p99':>8s} {'fps':>8s} {'late%':>8s} {'NE mW':>8s} {'GPU mW':>8s} {'CPU mW':>8s}")
for r in rows:
    print(f"{r['model']:11s} {r['mode']:8s} {r['network']:4s} {r['unit']:4s} {r['runs']:4d}" +
          "".join(fmt(r[k]) for k in ("call_ms", "network_ms", "p99_call_ms", "fps", "late_pct", "ne_mW", "gpu_mW", "cpu_mW")))

print("\n== slowdown ratios vs NE (g = t(GPU)/t(NE), c = t(CPU)/t(NE)), call time / network time")
for M in ("mlvc_360p", "mlvcs_540p"):
    for mode in ("unpaced", "paced30"):
        for net in ("enc", "dec"):
            ne = T.get((M, mode, net, "npu"))
            if not ne: continue
            parts = []
            for cu, lab in (("gpu", "g"), ("cpu", "c")):
                o = T.get((M, mode, net, cu))
                if o: parts.append(f"{lab} = {o['call_ms']/ne['call_ms']:.2f} / {o['network_ms']/ne['network_ms']:.2f}")
            if parts: print(f"  {M:11s} {mode:8s} {net}: " + "   ".join(parts))

print("\n== D5 rules (plan Step 1)")
for net in ("enc", "dec"):
    ne, gp = T.get(("mlvc_360p", "paced30", net, "npu")), T.get(("mlvc_360p", "paced30", net, "gpu"))
    cp = T.get(("mlvc_360p", "unpaced", net, "cpu")); neu = T.get(("mlvc_360p", "unpaced", net, "npu")); gpu = T.get(("mlvc_360p", "unpaced", net, "gpu"))
    if gp: print(f"  360p {net}: GPU paced call {gp['call_ms']:.1f} ms -> {'well under' if gp['call_ms'] < 0.6*DEADLINE else 'NOT well under'} 33.3 ms")
    if gpu and neu: print(f"  360p {net}: g (unpaced) = {gpu['call_ms']/neu['call_ms']:.2f} -> {'> 3x: keep GPU only for MLVC-S and 360-540p' if gpu['call_ms']/neu['call_ms'] > 3 else '<= 3x: keep GPU placements at all resolutions'}; 720p NE->GPU needs g <= 1.10")
    if cp: print(f"  360p {net}: CPU call {cp['call_ms']:.1f} ms -> {'drop CPU from timing table (keep for correctness)' if cp['call_ms'] > DEADLINE else 'CPU can stay in the timing table'}")
ZZEND
chmod +x ~/Downloads/d/1 ~/Downloads/d/1t ~/Downloads/d/1r
echo "Step 1 scripts installed in ~/Downloads/d: ./1t (trace), ./1 (timing), ./1r (results)"
