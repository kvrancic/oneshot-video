#!/usr/bin/env python3
"""Render a full edit: shots -> picture, Remotion inserts, subtitles, sound, chapters.

  longrender.py DIR/edit.json [--preview 0-180] [--jobs 4] [--audio-only] [--skip-shots]

1. Sound: the lavalier over the edit timeline (audio.py, adaptive cleaning), the room
   microphone gated in during audience turns (signals.json), limiter, -14 LUFS.
2. Shots: every shot of edit.shots.json cut from its camera's original (crop, scale,
   grade from grade.json), hardware-encoded in parallel, joined without re-encoding.
3. Inserts: plan "inserts" (the opening title behind the speaker, chapter titles,
   notes, motion-graphics B-roll) rendered by Remotion over their slice of the picture
   and laid over it.
4. Subtitles: sentence captions burned in with libass (Inter SemiBold, soft outline and
   shadow; a soft box over screen-recording shots so slide footers stay readable), plus
   an .srt, YouTube chapters and a cut list.
--preview renders only that span of the edit (seconds) for a style check.
"""
import argparse, json, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
RENDERER = ROOT / "renderer"
FONTS = ROOT / "assets" / "fonts"
PY = sys.executable
FPS = 30
sys.path.insert(0, str(SCRIPTS))
from render import Timeline, resolve_obj, stage, retime, stale, stamp  # noqa: E402

FILLERS = {"um", "uh", "uhm", "erm", "er", "ah", "hmm", "mm", "mhm"}


TIME_KEYS = ("from", "to", "at", "until", "land", "subAt", "idsAt", "pickAt")


def shift_times(o, delta):
    """Every resolved time inside an insert moves onto the insert's own clock."""
    if isinstance(o, list):
        return [shift_times(x, delta) for x in o]
    if not isinstance(o, dict):
        return o
    out = {}
    for k, v in o.items():
        if k == "kenburns":  # {from: [x, y, scale], to: [...]} is a framing, not times
            out[k] = v
        elif k in TIME_KEYS and isinstance(v, (int, float)):
            out[k] = round(v - delta, 3)
        elif k in TIME_KEYS and isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
            out[k] = [round(x - delta, 3) for x in v]
        else:
            out[k] = shift_times(v, delta)
    return out


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def cam_time(cam, t):
    return t + cam.get("offset", 0.0) + cam.get("drift", 0.0) * (t - cam.get("ref", 0.0))


def fmt_ts(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_ts(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def srt_ts(t):
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------- words -> cues

def edit_tokens(plan, tl, W):
    cap = plan.get("captions", {})
    fixes = {int(k): v for k, v in cap.get("fixes", {}).items()}
    drop = set(cap.get("drop", [])) | set(plan.get("cut", []))
    toks = []
    for k, s in enumerate(tl.segs):
        i0, i1 = s["w"]
        for i in range(i0, i1 + 1):
            if i in drop:
                continue
            text = fixes.get(i, W[i]["w"])
            if not text or re.sub(r"[^a-z]", "", text.lower()) in FILLERS:
                continue
            a = float(tl.off[k] + max(W[i]["s"], s["a"]) - s["a"])
            b = float(tl.off[k] + min(W[i]["e"], s["b"]) - s["a"])
            if b > a:
                toks.append({"text": text, "start": round(a, 3), "end": round(b, 3), "src": i})
    return toks


_FONT = {}


def plate(text, size=46, margin_v=64, pad_x=26, pad_y=14, radius=12):
    """One rounded translucent box behind a whole subtitle (an ASS vector drawing), so two
    lines never stack two semi-transparent boxes into a darker band."""
    from PIL import ImageFont

    if size not in _FONT:
        # libass sizes a font so ascender + descender equal the point size; PIL sizes the em.
        probe = ImageFont.truetype(str(FONTS / "Inter-SemiBold.ttf"), 1000)
        a, d = probe.getmetrics()
        _FONT[size] = ImageFont.truetype(str(FONTS / "Inter-SemiBold.ttf"), max(1, round(size * 1000 / (a + d))))
    f = _FONT[size]
    lines = text.split("\\N")
    w = max(f.getlength(l) for l in lines) + 2 * pad_x
    h = size * len(lines) + 2 * pad_y
    r = radius
    x0, y0 = -w / 2, -h
    x1, y1 = w / 2, 0
    path = (f"m {x0 + r:.0f} {y0:.0f} l {x1 - r:.0f} {y0:.0f} b {x1:.0f} {y0:.0f} {x1:.0f} {y0:.0f} {x1:.0f} {y0 + r:.0f} "
            f"l {x1:.0f} {y1 - r:.0f} b {x1:.0f} {y1:.0f} {x1:.0f} {y1:.0f} {x1 - r:.0f} {y1:.0f} l {x0 + r:.0f} {y1:.0f} "
            f"b {x0:.0f} {y1:.0f} {x0:.0f} {y1:.0f} {x0:.0f} {y1 - r:.0f} l {x0:.0f} {y0 + r:.0f} b {x0:.0f} {y0:.0f} {x0:.0f} {y0:.0f} {x0 + r:.0f} {y0:.0f}")
    return f"{{\\an7\\pos(960,{1080 - margin_v + pad_y:.0f})\\p1}}{path}"


def cues_from(tokens, max_chars=84, max_line=44, max_dur=6.5):
    cues, cur = [], []
    for t in tokens:
        if cur:
            text = " ".join(x["text"] for x in cur + [t])
            gap = t["start"] - cur[-1]["end"]
            # A sentence's last word may run a little long rather than open the next cue alone.
            fin = bool(re.search(r"[.!?][\"')\]]?$", t["text"]))
            if (len(text) > max_chars + (12 if fin else 0) or t["end"] - cur[0]["start"] > max_dur + (1.5 if fin else 0) or gap > 1.2
                    or re.search(r"[.!?][\"')\]]?$", cur[-1]["text"]) and len(" ".join(x["text"] for x in cur)) > 18):
                cues.append(cur)
                cur = []
        cur.append(t)
    if cur:
        cues.append(cur)
    out = []
    for c in cues:
        words = [x["text"] for x in c]
        text = " ".join(words)
        if len(text) > max_line and len(words) > 1:
            best, bi = 1e9, 1
            for k in range(1, len(words)):
                l1, l2 = " ".join(words[:k]), " ".join(words[k:])
                score = max(len(l1), len(l2)) - (6 if re.search(r"[,;:]$", words[k - 1]) else 0)
                if score < best:
                    best, bi = score, k
            text = " ".join(words[:bi]) + "\\N" + " ".join(words[bi:])
        text = text[0].upper() + text[1:] if text else text
        out.append({"start": c[0]["start"] - 0.08, "end": c[-1]["end"] + 0.35, "text": text})
    for x, y in zip(out, out[1:]):
        x["end"] = min(x["end"], y["start"] - 0.02)
    return out


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Inter SemiBold,48,&H00F4F1EA,&H000000FF,&H73000000,&H8C000000,0,0,0,0,100,100,-0.3,0,1,2.2,2,2,140,140,64,1
Style: Box,Inter SemiBold,46,&H00F4F1EA,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,-0.3,0,1,0,0,2,140,140,64,1
Style: Plate,Inter SemiBold,46,&H4D0B0B0B,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--preview", help="A-B edit seconds")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--skip-shots", action="store_true", help="reuse rendered shots")
    ap.add_argument("--bitrate", default="8M")
    args = ap.parse_args()
    plan_path = Path(args.plan).resolve()
    d = plan_path.parent
    plan = json.loads(plan_path.read_text())
    W = json.loads(Path(plan["source"]["words"]).read_text())["words"]
    tl = Timeline(plan["segments"], W)
    shots = json.loads((d / "edit.shots.json").read_text())
    grade = json.loads((d / "grade.json").read_text()) if (d / "grade.json").exists() else {}
    cams = {c["id"]: c for c in plan["source"]["cameras"]}
    total = tl.duration
    p0, p1 = (0.0, total)
    if args.preview:
        p0, p1 = [float(x) for x in args.preview.split("-")]
        p1 = min(p1, total)
    tag = f"preview-{int(p0)}-{int(p1)}" if args.preview else "full"
    out_dir = d / "out"
    out_dir.mkdir(exist_ok=True)
    t_start = time.time()

    # ---- 1. sound
    voice = d / "voice.wav"
    if not voice.exists():
        run([PY, SCRIPTS / "audio.py", "--plan", plan_path, "--out", voice])
    room = d / "room.wav"
    if not room.exists():
        room_plan = d / ".room.plan.json"
        room_plan.write_text(json.dumps({**plan, "source": {"video": plan["source"]["video"]}}))
        run([PY, SCRIPTS / "audio.py", "--plan", room_plan, "--out", room, "--clean", "rnn"])
    sig = json.loads((d / "signals.json").read_text())
    turns = []
    # Every audience turn from 0.5 s up (a shouted guess counts), plus ranges the plan adds by hand.
    aud = [x for x in sig.get("speech", []) if x["who"] == "audience" and x["b"] - x["a"] >= 0.5]
    for r in plan.get("audience", []):
        aud.append({"a": W[int(str(r["from"]).lstrip("#"))]["s"] - 0.2, "b": W[int(str(r["to"]).lstrip("#"))]["e"] + 0.2})
    for x in aud:
        for k, s in enumerate(tl.segs):
            a, b = max(x["a"], s["a"]), min(x["b"], s["b"])
            if b - a > 0.3:
                turns.append((float(tl.off[k] + a - s["a"]), float(tl.off[k] + b - s["a"])))
    gate = "+".join(f"clip((t-{a - 0.25:.2f})/0.25,0,1)*clip(({b + 0.4:.2f}-t)/0.4,0,1)" for a, b in turns) or "0"
    mixed = d / "mix.wav"
    if not mixed.exists() or args.audio_only:
        pre = d / ".mix.pre.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", room, "-filter_complex",
             f"[1:a]volume='min(1,{gate})':eval=frame[r];[0:a][r]amix=inputs=2:normalize=0:duration=first[m]",
             "-map", "[m]", "-ar", "48000", "-ac", "2", pre])
        pr = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af",
                             "alimiter=limit=0.89:level=false,loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        m = json.loads(pr[pr.rindex("{"):pr.rindex("}") + 1])
        run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
             f"alimiter=limit=0.89:level=false,loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
             f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
             "-ar", "48000", mixed])
        pre.unlink(missing_ok=True)
        print(f"sound: lavalier + room for {len(turns)} audience turns, -14 LUFS ({time.time() - t_start:.0f}s)")

    # ---- subtitles
    tokens = edit_tokens(plan, tl, W)
    tok_path = d / "tokens.json"
    if not tok_path.exists():
        frac, med, mx = retime(tokens, voice)
        print(f"captions re-timed on the voice: {frac:.0%} matched, median shift {med * 1000:.0f} ms")
        tok_path.write_text(json.dumps(tokens))
    tokens = json.loads(tok_path.read_text())
    cues = cues_from(tokens)
    screen_spans = [(s["e0"], s["e1"]) for s in shots if s["cam"] == "screen"]
    # Inserts over a light picture (a title card) ask for the boxed subtitle too.
    screen_spans += [(tl.ref(i["from"]), tl.ref(i["to"])) for i in plan.get("inserts", []) if i.get("captionBox")]
    ins_spans = []
    lines = []
    srt = []
    for n, c in enumerate(cues, 1):
        mid = (c["start"] + c["end"]) / 2
        style = "Box" if any(a <= mid < b for a, b in screen_spans) else "Sub"
        if c["end"] > p0 and c["start"] < p1:
            if style == "Box":
                lines.append(f"Dialogue: 0,{ass_ts(c['start'] - p0)},{ass_ts(c['end'] - p0)},Plate,,0,0,0,,{plate(c['text'])}")
            lines.append(f"Dialogue: 1,{ass_ts(c['start'] - p0)},{ass_ts(c['end'] - p0)},{style},,0,0,0,,{c['text']}")
        srt.append(f"{n}\n{srt_ts(c['start'])} --> {srt_ts(c['end'])}\n{c['text'].replace(chr(92) + 'N', chr(10))}\n")
    ass = d / f"captions-{tag}.ass"
    ass.write_text(ASS_HEAD + "\n".join(lines) + "\n")
    (out_dir / f"{plan['id']}.srt").write_text("\n".join(srt))

    if args.audio_only:
        final = out_dir / f"{plan['id']}-{tag}.mp4"
        tmp = final.with_suffix(".remux.mp4")
        run(["ffmpeg", "-v", "error", "-y", "-i", final, "-i", mixed, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
             "-b:a", "256k", "-shortest", tmp])
        tmp.replace(final)
        print(f"-> {final} (new sound)")
        return

    # ---- 2. shots
    shot_dir = d / "shots"
    shot_dir.mkdir(exist_ok=True)
    todo = [(i, s) for i, s in enumerate(shots) if s["e1"] > p0 and s["e0"] < p1]

    def render_shot(item):
        i, s = item
        f0, f1 = round(max(s["e0"], p0) * FPS), round(min(s["e1"], p1) * FPS)
        nfr = f1 - f0
        import hashlib
        key = hashlib.sha1(json.dumps([s["cam"], s.get("crop"), s["a"], s["angle"], grade.get(s["cam"])]).encode()).hexdigest()[:8]
        out = shot_dir / f"{f0}-{f1}-{key}.mp4"  # named by content: a changed shot list reuses every unchanged shot
        if out.exists() and args.skip_shots or out.exists() and out.stat().st_size > 1000:
            return out
        cam = cams[s["cam"]]
        t = cam_time(cam, s["a"] + (f0 / FPS - s["e0"]))
        vf = []
        if s.get("crop"):
            x, y, w, h = [int(round(v / 2) * 2) for v in s["crop"]]
            vf.append(f"crop={w}:{h}:{x}:{y}")
        vf += ["scale=1920:1080:flags=lanczos", "setsar=1", "fps=30"]
        g = grade.get(s["cam"])
        if g and g != "null":
            vf.append(g)
        vf.append("format=yuv420p")
        cmd = ["ffmpeg", "-v", "error", "-y", "-hwaccel", "videotoolbox", "-ss", f"{max(t, 0):.3f}", "-i", cam["path"],
               "-frames:v", str(nfr), "-vf", ",".join(vf), "-an", "-c:v", "h264_videotoolbox", "-b:v", "14M",
               "-profile:v", "high", "-g", "60", "-r", "30", out]
        try:
            run(cmd)
        except subprocess.CalledProcessError:
            # A camera that was not rolling here: fall back to the picture camera, full frame.
            c2 = cams["close"]
            run(["ffmpeg", "-v", "error", "-y", "-hwaccel", "videotoolbox", "-ss", f"{max(cam_time(c2, s['a']), 0):.3f}", "-i",
                 c2["path"], "-frames:v", str(nfr), "-vf", f"scale=1920:1080:flags=lanczos,setsar=1,fps=30,{grade.get('close', 'null')},format=yuv420p",
                 "-an", "-c:v", "h264_videotoolbox", "-b:v", "14M", "-profile:v", "high", "-g", "60", "-r", "30", out])
        # A short decode (a camera that stopped early) is padded with its last frame.
        got = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                  "stream=nb_read_packets", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip() or 0)
        if got < nfr:
            pad = out.with_suffix(".pad.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vf", f"tpad=stop_mode=clone:stop={nfr - got}", "-an",
                 "-c:v", "h264_videotoolbox", "-b:v", "14M", "-profile:v", "high", "-g", "60", "-r", "30", pad])
            pad.replace(out)
        return out

    t1 = time.time()
    with ThreadPoolExecutor(args.jobs) as ex:
        files = list(ex.map(render_shot, todo))
    lst = d / f".shots-{tag}.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    picture = d / f"picture-{tag}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", picture])
    print(f"picture: {len(files)} shots in {time.time() - t1:.0f}s")

    # ---- 3. inserts (Remotion over their slice of the picture)
    job_dir = RENDERER / "public" / "jobs" / plan["id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    src_rev = max(f.stat().st_mtime for f in (RENDERER / "src").rglob("*.ts*"))  # a renderer change re-renders inserts
    for n, ins in enumerate(plan.get("inserts", [])):
        # Plain numbers on an insert's overlays and layout spans are seconds from the
        # insert's start; word references are absolute. Make everything absolute, resolve,
        # then move it all onto the insert's own clock.
        a_abs = tl.ref(ins["from"])
        ins = json.loads(json.dumps(ins))
        for o in ins.get("overlays", []) + ins.get("layout", []):
            for key in ("from", "to"):
                if isinstance(o.get(key), (int, float)):
                    o[key] = a_abs + o[key]
        r = resolve_obj(ins, tl, d, job_dir)
        a, b = r["from"], r["to"]
        if b <= p0 or a >= p1:
            continue
        a, b = max(a, p0), min(b, p1)
        seg = d / "inserts" / f"plate-{n:02d}.mp4"
        seg.parent.mkdir(exist_ok=True)
        # A plate depends only on the shots under it; unchanged inserts are not rebuilt.
        plate_key = [round(a, 3), round(b, 3), [[s["e0"], s["e1"], s["cam"], s.get("crop"), s["a"], grade.get(s["cam"])]
                                                for s in shots if s["e1"] > a and s["e0"] < b]]
        if stale(seg, key=plate_key):
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a - p0:.3f}", "-i", picture, "-frames:v", str(round((b - a) * FPS)),
                 "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-g", "15", "-pix_fmt", "yuv420p", seg])
            stamp(seg, plate_key)
        r = shift_times(r, a)
        ovs = []
        for o in r.get("overlays", []):
            o = dict(o)
            o.setdefault("from", 0.0)
            o.setdefault("to", b - a)
            if o["type"] == "TextBehind":
                fg = seg.with_name(f"fg-{n:02d}.webm")
                fg_key = [plate_key, o["from"], o["to"]]
                if stale(fg, key=fg_key):
                    matte = subprocess.Popen([str(ROOT / "bin" / "matte"), str(seg), f"{o['from']:.3f}", f"{o['to'] - o['from']:.3f}",
                                              "1920", "1080"], stdout=subprocess.PIPE)
                    run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "1920x1080", "-r", str(FPS), "-i", "-",
                         "-ss", f"{o['from']:.3f}", "-t", f"{o['to'] - o['from']:.3f}", "-i", seg, "-filter_complex",
                         "[1:v][0:v]alphamerge,format=yuva420p", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "8M",
                         "-deadline", "good", "-cpu-used", "4", "-an", fg], stdin=matte.stdout)
                    matte.wait()
                    stamp(fg, fg_key)
                o.setdefault("props", {})["fg"] = stage(fg, job_dir, f"fg-{n:02d}.webm")
            ovs.append(o)
        spans = []
        for sp in r.get("layout", []):
            sp = dict(sp)
            sp.setdefault("from", 0.0)
            sp.setdefault("to", b - a)
            spans.append(sp)
        props = {"id": plan["id"], "format": "16x9", "fps": FPS, "durationInFrames": round((b - a) * FPS),
                 "palette": plan.get("palette", "paper"), "plate": stage(seg, job_dir, f"plate-{n:02d}.mp4"),
                 "face": {"every": 1, "xy": [[960, 420]]}, "captions": {"preset": "lecture", "tokens": [], "sentenceStarts": [],
                                                                         "zones": [], "off": True},
                 "layout": spans, "overlays": ovs, "hook": None, "end": None, "grain": 0.04}
        pp = d / "inserts" / f"props-{n:02d}.json"
        pp.write_text(json.dumps(props))
        vid = d / "inserts" / f"insert-{n:02d}.mp4"
        jobs.append((n, pp, vid, a, b, ins.get("kind", ins.get("type", "")), {"plate": plate_key, "props": props, "src": src_rev}))

    def render_insert(job):
        n, pp, vid, a, b, kind, key = job
        if not stale(vid, key=key):
            return (vid, a - p0, b - p0)
        cmd = ["npx", "remotion", "render", "src/index.ts", "Clip", vid, f"--props={pp}", "--muted", "--concurrency=3",
               "--timeout=120000", "--log=error", "--codec=h264", "--crf=14"]
        try:
            run(cmd, cwd=RENDERER)
        except subprocess.CalledProcessError:
            run([c if not str(c).startswith("--concurrency=") else "--concurrency=1" for c in cmd], cwd=RENDERER)
        stamp(vid, key)
        print(f"insert {n}: {kind} {a:.1f}-{b:.1f}s")
        return (vid, a - p0, b - p0)

    t2 = time.time()
    with ThreadPoolExecutor(2) as ex:  # two Remotion renders at once
        overlays = list(ex.map(render_insert, jobs))
    if jobs:
        print(f"inserts: {len(jobs)} in {time.time() - t2:.0f}s")

    # ---- 4. final: picture + inserts + subtitles + sound + chapters
    inputs = ["-i", str(picture)]
    fc = []
    last = "0:v"
    for k, (vid, a, b) in enumerate(overlays, 1):
        inputs += ["-itsoffset", f"{a:.3f}", "-i", str(vid)]
        fc.append(f"[{last}][{k}:v]overlay=enable='between(t,{a:.3f},{b - 1 / FPS:.3f})':eof_action=pass[v{k}]")
        last = f"v{k}"
    fc.append(f"[{last}]ass={ass}:fontsdir={FONTS}[vout]")
    inputs += ["-ss", f"{p0:.3f}", "-t", f"{p1 - p0:.3f}", "-i", str(mixed)]
    ai = len(overlays) + 1
    chapters = []
    for c in plan.get("chapters", []):
        t = tl.ref(c["at"])
        chapters.append((t, c["title"]))
    if chapters and chapters[0][0] > 1.0:
        chapters.insert(0, (0.0, "Cold open"))  # YouTube needs the first chapter at 0:00
    meta = d / ".chapters.ffmeta"
    meta.write_text(";FFMETADATA1\n" + "".join(
        f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int((t - p0) * 1000)}\nEND={int(((chapters[i + 1][0] if i + 1 < len(chapters) else p1) - p0) * 1000)}\ntitle={ttl}\n"
        for i, (t, ttl) in enumerate(chapters) if p0 <= t < p1))
    inputs += ["-i", str(meta)]
    final = out_dir / f"{plan['id']}-{tag}.mp4"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{ai}:a",
         "-map_metadata", str(ai + 1), "-map_chapters", str(ai + 1), "-c:v", "h264_videotoolbox", "-b:v", args.bitrate,
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final])
    yt = "".join((f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}" if t >= 3600 else f"{int(t // 60)}:{int(t % 60):02d}")
                 + f" {ttl}\n" for t, ttl in chapters)
    (out_dir / "chapters.txt").write_text(yt)
    print(f"-> {final} ({(p1 - p0) / 60:.1f} min, total {time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
