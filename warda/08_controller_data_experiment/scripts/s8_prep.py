#!/usr/bin/env python3
"""STEP 8 (controller data): normalise every multi-person clip, then label its faces.

usage: ~/Downloads/duplexnvc-baseline/.venv/bin/python s8_prep.py [--nv12]

Reads  $S8/clips.csv  (id,source,input,start_s,license,url,notes); `input` is a file in $S8/src.
Per clip (resumable: finished clips are skipped):
  1. master   up to 300 frames (10 s) at 30 fps, starting at start_s; shorter sources give a shorter
              master (at least 120 frames, 4 s), and its length is recorded in meta.json:
              - source >= 1080p tall: scaled to 1920x1080 with Lanczos  -> master/<id>_1920x1080_30.mp4
              - source 720p (HEVC Class E): kept at 1280x720            -> master/<id>_1280x720_30.mp4
              50/60 fps sources keep every 2nd frame; 24/25/30 fps keep every frame and are
              relabelled to 30 fps (setpts), as the baseline did, so no frame is duplicated or interpolated.
              The master is the display-scale reference (the role of VCD's 1080p MP4 in the baseline).
  2. faces    every 10th master frame (i = 0, 10, ..., 290) as JPG, Apple Vision boxes with the
              baseline's facebox -> faces/<id>.json   (all labels from this one Mac). Same format as the
              baseline's face cache ("i" = JPG index 0..29), plus "frame" = master frame index (i x 10).
  3. --nv12   optional: encoder inputs at 360p/540p/720p, same ffmpeg command as the baseline
              (scale=W:H:flags=lanczos, NV12, 300 frames). Large (~0.75 GB per clip); the Mac that
              runs the codec can regenerate them from the master with the same command.
"""
import csv, json, os, subprocess, sys

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
FACEBOX = f"{WORK}/tools/facebox"
FRAMES, MIN_FRAMES, STEP, FPS = 300, 120, 10, 30
SIZES = {"360p": (640, 360), "540p": (960, 540), "720p": (1280, 720)}


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{(r.stdout + r.stderr)[-600:]}")
    return r.stdout


def probe(path):
    out = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                         "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", path]))["streams"][0]
    n, d = out["r_frame_rate"].split("/")
    return int(out["width"]), int(out["height"]), float(n) / float(d), int(out.get("nb_read_frames", 0) or 0)


def master(c, meta):
    src = c["input"] if os.path.isabs(c["input"]) else f"{S8}/src/{c['input']}"
    m = meta.get(c["id"])
    if m:   # master already made: the source may have been deleted to save space
        out = f"{S8}/master/{c['id']}_{m['master_w']}x{m['master_h']}_30.mp4"
        if os.path.exists(out):
            return out, m
    if not os.path.exists(src):
        sys.exit(f"{c['id']}: input not found: {src}")
    w, h, fps, nf = probe(src)
    mw, mh = (1920, 1080) if h >= 1000 else (1280, 720)
    if h < 700:
        sys.exit(f"{c['id']}: source is only {w}x{h}; need at least 720p")
    out = f"{S8}/master/{c['id']}_{mw}x{mh}_30.mp4"
    keep = 2 if fps > 45 else 1
    # exact number of output frames, so ffmpeg stops by count and never has to run into the end of a short
    # source (with -r 30, some ffmpeg versions loop forever at the end of a short 25 fps clip)
    avail = int((nf - float(c.get("start_s") or 0) * fps) // keep) if nf else FRAMES
    nout = min(FRAMES, avail if avail >= FRAMES else avail - 1)
    if not os.path.exists(out):
        # wider/taller than 16:9 (e.g. 4096x2160 DCI 4K): crop the centre to 16:9 first, so faces are not squashed
        crop = "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)'," if abs(w / h - 16 / 9) > 0.01 else ""
        vf = (f"select='not(mod(n\\,{keep}))'," if keep > 1 else "") + \
             f"setpts=N/({FPS}*TB),{crop}scale={mw}:{mh}:flags=lanczos"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", str(c.get("start_s") or 0), "-i", src, "-vf", vf,
            "-r", str(FPS), "-frames:v", str(nout), "-an", "-c:v", "libx264", "-preset", "slow",
            "-crf", "10", "-pix_fmt", "yuv420p", out + ".part.mp4"])
        os.replace(out + ".part.mp4", out)
    got = probe(out)[3]
    if got < MIN_FRAMES:
        sys.exit(f"{c['id']}: master has {got} frames, fewer than {MIN_FRAMES} (source too short after start_s?)")
    return out, dict(src_w=w, src_h=h, src_fps=round(fps, 3), src_frames=nf, keep_every=keep,
                     cropped_to_16x9=abs(w / h - 16 / 9) > 0.01, master_w=mw, master_h=mh, frames=got)


def faces(c, mp4):
    fj = f"{S8}/faces/{c['id']}.json"
    if os.path.exists(fj):
        return fj
    jd = f"{S8}/frames/{c['id']}"
    os.makedirs(jd, exist_ok=True)
    sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"select='not(mod(n\\,{STEP}))'",
        "-fps_mode", "passthrough", "-q:v", "2", "-start_number", "0", f"{jd}/%04d.jpg"])
    sh([FACEBOX, jd, fj + ".part"])
    d = json.load(open(fj + ".part"))
    for f in d["frames"]:          # keep facebox's own "i" (JPG index, as the baseline's cache does)
        f["frame"] = f["i"] * STEP  # and add the master frame index
    json.dump(d, open(fj, "w"), indent=1)
    os.remove(fj + ".part")
    return fj


def nv12(c, mp4):
    for res, (w, h) in SIZES.items():
        out = f"{S8}/nv12/{c['id']}_{res}.nv12"
        if os.path.exists(out):
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-frames:v", str(FRAMES),
            "-vf", f"scale={w}:{h}:flags=lanczos", "-pix_fmt", "nv12", "-f", "rawvideo", out])


def main():
    if not os.path.exists(FACEBOX):
        sys.exit("run ./s8_setup first (facebox missing)")
    for d in ("master", "frames", "faces"):
        os.makedirs(f"{S8}/{d}", exist_ok=True)
    clips = [r for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["id"].strip()]
    ids = [c["id"] for c in clips]
    short = [i[:6] for i in ids]
    if len(set(ids)) != len(ids) or len(set(short)) != len(short):
        sys.exit("clip ids must be unique, and unique in their first 6 characters "
                 "(the baseline scripts cache by clip[:6])")
    meta = {}
    mf = f"{S8}/master/meta.json"
    if os.path.exists(mf):
        meta = json.load(open(mf))
    for k, c in enumerate(clips, 1):
        print(f"[{k}/{len(clips)}] {c['id']}", flush=True)
        mp4, m = master(c, meta)
        meta[c["id"]] = m
        json.dump(meta, open(mf, "w"), indent=1)
        fj = faces(c, mp4)
        n = sum(len(f["faces"]) for f in json.load(open(fj))["frames"])
        nl = len(json.load(open(fj))["frames"])
        print(f"    master {m['master_w']}x{m['master_h']}, {m.get('frames', FRAMES)} frames, from "
              f"{m['src_w']}x{m['src_h']} @ {m['src_fps']} fps, {n} faces in {nl} labelled frames")
        if "--nv12" in sys.argv:
            nv12(c, mp4)
    print("done. next: s8_table.py")


if __name__ == "__main__":
    main()
