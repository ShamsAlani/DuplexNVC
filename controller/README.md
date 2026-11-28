# Participant rule and controller behaviour

This document fixes two things DuplexNVC needs before the controller is built:

1. **The participant rule:** which faces the detector reports as **regions of interest (ROI)**, the people in the call, and how far each is from the camera.
2. **The controller's behaviour:** how resolution, model, placement and schedule follow the content (the participants) and the energy state.

The rules come from Step 8 ([`controller_data/`](../controller_data/)), our recorded call clips, and the measurements of the baseline, the system measurements and the Algorithm Enhancements. Where a value was measured, the source is given; where it is a choice we made, it says so.

---

## 1. Participant rule (detection)

### Why a rule is needed

On our recorded call clips, face detection alone catches every join and leave (5 of 5). Its only false events come from **someone walking past behind** (`rcwalk`), who is counted as joining and then leaving. That person must not change the controller's settings.

The difference between a participant and a passer-by is **motion**. A person in a video call sits in front of the laptop and stays roughly where they are; a passer-by crosses the frame. Measured in face heights (so near and far faces are treated alike):

| | Largest movement from where the face first appeared |
|---|---|
| Seated participant (all call clips) | ≤ 0.51 face heights |
| Turning the head and talking in profile for 9 s (`rclook`) | 0.47 face heights |
| Shifting to make room for someone (`rcjoin`) | 0.51 face heights |
| Someone walking past behind (`rcwalk`) | 2–3 face heights **every 1/3 s** |

Size is not used. A size limit (the previous rule: at least 30 % of the largest face) would throw away a participant sitting further back. That is exactly the person who should set the resolution (section 2).

### The rule: seats

The detector does not follow people. It keeps a list of **seats**: places where a face has settled. A seat is a reference position plus the face height there. We only need to know whether each seat is still taken, not who is in it.

1. **Detect faces** with Apple Vision (`VNDetectFaceRectanglesRequest`) every 1/3 s (every 10th frame at 30 fps).
2. **A seat stays taken** while a face is within **1 face height** of its reference position. The face in it is a region of interest.
3. **Each face fills at most one seat** (its nearest). Two people sitting close together cannot keep each other's seat taken.
4. **A seat is emptied** when no face has been within 1 face height of it for **2 labelled frames (2/3 s)**. This allows for one missed detection (a hand over the face). Someone who walks away or stands up to leave is then **no longer a region of interest**.
5. **A new seat is created** when a face that is not near any seat **holds still for 1 s**: a face within 1 face height of the same spot in 3 labelled frames in a row. Its reference position and face height are set there. A new face does not count until then.

### What this does in each situation

| Situation | What happens |
|---|---|
| Someone sits down and stays | After 1 s still, a new seat: one more participant |
| Someone walks past behind | Never holds still, never gets a seat: not counted, no event |
| Someone stands up and leaves | Moves more than 1 face height from the seat, the seat is emptied: one participant fewer |
| Someone turns their head | The box shrinks but its centre stays within 1 face height: the seat stays taken and its face height (the distance) does not change |
| Someone changes seats | The old seat is emptied, a new seat is created 1 s after they settle: one short leave and one join |

A head turn and a change of seat both change the box, but only the change of seat moves the face centre more than 1 face height. The rule looks only at the centre, so it never mistakes one for the other.

### Distance from the camera

A seat's **face height** (set when the seat is created) is the distance of that participant from the camera: half the face height means about twice the distance. It is not updated from the current box, which shrinks when the head turns and is never constant. Distances are kept in face height at 360p, not centimetres; centimetres would only be an approximation.

The **furthest participant** is the taken seat with the smallest face height.

### Output, every labelled frame

| Output | Used by the controller for |
|---|---|
| Number of participants (taken seats) | Joins and leaves |
| Smallest face height of a taken seat, at 360p | The furthest participant |
| Its face-size group: < 32, 32–63, 64–127, ≥ 128 px at 360p | The minimum resolution |

A change in the number of participants, or in the furthest participant's size group, counts only when it **holds for 1 s** (3 labelled frames), the same rule as every Step 8 event.

### Parameters

| Parameter | Value | Where it comes from |
|---|---|---|
| Detection interval | every 10th frame (1/3 s) | Step 8 labels; Step 7: faces from 32 px at 360p are found |
| Seat radius | 1 face height | Choice. Between the largest movement of a seated participant (0.51) and a passer-by's step (2–3); every value from 0.5 to 2 gave the same result on the call clips with the previous, tracking version of this rule |
| Time still to create a seat | 1 s (3 labelled frames) | Choice, the same as the 1 s event rule |
| Missed detections before a seat is emptied | 2 labelled frames (2/3 s) | Choice |
| Events | a change must hold for 1 s | Step 8 |

---

## 2. Controller behaviour

### What the controller reads and decides

| Reads | Decides |
|---|---|
| **Content** (from the participant rule): the furthest participant's face-size group, and the number of participants, which changes through joins and leaves | **Resolution** |
| **Energy state:** AC or battery, Low Power Mode | **Model:** full MLVC, MLVC-S, or the Mac's hardware HEVC |
| **This chip:** its Neural Engine generation | **Placement:** Neural Engine, GPU or CPU, for the encoder and decoder separately |
| **The other laptop:** which processor decodes there | **Schedule** |

### Rules

1. **It acts only on regions of interest.** Faces that are not in a taken seat (passers-by, people leaving) never affect resolution, model or placement.
2. **The furthest participant sets the minimum resolution.** Its face-size group sets the lowest resolution that still codes that face well. The thresholds come from experiment 10 (face quality per setting) and Step 7 (faces from 32 px at 360p are detected). The other rules then choose the cheapest setting at or above that minimum.
3. **The number of participants changes through joins and leaves.** Every confirmed join or leave triggers a re-check of the setting:

   | Event | Effect |
   |---|---|
   | 0 → 1 (first person) | A face-based minimum resolution applies again, set by this person |
   | Someone joins **further** than the current furthest participant | They become the furthest participant: the minimum may go up |
   | Someone joins **closer** | The furthest participant is unchanged |
   | **The furthest participant** leaves | The next-furthest decides: the minimum may go down |
   | Someone **closer** leaves | The furthest participant is unchanged |
   | 1 → 0 (last person leaves) | **Drop to the cheapest setting right away** |

4. **Changes follow the detections, with no fixed timer.** The controller switches, up or down, as soon as the detector confirms the new state: the seat created or emptied, and the change held for 1 s.
5. **Start from the cheapest good setting.** MLVC-S 540p is the default: it beats B\* at every bitrate where both exist, with 32 % less energy (experiment 10).
6. **Keep both networks on the Neural Engine while they keep up.** It is 3–7× cheaper than any placement that uses the GPU (experiment 09). If a setting does not keep up, move only the **encoder** to the GPU; the **decoder** stays on the Neural Engine, because a decoder anywhere else drifts.
7. **Energy state limits the choice.**
   - **Low Power Mode:** no GPU encoder; 18–20 % of its frames are late (Step 6). Low Power Mode saves 6.6 % for B\* with no late frames.
   - **On battery:** Neural Engine settings first. A B\* call lasts about 10 h on battery; MLVC-S 720p with a GPU encoder about 1.7 h (Step 6).
8. **Hardware HEVC is the last resort.** It costs about 48× less energy than B\* but needs +69 % more bits (Step 9). It is used only when no MLVC setting fits the energy left.
9. **Agree on decoding with the other laptop.** If both decode on the Neural Engine, there is no drift, even between chip generations (cross-chip study). If the other laptop decodes on a different processor, use A2's bound: recovery from a long-term reference every 32 frames (about +9 % bits on MLVC-S 540p, E6).
10. **Adjust the schedule to the chip.** On the M1, B\* misses 30 fps (7.1 % late sends); letting the encoder and decoder take turns on the Neural Engine brings it to 0 % (cross-chip study). The controller keeps one table of Neural Engine times per chip generation.
11. **Scene events change the setting, never force a key frame.** A forced key frame when people join or leave costs 11–15 P-frames' worth of bits and the picture after the event is no better (A3).
12. **Always on, whatever the setting:** −8 QP on I-frames (A1), and a loss report answered with a frame predicted from a long-term reference (E3).

---

## 3. Known limitations

- **Moving straight back.** Someone who moves back without moving sideways keeps their seat and its old face height, so they can be under-resolved. We decided not to handle this: it is uncommon in calls, and handling it would make the rule much more complex.
- **Joins count 1 s later** than with face detection alone, because a new face must hold still for 1 s to get a seat.
- **Two switches for a short absence.** Someone who steps away briefly or changes seats causes a step down and then a step up again. If a switch costs a key frame, each one costs some bits.
- **Printed faces.** A poster or photo of a face does not move, so it would get a seat and could become the furthest participant. That costs energy (a higher resolution than needed), never quality. It is rare, so the rule does not handle it.
- **Thresholds chosen on few clips.** The seat radius and times were chosen on clips with one passer-by. They have to be confirmed on new recordings, for example someone walking past slowly or close to the camera.

## 4. Still to do

1. ~~Implement the seat rule and run it on the call clips.~~ Done (28 Nov): `controller_data/scripts/participant_rule.py`; on our call clips it catches 5 of 5 joins and leaves with no false event, median delay 1.2 s ([results](../controller_data/README.md#the-seat-rule-replaces-it)).
2. Record new call clips to check the thresholds: someone walking past slowly, and someone walking past close to the camera.
3. Build the controller with these rules and measure it against B\* with the baseline's protocol.
