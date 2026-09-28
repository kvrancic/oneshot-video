#!/usr/bin/env python3
"""Match cameras to each other and give them one gentle look, as ffmpeg filters.

  grade.py DIR/edit.json [--look natural|warm|punchy] [--preview]

Samples frames across the talk from every camera and white-balances each one on its
neutral surfaces (walls, tables, ceilings: low saturation, mid to high brightness), so
the cameras agree on what white is; whole-frame statistics would be skewed by a bright
projection. Then one shared look. Screen recordings are left
alone. Writes grade.json {camera id: ffmpeg filter string}; --preview writes a before/
after still per camera into DIR/grade/.
"""
import argparse, json, subprocess
from pathlib import Path

import numpy as np

LOOKS = {
    # contrast, saturation, gamma, warm (colorbalance midtones red+ / blue-)
    "natural": (1.05, 1.08, 1.0, 0.03),
    "warm": (1.07, 1.10, 0.98, 0.06),
    "punchy": (1.12, 1.18, 0.97, 0.04),
}


def sample(path, offset, times, w=480):
    out = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t + offset, 0):.2f}", "-i", path, "-frames:v", "1",
                              "-vf", f"scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if raw:
            out.append(np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(float))
    return np.concatenate(out) if out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--look", default="natural", choices=LOOKS)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    plan_path = Path(args.plan)
    d = plan_path.parent
    plan = json.loads(plan_path.read_text())
    cams = plan["source"]["cameras"]
    segs = plan.get("segments") or []
    lo = min(s["a"] for s in segs) if segs else 60.0
    hi = max(s["b"] for s in segs) if segs else 600.0
    times = list(np.linspace(lo + 30, hi - 30, 12))
    con, sat, gam, warm = LOOKS[args.look]
    look = f"eq=contrast={con}:saturation={sat}:gamma={gam},colorbalance=rm={warm}:bm={-warm}"
    out = {}
    for c in cams:
        if c["id"] == "screen":
            out[c["id"]] = "null"
            continue
        px = sample(c["path"], c.get("offset", 0.0), times)
        mx, mn = px.max(axis=1), px.min(axis=1)
        sat_ = (mx - mn) / np.maximum(mx, 1)
        neutral = (sat_ < 0.12) & (mx > 90) & (mx < 235)
        ref = px[neutral].mean(axis=0) if neutral.sum() > 500 else px.mean(axis=0)
        gray = ref.mean()
        gains = np.clip(gray / np.maximum(ref, 1), 0.85, 1.2)
        out[c["id"]] = f"colorchannelmixer=rr={gains[0]:.3f}:gg={gains[1]:.3f}:bb={gains[2]:.3f}," + look
        print(f"{c['id']}: neutral surfaces {ref.round(1)} ({neutral.mean():.0%} of pixels) -> gains {gains.round(3)}")
    (d / "grade.json").write_text(json.dumps(out, indent=1))
    print(f"look '{args.look}' -> {d / 'grade.json'}")
    if args.preview:
        gd = d / "grade"
        gd.mkdir(exist_ok=True)
        t = times[len(times) // 2]
        for c in cams:
            if c["id"] == "screen":
                continue
            src = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t + c.get('offset', 0.0):.2f}", "-i", c["path"], "-frames:v", "1"]
            subprocess.run(src + ["-vf", "scale=960:-2", str(gd / f"{c['id']}-before.jpg")], check=True)
            subprocess.run(src + ["-vf", f"scale=960:-2,{out[c['id']]}", str(gd / f"{c['id']}-after.jpg")], check=True)
        print(f"preview stills -> {gd}")


if __name__ == "__main__":
    main()
