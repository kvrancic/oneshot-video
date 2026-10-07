#!/usr/bin/env python3
"""Find and follow the subject (a face) through a time window of a video.

Decodes the window with ffmpeg (VideoToolbox), samples it at --fps, detects faces
with YuNet, links detections into tracks and picks the subject track: the face that
is present most of the time and actually moves (a face printed on a slide is
perfectly still, a speaker never is). Writes positions in SOURCE pixel
coordinates so the reframer can crop from the full-resolution original.

  track.py SOURCE --from 2200 --to 2330 --out work/talk/clips/01/track.json
           [--fps 8] [--width 1920] [--hint 1250,620] [--scenes]

--hint x,y (source pixels) picks the track nearest that point instead (useful for
podcasts: one run per person). --scenes also records hard cuts (edited sources).
"""
import argparse, json, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
YUNET = ROOT / "models/face_detection_yunet_2023mar.onnx"


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation", "-of", "json", src],
                         capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    return w, h


def frames(src, a, b, fps, width, height):
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-ss", str(a), "-t", str(b - a), "-i", src,
           "-vf", f"fps={fps},scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = width * height * 3
    i = 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield a + i / fps, np.frombuffer(buf, np.uint8).reshape(height, width, 3)
        i += 1
    p.wait()


def link(dets, max_jump):
    """Greedy nearest-neighbour linking of per-frame detections into tracks."""
    tracks = []  # each: list of (frame_idx, det)
    open_ = []
    for fi, ds in enumerate(dets):
        used = set()
        still_open = []
        for tr in open_:
            last_fi, last = tr[-1]
            if fi - last_fi > 12:  # lost for too long
                continue
            best, bd = None, 1e9
            for di, d in enumerate(ds):
                if di in used:
                    continue
                dist = np.hypot(d["cx"] - last["cx"], d["cy"] - last["cy"])
                size_ratio = d["w"] / max(last["w"], 1)
                if dist < max_jump * (fi - last_fi) ** 0.5 and 0.6 < size_ratio < 1.6 and dist < bd:
                    best, bd = di, dist
            if best is not None:
                tr.append((fi, ds[best]))
                used.add(best)
            still_open.append(tr)
        for di, d in enumerate(ds):
            if di not in used:
                tr = [(fi, d)]
                tracks.append(tr)
                still_open.append(tr)
        open_ = still_open
    return tracks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--from", dest="a", type=float, required=True)
    ap.add_argument("--to", dest="b", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=8)
    ap.add_argument("--width", type=int, default=1920, help="analysis width")
    ap.add_argument("--hint", help="x,y in source pixels: follow the face nearest this point")
    ap.add_argument("--scenes", action="store_true", help="also detect hard cuts")
    ap.add_argument("--min-score", type=float, default=0.6)
    args = ap.parse_args()

    sw, sh = probe(args.source)
    aw = min(args.width, sw)
    ah = int(round(sh * aw / sw / 2) * 2)
    k = sw / aw  # analysis -> source scale
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (aw, ah), args.min_score, 0.3, 50)

    times, dets, cuts = [], [], []
    prev_hist = None
    for t, img in frames(args.source, args.a, args.b, args.fps, aw, ah):
        _, faces = det.detect(img)
        ds = []
        for f in (faces if faces is not None else []):
            x, y, w, h = [float(v) for v in f[:4]]
            lm = [float(v) * k for v in f[4:14]]
            ds.append({"x": x * k, "y": y * k, "w": w * k, "h": h * k, "cx": (x + w / 2) * k, "cy": (y + h / 2) * k,
                       "score": float(f[14]), "eyes": lm[0:4]})
        times.append(round(t, 3))
        dets.append(ds)
        if args.scenes:
            small = cv2.resize(img, (160, 90))
            hist = cv2.calcHist([cv2.cvtColor(small, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            if prev_hist is not None and cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) > 0.45:
                cuts.append(round(t, 3))
            prev_hist = hist
    n = len(times)
    if n == 0:
        sys.exit("no frames decoded")

    tracks = link(dets, max_jump=0.08 * sw / args.fps ** 0.5)

    def track_score(tr):
        c = np.array([[d["cx"], d["cy"]] for _, d in tr])
        motion = float(np.median(np.abs(np.diff(c, axis=0)).sum(axis=1))) if len(c) > 2 else 0.0
        size = float(np.median([d["w"] for _, d in tr]))
        live = min(motion / (0.0015 * sw), 1.0)  # printed faces barely move between samples
        return len(tr) / n * (0.25 + 0.75 * live) * (size / sw) ** 0.25, motion

    if args.hint:
        hx, hy = [float(v) for v in args.hint.split(",")]
        subject = min(tracks, key=lambda tr: min(np.hypot(d["cx"] - hx, d["cy"] - hy) for _, d in tr) - len(tr))
    else:
        subject = max(tracks, key=lambda tr: track_score(tr)[0])

    # Fill gaps: other tracks that continue the subject after it was lost (turned away, occluded).
    chosen = {fi: d for fi, d in subject}
    for tr in sorted(tracks, key=len, reverse=True):
        if tr is subject or len(tr) < 3 or track_score(tr)[1] < 0.0008 * sw:
            continue
        overlap = sum(1 for fi, _ in tr if fi in chosen)
        if overlap > 0.1 * len(tr):
            continue
        fi0, d0 = tr[0]
        before = [f for f in chosen if f < fi0]
        if before:
            last = chosen[max(before)]
            if np.hypot(d0["cx"] - last["cx"], d0["cy"] - last["cy"]) > 0.35 * sw:
                continue
        for fi, d in tr:
            chosen.setdefault(fi, d)

    path = []
    for fi in range(n):
        d = chosen.get(fi)
        path.append(None if d is None else {k2: round(v, 1) for k2, v in d.items() if k2 != "eyes"} | {
            "eyes": [round(v, 1) for v in d["eyes"]]})
    coverage = sum(p is not None for p in path) / n

    out = {"source": str(Path(args.source).resolve()), "width": sw, "height": sh, "from": args.a, "to": args.b,
           "fps": args.fps, "times": times, "subject": path, "coverage": round(coverage, 3), "cuts": cuts,
           "others": [[{k2: round(v, 1) for k2, v in d.items() if k2 in ("cx", "cy", "w")} for d in ds] for ds in dets]}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out))
    ws = [p["w"] for p in path if p]
    print(f"{n} samples, subject coverage {coverage:.0%}, median face {np.median(ws) if ws else 0:.0f}px "
          f"in {sw}x{sh}, {len(tracks)} tracks, {len(cuts)} cuts -> {args.out}")


if __name__ == "__main__":
    main()
