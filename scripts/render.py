#!/usr/bin/env python3
"""Plan -> Remotion props -> rendered, mixed, loudness-normalized clip.

  render.py clip/plan.json [--formats 9x16,16x9] [--stills 12.5,40] [--skip-plate] [--skip-voice] [--draft]

Steps (each skipped when its output is newer than the plan, unless forced):
  1. voice.wav from the segments (audio.py)
  2. plate-<fmt>.mp4 per format (reframe.py; needs track.json, made by track.py)
  3. caption tokens in edit time: fixes, cuts, emphasis, then re-timed against a
     fresh Parakeet pass over voice.wav, so captions sync with the audio that ships
  4. props-<fmt>.json with every time resolved to edit seconds, assets staged
  5. Remotion render (muted, hardware H.264), then the sound mix in ffmpeg:
     voice + sfx + music (ducked under speech), limiter, two-pass loudnorm to -14 LUFS

Time references in a plan (overlays, layout spans, sfx, zooms) may be:
  "#5096"      start of word 5096        "#5096.e"  end of word 5096
  "#5096+0.3"  with an offset (s)         12.5       edit seconds
  "#5096@2"    the second time that word plays (a cold open repeats material); "@last"
  "end", "end-2.5"                        the clip end, minus seconds
"""
import argparse, difflib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "renderer"
SCRIPTS = ROOT / "scripts"
PY = sys.executable
FPS = 30
SFX_DIR = ROOT / "assets" / "sfx"


def find_path(p, *bases):
    """A plan path may be absolute, or relative to the plan's folder, the working directory or the repo."""
    p = Path(p).expanduser()
    if p.is_absolute():
        return p
    for b in [*bases, Path.cwd(), ROOT]:
        if (Path(b) / p).exists():
            return Path(b) / p
    return p


class Timeline:
    def __init__(self, segs, words):
        self.segs = segs
        self.W = words
        self.off = np.concatenate([[0], np.cumsum([s["b"] - s["a"] for s in segs])])
        self.duration = float(self.off[-1])

    def edit(self, t, snap="next", occ=1):
        """Source seconds -> edit seconds (None when the moment was cut). A source moment
        used twice (a cold open repeats the payoff) is picked with occ (1, 2, ... or -1 = last)."""
        hits = [k for k, s in enumerate(self.segs) if s["a"] - 1e-3 <= t <= s["b"] + 1e-3]
        if hits:
            k = hits[occ - 1 if occ > 0 else occ] if abs(occ) <= len(hits) else hits[-1]
            s = self.segs[k]
            return float(self.off[k] + min(max(t - s["a"], 0), s["b"] - s["a"]))
        if snap == "next":
            for k, s in enumerate(self.segs):
                if s["a"] > t:
                    return float(self.off[k])
        return None

    def ref(self, r):
        if r is None:
            return None
        if isinstance(r, (int, float)):
            return float(r)
        r = str(r).strip()
        m = re.match(r"^end([+-][\d.]+)?$", r)
        if m:
            return self.duration + float(m.group(1) or 0)
        m = re.match(r"^#(\d+)(\.e)?(@(?:-?\d+|last))?([+-][\d.]+)?$", r)
        if m:
            w = self.W[int(m.group(1))]
            t = w["e"] if m.group(2) else w["s"]
            occ = m.group(3)
            occ = 1 if not occ else (-1 if occ == "@last" else int(occ[1:]))
            e = self.edit(t, occ=occ)
            if e is None:
                raise ValueError(f"time ref {r} points at material that was cut")
            return e + float(m.group(4) or 0)
        return float(r)


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "")
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def stale(out, *deps, key=None):
    """True when `out` must be rebuilt: missing, older than a file dependency, or built from
    different plan content (`key`: the plan fields it depends on; editing post copy or
    captions never re-renders a camera plate)."""
    out = Path(out)
    if not out.exists():
        return True
    if key is not None:
        import hashlib
        h = hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()
        stamp = out.with_name(out.name + ".key")
        if not stamp.exists() or stamp.read_text() != h:
            return True
        deps = [d for d in deps if not str(d).endswith("plan.json")]
    return any(Path(d).exists() and Path(d).stat().st_mtime > out.stat().st_mtime for d in deps)


def stamp(out, key):
    import hashlib
    Path(out).with_name(Path(out).name + ".key").write_text(hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest())


# ---------------------------------------------------------------- captions

def build_tokens(plan, tl):
    W = tl.W
    cap = plan.get("captions", {})
    fixes = {int(k): v for k, v in cap.get("fixes", {}).items()}
    drop = set(cap.get("drop", [])) | set(plan.get("cut", []))
    emph = {int(k): v for k, v in cap.get("emph", {}).items()}
    breaks = set(cap.get("breaks", []))
    speakers = {int(k): v for k, v in cap.get("speakers", {}).items()}
    fillers = {"um", "uh", "uhm", "erm", "er", "ah", "hmm", "mm"}
    toks = []
    cur_speaker = None
    for k, s in enumerate(tl.segs):
        i0, i1 = s["w"]
        for i in range(i0, i1 + 1):
            if i in speakers:
                cur_speaker = speakers[i]
            if i in drop:
                continue
            text = fixes.get(i, W[i]["w"])
            if not text or re.sub(r"[^\w]", "", text).lower() in fillers:
                continue
            # Map through this segment's own offset: a cold open plays some words twice.
            a = float(tl.off[k] + max(W[i]["s"], s["a"]) - s["a"])
            b = float(tl.off[k] + min(W[i]["e"], s["b"]) - s["a"])
            if b <= a:
                continue
            t = {"text": text, "start": round(a, 3), "end": round(max(b, a + 0.06), 3), "src": i}
            if i in emph:
                t["emph"] = emph[i]
            if i in breaks:
                t["breakAfter"] = True
            if cur_speaker:
                t["speaker"] = cur_speaker
            toks.append(t)
    return toks


def retime(tokens, voice_wav):
    """Align caption tokens to a fresh Parakeet pass over the finished voice track."""
    sys.path.insert(0, str(SCRIPTS))
    from transcribe import _parakeet, _pk_words, norm  # noqa
    import soundfile as sf

    audio, sr = sf.read(voice_wav, dtype="float32")
    if sr != 16000:
        tmp = str(voice_wav) + ".16k.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", voice_wav, "-ac", "1", "-ar", "16000", tmp])
        voice_wav = tmp
        audio, sr = sf.read(voice_wav, dtype="float32")
    rec = _parakeet(vad=False)
    pk = []
    step = 45 * sr
    ov = 3 * sr
    tmpw = str(voice_wav) + ".win.wav"
    for i in range(0, len(audio), step):
        lo = max(i - ov, 0)
        sf.write(tmpw, audio[lo:i + step], sr)
        ws = _pk_words(rec.recognize(tmpw), lo / sr)
        pk.extend(w for w in ws if w["s"] >= i / sr - 1e-6 or i == 0)
    a = [norm(t["text"]) for t in tokens]
    b = [norm(w["w"]) for w in pk]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    new = [None] * len(tokens)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                new[i1 + d] = (pk[j1 + d]["s"], pk[j1 + d]["e"])
    # A match far from where the token already sits is a repeat (a cold open and its
    # payoff share words), not a correction.
    for k, v in enumerate(new):
        if v and abs(v[0] - tokens[k]["start"]) > 1.5:
            new[k] = None
    matched = [k for k, v in enumerate(new) if v]
    deltas = [abs(new[k][0] - tokens[k]["start"]) for k in matched]
    # Unmatched tokens move with the offset of their nearest matched neighbours.
    for k in range(len(tokens)):
        if new[k]:
            continue
        prev = next((m for m in range(k - 1, -1, -1) if new[m]), None)
        nxt = next((m for m in range(k + 1, len(tokens)) if new[m]), None)
        offs = [new[m][0] - tokens[m]["start"] for m in (prev, nxt) if m is not None]
        d = float(np.mean(offs)) if offs else 0.0
        new[k] = (tokens[k]["start"] + d, tokens[k]["end"] + d)
    for k, t in enumerate(tokens):
        t["start"], t["end"] = round(new[k][0], 3), round(max(new[k][1], new[k][0] + 0.06), 3)
    for k in range(len(tokens) - 1):
        if tokens[k]["end"] > tokens[k + 1]["start"]:
            tokens[k]["end"] = tokens[k + 1]["start"]
        if tokens[k + 1]["start"] < tokens[k]["start"]:
            tokens[k + 1]["start"] = tokens[k]["start"]
    return len(matched) / max(len(tokens), 1), (float(np.median(deltas)) if deltas else 0.0), (float(np.max(deltas)) if deltas else 0.0)


# ---------------------------------------------------------------- props

def stage(path, job_dir, name=None):
    """Hard-link (or copy) an asset into renderer/public/jobs/<id>/ and return its public path."""
    src = Path(path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    dst = job_dir / (name or src.name)
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime or dst.stat().st_size != src.stat().st_size:
        if dst.exists():
            dst.unlink()
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    return str(dst.relative_to(RENDERER / "public"))


def resolve_obj(o, tl, clip_dir, job_dir):
    """Resolve time refs (keys from/to/at/until) and asset paths (keys src/image/photo) recursively."""
    if isinstance(o, list):
        return [resolve_obj(x, tl, clip_dir, job_dir) for x in o]
    if not isinstance(o, dict):
        return o
    out = {}
    for k, v in o.items():
        if k in ("from", "to", "at", "until", "land", "subAt", "idsAt", "pickAt") and isinstance(v, list):
            out[k] = [round(tl.ref(x), 3) for x in v]
        elif k in ("from", "to", "at", "until", "land", "subAt", "idsAt", "pickAt") and (isinstance(v, (int, float)) or (isinstance(v, str) and (v.startswith("#") or v.startswith("end") or re.match(r"^[\d.]+$", v)))):
            out[k] = round(tl.ref(v), 3)
        elif k in ("src", "image", "photo") and isinstance(v, str) and not v.startswith("http"):
            out[k] = stage(find_path(v, clip_dir, clip_dir.parent.parent), job_dir)
        else:
            out[k] = resolve_obj(v, tl, clip_dir, job_dir)
    return out


def face_track(camera_json, step=3):
    cam = json.loads(Path(camera_json).read_text())
    return {"every": step, "xy": cam["face"][::step]}


# ---------------------------------------------------------------- audio mix

def mix_audio(plan, tl, voice, sfx_events, out_wav, clip_dir):
    dur = tl.duration + 0.05
    inputs = ["-i", str(voice)]
    filters = []
    labels = ["[0:a]"]
    n = 1
    for ev in sfx_events:
        f = Path(ev["file"])
        if not f.exists():
            f = SFX_DIR / f"{ev['file']}.wav"
        if not f.exists():
            print(f"  ! missing sfx {ev['file']}")
            continue
        inputs += ["-i", str(f)]
        ms = int(max(ev["at"], 0) * 1000)
        filters.append(f"[{n}:a]aformat=channel_layouts=mono,volume={ev.get('gain', -20)}dB,adelay={ms}:all=1[s{n}]")
        labels.append(f"[s{n}]")
        n += 1
    music = plan.get("music")
    if music and music.get("file"):
        mf = Path(music["file"]).expanduser()
        if not mf.is_absolute():
            mf = clip_dir / mf
        inputs += ["-stream_loop", "-1", "-i", str(mf)]
        gain = music.get("gainDb", -22)
        # Duck under speech from the transcript: -duck dB while words play, eased.
        segs = []
        for t in json.loads((clip_dir / "tokens.json").read_text()):
            if segs and t["start"] - segs[-1][1] < 0.6:
                segs[-1][1] = t["end"]
            else:
                segs.append([t["start"], t["end"]])
        duck = music.get("duckDb", 8)
        expr = "+".join(f"between(t,{a - 0.15:.2f},{b + 0.4:.2f})" for a, b in segs) or "0"
        fade_out = max(dur - 2.0, 0)
        filters.append(f"[{n}:a]aformat=channel_layouts=mono,atrim=0:{dur:.2f},volume={gain}dB,"
                       f"volume='if(gt({expr},0),{10 ** (-duck / 20):.4f},1)':eval=frame,"
                       f"afade=t=in:d=1.2,afade=t=out:st={fade_out:.2f}:d=2[m]")
        labels.append("[m]")
        n += 1
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[mx]")
    # Limiter first, then two-pass loudnorm in linear mode to -14 LUFS / -1 dBTP.
    pre = Path(str(out_wav) + ".pre.wav")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[mx]",
         "-ar", "48000", "-ac", "2", str(pre)])
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af",
                            "alimiter=limit=0.89:level=false,loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    ln = (f"alimiter=limit=0.89:level=false,loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
    res = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(pre), "-af", ln, "-ar", "48000", str(out_wav)],
                         capture_output=True, text=True).stderr
    r = json.loads(res[res.rindex("{"):res.rindex("}") + 1])
    print(f"  mix: {len(sfx_events)} sfx, music={'yes' if music and music.get('file') else 'no'}, "
          f"loudnorm {r.get('normalization_type')} -> {r.get('output_i')} LUFS, TP {r.get('output_tp')}")
    pre.unlink(missing_ok=True)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--formats")
    ap.add_argument("--stills", help="comma-separated edit seconds: render stills instead of video")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--draft", action="store_true", help="half-resolution fast render")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--no-retime", action="store_true")
    ap.add_argument("--audio-only", action="store_true",
                    help="rebuild voice and mix and remux them onto the existing renders (sound changes only)")
    args = ap.parse_args()

    plan_path = Path(args.plan).resolve()
    clip_dir = plan_path.parent
    plan = json.loads(plan_path.read_text())
    if "segments" not in plan:
        sys.exit("run edl.py first (plan has no resolved segments)")
    W = json.loads(find_path(plan["source"]["words"], clip_dir, clip_dir.parent.parent).read_text())["words"]
    tl = Timeline(plan["segments"], W)
    formats = (args.formats or ",".join(plan.get("formats", ["9x16"]))).split(",")
    print(f"{plan['id']}: {tl.duration:.1f}s, {len(plan['segments'])} segments, formats {formats}")

    # 1. voice
    voice = clip_dir / "voice.wav"
    voice_key = [plan["segments"], plan.get("audio"), plan["source"]]
    if args.force or stale(voice, key=voice_key):
        run([PY, SCRIPTS / "audio.py", "--plan", plan_path, "--out", voice, "--clean", (plan.get("audio") or {}).get("clean", "auto")])
        stamp(voice, voice_key)

    if args.audio_only:
        # Captions are burned into the picture; check they still sit on the new voice.
        probe = json.loads((clip_dir / "tokens.json").read_text())
        frac, med, mx = retime(probe, voice)
        print(f"  captions vs the new voice: {frac:.0%} matched, median shift {med * 1000:.0f} ms, max {mx * 1000:.0f} ms"
              + ("  (over 80 ms: re-render the picture too)" if med > 0.08 else ""))
        tl_sfx = [resolve_obj(s, tl, clip_dir, RENDERER / "public" / "jobs" / plan["id"]) for s in plan.get("sfx", [])]
        mixed = clip_dir / "mix.wav"
        mix_audio(plan, tl, voice, tl_sfx, mixed, clip_dir)
        for fmt in formats:
            final = clip_dir / "renders" / f"{plan['id']}-{fmt}.mp4"
            if not final.exists():
                print(f"  ! no render for {fmt}; run without --audio-only")
                continue
            tmp = final.with_name(final.stem + ".remux.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-i", final, "-i", mixed, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", tmp])
            tmp.replace(final)
            print(f"  -> {final} (new sound)")
        return

    # 2. tracking + plates
    track = clip_dir / "track.json"
    lo = min(s["a"] for s in plan["segments"]) - 0.5
    hi = max(s["b"] for s in plan["segments"]) + 0.5
    if not track.exists():
        hint = plan.get("camera", {}).get("hint")
        run([PY, SCRIPTS / "track.py", plan["source"]["video"], "--from", f"{lo:.2f}", "--to", f"{hi:.2f}",
             "--out", track, "--fps", "6"] + (["--hint", hint] if hint else []))
    # Zoom events may use word refs; resolve them on the edit timeline (a cold open can
    # repeat source material, so source seconds would be ambiguous).
    cam = json.loads(json.dumps(plan.get("camera", {})))
    for z in cam.get("zooms", []):
        z["te"] = tl.ref(z.pop("t"))
        if z.get("until") is not None:
            z["untile"] = tl.ref(z.pop("until"))
    resolved_plan = clip_dir / ".plan.resolved.json"
    resolved_plan.write_text(json.dumps({**plan, "camera": cam}))
    for fmt in formats:
        plate = clip_dir / f"plate-{fmt}.mp4"
        lay_cam = {k: v for k, v in plan.get("layout", {}).get(fmt, {}).items() if k != "spans"}
        plate_key = [plan["segments"], cam, plan["source"], lay_cam]
        if args.force or stale(plate, track, key=plate_key):
            run([PY, SCRIPTS / "reframe.py", "--plan", resolved_plan, "--format", fmt, "--track", track, "--out", plate])
            stamp(plate, plate_key)
        # Horizontal stage layouts get a second camera: a speaker-only shot for the right third.
        spans = plan.get("layout", {}).get(fmt, {}).get("spans", [])
        if fmt == "16x9" and any(sp.get("mode") == "stage" for sp in spans):
            sp_plate = clip_dir / f"plate-{fmt}-stage.mp4"
            if args.force or stale(sp_plate, track, key=plate_key):
                run([PY, SCRIPTS / "reframe.py", "--plan", resolved_plan, "--format", fmt, "--track", track, "--out", sp_plate,
                     "--size", "820x1080", "--mode", "follow", "--face-frac", "0.2"])
                stamp(sp_plate, plate_key)

    # 3. captions
    tokens_path = clip_dir / "tokens.json"
    tokens = build_tokens(plan, tl)
    if not args.no_retime:
        t0 = time.time()
        frac, med, mx = retime(tokens, voice)
        print(f"  captions re-timed on the voice track: {frac:.0%} matched, median shift {med * 1000:.0f} ms, "
              f"max {mx * 1000:.0f} ms ({time.time() - t0:.0f}s)")
    tokens_path.write_text(json.dumps(tokens, ensure_ascii=False))
    starts = [i for i, t in enumerate(tokens) if i == 0 or re.search(r"[.!?][\"')\]]?$", tokens[i - 1]["text"])]

    # 4. props per format
    job_dir = RENDERER / "public" / "jobs" / plan["id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    out_dir = clip_dir / "renders"
    out_dir.mkdir(exist_ok=True)
    sfx_events = [resolve_obj(s, tl, clip_dir, job_dir) for s in plan.get("sfx", [])]
    for ev in sfx_events:
        ev["at"] = ev["at"]
    for fmt in formats:
        fplan = {**plan, **plan.get("overrides", {}).get(fmt, {})}
        props = {
            "id": plan["id"],
            "format": fmt,
            "fps": FPS,
            "durationInFrames": int(round(tl.duration * FPS)),
            "palette": fplan.get("palette", "paper"),
            "plate": stage(clip_dir / f"plate-{fmt}.mp4", job_dir, f"plate-{fmt}.mp4"),
            "face": face_track(clip_dir / f"plate-{fmt}.camera.json"),
            "stagePlate": stage(clip_dir / f"plate-{fmt}-stage.mp4", job_dir, f"plate-{fmt}-stage.mp4")
            if (clip_dir / f"plate-{fmt}-stage.mp4").exists() else None,
            "captions": {
                "preset": fplan.get("captions", {}).get("preset", "lecture"),
                "tokens": tokens,
                "sentenceStarts": starts,
                "zones": resolve_obj(fplan.get("captions", {}).get("zones", {}).get(fmt, []), tl, clip_dir, job_dir),
                "off": fplan.get("captions", {}).get("off", False),
            },
            "layout": resolve_obj(fplan.get("layout", {}).get(fmt, {}).get("spans", []), tl, clip_dir, job_dir),
            "overlays": resolve_obj([o for o in fplan.get("overlays", []) if fmt in o.get("formats", [fmt])], tl, clip_dir, job_dir),
            "hook": resolve_obj(fplan.get("hook"), tl, clip_dir, job_dir),
            "end": resolve_obj(fplan.get("end"), tl, clip_dir, job_dir),
            "progress": fplan.get("progress", False),
            "grain": fplan.get("grain", 0.06),
            "cutFlash": [round(float(x), 3) for x in tl.off[1:-1]],
        }
        # Text behind the speaker: an alpha cut-out of the speaker for just that span.
        for k, o in enumerate(props["overlays"]):
            if o["type"] != "TextBehind":
                continue
            fg = clip_dir / f"fg-{fmt}-{k}.webm"
            plate = clip_dir / f"plate-{fmt}.mp4"
            fg_key = [o["from"], o["to"], plan["segments"], cam]
            if args.force or stale(fg, plate, key=fg_key):
                w, h = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}[fmt]
                a, d = o["from"], o["to"] - o["from"]
                matte = subprocess.Popen([str(ROOT / "bin" / "matte"), str(plate), f"{a:.3f}", f"{d:.3f}", str(w), str(h)],
                                         stdout=subprocess.PIPE)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(FPS),
                                "-i", "-", "-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", str(plate), "-filter_complex",
                                "[1:v][0:v]alphamerge,format=yuva420p", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "8M",
                                "-deadline", "good", "-cpu-used", "4", "-an", str(fg)], stdin=matte.stdout, check=True)
                matte.wait()
                stamp(fg, fg_key)
            o.setdefault("props", {})["fg"] = stage(fg, job_dir, fg.name)
        props_path = clip_dir / f"props-{fmt}.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False))

        if args.stills:
            for s in args.stills.split(","):
                fr = int(round(float(s) * FPS))
                run(["npx", "remotion", "still", "src/index.ts", "Clip", out_dir / f"still-{fmt}-{s}.png",
                     f"--frame={fr}", f"--props={props_path}", "--log=error"], cwd=RENDERER)
            continue

        video = out_dir / f".{plan['id']}-{fmt}.video.mp4"
        cmd = ["npx", "remotion", "render", "src/index.ts", "Clip", video, f"--props={props_path}", "--muted",
               f"--concurrency={args.concurrency}", "--hardware-acceleration=if-possible", f"--video-bitrate={'8M' if fmt in ('9x16', '4x5', '1x1') else '10M'}",
               "--log=error"]
        if args.draft:
            cmd += ["--scale=0.5"]
        cmd += ["--timeout=120000"]
        t0 = time.time()
        try:
            run(cmd, cwd=RENDERER)
        except subprocess.CalledProcessError:
            # Headless Chrome can time out or drop a page on a loaded machine; retry once gentler.
            half = max(1, args.concurrency // 2)
            print(f"  render failed; retrying {fmt} at concurrency {half}")
            run([f"--concurrency={half}" if str(c).startswith("--concurrency=") else c for c in cmd], cwd=RENDERER)
        print(f"  rendered {fmt} in {time.time() - t0:.0f}s")

    if args.stills:
        return
    # 5. sound mix once, muxed into every format
    mixed = clip_dir / "mix.wav"
    mix_audio(plan, tl, voice, sfx_events, mixed, clip_dir)
    for fmt in formats:
        video = out_dir / f".{plan['id']}-{fmt}.video.mp4"
        final = out_dir / f"{plan['id']}-{fmt}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mixed, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final])
        video.unlink(missing_ok=True)
        print(f"  -> {final}")


if __name__ == "__main__":
    main()
