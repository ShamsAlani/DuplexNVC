"""Step 8: a video wall of our recorded call clips, all playing at once with the face detector's boxes.

    ~/Downloads/duplexnvc-baseline/.venv/bin/python s8_wall.py [repo]

Uses the masters and face labels Step 8 already made (no new detection). Writes into <repo>/controller_data/showcase:
  call_clips_wall.gif   4 x 2 grid, 480 px tiles... small enough for the README (10 fps)
  call_clips_wall.mp4   the same at 640 px tiles, 30 fps (for slides)
Each tile: the clip, a green box on every face counted as a participant, a grey box on a face the participant
rule leaves out (smaller than 30 % of the largest face and in view for less than 2 s: someone walking past),
the number of people in the call, and a white note while a real event is happening.
"""
import csv, json, os, subprocess, sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
    from PIL import Image, ImageDraw, ImageFont
import cv2

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
REPO = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/DuplexNVC")
OUT = f"{REPO}/controller_data/showcase"
STEP, FPS, N = 10, 30, 300
GREEN, INK, PAPER, MUTED, GREY = (27, 175, 122), (11, 11, 11), (252, 252, 251), (82, 81, 78), (150, 150, 146)
SIZE, STAY = 0.30, 6   # the participant rule (s8_calls.py)
NAMES = {"rcleav": "leaves the call", "rc2to1": "two people, one leaves", "rcbck1": "steps away",
         "rcbck2": "comes back", "rcjoin": "someone joins", "rclook": "looks away (stays)",
         "rcwalk": "someone walks past"}


def font(size, bold=False):
    for p in (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + \
             ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def pill(d, x, y, text, bg, f, fg=(255, 255, 255), right=False):
    b = d.textbbox((0, 0), text, font=f); w, h = b[2] - b[0], b[3] - b[1]
    if right: x -= w + 12
    d.rounded_rectangle([x, y, x + w + 12, y + h + 8], radius=(h + 8) // 2, fill=bg)
    d.text((x + 6, y + 4 - b[1]), text, font=f, fill=fg)


def tiles(TW):
    TH = TW * 9 // 16
    s = TW / 1280
    f = font(max(11, TW // 26)); fb = font(max(11, TW // 26), True)
    clips = [r for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["source"] == "recorded"]
    meta = json.load(open(f"{S8}/master/meta.json"))
    truth = {}
    for r in csv.DictReader(open(f"{S8}/events_truth.csv")):
        truth.setdefault(r["clip"], []).append((int(r["frame"]), r["kind"]))
    out = []
    for c in clips:
        cid = c["id"]; m = meta[cid]; W, H = m["master_w"], m["master_h"]
        faces = {fr["i"]: fr["faces"] for fr in json.load(open(f"{S8}/faces/{cid}.json"))["frames"]}
        idx = sorted(faces)
        # participant rule: big enough (>= 30 % of the largest face) or in view for 2 s
        n_all = [len(faces[i]) for i in idx]
        part = {}
        for k, i in enumerate(idx):
            hs = [b[3] for b in faces[i]]
            big = sum(1 for h in hs if h >= SIZE * max(hs)) if hs else 0
            stayed = min(n_all[k - STAY + 1:k + 1]) if k >= STAY - 1 else big
            part[i] = max(big, stayed)
        cap = cv2.VideoCapture(f"{S8}/master/{cid}_{W}x{H}_30.mp4"); frames = []
        while True:
            ok, fr = cap.read()
            if not ok: break
            frames.append(cv2.resize(fr, (TW, TH), interpolation=cv2.INTER_AREA))
        seq = []
        for n in range(N):
            k = min(n, len(frames) - 1)
            im = Image.fromarray(cv2.cvtColor(frames[k], cv2.COLOR_BGR2RGB))
            d = ImageDraw.Draw(im)
            i = max([j for j in idx if j * STEP <= k] or [idx[0]])
            ranked = sorted(faces[i], key=lambda b: -b[3])          # the largest faces are the participants
            for k2, (x, y, w, h) in enumerate(ranked):
                ok = k2 < part[i]
                d.rectangle([x * s, y * s, (x + w) * s, (y + h) * s], outline=GREEN if ok else GREY, width=max(2, TW // 160))
                if not ok:
                    b = d.textbbox((0, 0), "passing by", font=f)
                    pill(d, min(max(0, x * s), TW - (b[2] - b[0]) - 16), max(0, y * s - f.size - 12), "passing by", GREY, f)
            pill(d, 6, 6, f"{cid} · {NAMES.get(cid, '')}", INK, fb)
            pill(d, TW - 6, TH - 6 - fb.size - 10, f"in the call: {part[i]}", GREEN, fb, right=True)
            for tf, kind in truth.get(cid, []):
                if 0 <= k - tf < 60:
                    pill(d, 6, TH - 6 - f.size - 10, "real: someone " + ("joins" if kind == "enter" else "leaves"), (255, 255, 255), f, fg=INK)
            seq.append(im)
        out.append(seq)
    return out, TW, TH


def wall(TW, every, path_fmt):
    seqs, TW, TH = tiles(TW)
    cols, rows, g = 4, 2, max(4, TW // 80)
    WW, HH = cols * TW + (cols + 1) * g, rows * TH + (rows + 1) * g
    frames = []
    for n in range(0, N, every):
        page = Image.new("RGB", (WW, HH), PAPER)
        for k, seq in enumerate(seqs[:cols * rows]):
            r = k // cols; in_row = min(cols, len(seqs) - r * cols)        # centre a shorter last row
            x0 = g + (cols - in_row) * (TW + g) // 2
            page.paste(seq[n], (x0 + (k % cols) * (TW + g), g + r * (TH + g)))
        frames.append(page)
    return frames, WW, HH


def main():
    os.makedirs(OUT, exist_ok=True)
    frames, WW, HH = wall(640, 1, None)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WW}x{HH}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                          "-movflags", "+faststart", f"{OUT}/call_clips_wall.mp4"], stdin=subprocess.PIPE)
    for im in frames: p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    print(f"   call_clips_wall.mp4 ({WW}x{HH}, {os.path.getsize(f'{OUT}/call_clips_wall.mp4') // 1024} KB)", flush=True)
    frames, WW, HH = wall(300, 3, None)
    pal = frames[len(frames) // 2].quantize(colors=160, method=Image.MEDIANCUT)
    small = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in frames]
    small[0].save(f"{OUT}/call_clips_wall.gif", save_all=True, append_images=small[1:], duration=100, loop=0, optimize=True)
    print(f"   call_clips_wall.gif ({WW}x{HH}, {os.path.getsize(f'{OUT}/call_clips_wall.gif') // 1024} KB)")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
