#!/usr/bin/env python3
"""E6, A2 part: A2's drift bound on all 160 VCD clips (th, th-bb, th-m, th-ob; 40 each), for confidence intervals.
Per clip: MLVC-S 540p and B* (full MLVC 360p) x QP 16/24/32/40 x {main (I-frame every 64, MLVC's default LTRs),
l32 (A2's bound: LTR recovery every 32 frames)}; encoder on the NE and the GPU, decoder on the NE and the GPU (4 pairs):
quality, failures, drift. Experiment 11's job (drift_runner.py) with the CPU left out (A2's case is the GPU decoder).
Clips are taken in turn from the four groups, so a partial run covers all of them. The 300-frame inputs are deleted
after each clip (they would take 54 GB). RESUMABLE; stop with Ctrl-C at any time.
Output: ~/Downloads/duplexnvc-baseline/phase2/e6/ (r.csv, frames/, bits/, cfg/)
"""
import csv, os, shutil, sys, time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "5"))
try:
    import drift_runner as c
except ImportError:
    import c

WORK = c.WORK
V = f"{WORK}/data/vcd_1080p"
c.OUT = f"{WORK}/phase2/e6"
c.IN, c.TMP = f"{c.OUT}/in", f"{c.OUT}/tmp"
c.B4 = f"{c.OUT}/none"
c.UNITS = ["npu", "gpu"]
SETS = ["mlvcs_540p", "mlvc_360p"]
VARS = ["main", "l32"]
GROUPS = ["th", "th-bb", "th-m", "th-ob"]
# th-m (mobile) clips are portrait, 1080x1920. E6_PORTRAIT=rotate turns them 90 degrees clockwise before scaling, so
# they run at the same landscape sizes and with the same bundles as the other groups; E6_PORTRAIT=skip leaves them out.
PORTRAIT = os.environ.get("E6_PORTRAIT", "skip")


def src(g, k):
    """(mp4 path, rotate?) or None"""
    land, port = f"{V}/mp4/{g}/{k}_1920x1080_30.mp4", f"{V}/mp4/{g}/{k}_1080x1920_30.mp4"
    if os.path.exists(land):
        return land, False
    if PORTRAIT == "rotate" and os.path.exists(port):
        return port, True
    return None


def make_input(clip, res):   # replaces drift_runner's: same output, but finds portrait clips and rotates them
    import subprocess
    w, h = c.SIZE[res]
    out = f"{c.IN}/{clip[:6]}_{res}.nv12"
    if os.path.exists(out) and os.path.getsize(out) == w * h * 3 // 2 * 300:
        return out
    g = os.path.basename(c.MP4)
    path, rot = src(g, clip)
    vf = ("transpose=1," if rot else "") + f"scale={w}:{h}:flags=lanczos"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-frames:v", "300", "-vf", vf,
                        "-pix_fmt", "nv12", "-f", "rawvideo", out + ".part"], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed for {clip[:6]} {res}: {r.stderr[-300:]}")
    os.replace(out + ".part", out)
    return out


c.make_input = make_input


def clip_list():
    L = [l.strip() for l in open(f"{V}/VCD/download/mp4_list.txt") if l.startswith("mp4/")]
    by = {g: sorted(p for p in L if p.split("/")[1] == g) for g in GROUPS}
    out = []
    for i in range(max(len(v) for v in by.values())):
        for g in GROUPS:
            if i < len(by[g]):
                out.append((g, os.path.basename(by[g][i]).split("_")[0]))
    return out


def main():
    for p in (c.OUT, c.IN, c.TMP, *(f"{c.OUT}/mcache/{u}" for u in c.UNITS)):
        os.makedirs(p, exist_ok=True)
    rcsv = f"{c.OUT}/r.csv"
    done = set()
    if os.path.exists(rcsv):
        done = {(r["setting"], r["variant"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(rcsv))}
    C = clip_list()
    have = [(g, k) for g, k in C if src(g, k)]
    jobs = [(g, k, s, q, v) for g, k in have for s in SETS for q in c.QPS for v in VARS]
    todo = [j for j in jobs if (j[2], j[4], j[1][:6], j[3]) not in done]
    print(f"E6 (A2 on all VCD clips): {len(C)} clips listed, {len(have)} usable (portrait th-m: {PORTRAIT}); {len(jobs)} jobs, "
          f"{len(jobs) - len(todo)} done, {len(todo)} to do")
    t0, streak = time.time(), 0
    for n, (g, k, s, q, v) in enumerate(todo, 1):
        c.MP4 = f"{V}/mp4/{g}"
        tj = time.time()
        try:
            rows = c.job(s, v, k, q, False)
            streak = 0
        except (Exception, SystemExit) as ex:
            streak += 1
            print(f"   FAILED {g} {k[:6]} {s} {v} qp{q}: {str(ex)[:200]}")
            shutil.rmtree(f"{c.TMP}/{s}_{v}_{k[:6]}_qp{q}", ignore_errors=True)
            if streak >= 6:
                sys.exit("== 6 jobs in a row failed: stopping")
            continue
        for r in rows:
            r["clip"] = k[:6]
        new = not os.path.exists(rcsv)
        with open(rcsv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=c.FIELDS + ["group"], restval="")
            if new:
                w.writeheader()
            w.writerows([dict(r, group=g) for r in rows])
        nxt = todo[n] if n < len(todo) else None
        if nxt is None or nxt[1] != k:              # last job of this clip: drop its inputs
            for res in ("360p", "540p"):
                p = f"{c.IN}/{k[:6]}_{res}.nv12"
                if os.path.exists(p):
                    os.remove(p)
        mm = [r for r in rows if r.get("dec_ok") == 1 and r["enc"] != r["dec"] and r.get("drift_min_db") != ""]
        worst = min((float(r["drift_min_db"]) for r in mm), default=float("nan"))
        bad = [f"{r['enc']}>{r['dec']}" for r in rows if r.get("dec_ok") == 0 or r.get("enc_ok") == 0]
        el = (time.time() - t0) / 3600; left = (time.time() - t0) / n * (len(todo) - n) / 3600
        print(f"[{n}/{len(todo)}] {time.strftime('%d %I:%M %p')} {g:<5} {k[:6]} {s:<10} {v:<4} qp{q}  worst drift {worst:.1f} dB  "
              f"{'FAIL ' + ','.join(bad) if bad else 'all 4 ok'}  {time.time() - tj:.0f} s  elapsed {el:.1f} h  left ~{left:.1f} h")
    print(f"== pass finished  {time.strftime('%d %b %I:%M %p')}")


if __name__ == "__main__":
    main()
