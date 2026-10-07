#!/usr/bin/env python3
"""Virtual camera operator: plan a crop path through the source and render a plate.

The operator behaves like a person on a tripod, not like a stabiliser: it holds a
locked-off shot while the subject stays inside a dead zone, and when the subject
leaves it, it eases to a new framing that starts before they reach the edge (it
knows the future). A subject who keeps walking gets a smooth follow instead of a
string of lurches. Every edit cut restarts the shot, and cut zooms alternate
(1.00 / 1.12 by default) so jump cuts read as a second camera. Punch-ins and slow
pushes come from the plan, keep the face where it is, and are cropped from the
source pixels, so a zoom on a 4K original stays sharp.

  reframe.py --plan clip/plan.json --format 9x16 --track clip/track.json --out clip/plate-9x16.mp4
  reframe.py ... --dry   (writes camera.json and a preview strip, no render)

Plan fields used: segments[{a,b}], camera{style, faceFrac, eyeLine, cutZoom, zooms[{t,z,kind,dur}]},
layout{<format>: {mode: follow|static|full, rect:[x,y,w,h]}}.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track import probe  # noqa: E402

SIZES = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}


def ease_io(u):
    u = np.clip(u, 0, 1)
    return np.where(u < 0.5, 4 * u ** 3, 1 - (-2 * u + 2) ** 3 / 2)


def subject_series(track, t):
    """Face centre x, eye-line y and face width at times t (seconds), gaps interpolated."""
    tt = np.array(track["times"])
    rows = [(i, s) for i, s in enumerate(track["subject"]) if s]
    if not rows:
        return None
    idx = np.array([i for i, _ in rows])
    cx = np.array([s["cx"] for _, s in rows])
    ey = np.array([(s["eyes"][1] + s["eyes"][3]) / 2 if s.get("eyes") else s["y"] + 0.4 * s["h"] for _, s in rows])
    fw = np.array([s["w"] for _, s in rows])
    # Median filter against detector jitter and one-frame misses.
    k = 5
    if len(cx) >= k:
        pad = k // 2
        cx = np.array([np.median(cx[max(0, i - pad):i + pad + 1]) for i in range(len(cx))])
        ey = np.array([np.median(ey[max(0, i - pad):i + pad + 1]) for i in range(len(ey))])
    tsub = tt[idx]
    return (np.interp(t, tsub, cx), np.interp(t, tsub, ey), np.interp(t, tsub, fw))


def plan_axis(target, fps, half_band, min_hold=1.2, max_speed=None):
    """Greedy holds: the longest runs the camera can stay still for, eased between.
    Runs shorter than min_hold (a walking subject) become a smoothed follow."""
    n = len(target)
    holds = []
    i = 0
    while i < n:
        lo = hi = target[i]
        j = i
        while j + 1 < n:
            lo2, hi2 = min(lo, target[j + 1]), max(hi, target[j + 1])
            if hi2 - lo2 > 2 * half_band:
                break
            lo, hi, j = lo2, hi2, j + 1
        holds.append([i, j, (lo + hi) / 2])
        i = j + 1
    path = np.empty(n)
    for a, b, c in holds:
        path[a:b + 1] = c
    # Follow sections: runs of short holds become a zero-phase smoothed follow.
    short = [h for h in holds if (h[1] - h[0] + 1) / fps < min_hold]
    if short:
        sigma = 0.45 * fps
        ker = np.exp(-0.5 * (np.arange(-3 * sigma, 3 * sigma + 1) / sigma) ** 2)
        ker /= ker.sum()
        smooth = np.convolve(np.pad(target, len(ker) // 2, mode="edge"), ker, mode="valid")[:n]
        for a, b, _ in short:
            path[a:b + 1] = smooth[a:b + 1]
    # Ease between consecutive holds, finishing when the new hold starts (anticipation).
    out = path.copy()
    for k in range(1, len(holds)):
        a0, b0, c0 = holds[k - 1]
        a1, b1, c1 = holds[k]
        if (b0 - a0 + 1) / fps < min_hold or (b1 - a1 + 1) / fps < min_hold:
            continue
        dist = abs(c1 - c0)
        dur = int(np.clip(dist / (max_speed or (half_band * 2.5)) , 0.5, 1.2) * fps)
        s = max(a1 - int(dur * 0.7), a0)
        e = min(s + dur, b1)
        u = (np.arange(s, e + 1) - s) / max(e - s, 1)
        out[s:e + 1] = c0 + (c1 - c0) * ease_io(u)
    return out, holds


def zoom_curve(t_src, seg_starts, fps, cam):
    """Multiplier >= 1 per frame: cut zooms alternate per segment, plus planned punches/pushes."""
    n = len(t_src)
    z = np.ones(n)
    cutz = cam.get("cutZoom", [1.0, 1.12])
    seg_id = np.zeros(n, int)
    for k, s in enumerate(seg_starts):
        seg_id[s:] = k
    if cutz:
        z *= np.array([cutz[k % len(cutz)] for k in seg_id])
    for ev in sorted(cam.get("zooms", []), key=lambda e: e.get("te", e.get("t", 0))):
        # "te"/"untile" are edit seconds (render.py); "t"/"until" are source seconds.
        if "te" in ev:
            f0 = int(round(ev["te"] * fps))
            f1 = int(round(ev["untile"] * fps)) if ev.get("untile") is not None else n
            until = ev.get("untile")
        else:
            hit = np.where(np.abs(t_src - ev["t"]) < 0.6 / fps)[0]
            if not len(hit):
                continue
            f0 = hit[0]
            until = ev.get("until")
            f1 = n
            if until is not None:
                h2 = np.where(np.abs(t_src - until) < 0.6 / fps)[0]
                f1 = h2[0] if len(h2) else n
        if f0 >= n:
            continue
        zz = float(ev.get("z", 1.12))
        kind = ev.get("kind", "punch")
        # A zoom never survives the segment it starts in (the next cut resets framing).
        f1 = min(f1, next((s for s in seg_starts if s > f0), n))
        if kind == "punch":
            z[f0:f1] *= zz
        else:  # push: ease in over dur seconds, hold; with "until", ease back out over 8 frames
            dur = int(ev.get("dur", 2.5) * fps)
            u = np.arange(f1 - f0) / max(dur, 1)
            ramp = 1 + (zz - 1) * ease_io(np.clip(u, 0, 1))
            if until is not None and ev.get("release") == "ease" and f1 - f0 > 16:
                ramp[-8:] = 1 + (ramp[-8:] - 1) * ease_io(np.linspace(1, 0, 8))
            z[f0:f1] *= ramp
    return z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--format", default="9x16", choices=SIZES)
    ap.add_argument("--track", help="track.json covering the clip's segments")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--crf", type=int, default=15)
    ap.add_argument("--size", help="WxH output size overriding the format (a second shot, e.g. 820x1080)")
    ap.add_argument("--mode", choices=["follow", "static", "full"], help="override the plan's layout mode")
    ap.add_argument("--face-frac", type=float, help="face width as a fraction of the crop width")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    src = plan["source"]["video"]
    sw, sh = probe(src)
    ow, oh = [int(v) for v in args.size.split("x")] if args.size else SIZES[args.format]
    cam = dict(plan.get("camera", {}))
    if args.face_frac:
        cam["faceFrac"] = args.face_frac
    lay = plan.get("layout", {}).get(args.format, {})
    mode = args.mode or lay.get("mode", "follow" if args.format != "16x9" else "full")
    fps = args.fps

    # Edit timeline: frame -> source time.
    segs = plan["segments"]
    t_src, seg_starts = [], []
    for s in segs:
        seg_starts.append(len(t_src))
        nfr = int(round((s["b"] - s["a"]) * fps))
        t_src.extend(s["a"] + np.arange(nfr) / fps)
    t_src = np.array(t_src)
    n = len(t_src)

    # Base crop size: the largest window of the output aspect that fits the source...
    aspect = ow / oh
    base_h = min(sh, sw / aspect)
    track = json.loads(Path(args.track).read_text()) if args.track else None
    subj = subject_series(track, t_src) if track else None
    if mode == "follow" and subj is not None:
        # ...then tightened so the face is faceFrac of the crop width (a medium shot).
        face_frac = args.face_frac or lay.get("faceFrac") or cam.get("faceFrac") or (0.17 if aspect < 1 else 0.09)
        fw_med = float(np.median(subj[2]))
        want_h = (fw_med / face_frac) / aspect
        base_h = float(np.clip(want_h, min(base_h, oh * 0.62), base_h))
    base_w = base_h * aspect

    z = zoom_curve(t_src, seg_starts, fps, cam)

    if mode == "static" or subj is None and mode != "full":
        r = lay.get("rect") or [(sw - base_w) / 2, (sh - base_h) / 2, base_w, base_h]
        cx = np.full(n, r[0] + r[2] / 2)
        cy = np.full(n, r[1] + r[3] / 2)
        base_w, base_h = r[2], r[3]
        fx, fy = cx.copy(), cy.copy()
    elif mode == "full":
        cx = np.full(n, sw / 2)
        cy = np.full(n, sh / 2)
        base_w, base_h = min(sw, sh * aspect), min(sh, sw / aspect)
        if subj is not None:
            fx, fy = subj[0], subj[1]
        else:
            fx, fy = cx.copy(), cy.copy()
    else:
        fx, fy, _ = subj
        eye_line = cam.get("eyeLine", 0.36 if aspect < 1 else 0.40)
        band = cam.get("deadZone", 0.18)  # half-width of the dead zone, fraction of crop width
        cx = np.empty(n)
        cy = np.empty(n)
        for k, s0 in enumerate(seg_starts):
            s1 = seg_starts[k + 1] if k + 1 < len(seg_starts) else n
            xs, _ = plan_axis(fx[s0:s1], fps, band * base_w)
            ys, _ = plan_axis(fy[s0:s1], fps, 0.08 * base_h)
            cx[s0:s1] = xs
            cy[s0:s1] = ys + (0.5 - eye_line) * base_h

    # Apply zoom around the face so the face keeps its place in frame.
    cw = base_w / z
    ch = base_h / z
    ccx = fx + (cx - fx) / z
    ccy = fy + (cy - fy) / z
    ccx = np.clip(ccx, cw / 2, sw - cw / 2)
    ccy = np.clip(ccy, ch / 2, sh - ch / 2)
    x0 = ccx - cw / 2
    y0 = ccy - ch / 2

    # Face position in OUTPUT pixels, for captions and overlays that must avoid it.
    face_out = [[round(float((fx[i] - x0[i]) / cw[i] * ow), 1), round(float((fy[i] - y0[i]) / ch[i] * oh), 1)]
                for i in range(n)]
    upscale = float(np.max(ow / cw))
    cam_out = {"format": args.format, "fps": fps, "frames": n, "source": src, "sourceSize": [sw, sh],
               "segStarts": seg_starts, "maxUpscale": round(upscale, 2),
               "crop": [[round(float(x0[i]), 1), round(float(y0[i]), 1), round(float(cw[i]), 1), round(float(ch[i]), 1)]
                        for i in range(n)],
               "face": face_out}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(str(out).replace(".mp4", ".camera.json")).write_text(json.dumps(cam_out))
    print(f"{n} frames, crop {base_w:.0f}x{base_h:.0f} of {sw}x{sh} -> {ow}x{oh}, max upscale {upscale:.2f}x, "
          f"{len(seg_starts)} segments")
    if args.dry:
        return

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
                            "-pix_fmt", "yuv420p", "-g", "15", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    fi = 0
    fb = sw * sh * 3
    for k, s in enumerate(segs):
        nfr = (seg_starts[k + 1] if k + 1 < len(seg_starts) else n) - seg_starts[k]
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-ss", f"{s['a']:.3f}", "-i", src,
                                "-frames:v", str(nfr), "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                               stdout=subprocess.PIPE)
        got = 0
        last = None
        while got < nfr:
            buf = dec.stdout.read(fb)
            if len(buf) < fb:
                if last is None:
                    sys.exit(f"decode failed at segment {k}")
                img = last  # pad a short segment with its last frame
            else:
                img = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
                last = img
            x, y, w, h = x0[fi], y0[fi], cw[fi], ch[fi]
            # Sub-pixel crop via an affine warp, so slow moves glide instead of stepping.
            sx, sy = ow / w, oh / h
            M = np.array([[sx, 0, -x * sx], [0, sy, -y * sy]], np.float32)
            interp = cv2.INTER_AREA if sx < 1 else cv2.INTER_LANCZOS4
            if sx < 1:
                # Downscale: crop to the integer bounding box first (cheap), then warp.
                xi, yi = int(x), int(y)
                sub = img[yi:yi + int(h) + 2, xi:xi + int(w) + 2]
                M2 = np.array([[sx, 0, -(x - xi) * sx], [0, sy, -(y - yi) * sy]], np.float32)
                frame = cv2.warpAffine(sub, M2, (ow, oh), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
            else:
                xi, yi = max(int(x) - 2, 0), max(int(y) - 2, 0)
                sub = img[yi:yi + int(h) + 6, xi:xi + int(w) + 6]
                M2 = np.array([[sx, 0, -(x - xi) * sx], [0, sy, -(y - yi) * sy]], np.float32)
                frame = cv2.warpAffine(sub, M2, (ow, oh), flags=interp, borderMode=cv2.BORDER_REPLICATE)
                if sx > 1.25:  # light unsharp mask to offset upscaling softness
                    blur = cv2.GaussianBlur(frame, (0, 0), 1.2)
                    frame = cv2.addWeighted(frame, 1.35, blur, -0.35, 0)
            enc.stdin.write(frame.tobytes())
            got += 1
            fi += 1
        dec.stdout.close()
        dec.wait()
    enc.stdin.close()
    enc.wait()
    print(f"plate -> {out}")


if __name__ == "__main__":
    main()
