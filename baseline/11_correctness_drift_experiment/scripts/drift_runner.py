#!/usr/bin/env python3
"""Step 5 + A2: codec correctness of every encoder->decoder pair (NE/GPU/CPU) and drift bounds.

usage: drift_runner.py            all phases (main first, then A2), settings in priority order, resumable
env:   PHASE=main|a2|all   (default all)
       ONLY="mlvc_360p mlvcs_720p"   restrict to these settings (default: all 7)

Per setting x variant x clip x QP (one "job"):
  - input: the clip's 1080p MP4 scaled with ffmpeg Lanczos to the setting's size, 300 frames (as experiment 10),
    cached in phase2/5/in/
  - encode with `mlvc encode` on the NE, the GPU and the CPU at the same time (3 bitstreams)
  - decode every bitstream on the NE, the GPU and the CPU (3 lanes in parallel) -> 9 encoder->decoder pairs
  - per pair: failure, frames, kbps, PSNR-Y / PSNR-YUV against the encoder input (all frames),
    drift = PSNR-Y against the decode on the encoder's own processor (= the encoder's reconstruction), per frame
  - main variant, first clip: every bitstream decoded twice on every processor (determinism)
  - main variant: the NE (and, where it exists, GPU) bitstream compared with experiment 10's (same encoder?)
Variants: main = B* structure (I-frame every 64, MLVC's default LTR: period 16, recovery every 4 periods = 64 frames);
          A2: i32 / i16 = I-frame every 32 / 16; l32 / l16 = I-frame 64 + LTR recovery every 32 / 16 frames
          (LTR period 16 / 8, recovery period 2).
Each processor gets its own Core ML model cache (phase2/5/mcache/<unit>), because three mlvc processes run at once.
Outputs in ~/Downloads/duplexnvc-baseline/phase2/5/: r.csv (one row per pair), frames/ (per-frame PSNR and drift),
bits/ (bitstreams), cfg/ (encoder configuration printed by mlvc, once per setting and variant), fail/ (logs of failures)
"""
import csv, filecmp, json, math, os, re, shutil, subprocess, sys, threading, time
import numpy as np

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
MLVC = f"{WORK}/libmlvc/install/mac-arm64-ninja-release/bin/mlvc"
MP4 = f"{WORK}/data/vcd_1080p/mp4/th"
OUT = f"{WORK}/phase2/5"
IN, TMP, B4 = f"{OUT}/in", f"{OUT}/tmp", f"{WORK}/phase2/4b/bits"
UNITS = ["npu", "gpu", "cpu"]
QPS = [16, 24, 32, 40]
SETTINGS = ["mlvc_360p", "mlvcs_720p", "mlvcs_540p", "mlvc_540p", "mlvc_720p", "mlvcs_1080p", "mlvc_1080p"]
SIZE = {"360p": (640, 360), "540p": (960, 540), "720p": (1280, 720), "1080p": (1920, 1080)}
VARIANTS = {
    "main": ["--iframe-period", "64"],
    "i32": ["--iframe-period", "32"],
    "l32": ["--iframe-period", "64", "--ltr-period", "16", "--ltr-recovery-period", "2"],
    "i16": ["--iframe-period", "16"],
    "l16": ["--iframe-period", "64", "--ltr-start-idx", "0", "--ltr-period", "8", "--ltr-recovery-period", "2"],
}
A2 = ["i32", "l32", "i16", "l16"]
FIELDS = ["setting", "variant", "clip", "qp", "enc", "dec", "enc_ok", "dec_ok", "frames", "src_frames", "bytes", "kbps",
          "psnr_y", "psnr_yuv", "drift_db", "drift_min_db", "identical_frames", "bitexact", "det", "same_as_4b",
          "t_enc_s", "t_dec_s"]


def res_of(s):
    return s.split("_")[1]


def bundle(s):
    return f"{WORK}/bundles/mlvc" if s == "mlvc_360p" else f"{WORK}/bundles/{s}"


def frames(path, w, h):
    fb = w * h * 3 // 2
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    return mm[: (mm.size // fb) * fb].reshape(-1, fb)


def mse(a, b):
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


def db(m):
    return 100.0 if m == 0 else min(100.0, 10 * math.log10(255.0 ** 2 / m))


def make_input(clip, res):
    w, h = SIZE[res]
    out = f"{IN}/{clip[:6]}_{res}.nv12"
    if os.path.exists(out) and os.path.getsize(out) == w * h * 3 // 2 * 300:
        return out
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{MP4}/{clip}_1920x1080_30.mp4", "-frames:v", "300",
                        "-vf", f"scale={w}:{h}:flags=lanczos", "-pix_fmt", "nv12", "-f", "rawvideo", out + ".part"],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed for {clip[:6]} {res}: {r.stderr[-300:]}")
    os.replace(out + ".part", out)
    return out


def run(cmd, log):
    t = time.time()
    with open(log, "w") as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    return rc == 0, time.time() - t


def job(s, v, clip, qp, det):
    c6, res = clip[:6], res_of(s)
    W, H = SIZE[res]
    B = bundle(s)
    inp = make_input(clip, res)
    wd = f"{TMP}/{s}_{v}_{c6}_qp{qp}"
    shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
    # --- 3 encodes at the same time -------------------------------------------------------------
    enc_ok, t_enc = {}, {}

    def enc(u):
        enc_ok[u], t_enc[u] = run([MLVC, "encode", "--model-bundles-dir", B, "--compute-unit", u,
                                   "--cache-dir", f"{OUT}/mcache/{u}", "--input", inp,
                                   "--input-width", str(W), "--input-height", str(H), "--output", f"{wd}/e_{u}.mlvc",
                                   "--qp", str(qp)] + VARIANTS[v], f"{wd}/e_{u}.log")
        enc_ok[u] = enc_ok[u] and os.path.exists(f"{wd}/e_{u}.mlvc") and os.path.getsize(f"{wd}/e_{u}.mlvc") > 0

    th = [threading.Thread(target=enc, args=(u,)) for u in UNITS]
    [t.start() for t in th]; [t.join() for t in th]
    if not any(enc_ok.values()):
        keep_fail(wd, s, v, c6, qp)
        raise RuntimeError("every encode failed: " + open(f"{wd}/e_npu.log").read()[-300:])
    cfgf = f"{OUT}/cfg/{s}_{v}.txt"
    if not os.path.exists(cfgf):
        os.makedirs(f"{OUT}/cfg", exist_ok=True)
        with open(cfgf, "w") as f:
            for u in UNITS:
                f.write(f"== encode on {u}\n" + open(f"{wd}/e_{u}.log").read()[-3000:] + "\n")
    # --- decodes: one lane per processor, each decodes every bitstream (twice when det) ---------
    dec_ok, t_dec, same = {}, {}, {}

    def lane(d):
        for e in UNITS:
            if not enc_ok[e]:
                continue
            out = f"{wd}/d_{e}_{d}.nv12"
            dec_ok[(e, d)], t_dec[(e, d)] = run([MLVC, "decode", "--model-bundles-dir", B, "--compute-unit", d,
                                                 "--cache-dir", f"{OUT}/mcache/{d}",
                                                 "--input", f"{wd}/e_{e}.mlvc", "--output", out], f"{wd}/d_{e}_{d}.log")
            dec_ok[(e, d)] = dec_ok[(e, d)] and os.path.exists(out)
            if det and dec_ok[(e, d)]:
                ok2, _ = run([MLVC, "decode", "--model-bundles-dir", B, "--compute-unit", d,
                              "--cache-dir", f"{OUT}/mcache/{d}", "--input",
                              f"{wd}/e_{e}.mlvc", "--output", out[:-5] + "_2.nv12"], f"{wd}/d_{e}_{d}.2.log")
                same[(e, d)] = int(ok2 and filecmp.cmp(out, out[:-5] + "_2.nv12", shallow=False))
                if os.path.exists(out[:-5] + "_2.nv12"):
                    os.remove(out[:-5] + "_2.nv12")

    th = [threading.Thread(target=lane, args=(d,)) for d in UNITS]
    [t.start() for t in th]; [t.join() for t in th]
    # --- metrics ---------------------------------------------------------------------------------
    S = frames(inp, W, H)
    n, ys = len(S), W * H
    D = {k: frames(f"{wd}/d_{k[0]}_{k[1]}.nv12", W, H) for k, ok in dec_ok.items() if ok}
    rows, per, M = [], {}, None
    for e in UNITS:
        if not enc_ok[e]:
            for d in UNITS:
                rows.append(dict(setting=s, variant=v, clip=c6, qp=qp, enc=e, dec=d, enc_ok=0, dec_ok=0))
            continue
        nbytes = os.path.getsize(f"{wd}/e_{e}.mlvc")
        same4b = ""
        if v == "main":
            ref = f"{B4}/{s}_{e}-npu/{c6}_qp{qp}.mlvc"
            if os.path.exists(ref):
                same4b = int(filecmp.cmp(ref, f"{wd}/e_{e}.mlvc", shallow=False))
        M = D.get((e, e))
        for d in UNITS:
            base = dict(setting=s, variant=v, clip=c6, qp=qp, enc=e, dec=d, enc_ok=1, bytes=nbytes,
                        src_frames=n, same_as_4b=same4b, t_enc_s=round(t_enc[e], 1),
                        t_dec_s=round(t_dec.get((e, d), 0.0), 1), det=same.get((e, d), ""))
            if (e, d) not in D:
                rows.append(dict(base, dec_ok=0, frames=0)); continue
            X = D[(e, d)]
            k = min(n, len(X))
            my = [mse(X[i][:ys], S[i][:ys]) for i in range(k)]
            muv = [mse(X[i][ys:], S[i][ys:]) for i in range(k)]
            if M is not None and d != e:
                kk = min(k, len(M))
                dm = [0.0 if np.array_equal(X[i][:ys], M[i][:ys]) else mse(X[i][:ys], M[i][:ys]) for i in range(kk)]
                exact = int(kk == k and filecmp.cmp(f"{wd}/d_{e}_{d}.nv12", f"{wd}/d_{e}_{e}.nv12", shallow=False))
            elif d == e:
                dm, exact = [0.0] * k, 1
            else:
                dm, exact = [], ""
            py = [db(x) for x in my]
            per[(e, d)] = (py, [db(x) for x in dm])
            rows.append(dict(base, dec_ok=1, frames=k, kbps=round(nbytes * 8 / 1000 / (k / 30.0), 3) if k else "",
                             psnr_y=round(sum(py) / k, 4) if k else "",
                             psnr_yuv=round(sum((6 * a + 2 * db(b)) / 8 for a, b in zip(py, muv)) / k, 4) if k else "",
                             drift_db=round(db(sum(dm) / len(dm)), 3) if dm else "",
                             drift_min_db=round(min(db(x) for x in dm), 3) if dm else "",
                             identical_frames=sum(1 for x in dm if x == 0) if dm else "", bitexact=exact))
    # --- keep bitstreams and per-frame values, drop the decodes ----------------------------------
    bd = f"{OUT}/bits/{s}/{v}"; os.makedirs(bd, exist_ok=True)
    for e in UNITS:
        if enc_ok[e]:
            shutil.copy(f"{wd}/e_{e}.mlvc", f"{bd}/{c6}_qp{qp}_{e}.mlvc")
    fd = f"{OUT}/frames/{s}/{v}"; os.makedirs(fd, exist_ok=True)
    keys = sorted(per)
    with open(f"{fd}/{c6}_qp{qp}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i"] + [f"psnr_y_{e}_{d}" for e, d in keys] + [f"drift_{e}_{d}" for e, d in keys])
        for i in range(n):
            w.writerow([i] + [round(per[k][0][i], 3) if i < len(per[k][0]) else "" for k in keys]
                       + [round(per[k][1][i], 3) if i < len(per[k][1]) else "" for k in keys])
    if any(r.get("dec_ok") == 0 or r.get("enc_ok") == 0 for r in rows):
        keep_fail(wd, s, v, c6, qp)
    del S, D, M
    shutil.rmtree(wd, ignore_errors=True)
    return rows


def keep_fail(wd, s, v, c6, qp):
    fd = f"{OUT}/fail/{s}_{v}_{c6}_qp{qp}"
    os.makedirs(fd, exist_ok=True)
    for x in os.listdir(wd):
        if x.endswith(".log"):
            shutil.copy(f"{wd}/{x}", fd)


def main():
    phase = os.environ.get("PHASE", "all")
    only = os.environ.get("ONLY", "").split()
    for p in (OUT, IN, TMP, *(f"{OUT}/mcache/{u}" for u in UNITS)):
        os.makedirs(p, exist_ok=True)
    ev = json.load(open(f"{WORK}/data/split.json"))["evaluation"]
    sets = [s for s in SETTINGS if not only or s in only]
    plan = []
    if phase in ("main", "all"):
        plan += [(s, "main") for s in sets]
    if phase in ("a2", "all"):
        plan += [(s, v) for s in sets for v in A2]
    rcsv = f"{OUT}/r.csv"
    done = set()
    if os.path.exists(rcsv):
        done = {(r["setting"], r["variant"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(rcsv))}
    todo = [(s, v, c, q) for s, v in plan for c in ev for q in QPS if (s, v, c[:6], q) not in done]
    total = len(plan) * len(ev) * len(QPS)
    print(f"PHASE={phase}  settings={' '.join(sets)}")
    print(f"{total} jobs (setting x variant x clip x QP, 9 pairs each), {total - len(todo)} done, {len(todo)} to do")
    t0, streak, tset = time.time(), 0, {}
    for n, (s, v, clip, q) in enumerate(todo, 1):
        det = v == "main" and clip == ev[0]
        tj = time.time()
        try:
            rows = job(s, v, clip, q, det)
            streak = 0
        except Exception as ex:
            streak += 1
            print(f"   FAILED {s} {v} {clip[:6]} qp{q}: {type(ex).__name__}: {str(ex)[:300]}")
            shutil.rmtree(f"{TMP}/{s}_{v}_{clip[:6]}_qp{q}", ignore_errors=True)
            if streak >= 6:
                sys.exit("== 6 jobs in a row failed: stopping this pass (see the messages above)")
            continue
        new = not os.path.exists(rcsv)
        with open(rcsv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, restval="")
            if new:
                w.writeheader()
            w.writerows(rows)
        dt = time.time() - tj
        tset.setdefault((s, v), []).append(dt)
        el = (time.time() - t0) / 3600
        # remaining time: mean job time of each setting so far (any variant), else the overall mean
        mean_all = (time.time() - t0) / n
        avg = {}
        for (a, _), x in tset.items():
            avg.setdefault(a, []).extend(x)
        rem = sum((sum(avg[a]) / len(avg[a])) if a in avg else mean_all for a, _, _, _ in todo[n:]) / 3600
        bad = [f"{r['enc']}>{r['dec']}" for r in rows if r.get("dec_ok") == 0 or r.get("enc_ok") == 0]
        mm = [r for r in rows if r.get("dec_ok") == 1 and r["enc"] != r["dec"] and r.get("drift_min_db") != ""]
        worst = min((float(r["drift_min_db"]) for r in mm), default=float("nan"))
        print(f"[{n}/{len(todo)}] {time.strftime('%d %H:%M')} {s:<12} {v:<4} {clip[:6]} qp{q}  "
              f"NE>NE {next((r.get('psnr_y') for r in rows if r['enc'] == 'npu' and r['dec'] == 'npu' and r.get('dec_ok') == 1), '-')} dB  "
              f"worst drift {worst:.1f} dB  {'FAIL ' + ','.join(bad) if bad else 'all 9 ok'}"
              f"{'  det ' + ''.join(str(r.get('det', '')) for r in rows if r.get('det', '') != '') if det else ''}  "
              f"{dt:.0f} s  elapsed {el:.1f} h  left ~{rem:.1f} h")
    print(f"== pass finished: {len(todo)} jobs attempted, {(time.time() - t0) / 3600:.1f} h")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
