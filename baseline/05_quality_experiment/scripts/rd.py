"""Rate-distortion (+ optional face quality) of full MLVC 360p, per clip, untimed.

usage: python3 rd.py CLIPS_TXT OUT_CSV
CLIPS_TXT lines: <name> <nv12_640x360> [<mp4_1920x1080 original>]
For each clip and QP in 16 24 32 40: encode (duplex_bench prepare, NE) -> decode (mlvc decode, NE)
-> kbps, PSNR-Y and PSNR-YUV(6:1:1) at coded scale.
If an MP4 original is given: every 10th frame is upscaled (Lanczos) to 1920x1080 and compared with the
original inside Apple Vision face boxes -> face PSNR-Y and LPIPS at display scale, by coded face height.
"""
import csv, json, math, os, shutil, subprocess, sys, statistics as st
import numpy as np

W, H, DW, DH, STEP = 640, 360, 1920, 1080, 10
QPS = [16, 24, 32, 40]
WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
BENCH = f"{WORK}/harness/build/ninja-release/libmlvc_example"
MLVC = f"{WORK}/libmlvc/install/mac-arm64-ninja-release/bin/mlvc"
FACEBOX = f"{WORK}/tools/facebox"
BUNDLES = f"{WORK}/bundles/mlvc"
FB = W * H * 3 // 2


def nv12_frames(path, w, h):
    fb = w * h * 3 // 2
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    return mm[: (mm.size // fb) * fb].reshape(-1, fb)


def psnr(a, b):
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return 100.0 if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def originals(name, mp4, tmp):
    """Every STEP-th original frame at 1080p (NV12) + Vision face boxes on the same frames."""
    jpg = os.path.join(tmp, f"{name}_jpg"); os.makedirs(jpg, exist_ok=True)
    raw = os.path.join(tmp, f"{name}_1080_sampled.nv12")
    sel = f"select='not(mod(n\\,{STEP}))'"
    run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", sel, "-fps_mode", "passthrough",
         "-f", "rawvideo", "-pix_fmt", "nv12", raw])
    run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", sel, "-fps_mode", "passthrough",
         "-q:v", "2", "-start_number", "0", os.path.join(jpg, "%04d.jpg")])
    faces = os.path.join(tmp, f"{name}_faces.json")
    ok, msg = run([FACEBOX, jpg, faces]) if os.path.exists(FACEBOX) else (False, "no facebox")
    shutil.rmtree(jpg, ignore_errors=True)
    if not ok or not os.path.exists(faces):
        print(f"   faces skipped for {name}: {msg.strip()[-120:]}")
        return raw, None
    return raw, {f["i"]: f["faces"] for f in json.load(open(faces))["frames"]}


def main():
    clips = [l.split() for l in open(sys.argv[1]) if l.strip()]
    out = sys.argv[2]
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), "rd_tmp"); os.makedirs(tmp, exist_ok=True)
    try:
        import cv2
    except Exception:
        cv2 = None
    net = None
    try:
        import lpips, torch
        net = lpips.LPIPS(net="alex", verbose=False)
    except Exception as e:
        print("LPIPS unavailable:", e)
    rows = []
    for c in clips:
        name, nv12 = c[0], c[1]
        mp4 = c[2] if len(c) > 2 else None
        src = nv12_frames(nv12, W, H)
        n = len(src)
        orig, faces = (None, None)
        if mp4 and cv2 is not None:
            orig, faces = originals(name, mp4, tmp)
        for qp in QPS:
            d = os.path.join(tmp, f"{name}_qp{qp}")
            ok1, m1 = run([BENCH, "prepare", "--input", nv12, "--size", f"{W}x{H}", "--qp", str(qp),
                           "--bundles", BUNDLES, "--iframe-period", "64", "--out-dir", d])
            dec = os.path.join(d, "dec.nv12")
            ok2, m2 = run([MLVC, "decode", "--model-bundles-dir", BUNDLES, "--input", os.path.join(d, "incoming.mlvc"),
                           "--output", dec]) if ok1 else (False, m1)
            if not (ok1 and ok2 and os.path.exists(dec)):
                print(f"   {name} qp{qp}: FAILED {(m1 if not ok1 else m2).strip()[-200:]}")
                continue
            D = nv12_frames(dec, W, H)
            k = min(len(D), n)
            py = [psnr(D[i][: W * H], src[i][: W * H]) for i in range(k)]
            puv = [psnr(D[i][W * H:], src[i][W * H:]) for i in range(k)]
            byts = os.path.getsize(os.path.join(d, "incoming.mlvc"))
            row = dict(clip=name, qp=qp, frames=k, bytes=byts, kbps=byts * 8 / 1000 / (k / 30.0),
                       psnr_y=st.mean(py), psnr_yuv=st.mean((6 * a + 2 * b) / 8 for a, b in zip(py, puv)),
                       decoded_frames=len(D), source_frames=n)
            # display-scale face quality on sampled frames
            if orig is not None and cv2 is not None and os.path.exists(orig):
                O = nv12_frames(orig, DW, DH)
                fp, fl, small, fpy_d = [], [], [], []
                for j in range(len(O)):
                    i = j * STEP
                    if i >= k:
                        break
                    up = cv2.resize(cv2.cvtColor(D[i].reshape(H * 3 // 2, W), cv2.COLOR_YUV2RGB_NV12), (DW, DH),
                                    interpolation=cv2.INTER_LANCZOS4)
                    org = cv2.cvtColor(O[j].reshape(DH * 3 // 2, DW), cv2.COLOR_YUV2RGB_NV12)
                    uy = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY); oy = cv2.cvtColor(org, cv2.COLOR_RGB2GRAY)
                    fpy_d.append(psnr(uy, oy))
                    for (x, y, w, h) in (faces or {}).get(j, []):
                        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, DW), min(y + h, DH)
                        if x1 - x0 < 8 or y1 - y0 < 8:
                            continue
                        fp.append(psnr(uy[y0:y1, x0:x1], oy[y0:y1, x0:x1]))
                        small.append((y1 - y0) * H / DH)
                        if net is not None and min(x1 - x0, y1 - y0) >= 32:
                            t = lambda im: torch.from_numpy(im[y0:y1, x0:x1].astype(np.float32) / 127.5 - 1).permute(2, 0, 1)[None]
                            with torch.no_grad():
                                fl.append(float(net(t(up), t(org))))
                row.update(psnr_y_display=st.mean(fpy_d) if fpy_d else float("nan"),
                           faces=len(fp), face_psnr_y=st.mean(fp) if fp else float("nan"),
                           face_lpips=st.mean(fl) if fl else float("nan"),
                           face_h_coded_mean=st.mean(small) if small else float("nan"))
            rows.append(row)
            print(f"   {name} qp{qp}: {row['kbps']:7.1f} kbps  PSNR-Y {row['psnr_y']:.2f}  YUV {row['psnr_yuv']:.2f}"
                  + (f"  | display PSNR-Y {row['psnr_y_display']:.2f}  face PSNR-Y {row['face_psnr_y']:.2f}"
                     f"  LPIPS {row['face_lpips']:.3f}  faces {row['faces']}" if 'faces' in row else "")
                  + ("" if k == n else f"  (decoded {len(D)} of {n})"))
            shutil.rmtree(d, ignore_errors=True)
        if orig and os.path.exists(orig):
            os.remove(orig)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("clip", "qp"), k))
    with open(out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys); wr.writeheader(); wr.writerows(rows)
    print(f"\n== mean over clips per QP ({len(clips)} clips) -> {out}")
    for qp in QPS:
        g = [r for r in rows if r["qp"] == qp]
        if not g:
            continue
        def m(k):
            v = [r[k] for r in g if k in r and not math.isnan(r[k])]
            return st.mean(v) if v else float("nan")
        print(f"   QP {qp:2d}: {m('kbps'):7.1f} kbps  PSNR-Y {m('psnr_y'):.2f}  PSNR-YUV {m('psnr_yuv'):.2f}"
              f"  display PSNR-Y {m('psnr_y_display'):.2f}  face PSNR-Y {m('face_psnr_y'):.2f}  face LPIPS {m('face_lpips'):.3f}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
