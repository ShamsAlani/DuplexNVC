"""Recorded call clips: unpack them into Step 8's src/ and make one overview picture per clip.

    ~/Downloads/duplexnvc-baseline/.venv/bin/python rc_sheets.py <zip or folder with rc*.mov>

For each rc*.mov: size, frame rate, length, and a picture with one frame every 0.5 s, each labelled with its time,
so the second of every event can be read off. Pictures: ~/Downloads/rc_sheets/<clip>.jpg (send them to the chat).
"""
import glob, json, os, shutil, subprocess, sys, zipfile
import cv2, numpy as np

S8 = os.path.expanduser("~/Downloads/duplexnvc-baseline/phase2/step8")
OUT = os.path.expanduser("~/Downloads/rc_sheets")
STEP_S, COLS, TW = 0.5, 6, 320

src = sys.argv[1] if len(sys.argv) > 1 else ""
os.makedirs(f"{S8}/src", exist_ok=True); os.makedirs(OUT, exist_ok=True)
if src.endswith(".zip"):
    with zipfile.ZipFile(src) as z:
        for n in z.namelist():
            b = os.path.basename(n)
            if b.startswith("rc") and b.lower().endswith((".mov", ".mp4")):
                with z.open(n) as f, open(f"{S8}/src/{b}", "wb") as g: shutil.copyfileobj(f, g)
elif os.path.isdir(src):
    for p in glob.glob(f"{src}/rc*.mov") + glob.glob(f"{src}/rc*.mp4"): shutil.copy(p, f"{S8}/src/")
clips = sorted(glob.glob(f"{S8}/src/rc*.mov") + glob.glob(f"{S8}/src/rc*.mp4"))
if not clips: sys.exit("no rc*.mov found: check the zip")
info = {}
for p in clips:
    cid = os.path.splitext(os.path.basename(p))[0]
    s = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                                   "stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames:format=duration",
                                   "-of", "json", p], capture_output=True, text=True).stdout)
    st, dur = s["streams"][0], float(s["format"]["duration"])
    info[cid] = dict(file=os.path.basename(p), width=st["width"], height=st["height"], r_fps=st["r_frame_rate"],
                     avg_fps=st["avg_frame_rate"], frames=int(st.get("nb_read_frames") or 0), seconds=round(dur, 2))
    cap = cv2.VideoCapture(p); tiles = []
    t = 0.0
    while t < dur - 0.05:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, fr = cap.read()
        if not ok: break
        th = cv2.resize(fr, (TW, int(TW * fr.shape[0] / fr.shape[1])))
        cv2.rectangle(th, (0, 0), (92, 26), (0, 0, 0), -1)
        cv2.putText(th, f"{t:4.1f} s", (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        tiles.append(th); t += STEP_S
    h = tiles[0].shape[0]
    while len(tiles) % COLS: tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
    head = np.zeros((40, rows[0].shape[1], 3), np.uint8)
    cv2.putText(head, f"{cid}: {st['width']}x{st['height']}, {dur:.1f} s, one frame every {STEP_S} s", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(f"{OUT}/{cid}.jpg", np.vstack([head] + rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"   {cid}: {st['width']}x{st['height']}, fps {st['r_frame_rate']} (avg {st['avg_frame_rate']}), "
          f"{info[cid]['frames']} frames, {dur:.1f} s -> {OUT}/{cid}.jpg")
json.dump(info, open(f"{OUT}/info.json", "w"), indent=1)
print(f"\nDone: send the 6 pictures in {OUT} to the chat.")
