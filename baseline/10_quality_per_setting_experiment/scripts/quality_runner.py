#!/usr/bin/env python3
"""Step 4b: quality of every setting on the 20 evaluation clips (the E6 method at every resolution).

usage: quality_runner.py [pilot]
  pilot  first evaluation clip, QP 24, all 9 configurations: time per run + cross-check with E6
  (none) every clip x configuration x QP not yet in q.csv (resumable)

Per clip
  - encoder input at each resolution: the 1080p MP4 scaled with ffmpeg's Lanczos filter (as the streams of 2b)
  - every 10th original 1080p frame and its Apple Vision face boxes (cached, reused by every configuration)
Per configuration x QP (same as rd_points.py of E6, generalised to any size and compute unit)
  - encode: libmlvc_example prepare --enc-cu <unit>, I-frame period 64
  - decode: mlvc decode --compute-unit <unit>
  - coded scale, all frames: PSNR-Y and PSNR-YUV (6Y+U+V)/8 against the encoder input
  - display scale, every 10th frame: decode upscaled with Lanczos (OpenCV) to 1920x1080 against the original
    (no resize at 1080p); face PSNR-Y inside the face boxes (>= 8 px), LPIPS AlexNet (faces >= 32 px)
Outputs in ~/Downloads/duplexnvc-baseline/phase2/4b/
  q.csv                  one row per configuration x clip x QP
  faces.csv              one row per scored face (for face-size groups later)
  frames/<cfg>/<clip>_qp<QP>.csv   per-frame PSNR
  bits/<cfg>/<clip>_qp<QP>.mlvc    the bitstream
"""
import csv, json, math, os, re, shutil, subprocess, sys, time, statistics as st
import numpy as np
import cv2

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
BENCH = f"{WORK}/harness/build/ninja-release/libmlvc_example"
MLVC = f"{WORK}/libmlvc/install/mac-arm64-ninja-release/bin/mlvc"
FACEBOX = f"{WORK}/tools/facebox"
MP4 = f"{WORK}/data/vcd_1080p/mp4/th"
OUT = f"{WORK}/phase2/4b"
TMP, CACHE = f"{OUT}/tmp", f"{OUT}/cache"
E6 = f"{WORK}/runs/quality_eval/rd_eval.csv"
DW, DH, STEP = 1920, 1080, 10
QPS = [16, 24, 26, 32, 40]
SIZE = {"360p": (640, 360), "540p": (960, 540), "720p": (1280, 720), "1080p": (1920, 1080)}
CFGS = [("mlvc_360p", "npu", "npu"),
        ("mlvc_540p", "npu", "npu"), ("mlvc_540p", "gpu", "npu"), ("mlvcs_540p", "npu", "npu"),
        ("mlvc_720p", "npu", "npu"), ("mlvcs_720p", "npu", "npu"), ("mlvcs_720p", "gpu", "npu"),
        ("mlvc_1080p", "npu", "npu"), ("mlvcs_1080p", "npu", "npu")]
FIELDS = ["cfg", "setting", "enc", "dec", "clip", "qp", "frames", "bytes", "kbps", "psnr_y", "psnr_yuv",
          "psnr_y_display", "faces", "face_psnr_y", "face_lpips", "face_h_coded_mean",
          "decoded_frames", "source_frames", "enc_resolved", "t_enc_s", "t_dec_s", "t_metric_s"]
FACE_FIELDS = ["cfg", "clip", "qp", "i", "face_h_display", "face_h_coded", "face_psnr_y", "face_lpips"]


def cid(s, e, d):
    return f"{s}_{e}-{d}"


def res_of(s):
    return s.split("_")[1]


def bundle(s):
    return f"{WORK}/bundles/mlvc" if s == "mlvc_360p" else f"{WORK}/bundles/{s}"


def run(cmd):
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr, time.time() - t


def nv12_frames(path, w, h):
    fb = w * h * 3 // 2
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    return mm[: (mm.size // fb) * fb].reshape(-1, fb)


def psnr(a, b):
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 100.0 if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)


def originals(clip):
    """Every STEP-th original 1080p frame (NV12) + Vision face boxes, cached per clip."""
    c6 = clip[:6]
    raw, fj = f"{CACHE}/{c6}_orig.nv12", f"{CACHE}/{c6}_faces.json"
    if not (os.path.exists(raw) and os.path.exists(fj)):
        mp4 = f"{MP4}/{clip}_1920x1080_30.mp4"
        jpg = f"{TMP}/{c6}_jpg"; os.makedirs(jpg, exist_ok=True)
        sel = f"select='not(mod(n\\,{STEP}))'"
        run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", sel, "-fps_mode", "passthrough",
             "-f", "rawvideo", "-pix_fmt", "nv12", raw + ".part"])
        run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", sel, "-fps_mode", "passthrough",
             "-q:v", "2", "-start_number", "0", os.path.join(jpg, "%04d.jpg")])
        ok, msg, _ = run([FACEBOX, jpg, fj + ".part"])
        shutil.rmtree(jpg, ignore_errors=True)
        if not ok:
            sys.exit(f"facebox FAILED for {c6}: {msg[-300:]}")
        os.replace(raw + ".part", raw); os.replace(fj + ".part", fj)
    faces = {f["i"]: f["faces"] for f in json.load(open(fj))["frames"]}
    return nv12_frames(raw, DW, DH), faces


def make_input(clip, res):
    w, h = SIZE[res]
    out = f"{TMP}/{clip[:6]}_{res}.nv12"
    ok, msg, _ = run(["ffmpeg", "-v", "error", "-y", "-i", f"{MP4}/{clip}_1920x1080_30.mp4", "-frames:v", "300",
                      "-vf", f"scale={w}:{h}:flags=lanczos", "-pix_fmt", "nv12", "-f", "rawvideo", out])
    if not ok:
        sys.exit(f"ffmpeg FAILED for {clip[:6]} {res}: {msg[-300:]}")
    return out


def one(s, e, d, clip, qp, inp, O, faces, net):
    c, c6 = cid(s, e, d), clip[:6]
    W, H = SIZE[res_of(s)]
    B = bundle(s)
    wd = f"{TMP}/{c}_{c6}_qp{qp}"; shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
    ok1, m1, t1 = run([BENCH, "prepare", "--input", inp, "--size", f"{W}x{H}", "--qp", str(qp), "--bundles", B,
                       "--iframe-period", "64", "--enc-cu", e, "--out-dir", wd])
    resolved = ",".join(sorted(set(re.findall(r"resolved=(\w+)", m1)))) or "?"
    dec = f"{wd}/dec.nv12"
    ok2, m2, t2 = run([MLVC, "decode", "--model-bundles-dir", B, "--compute-unit", d,
                       "--input", f"{wd}/incoming.mlvc", "--output", dec]) if ok1 else (False, m1, 0.0)
    if not (ok1 and ok2 and os.path.exists(dec)):
        print(f"   FAILED {c} {c6} qp{qp}: {(m1 if not ok1 else m2).strip()[-300:]}")
        shutil.rmtree(wd, ignore_errors=True)
        return None, None
    t = time.time()
    S, D = nv12_frames(inp, W, H), nv12_frames(dec, W, H)
    n, nd = len(S), len(D)
    k = min(n, nd)
    ys = W * H
    py = [psnr(D[i][:ys], S[i][:ys]) for i in range(k)]
    puv = [psnr(D[i][ys:], S[i][ys:]) for i in range(k)]
    byts = os.path.getsize(f"{wd}/incoming.mlvc")
    disp, fp, fl, fh, frows = {}, [], [], [], []
    for j in range(len(O)):
        i = j * STEP
        if i >= k:
            break
        up = cv2.cvtColor(np.asarray(D[i]).reshape(H * 3 // 2, W), cv2.COLOR_YUV2RGB_NV12)
        if (W, H) != (DW, DH):
            up = cv2.resize(up, (DW, DH), interpolation=cv2.INTER_LANCZOS4)
        org = cv2.cvtColor(np.asarray(O[j]).reshape(DH * 3 // 2, DW), cv2.COLOR_YUV2RGB_NV12)
        uy, oy = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY), cv2.cvtColor(org, cv2.COLOR_RGB2GRAY)
        disp[i] = psnr(uy, oy)
        for (x, y, w, h) in faces.get(j, []):
            x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, DW), min(y + h, DH)
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            p = psnr(uy[y0:y1, x0:x1], oy[y0:y1, x0:x1])
            fp.append(p); fh.append((y1 - y0) * H / DH)
            lp = ""
            if net is not None and min(x1 - x0, y1 - y0) >= 32:
                import torch
                tt = lambda im: torch.from_numpy(im[y0:y1, x0:x1].astype(np.float32) / 127.5 - 1).permute(2, 0, 1)[None]
                with torch.no_grad():
                    lp = float(net(tt(up), tt(org)))
                fl.append(lp)
            frows.append(dict(cfg=c, clip=c6, qp=qp, i=i, face_h_display=y1 - y0,
                              face_h_coded=round((y1 - y0) * H / DH, 1), face_psnr_y=round(p, 4),
                              face_lpips=round(lp, 5) if lp != "" else ""))
    t3 = time.time() - t
    # keep the bitstream and per-frame PSNR, drop the decode
    os.makedirs(f"{OUT}/bits/{c}", exist_ok=True); os.makedirs(f"{OUT}/frames/{c}", exist_ok=True)
    shutil.copy(f"{wd}/incoming.mlvc", f"{OUT}/bits/{c}/{c6}_qp{qp}.mlvc")
    with open(f"{OUT}/frames/{c}/{c6}_qp{qp}.csv", "w", newline="") as f:
        w_ = csv.writer(f); w_.writerow(["i", "psnr_y", "psnr_uv", "psnr_y_display"])
        for i in range(k):
            w_.writerow([i, round(py[i], 4), round(puv[i], 4), round(disp[i], 4) if i in disp else ""])
    del S, D
    shutil.rmtree(wd, ignore_errors=True)
    nan = float("nan")
    row = dict(cfg=c, setting=s, enc=e, dec=d, clip=c6, qp=qp, frames=k, bytes=byts,
               kbps=round(byts * 8 / 1000 / (k / 30.0), 3), psnr_y=round(st.mean(py), 4),
               psnr_yuv=round(st.mean((6 * a + 2 * b) / 8 for a, b in zip(py, puv)), 4),
               psnr_y_display=round(st.mean(disp.values()), 4) if disp else nan, faces=len(fp),
               face_psnr_y=round(st.mean(fp), 4) if fp else nan, face_lpips=round(st.mean(fl), 5) if fl else nan,
               face_h_coded_mean=round(st.mean(fh), 2) if fh else nan, decoded_frames=nd,
               source_frames=n, enc_resolved=resolved, t_enc_s=round(t1, 1), t_dec_s=round(t2, 1),
               t_metric_s=round(t3, 1))
    return row, frows


def append(path, fields, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerows(rows)


def main():
    pilot = len(sys.argv) > 1 and sys.argv[1] == "pilot"
    for p in (OUT, TMP, CACHE):
        os.makedirs(p, exist_ok=True)
    ev = json.load(open(f"{WORK}/data/split.json"))["evaluation"]
    clips, qps = (ev[:1], [24]) if pilot else (ev, QPS)
    qcsv = f"{OUT}/q.csv"
    done = set()
    if os.path.exists(qcsv):
        done = {(r["cfg"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(qcsv))}
    total = len(clips) * len(CFGS) * len(qps)
    left = sum(1 for c in clips for s, e, d in CFGS for q in qps if (cid(s, e, d), c[:6], q) not in done)
    print(f"{'PILOT' if pilot else 'FULL'}: {len(clips)} clips x {len(CFGS)} configurations x QP {qps}"
          f" = {total} runs, {total - left} already done, {left} to do")
    try:
        import lpips
        net = lpips.LPIPS(net="alex", verbose=False)
    except Exception as ex:
        sys.exit(f"LPIPS unavailable: {ex}")
    t0, nrun, fails, tcfg, streak = time.time(), 0, 0, {}, 0
    for ci, clip in enumerate(clips):
        c6 = clip[:6]
        todo = [(s, e, d, q) for s, e, d in CFGS for q in qps if (cid(s, e, d), c6, q) not in done]
        if not todo:
            continue
        print(f"== clip {ci + 1}/{len(clips)} {c6}  {time.strftime('%H:%M:%S')}")
        ta = time.time()
        O, faces = originals(clip)
        print(f"   originals + face boxes: {len(O)} frames, {sum(len(v) for v in faces.values())} faces"
              f" ({time.time() - ta:.0f} s)")
        for res in [r for r in SIZE if any(res_of(s) == r for s, _, _, _ in todo)]:
            inp = make_input(clip, res)
            for s, e, d, q in [x for x in todo if res_of(x[0]) == res]:
                tr = time.time()
                try:
                    row, frows = one(s, e, d, clip, q, inp, O, faces, net)
                except Exception as ex:
                    print(f"   FAILED {cid(s, e, d)} {c6} qp{q}: {type(ex).__name__}: {ex}")
                    row, frows = None, None
                nrun += 1
                if row is None:
                    fails += 1; streak += 1
                    if streak >= 8:
                        sys.exit("== 8 failures in a row: stopping this pass (see the messages above)")
                    continue
                streak = 0
                append(qcsv, FIELDS, [row]); append(f"{OUT}/faces.csv", FACE_FIELDS, frows)
                dt = time.time() - tr
                tcfg.setdefault(row["cfg"], []).append(dt)
                el = time.time() - t0
                eta = el / nrun * (left - nrun) / 3600
                print(f"   [{nrun}/{left}] {row['cfg']:<20} qp{q}  {row['kbps']:8.1f} kbps  Y {row['psnr_y']:.2f}"
                      f"  disp {row['psnr_y_display']:.2f}  face {row['face_psnr_y']:.2f} / {row['face_lpips']:.3f}"
                      f"  ({row['faces']} faces)  enc={row['enc_resolved']}  {dt:.0f} s  ETA {eta:.1f} h")
            os.remove(inp)
        del O
    print(f"== {nrun} runs, {fails} failed, {(time.time() - t0) / 60:.1f} min")
    if pilot and tcfg:
        per_clip = sum(st.mean(v) for v in tcfg.values()) * len(QPS)
        print("\n== pilot: time per run (s) and full-run estimate (20 clips x 5 QPs)")
        for c, v in tcfg.items():
            print(f"   {c:<20} {st.mean(v):6.1f} s  -> {st.mean(v) * 100 / 3600:5.2f} h")
        print(f"   total about {per_clip * 20 / 3600:.1f} h (+ about 1 min per clip for inputs and face boxes)")
        if os.path.exists(E6):
            e6 = [r for r in csv.DictReader(open(E6)) if r["clip"] == clips[0][:6] and r["qp"] == "24"]
            new = [r for r in csv.DictReader(open(qcsv)) if r["cfg"] == "mlvc_360p_npu-npu"
                   and r["clip"] == clips[0][:6] and r["qp"] == "24"]
            if e6 and new:
                a, b = e6[0], new[0]
                print(f"\n== 360p cross-check, clip {clips[0][:6]} QP 24 (E6 input = VCD 360p YUV; 4b input = Lanczos"
                      f" from the 1080p MP4)")
                for k_ in ("kbps", "psnr_y", "psnr_yuv", "psnr_y_display", "face_psnr_y", "face_lpips", "faces"):
                    print(f"   {k_:<15} E6 {float(a[k_]):9.3f}   4b {float(b[k_]):9.3f}   diff {float(b[k_]) - float(a[k_]):+8.3f}")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
