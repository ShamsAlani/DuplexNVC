#!/usr/bin/env python3
"""Multi-person drift check: Step 5's main structure (9 encoder->decoder pairs, B* structure, QP 16/24/32/40) on the
11 Step 8 multi-person clips (the Step 8 masters, `controller_data/`: 3 HEVC Class E at 720p, 8 Pexels at 1080p), for B* (full MLVC 360p),
MLVC-S 540p and MLVC-S 720p. Same code as Step 5 (drift_runner.py), only the clips and the output folder change.
Question: does cross-processor drift on multi-person content (motion, people entering and leaving) stay where it is on
the single-person VCD clips?
usage: multi_person_runner.py <folder holding the 11 masters>   RESUMABLE. Output: ~/Downloads/duplexnvc-baseline/phase2/5m/
"""
import csv, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drift_runner as c  # Step 5's code

IDS = ["ce4peo", "cejohn", "cekris", "px2ent", "px4ppl", "px5ppl", "px7ppl", "pxcrwd", "pxdown", "pxentr", "pxleav"]
SETS = ["mlvc_360p", "mlvcs_540p", "mlvcs_720p"]
SRC = sys.argv[1]
c.OUT = f"{c.WORK}/phase2/5m"
c.IN, c.TMP = f"{c.OUT}/in", f"{c.OUT}/tmp"
c.B4 = "/nonexistent"                                   # no experiment-10 bitstreams for these clips


def master(cid):
    for n in (f"{cid}_1920x1080_30.mp4", f"{cid}_1280x720_30.mp4"):
        if os.path.exists(f"{SRC}/{n}"):
            return f"{SRC}/{n}"
    sys.exit(f"missing master for {cid} in {SRC}")


def make_input(clip, res):                              # replaces c.make_input: masters have 148-300 frames
    w, h = c.SIZE[res]
    out = f"{c.IN}/{clip[:6]}_{res}.nv12"
    if os.path.exists(out + ".ok"):
        return out
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master(clip), "-frames:v", "300",
                        "-vf", f"scale={w}:{h}:flags=lanczos", "-pix_fmt", "nv12", "-f", "rawvideo", out + ".part"],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed for {clip} {res}: {r.stderr[-300:]}")
    os.replace(out + ".part", out); open(out + ".ok", "w").close()
    return out


c.make_input = make_input


def main():
    for p in (c.OUT, c.IN, c.TMP, *(f"{c.OUT}/mcache/{u}" for u in c.UNITS)):
        os.makedirs(p, exist_ok=True)
    rcsv = f"{c.OUT}/r.csv"
    done = {(r["setting"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(rcsv))} if os.path.exists(rcsv) else set()
    todo = [(s, cl, q) for s in SETS for cl in IDS for q in c.QPS if (s, cl, q) not in done]
    print(f"{len(SETS) * len(IDS) * len(c.QPS)} jobs, {len(done)} done, {len(todo)} to do")
    t0, streak = time.time(), 0
    for n, (s, cl, q) in enumerate(todo, 1):
        tj = time.time()
        try:
            rows = c.job(s, "main", cl, q, cl == IDS[0]); streak = 0
        except Exception as ex:
            streak += 1
            print(f"   FAILED {s} {cl} qp{q}: {type(ex).__name__}: {str(ex)[:300]}")
            if streak >= 6:
                sys.exit("== 6 jobs in a row failed: stopping")
            continue
        new = not os.path.exists(rcsv)
        with open(rcsv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=c.FIELDS, restval="")
            if new:
                w.writeheader()
            w.writerows(rows)
        mm = [r for r in rows if r.get("dec_ok") == 1 and r["enc"] != r["dec"] and r.get("drift_min_db") != ""]
        worst = min((float(r["drift_min_db"]) for r in mm), default=float("nan"))
        ne = next((r.get("psnr_y") for r in rows if r["enc"] == "npu" and r["dec"] == "npu" and r.get("dec_ok") == 1), "-")
        bad = [f"{r['enc']}>{r['dec']}" for r in rows if r.get("dec_ok") == 0 or r.get("enc_ok") == 0]
        el = time.time() - t0
        print(f"[{n}/{len(todo)}] {time.strftime('%H:%M')} {s:<11} {cl} qp{q}  frames {rows[0].get('src_frames', '')}  "
              f"NE>NE {ne} dB  worst drift {worst:.1f} dB  {'FAIL ' + ','.join(bad) if bad else 'all 9 ok'}  "
              f"{time.time() - tj:.0f} s  left ~{el / n * (len(todo) - n) / 3600:.1f} h")
    print(f"== finished: {(time.time() - t0) / 3600:.1f} h")


if __name__ == "__main__":
    main()
