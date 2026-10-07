#!/usr/bin/env python3
"""Look at every source file once and write DIR/project.json.

  ingest.py SOURCE [SOURCE ...] --project DIR [--slides deck.pdf|dir] [--youtube URL]

For each file: duration, displayed size (after rotation), frame rate (and whether it
is variable), codec, HDR transfer, audio. The primary picture source is the
highest-resolution file (a 4K original beats a 1080p edit for any crop); other files
covering the same event are aligned to it by audio cross-correlation, so a second
camera or a separate audio recorder can be used on the same timeline (offset in
seconds: other_time = primary_time + offset).

--slides converts a PDF deck to PNG pages (or indexes a folder of slide images) into
DIR/slides/ so clips can show the crisp page instead of the filmed projection.
--youtube pulls the "Most replayed" heatmap of an already-published version into
DIR/heatmap.json: real viewer behaviour, the best prior for picking moments.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audiosrc import AudioSrc, snr_db  # noqa: E402

SR = 100  # envelope rate for sync (10 ms frames of speech-band energy)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,"
                          "color_transfer,channels,sample_rate:stream_side_data=rotation", "-of", "json", str(path)],
                         capture_output=True, text=True)
    if out.returncode:
        return {"path": str(path), "error": out.stderr.strip()[:200]}
    d = json.loads(out.stdout)
    info = {"path": str(Path(path).resolve()), "duration": float(d.get("format", {}).get("duration", 0) or 0)}
    for st in d.get("streams", []):
        if st["codec_type"] == "video" and "width" not in info:
            w, h = st["width"], st["height"]
            rot = 0
            for sd in st.get("side_data_list", []) or []:
                rot = int(sd.get("rotation", 0) or 0)
            if abs(rot) % 180 == 90:
                w, h = h, w
            num, den = [int(x) for x in st["avg_frame_rate"].split("/")] if st.get("avg_frame_rate", "0/0") != "0/0" else (0, 1)
            rn, rd = [int(x) for x in st["r_frame_rate"].split("/")]
            avg = num / den if den else 0
            info.update({"width": w, "height": h, "rotation": rot, "codec": st["codec_name"], "fps": round(rn / rd, 3),
                         "vfr": abs(avg - rn / rd) > 0.01, "hdr": st.get("color_transfer") in ("arib-std-b67", "smpte2084")})
        elif st["codec_type"] == "audio":
            info["audioStreams"] = info.get("audioStreams", 0) + 1
            if "audio" not in info:
                info["audio"] = {"codec": st["codec_name"], "channels": st.get("channels"), "rate": st.get("sample_rate")}
    return info


def envelope(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(max(start, 0)), "-t", str(dur), "-i", str(path), "-vn", "-ac", "1",
                          "-af", "highpass=f=200,lowpass=f=4000", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    hop = 16000 // SR
    e = np.sqrt((a[: len(a) // hop * hop].reshape(-1, hop) ** 2).mean(axis=1))
    e = 20 * np.log10(e + 1e-6)
    e = np.diff(e, prepend=e[0])  # onsets correlate across mics better than levels
    return (e - e.mean()) / (e.std() + 1e-9)


def created(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=creation_time,com.apple.quicktime.creationdate",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    tags = json.loads(out).get("format", {}).get("tags", {})
    t = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    if not t:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def is_screen(path, duration):
    """A screen recording is pixel-still between slide changes; a camera never is
    (sensor noise, people). Median frame-to-frame difference over a few 1 s pairs."""
    import cv2

    diffs = []
    for k in range(1, 7):
        t = duration * k / 7
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "2", "-vf", "fps=1,scale=320:-2",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        n = len(raw) // 2
        if n == 0:
            continue
        a = np.frombuffer(raw[:n], np.uint8).astype(float)
        b = np.frombuffer(raw[n:2 * n], np.uint8).astype(float)
        diffs.append(float(np.abs(a - b).mean()))
    return bool(diffs) and float(np.median(diffs)) < 0.6


def face_size(path, duration):
    """Median face width (px) over a few frames: the camera closest to the speaker wins ties."""
    import cv2

    model = Path(__file__).resolve().parent.parent / "models/face_detection_yunet_2023mar.onnx"
    sizes = []
    for k in range(1, 6):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(duration * k / 6), "-i", str(path), "-frames:v", "1",
                              "-vf", "scale=1920:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        det = cv2.FaceDetectorYN.create(str(model), "", (img.shape[1], img.shape[0]), 0.6, 0.3, 50)
        _, f = det.detect(img)
        if f is not None:
            sizes.append(float(max(x[2] for x in f)))
    return float(np.median(sizes)) if sizes else 0.0


def sync(primary, other, probe_at, probe_len=120, search=1200, guess=0.0):
    """Offset (s) so that other_time = primary_time + offset, and a confidence score."""
    ref = envelope(primary, probe_at, probe_len)
    lo = max(probe_at + guess - search, 0)
    tgt = envelope(other, lo, probe_len + 2 * search)
    if len(tgt) <= len(ref):
        return None, 0.0
    n = 1 << int(np.ceil(np.log2(len(tgt) + len(ref))))
    corr = np.fft.irfft(np.fft.rfft(tgt, n) * np.conj(np.fft.rfft(ref, n)), n)[: len(tgt) - len(ref)]
    k = int(np.argmax(corr))
    conf = float(corr[k] / (np.sqrt((ref ** 2).sum() * (tgt[k:k + len(ref)] ** 2).sum()) + 1e-9))
    return round(lo + k / SR - probe_at, 3), round(conf, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--project", required=True)
    ap.add_argument("--slides")
    ap.add_argument("--youtube")
    args = ap.parse_args()
    proj = Path(args.project)
    proj.mkdir(parents=True, exist_ok=True)

    infos = [probe(s) for s in args.sources]
    bad = [i for i in infos if "error" in i]
    for b in bad:
        print(f"! unreadable: {b['path']}: {b['error']}")
    good = [i for i in infos if "error" not in i and "width" in i]
    if not good:
        sys.exit("no readable video")
    # Picture: the highest resolution; among equals, the camera that sees the face largest.
    for i in good:
        i["faceWidth"] = face_size(i["path"], i["duration"])
    top = max(i["width"] * i["height"] for i in good if i["faceWidth"] > 0) if any(i["faceWidth"] > 0 for i in good) else \
        max(i["width"] * i["height"] for i in good)
    best = [i for i in good if i["width"] * i["height"] == top]
    primary = max(best, key=lambda i: (i.get("faceWidth", 0), i["duration"]))
    primary["role"] = "primary"
    t_primary = created(primary["path"])
    for i in infos:
        if "error" in i or i is primary:
            continue
        t_other = created(i["path"])
        guess = (t_primary - t_other) if (t_primary and t_other and abs(t_primary - t_other) < 6 * 3600) else 0.0
        search = 180 if guess else 1500
        off, conf = sync(primary["path"], i["path"], probe_at=min(primary["duration"] / 2, primary["duration"] - 130),
                         search=search, guess=guess)
        i["offset"], i["syncConfidence"] = off, conf
        # Continuity: an edited file (cuts removed material) syncs at a different offset
        # in different places and cannot stand in for a continuous recording.
        if conf > 0.12:
            offs = [off]
            for frac in (0.1, 0.3, 0.7, 0.9):
                o2, c2 = sync(primary["path"], i["path"], probe_at=primary["duration"] * frac, probe_len=60, search=60, guess=off)
                if o2 is not None and c2 > 0.12:
                    offs.append(o2)
            i["offsetSpread"] = round(max(offs) - min(offs), 3)
        if conf <= 0.12:
            i["role"] = "unrelated"
        elif i.get("offsetSpread", 0) > 0.3:
            i["role"] = "edit"
        elif "width" not in i:
            i["role"] = "audio"
        elif is_screen(i["path"], i["duration"]):
            i["role"] = "screen"  # a synced screen share: the slides as shown
        else:
            i["role"] = "camera"

    # Sound: score every audio stream of every synced file; the microphone wins.
    mid = primary["duration"] / 2
    streams = []
    for i in infos:
        if "error" in i or i.get("role") in (None, "unrelated", "edit"):
            continue
        for k in range(i.get("audioStreams", 1)):
            src = AudioSrc({"video": i["path"], "audio": {"path": i["path"], "stream": k, "offset": i.get("offset", 0.0)}})
            try:
                x = src.pcm(mid - 30, 60)
            except subprocess.CalledProcessError:
                continue  # a codec ffmpeg cannot decode (Apple spatial audio)
            if len(x) < 16000 * 20 or float(np.sqrt((x ** 2).mean())) < 1e-4:
                continue  # silent track
            streams.append({"path": i["path"], "stream": k, "offset": i.get("offset", 0.0), "snr": round(snr_db(x), 1)})
    audio = max(streams, key=lambda a: a["snr"]) if streams else {"path": primary["path"], "stream": None, "offset": 0.0, "snr": 0}
    if audio["path"] != primary["path"]:
        # Offset and drift from three points across the recording.
        pts = []
        for frac in (0.2, 0.5, 0.8):
            at = primary["duration"] * frac
            o, c = sync(primary["path"], audio["path"], probe_at=at, probe_len=60, search=3, guess=audio["offset"])
            if o is not None and c > 0.12:
                pts.append((at, o))
        if len(pts) >= 2:
            ts, os_ = np.array(pts).T
            slope, icpt = np.polyfit(ts, os_, 1) if len(pts) > 2 else ((os_[-1] - os_[0]) / (ts[-1] - ts[0]), 0)
            audio["ref"] = round(float(mid), 1)
            audio["drift"] = float(slope)
            audio["offset"] = round(float(np.interp(mid, ts, os_)), 3)
    own = [a for a in streams if a["path"] == primary["path"]]
    project = {"primary": primary["path"], "audio": audio, "sources": infos,
               "screens": [{"path": i["path"], "offset": i["offset"]} for i in infos if i.get("role") == "screen"]}
    if args.slides:
        sd = proj / "slides"
        sd.mkdir(exist_ok=True)
        sp = Path(args.slides)
        if sp.suffix.lower() == ".pdf":
            subprocess.run(["pdftoppm", "-png", "-r", "200", str(sp), str(sd / "slide")], check=True)
            project["slides"] = sorted(str(p) for p in sd.glob("slide*.png"))
        else:
            project["slides"] = sorted(str(p) for p in sp.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if args.youtube:
        meta = json.loads(subprocess.run(["yt-dlp", "--dump-json", "--skip-download", args.youtube],
                                         capture_output=True, text=True, check=True).stdout)
        hm = meta.get("heatmap") or []
        (proj / "heatmap.json").write_text(json.dumps(hm))
        top = sorted(hm, key=lambda x: -x["value"])[:8]
        project["heatmapPeaks"] = [[round(x["start_time"]), round(x["end_time"]), round(x["value"], 2)] for x in top]
    (proj / "project.json").write_text(json.dumps(project, indent=2))

    for i in infos:
        if "error" in i:
            continue
        tag = i.get("role", "?")
        dims = f"{i.get('width', '-')}x{i.get('height', '-')}"
        extra = []
        if i.get("vfr"):
            extra.append("variable frame rate (normalized to 30 fps on decode)")
        if i.get("hdr"):
            extra.append("HDR: colours need tone-mapping")
        if "offset" in i:
            extra.append(f"offset {i['offset']:+.2f}s (confidence {i['syncConfidence']})")
        if i.get("role") == "edit":
            extra.append(f"an edit (offset moves {i['offsetSpread']:.1f}s across the file): use the originals")
        print(f"{tag:9s} {dims:>10s} {i['duration'] / 60:6.1f} min  {Path(i['path']).name}  {'; '.join(extra)}")
    print(f"\npicture: {Path(primary['path']).name} ({primary['width']}x{primary['height']}, face {primary.get('faceWidth', 0):.0f} px)")
    print(f"audio:   {Path(audio['path']).name}" + (f" stream {audio['stream']}" if audio.get("stream") is not None else "")
          + f" ({audio['snr']} dB SNR" + (f"; the picture's own audio {max(a['snr'] for a in own)} dB" if own and audio['path'] != primary['path'] else "")
          + (f"; offset {audio['offset']:+.3f}s, drift {audio.get('drift', 0) * 3600 * 1000:+.0f} ms/h" if audio["path"] != primary["path"] else "") + ")")
    for sc in project["screens"]:
        print(f"screen:  {Path(sc['path']).name} (offset {sc['offset']:+.2f}s): slides as shown, usable for stage panels")
    print("use in plans: \"source\": {\"video\": <picture>, \"audio\": <project.json audio>}; transcribe from the audio "
          "(--stream, --offset)")
    if primary["height"] < 1440 and primary["width"] <= 1920:
        print("\nnote: the best picture source is 1080p or less; 9:16 medium shots will be upscaled 2.5x or more. "
              "If a 4K original exists, pass it too.")
    if project.get("heatmapPeaks"):
        print("most replayed (s):", project["heatmapPeaks"])
    print(f"-> {proj / 'project.json'}")


if __name__ == "__main__":
    main()
