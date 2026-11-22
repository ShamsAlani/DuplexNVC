"""Step 7 detection recall: the smallest face the scene analyzer detects, by face size and analysis resolution.

The scene analyzer runs Apple Vision face detection (VNDetectFaceRectanglesRequest, the baseline's facebox) on the
CAMERA FRAME THE ENCODER GETS, i.e. at the call resolution (360p, 540p, 720p), not on the display-size original.
The reference is the Step 8 labels: the same detector on the display-size masters (1080p or 720p), every 10th frame,
participants only (exclude.csv: poster faces left out).

For every labelled frame of every Step 8 clip, the master is scaled down with Lanczos (as the encoder input is made)
and facebox runs on it. A reference face counts as DETECTED when a box at the lower resolution, scaled back to the
master size, overlaps it with IoU >= 0.5 (one-to-one, best overlap first). IoU >= 0.3 is reported as well.

Reads  ~/Downloads/duplexnvc-baseline/phase2/step8/{clips.csv, exclude.csv, master/, faces/}
Writes ~/Downloads/duplexnvc-baseline/phase2/step7/{frames/, faces/, results/}
  results/recall_by_size.csv     resolution x face-size group (<32, 32-63, 64-127, >=128 px at 360p): faces, detected, recall
  results/recall_curve.csv       resolution x 4-px size bins (face height at 360p): recall
  results/smallest_face.csv      per resolution: smallest face detected; size from which every 4-px bin has recall >= 50 / 90 / 100 %
  results/recall_by_clip.csv     resolution x clip: faces, detected, recall, extra boxes
  results/extra_boxes.csv        boxes at the lower resolution that match no participant (poster faces / others)
  results/faces_step7.csv        one row per reference face per resolution: size, detected, IoU
  results/check/<clip>_360p.jpg  the 360p frame with the most misses: green = detected, red = missed
"""
import csv, glob, json, os, subprocess, sys
import cv2

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
S7 = f"{WORK}/phase2/step7"
RES = f"{S7}/results"
FACEBOX = f"{WORK}/tools/facebox"
STEP = 10
SIZES = [("360p", 640, 360), ("540p", 960, 540), ("720p", 1280, 720), ("1080p", 1920, 1080)]
GROUPS = [("<32", 0, 32), ("32-63", 32, 64), ("64-127", 64, 128), (">=128", 128, 10**9)]
IOU, IOU_LOOSE = 0.5, 0.3


def group(h):
    return next(g for g, lo, hi in GROUPS if lo <= h < hi)


def iou(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx)); iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / (aw * ah + bw * bh - inter) if inter else 0.0


def match(ref, test, thr):
    """one-to-one, best overlap first. Returns {ref index: (test index, iou)}"""
    pairs = sorted(((iou(r, t), i, j) for i, r in enumerate(ref) for j, t in enumerate(test)), reverse=True)
    used_r, used_t, out = set(), set(), {}
    for v, i, j in pairs:
        if v < thr: break
        if i in used_r or j in used_t: continue
        used_r.add(i); used_t.add(j); out[i] = (j, v)
    return out


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-800:]}")
    return r.stdout


def main():
    for p in (FACEBOX, f"{S8}/clips.csv", f"{S8}/master/meta.json"):
        if not os.path.exists(p):
            sys.exit(f"MISSING {p}  (this must run on the Mac that made Step 8)")
    os.makedirs(f"{RES}/check", exist_ok=True)
    clips = [r["id"].strip() for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["id"].strip()]
    meta = json.load(open(f"{S8}/master/meta.json"))
    excl = {r["clip"]: float(r["min_face_360"]) for r in csv.DictReader(open(f"{S8}/exclude.csv"))} if os.path.exists(f"{S8}/exclude.csv") else {}

    face_rows, extra_rows, clip_rows = [], [], []
    for cid in clips:
        m = meta[cid]; W, H = m["master_w"], m["master_h"]
        mp4 = f"{S8}/master/{cid}_{W}x{H}_30.mp4"
        if not os.path.exists(mp4):
            sys.exit(f"MISSING {mp4}")
        ref = {f["i"]: f for f in json.load(open(f"{S8}/faces/{cid}.json"))["frames"]}
        lim = excl.get(cid, 0)
        for res, w, h in SIZES:
            if h > H:
                continue                      # never upscale: a 720p master has no 1080p test
            fd, fj = f"{S7}/frames/{cid}_{res}", f"{S7}/faces/{cid}_{res}.json"
            if not os.path.exists(fj):
                os.makedirs(fd, exist_ok=True); os.makedirs(f"{S7}/faces", exist_ok=True)
                print(f"   {cid} {res}: frames + face detection", flush=True)
                sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"select='not(mod(n\\,{STEP}))',scale={w}:{h}:flags=lanczos",
                    "-fps_mode", "passthrough", "-start_number", "0", f"{fd}/%04d.png"])
                sh([FACEBOX, fd, fj + ".part"]); os.replace(fj + ".part", fj)
            test = {f["i"]: f for f in json.load(open(fj))["frames"]}
            s = W / w                         # lower-resolution pixels -> master pixels
            nref = ndet = nextra = 0
            worst = (-1, None)
            for i, rf in ref.items():
                boxes = [b for b in rf["faces"] if b[3] * 360 / H >= lim]        # participants
                poster = [b for b in rf["faces"] if b[3] * 360 / H < lim]
                tb = [[round(x * s), round(y * s), round(bw * s), round(bh * s)] for x, y, bw, bh in test.get(i, {}).get("faces", [])]
                strict, loose = match(boxes, tb, IOU), match(boxes, tb, IOU_LOOSE)
                misses = 0
                for k, b in enumerate(boxes):
                    h360 = b[3] * 360 / H
                    det = k in strict
                    misses += not det
                    face_rows.append(dict(clip=cid, i=i, frame=i * STEP, resolution=res, face_h_360=round(h360, 1), group=group(h360),
                                          face_h_at_res=round(b[3] / s, 1), detected=int(det), iou=round(strict[k][1], 3) if det else "",
                                          detected_iou03=int(k in loose)))
                nref += len(boxes); ndet += len(strict)
                used = {j for j, _ in strict.values()}
                left = [t for j, t in enumerate(tb) if j not in used]
                pm = match(poster, left, IOU)
                for j, t in enumerate(left):
                    kind = "poster face (excluded in Step 8)" if j in {jj for jj, _ in pm.values()} else "no participant here"
                    extra_rows.append(dict(clip=cid, i=i, frame=i * STEP, resolution=res, x=t[0], y=t[1], w=t[2], h=t[3],
                                           face_h_360=round(t[3] * 360 / H, 1), kind=kind))
                    nextra += kind == "no participant here"
                if res == "360p" and misses > worst[0]:
                    worst = (misses, i, boxes, strict)
            clip_rows.append(dict(clip=cid, resolution=res, master=f"{W}x{H}", faces=nref, detected=ndet,
                                  recall_pct=round(100 * ndet / nref, 1) if nref else "", extra_boxes=nextra))
            if res == "360p" and worst[1] is not None:
                _, i, boxes, strict = worst
                img = cv2.imread(f"{fd}/{i:04d}.png")
                img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_NEAREST)
                for k, (x, y, bw, bh) in enumerate(boxes):
                    p = [int(v / s * 2) for v in (x, y, bw, bh)]
                    col = (0, 200, 0) if k in strict else (0, 0, 255)
                    cv2.rectangle(img, (p[0], p[1]), (p[0] + p[2], p[1] + p[3]), col, 2)
                    cv2.putText(img, f"{bh * 360 / H:.0f}px", (p[0], max(14, p[1] - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
                cv2.putText(img, f"{cid} frame {i * STEP} at 360p: green detected, red missed", (8, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imwrite(f"{RES}/check/{cid}_360p.jpg", img)

    # ---------- tables ----------
    def write(name, rows):
        with open(f"{RES}/{name}", "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)

    write("faces_step7.csv", face_rows); write("recall_by_clip.csv", clip_rows)
    write("extra_boxes.csv", extra_rows or [dict(clip="", i="", frame="", resolution="", x="", y="", w="", h="", face_h_360="", kind="")])
    resl = [r for r, _, _ in SIZES if any(f["resolution"] == r for f in face_rows)]
    by_size, curve, small = [], [], []
    print("\n== Detection recall by face size (face height at 360p), IoU >= 0.5")
    print("   resolution " + "".join(f"{g:>16s}" for g, _, _ in GROUPS) + "      all")
    for r in resl:
        fr = [f for f in face_rows if f["resolution"] == r]
        line = f"   {r:10s} "
        for g, _, _ in GROUPS:
            x = [f for f in fr if f["group"] == g]
            d, dl = sum(f["detected"] for f in x), sum(f["detected_iou03"] for f in x)
            by_size.append(dict(resolution=r, group=g, faces=len(x), detected=d, recall_pct=round(100 * d / len(x), 1) if x else "",
                                recall_pct_iou03=round(100 * dl / len(x), 1) if x else "", clips=len({f["clip"] for f in x})))
            line += f"{(f'{100 * d / len(x):5.1f} % of {len(x):4d}') if x else '-':>16s}"
        tot = sum(f["detected"] for f in fr)
        print(line + f"   {100 * tot / len(fr):5.1f} % of {len(fr)}")
        for lo in range(0, 132, 4):
            x = [f for f in fr if lo <= f["face_h_360"] < lo + 4]
            if x:
                curve.append(dict(resolution=r, face_h_360_from=lo, face_h_360_to=lo + 4, faces=len(x),
                                  detected=sum(f["detected"] for f in x), recall_pct=round(100 * sum(f["detected"] for f in x) / len(x), 1)))
        det = sorted(f["face_h_360"] for f in fr if f["detected"])

        bins = [c for c in curve if c["resolution"] == r]

        def size_for(target):  # lowest 4-px bin from which EVERY bin upward has recall >= target
            for k, c in enumerate(bins):
                if all(b["recall_pct"] >= 100 * target for b in bins[k:]):
                    return c["face_h_360_from"]
            return ""
        h, = [hh for rr, _, hh in SIZES if rr == r]
        small.append(dict(resolution=r, smallest_detected_face_h_360=det[0] if det else "",
                          smallest_detected_face_h_at_res=round(det[0] * h / 360, 1) if det else "",
                          recall_50pct_from_face_h_360=size_for(0.5), recall_90pct_from_face_h_360=size_for(0.9),
                          recall_100pct_from_face_h_360=size_for(1.0),
                          largest_missed_face_h_360=max((f["face_h_360"] for f in fr if not f["detected"]), default="")))
    write("recall_by_size.csv", by_size); write("recall_curve.csv", curve); write("smallest_face.csv", small)
    print("\n== Smallest face the analyzer detects (face height at 360p)")
    for s in small:
        print(f"   {s['resolution']:6s} smallest detected {s['smallest_detected_face_h_360']} px; "
              f"every size from {s['recall_50pct_from_face_h_360']} px up: >= 50 % found, from {s['recall_90pct_from_face_h_360']} px: >= 90 %, from {s['recall_100pct_from_face_h_360']} px: all; "
              f"largest missed {s['largest_missed_face_h_360']} px")
    ne = {}
    for e in extra_rows: ne[(e["resolution"], e["kind"])] = ne.get((e["resolution"], e["kind"]), 0) + 1
    print("\n== Boxes at the lower resolution that match no participant: " + (", ".join(f"{r} {k}: {n}" for (r, k), n in sorted(ne.items())) or "none"))
    print(f"\n-> {RES}/")


if __name__ == "__main__":
    main()
