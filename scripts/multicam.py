#!/usr/bin/env python3
"""The director: turn a resolved long edit into a shot list across cameras and angles.

  multicam.py DIR/edit.json [--seed 7]

Angles (16:9 output):
  close.wide    the whole picture-camera frame (speaker, screen, room)
  close.medium  a 16:9 crop around the speaker from the 4K original (waist up)
  close.punch   the same crop 1.12x tighter (hides jump cuts inside a shot)
  close.tight   head and shoulders, for lines that matter (rarely)
  close.widepunch  the whole frame 1.15x tighter (hides a jump cut inside a wide shot)
  close.stage   speaker and projection together (a 1080p camera's everyday shot; zoom set by
                plan "framing"), with close.stagepunch hiding its jump cuts
  wide          the second camera: the room and the audience
  screen        the screen recording, full frame (slides as shown)

Rules, in order: the audience speaks -> wide; a title behind the speaker -> close.medium
(never the screen; a slide that appears under it follows it); a slide appears -> screen for
one or two sentences; the speaker walks out of the picture camera's frame (the tracker
loses the face) -> wide; a chapter starts -> close.wide; otherwise cycle speaker angles with shots
of 6 to 14 s (holds up to 20 s on a long thought), cutting on sentence ends only.
Every internal cut (a removed filler or pause) inside a speaker shot alternates
close.medium and close.punch so it reads as a camera change. `angles` in the plan
overrides any range: [{"from": "#idx", "to": "#idx", "angle": "screen"}].
Writes edit.shots.json: [{e0, e1, angle, cam, t (camera time at e0), crop [x, y, w, h]}].
"""
import argparse, json, random, re, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

W_OUT, H_OUT = 1920, 1080


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    plan_path = Path(args.plan)
    d = plan_path.parent
    plan = json.loads(plan_path.read_text())
    W = json.loads(Path(plan["source"]["words"]).read_text())["words"]
    sig = json.loads((d / "signals.json").read_text())
    cams = {c["id"]: c for c in plan["source"]["cameras"]}
    close = cams["close"]
    track = json.loads(Path(close["track"]).read_text())
    tt = np.array(track["times"])
    fx = np.array([p["cx"] if p else np.nan for p in track["subject"]])
    fy = np.array([(p["eyes"][1] + p["eyes"][3]) / 2 if p and p.get("eyes") else np.nan for p in track["subject"]])
    fw = np.array([p["w"] if p else np.nan for p in track["subject"]])
    ok = ~np.isnan(fx)
    SW, SH = track["width"], track["height"]
    face_w = float(np.nanmedian(fw))

    segs = plan["segments"]
    off = np.concatenate([[0], np.cumsum([s["b"] - s["a"] for s in segs])])

    def to_edit(k, t):
        return float(off[k] + (t - segs[k]["a"]))

    # Units: sentences inside segments, in edit time, with their source span.
    units = []
    for k, s in enumerate(segs):
        i0, i1 = s["w"]
        start = i0
        for i in range(i0, i1 + 1):
            if W[i].get("eos") or i == i1:
                a = s["a"] if start == i0 else W[start]["s"]
                b = s["b"] if i == i1 else W[i]["e"]
                units.append({"k": k, "i0": start, "i1": i, "a": a, "b": b, "e0": to_edit(k, a), "e1": to_edit(k, b),
                              "segStart": start == i0})
                start = i + 1
    # Close the gaps between units inside a segment (the pauses belong to the sentence before).
    for u, v in zip(units, units[1:]):
        if u["k"] == v["k"]:
            u["e1"] = v["e0"]
            u["b"] = v["a"]

    # Title windows (a word behind the speaker) in edit time: they need the speaker, never a slide.
    from render import Timeline
    tl = Timeline(segs, W)
    tl_e = tl
    titles = [(tl.ref(ins["from"]), tl.ref(ins["to"])) for ins in plan.get("inserts", [])
              if any(o.get("type") == "TextBehind" for o in ins.get("overlays", []))]
    # A long sentence under a title splits where the title ends, so a slide can follow it.
    split = []
    for u in units:
        end = next((y for x, y in titles if u["e0"] <= x < u["e1"] and u["e1"] - y > 2.0), None)
        i = next((i for i in range(u["i0"] + 1, u["i1"] + 1) if end is not None and to_edit(u["k"], W[i]["s"]) >= end), None)
        if i is None:
            split.append(u)
            continue
        t = W[i]["s"]
        split.append({**u, "i1": i - 1, "b": t, "e1": to_edit(u["k"], t)})
        split.append({**u, "i0": i, "a": t, "e0": to_edit(u["k"], t), "segStart": False})
    units = split

    def present(a, b):
        """Share of tracked frames in which the picture camera sees the speaker's face."""
        m = (tt >= a) & (tt <= b)
        return float(ok[m].mean()) if m.sum() >= 2 else 1.0

    def in_title(u):
        return any(min(u["e1"], y) - max(u["e0"], x) > 0.3 for x, y in titles)

    audience = [(t["a"], t["b"]) for t in sig.get("audience", [])]
    slides = sig.get("screen", {}).get("slides", [])
    busy = sig.get("screen", {}).get("busy", [])
    idx = lambda r: int(str(r).lstrip("#").split("@")[0].split(".")[0].split("+")[0])  # noqa: E731
    chapters = {idx(c["at"]) for c in plan.get("chapters", [])}
    overrides = []        # (source from, source to, angle): every copy of those words in the edit
    overrides_e = []      # (edit from, edit to, angle): one copy, when the reference names it (#i@2, #i@last)
    for o in plan.get("angles", []):
        if "@" in str(o["from"]) or "@" in str(o["to"]):
            fr, to = str(o["from"]), str(o["to"])
            to = to if ".e" in to else to.replace("@", ".e@", 1) if "@" in to else to + ".e"
            overrides_e.append((tl_e.ref(fr), tl_e.ref(to), o["angle"]))
        else:
            overrides.append((W[idx(o["from"])]["s"], W[idx(o["to"])]["e"], o["angle"]))

    def overlaps(a, b, ranges, frac=0.5):
        return any(min(b, y) - max(a, x) > frac * (b - a) for x, y in ranges)

    # One camera only: the room view is the picture camera's whole frame.
    ROOM = "wide" if "wide" in cams else "close.wide"

    # 1. Assign a wanted angle per unit.
    want = []
    screen_hold = 0.0
    slide_owed = False  # a slide that appeared under a title shows right after it
    for u in units:
        a, b = u["a"], u["b"]
        away = present(a, b) < 0.5  # the speaker has walked out of the picture camera's frame
        forced = next((ang for x, y, ang in overrides_e if min(u["e1"], y) - max(u["e0"], x) > 0.5 * (u["e1"] - u["e0"])), None) \
            or next((ang for x, y, ang in overrides if min(b, y) - max(a, x) > 0.5 * (b - a)), None)
        if forced:
            want.append(ROOM if away and forced.startswith("close.") else forced)
            continue
        if overlaps(a, b, audience, 0.4):
            want.append(ROOM)
            continue
        slide_here = any(a - 0.5 <= t <= b for t in slides)
        if in_title(u):
            want.append(ROOM if away else "close.medium")
            slide_owed = slide_owed or slide_here
            continue
        if slide_here or slide_owed or overlaps(a, b, [tuple(x) for x in busy], 0.5):
            want.append("screen")
            screen_hold = plan.get("screenHold", 6.0)
            slide_owed = False
            continue
        if screen_hold > 0 and u["e1"] - u["e0"] < 8:
            want.append("screen")
            screen_hold -= u["e1"] - u["e0"]
            continue
        screen_hold = 0.0
        if away:
            want.append(ROOM)
            continue
        if u["i0"] in chapters:
            want.append("close.wide")
            continue
        want.append(None)  # a speaker shot, decided by cadence below

    # 2. Group into shots: forced angles as runs; speaker runs cut into 6-14 s shots.
    shots = []
    # Mostly wide (the room reads the talk best), medium for explaining, tight rarely.
    cycle = plan.get("angleCycle") or ["close.wide", "close.medium", "wide", "close.wide", "close.medium", "wide", "close.tight"]
    ci = rnd.randrange(len(cycle))
    i = 0
    while i < len(units):
        if want[i] is not None:
            j = i
            while j + 1 < len(units) and want[j + 1] == want[i]:
                j += 1
            shots.append({"u0": i, "u1": j, "angle": want[i]})
            i = j + 1
            continue
        target = rnd.uniform(6, 14)
        j = i
        while j + 1 < len(units) and want[j + 1] is None and units[j]["e1"] - units[i]["e0"] < target:
            j += 1
        # A single long sentence can run to 20 s; beyond that it stays but gets a punch.
        angle = cycle[ci % len(cycle)]
        if shots and shots[-1]["angle"] == angle:
            ci += 1
            angle = cycle[ci % len(cycle)]
        ci += 1
        shots.append({"u0": i, "u1": j, "angle": angle})
        i = j + 1
    # No shot under 2.5 s: merge into the previous one (an angle the plan asked for stays).
    def asked(s):
        us = units[s["u0"]:s["u1"] + 1]
        return any(ang == s["angle"] and min(u["b"], y) - max(u["a"], x) > 0.5 * (u["b"] - u["a"]) for u in us for x, y, ang in overrides) \
            or any(ang == s["angle"] and min(u["e1"], y) - max(u["e0"], x) > 0.5 * (u["e1"] - u["e0"]) for u in us for x, y, ang in overrides_e)

    merged = []
    for s in shots:
        dur = units[s["u1"]]["e1"] - units[s["u0"]]["e0"]
        titled = any(in_title(u) for u in units[s["u0"]:s["u1"] + 1])
        if merged and dur < 2.5 and s["angle"] not in ("wide",) and not titled and not asked(s):
            merged[-1]["u1"] = s["u1"]
        else:
            merged.append(s)
    shots = merged

    # 3. Split shots at segment boundaries (the edit's own cuts) and set crops.
    out = []

    # A 1080p camera cannot take the face-sized crops a 4K one can: "framing" gives each
    # angle a zoom on the source frame instead ({"close.stage": 1.5, "close.medium": 2.0}).
    framing = plan.get("framing", {})

    def crop_for(angle, a, b):
        if angle == "screen":
            return plan.get("screenCrop")  # e.g. the 16:9 slide area of a 16:10 screen recording
        if angle in plan.get("fixedCrops", {}):
            return plan["fixedCrops"][angle]  # a static camera: a framing chosen by eye ([x, y, w, h] on the source)
        if angle in ("close.wide", "wide"):
            return None
        if angle == "close.widepunch":
            m = ok & (tt >= a - 0.5) & (tt <= b + 0.5)
            cx = float(np.median(fx[m])) if m.any() else float(np.nanmedian(fx))
            cw, ch = SW / 1.15, SH / 1.15
            x = min(max(cx - cw / 2, 0), SW - cw)
            return [round(x, 1), round((SH - ch) * 0.35, 1), round(cw, 1), round(ch, 1)]
        m = ok & (tt >= a - 0.5) & (tt <= b + 0.5)
        cx = float(np.median(fx[m])) if m.any() else float(np.nanmedian(fx))
        cy = float(np.median(fy[m])) if m.any() else float(np.nanmedian(fy))
        if angle in framing:
            cw = SW / framing[angle]
        else:
            frac = {"close.medium": 0.075, "close.punch": 0.084, "close.tight": 0.13}[angle]
            cw = min(SW, face_w / frac)
        ch = cw * H_OUT / W_OUT
        if ch > SH:
            ch, cw = SH, SH * W_OUT / H_OUT
        eye = {"close.medium": 0.36, "close.punch": 0.36, "close.tight": 0.40, "close.stage": 0.3, "close.stagepunch": 0.3}[angle]
        x = min(max(cx - cw / 2, 0), SW - cw)
        y = min(max(cy - eye * ch, 0), SH - ch)
        return [round(x, 1), round(y, 1), round(cw, 1), round(ch, 1)]

    for s in shots:
        us = units[s["u0"]:s["u1"] + 1]
        parts = [[us[0]]]
        for u in us[1:]:
            if u["k"] != parts[-1][-1]["k"]:
                parts.append([u])
            else:
                parts[-1].append(u)
        for n, p in enumerate(parts):
            angle = s["angle"]
            # A jump cut inside a shot becomes a framing change of the same size class.
            if n % 2 == 1:
                alt = {"close.medium": "close.punch", "close.wide": "close.widepunch", "wide": "close.wide",
                       "close.tight": "close.medium", "close.stage": "close.stagepunch"}.get(angle, angle)
                if not (alt.startswith("close.") and present(p[0]["a"], p[-1]["b"]) < 0.5):
                    angle = alt
            cam = "screen" if angle == "screen" else "wide" if angle == "wide" else "close"
            a, b = p[0]["a"], p[-1]["b"]
            e0, e1 = p[0]["e0"], p[-1]["e1"]
            out.append({"e0": round(e0, 3), "e1": round(e1, 3), "angle": angle, "cam": cam, "a": round(a, 3),
                        "crop": crop_for(angle if angle != "close.punch" else "close.punch", a, b),
                        "text": " ".join(W[q]["w"] for q in range(p[0]["i0"], min(p[0]["i0"] + 8, p[-1]["i1"] + 1)))})
    # Adjacent pieces of one segment inside the same shot were merged; make the timeline exact.
    for x, y in zip(out, out[1:]):
        y["e0"] = x["e1"]
    total = float(off[-1])
    if out:
        out[-1]["e1"] = round(total, 3)
    (d / "edit.shots.json").write_text(json.dumps(out, indent=1))
    from collections import Counter
    c = Counter(o["angle"] for o in out)
    lens = [o["e1"] - o["e0"] for o in out]
    print(f"{len(out)} shots over {total / 60:.1f} min; median {np.median(lens):.1f}s; " + ", ".join(f"{k} {v}" for k, v in c.most_common()))


if __name__ == "__main__":
    main()
