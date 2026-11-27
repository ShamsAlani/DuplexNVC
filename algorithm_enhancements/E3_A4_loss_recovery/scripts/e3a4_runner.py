#!/usr/bin/env python3
"""E3 + A4 runs: e3a4 (the C++ program) on every clip, setting and QP. RESUMABLE (a finished run is skipped).

Clips:    the 20 VCD evaluation clips (talking heads, as experiments 10 and 11) and the 11 multi-person call clips of
          Step 8 / A3 (4 with people entering or leaving), 300 frames each.
Settings: B* (full MLVC 360p) and MLVC-S 540p, encoder and decoder on the NE.  QPs 24 and 32.
Each run tries every combination of loss pattern x E3 arm x A4 marking (see e3a4.cpp) on the same frames.
usage: e3a4_runner.py [check]
Output: ~/Downloads/duplexnvc-baseline/phase2/e3a4/  runs/<setting>/<clip>_qp<q>.csv (per frame) and _sum.csv (per
combination), logs/, in/ (inputs)
"""
import json, os, subprocess, sys, time

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
EXE = f"{WORK}/harness_e3a4/build/ninja-release/libmlvc_example"
OUT = f"{WORK}/phase2/e3a4"
SETTINGS = {"mlvc_360p": (f"{WORK}/bundles/mlvc", 640, 360), "mlvcs_540p": (f"{WORK}/bundles/mlvcs_540p", 960, 540)}
QPS = [24, 32]
CALL = ["ce4peo", "cejohn", "cekris", "px2ent", "px4ppl", "px5ppl", "px7ppl", "pxcrwd", "pxdown", "pxentr", "pxleav"]
CHECK = len(sys.argv) > 1 and sys.argv[1] == "check"


def clips():
    ev = json.load(open(f"{WORK}/data/split.json"))["evaluation"]
    out = [("vcd", c[:6], f"{WORK}/data/vcd_1080p/mp4/th/{c}_1920x1080_30.mp4", f"{WORK}/phase2/5/in/{c[:6]}_%s.nv12") for c in ev]
    out += [("call", c, f"{WORK}/phase2/a3/m1080/{c}_1920x1080_30.mp4", None) for c in CALL]
    return out


def make_input(group, c6, mp4, cached, w, h):
    res = f"{h}p"
    if cached and os.path.exists(cached % res) and os.path.getsize(cached % res) == w * h * 3 // 2 * 300:
        return cached % res
    out = f"{OUT}/in/{c6}_{res}.nv12"
    if os.path.exists(out) and os.path.getsize(out) == w * h * 3 // 2 * 300:
        return out
    if not os.path.exists(mp4):
        return None
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-frames:v", "300", "-vf", f"scale={w}:{h}:flags=lanczos",
                        "-pix_fmt", "nv12", "-f", "rawvideo", out + ".part"], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out + ".part") or os.path.getsize(out + ".part") != w * h * 3 // 2 * 300:
        print(f"   ffmpeg failed or short clip for {c6} {res}: {r.stderr[-200:]}")
        return None
    os.replace(out + ".part", out)
    return out


def main():
    for d in ("in", "logs", *(f"runs/{s}" for s in SETTINGS)):
        os.makedirs(f"{OUT}/{d}", exist_ok=True)
    C = clips()
    if CHECK:
        g, c6, mp4, cached = C[0]
        b, w, h = SETTINGS["mlvc_360p"]
        inp = make_input(g, c6, mp4, cached, w, h)
        if not inp:
            sys.exit("check: no input")
        o = f"{OUT}/check_{c6}.csv"
        cmd = [EXE, "--bundles", b, "--input", inp, "--size", f"{w}x{h}", "--qp", "26", "--seed", "1", "--frames", "120",
               "--out", o, "--check"]
        print("   " + " ".join(cmd[:1]) + " ... --check")
        with open(f"{OUT}/logs/check.log", "w") as lf:
            rc = subprocess.run(cmd, stdout=None, stderr=lf).returncode
        print(f"   check exit {rc} ({'OK' if rc == 0 else 'FAILED: see ' + OUT + '/logs/check.log'})")
        sys.exit(rc)
    jobs = [(g, c6, mp4, cached, s, q, seed) for seed, (g, c6, mp4, cached) in enumerate(C, 1) for s in SETTINGS for q in QPS]
    todo = [j for j in jobs if not os.path.exists(f"{OUT}/runs/{j[4]}/{j[1]}_qp{j[5]}_sum.csv")]
    print(f"{len(jobs)} runs (clip x setting x QP, 14 combinations each), {len(jobs) - len(todo)} done, {len(todo)} to do")
    t0, fails = time.time(), 0
    for n, (g, c6, mp4, cached, s, q, seed) in enumerate(todo, 1):
        b, w, h = SETTINGS[s]
        inp = make_input(g, c6, mp4, cached, w, h)
        if not inp:
            print(f"   SKIP {s} {c6}: input missing ({mp4})"); continue
        o = f"{OUT}/runs/{s}/{c6}_qp{q}.csv"
        tj = time.time()
        with open(f"{OUT}/logs/{s}_{c6}_qp{q}.log", "w") as lf:
            r = subprocess.run([EXE, "--bundles", b, "--input", inp, "--size", f"{w}x{h}", "--qp", str(q), "--seed", str(seed),
                                "--frames", "300", "--out", o], stdout=subprocess.PIPE, stderr=lf, text=True)
        dt = time.time() - tj
        lines = r.stdout.strip().splitlines()
        errs = [x.strip() for x in lines if "ERRORS" in x]
        if r.returncode not in (0, 3) or not os.path.exists(o[:-4] + "_sum.csv"):
            fails += 1
            print(f"   FAILED {s} {c6} qp{q} (exit {r.returncode}); see {OUT}/logs/{s}_{c6}_qp{q}.log")
            if fails >= 5:
                sys.exit("== 5 runs failed: stopping")
            continue
        el = (time.time() - t0) / 3600
        left = (time.time() - t0) / n * (len(todo) - n) / 3600
        key = [x.strip() for x in lines if x.strip().startswith(("p5/wait/", "p5/idr/", "p5/ltr/fixed"))]
        short = "  ".join(f'{k.split(":")[0].split("/")[1]} {float(k.split("shown ")[1].split(" dB")[0]):.2f}' for k in key)
        print(f"[{n}/{len(todo)}] {time.strftime('%d %I:%M %p')} {s:<11} {g:<4} {c6} qp{q}  5% loss, dB shown: {short}"
              f"{'  CHECK ERRORS: ' + str(len(errs)) if errs else ''}  {dt:.0f} s  elapsed {el:.1f} h  left ~{left:.1f} h")
    print(f"== runs finished  {time.strftime('%d %b %I:%M %p')}")


if __name__ == "__main__":
    main()
