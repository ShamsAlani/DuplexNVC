#!/usr/bin/env python3
"""STEP 8 add-on: combine the face and body detectors. Which combination catches the real events best?

usage: ~/Downloads/duplexnvc-baseline/.venv/bin/python s8_fusion.py

Reads what s8_prep.py, s8_table.py and s8_bodies.py already wrote (no new detection):
  $S8/faces/<id>.json, $S8/bodies/<id>.json, $S8/master/meta.json, $S8/exclude.csv, $S8/events_truth.csv
Five ways to decide that people entered or left, on the same labelled frames (every 10th master frame):
  faces   participant faces (poster faces removed with exclude.csv), events with the 1 s rule
  bodies  bodies, events with the 1 s rule
  or      an event from faces OR bodies (two events in the same direction within 1 s count once)
  and     an event only when faces AND bodies both have one in the same direction within 1 s
          (it fires at the later of the two: the moment both agree)
  max     per frame, people = max(participant faces, bodies); events with the 1 s rule on that count
Each is scored like s8_bodies.py: a real event is caught when an event in the same direction starts between
10 frames before it and 150 frames (5 s) after it (walking-away clips: anywhere in the clip); one automatic
event catches at most one real event.
Outputs in $S8/results/: fusion_summary.csv (one row per method), fusion_events.csv (one row per real event:
caught by which method, and when)
"""
import csv, json, os

WORK = os.path.expanduser("~/Downloads/duplexnvc-baseline")
S8 = f"{WORK}/phase2/step8"
RES = f"{S8}/results"
STEP, HOLD, BEFORE, AFTER, FPS, AGREE = 10, 3, 10, 150, 30, 30
METHODS = ["faces", "bodies", "or", "and", "max"]


def events(counts):
    """a new count that holds for HOLD labelled frames (same rule as s8_table.py / s8_bodies.py)"""
    out, cur = [], None
    n = [k for _, k in counts]
    for k in range(len(n) - HOLD + 1):
        if len(set(n[k:k + HOLD])) == 1:
            if cur is not None and n[k] != cur:
                out.append((counts[k][0], cur, n[k]))
            cur = n[k]
    return out


def up(e):
    return e[2] > e[1]


def union(a, b):
    """events of a and b; one in b within AGREE frames of a same-direction one in a counts once"""
    out = list(a)
    for e in b:
        if not any(up(x) == up(e) and abs(x[0] - e[0]) <= AGREE for x in a):
            out.append(e)
    return sorted(out)


def both(a, b):
    """events confirmed by both: same direction within AGREE frames, at the later of the two"""
    out, used = [], set()
    for e in a:
        for j, x in enumerate(b):
            if j not in used and up(x) == up(e) and abs(x[0] - e[0]) <= AGREE:
                out.append((max(e[0], x[0]), e[1], e[2])); used.add(j); break
    return sorted(out)


def score(truth, auto):
    hit, used = {}, set()
    for ti, (tf, kind) in sorted(enumerate(truth), key=lambda x: x[1][0]):
        for ai, (af, b, a) in enumerate(auto):
            if ai in used or (a > b) != (kind == "enter"):
                continue
            if (kind == "leave" and tf == 0) or (tf - BEFORE <= af <= tf + AFTER):
                hit[ti] = af; used.add(ai); break
    return hit, used


def main():
    clips = [r["id"] for r in csv.DictReader(open(f"{S8}/clips.csv")) if r["id"].strip()]
    meta = json.load(open(f"{S8}/master/meta.json"))
    excl = {}
    if os.path.exists(f"{S8}/exclude.csv"):
        excl = {r["clip"]: float(r["min_face_360"]) for r in csv.DictReader(open(f"{S8}/exclude.csv"))}
    truth = {}
    for r in csv.DictReader(open(f"{S8}/events_truth.csv")):
        truth.setdefault(r["clip"], []).append((int(r["frame"]), r["kind"]))

    tot = {m: dict(method=m, caught=0, real=0, automatic=0, not_real=0, delays=[]) for m in METHODS}
    ev_rows = []
    for cid in clips:
        H = meta[cid]["master_h"]
        lim = excl.get(cid, 0)
        fd = json.load(open(f"{S8}/faces/{cid}.json"))["frames"]
        bd = {f["i"]: f for f in json.load(open(f"{S8}/bodies/{cid}.json"))["frames"]}
        fc, bc, mc = [], [], []
        for fr in fd:
            frame = fr["i"] * STEP
            nf = sum(1 for (_, _, _, h) in fr["faces"] if h * 360 / H >= lim)
            nb = len(bd.get(fr["i"], {}).get("bodies", []))
            fc.append((frame, nf)); bc.append((frame, nb)); mc.append((frame, max(nf, nb)))
        fe, be = events(fc), events(bc)
        auto = {"faces": fe, "bodies": be, "or": union(fe, be), "and": both(fe, be), "max": events(mc)}
        tr = truth.get(cid, [])
        row_by_t = [dict(clip=cid, frame=tf, kind=kind) for tf, kind in tr]
        for m in METHODS:
            hit, used = score(tr, auto[m])
            t = tot[m]
            t["real"] += len(tr); t["caught"] += len(hit)
            t["automatic"] += len(auto[m]); t["not_real"] += len(auto[m]) - len(used)
            for ti, (tf, kind) in enumerate(tr):
                if ti in hit:
                    row_by_t[ti][m] = hit[ti]
                    if tf:
                        t["delays"].append((hit[ti] - tf) / FPS)
                else:
                    row_by_t[ti][m] = ""
        ev_rows += row_by_t

    summary = []
    for m in METHODS:
        t = tot[m]
        d = sorted(t["delays"])
        summary.append(dict(method=m, caught=t["caught"], real=t["real"], automatic=t["automatic"],
                            not_real=t["not_real"],
                            median_delay_s=round(d[len(d) // 2], 1) if d else ""))
    os.makedirs(RES, exist_ok=True)
    for name, rows in (("fusion_summary.csv", summary), ("fusion_events.csv", ev_rows)):
        with open(f"{RES}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)

    print(f"\n   method   caught   automatic   not real   median delay")
    for s in summary:
        print(f"   {s['method']:<7}  {s['caught']:>2} of {s['real']:<3} {s['automatic']:>6}     {s['not_real']:>6}"
              f"      {s['median_delay_s']} s")
    print("\n   real event            " + "  ".join(f"{m:>6}" for m in METHODS))
    for r in ev_rows:
        cells = "  ".join(f"{str(r[m]) if r[m] != '' else '-':>6}" for m in METHODS)
        print(f"   {r['clip']:<7} {r['kind']:<5} {r['frame']:>4}  {cells}")
    print(f"\n   (numbers = master frame where the method caught the event, - = missed)")
    print(f"results in {RES}: fusion_summary.csv, fusion_events.csv")


if __name__ == "__main__":
    main()
