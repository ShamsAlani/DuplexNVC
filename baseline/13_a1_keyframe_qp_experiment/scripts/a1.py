#!/usr/bin/env python3
"""A1: more bits for key frames and LTR frames. B* (full MLVC 360p, encoder and decoder on the NE), 20 evaluation
clips, QP 16/24/26/32/40, the method of experiment 10 (q.py: Lanczos input from the 1080p MP4, coded, display and
face quality), with a QP offset on I-frames and on the frames libmlvc marks as long-term references (LTR).

Configurations (offset on I-frames / on the other LTR frames):
  o0  0 / 0     check: bitstreams must be identical to experiment 10's B* bitstreams
  b2 -2 / -2    b4 -4 / -4    b6 -6 / -6     both roles
  i4 -4 / 0     only I-frames
  l4  0 / -4    only LTR frames
usage: a1.py [check]   check = first clip, QP 26, o0 and b4 only (pilot). RESUMABLE.
Output: ~/Downloads/duplexnvc-baseline/phase2/a1/  q.csv, faces.csv, flog/<cfg>/<clip>_qp<QP>.csv (per-frame type,
LTR, QP, bytes), bits/, frames/. Face boxes and originals are reused from experiment 10's cache.
"""
import csv, filecmp, json, os, sys, time
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import q  # experiment 10's quality code

BENCH_A1 = f"{q.WORK}/harness_a1/build/ninja-release/libmlvc_example"
CFGS = {"o0": (0, 0), "b2": (-2, -2), "b4": (-4, -4), "b6": (-6, -6), "i4": (-4, 0), "l4": (0, -4)}
OUT = f"{q.WORK}/phase2/a1"
B4BITS = f"{q.WORK}/phase2/4b/bits/mlvc_360p_npu-npu"
q.OUT, q.TMP = OUT, f"{OUT}/tmp"                     # q.CACHE stays phase2/4b/cache (originals + face boxes)
q.BENCH = BENCH_A1
CUR = {"tag": "o0", "flog": ""}
_run = q.run


def run(cmd):                                        # add the A1 flags to every encode
    if cmd and cmd[0] == BENCH_A1:
        di, dl = CFGS[CUR["tag"]]
        cmd = cmd + ["--qp-i-offset", str(di), "--qp-ltr-offset", str(dl), "--frame-log", CUR["flog"]]
    return _run(cmd)


q.run = run
q.cid = lambda s, e, d: f"a1_{CUR['tag']}"


def main():
    check = len(sys.argv) > 1 and sys.argv[1] == "check"
    for p in (OUT, q.TMP, q.CACHE):
        os.makedirs(p, exist_ok=True)
    ev = json.load(open(f"{q.WORK}/data/split.json"))["evaluation"]
    clips, qps, tags = (ev[:1], [26], ["o0", "b4"]) if check else (ev, q.QPS, list(CFGS))
    qcsv = f"{OUT}/q.csv"
    done = {(r["cfg"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(qcsv))} if os.path.exists(qcsv) else set()
    todo_all = [(c, t, p) for c in clips for t in tags for p in qps if (f"a1_{t}", c[:6], p) not in done]
    print(f"{'CHECK' if check else 'FULL'}: {len(clips)} clips x {len(tags)} configurations x QP {qps}; "
          f"{len(todo_all)} runs to do")
    import lpips
    net = lpips.LPIPS(net="alex", verbose=False)
    t0, n, streak, same = time.time(), 0, 0, [0, 0]
    for ci, clip in enumerate(clips):
        c6 = clip[:6]
        todo = [(t, p) for c, t, p in todo_all if c == clip]
        if not todo:
            continue
        print(f"== clip {ci + 1}/{len(clips)} {c6}  {time.strftime('%H:%M:%S')}")
        O, faces = q.originals(clip)
        inp = q.make_input(clip, "360p")
        for t, p in todo:
            CUR["tag"] = t
            os.makedirs(f"{OUT}/flog/{t}", exist_ok=True)
            CUR["flog"] = f"{OUT}/flog/{t}/{c6}_qp{p}.csv"
            tr = time.time()
            try:
                row, frows = q.one("mlvc_360p", "npu", "npu", clip, p, inp, O, faces, net)
            except Exception as ex:
                print(f"   FAILED {t} {c6} qp{p}: {type(ex).__name__}: {ex}"); row = None
            n += 1
            if row is None:
                streak += 1
                if streak >= 8:
                    sys.exit("== 8 failures in a row: stopping")
                continue
            streak = 0
            row["setting"] = f"qpI{CFGS[t][0]:+d}_qpLTR{CFGS[t][1]:+d}"
            q.append(qcsv, q.FIELDS, [row]); q.append(f"{OUT}/faces.csv", q.FACE_FIELDS, frows)
            chk = ""
            if t == "o0":
                ref = f"{B4BITS}/{c6}_qp{p}.mlvc"
                if os.path.exists(ref):
                    ok = filecmp.cmp(ref, f"{OUT}/bits/a1_o0/{c6}_qp{p}.mlvc", shallow=False)
                    same[0] += ok; same[1] += 1
                    chk = "  same as exp. 10: " + ("YES" if ok else "NO")
            fl = list(csv.DictReader(open(CUR["flog"])))
            nI = sum(r["type"] == "0" for r in fl); nL = sum(r["ltr"] == "1" and r["type"] != "0" for r in fl)
            el = time.time() - t0
            print(f"   [{n}/{len(todo_all)}] {t} qp{p}  {row['kbps']:7.1f} kbps  Y {row['psnr_y']:.2f}  disp "
                  f"{row['psnr_y_display']:.2f}  face {row['face_psnr_y']:.2f} / {row['face_lpips']:.3f}  "
                  f"I {nI}, LTR {nL}{chk}  {time.time() - tr:.0f} s  left ~{el / n * (len(todo_all) - n) / 3600:.1f} h")
        os.remove(inp)
    if same[1]:
        print(f"== offset 0 identical to experiment 10's B* bitstreams: {same[0]} of {same[1]}")
    print(f"== {n} runs, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
