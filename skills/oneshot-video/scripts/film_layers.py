#!/usr/bin/env python3
"""Hand a from-scratch film to Premiere Pro (and Final Cut / Resolve) as editable layers.

  film_layers.py DIR [--comp Film] [--skip-render] [--fcpxml]

Renders the composition once per layer (the same code as the film, so every frame lines up) and
writes DIR/out/premiere/<name>.xml (File > Import) with:

  V1      plates: footage only, graded and moving, cut at timing.ts SHOTS
  V2      graphics: titles, boards, maps, cards, transitions, ProRes 4444 with alpha, cut at SCENES
  A1/A2   music stem        A3/A4  sound effects stem        A5/A6  voice stem (clips' own sound)
  A7/A8   the mastered film (out/<name>.mp4), muted, as a reference
  markers from MARKERS

Stems that are silent are left out. --fcpxml also writes the Final Cut / Resolve version (fcpxml.py).
The film must wrap everything in <Film layer={layer}> and mark footage with className="plate"
(Shot does); timing.ts exports FPS, W, H, T.total, SCENES, SHOTS and MARKERS as in the template.
"""
import argparse, json, subprocess, sys
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from premiere import Files, clipitem, sub  # noqa: E402

DUMP = """
import { createRequire } from "module";
const require = createRequire(process.cwd() + "/node_modules/");
const { build } = require("esbuild");
const r = await build({ entryPoints: ["src/timing.ts"], bundle: true, write: false, format: "esm", platform: "node", loader: { ".json": "json" } });
const m = await import("data:text/javascript;base64," + Buffer.from(r.outputFiles[0].text).toString("base64"));
console.log(JSON.stringify({ FPS: m.FPS, W: m.W, H: m.H, total: m.T.total, SCENES: m.SCENES ?? [], SHOTS: m.SHOTS ?? [], MARKERS: m.MARKERS ?? [] }));
"""


def run(cmd, cwd):
    print("$", " ".join(str(c) for c in cmd)[:150])
    subprocess.run([str(c) for c in cmd], check=True, cwd=cwd)


def silent(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    line = next((x for x in r.splitlines() if "max_volume" in x), "max_volume: -inf dB")
    v = line.split("max_volume:")[1].split()[0]
    return v == "-inf" or float(v) < -70


def rate(parent, fps):
    r = sub(parent, "rate")
    sub(r, "timebase", fps)
    sub(r, "ntsc", "FALSE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--comp", default="Film")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--fcpxml", action="store_true")
    args = ap.parse_args()
    d = Path(args.dir).resolve()
    name = d.name
    out = d / "out" / "premiere"
    media = out / "media"
    media.mkdir(parents=True, exist_ok=True)
    tm = json.loads(subprocess.run(["node", "--input-type=module", "-e", DUMP], cwd=d, capture_output=True, text=True, check=True).stdout)
    fps = int(tm["FPS"])

    if not args.skip_render:
        base = ["npx", "remotion", "render", "src/index.ts", args.comp, "--concurrency=8", "--log=error"]
        run(base + [media / "plates.mp4", "--props", '{"layer":"plates"}', "--muted", "--crf=12"], d)
        run(base + [media / "graphics.mov", "--props", '{"layer":"graphics"}', "--muted", "--codec=prores", "--prores-profile=4444",
                    "--image-format=png", "--pixel-format=yuva444p10le"], d)
        for stem in ("music", "sfx", "voice"):
            run(base + [media / f"stem_{stem}.wav", "--props", json.dumps({"layer": stem}), "--codec=wav"], d)
        final = d / "out" / f"{name}.mp4"
        if final.exists():
            run(["ffmpeg", "-v", "error", "-y", "-i", final, "-vn", "-ar", "48000", "-c:a", "pcm_s16le", media / "final_mix.wav"], d)

    fr = lambda s: round(s * fps)  # noqa: E731
    total = fr(tm["total"])
    root = ET.Element("xmeml", version="4")
    seq = sub(root, "sequence", id="sequence-1")
    sub(seq, "name", name)
    sub(seq, "duration", total)
    rate(seq, fps)
    tc = sub(seq, "timecode")
    rate(tc, fps)
    sub(tc, "string", "00:00:00:00")
    sub(tc, "frame", 0)
    sub(tc, "displayformat", "NDF")
    m = sub(seq, "media")
    video = sub(m, "video")
    sc = sub(sub(video, "format"), "samplecharacteristics")
    rate(sc, fps)
    for k, v in (("width", tm["W"]), ("height", tm["H"]), ("anamorphic", "FALSE"), ("pixelaspectratio", "square"), ("fielddominance", "none")):
        sub(sc, k, v)
    files = Files()
    n = 0
    for track_media, cuts in ((media / "plates.mp4", tm["SHOTS"] or [[0, tm["total"], "plates"]]),
                              (media / "graphics.mov", tm["SCENES"] or [[0, tm["total"], "graphics"]])):
        tr = sub(video, "track")
        for a, b, label in cuts:
            if fr(b) > fr(a):
                n += 1
                clipitem(tr, files, n, track_media, fr(a), min(fr(b), total), fr(a), name=label, fit=(100.0, 0.0, 0.0))
    audio = sub(m, "audio")
    kept = []
    for stem, label, enabled in (("stem_music.wav", "Music", True), ("stem_sfx.wav", "Sound effects", True),
                                 ("stem_voice.wav", "Voice", True), ("final_mix.wav", "Mastered film (reference)", False)):
        path = media / stem
        if not path.exists() or silent(path):
            continue
        kept.append(label)
        nf = min(files.dur(path), total)
        for ch in (1, 2):
            tr = sub(audio, "track")
            sub(tr, "outputchannelindex", ch)
            n += 1
            clipitem(tr, files, n, path, 0, nf, 0, name=label, audio=True, channel=ch, enabled=enabled)
    for t, label in tm["MARKERS"]:
        mk = sub(seq, "marker")
        sub(mk, "name", label)
        sub(mk, "comment", "")
        sub(mk, "in", fr(t))
        sub(mk, "out", -1)
    ET.indent(root)
    xml = out / f"{name}.xml"
    xml.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding="unicode") + "\n")
    (out / "README.md").write_text(f"""# {name}: the film as editable layers

1. **Premiere Pro:** File > Import, choose `{name}.xml`. **Final Cut Pro:** File > Import > XML, choose `{name}.fcpxml` (beta).
   **DaVinci Resolve:** File > Import > Timeline with either file (beta).
2. V1 is the footage (graded, with its moves), cut per shot. V2 is every graphic on alpha, cut per scene: turn it
   off to see the plates, or replace a scene's graphic. Both line up frame for frame with the film.
3. Audio: {", ".join(kept) or "none"}. The stems sum to the film before mastering; the mastered film sits muted at the
   bottom as a reference. On export, normalise to -14 LUFS / -2 dBTP to match it.
4. Markers: {", ".join(label for _, label in tm["MARKERS"]) or "none"}.
""")
    print(f"-> {xml}\n   V1 {len(tm['SHOTS'])} shots, V2 {len(tm['SCENES'])} scenes, audio: {', '.join(kept) or 'none'}, {len(tm['MARKERS'])} markers")
    if args.fcpxml:
        subprocess.run([sys.executable, str(SCRIPTS / "fcpxml.py"), str(xml)], check=True)


if __name__ == "__main__":
    main()
