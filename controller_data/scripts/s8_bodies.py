#!/usr/bin/env python3
"""STEP 8 add-on: does Apple Vision's BODY detector catch the entries and exits that the FACE detector misses?

usage: ~/Downloads/duplexnvc-baseline/.venv/bin/python s8_bodies.py

Uses the frames s8_prep.py already extracted (every 10th master frame, $S8/frames/<id>/), so the bodies are
found on exactly the frames the faces were found on.
  1. bodybox (VNDetectHumanRectanglesRequest, full body) on every clip  -> $S8/bodies/<id>.json  (resumable)
  2. body-count events with the same rule as the faces (a new count that holds for 3 labelled frames, 1 s)
  3. both detectors scored against the events marked by eye (raw_data events_truth.csv in $S8):
     a real event is caught when an event in the same direction (count up = enter, count down = leave)
     starts between 10 frames before it and 150 frames (5 s) after it; for leaving that lasts the whole
     clip (truth frame 0), anywhere in the clip. One automatic event catches at most one real event.
Outputs in $S8/results/: bodies_step8.csv (one row per box), body_events.csv,
  faces_vs_bodies.csv (one row per real event: caught by faces? by bodies? delay), detector_summary.csv
Detection time per frame is measured on the full-size frames of this Mac (an indication only; the
cost inside a call, on a thumbnail, is Step 7).
"""
import csv, json, os, subprocess, sys, statistics as st

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
RES = f"{S8}/results"
BODYBOX = f"{WORK}/tools/bodybox"
STEP, HOLD, BEFORE, AFTER, FPS = 10, 3, 10, 150, 30


def events(counts):
    """same rule as s8_table.py: a new count that holds for HOLD labelled frames"""
    out, cur = [], None
    n = [k for _, k in counts]
    for k in range(len(n) - HOLD + 1):
        if len(set(n[k:k + HOLD])) == 1:
            if cur is not None and n[k] != cur:
                out.append((counts[k][0], cur, n[k]))
            cur = n[k]
    return out


def score(truth, auto):
    """truth: [(frame, kind)], auto: [(frame, before, after)] -> {truth index: auto frame}, used auto set"""
    hit, used = {}, set()
    for ti, (tf, kind) in sorted(enumerate(truth), key=lambda x: x[1][0]):
        for ai, (af, b, a) in enumerate(auto):
            if ai in used or (a > b) != (kind == "enter"):
                continue
            if (kind == "leave" and tf == 0) or (tf - BEFORE <= af <= tf + AFTER):
                hit[ti] = af; used.add(ai); break
    return hit, used


def main():
    if not os.path.exists(BODYBOX):
        sys.exit(f"build the body detector first:\n  swiftc -O bodybox.swift -o {BODYBOX}")
    os.makedirs(f"{S8}/bodies", exist_ok=True)
    clips = [r["id"] for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["id"].strip()]
    truth = {}
    for r in csv.DictReader(open(f"{S8}/events_truth.csv")):
        truth.setdefault(r["clip"], []).append((int(r["frame"]), r["kind"], r["people"], r["note"]))
    face_ev = {}
    for r in csv.DictReader(open(f"{RES}/events.csv")):
        face_ev.setdefault(r["clip"], []).append((int(r["frame"]), int(r["faces_before"]), int(r["faces_after"])))

    box_rows, bev_rows, cmp_rows, people, times = [], [], [], [], []
    tot = dict(real=0, face_hit=0, body_hit=0, face_auto=0, body_auto=0, face_false=0, body_false=0)
    for k, cid in enumerate(clips, 1):
        bj = f"{S8}/bodies/{cid}.json"
        if not os.path.exists(bj):
            print(f"[{k}/{len(clips)}] {cid}: body detection", flush=True)
            r = subprocess.run([BODYBOX, f"{S8}/frames/{cid}", bj + ".part"], capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f"bodybox FAILED for {cid}: {(r.stdout + r.stderr)[-400:]}")
            os.replace(bj + ".part", bj)
        d = json.load(open(bj))
        counts = []
        for fr in d["frames"]:
            frame = fr["i"] * STEP
            counts.append((frame, len(fr["bodies"])))
            for (x, y, w, h, c) in fr["bodies"]:
                box_rows.append(dict(clip=cid, i=fr["i"], frame=frame, x=int(x), y=int(y), w=int(w), h=int(h),
                                     confidence=round(c, 3)))
            if fr["i"] > 0:                        # the first frame includes loading the model
                times.append(fr["ms"])
        n = [c for _, c in counts]
        bev = events(counts)
        bev_rows += [dict(clip=cid, frame=f, bodies_before=b, bodies_after=a, kind="enter" if a > b else "leave")
                     for f, b, a in bev]
        tr = truth.get(cid, [])
        tlist = [(f, kind) for f, kind, _, _ in tr]
        fe = face_ev.get(cid, [])
        fhit, fused = score(tlist, fe)
        bhit, bused = score(tlist, bev)
        for ti, (tf, kind, ppl, note) in enumerate(tr):
            cmp_rows.append(dict(clip=cid, frame=tf, kind=kind, people=ppl,
                                 face_event=fhit.get(ti, ""), face_delay_s=round((fhit[ti] - tf) / FPS, 1) if ti in fhit and tf else "",
                                 body_event=bhit.get(ti, ""), body_delay_s=round((bhit[ti] - tf) / FPS, 1) if ti in bhit and tf else "",
                                 note=note))
        people.append(dict(clip=cid, bodies_max=max(n) if n else 0, bodies_median=st.median(n) if n else 0,
                           body_events=len(bev), body_false=len(bev) - len(bused),
                           face_events=len(fe), face_false=len(fe) - len(fused)))
        tot["real"] += len(tr); tot["face_hit"] += len(fhit); tot["body_hit"] += len(bhit)
        tot["face_auto"] += len(fe); tot["body_auto"] += len(bev)
        tot["face_false"] += len(fe) - len(fused); tot["body_false"] += len(bev) - len(bused)

    def write(name, rows):
        if rows:
            with open(f"{RES}/{name}", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)

    write("bodies_step8.csv", box_rows)
    write("body_events.csv", bev_rows)
    write("faces_vs_bodies.csv", cmp_rows)
    write("detector_summary.csv", people)

    print(f"\n== {tot['real']} real events (events_truth.csv)")
    print(f"   faces : caught {tot['face_hit']:2d} of {tot['real']}, {tot['face_auto']:2d} automatic events, "
          f"{tot['face_false']:2d} not real")
    print(f"   bodies: caught {tot['body_hit']:2d} of {tot['real']}, {tot['body_auto']:2d} automatic events, "
          f"{tot['body_false']:2d} not real")
    if times:
        print(f"   body detection time on this Mac: median {st.median(times):.1f} ms per full-size frame "
              f"({len(times)} frames)")
    print("\n   real event                     faces          bodies")
    for r in cmp_rows:
        fs = f"{r['face_event']} ({r['face_delay_s']} s)" if r["face_event"] != "" else "missed"
        bs = f"{r['body_event']} ({r['body_delay_s']} s)" if r["body_event"] != "" else "missed"
        print(f"   {r['clip']:<7} {r['kind']:<5} at {r['frame']:>3}       {fs:<14} {bs}")
    print("\n   people per clip (max / median per labelled frame)")
    for p in people:
        print(f"   {p['clip']:<7} bodies {p['bodies_max']} / {p['bodies_median']}   "
              f"body events {p['body_events']} ({p['body_false']} not real)   "
              f"face events {p['face_events']} ({p['face_false']} not real)")
    print(f"\nresults in {RES}: faces_vs_bodies.csv, detector_summary.csv, body_events.csv, bodies_step8.csv")


if __name__ == "__main__":
    main()
