#!/usr/bin/env python3
"""STEP 8 add-on: our recorded call clips vs the stock clips, and the participant rule.

usage: python3 s8_calls.py [controller_data folder]      (default: the folder this script is in, one level up)

Reads only what is in the repo (raw_data/ and results/bodies_step8.csv); runs on any machine, no detection.
1. Every method of s8_fusion.py (faces, bodies, or, and, max), scored separately on the stock clips
   (HEVC Class E, Pexels) and on our recorded call clips (source "recorded").
2. The participant rule for calls: a face counts as a participant when it is at least SIZE (30 %) of the largest
   face in the frame, OR when it has stayed in view for STAY labelled frames (2 s). A person walking past behind
   is small and brief, so they are not counted; someone who sits down further back still is, after 2 s.
   Events then use the same 1 s rule as everything else. Scored the same way, on both sets.
   The 30 % and 2 s were chosen by looking at these clips (one passer-by clip): to be checked on new recordings.
Outputs in results/: calls_vs_stock.csv (method x set), participant_rule.csv (rule x set),
participant_rule_events.csv (every automatic event of the faces method with and without the rule).
"""
import csv, importlib.util, json, os, sys
from collections import defaultdict

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("fu", f"{D}/scripts/s8_fusion.py")
fu = importlib.util.module_from_spec(spec); spec.loader.exec_module(fu)
STEP, FPS, SIZE, STAY = 10, 30, 0.30, 6

meta = json.load(open(f"{D}/raw_data/meta.json"))
excl = {r["clip"]: float(r["min_face_360"]) for r in csv.DictReader(open(f"{D}/raw_data/exclude.csv"))}
truth = defaultdict(list)
for r in csv.DictReader(open(f"{D}/raw_data/events_truth.csv")):
    truth[r["clip"]].append((int(r["frame"]), r["kind"]))
clips = list(csv.DictReader(open(f"{D}/raw_data/clips.csv")))
group = {c["id"]: ("recorded call clips" if c["source"] == "recorded" else "stock clips") for c in clips}
bodies = defaultdict(int)
for r in csv.DictReader(open(f"{D}/results/bodies_step8.csv")):
    bodies[(r["clip"], int(r["i"]))] += 1


def counts(cid):
    H = meta[cid]["master_h"]; lim = excl.get(cid, 0)
    rows = []
    for fr in json.load(open(f"{D}/raw_data/faces/{cid}.json"))["frames"]:
        hs = [b[3] for b in fr["faces"] if b[3] * 360 / H >= lim]          # participants (posters removed)
        big = sum(1 for h in hs if h >= SIZE * max(hs)) if hs else 0
        rows.append((fr["i"] * STEP, len(hs), big, bodies[(cid, fr["i"])]))
    rule = []
    for k, (f, n, big, _) in enumerate(rows):
        stayed = min(r[1] for r in rows[k - STAY + 1:k + 1]) if k >= STAY - 1 else big
        rule.append((f, max(big, stayed)))
    return rows, rule


def score(auto_by_clip, ids):
    t = dict(caught=0, real=0, automatic=0, not_real=0, d=[])
    for cid in ids:
        tr = truth.get(cid, []); au = auto_by_clip[cid]
        hit, used = fu.score(tr, au)
        t["real"] += len(tr); t["caught"] += len(hit); t["automatic"] += len(au); t["not_real"] += len(au) - len(used)
        t["d"] += [(hit[i] - tf) / FPS for i, (tf, k) in enumerate(tr) if i in hit and tf]
    d = sorted(t.pop("d"))
    t["median_delay_s"] = round(d[len(d) // 2], 1) if d else ""
    return t


auto = defaultdict(dict); rule_auto = {}
for c in clips:
    cid = c["id"]
    rows, rule = counts(cid)
    fe = fu.events([(f, n) for f, n, _, _ in rows]); be = fu.events([(f, b) for f, _, _, b in rows])
    auto["faces"][cid] = fe; auto["bodies"][cid] = be
    auto["or"][cid] = fu.union(fe, be); auto["and"][cid] = fu.both(fe, be)
    auto["max"][cid] = fu.events([(f, max(n, b)) for f, n, _, b in rows])
    rule_auto[cid] = fu.events(rule)

sets = ["stock clips", "recorded call clips"]
out = []
for m in fu.METHODS:
    for s in sets:
        out.append(dict(method=m, set=s, clips=sum(group[c["id"]] == s for c in clips),
                        **score(auto[m], [c["id"] for c in clips if group[c["id"]] == s])))
rule_rows = []
for name, au in (("faces, 1 s rule (as before)", auto["faces"]),
                 ("faces + participant rule (>= 30 % of the largest face, or in view >= 2 s)", rule_auto)):
    for s in sets:
        rule_rows.append(dict(method=name, set=s, **score(au, [c["id"] for c in clips if group[c["id"]] == s])))
ev_rows = []
for c in clips:
    cid = c["id"]
    for name, au in (("faces", auto["faces"][cid]), ("faces + participant rule", rule_auto[cid])):
        hit, used = fu.score(truth.get(cid, []), au)
        for j, (f, b, a) in enumerate(au):
            ev_rows.append(dict(clip=cid, set=group[cid], method=name, frame=f, seconds=round(f / FPS, 1),
                                faces_before=b, faces_after=a, real="yes" if j in used else "no"))

for name, rows in (("calls_vs_stock.csv", out), ("participant_rule.csv", rule_rows), ("participant_rule_events.csv", ev_rows)):
    with open(f"{D}/results/{name}", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print("method  set                    caught   automatic  not real  median delay")
for r in out + rule_rows:
    print(f"{r['method'][:40]:40s} {r['set']:20s} {r['caught']:>2} of {r['real']:<3} {r['automatic']:>5} {r['not_real']:>8}    {r['median_delay_s']} s")
print(f"results in {D}/results: calls_vs_stock.csv, participant_rule.csv, participant_rule_events.csv")
