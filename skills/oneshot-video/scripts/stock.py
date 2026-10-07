#!/usr/bin/env python3
"""Stock footage from Pexels for from-scratch films: search, look, then download.

  stock.py search "boston skyline dusk" [--n 30] [--orientation landscape]   ids, sizes, titles (needs PEXELS_API_KEY)
  stock.py sheet ID [ID ...] --out sheet.jpg [--at 3]                          one frame per clip, labelled, tiled 6 wide
  stock.py frames ID --out strip.jpg [--every 3]                              one frame every N s of one clip (pick the in-point)
  stock.py get ID [ID ...] --out DIR/public/footage [--seconds 20] [--size 1920x1080] [--from 0]

`get` and `sheet` need no key: they read Pexels' public file URLs. `get` writes px_<id>.mp4
trimmed, silent, cropped to the frame, 30 fps, with short GOPs (Remotion seeks fast) and a
px_<id>.json with the source page for credits. Without a key, search in the browser (pexels.com,
filter by orientation) and read the ids from the result URLs (/video/<slug>-<id>/).

Pexels License: free to use and modify, no attribution required (credit anyway in the post);
never redistribute clips unedited or imply endorsement by people in them.
Titles do not prove places: look at the sheet before using a clip as a named location.
"""
import argparse, json, subprocess, sys, tempfile, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assets import env_key  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari/537.36"


def source_url(vid, size="1920x1080"):
    """The direct file URL of a Pexels video: the HD rendition at its own frame rate, or the
    download redirect (which serves the original) when no HD file answers."""
    w, h = size.split("x")
    label = "uhd" if int(w) > 1920 or int(h) > 1920 else "hd"
    for fps in (30, 25, 24, 60, 50, 29.97, 23.98):
        f = f"{fps:g}"
        for wh in (f"{w}_{h}", f"{h}_{w}"):
            u = f"https://videos.pexels.com/video-files/{vid}/{vid}-{label}_{wh}_{f}fps.mp4"
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Range": "bytes=0-10"})
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    if r.status in (200, 206):
                        return u
            except Exception:
                pass
    return f"https://www.pexels.com/download/video/{vid}/"


def search(args):
    key = env_key("PEXELS_API_KEY")
    if not key:
        sys.exit("PEXELS_API_KEY missing (free: https://www.pexels.com/api/). Without it: search on pexels.com in the "
                 "browser and pass the ids from the result URLs to `stock.py sheet`.")
    q = urllib.parse.quote(args.query)
    url = f"https://api.pexels.com/videos/search?query={q}&per_page={args.n}&orientation={args.orientation}"
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    for v in data.get("videos", []):
        slug = v["url"].rstrip("/").split("/")[-1].rsplit("-", 1)[0].replace("-", " ")
        print(f"{v['id']:>10}  {v['duration']:>3}s  {v['width']}x{v['height']}  {slug[:70]}  ({v['user']['name']})")


def grab(vid, at, tmp):
    out = Path(tmp) / f"{vid}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-user_agent", UA, "-ss", str(at), "-i", source_url(vid), "-frames:v", "1",
                    "-vf", f"scale=480:270:force_original_aspect_ratio=increase,crop=480:270,drawtext=text='{vid}':x=10:y=10:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6",
                    str(out)], check=False)
    return out if out.exists() else None


def sheet(args):
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(10) as ex:
        shots = [p for p in ex.map(lambda v: grab(v, args.at, tmp), args.ids) if p]
        if not shots:
            sys.exit("no frames (check the ids)")
        cols = min(6, len(shots))
        rows = -(-len(shots) // cols)
        inputs = sum((["-i", str(p)] for p in shots), [])
        pad = "".join(f"[{i}]" for i in range(len(shots)))
        layout = "|".join(f"{(i % cols) * 480}_{(i // cols) * 270}" for i in range(len(shots)))
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
                        f"{pad}xstack=inputs={len(shots)}:layout={layout}:fill=black" if len(shots) > 1 else "null", args.out], check=True)
    print(f"{args.out}  {len(shots)} clips, {cols}x{rows}")


def frames(args):
    src = source_url(args.id)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-user_agent", UA, "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout or 20)
    n = max(1, int(dur // args.every))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-user_agent", UA, "-i", src, "-vf",
                    f"fps=1/{args.every},scale=480:-2,drawtext=text='%{{pts\\:hms}}':x=10:y=10:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6,tile=1x{n}",
                    "-frames:v", "1", args.out], check=True)
    print(f"{args.out}  {n} frames, one every {args.every} s ({dur:.0f} s clip)")


def get(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    w, h = args.size.split("x")

    def one(vid):
        dst = out / f"px_{vid}.mp4"
        if dst.exists():
            return f"have {dst.name}"
        src = source_url(vid, args.size)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-user_agent", UA, "-ss", str(args.from_), "-i", src, "-t", str(args.seconds), "-an",
                            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},fps=30,format=yuv420p",
                            "-c:v", "libx264", "-crf", "15", "-preset", "fast", "-g", "15", str(dst)], capture_output=True, text=True)
        if r.returncode:
            return f"FAILED {vid}: {r.stderr.strip()[:200]}"
        (out / f"px_{vid}.json").write_text(json.dumps({"source": "Pexels", "url": f"https://www.pexels.com/video/{vid}/",
                                                        "license": "Pexels License (https://www.pexels.com/license/)"}, indent=2))
        return f"ok {dst.name}"

    with ThreadPoolExecutor(4) as ex:
        for line in ex.map(one, args.ids):
            print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("search")
    p.add_argument("query")
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--orientation", default="landscape", choices=["landscape", "portrait", "square"])
    p = sp.add_parser("sheet")
    p.add_argument("ids", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--at", type=float, default=3)
    p = sp.add_parser("frames")
    p.add_argument("id")
    p.add_argument("--out", required=True)
    p.add_argument("--every", type=float, default=3)
    p = sp.add_parser("get")
    p.add_argument("ids", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--size", default="1920x1080")
    p.add_argument("--from", dest="from_", type=float, default=0)
    args = ap.parse_args()
    {"search": search, "sheet": sheet, "frames": frames, "get": get}[args.cmd](args)


if __name__ == "__main__":
    main()
