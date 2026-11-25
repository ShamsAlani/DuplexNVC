#!/usr/bin/env python3
"""A1, round 2, and E4 (A1 combined with A2's drift bound), on the 20 evaluation clips at QP 16/24/26/32/40, with the
method of experiment 10 (quality_runner.py). Offsets: QP on I-frames / on the other LTR-marked frames.
  B* (full MLVC 360p):  i8 -8/0, i10 -10/0          (round 1 stopped at -6 and was still gaining; reference = A1's o0)
  MLVC-S 540p (marks LTRs every 16 frames):  o0 0/0 (control: must equal experiment 10's bitstreams), i4 -4/0,
                                             l4 0/-4, b4 -4/-4, i8 -8/0
  MLVC-S 540p with LTR recovery every 32 frames (A2's cheapest drift bound: LTR period 16, recovery period 2):
                                             r0 0/0, rl4 0/-4, rb4 -4/-4
usage: a1b.py [check]   check = first clip, QP 26, the two o0-type controls. RESUMABLE.
Output: ~/Downloads/duplexnvc-baseline/phase2/a1b/
"""
import csv, filecmp, json, os, sys, time
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import quality_runner as q

BENCH_A1 = f"{q.WORK}/harness_a1/build/ninja-release/libmlvc_example"
REC = ["--ltr-period", "16", "--ltr-recovery-period", "2"]
CFGS = [("mlvc_360p", "i8", -8, 0, []), ("mlvc_360p", "i10", -10, 0, []),
        ("mlvcs_540p", "o0", 0, 0, []), ("mlvcs_540p", "i4", -4, 0, []), ("mlvcs_540p", "l4", 0, -4, []),
        ("mlvcs_540p", "b4", -4, -4, []), ("mlvcs_540p", "i8", -8, 0, []),
        ("mlvcs_540p", "r0", 0, 0, REC), ("mlvcs_540p", "rl4", 0, -4, REC), ("mlvcs_540p", "rb4", -4, -4, REC)]
OUT = f"{q.WORK}/phase2/a1b"
q.OUT, q.TMP = OUT, f"{OUT}/tmp"
q.BENCH = BENCH_A1
CUR = {}
_run = q.run


def run(cmd):
    if cmd and cmd[0] == BENCH_A1:
        cmd = cmd + ["--qp-i-offset", str(CUR["di"]), "--qp-ltr-offset", str(CUR["dl"]), "--frame-log", CUR["flog"]] + CUR["extra"]
    return _run(cmd)


q.run = run


def main():
    check = len(sys.argv) > 1 and sys.argv[1] == "check"
    for p in (OUT, q.TMP, q.CACHE):
        os.makedirs(p, exist_ok=True)
    ev = json.load(open(f"{q.WORK}/data/split.json"))["evaluation"]
    cfgs = [x for x in CFGS if x[1] in ("o0", "r0")] if check else CFGS
    clips, qps = (ev[:1], [26]) if check else (ev, q.QPS)
    qcsv = f"{OUT}/q.csv"
    done = {(r["cfg"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(qcsv))} if os.path.exists(qcsv) else set()
    todo = [(c, x, p) for c in clips for x in cfgs for p in qps if (f"a1b_{x[0]}_{x[1]}", c[:6], p) not in done]
    print(f"{'CHECK' if check else 'FULL'}: {len(clips)} clips x {len(cfgs)} configurations x QP {qps}; {len(todo)} runs to do")
    import lpips
    net = lpips.LPIPS(net="alex", verbose=False)
    t0, n, streak, same = time.time(), 0, 0, [0, 0]
    for ci, clip in enumerate(clips):
        c6 = clip[:6]
        tc = [x for x in todo if x[0] == clip]
        if not tc:
            continue
        print(f"== clip {ci + 1}/{len(clips)} {c6}  {time.strftime('%H:%M:%S')}")
        O, faces = q.originals(clip)
        inputs = {}
        for _, (s, tag, di, dl, extra), p in tc:
            res = q.res_of(s)
            if res not in inputs:
                inputs[res] = q.make_input(clip, res)
            CUR.update(di=di, dl=dl, extra=extra)
            name = f"a1b_{s}_{tag}"
            os.makedirs(f"{OUT}/flog/{name}", exist_ok=True)
            CUR["flog"] = f"{OUT}/flog/{name}/{c6}_qp{p}.csv"
            q.cid = lambda s_, e, d, name=name: name
            tr = time.time()
            try:
                row, frows = q.one(s, "npu", "npu", clip, p, inputs[res], O, faces, net)
            except Exception as ex:
                print(f"   FAILED {name} {c6} qp{p}: {type(ex).__name__}: {ex}"); row = None
            n += 1
            if row is None:
                streak += 1
                if streak >= 8:
                    sys.exit("== 8 failures in a row: stopping")
                continue
            streak = 0
            row["setting"] = f"{s} I{di:+d} LTR{dl:+d}{' rec32' if extra else ''}"
            q.append(qcsv, q.FIELDS, [row]); q.append(f"{OUT}/faces.csv", q.FACE_FIELDS, frows)
            chk = ""
            if tag == "o0":
                ref = f"{q.WORK}/phase2/4b/bits/{s}_npu-npu/{c6}_qp{p}.mlvc"
                if os.path.exists(ref):
                    ok = filecmp.cmp(ref, f"{OUT}/bits/{name}/{c6}_qp{p}.mlvc", shallow=False)
                    same[0] += ok; same[1] += 1; chk = "  same as exp. 10: " + ("YES" if ok else "NO")
            fl = list(csv.DictReader(open(CUR["flog"])))
            nI = sum(r["type"] == "0" for r in fl); nL = sum(r["ltr"] == "1" and r["type"] != "0" for r in fl)
            nR = sum(r["type"] == "2" for r in fl)
            el = time.time() - t0
            print(f"   [{n}/{len(todo)}] {s:<10} {tag:<4} qp{p}  {row['kbps']:7.1f} kbps  Y {row['psnr_y']:.2f}  disp "
                  f"{row['psnr_y_display']:.2f}  face {row['face_psnr_y']:.2f} / {row['face_lpips']:.3f}  I {nI}, LTR {nL}, "
                  f"recovery {nR}{chk}  {time.time() - tr:.0f} s  left ~{el / n * (len(todo) - n) / 3600:.1f} h")
        for f in inputs.values():
            os.remove(f)
    if same[1]:
        print(f"== MLVC-S 540p offset 0 identical to experiment 10's bitstreams: {same[0]} of {same[1]}")
    print(f"== {n} runs, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
