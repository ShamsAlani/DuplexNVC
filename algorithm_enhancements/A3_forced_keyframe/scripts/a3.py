#!/usr/bin/env python3
"""A3: a forced key frame when the content changes, on the 11 multi-person clips of Step 8 (controller_data/).
MLVC normally sends an I-frame every 64 frames whatever happens in the picture; when people enter or leave, the
references go stale until then. A3 forces an I-frame at the change (libmlvc EncodeParams.forceIdr); the 64-frame
period restarts from it. Four policies, B* (full MLVC 360p, NE-NE) and MLVC-S 540p (NE-NE), QP 16/24/26/32/40:
  none   no forced I-frame (the default)
  truth  at every real event marked by hand in Step 8 (events_truth.csv): an oracle, the best a trigger could do
  fused  Step 8's best detector: people = max(participant faces, bodies) on every 10th frame; a new count that holds
         for 3 labelled frames (1 s) is an event; the I-frame is forced when the event is confirmed (causal)
  diff   frame difference: mean absolute luma difference (360p) between the frame and the last I-frame > 6 (0-255),
         at least 30 frames after the last I-frame
Same inputs and metrics as experiment 10 (quality_runner.py), with display-size originals at 1080p (the 720p Class E masters are
upscaled losslessly). usage: a3.py <folder with the Step 8 masters> [check]   RESUMABLE.
Output: ~/Downloads/duplexnvc-baseline/phase2/a3/ (q.csv, faces.csv, frames/, flog/, trig/, bits/)
"""
import csv, os, subprocess, sys, time
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import quality_runner as q

SRC = sys.argv[1]
CHECK = len(sys.argv) > 2 and sys.argv[2] == "check"
IDS = ["ce4peo", "cejohn", "cekris", "px2ent", "px4ppl", "px5ppl", "px7ppl", "pxcrwd", "pxdown", "pxentr", "pxleav"]
SETS = ["mlvc_360p", "mlvcs_540p"]
TRIGS = ["none", "truth", "fused", "diff"]
OUT = f"{q.WORK}/phase2/a3"
q.OUT, q.TMP, q.CACHE = OUT, f"{OUT}/tmp", f"{OUT}/cache"
q.MP4 = f"{OUT}/m1080"
q.BENCH = f"{q.WORK}/harness_a1/build/ninja-release/libmlvc_example"
CUR = {"trig": "", "flog": ""}
_run = q.run


def run(cmd):
    if cmd and cmd[0] == q.BENCH:
        cmd = cmd + ["--force-idr", CUR["trig"], "--frame-log", CUR["flog"]]
    return _run(cmd)


q.run = run


def stage():
    """display-size masters named as quality_runner.py expects: 1080p Pexels linked, 720p Class E upscaled losslessly"""
    os.makedirs(q.MP4, exist_ok=True)
    for c in IDS:
        dst = f"{q.MP4}/{c}_1920x1080_30.mp4"
        if os.path.exists(dst):
            continue
        p1080, p720 = f"{SRC}/{c}_1920x1080_30.mp4", f"{SRC}/{c}_1280x720_30.mp4"
        if os.path.exists(p1080):
            os.symlink(p1080, dst)
        else:
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p720, "-vf", "scale=1920:1080:flags=lanczos",
                                "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", "-pix_fmt", "yuv420p", dst + ".mp4"],
                               capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"upscale failed for {c}: {r.stderr[-300:]}")
            os.replace(dst + ".mp4", dst)


def events_hold(counts, hold=3):
    """Step 8's rule (s8_fusion.events): a new count that holds for `hold` labels; returns the confirming frame"""
    out, cur, n = [], None, [k for _, k in counts]
    for k in range(len(n) - hold + 1):
        if len(set(n[k:k + hold])) == 1:
            if cur is not None and n[k] != cur:
                out.append(counts[k + hold - 1][0])
            cur = n[k]
    return out


def triggers(c, inp360, nfr):
    truth = [int(r["frame"]) for r in csv.DictReader(open(f"{D}/data/events_truth.csv")) if r["clip"] == c and int(r["frame"]) > 0]
    fc, bc = {}, {}
    for r in csv.DictReader(open(f"{D}/data/faces_step8.csv")):
        if r["clip"] == c and r["participant"] == "1":
            fc[int(r["frame"])] = fc.get(int(r["frame"]), 0) + 1
    for r in csv.DictReader(open(f"{D}/data/bodies_step8.csv")):
        if r["clip"] == c:
            bc[int(r["frame"])] = bc.get(int(r["frame"]), 0) + 1
    counts = [(f, max(fc.get(f, 0), bc.get(f, 0))) for f in range(0, nfr, 10)]
    fused = [f for f in events_hold(counts) if f > 0]
    Y = np.fromfile(inp360, np.uint8).reshape(-1, 360 * 3 // 2, 640)[:, :360, :].astype(np.int16)
    diff, key = [], 0
    for t in range(1, len(Y)):
        if t - key >= 64:
            key = t; continue
        if t - key >= 30 and np.abs(Y[t] - Y[key]).mean() > 6:
            diff.append(t); key = t
    return {"none": [], "truth": truth, "fused": fused, "diff": diff}


def main():
    for p in (OUT, q.TMP, q.CACHE, f"{OUT}/trig", f"{OUT}/flog"):
        os.makedirs(p, exist_ok=True)
    stage()
    qcsv = f"{OUT}/q.csv"
    done = {(r["cfg"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(qcsv))} if os.path.exists(qcsv) else set()
    clips, qps = (IDS[3:4], [26]) if CHECK else (IDS, q.QPS)
    todo = [(c, s, t, p) for c in clips for s in SETS for t in TRIGS for p in qps if (f"a3_{t}_{s}", c, p) not in done]
    print(f"{'CHECK' if CHECK else 'FULL'}: {len(clips)} clips x {SETS} x {TRIGS} x QP {qps}; {len(todo)} runs to do")
    import lpips
    net = lpips.LPIPS(net="alex", verbose=False)
    t0, n, streak = time.time(), 0, 0
    for c in clips:
        tc = [x for x in todo if x[0] == c]
        if not tc:
            continue
        print(f"== {c}  {time.strftime('%H:%M:%S')}")
        O, faces = q.originals(c)
        inp360 = q.make_input(c, "360p")
        nfr = os.path.getsize(inp360) // (640 * 360 * 3 // 2)
        T = triggers(c, inp360, nfr)
        for t, fr in T.items():
            open(f"{OUT}/trig/{c}_{t}.txt", "w").write("\n".join(map(str, fr)) + "\n")
        print("   triggers: " + "  ".join(f"{t} {T[t]}" for t in TRIGS[1:]))
        for s in SETS:
            ts = [x for x in tc if x[1] == s]
            if not ts:
                continue
            inp = inp360 if s == "mlvc_360p" else q.make_input(c, q.res_of(s))
            for _, _, t, p in ts:
                CUR["trig"] = f"{OUT}/trig/{c}_{t}.txt"
                os.makedirs(f"{OUT}/flog/a3_{t}_{s}", exist_ok=True)
                CUR["flog"] = f"{OUT}/flog/a3_{t}_{s}/{c}_qp{p}.csv"
                q.cid = lambda s_, e, d, t=t, s=s: f"a3_{t}_{s}"
                tr = time.time()
                try:
                    row, frows = q.one(s, "npu", "npu", c, p, inp, O, faces, net)
                except Exception as ex:
                    print(f"   FAILED {t} {s} {c} qp{p}: {type(ex).__name__}: {ex}"); row = None
                n += 1
                if row is None:
                    streak += 1
                    if streak >= 8:
                        sys.exit("== 8 failures in a row: stopping")
                    continue
                streak = 0
                q.append(qcsv, q.FIELDS, [row]); q.append(f"{OUT}/faces.csv", q.FACE_FIELDS, frows)
                fl = list(csv.DictReader(open(CUR["flog"])))
                nI = sum(r["type"] == "0" for r in fl); nF = sum(r["forced"] == "1" for r in fl)
                el = time.time() - t0
                print(f"   [{n}/{len(todo)}] {s:<10} {t:<5} qp{p}  {row['kbps']:7.1f} kbps  Y {row['psnr_y']:.2f}  disp "
                      f"{row['psnr_y_display']:.2f}  face {row['face_psnr_y']:.2f} / {row['face_lpips']:.3f}  "
                      f"I {nI} (forced {nF})  {time.time() - tr:.0f} s  left ~{el / n * (len(todo) - n) / 3600:.1f} h")
            if inp != inp360:
                os.remove(inp)
        os.remove(inp360)
    print(f"== {n} runs, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
