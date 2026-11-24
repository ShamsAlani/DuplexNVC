#!/usr/bin/env python3
"""Step 9, quality part: Apple's hardware HEVC encoder (VideoToolbox, through ffmpeg's hevc_videotoolbox) at MLVC's
own bitrates, measured exactly like MLVC in experiment 10 (same inputs, same coded/display/face metrics, same code).

Per clip and per point, the target bitrate is MLVC's bitrate for that clip at QP 16/24/26/32/40 (experiment 10):
  hevc_360p  targets = B* (full MLVC 360p)            compared with B*
  hevc_720p  targets = MLVC-S 720p                     compared with MLVC-S 720p and full MLVC 720p
Encoder: hevc_videotoolbox, hardware only (-allow_sw 0), real-time mode (-realtime 1), no B-frames (-bf 0),
an I-frame every 64 frames (-g 64, as B*), average bitrate -b:v. Decode: ffmpeg's HEVC decoder (bit-exact by standard).
usage: hv.py [check]   check = first clip, 360p, two points. RESUMABLE.
Output: ~/Downloads/duplexnvc-baseline/phase2/hv/ q.csv (column qp = the MLVC QP whose bitrate is the target),
faces.csv, frames/, bits/ (raw HEVC streams, .mlvc name kept by the shared code). Face boxes reuse experiment 10's cache.
"""
import csv, json, os, subprocess, sys, time
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "4b"))
import q  # experiment 10's quality code

OUT = f"{q.WORK}/phase2/hv"
REF = {"360p": "mlvc_360p_npu-npu", "720p": "mlvcs_720p_npu-npu"}
q.OUT, q.TMP = OUT, f"{OUT}/tmp"
CUR = {"kbps": 0}
_run = q.run


def run(cmd):
    """Replaces the MLVC encode (prepare) and decode of q.one with hardware HEVC encode and ffmpeg decode."""
    if cmd and cmd[0] == q.BENCH:
        a = dict(zip(cmd[2::2], cmd[3::2]))
        w, h = a["--size"].split("x")
        out = a["--out-dir"] + "/incoming.mlvc"
        b = int(round(CUR["kbps"] * 1000))
        ok, msg, t = _run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "nv12", "-s", f"{w}x{h}",
                           "-r", "30", "-i", a["--input"], "-c:v", "hevc_videotoolbox", "-allow_sw", "0",
                           "-realtime", "1", "-bf", "0", "-g", "64", "-b:v", str(b), "-f", "hevc", out])
        return ok, msg + " resolved=vt_hw", t
    if cmd and cmd[0] == q.MLVC and len(cmd) > 1 and cmd[1] == "decode":
        a = dict(zip(cmd[2::2], cmd[3::2]))
        return _run(["ffmpeg", "-v", "error", "-y", "-f", "hevc", "-i", a["--input"], "-f", "rawvideo",
                     "-pix_fmt", "nv12", a["--output"]])
    return _run(cmd)


q.run = run


def main():
    check = len(sys.argv) > 1 and sys.argv[1] == "check"
    for p in (OUT, q.TMP, q.CACHE):
        os.makedirs(p, exist_ok=True)
    ev = json.load(open(f"{q.WORK}/data/split.json"))["evaluation"]
    tgt = {}
    for r in csv.DictReader(open(f"{q.WORK}/phase2/4b/q.csv")):
        for res, cfg in REF.items():
            if r["cfg"] == cfg:
                tgt[(res, r["clip"], int(r["qp"]))] = float(r["kbps"])
    clips, ress, qps = (ev[:1], ["360p"], [16, 40]) if check else (ev, ["360p", "720p"], q.QPS)
    qcsv = f"{OUT}/q.csv"
    done = {(r["cfg"], r["clip"], int(r["qp"])) for r in csv.DictReader(open(qcsv))} if os.path.exists(qcsv) else set()
    todo_all = [(c, rs, p) for c in clips for rs in ress for p in qps if (f"hevc_{rs}", c[:6], p) not in done]
    print(f"{'CHECK' if check else 'FULL'}: {len(clips)} clips x {ress} x {len(qps)} target bitrates; {len(todo_all)} runs to do")
    import lpips
    net = lpips.LPIPS(net="alex", verbose=False)
    t0, n, streak = time.time(), 0, 0
    for ci, clip in enumerate(clips):
        c6 = clip[:6]
        todo = [(rs, p) for c, rs, p in todo_all if c == clip]
        if not todo:
            continue
        print(f"== clip {ci + 1}/{len(clips)} {c6}  {time.strftime('%H:%M:%S')}")
        O, faces = q.originals(clip)
        for rs in [r for r in ress if any(x == r for x, _ in todo)]:
            inp = q.make_input(clip, rs)
            q.cid = lambda s, e, d, rs=rs: f"hevc_{rs}"
            for _, p in [x for x in todo if x[0] == rs]:
                CUR["kbps"] = tgt[(rs, c6, p)]
                tr = time.time()
                setting = "mlvc_360p" if rs == "360p" else "mlvcs_720p"      # only its size is used by q.one
                try:
                    row, frows = q.one(setting, "npu", "npu", clip, p, inp, O, faces, net)
                except Exception as ex:
                    print(f"   FAILED hevc_{rs} {c6} qp{p}: {type(ex).__name__}: {ex}"); row = None
                n += 1
                if row is None:
                    streak += 1
                    if streak >= 8:
                        sys.exit("== 8 failures in a row: stopping")
                    continue
                streak = 0
                row["setting"], row["enc"], row["dec"] = f"hevc_vt_{rs}", "vt_hw", "ffmpeg"
                row["enc_resolved"] = f"target_kbps={CUR['kbps']:.1f}"
                q.append(qcsv, q.FIELDS, [row]); q.append(f"{OUT}/faces.csv", q.FACE_FIELDS, frows)
                el = time.time() - t0
                print(f"   [{n}/{len(todo_all)}] hevc_{rs} @QP{p} target {CUR['kbps']:7.1f} -> {row['kbps']:7.1f} kbps"
                      f"  Y {row['psnr_y']:.2f}  disp {row['psnr_y_display']:.2f}  face {row['face_psnr_y']:.2f} / "
                      f"{row['face_lpips']:.3f}  {time.time() - tr:.0f} s  left ~{el / n * (len(todo_all) - n) / 3600:.1f} h")
            os.remove(inp)
    print(f"== {n} runs, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
