#!/usr/bin/env python3
"""Check a finished full edit before anyone watches it.

  longqa.py DIR/edit.json [--video DIR/out/<id>-full.mp4]

- Sound: integrated loudness and true peak (target -14 LUFS, below -1 dBTP).
- Picture: black frames anywhere; frozen picture on a camera shot (a static slide or a
  graphic hold is fine; a camera that stops moving for 4 s is aimed at an empty spot).
- Speaker lost: camera shots where the picture camera's tracker saw no face.
- Inserts: a contact sheet (DIR/out/inserts-sheet.jpg) with every title, chapter title,
  note and B-roll graphic, labelled, to read for overlaps and titles over slides.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import Timeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--video")
    args = ap.parse_args()
    plan_path = Path(args.plan)
    d = plan_path.parent
    plan = json.loads(plan_path.read_text())
    video = Path(args.video or d / "out" / f"{plan['id']}-full.mp4")
    W = json.loads(Path(plan["source"]["words"]).read_text())["words"]
    tl = Timeline(plan["segments"], W)
    shots = json.loads((d / "edit.shots.json").read_text())
    problems = []

    er = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", er)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", er)[-1])
    print(f"sound: {lufs} LUFS, true peak {peak} dBFS")
    if abs(lufs + 14) > 1 or peak > -0.5:
        problems.append(f"loudness {lufs} LUFS / peak {peak} dBFS")

    ins = []
    for n, x in enumerate(plan.get("inserts", [])):
        ins.append((n, x.get("kind", ""), tl.ref(x["from"]), tl.ref(x["to"])))
    vf = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf",
                         "scale=320:-2,blackdetect=d=0.3:pix_th=0.08,freezedetect=n=0.002:d=4", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", vf):
        problems.append(f"black {float(a):.1f}-{float(b):.1f}s")
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", vf)]
    durs = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", vf)]
    for s, du in zip(starts, durs):
        m = s + du / 2
        if any(a <= m < b for _, k, a, b in ins if k == "broll"):
            continue
        shot = next((x for x in shots if x["e0"] <= m < x["e1"]), None)
        if shot and shot["cam"] != "screen":
            problems.append(f"frozen {shot['angle']} {s:.1f}s for {du:.1f}s: \"{shot['text'][:40]}\"")

    track = next((c.get("track") for c in plan["source"]["cameras"] if c["id"] == "close"), None)
    if track and Path(track).exists():
        tr = json.loads(Path(track).read_text())
        tt = np.array(tr["times"])
        ok = np.array([p is not None for p in tr["subject"]])
        for x in shots:
            if x["cam"] != "close":
                continue
            m = (tt >= x["a"]) & (tt <= x["a"] + x["e1"] - x["e0"])
            if m.sum() >= 3 and ok[m].mean() < 0.5:
                problems.append(f"speaker not in {x['angle']} at {x['e0']:.1f}s ({x['e1'] - x['e0']:.1f}s)")

    tiles = []
    for n, kind, a, b in ins:
        t = a + min(2.2, (b - a) * 0.6) if kind in ("title", "chapter", "note") else a + (b - a) * 0.7
        f = d / "out" / f".qa-{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf",
                        f"scale=480:-2,drawtext=text='{n} {kind} {t:.0f}s':x=8:y=8:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6",
                        str(f)], check=True)
        tiles.append(f)
        for n2, k2, a2, b2 in ins:
            if n2 > n and min(b, b2) - max(a, a2) > 0.2:
                problems.append(f"inserts {n} ({kind}) and {n2} ({k2}) overlap at {max(a, a2):.1f}s")
        shot = next((x for x in shots if x["e0"] <= a + 0.5 < x["e1"]), None)
        if kind in ("title", "chapter") and shot and shot["cam"] == "screen":
            problems.append(f"insert {n} ({kind}) title over the screen recording at {a:.1f}s")
    if tiles:
        cols = 5
        tiles += [tiles[-1]] * (-len(tiles) % cols)
        inp = [x for f in tiles for x in ("-i", str(f))]
        sheet = d / "out" / "inserts-sheet.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex",
                        f"xstack=inputs={len(tiles)}:grid={cols}x{len(tiles) // cols}", str(sheet)], check=True)
        for f in set(tiles):
            f.unlink()
        print(f"inserts: {len(ins)} -> {sheet}")

    print("\n".join(["problems:"] + [f"  - {p}" for p in problems]) if problems else "no problems found")


if __name__ == "__main__":
    main()
