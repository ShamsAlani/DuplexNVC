#!/usr/bin/env python3
"""Small quality helpers for the baseline.

  drift   two decodes of the SAME bitstream (e.g. on NE and on GPU): per-frame PSNR between them
          python3 quality_tools.py drift dec_ne.nv12 dec_gpu.nv12 640x360 [--iframe-period 64]
  psnr    decoded vs original, per frame and mean (Y and YUV 6:1:1)
          python3 quality_tools.py psnr decoded.nv12 original.nv12 640x360
  bdrate  Bjontegaard delta rate (piecewise cubic, as in common test conditions)
          python3 quality_tools.py bdrate --ref 210:34.1,330:36.0,520:37.8,800:39.4 --test 200:34.5,...
"""
import argparse, math, sys
import numpy as np


def frames(path, w, h):
    fb = w * h * 3 // 2
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    return mm[: (mm.size // fb) * fb].reshape(-1, fb), fb


def psnr_planes(a, b, w, h):
    ys = w * h
    out = []
    for p in (slice(0, ys), slice(ys, None)):
        mse = np.mean((a[p].astype(np.float64) - b[p].astype(np.float64)) ** 2)
        out.append(100.0 if mse == 0 else 10 * math.log10(255 ** 2 / mse))
    return out  # [Y, UV]


def cmd_drift(a):
    w, h = map(int, a.size.split("x"))
    A, _ = frames(a.a, w, h)
    B, _ = frames(a.b, w, h)
    n = min(len(A), len(B))
    if len(A) != len(B):
        print(f"frame counts differ: {len(A)} vs {len(B)} -> decoding failure or early stop on one side")
    ys = [psnr_planes(A[i], B[i], w, h)[0] for i in range(n)]
    identical = sum(1 for y in ys if y >= 100.0)
    print(f"frames compared {n}; bit-identical {identical}; Y-PSNR between decodes: "
          f"mean {np.mean(ys):.2f} dB, min {np.min(ys):.2f} dB")
    if a.iframe_period:
        pos = np.arange(n) % a.iframe_period
        for lo, hi in ((0, 1), (1, 16), (16, 32), (32, 48), (48, a.iframe_period)):
            sel = [ys[i] for i in range(n) if lo <= pos[i] < hi]
            if sel:
                print(f"  frames {lo:2d}-{hi - 1:2d} after an I-frame: mean {np.mean(sel):6.2f} dB  min {np.min(sel):6.2f} dB")


def cmd_psnr(a):
    w, h = map(int, a.size.split("x"))
    D, _ = frames(a.decoded, w, h)
    O, _ = frames(a.original, w, h)
    n = min(len(D), len(O))
    y, uv = zip(*(psnr_planes(D[i], O[i], w, h) for i in range(n)))
    yuv = [(6 * a_ + 2 * b_) / 8 for a_, b_ in zip(y, uv)]  # 6:1:1 weighting, U and V pooled (approximation)
    if a.csv:
        print(f"{n},{np.mean(y):.4f},{np.mean(yuv):.4f}")
    else:
        print(f"frames {n}: PSNR-Y {np.mean(y):.3f} dB, PSNR-YUV(6:1:1) {np.mean(yuv):.3f} dB")


def bd_rate(ref, test):
    """Average bitrate difference (%) of test vs ref at equal PSNR. Negative = test needs fewer bits."""
    from scipy.interpolate import PchipInterpolator
    r = sorted(ref, key=lambda p: p[1]); t = sorted(test, key=lambda p: p[1])
    lo, hi = max(r[0][1], t[0][1]), min(r[-1][1], t[-1][1])
    if lo >= hi:
        raise ValueError("PSNR ranges do not overlap")
    fr = PchipInterpolator([p[1] for p in r], [math.log10(p[0]) for p in r])
    ft = PchipInterpolator([p[1] for p in t], [math.log10(p[0]) for p in t])
    q = np.linspace(lo, hi, 1000)
    diff = np.trapezoid(ft(q) - fr(q), q) / (hi - lo) if hasattr(np, "trapezoid") else np.trapz(ft(q) - fr(q), q) / (hi - lo)
    return (10 ** diff - 1) * 100


def parse_pts(s):
    return [tuple(map(float, p.split(":"))) for p in s.split(",")]


def cmd_bdrate(a):
    print(f"BD-rate: {bd_rate(parse_pts(a.ref), parse_pts(a.test)):+.2f} %")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("drift"); d.add_argument("a"); d.add_argument("b"); d.add_argument("size")
    d.add_argument("--iframe-period", type=int, default=64)
    p = sp.add_parser("psnr"); p.add_argument("decoded"); p.add_argument("original"); p.add_argument("size")
    p.add_argument("--csv", action="store_true", help="print frames,psnr_y,psnr_yuv only")
    b = sp.add_parser("bdrate"); b.add_argument("--ref", required=True); b.add_argument("--test", required=True)
    a = ap.parse_args()
    {"drift": cmd_drift, "psnr": cmd_psnr, "bdrate": cmd_bdrate}[a.cmd](a)
