#!/usr/bin/env python3
"""The seat rule (participant rule, controller README section 1), tested on our recorded call clips.

usage: python3 participant_rule.py [controller_data folder]      (default: one level up from this script)

Reads only raw_data/ (face boxes every 10th frame) and needs no detection. Implements the rule as written:
  - a seat = reference centre + face height; a seat stays taken while a face is within 1 face height
    (the seat's face height) of its reference centre;
  - each face fills at most one seat (its nearest), each seat holds at most one face (closest pairs first);
  - a seat is emptied when no face has been near it for 2 labelled frames (2/3 s);
  - a face not near any seat that stays within 1 face height of the same spot for 3 labelled frames in a row
    (1 s) creates a new seat there (reference = where it is on the third frame);
  - the participant count = taken seats; events: a change that holds 1 s (3 labelled frames), as in Step 8;
  - the furthest participant = the taken seat with the smallest face height, in face-size groups at 360p.
Only our recorded call clips (source "recorded" in raw_data/clips.csv) are used; the stock clips are not calls.
Scored like Step 8 (s8_fusion.score): same direction, 10 frames before to 150 frames after a real event.
Outputs in results/: seat_rule.csv (summary, with faces only for comparison), seat_rule_events.csv (every event),
seat_rule_seats.csv (participants and the furthest participant's face per labelled frame).
"""
import csv, importlib.util, json, math, os, sys
from collections import defaultdict

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("fu", f"{D}/scripts/s8_fusion.py")
fu = importlib.util.module_from_spec(spec); spec.loader.exec_module(fu)
STEP, FPS = 10, 30
RADIUS, STILL, MISS = 1.0, 3, 2          # face heights; labelled frames to create; labelled frames missed to empty

meta = json.load(open(f"{D}/raw_data/meta.json"))
truth = defaultdict(list)
for r in csv.DictReader(open(f"{D}/raw_data/events_truth.csv")):
    truth[r["clip"]].append((int(r["frame"]), r["kind"]))
clips = [c for c in csv.DictReader(open(f"{D}/raw_data/clips.csv")) if c["source"] == "recorded"]


def size_group(h360):
    return "<32" if h360 < 32 else "32-63" if h360 < 64 else "64-127" if h360 < 128 else ">=128"


def seat_rule(cid):
    H = meta[cid]["master_h"]
    seats, cands, out = [], [], []          # seat: [cx, cy, h, missed]; cand: [cx, cy, h, n]
    for fr in json.load(open(f"{D}/raw_data/faces/{cid}.json"))["frames"]:
        faces = [(x + w / 2, y + h / 2, h) for x, y, w, h in fr["faces"]]
        # match faces to seats one-to-one, closest pairs first, within RADIUS seat face heights
        pairs = sorted((math.dist(f[:2], s[:2]) / s[2], i, j) for i, f in enumerate(faces) for j, s in enumerate(seats))
        used_f, used_s = set(), set()
        for d, i, j in pairs:
            if d <= RADIUS and i not in used_f and j not in used_s:
                used_f.add(i); used_s.add(j)
        for j, s in enumerate(seats):
            s[3] = 0 if j in used_s else s[3] + 1
        seats = [s for s in seats if s[3] < MISS]
        # faces near no seat: candidates that must hold still for STILL labelled frames in a row
        free = [f for i, f in enumerate(faces) if i not in used_f
                and not any(math.dist(f[:2], s[:2]) <= RADIUS * s[2] for s in seats)]
        new_c = []
        for f in free:
            near = [c for c in cands if math.dist(f[:2], c[:2]) <= RADIUS * c[2]]
            if near:
                c = min(near, key=lambda c: math.dist(f[:2], c[:2])); cands.remove(c)
                n = c[3] + 1
                if n >= STILL: seats.append([f[0], f[1], f[2], 0])
                else: new_c.append([c[0], c[1], c[2], n])
            else:
                new_c.append([f[0], f[1], f[2], 1])
        cands = new_c                                   # a candidate not seen this frame starts again
        hs = [s[2] * 360 / H for s in seats]
        out.append((fr["i"] * STEP, len(seats), round(min(hs), 1) if hs else "", size_group(min(hs)) if hs else ""))
    return out


def faces_only(cid):
    return [(fr["i"] * STEP, len(fr["faces"]))
            for fr in json.load(open(f"{D}/raw_data/faces/{cid}.json"))["frames"]]


def score(auto_by_clip, ids):
    t = dict(caught=0, real=0, automatic=0, not_real=0, d=[])
    for cid in ids:
        tr = truth.get(cid, []); au = auto_by_clip[cid]
        hit, used = fu.score(tr, au)
        t["real"] += len(tr); t["caught"] += len(hit); t["automatic"] += len(au); t["not_real"] += len(au) - len(used)
        t["d"] += [(hit[i] - tf) / FPS for i, (tf, k) in enumerate(tr) if i in hit and tf]
    d = sorted(t.pop("d"))
    t["median_delay_s"] = round(d[len(d) // 2], 1) if d else ""
    t["delays_s"] = " ".join(f"{x:.1f}" for x in d)
    return t


methods = {"faces only, 1 s rule (Step 8)": {c["id"]: fu.events(faces_only(c["id"])) for c in clips},
           "seat rule": {c["id"]: fu.events([(f, n) for f, n, _, _ in seat_rule(c["id"])]) for c in clips}}
seats_rows, ev_rows = [], []
for c in clips:
    cid = c["id"]
    for f, n, h, g in seat_rule(cid):
        seats_rows.append(dict(clip=cid, frame=f, seconds=round(f / FPS, 2), participants=n,
                               furthest_face_h_360=h, furthest_group=g))
    for name, by_clip in methods.items():
        au = by_clip[cid]
        hit, used = fu.score(truth.get(cid, []), au)
        for j, (f, b, a) in enumerate(au):
            ev_rows.append(dict(clip=cid, method=name, frame=f, seconds=round(f / FPS, 1),
                                participants_before=b, participants_after=a, real="yes" if j in used else "no"))

ids = [c["id"] for c in clips]
summary = [dict(method=m, clips=len(ids), **score(au, ids)) for m, au in methods.items()]
for name, rows in (("seat_rule.csv", summary), ("seat_rule_events.csv", ev_rows), ("seat_rule_seats.csv", seats_rows)):
    with open(f"{D}/results/{name}", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print(f"Our recorded call clips ({len(ids)}): {' '.join(ids)}")
print(f"{'method':32s} caught  events  not real  median delay  (delays)")
for r in summary:
    print(f"{r['method']:32s} {r['caught']:>2} of {r['real']:<3} {r['automatic']:>5} {r['not_real']:>8}   {str(r['median_delay_s']):>5} s   ({r['delays_s']})")
print("\nEvents of the seat rule:")
for r in ev_rows:
    if r["method"] == "seat rule":
        print(f"  {r['clip']:7s} {r['seconds']:>5} s  participants {r['participants_before']} -> {r['participants_after']}  real: {r['real']}")
print("\nParticipants and furthest participant over time (seat rule):")
prev = None
for r in seats_rows:
    k = (r["clip"], r["participants"], r["furthest_group"])
    if k != prev:
        print(f"  {r['clip']:7s} from {r['seconds']:>5} s: {r['participants']} participant(s), furthest face {r['furthest_face_h_360'] or '-'} px at 360p ({r['furthest_group'] or '-'})")
        prev = k
print(f"\nresults in {D}/results: seat_rule.csv, seat_rule_events.csv, seat_rule_seats.csv")
