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
            if b <= a and W[i]["e"] <= W[i]["s"] and s["a"] <= W[i]["s"] <= s["b"]:
                b = min(a + 0.12, float(tl.off[k] + s["b"] - s["a"]))  # a zero-length word from the aligner is still a word
            if b > a:
                toks.append({"text": text, "start": round(a, 3), "end": round(b, 3), "src": i})
    return toks


_FONT = {}


def plate(text, size=46, margin_v=64, pad_x=26, pad_y=14, radius=12, top=False):
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
    y = margin_v - pad_y + h if top else 1080 - margin_v + pad_y
    return f"{{\\an7\\pos(960,{y:.0f})\\p1}}{path}"


EOS = re.compile(r"[.!?][\"')\]]?$")
CONJ = {"and", "which", "that", "who", "because", "but", "so", "or", "where", "when", "while", "if", "until"}


def cues_from(tokens, max_chars=84, max_line=44, max_dur=6.5, narrow=()):
    """Subtitles by sentence: a sentence that fits is one subtitle; a longer one splits into the
    fewest pieces that fit, at a comma or before a joining word where it can, never leaving fewer
    than three words on either side. `narrow` spans (edit seconds) take one-line subtitles."""
    import math
    tokens = [{**t, "end": min(t["end"], t["start"] + 1.5)} for t in tokens]
    runs, cur = [], []
    for t in tokens:
        if cur and (t["start"] - cur[-1]["end"] > 1.2 or t.get("speaker") != cur[-1].get("speaker")):
            runs.append(cur); cur = []
        cur.append(t)
        if EOS.search(t["text"]):
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)

    def length(ts):
        return len(" ".join(x["text"] for x in ts))

    def split(ts):
        limit = max_line - 8 if any(a <= ts[0]["start"] < b for a, b in narrow) else max_chars  # +8 slack still fits one line
        if (length(ts) <= limit and ts[-1]["end"] - ts[0]["start"] <= max_dur + 1.5) or len(ts) < 6:
            return [ts]
        n = len(ts)
        INF = float("inf")
        dp, back = [0.0] + [INF] * n, [0] * (n + 1)
        for i in range(1, n + 1):
            for j in range(max(0, i - 40), i):
                ch = ts[j:i]
                L = length(ch)
                if (L > limit + 8 or ch[-1]["end"] - ch[0]["start"] > max_dur + 1.5) and i - j > 1:
                    continue
                if (i - j < 3 and i < n) or (n - i < 3 and i < n) or (i - j < 3 and j > 0):
                    continue  # no orphans at either end of a piece
                good = i == n or re.search(r"[,;:]$", ts[i - 1]["text"]) or re.sub(r"\W", "", ts[i]["text"].lower()) in CONJ
                cost = dp[j] + 100 + (0 if good else 45) + abs(L - limit * 0.75) * 0.3
                if cost < dp[i]:
                    dp[i], back[i] = cost, j
        if dp[n] == INF:
            k = math.ceil(length(ts) / limit)
            step = math.ceil(n / k)
            return [ts[q:q + step] for q in range(0, n, step)]
        pieces, i = [], n
        while i > 0:
            pieces.append(ts[back[i]:i]); i = back[i]
        return pieces[::-1]

    cues = []
    for r in runs:
        for piece in split(r):
            # a short sentence ("Okay.", "Good job.") shares a subtitle with what follows when it fits
            if cues and length(cues[-1]) <= 18 and EOS.search(cues[-1][-1]["text"]) and length(cues[-1] + piece) <= max_chars \
                    and piece[0]["start"] - cues[-1][-1]["end"] < 1.0 and piece[0].get("speaker") == cues[-1][-1].get("speaker"):
                cues[-1] = cues[-1] + piece
            else:
                cues.append(piece)
    out = []
    new_sentence = True
    for c in cues:
        words = [x["text"] for x in c]
        text = " ".join(words)
        one_line = any(a <= c[0]["start"] < b for a, b in narrow) and len(text) <= 64
        if len(text) > max_line and len(words) > 1 and not one_line:
            best, bi = 1e9, 1
            for k in range(1, len(words)):
                l1, l2 = " ".join(words[:k]), " ".join(words[k:])
                score = max(len(l1), len(l2)) - (8 if re.search(r"[,;:.?!]$", words[k - 1]) else 0) \
                    - (5 if re.sub(r"\W", "", words[k].lower()) in CONJ else 0) \
                    + (9 if words[k - 1].lower() in {"a", "an", "the", "of", "to", "in", "on", "for", "with", "my", "your", "its",
                                                      "our", "their", "this", "these", "is", "are", "be", "was", "not", "very"} else 0)
                if score < best:
                    best, bi = score, k
            text = " ".join(words[:bi]) + "\\N" + " ".join(words[bi:])
        if new_sentence and text:  # a subtitle that carries on a sentence keeps its lower case
            text = text[0].upper() + text[1:]
        new_sentence = bool(re.search(r"[.!?][\"')\]]?$", text))
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
Style: SubTop,Inter SemiBold,48,&H00F4F1EA,&H000000FF,&H73000000,&H8C000000,0,0,0,0,100,100,-0.3,0,1,2.2,2,8,140,140,30,1
Style: BoxTop,Inter SemiBold,46,&H00F4F1EA,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,-0.3,0,1,0,0,8,140,140,30,1
Style: PlateTop,Inter SemiBold,46,&H4D0B0B0B,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1

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
        # Effects (plan "sfx": [{at: ref, file: kit name or path, gain: dB}]) and a pre-composed
        # bed (plan "bed": {file, at: ref, gainDb}) join the voice before loudness.
        extra_in, extra_fc, labels = [], [], ["[v0]", "[r]"]
        n_in = 2
        for e in plan.get("sfx", []):
            f = Path(str(e["file"])).expanduser()
            if not f.exists():
                f = ROOT / "assets" / "sfx" / f"{e['file']}.wav"
            if not f.exists():
                print(f"  ! missing sfx {e['file']}")
                continue
            ms = int(max(tl.ref(e["at"]), 0) * 1000)
            extra_in += ["-i", str(f)]
            extra_fc.append(f"[{n_in}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={e.get('gain', -20)}dB,adelay={ms}:all=1[x{n_in}]")
            labels.append(f"[x{n_in}]"); n_in += 1
        beds = plan.get("bed") or []
        for bed in (beds if isinstance(beds, list) else [beds]):
            if not bed.get("file"):
                continue
            ms = int(max(tl.ref(bed.get("at", 0)), 0) * 1000)
            extra_in += ["-i", str(Path(bed["file"]).expanduser())]
            extra_fc.append(f"[{n_in}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={bed.get('gainDb', 0)}dB,adelay={ms}:all=1[x{n_in}]")
            labels.append(f"[x{n_in}]"); n_in += 1
        run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", room, *extra_in, "-filter_complex",
             # everything stereo before the mix: amix otherwise folds to the mono voice's layout and a
             # stereo bed (music, widened applause) comes out mono
             ";".join(["[0:a]aformat=channel_layouts=stereo[v0]",
                       f"[1:a]aformat=channel_layouts=stereo,volume='min(1,{gate})':eval=frame[r]"] + extra_fc +
                      [f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[m]"]),
             "-map", "[m]", "-ar", "48000", "-ac", "2", pre])
        # -1.5 dBTP: AAC overshoots a sharp clap by up to about 1 dB, so -1 can come out at 0 dBFS
        pr = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af",
                             "alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        m = json.loads(pr[pr.rindex("{"):pr.rindex("}") + 1])
        run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
             f"alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
             f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
             "-ar", "48000", mixed])
        pre.unlink(missing_ok=True)
        print(f"sound: lavalier + room for {len(turns)} audience turns, {len(labels) - 2} effects/bed, -14 LUFS ({time.time() - t_start:.0f}s)")

    # ---- subtitles
    tokens = edit_tokens(plan, tl, W)
    tok_path = d / "tokens.json"
    if not tok_path.exists():
        frac, med, mx = retime(tokens, voice)
        print(f"captions re-timed on the voice: {frac:.0%} matched, median shift {med * 1000:.0f} ms")
        tok_path.write_text(json.dumps(tokens))
    tokens = json.loads(tok_path.read_text())
    # one-line subtitles at the top zones and where a slide has text both top and bottom ("oneLine")
    narrow = [(tl.ref(a), tl.ref(b)) for a, b in plan.get("captions", {}).get("top", []) + plan.get("captions", {}).get("oneLine", [])]
    cues = cues_from(tokens, narrow=narrow)
    screen_spans = [(s["e0"], s["e1"]) for s in shots if s["cam"] == "screen"]
    # Inserts over a light picture (a title card) ask for the boxed subtitle too.
    screen_spans += [(tl.ref(i["from"]), tl.ref(i["to"])) for i in plan.get("inserts", []) if i.get("captionBox")]
    ins_spans = []
    # A full-frame graphic that already shows the words (a title card) takes the captions off.
    hide_spans = [(tl.ref(i["from"]), tl.ref(i["to"])) for i in plan.get("inserts", []) + plan.get("clips", [])
                  if i.get("captionsOff")]
    # Slides with text along the bottom (a list, a label, a result) take the captions at the top.
    top_spans = [(tl.ref(a), tl.ref(b)) for a, b in plan.get("captions", {}).get("top", [])]
    lines = []
    srt = []
    for n, c in enumerate(cues, 1):
        # a subtitle reaching into a captions-off span (a chapter card) waits for it, or ends before it
        for a_, b_ in hide_spans:
            if c["start"] < b_ and c["end"] > a_ and not (a_ <= (c["start"] + c["end"]) / 2 < b_):
                if c["end"] > b_:
                    c["start"] = b_
                else:
                    c["end"] = a_
        mid = (c["start"] + c["end"]) / 2
        style = "Box" if any(a <= mid < b for a, b in screen_spans) else "Sub"
        if any(a <= mid < b for a, b in top_spans):
            style = "BoxTop" if style == "Box" else "SubTop"
        if c["end"] > p0 and c["start"] < p1 and not any(a <= mid < b for a, b in hide_spans):
            if style in ("Box", "BoxTop"):
                lines.append(f"Dialogue: 0,{ass_ts(c['start'] - p0)},{ass_ts(c['end'] - p0)},{'PlateTop' if style == 'BoxTop' else 'Plate'},,0,0,0,,{plate(c['text'], top=style == 'BoxTop', margin_v=30 if style == 'BoxTop' else 64)}")
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
        cam = cams[s["cam"]]
        src = Path(cam["path"]).stat()   # a rebuilt source (a new screen feed) renders its shots again
        key = hashlib.sha1(json.dumps([s["cam"], s.get("crop"), s["a"], s["angle"], grade.get(s["cam"]),
                                       src.st_size, int(src.st_mtime)]).encode()).hexdigest()[:8]
        out = shot_dir / f"{f0}-{f1}-{key}.mp4"  # named by content: a changed shot list reuses every unchanged shot

        def frames(p):
            return int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                       "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)
        # A cached shot is reused only at its exact length: one frame too many delays every later shot against the sound.
        if out.exists() and args.skip_shots or out.exists() and out.stat().st_size > 1000 and frames(out) == nfr:
            return out
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
        got = frames(out)
        if got < nfr:
            pad = out.with_suffix(".pad.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vf", f"tpad=stop_mode=clone:stop={nfr - got}", "-an",
                 "-c:v", "h264_videotoolbox", "-b:v", "14M", "-profile:v", "high", "-g", "60", "-r", "30", pad])
            pad.replace(out)
        elif got > nfr:
            # The encoder once returned 3 frames over under load (the frames are extra at the end; no B-frames, so a copy cuts clean)
            cut = out.with_suffix(".cut.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-i", out, "-frames:v", str(nfr), "-c", "copy", cut])
            cut.replace(out)
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

    def movie(path):
        # A movie= source is pulled only when the overlay needs it. Opened as an input instead,
        # ffmpeg reads the clip ahead, the queue overflows and the clip's first frames are dropped
        # (a title starting 30 s in lost its first 0.3 s).
        return "movie='" + str(path).replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:") + "'"

    for k, (vid, a, b) in enumerate(overlays, 1):
        fc.append(f"{movie(vid)},setpts=PTS-STARTPTS+{a:.3f}/TB[iv{k}];"
                  f"[{last}][iv{k}]overlay=enable='between(t,{a:.3f},{b - 1 / FPS:.3f})':eof_action=pass[v{k}]")
        last = f"v{k}"
    # Pre-rendered clips (plan "clips": [{src, from, to, captionsOff?}]) go straight over the picture,
    # untouched by Remotion: pixel art stays crisp; a .mov with alpha (png/prores 4444) keys itself.
    k = len(overlays)
    for c in plan.get("clips", []):
        a, b = tl.ref(c["from"]), tl.ref(c["to"])
        if b <= p0 or a >= p1:
            continue
        k += 1
        # a clip that starts before the preview window starts part-way through
        skip = max(0.0, p0 - a)
        trim = f",trim=start={skip:.3f}" if skip else ""
        fc.append(f"{movie(Path(c['src']).expanduser())}{trim},setpts=PTS-STARTPTS+{max(a - p0, 0):.3f}/TB[cm{k}];"
                  f"[{last}][cm{k}]overlay=enable='between(t,{max(a - p0, 0):.3f},{b - p0 - 1 / FPS:.3f})':eof_action=pass[c{k}]")
        last = f"c{k}"
    fc.append(f"[{last}]ass={ass}:fontsdir={FONTS}[vout]")
    inputs += ["-ss", f"{p0:.3f}", "-t", f"{p1 - p0:.3f}", "-i", str(mixed)]
    ai = 1
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
