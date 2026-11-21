# DuplexNVC lab GPU script for Windows + NVIDIA (8 GB GPU settings).
# Run every command as:   powershell -ExecutionPolicy Bypass -File .\lab.ps1 <command>
#   setup     install + downloads (~15-20 min)
#   smoke     released MLVC on the GPU, 360p validation
#   github    one-time GitHub link:  ... github <owner>/<repo> "Your Name" you@email
#   weekend   starts the unattended pipeline in a separate minimized window (keep that window open)
#   status    progress
#   push      push results now
param([string]$cmd = "", [string]$a1 = "", [string]$a2 = "", [string]$a3 = "")
$ErrorActionPreference = "Continue"
$R = "$HOME\mlvc"; $C = "$R\code\video"; $L = "$R\logs"; $G = "$HOME\.gh"
New-Item -ItemType Directory -Force $L | Out-Null
$env:Path = "$HOME\.local\bin;$env:Path"
$env:PYTHONUTF8 = "1"
$BLOB = "https://mlvideopub.blob.core.windows.net/mlvc"
$HF = "https://huggingface.co/datasets/nkp37/OpenVid-1M/resolve/main/OpenVidHD"
$PART = "OpenVidHD_part_10.zip"
$BS = 2; $CHUNK = 2; $MAXEP = 200
$VAL = "benchmark_test.VCD_640x360_30fps_40s48f"

function Log($f, $m) { Add-Content -Path "$L\$f" -Value $m; Write-Host $m }
function Get-File($url, $out) {   # resumable download with retries (curl.exe ships with Windows 10/11)
  if (Test-Path "$out.done") { return }
  $h = @(); if ($env:HF_TOKEN -and $url -like "*huggingface*") { $h = @("-H", "Authorization: Bearer $env:HF_TOKEN") }
  for ($i = 0; $i -lt 50; $i++) {
    curl.exe -L --fail -C - @h -o $out $url
    if ($LASTEXITCODE -eq 0) { New-Item "$out.done" -ItemType File -Force | Out-Null; return }
    Start-Sleep 60
  }
  throw "download failed: $url"
}
function Get-Big($url, $out, $n = 32) {   # parallel ranged download (one slow connection -> 32 connections)
  if (Test-Path "$out.done") { return }
  $len = 0; $m = (curl.exe -sIL $url) | Select-String -Pattern '^content-length:\s*(\d+)' | Select-Object -Last 1
  if ($m) { $len = [long]$m.Matches[0].Groups[1].Value }
  if ($len -lt 100MB) { Get-File $url $out; return }
  $sz = [long][math]::Ceiling($len / $n)
  for ($round = 0; $round -lt 30; $round++) {
    $procs = @()
    for ($i = 0; $i -lt $n; $i++) {
      $s0 = $i * $sz; $e = [math]::Min($len - 1, $s0 + $sz - 1); $pf = "$out.p$i"
      if ((Test-Path $pf) -and (Get-Item $pf).Length -eq ($e - $s0 + 1)) { continue }
      $procs += Start-Process curl.exe -ArgumentList "-sL --fail --retry 5 -r $s0-$e -o `"$pf`" `"$url`"" -NoNewWindow -PassThru
    }
    if ($procs.Count -eq 0) { break }
    $procs | Wait-Process
  }
  $fs = [IO.File]::Create($out)
  for ($i = 0; $i -lt $n; $i++) { $in = [IO.File]::OpenRead("$out.p$i"); $in.CopyTo($fs); $in.Close() }
  $fs.Close()
  if ((Get-Item $out).Length -ne $len) { throw "size mismatch for $out" }
  for ($i = 0; $i -lt $n; $i++) { Remove-Item "$out.p$i" }
  New-Item "$out.done" -ItemType File -Force | Out-Null
}
function Uvr { & uv run --no-sync @args }

$VALYAML = @"
model.p_frame.ckpt_path: pretrained/mlvc-psnr-v1.ckpt
$VAL.schedule: []
$VAL.use_i_frame_model: false
$VAL.calc_deqa_score_rgb: false
$VAL.encode_bit_stream: false
$VAL.test_interval: 1
$VAL.deqa_test_interval: 0
$VAL.max_batch_size: 2
$VAL.log_metrics: [p_frame_bpp_estimate, p_frame_psnr, p_frame_msssim]
"@

function Ensure-Ffmpeg {   # MLVC calls "ffmpeg" to decode videos; install a portable copy (no admin needed)
  $bin = Get-ChildItem "$R\ffmpeg" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $bin) {
    New-Item -ItemType Directory -Force "$R\ffmpeg" | Out-Null
    curl.exe -L --fail -o "$R\ffmpeg.zip" "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    tar -xf "$R\ffmpeg.zip" -C "$R\ffmpeg"; Remove-Item "$R\ffmpeg.zip"
    $bin = Get-ChildItem "$R\ffmpeg" -Recurse -Filter ffmpeg.exe | Select-Object -First 1
  }
  $env:Path = "$($bin.DirectoryName);$env:Path"
}
Ensure-Ffmpeg *> $null
# optional input gate for "B1 + input gate" (off unless model.p_frame.input_gate: true)
if ((Test-Path "$C\src\models\dmc_6\dmc_61sb.py") -and -not (Select-String -Path "$C\src\models\dmc_6\dmc_61sb.py" -Pattern "input_gate" -Quiet)) {
@'
"""Adds an optional separate input gate to MLVC's decoder memory (DMC-6.1sb).

Off by default (model.p_frame.input_gate: false), so other runs are unchanged.
With input_gate on, the memory update becomes  m = f*m + i*s  instead of  m = f*m + (1-f)*s.
When loading a checkpoint without the input-gate channels, the new channels are
initialised as the negated forget-gate channels, so with hard_sigmoid the model starts
exactly equal to the loaded one (hard_sigmoid(-x) = 1 - hard_sigmoid(x)).
Usage: python patch_input_gate.py <path to mlvc/video>   (safe to run more than once)
"""
import os
import sys

root = sys.argv[1]
model_py = os.path.join(root, "src", "models", "dmc_6", "dmc_61sb.py")
factory_py = os.path.join(root, "src", "utils", "model_factory.py")


def patch(path, edits):
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    if "input_gate" in text:
        print("already patched:", os.path.basename(path))
        return
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"patch anchor not found exactly once in {path}: {old[:60]!r}")
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)
    print("patched:", os.path.basename(path))


patch(model_py, [
    (
        "        gate_activation: str,\n        network_mode: NetworkMode,\n    ):\n        super().__init__()\n\n        block_args",
        "        gate_activation: str,\n        network_mode: NetworkMode,\n        input_gate: bool = False,\n    ):\n        super().__init__()\n\n        block_args",
    ),
    (
        "        self.conv2 = DMCConv2d(mid_ch, 3 * out_ch, 1, **conv_args)",
        "        self.input_gate = input_gate\n        self.out_ch = out_ch\n"
        "        self.conv2 = DMCConv2d(mid_ch, (4 if input_gate else 3) * out_ch, 1, **conv_args)",
    ),
    (
        "        state, forget_gate, output_gate = torch.chunk(feature, 3, dim=1)\n"
        "        forget_gate = self.gate_activation(forget_gate)\n"
        "        output_gate = self.gate_activation(output_gate)\n"
        "        state = self.memory_activation(state)\n\n"
        "        memory = forget_gate * memory + (1 - forget_gate) * state\n",
        "        if self.input_gate:\n"
        "            state, forget_gate, output_gate, input_gate = torch.chunk(feature, 4, dim=1)\n"
        "            input_gate = self.gate_activation(input_gate)\n"
        "        else:\n"
        "            state, forget_gate, output_gate = torch.chunk(feature, 3, dim=1)\n"
        "        forget_gate = self.gate_activation(forget_gate)\n"
        "        output_gate = self.gate_activation(output_gate)\n"
        "        state = self.memory_activation(state)\n\n"
        "        if self.input_gate:\n"
        "            memory = forget_gate * memory + input_gate * state\n"
        "        else:\n"
        "            memory = forget_gate * memory + (1 - forget_gate) * state\n",
    ),
    (
        "        return feature, memory\n",
        "        return feature, memory\n\n"
        "    def _load_from_state_dict(self, state_dict, prefix, *args, **kwargs):\n"
        "        if self.input_gate:\n"
        "            c = self.out_ch\n"
        "            for name in (\"conv2.weight\", \"conv2.bias\"):\n"
        "                key = prefix + name\n"
        "                if key in state_dict and state_dict[key].shape[0] == 3 * c:\n"
        "                    t = state_dict[key]\n"
        "                    state_dict[key] = torch.cat((t, -t[c:2 * c]), dim=0)\n"
        "        super()._load_from_state_dict(state_dict, prefix, *args, **kwargs)\n",
    ),
    (
        '        gate_activation: str = "sigmoid",\n',
        '        gate_activation: str = "sigmoid",\n        input_gate: bool = False,\n',
    ),
    (
        "            gate_activation=gate_activation,\n",
        "            gate_activation=gate_activation,\n            input_gate=input_gate,\n",
    ),
])

patch(factory_py, [
    (
        '            gate_activation=config.get("gate_activation", "sigmoid"),\n',
        '            gate_activation=config.get("gate_activation", "sigmoid"),\n'
        '            input_gate=config.get("input_gate", False),\n',
    ),
])

'@ | Set-Content "$R\patch_input_gate.py" -Encoding UTF8
  & "$R\code\.venv\Scripts\python.exe" "$R\patch_input_gate.py" $C *> "$L\patch.txt"
}
# new ffmpeg builds removed "-vsync"; MLVC still passes it -> use the replacement option
$ffds = "$C\src\datasets\ffmpeg_dataset.py"
if ((Test-Path $ffds) -and (Select-String -Path $ffds -Pattern '"-vsync", "0"' -Quiet)) {
  (Get-Content $ffds -Raw).Replace('"-vsync", "0"', '"-fps_mode", "passthrough"') | Set-Content $ffds -Encoding UTF8 -NoNewline
}

function Setup {
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$HOME\.local\bin;$env:Path"
  }
  foreach ($d in "$R\data\VCD\yuv", "$R\data\OpenVidHD\raw", "$R\job-outputs\pretrained", "$R\job-outputs\benchmark_test\anchor\vcd\640x360_30fps") { New-Item -ItemType Directory -Force $d | Out-Null }
  if (-not (Test-Path "$R\code")) {
    if (Get-Command git -ErrorAction SilentlyContinue) { git clone https://github.com/microsoft/mlvc.git "$R\code" }
    else {
      Get-File "https://github.com/microsoft/mlvc/archive/refs/heads/main.zip" "$R\mlvc.zip"
      tar -xf "$R\mlvc.zip" -C $R; Rename-Item "$R\mlvc-main" "$R\code"
    }
  }
  Push-Location "$R\code"; uv sync; $ok = $LASTEXITCODE; Pop-Location
  if ($ok -ne 0) { Write-Host "UV SYNC FAILED - send me the error"; return }
  Push-Location $C
  Uvr python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  Pop-Location
  Get-File "$BLOB/models/mlvc-psnr-v1.ckpt" "$R\job-outputs\pretrained\mlvc-psnr-v1.ckpt"
  Get-File "$BLOB/anchors/vcd/640x360_30fps/dcvcrt_with_iframe_metrics_VCD_640x360_30fps_40s48f.json" "$R\job-outputs\benchmark_test\anchor\vcd\640x360_30fps\dcvcrt_with_iframe_metrics_VCD_640x360_30fps_40s48f.json"
  Get-File "$BLOB/datasets/OpenVidHD_parts_10-28/openvidhd_60k64_frame_sequences.csv" "$R\data\OpenVidHD\openvidhd_60k64_frame_sequences.csv"
  Remove-Item "$R\data\VCD\yuv\640x360_30fps.tar*" -ErrorAction SilentlyContinue   # skipped: too slow here, models are tested on the Mac
  if (Test-Path "$R\job-outputs\pretrained\DMCI-6.0.pth.tar") { "DMCI-6.0 OK" } else { "!! MISSING DMCI-6.0.pth.tar (move it in, see step 5)" }
  Get-PSDrive ($R.Substring(0,1)) | Select-Object @{n="FreeGB";e={[math]::Round($_.Free/1GB)}}
  "SETUP DONE"
}

function Smoke {
  Push-Location $C
  $VALYAML | Set-Content "$R\val.yaml"
  Uvr train_video.py --config configs/train_video-mlvc.yaml --validate --data_mount $R --checkpoints_mount "$R\job-outputs" `
    --save_dir checkpoints/smoke --overrides_file "$R\val.yaml" --overrides "{train.compile_model: false, train.compile_loss: false}" 2>&1 |
    Tee-Object "$L\smoke.txt" | Select-String -Pattern "psnr|bpp|error|Traceback" | Select-Object -Last 20
  Pop-Location
}

function Prep {
  $D = "$R\data\OpenVidHD"; $OUT = "$D\sub64"
  if ((Test-Path "$OUT\description.json") -and ((Get-ChildItem $OUT -Directory -ErrorAction SilentlyContinue).Count -gt 0)) { return $true }
  Remove-Item -Recurse -Force $OUT -ErrorAction SilentlyContinue
  Get-Big "$HF/$PART" "$D\raw\$PART" *>> "$L\prep.txt"
  if (-not (Test-Path "$D\raw\.unzipped")) {
    tar -xf "$D\raw\$PART" -C "$D\raw" *>> "$L\prep.txt"
    if ($LASTEXITCODE -ne 0) { Log prep.txt "UNZIP FAILED"; return $false }
    New-Item "$D\raw\.unzipped" -ItemType File | Out-Null; Remove-Item "$D\raw\$PART"
  }
  @'
import sys, os, pandas as pd
d=sys.argv[1]; raw=os.path.join(d,"raw"); m={}
for root,_,fs in os.walk(raw):
    for f in fs:
        if f.endswith(".mp4"): m[f]=os.path.relpath(os.path.join(root,f),raw).replace("\\","/")
df=pd.read_csv(os.path.join(d,"openvidhd_60k64_frame_sequences.csv"))
df["base"]=df["filename"].map(lambda s: s.replace("\\","/").split("/")[-1]); df=df[df["base"].isin(m)].copy()
df["filename"]=df["base"].map(m); df.drop(columns="base").to_csv(os.path.join(d,"sub64.csv"),index=False)
print("videos found",len(m),"sequences kept",len(df))
'@ | Set-Content "$R\filter.py"
  Push-Location $C
  Uvr python "$R\filter.py" $D *>> "$L\prep.txt"
  New-Item -ItemType Directory -Force $OUT | Out-Null
  $Dy = $D -replace '\\','/'; $OUTy = $OUT -replace '\\','/'
  Uvr extract_frame_sequences.py --config configs/dataset/extract_frame_sequences.yaml --data_mount $R --checkpoints_mount "$R\job-outputs" `
    --save_dir $OUT --overrides "{frame_sequence_extractor.source_dir: '$Dy/raw', frame_sequence_extractor.frame_sequences_csv: '$Dy/sub64.csv', frame_sequence_extractor.output_dir: '$OUTy', process_count: $env:NUMBER_OF_PROCESSORS}" *>> "$L\prep.txt"
  Uvr build_dataset_description.py "$D\sub64.csv" "$OUT\description.json" *>> "$L\prep.txt"
  Pop-Location
  return (Test-Path "$OUT\description.json")
}

function Write-FtYaml {
@"
seed: 0
train.compile_model: false
train.compile_loss: false
train.flat_parameters: false
train.ckpt_per_epoch: 1
train.restart: true
train.schedule: []
train.use_backprop_checkpoints: true
train.dataset.path: data/OpenVidHD/sub64/description.json
train.dataset.patch_size: [256, 256]
train.dataset.desired_length: 2000
train.dataset.target_resolution: 360
train.dataset.resampling_method: "bilinear/0.15 box/0.15 bicubic/0.35 lanczos/0.35"
train.dataset.max_frame_distance: 1
train.dataset.n_frames: 4
train.dataset.n_workers: 4
train.learning_rate: 1.e-5
train.bpp_loss_weight: 1.
train.cascade: true
train.distortion_weights: [0.52, 1.33, 0.83]
train.i_frame_dropout: 0.5
model.p_frame.ckpt_path: pretrained/mlvc-psnr-v1.ckpt
benchmark_test: {}
"@ | Set-Content "$R\ft.yaml"
}

function TrainTo($name, $ep, $extra, $seedBase = 0) {
  # MLVC does not store its random state in checkpoints, so every restart would replay the same samples.
  # A different, reproducible seed per 2-epoch chunk gives every chunk new training samples.
  $extra = "$extra, seed: $([int]$seedBase * 100000 + $ep)"
  if (Test-Path "$R\job-outputs\checkpoints\$name\model_epo$($ep - 1).ckpt") { return $true }
  $bs = $BS
  for ($t = 1; $t -le 3; $t++) {
    Push-Location $C
    Uvr train_video.py --config configs/train_video-mlvc.yaml --data_mount $R --checkpoints_mount "$R\job-outputs" `
      --save_dir "checkpoints/$name" --overrides_file "$R\ft.yaml" --overrides "{train.n_epoch: $ep, train.dataset.batch_size: $bs$extra}" *>> "$L\$name.txt"
    $ok = $LASTEXITCODE; Pop-Location
    if ($ok -eq 0) { return $true }
    Log "$name.txt" "[$name] crashed (try $t) $(Get-Date)"
    if ($bs -gt 1) { $bs = 1 }
  }
  return $false
}

function Push-Results($msg) {
  if (-not (Test-Path "$G\token")) { return }
  try {
    $tok = (Get-Content "$G\token" -Raw).Trim(); $repo = (Get-Content "$G\repo" -Raw).Trim()
    $name = (Get-Content "$G\name" -Raw).Trim(); $email = (Get-Content "$G\email" -Raw).Trim()
    $hdr = @{ Authorization = "Bearer $tok"; "User-Agent" = "lab"; Accept = "application/vnd.github+json" }
    $files = @{}
    Get-ChildItem "$L\*.txt" -ErrorAction SilentlyContinue | ForEach-Object { $files["lab/logs/$($_.Name)"] = (Get-Content $_.FullName -Tail 5000) -join "`n" }
    if (Test-Path "$R\ft.yaml") { $files["lab/ft.yaml"] = Get-Content "$R\ft.yaml" -Raw }
    $files["lab/nvidia-smi.txt"] = (nvidia-smi | Out-String)
    $files["lab/updated.txt"] = "$(Get-Date) | $msg | free GB: $([math]::Round((Get-PSDrive ($R.Substring(0,1))).Free/1GB))"
    if (Test-Path "$R\job-outputs\checkpoints") {
      Get-ChildItem "$R\job-outputs\checkpoints\control", "$R\job-outputs\checkpoints\b1" -Recurse -Include *.json, *.csv, *.yaml -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -lt 900KB } | Sort-Object LastWriteTime -Descending | Select-Object -First 30 | ForEach-Object {
          $rel = $_.FullName.Substring("$R\job-outputs\checkpoints\".Length) -replace '\\','/'
          $files["lab/metrics/$rel"] = Get-Content $_.FullName -Raw }
    }
    foreach ($p in $files.Keys) {
      $url = "https://api.github.com/repos/$repo/contents/$p"
      $sha = $null; try { $sha = (Invoke-RestMethod -Uri $url -Headers $hdr -Method Get).sha } catch {}
      $body = @{ message = "Lab training update: $msg"; content = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$files[$p]))
                 committer = @{ name = $name; email = $email } }
      if ($sha) { $body.sha = $sha }
      Invoke-RestMethod -Uri $url -Headers $hdr -Method Put -Body ($body | ConvertTo-Json -Depth 4) | Out-Null
    }
    "pushed $($files.Count) files"
  } catch { "push failed: $_" }
}

function Fix-Data {   # keep only sequences whose frames were all extracted
  $OUT = "$R\data\OpenVidHD\sub64"
  if (-not (Test-Path "$OUT\description_full.json")) { Copy-Item "$OUT\description.json" "$OUT\description_full.json" }
  @'
import sys, os, json
out=sys.argv[1]; d=json.load(open(os.path.join(out,"description_full.json")))
keep=[s for s in d if all(os.path.isfile(os.path.join(out,s["path"],f)) for f in s["frames"])]
json.dump(keep,open(os.path.join(out,"description.json"),"w"))
print(f"sequences listed {len(d)}, fully extracted {len(keep)}")
'@ | Set-Content "$R\fixdata.py"
  Push-Location $C; $r = Uvr python "$R\fixdata.py" $OUT 2>&1 | Out-String; Pop-Location
  return $r.Trim()
}

function Upload-Models {   # puts selected checkpoints + full logs on a GitHub release (files too big for the repo)
  $tok = (Get-Content "$G\token" -Raw).Trim(); $repo = (Get-Content "$G\repo" -Raw).Trim()
  $hdr = @{ Authorization = "Bearer $tok"; "User-Agent" = "lab"; Accept = "application/vnd.github+json" }
  $tag = "models-" + (Get-Date -Format "yyyyMMdd-HHmm")
  $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases" -Headers $hdr -Method Post `
    -Body (@{ tag_name = $tag; name = "Lab models $tag"; body = "Checkpoints (model weights only) and full training logs." } | ConvertTo-Json)
  "release $tag created"
  $files = @()
  foreach ($n in "control", "b1", "b1gate", "b2p25", "b2p75", "control_s2", "v1_control", "v1_b1") {
    foreach ($ep in 9, 24, 49, 99, 149, 199, 299, 399) {
      $f = "$R\job-outputs\checkpoints\$n\model_epo$ep.ckpt"
      if (Test-Path $f) { $files += @{ path = $f; name = "${n}_epo$ep.ckpt" } }
    }
  }
  Compress-Archive -Path "$L\*.txt" -DestinationPath "$R\logs_full.zip" -Force
  $files += @{ path = "$R\logs_full.zip"; name = "logs_full.zip" }
  foreach ($x in $files) {
    $u = "https://uploads.github.com/repos/$repo/releases/$($rel.id)/assets?name=$($x.name)"
    curl.exe -s --fail -X POST -H "Authorization: Bearer $tok" -H "Content-Type: application/octet-stream" --data-binary "@$($x.path)" $u -o NUL
    if ($LASTEXITCODE -eq 0) { "uploaded $($x.name)" } else { "FAILED $($x.name)" }
  }
  "done: https://github.com/$repo/releases/tag/$tag"
}

function Pipeline {
  Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
  [W.P]::SetThreadExecutionState([uint32]2147483649) | Out-Null   # keep the PC awake while this window runs
  Log pipeline.txt "start $(Get-Date)"
  Push-Results "started" | Out-Null
  $okp = $false; try { $okp = [bool](Prep | Select-Object -Last 1) } catch { Log pipeline.txt "error: $_" }
  if (-not $okp) { Log pipeline.txt "PREP FAILED $(Get-Date) - see prep.txt"; Push-Results "prep failed" | Out-Null; return }
  Log pipeline.txt "data ready $(Get-Date)"; $fd = Fix-Data; Log pipeline.txt $fd; Push-Results "data ready" | Out-Null
  if ($fd -match "fully extracted 0$") { Log pipeline.txt "STOPPED: no usable clips, see prep.txt"; Push-Results "STOPPED - no clips" | Out-Null; return }
  Write-FtYaml
  $B1 = ", model.p_frame.memory_activation: hard_tanh, model.p_frame.gate_activation: hard_sigmoid"
  # Keep the first control/B1 runs (v1: every restart replayed the same samples) under v1_* and train them again.
  $CK = "$R\job-outputs\checkpoints"
  if ((Test-Path "$CK\control") -and -not (Test-Path "$CK\v1_control")) {
    foreach ($n in "control", "b1") {
      Rename-Item "$CK\$n" "v1_$n"
      if (Test-Path "$L\$n.txt") { Rename-Item "$L\$n.txt" "v1_$n.txt" }
    }
    Log pipeline.txt "v1 control/b1 kept as v1_control, v1_b1 (repeated samples); retraining with a new seed per chunk"
  }
  # Each run: settings and seed base. All start from the released MLVC checkpoint.
  $PHASES = @(
    @{ label = "Queue A"; runs = [ordered]@{ "control" = @("", 0); "b1" = @($B1, 0) } },
    @{ label = "Queue B+C"; runs = [ordered]@{
        "b1gate"     = @("$B1, model.p_frame.input_gate: true", 0)   # Run 3: B1 + input gate
        "b2p25"      = @(", train.i_frame_dropout: 0.25", 0)          # Run 4: B2, p = 0.25
        "b2p75"      = @(", train.i_frame_dropout: 0.75", 0)          # Run 5: B2, p = 0.75
        "control_s2" = @("", 2) } }                                   # Run 7: control, other seeds
  )
  if (-not (Select-String -Path "$C\src\models\dmc_6\dmc_61sb.py" -Pattern "input_gate" -Quiet)) {
    $PHASES[1].runs.Remove("b1gate"); Log pipeline.txt "input-gate patch missing (see patch.txt): b1gate skipped"
  }
  foreach ($ph in $PHASES) {
    for ($e = $CHUNK; $e -le $MAXEP; $e += $CHUNK) {   # the runs of a phase advance together, 2 epochs at a time
      $fails = 0
      foreach ($n in $ph.runs.Keys) {
        $r = $ph.runs[$n]
        if (-not (TrainTo $n $e $r[0] $r[1])) { $fails++; Log pipeline.txt "$n FAILED at $e" }
      }
      if ($fails -eq $ph.runs.Count) { Log pipeline.txt "STOPPED: every run crashes, see the run logs $(Get-Date)"; Push-Results "STOPPED - training crashes" | Out-Null; return }
      Log pipeline.txt "$($ph.label) at epoch $e  $(Get-Date)"; Push-Results "$($ph.label) at epoch $e" | Out-Null
    }
  }
  for ($e = $MAXEP + $CHUNK; $e -le 2 * $MAXEP; $e += $CHUNK) {   # Run 6: B1 trained 2x longer (continues b1)
    if (-not (TrainTo "b1" $e $B1 0)) { Log pipeline.txt "STOPPED: b1 (Run 6) crashes at $e"; Push-Results "STOPPED - Run 6 crashes" | Out-Null; return }
    Log pipeline.txt "Run 6 (b1) at epoch $e  $(Get-Date)"; Push-Results "Run 6 (b1) at epoch $e" | Out-Null
  }
  Log pipeline.txt "ALL DONE $(Get-Date)"; Push-Results "finished" | Out-Null
}

switch ($cmd) {
  "setup"   { Setup }
  "smoke"   { Smoke }
  "github"  {
    New-Item -ItemType Directory -Force $G | Out-Null
    $a1 | Set-Content "$G\repo"; $a2 | Set-Content "$G\name"; $a3 | Set-Content "$G\email"
    $s = Read-Host "Paste GitHub token" -AsSecureString
    [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)) | Set-Content "$G\token"
    Push-Results "connection test"
  }
  "weekend" { Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" _run" -WindowStyle Minimized
              "started in a minimized window. Do NOT close it. Lock the PC (Win+L), don't log out." }
  "_run"    { Pipeline }
  "push"    { Push-Results "manual" }
  "upload"  { Upload-Models }
  "fixdata" { Fix-Data }
  "ffmpeg"  { Ensure-Ffmpeg; ffmpeg -version | Select-Object -First 1 }
  "status"  {
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv
    $dl = (Get-ChildItem "$R\data\OpenVidHD\raw" -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    "data downloaded: $([math]::Round($dl/1GB,1)) GB of 50 GB"
    "free disk: $([math]::Round((Get-PSDrive ($R.Substring(0,1))).Free/1GB)) GB"
    Get-Content "$L\pipeline.txt" -Tail 5 -ErrorAction SilentlyContinue
    foreach ($n in "control", "b1", "b1gate", "b2p25", "b2p75", "control_s2") { "== $n"; Get-Content "$L\$n.txt" -Tail 1 -ErrorAction SilentlyContinue }
  }
  default   { "usage: powershell -ExecutionPolicy Bypass -File .\lab.ps1 setup|smoke|github|weekend|status|push" }
}
