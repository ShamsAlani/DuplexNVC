#!/bin/bash
# Installs the Phase 2 Step 2 scripts into ~/Downloads/d (./2a convert, ./2b streams, ./2c sanity+memory, ./2r results)
mkdir -p ~/Downloads/d
cat > ~/Downloads/d/s2cfg <<'ZZEND'
# Phase 2 Step 2 settings (sourced by 2a/2b/2c/2r). name -> model id, model input, video size
S2="$WORK/phase2/step2"; MP4="$WORK/data/vcd_1080p/mp4/th"; NV="$WORK/data/nv12"; INCD="$WORK/data/incoming"
CK_MLVC=~/mlvc/job-outputs/pretrained/mlvc-psnr-v1.ckpt
CK_MLVCS=~/mlvc/job-outputs/pretrained/mlvc-s-psnr-v1.ckpt
CAMIDS="0380a333cb0fef69001fb4260e2a705f 6587aeba8bb9bc97c0fc640ee664c444"
INCIDS="6c9c96d33030b3b3879c691760492b14 9c02f633262ef15f81eab1f2fa06faa5"
NEW="mlvc_540p mlvc_720p mlvc_1080p mlvcs_540p mlvcs_720p mlvcs_1080p"
cfg () {  # sets MODEL CKPT MSIZE VSIZE RES for a setting name
  case $1 in mlvc_*) MODEL=dmc61sbr_reglu; CKPT=$CK_MLVC;; mlvcs_*) MODEL=dmc61sbr_mini_reglu; CKPT=$CK_MLVCS;; esac
  case $1 in *_360p|mlvc_multi) MSIZE=640x368; VSIZE=640x360; RES=360p;;
             *_540p) MSIZE=960x544; VSIZE=960x540; RES=540p;;
             *_720p) MSIZE=1280x720; VSIZE=1280x720; RES=720p;;
             *_1080p) MSIZE=1920x1088; VSIZE=1920x1080; RES=1080p;; esac
}
# bundle folder, camera stream and incoming stream per setting
bund () { case $1 in mlvc_360p) echo "$WORK/bundles/mlvc";; *) echo "$WORK/bundles/$1";; esac; }
camf () { cfg $1; [ $RES = 360p ] && echo "$CAM" || echo "$NV/cam_$RES.nv12"; }
incf () { case $1 in mlvc_360p|mlvc_multi) echo "$BINC/incoming.aus";; *) echo "$INCD/$1-qp26/incoming.aus";; esac; }
ZZEND
cat > ~/Downloads/d/2a <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 2a: convert the 6 new bundles (+1 multi-size test) and trace each network. Wi-Fi ON (one download). ~30-45 min
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
exec > >(tee "$D/out_2a.txt") 2>&1
mkdir -p "$S2"; echo "== STEP 2a START  $(date)"; sw_vers | tr '\n' ' '; echo; df -h "$WORK" | tail -1
# 1. MLVC-S PSNR checkpoint
if [ ! -s "$CK_MLVCS" ]; then
  echo "-- downloading mlvc-s-psnr-v1.ckpt"
  curl -C - -L --fail -o "$CK_MLVCS" https://mlvideopub.blob.core.windows.net/mlvc/models/mlvc-s-psnr-v1.ckpt || { echo "DOWNLOAD FAILED (Wi-Fi on?)"; exit 1; }
fi
echo "-- checksum (must be 1b86b757...ca896):"; shasum -a 256 "$CK_MLVCS"
# 2. converter test clips at 540p/720p/1080p (Lanczos from the 1080p MP4, as MLVC does)
ID=0380a333cb0fef69001fb4260e2a705f
for wh in 960x540 1280x720 1920x1080; do
  d=~/mlvc/data/VCD/yuv/${wh}_30fps/s1; f="$d/${ID}_${wh}_30fps.yuv"; mkdir -p "$d"
  [ -s "$MP4/${ID}_1920x1080_30.mp4" ] || { echo "MISSING $MP4/${ID}_1920x1080_30.mp4"; exit 1; }
  [ -s "$f" ] || ffmpeg -v error -i "$MP4/${ID}_1920x1080_30.mp4" -vf "scale=${wh/x/:}:flags=lanczos" -pix_fmt yuv420p -f rawvideo "$f"
  # the converter names the 1080p clip ..._1920x1080_30.yuv (no "fps"); provide both names
  [ "$wh" = 1920x1080 ] && ln -sf "$f" "$d/${ID}_1920x1080_30.yuv"
  echo "   test clip $wh: $(ls -lh "$f" | awk '{print $5}')  ($(( $(stat -f %z "$f") / (${wh%x*} * ${wh#*x} * 3 / 2) )) frames)"
done
# 3. conversions
cd "$WORK/mlvc-tools/video" || exit 1
conv () {  # conv <name> <model> <ckpt> <sizes...>
  local name=$1 model=$2 ckpt=$3; shift 3; local sizes="$*"
  echo "== convert $name: $model, sizes $sizes  ($(date +%H:%M:%S))"
  uv run convert.py bundle --model-version $model --weights-path "$ckpt" --weights-version psnr_v1 \
     --model-input-sizes $sizes --mlvc-version v0.1 --model-type coreml --target-device apple > "$S2/convert_$name.log" 2>&1
  local tarf="output/model_bundles/${model}-psnr_v1-coreml-apple-v0.1.tar"
  if ! grep -q "Archive created: .*${model}-psnr_v1-coreml-apple-v0.1.tar" "$S2/convert_$name.log"; then
    echo "   FAILED - last lines of $S2/convert_$name.log:"; tail -12 "$S2/convert_$name.log"; return
  fi
  mkdir -p "$WORK/bundles/$name"; rm -f "$WORK/bundles/$name"/*.tar; cp "$tarf" "$WORK/bundles/$name/"
  for s in $sizes; do mkdir -p "$S2/models/$name/$s"; cp -R "output/models/${model}-psnr_v1/coreml-apple/$s/"*.mlpackage "$S2/models/$name/$s/" 2>/dev/null; done
  echo "   ok: $(ls -lh "$WORK/bundles/$name"/*.tar | awk '{print $5, $9}')"
}
conv mlvc_540p   dmc61sbr_reglu      "$CK_MLVC"  960x544
conv mlvc_720p   dmc61sbr_reglu      "$CK_MLVC"  1280x720
conv mlvc_1080p  dmc61sbr_reglu      "$CK_MLVC"  1920x1088
conv mlvcs_540p  dmc61sbr_mini_reglu "$CK_MLVCS" 960x544
conv mlvcs_720p  dmc61sbr_mini_reglu "$CK_MLVCS" 1280x720
conv mlvcs_1080p dmc61sbr_mini_reglu "$CK_MLVCS" 1920x1088
conv mlvc_multi  dmc61sbr_reglu      "$CK_MLVC"  640x368 960x544 1280x720
# 4. per-network trace (encoder and decoder separately)
echo "== where each network runs (MLComputePlan)"
[ -x "$TOOLS/mlplan" ] || swiftc -O -parse-as-library "$D/mlplan.swift" -o "$TOOLS/mlplan"
for p in $(find "$S2/models" -name "*.mlpackage" -prune | sort); do
  rel=${p#$S2/models/}; "$TOOLS/mlplan" "$p" "${rel%.mlpackage}" | grep -v "^$"
done
echo "== STEP 2a END  $(date)"; ls -lh "$WORK"/bundles/*/*.tar
ZZEND
cat > ~/Downloads/d/2b <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 2b: camera + incoming streams at 540p/720p/1080p (same clip pairs as B*, Lanczos from 1080p MP4),
# incoming prepared at QP 26 on the NE for each new setting, decode check. No quiet Mac needed. ~15 min, ~7 GB disk
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
exec > >(tee "$D/out_2b.txt") 2>&1
mkdir -p "$NV" "$INCD"; echo "== STEP 2b START  $(date)"; df -h "$WORK" | tail -1
mk () {  # mk <out.nv12> <WxH> <ids...>
  local out=$1 wh=$2; shift 2
  [ -s "$out" ] && { echo "   exists: $out"; return; }
  for id in "$@"; do
    ffmpeg -v error -i "$MP4/${id}_1920x1080_30.mp4" -frames:v 300 -vf "scale=${wh/x/:}:flags=lanczos" -pix_fmt nv12 -f rawvideo -
  done > "$out"
  local W=${wh%x*} H=${wh#*x}; local n=$(( $(stat -f %z "$out") / (W*H*3/2) ))
  echo "   $out: $n frames (must be 600)"
}
for wh in 960x540:540p 1280x720:720p 1920x1080:1080p; do
  echo "-- streams ${wh#*:}"
  mk "$NV/cam_${wh#*:}.nv12" ${wh%:*} $CAMIDS
  mk "$NV/incsrc_${wh#*:}.nv12" ${wh%:*} $INCIDS
done
for s in $NEW; do
  cfg $s; B=$(bund $s); O="$INCD/$s-qp26"; mkdir -p "$O"
  echo "-- prepare incoming $s ($VSIZE, QP 26, encoder on NE)"
  "$BENCH" prepare --input "$NV/incsrc_$RES.nv12" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$B" --enc-cu npu --out-dir "$O" 2> "$O/prepare.log"
  grep -E "Found model bundle|resolved|wrote|FAILED|rror" "$O/prepare.log" | sort -u | head -5
  "$MLVC" decode --model-bundles-dir "$B" --input "$O/incoming.mlvc" --output /tmp/s2_check.nv12 > "$O/decode_check.log" 2>&1 || echo "   DECODE FAILED"
  echo "   bitrate $(( $(stat -f %z "$O/incoming.mlvc") * 8 * 30 / 600 / 1000 )) kbps; $("$PY" "$TOOLS/quality_tools.py" psnr /tmp/s2_check.nv12 "$NV/incsrc_$RES.nv12" $VSIZE | tail -1)"
  rm -f /tmp/s2_check.nv12
done
echo "== STEP 2b END  $(date)"; du -sh "$NV" "$INCD"
ZZEND
cat > ~/Downloads/d/2c <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 2c: sanity timing of every bundle on the NE (encoder alone, decoder alone, unpaced, 3 interleaved rounds)
# + peak memory of a duplex run per bundle with both networks on the NE and on the GPU.
# QUIET MAC (charger, Wi-Fi + Bluetooth off, brightness MAX, apps closed). ~1 h 50 min. Run ./p first.
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
exec > >(tee "$D/out_2c.txt") 2>&1
ALL="mlvc_360p mlvc_multi $NEW"
echo "== STEP 2c START  $(date)"; sw_vers | tr '\n' ' '; echo; pmset -g batt | head -1
n=0; N=$(( 3*2*8 + 2*8 ))
for r in 1 2 3; do
  for s in $ALL; do
    cfg $s; for m in alone-enc alone-dec; do
      n=$((n+1)); O="$S2/sanity/$s/U_${m}_npu_r$r"; mkdir -p "$(dirname "$O")"
      echo "[$n/$N] $(date +%H:%M:%S) $s $m round $r"
      "$BENCH" $m --input "$(camf $s)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund $s)" --incoming "$(incf $s)" \
         --fps 0 --seconds 60 --out-dir "$O" 2> "$O.log"
      grep -oE "requested=[a-z]+ resolved=[a-z]+|FAILED|rror.*" "$O.log" | sort -u | tr '\n' ' '; echo
      sleep 60
    done
  done
done
echo "== peak memory (duplex 20 s, both networks on one unit)"
for s in $ALL; do
  cfg $s; for cu in npu gpu; do
    n=$((n+1)); O="$S2/memory/${s}_$cu"; mkdir -p "$(dirname "$O")"
    echo "[$n/$N] $(date +%H:%M:%S) $s duplex $cu/$cu"
    /usr/bin/time -l "$BENCH" duplex --input "$(camf $s)" --size $VSIZE --qp 26 --iframe-period 64 --bundles "$(bund $s)" \
       --incoming "$(incf $s)" --enc-cu $cu --dec-cu $cu --fps 0 --seconds 20 --warmup-frames 10 --out-dir "$O" 2> "$O.log"
    grep -E "peak memory footprint|maximum resident set size" "$O.log" | sed 's/^ */   /'
    sleep 30
  done
done
echo "== STEP 2c END  $(date)"
"$D/2r"
ZZEND
cat > ~/Downloads/d/2r <<'ZZEND'
#!/bin/bash
# PHASE 2 STEP 2 results: NE speed per bundle vs survey Table 11 (M3 Pro), multi-size vs single, memory
D=$(cd "$(dirname "$0")" && pwd); . "$D/v"; . "$D/s2cfg"
exec > >(tee "$D/out_2r.txt") 2>&1
"$PY" "$D/step2_sum.py" "$S2" "$TOOLS"
ZZEND
cat > ~/Downloads/d/step2_sum.py <<'ZZEND'
"""Step 2 summary: python3 step2_sum.py <phase2/step2 dir> <tools dir>"""
import csv, glob, os, re, statistics as st, sys
S2, tools = sys.argv[1], sys.argv[2]; sys.path.insert(0, tools)
import analyze_run as A
# survey Table 11, MLVC paper, M3 Pro NE, measured alone (fps)
M3 = {"mlvc_360p": (129.5, 122.9), "mlvc_540p": (65.7, 62.3), "mlvc_720p": (33.8, 33.1), "mlvc_1080p": (15.6, 15.2),
      "mlvcs_540p": (152.0, 137.6), "mlvcs_720p": (83.8, 73.5), "mlvcs_1080p": (39.5, 34.6)}
order = ["mlvc_360p", "mlvc_multi", "mlvc_540p", "mlvc_720p", "mlvc_1080p", "mlvcs_540p", "mlvcs_720p", "mlvcs_1080p"]
rows = []
def med(s, net, d):
    v = []
    for r in sorted(glob.glob(f"{S2}/sanity/{s}/U_{net}_npu_r*")):
        if not os.path.isdir(r): continue
        try:
            m, fr = A.load(r); x = A.direction_summary(m, fr, d)
            if x: v.append(x)
        except Exception: pass
    if not v: return None
    return dict(n=len(v), call=st.median(x["call_ms_mean"] for x in v), net=st.median(x["infer_ms_mean"] for x in v),
                lo=min(x["call_ms_mean"] for x in v), hi=max(x["call_ms_mean"] for x in v))
def mem(s, cu):
    p = f"{S2}/memory/{s}_{cu}.log"
    if not os.path.exists(p): return ""
    t = open(p, errors="ignore").read()
    m = re.search(r"(\d+)\s+peak memory footprint", t) or re.search(r"(\d+)\s+maximum resident set size", t)
    return round(int(m.group(1)) / 2**20) if m else ""
print(f"{'setting':12s} {'enc ms':>7s} {'dec ms':>7s} {'(min-max enc)':>14s} {'enc net':>7s} {'dec net':>7s} {'M3 enc':>7s} {'M3 dec':>7s} {'M4/M3':>6s} {'turns fps':>9s} {'mem NE MB':>9s} {'mem GPU MB':>10s}  note")
for s in order:
    e, d = med(s, "alone-enc", "E"), med(s, "alone-dec", "D")
    if not e or not d:
        print(f"{s:12s} no runs"); continue
    m3 = M3.get(s if s != "mlvc_multi" else "mlvc_360p")
    m3e, m3d = (1000 / m3[0], 1000 / m3[1]) if m3 else (None, None)
    ratio = ((e["call"] + d["call"]) / (m3e + m3d)) if m3 else None
    turns = 1000 / (e["call"] + d["call"])
    note = ""
    if ratio and ratio > 0.9: note = "SLOWER than expected (B* was ~0.75): check trace for CPU ops"
    row = dict(setting=s, enc_ms=e["call"], dec_ms=d["call"], enc_min=e["lo"], enc_max=e["hi"], enc_net_ms=e["net"],
               dec_net_ms=d["net"], m3_enc_ms=m3e or "", m3_dec_ms=m3d or "", m4_over_m3=ratio or "",
               turns_fps_each_way=turns, mem_duplex_ne_MB=mem(s, "npu"), mem_duplex_gpu_MB=mem(s, "gpu"), note=note)
    rows.append(row)
    f = lambda v, w=7: f"{v:{w}.2f}" if isinstance(v, float) else f"{str(v):>{w}s}"
    print(f"{s:12s} {f(e['call'])} {f(d['call'])} {e['lo']:6.2f}-{e['hi']:<7.2f} {f(e['net'])} {f(d['net'])} {f(m3e or '')} {f(m3d or '')} {f(ratio or '',6)} {f(turns,9)} {f(row['mem_duplex_ne_MB'],9)} {f(row['mem_duplex_gpu_MB'],10)}  {note}")
if rows:
    with open(f"{S2}/step2_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
        for r in rows: w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"\n-> {S2}/step2_table.csv")
r = {x["setting"]: x for x in rows}
if "mlvc_multi" in r and "mlvc_360p" in r:
    a, b = r["mlvc_360p"], r["mlvc_multi"]
    print(f"\nmulti-size bundle at 360p vs single-size: enc {b['enc_ms']:.2f} vs {a['enc_ms']:.2f} ms, dec {b['dec_ms']:.2f} vs {a['dec_ms']:.2f} ms"
          f" -> keep {'multi-size' if b['enc_ms'] + b['dec_ms'] < a['enc_ms'] + a['dec_ms'] else 'single-size'} bundles")
ZZEND
chmod +x ~/Downloads/d/2a ~/Downloads/d/2b ~/Downloads/d/2c ~/Downloads/d/2r
echo "Step 2 scripts installed in ~/Downloads/d: ./2a ./2b ./2c ./2r (fixed version)"
