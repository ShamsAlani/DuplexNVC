#!/usr/bin/env python3
"""STEP 8: dataset table, face-size groups, candidate enter/leave events, and spot-check images.

usage: ~/Downloads/duplexnvc-baseline/.venv/bin/python s8_table.py

Inputs : $S8/clips.csv, $S8/master/meta.json, $S8/faces/<id>.json  (from s8_prep.py)
         $S8/exclude.csv (optional): clip,min_face_360,reason. Faces smaller than min_face_360 px (height at
         360p) in that clip are not participants (e.g. faces printed on a poster behind the speaker). They stay
         in faces_step8.csv with participant=0 and are left out of people counts, size groups and events.
Outputs (in $S8/results/):
  faces_step8.csv    one row per face: clip, i (JPG index), frame, box, face height at the master size and at 360p, group
  dataset_table.csv  one row per clip: source, sizes, people, events, faces per size group, smallest/largest face
  groups.csv         faces per size group over the whole set (coverage check)
  events.csv         candidate events: labelled frames where the face count changes and stays changed
  check/<id>_<frame>.jpg   boxes drawn on frames 0, 150 and 290 (open them and confirm by eye)

Face-size groups use the face HEIGHT scaled to 360p: <32, 32-63, 64-127, >=128 px
(= <96, 96-191, 192-383, >=384 px at 1080p, the bins of the baseline's facesize.csv).
Check images: green = participant, red = excluded (exclude.csv).
"""
import csv, json, os, statistics as st
import cv2

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
RES = f"{S8}/results"
STEP = 10
GROUPS = [("<32", 0, 32), ("32-63", 32, 64), ("64-127", 64, 128), (">=128", 128, 10**9)]


def group(h360):
    return next(g for g, lo, hi in GROUPS if lo <= h360 < hi)


HOLD = 3   # a new face count must hold for 3 labelled frames (1 s) to count as an event


def events(counts):
    """Labelled frames where the participant count changes to a new value that holds for HOLD labels
    (filters detector flicker: a face turning away for one label is not an event)."""
    out, cur = [], None
    n = [k for _, k in counts]
    for k in range(len(n) - HOLD + 1):
        if len(set(n[k:k + HOLD])) == 1:          # stable run starts here
            if cur is not None and n[k] != cur:
                out.append((counts[k][0], cur, n[k]))
            cur = n[k]
    return out


def main():
    os.makedirs(f"{RES}/check", exist_ok=True)
    clips = [r for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["id"].strip()]
    meta = json.load(open(f"{S8}/master/meta.json"))
    excl = {}
    if os.path.exists(f"{S8}/exclude.csv"):
        excl = {r["clip"]: float(r["min_face_360"]) for r in csv.DictReader(open(f"{S8}/exclude.csv"))}
    face_rows, table, ev_rows = [], [], []
    for c in clips:
        cid = c["id"]
        m = meta[cid]
        H = m["master_h"]
        d = json.load(open(f"{S8}/faces/{cid}.json"))
        counts, hs, nbg = [], [], 0
        lim = excl.get(cid, 0)
        for fr in d["frames"]:
            frame = fr.get("frame", fr["i"] * STEP)
            k = 0
            for (x, y, w, h) in fr["faces"]:
                h360 = h * 360 / H
                part = h360 >= lim
                if part:
                    hs.append(h360); k += 1
                else:
                    nbg += 1
                face_rows.append(dict(clip=cid, i=fr["i"], frame=frame, x=x, y=y, w=w, h=h,
                                      face_h_master=h, face_h_360=round(h360, 1), group=group(h360),
                                      participant=int(part)))
            counts.append((frame, k))
        n = [k for _, k in counts]
        ev = events(counts)
        ev_rows += [dict(clip=cid, frame=f, faces_before=a, faces_after=b,
                         kind="enter" if b > a else "leave") for f, a, b in ev]
        row = dict(id=cid, source=c["source"], license=c["license"], url=c["url"], start_s=c["start_s"],
                   src_size=f"{m['src_w']}x{m['src_h']}", src_fps=m["src_fps"], keep_every=m["keep_every"],
                   master=f"{m['master_w']}x{m['master_h']}", frames=m.get("frames", 300), labelled_frames=len(counts),
                   people_max=max(n) if n else 0, people_median=st.median(n) if n else 0,
                   frames_no_face=sum(k == 0 for k in n), background_faces=nbg,
                   candidate_events=";".join(f"{f}:{a}->{b}" for f, a, b in ev),
                   smallest_face_360=round(min(hs), 1) if hs else "", largest_face_360=round(max(hs), 1) if hs else "",
                   notes=c["notes"])
        for g, _, _ in GROUPS:
            row[f"faces_{g}"] = sum(group(h) == g for h in hs)
        table.append(row)
        # spot-check images: boxes on the first, middle and last labelled frame
        last = (len(d["frames"]) - 1) * STEP
        for frame in sorted({0, (last // 20) * STEP, last}):
            cap = cv2.VideoCapture(f"{S8}/master/{cid}_{m['master_w']}x{m['master_h']}_30.mp4")
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, img = cap.read()
            cap.release()
            if not ok:
                continue
            for fr in d["frames"]:
                if fr.get("frame", fr["i"] * STEP) == frame:
                    for (x, y, w, h) in fr["faces"]:
                        col = (0, 255, 0) if h * 360 / H >= lim else (0, 0, 255)   # red = not a participant
                        cv2.rectangle(img, (x, y), (x + w, y + h), col, 3)
                        cv2.putText(img, f"{h * 360 / H:.0f}px@360p", (x, max(30, y - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, col, 2)
            cv2.imwrite(f"{RES}/check/{cid}_{frame:03d}.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])

    def write(name, rows):
        if rows:
            with open(f"{RES}/{name}", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)

    write("faces_step8.csv", face_rows)
    write("dataset_table.csv", table)
    write("events.csv", ev_rows)
    pr = [r for r in face_rows if r["participant"]]
    gtot = [dict(group=g, faces=sum(r["group"] == g for r in pr),
                 clips=len({r["clip"] for r in pr if r["group"] == g})) for g, _, _ in GROUPS]
    write("groups.csv", gtot)

    print(f"{len(table)} clips, {len(pr)} participant faces (+{len(face_rows) - len(pr)} background), "
          f"{len(ev_rows)} candidate events")
    for g in gtot:
        print(f"  face group {g['group']:>7} px @360p: {g['faces']:5d} faces in {g['clips']:2d} clips")
    for r in table:
        print(f"  {r['id']:<14} {r['source']:<8} {r['master']:>9}  people max {r['people_max']}"
              f"  median {r['people_median']}  background {r['background_faces']}"
              f"  events {r['candidate_events'] or '-'}")
    print(f"results in {RES}; open {RES}/check/*.jpg and confirm the boxes and events by eye")


if __name__ == "__main__":
    main()
