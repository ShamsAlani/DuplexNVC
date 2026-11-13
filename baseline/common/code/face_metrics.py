#!/usr/bin/env python3
"""Face-region and whole-frame quality of one timed run, scored offline.

Inputs
  --run       run directory of duplex_bench (frames.csv tells which source frame each outgoing AU coded)
  --decoded   outgoing stream decoded offline to NV12 (mlvc decode --input outgoing.mlvc --output dec.nv12)
  --coded     the NV12 clip that was fed to the encoder (coded resolution, e.g. 640x360)
  --display   the original clip at display resolution (e.g. 1920x1080 NV12); faces are scored here
  --faces     face boxes on the display clip (facebox.swift output)
Two views are reported:
  coded scale   decoded vs encoder input, same resolution: codec distortion only (comparable to MLVC's PSNR)
  display scale decoded upscaled (Lanczos) to the display size vs the original: what the viewer sees,
                the scale at which different resolutions and crops can be compared fairly
"""
import argparse, csv, json, math
import numpy as np
import cv2


def nv12_reader(path, w, h):
    fb = w * h * 3 // 2
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    n = mm.size // fb
    return n, (lambda i: np.asarray(mm[i * fb:(i + 1) * fb]).reshape(h * 3 // 2, w))


def y_of(nv12, h):
    return nv12[:h].astype(np.float64)


def rgb_of(nv12):
    return cv2.cvtColor(nv12, cv2.COLOR_YUV2RGB_NV12)


def psnr(a, b):
    mse = np.mean((a - b) ** 2)
    return 100.0 if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--decoded", required=True)
    ap.add_argument("--coded", required=True); ap.add_argument("--coded-size", default="640x360")
    ap.add_argument("--display", required=True); ap.add_argument("--display-size", default="1920x1080")
    ap.add_argument("--faces", required=True)
    ap.add_argument("--min-face", type=int, default=32, help="skip LPIPS for faces smaller than this (px)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cw, ch = map(int, a.coded_size.split("x"))
    dw, dh = map(int, a.display_size.split("x"))

    # Outgoing access units are written in encode order; map each to the source frame it coded.
    rows = [r for r in csv.DictReader(open(f"{a.run}/frames.csv")) if r["dir"] == "E" and r["ok"] == "1"]
    src_of = [int(r["src"]) for r in rows]
    warm = [r["warmup"] == "1" for r in rows]
    faces = {f["i"]: f["faces"] for f in json.load(open(a.faces))["frames"]}

    n_dec, dec = nv12_reader(a.decoded, cw, ch)
    _, cod = nv12_reader(a.coded, cw, ch)
    _, dis = nv12_reader(a.display, dw, dh)
    if n_dec != len(src_of):
        print(f"WARNING: {n_dec} decoded frames but {len(src_of)} encoded records; using the shorter")

    try:
        import lpips, torch
        net = lpips.LPIPS(net="alex", verbose=False)
    except Exception:
        net = None
        print("lpips/torch not installed: LPIPS skipped")

    per_frame, face_rows = [], []
    for i in range(min(n_dec, len(src_of))):
        if warm[i]:
            continue
        s = src_of[i]
        d_nv12 = dec(i)
        p_coded = psnr(y_of(d_nv12, ch), y_of(cod(s), ch))
        d_rgb_up = cv2.resize(rgb_of(d_nv12), (dw, dh), interpolation=cv2.INTER_LANCZOS4)
        o_rgb = rgb_of(dis(s))
        d_y_up = cv2.cvtColor(d_rgb_up, cv2.COLOR_RGB2GRAY).astype(np.float64)
        o_y = cv2.cvtColor(o_rgb, cv2.COLOR_RGB2GRAY).astype(np.float64)
        per_frame.append({"i": i, "src": s, "psnr_y_coded": p_coded, "psnr_y_display": psnr(d_y_up, o_y)})
        for (x, y, w, h) in faces.get(s, []):
            x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dw), min(y + h, dh)
            if x1 - x0 < 4 or y1 - y0 < 4:
                continue
            fr = {"i": i, "src": s, "face_h_display": y1 - y0,
                  "face_h_coded": round((y1 - y0) * ch / dh, 1),
                  "face_psnr_y": psnr(d_y_up[y0:y1, x0:x1], o_y[y0:y1, x0:x1])}
            if net is not None and min(x1 - x0, y1 - y0) >= a.min_face:
                t = lambda im: torch.from_numpy(im[y0:y1, x0:x1].astype(np.float32) / 127.5 - 1).permute(2, 0, 1)[None]
                with torch.no_grad():
                    fr["face_lpips"] = float(net(t(d_rgb_up), t(o_rgb)))
            face_rows.append(fr)

    def m(key, rows):
        v = [r[key] for r in rows if key in r]
        return (sum(v) / len(v)) if v else float("nan")
    summary = {
        "frames_scored": len(per_frame),
        "psnr_y_coded_mean": m("psnr_y_coded", per_frame),
        "psnr_y_display_mean": m("psnr_y_display", per_frame),
        "faces_scored": len(face_rows),
        "face_psnr_y_mean": m("face_psnr_y", face_rows),
        "face_lpips_mean": m("face_lpips", face_rows),
    }
    # Face-size groups: the controller's input. Report each group, never only the average.
    for lo, hi in ((0, 32), (32, 64), (64, 128), (128, 10_000)):
        g = [r for r in face_rows if lo <= r["face_h_coded"] < hi]
        summary[f"face_psnr_y_coded_h_{lo}_{hi}"] = (m("face_psnr_y", g), len(g))
    print(json.dumps(summary, indent=2))
    if a.out:
        json.dump({"summary": summary, "frames": per_frame, "faces": face_rows}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
