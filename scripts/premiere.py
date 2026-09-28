#!/usr/bin/env python3
"""Hand a full edit to Premiere Pro: the same cuts on the original media, editable.

  premiere.py DIR/edit.json [--out DIR/out/premiere]

Writes an FCP7 XML sequence (File > Import in Premiere Pro, or drag it into the
Project panel) that rebuilds the rendered edit frame for frame on the camera originals:

  V1  every shot of edit.shots.json on its original file (camera or screen recording);
      punch-ins are Motion scale and position, the screen recording is shown 1:1
  V2  the rendered inserts (opening title, chapter titles, graphics, notes), full frame
  A1  the voice: the microphone, cleaned once over the whole recording and placed in
      camera time (voice-camtime.wav), cut exactly like the picture
  A2  the room microphone, only where the audience speaks
  markers  one per chapter

Next to it: the subtitles as .srt (File > Import, then drag onto the timeline for a
captions track), the camera grade as a .cube LUT (Lumetri > Basic Correction > Input
LUT, or on an adjustment layer) and a README. The timeline positions are the render's
own frame grid, so the .srt, the inserts and the markers line up with it unchanged.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from audio import CHAINS  # noqa: E402
from render import Timeline  # noqa: E402

FPS = 30
W_SEQ, H_SEQ = 1920, 1080


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,channels",
                                   "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    return {"duration": float(d["format"]["duration"]), "w": v and v["width"], "h": v and v["height"],
            "channels": a and a.get("channels")}


def cam_time(cam, t):
    return t + cam.get("offset", 0.0) + cam.get("drift", 0.0) * (t - cam.get("ref", 0.0))


def latency(src, chain, stream=None, at=(600.0, 1500.0, 2500.0), dur=20.0):
    """Samples of delay a filter chain adds (afftdn and arnndn add 25 to 35 ms and ffmpeg does
    not trim it), measured by cross-correlating the chain's output with its input on the
    original recording (median of a few speech windows)."""
    def pcm(t, af):
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(src), *(["-map", f"0:a:{stream}"] if stream is not None else []),
               "-t", f"{dur}", "-ac", "1", "-ar", "48000", *(["-af", af] if af else []), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
    lags = []
    for t in at:
        ref, out = pcm(t, None), pcm(t, chain)
        n = min(len(ref), len(out)) - 9600
        c = np.correlate(out[:n + 4800], ref[2400:2400 + n - 4800], mode="valid")
        lags.append(int(np.argmax(np.abs(c))) - 2400)
    return max(int(np.median(lags)), 0)


def loudnorm(src, dst, chain, target=-16, lag=None):
    """The cleaning chain with its latency trimmed, then two-pass loudness normalisation over the
    whole file (linear: dynamics untouched). Output is sample-aligned with the input."""
    lag = latency(src, chain) if lag is None else lag
    # Clean and trim in one pass, normalise in another: in a single graph loudnorm's dynamic
    # fallback shifts the trimmed stream again (18.7 ms measured).
    clean = Path(dst).with_suffix(".clean.wav")
    trim = f",atrim=start_sample={lag},asetpts=PTS-STARTPTS,apad=pad_len={lag}" if lag else ""
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "48000", "-af", chain + trim, "-c:a", "pcm_f32le", clean])
    pr = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(clean), "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(pr[pr.rindex("{"):pr.rindex("}") + 1])
    run(["ffmpeg", "-v", "error", "-y", "-i", clean, "-af",
         f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
         f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", dst])
    clean.unlink()


def voice_camtime(audio, picture_dur, out, words, clean="light", chunk=170.0):
    """The microphone placed on the picture camera's clock over the whole recording
    (audio_time = t + offset + drift * (t - ref)). Drift is absorbed in pauses: the track is
    cut into ~chunk-second pieces at gaps between words, each placed at its own offset, so
    sync stays within drift * chunk / 2 (2 ms for 2.4e-5 and 170 s) and nothing is resampled."""
    from audiosrc import AudioSrc

    src = AudioSrc({"audio": audio})
    tmp = Path(out).resolve().with_suffix(".parts")
    tmp.mkdir(exist_ok=True)
    start = max(0.0, -src.t(0.0) / (1 + src.drift))  # camera time of the microphone's first sample
    end = min(picture_dur, start + probe(audio["path"])["duration"])
    gaps = [(w["e"] + n["s"]) / 2 for w, n in zip(words, words[1:]) if n["s"] - w["e"] >= 0.3]
    bounds = [start]
    while bounds[-1] + chunk < end - 30:
        target = bounds[-1] + chunk
        bounds.append(min(gaps, key=lambda g: abs(g - target)) if gaps else target)
    bounds.append(end)
    parts = [tmp / "lead.wav"]
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-af", f"atrim=end_sample={round(start * 48000)}",
         "-c:a", "pcm_f32le", parts[0]])
    stream = ["-map", f"0:a:{audio['stream']}"] if audio.get("stream") is not None else ["-vn"]
    for k, (a, b) in enumerate(zip(bounds, bounds[1:])):
        p = tmp / f"p{k:03d}.wav"
        n = round(b * 48000) - round(a * 48000)  # sample-exact on the camera clock
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(src.t(a), 0):.6f}", "-i", audio["path"], *stream, "-ac", "1", "-ar", "48000",
             "-af", f"apad,atrim=end_sample={n}", "-c:a", "pcm_f32le", p])
        parts.append(p)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    pre = Path(out).with_suffix(".pre.wav")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-af", f"apad,atrim=end={picture_dur:.3f}", "-c:a", "pcm_f32le", pre])
    loudnorm(pre, out, CHAINS[clean], lag=latency(audio["path"], CHAINS[clean], audio.get("stream"), at=[src.t(t) for t in (600, 1500, 2500)]))
    pre.unlink()
    shutil.rmtree(tmp)


def cube_from_filter(vf, out, level=8):
    """An ffmpeg colour filter chain as a 3D LUT (.cube, 64 points) via a Hald CLUT."""
    n = level * level
    tmp = Path(out).with_suffix(".hald.png")
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"haldclutsrc=level={level}", "-frames:v", "1",
         "-vf", f"{vf},format=rgb48le", tmp])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp), "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"],
                         capture_output=True, check=True).stdout
    px = np.frombuffer(raw, np.uint16).reshape(-1, 3).astype(float) / 65535.0
    tmp.unlink()
    # Hald order: red fastest, then green, then blue; .cube uses the same order.
    lines = [f'TITLE "cutroom grade"', f"LUT_3D_SIZE {n}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    lines += [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in px[: n ** 3]]
    Path(out).write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- xml

def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if text is not None:
        e.text = str(text)
    return e


def rate(parent):
    r = sub(parent, "rate")
    sub(r, "timebase", FPS)
    sub(r, "ntsc", "FALSE")
    return r


class Files:
    """<file> elements: the full definition on first use, a reference afterwards."""

    def __init__(self):
        self.ids, self.info = {}, {}

    def get(self, path):
        path = str(Path(path).resolve())
        if path not in self.info:
            self.info[path] = probe(path)
        return self.info[path]

    def add(self, parent, path):
        path = str(Path(path).resolve())
        if path in self.ids:
            sub(parent, "file", id=self.ids[path])
            return
        fid = f"file-{len(self.ids) + 1}"
        self.ids[path] = fid
        info = self.get(path)
        f = sub(parent, "file", id=fid)
        sub(f, "name", Path(path).name)
        sub(f, "pathurl", "file://localhost" + quote(path))
        rate(f)
        sub(f, "duration", int(info["duration"] * FPS))
        m = sub(f, "media")
        if info["w"]:
            sc = sub(sub(m, "video"), "samplecharacteristics")
            rate(sc)
            sub(sc, "width", info["w"])
            sub(sc, "height", info["h"])
            sub(sc, "anamorphic", "FALSE")
            sub(sc, "pixelaspectratio", "square")
            sub(sc, "fielddominance", "none")
        if info["channels"]:
            au = sub(m, "audio")
            sc = sub(au, "samplecharacteristics")
            sub(sc, "depth", 16)
            sub(sc, "samplerate", 48000)
            sub(au, "channelcount", info["channels"])

    def dur(self, path):
        return int(self.get(path)["duration"] * FPS)


def motion(parent, scale, horiz, vert):
    e = sub(sub(parent, "filter"), "effect")
    sub(e, "name", "Basic Motion")
    sub(e, "effectid", "basic")
    sub(e, "effectcategory", "motion")
    sub(e, "effecttype", "motion")
    sub(e, "mediatype", "video")
    p = sub(e, "parameter", authoringApp="PremierePro")
    sub(p, "parameterid", "scale")
    sub(p, "name", "Scale")
    sub(p, "valuemin", 0)
    sub(p, "valuemax", 1000)
    sub(p, "value", f"{scale:.3f}")
    p = sub(e, "parameter", authoringApp="PremierePro")
    sub(p, "parameterid", "center")
    sub(p, "name", "Center")
    v = sub(p, "value")
    sub(v, "horiz", f"{horiz:.6f}")
    sub(v, "vert", f"{vert:.6f}")


def clipitem(track, files, n, path, start, end, src_in, name=None, audio=False, fit=None):
    ci = sub(track, "clipitem", id=f"clipitem-{n}")
    sub(ci, "name", name or Path(path).name)
    sub(ci, "duration", files.dur(path))
    rate(ci)
    sub(ci, "start", start)
    sub(ci, "end", end)
    sub(ci, "enabled", "TRUE")
    sub(ci, "in", src_in)
    sub(ci, "out", src_in + end - start)
    files.add(ci, path)
    if audio:
        st = sub(ci, "sourcetrack")
        sub(st, "mediatype", "audio")
        sub(st, "trackindex", 1)
    elif fit is not None:
        motion(ci, *fit)
    return ci


def crop_fit(crop, sw, sh):
    """A source-pixel crop [x, y, w, h] as Premiere Motion: scale (%) and centre (fractions of
    the sequence frame from its middle, +x right, +y down)."""
    if not crop:
        crop = [0, 0, sw, sh] if sw * H_SEQ == sh * W_SEQ else [0, (sh - sw * H_SEQ / W_SEQ) / 2, sw, sw * H_SEQ / W_SEQ]
    x, y, w, h = crop
    s = W_SEQ / w
    dx, dy = x + w / 2 - sw / 2, y + h / 2 - sh / 2
    return 100.0 * s, -s * dx / W_SEQ, -s * dy / H_SEQ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    args = ap.parse_args()
    plan_path = Path(args.plan).resolve()
    d = plan_path.parent
    plan = json.loads(plan_path.read_text())
    W = json.loads(Path(plan["source"]["words"]).read_text())["words"]
    tl = Timeline(plan["segments"], W)
    shots = json.loads((d / "edit.shots.json").read_text())
    cams = {c["id"]: c for c in plan["source"]["cameras"]}
    proj = json.loads((d / "project.json").read_text())
    out = Path(args.out) if args.out else d / "out" / "premiere"
    out.mkdir(parents=True, exist_ok=True)
    media = out / "media"
    media.mkdir(exist_ok=True)
    fr = lambda t: int(round(t * FPS))  # noqa: E731

    # ---- sound on the camera's clock, cleaned once
    close = cams["close"]
    pic_dur = probe(close["path"])["duration"]
    voice = media / "voice-camtime.wav"
    if not voice.exists():
        voice_camtime(proj["audio"], pic_dur, voice, [w for w in W if w.get("src") != "room"])
        print(f"voice -> {voice}")
    room = media / "room-camtime.wav"
    if not room.exists():
        loudnorm(close["path"], room, CHAINS["rnn"])
        print(f"room -> {room}")

    root = ET.Element("xmeml", version="4")
    seq = sub(root, "sequence", id="sequence-1")
    sub(seq, "name", plan.get("title") or plan["id"])
    total = fr(tl.duration)
    sub(seq, "duration", total)
    rate(seq)
    tc = sub(seq, "timecode")
    rate(tc)
    sub(tc, "string", "00:00:00:00")
    sub(tc, "frame", 0)
    sub(tc, "displayformat", "NDF")
    m = sub(seq, "media")
    video = sub(m, "video")
    sc = sub(sub(video, "format"), "samplecharacteristics")
    rate(sc)
    for k, v in (("width", W_SEQ), ("height", H_SEQ), ("anamorphic", "FALSE"), ("pixelaspectratio", "square"), ("fielddominance", "none")):
        sub(sc, k, v)
    files = Files()
    n = 0

    # V1: shots
    v1 = sub(video, "track")
    for s in shots:
        f0, f1 = fr(s["e0"]), fr(s["e1"])
        if f1 <= f0:
            continue
        cam = cams[s["cam"]]
        info = files.get(cam["path"])
        n += 1
        clipitem(v1, files, n, cam["path"], f0, f1, fr(cam_time(cam, s["a"])), name=f"{s['angle']} · {s.get('text', '')[:40]}",
                 fit=crop_fit(s.get("crop"), info["w"], info["h"]))

    # V2: rendered inserts (same placement as longrender.py)
    v2 = sub(video, "track")
    ins_dir = d / "inserts"
    placed = []
    for k, ins in enumerate(plan.get("inserts", [])):
        vid = ins_dir / f"insert-{k:02d}.mp4"
        if not vid.exists():
            continue
        a, b = tl.ref(ins["from"]), tl.ref(ins["to"])
        f0 = fr(a)
        dst = media / f"{k:02d}-{ins.get('kind', 'insert')}.mp4"
        if not dst.exists() or dst.stat().st_size != vid.stat().st_size:
            shutil.copy2(vid, dst)
        nf = files.dur(dst)  # the same frame count the <file> element declares
        n += 1
        clipitem(v2, files, n, dst, f0, f0 + nf, 0, name=f"{ins.get('kind', 'insert')} {k:02d}", fit=(100.0, 0.0, 0.0))
        placed.append((f0, ins.get("kind")))

    audio = sub(m, "audio")
    sub(audio, "numOutputChannels", 2)
    af = sub(sub(audio, "format"), "samplecharacteristics")
    sub(af, "depth", 16)
    sub(af, "samplerate", 48000)

    # A1: the voice, cut exactly like the picture (segments on the render's frame grid)
    a1 = sub(audio, "track")
    for k, s in enumerate(plan["segments"]):
        f0, f1 = fr(tl.off[k]), fr(tl.off[k + 1])
        if f1 <= f0:
            continue
        n += 1
        clipitem(a1, files, n, voice, f0, f1, fr(s["a"]), name=" ".join(W[i]["w"] for i in range(s["w"][0], min(s["w"][0] + 6, s["w"][1] + 1))),
                 audio=True)

    # A2: the room microphone while the audience speaks
    a2 = sub(audio, "track")
    sig = json.loads((d / "signals.json").read_text()) if (d / "signals.json").exists() else {}
    aud = [(x["a"] - 0.25, x["b"] + 0.4) for x in sig.get("speech", []) if x["who"] == "audience" and x["b"] - x["a"] >= 0.5]
    for r in plan.get("audience", []):
        aud.append((W[int(str(r["from"]).lstrip("#"))]["s"] - 0.45, W[int(str(r["to"]).lstrip("#"))]["e"] + 0.6))
    spans = []
    for x0, x1 in aud:
        for k, s in enumerate(tl.segs):
            a, b = max(x0, s["a"]), min(x1, s["b"])
            if b - a > 0.3:
                spans.append((fr(tl.off[k] + a - s["a"]), fr(tl.off[k] + b - s["a"]), fr(a)))
    spans.sort()
    last_end = -1
    for f0, f1, src_in in spans:
        if f0 < last_end:
            src_in += last_end - f0
            f0 = last_end
        if f1 <= f0:
            continue
        n += 1
        clipitem(a2, files, n, room, f0, f1, src_in, name="audience", audio=True)
        last_end = f1

    # Chapter markers
    for c in plan.get("chapters", []):
        mk = sub(seq, "marker")
        sub(mk, "name", c["title"])
        sub(mk, "comment", "chapter")
        sub(mk, "in", fr(tl.ref(c["at"])))
        sub(mk, "out", -1)

    ET.indent(root)
    xml_path = out / f"{plan['id']}.xml"
    xml_path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding="unicode") + "\n")

    # Subtitles, grade LUT, readme
    srt = d / "out" / f"{plan['id']}.srt"
    if srt.exists():
        shutil.copy2(srt, out / srt.name)
    grade = json.loads((d / "grade.json").read_text()) if (d / "grade.json").exists() else {}
    luts, done = [], set()
    for cid, vf in grade.items():
        vf = ",".join(f for f in str(vf).split(",") if not f.startswith(("unsharp", "cas", "smartblur")))  # colour only
        if cid in cams and vf and vf != "null" and vf not in done:
            done.add(vf)
            lut = out / f"grade-{cid}.cube"
            cube_from_filter(vf, lut)
            luts.append(lut.name)
    v1n = sum(1 for _ in v1)
    sharpen = any("unsharp" in str(v) for v in grade.values())
    from collections import Counter
    names = {"title": "opening title", "chapter": "chapter title", "broll": "graphic", "note": "note"}
    kinds = ", ".join(f"{c} {names.get(k, k)}{'s' if c > 1 else ''}" for k, c in Counter(kind for _, kind in placed).items()) or "none"
    (out / "README.md").write_text(f"""# {plan.get('title') or plan['id']}: the edit, for Premiere Pro

1. **Open the timeline.** File > Import, choose `{xml_path.name}` (or drag it into the Project panel). Premiere
   builds the sequence at 1920x1080, 30 fps, with every shot, cut and graphic of the rendered video on the
   original files: the camera and the screen recording where they are now, the rest in `media/`.
   If anything shows as offline: right-click it > Link Media and point at the file.
2. **Subtitles.** File > Import, choose `{plan['id']}.srt`, then drag it onto the timeline: Premiere makes a
   captions track you can edit word by word (Window > Text).
3. **Colour.** The clips come in ungraded. Add an adjustment layer over V1 and load `{luts[0] if luts else 'the .cube'}` in
   Lumetri Color > Basic Correction > Input LUT.{' The render also sharpens the punch-ins lightly: Lumetri > Creative > Sharpen about 15.' if sharpen else ''}
4. **Loudness.** The voice sits near -16 LUFS. On export, turn on Effects > Loudness Normalization
   (ITU BS.1770-3, -14 LUFS, -1 dBTP) to match the render.

Tracks
- V1: every shot on the original media. Punch-ins are Motion > Scale and Position; the screen recording is 1:1.
- V2: the graphics ({kinds}), rendered full frame with the picture under them. Turn V2 off to see the raw
  shots. If you retime a shot under a graphic, re-render the graphic in cutroom or delete it.
- A1: the lavalier, cleaned once over the whole lecture (`media/voice-camtime.wav`), cut exactly like the picture.
- A2: the room camera's microphone, only where students speak.
- Markers: one per chapter (they are also the YouTube chapters in `chapters.txt` next to the render).

Every cut sits on a pause or a word boundary; ripple-delete, trim or extend any clip and the audio follows
because A1 is cut on the same frames as V1.
""")
    print(f"-> {xml_path}\n   V1 {v1n} shots, V2 {len(placed)} inserts, A1 {sum(1 for _ in a1)} voice clips, A2 {sum(1 for _ in a2)} room clips, "
          f"{len(plan.get('chapters', []))} markers; {total / FPS / 60:.1f} min" + (f"; LUT {', '.join(luts)}" if luts else ""))


if __name__ == "__main__":
    main()
