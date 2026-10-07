#!/usr/bin/env python3
"""Asset helpers. Source-derived visuals first (slides, frames, the speaker's own deck);
stock second (Pexels); public-figure photos from Wikimedia Commons with the licence
recorded next to the file (<file>.license.json) so the post can credit it.

  assets.py portrait IMAGE --out chip.png [--face 0] [--scale 2.6]   square head-and-shoulders crop
  assets.py frame VIDEO SECONDS --out still.jpg [--width 1920]
  assets.py pexels "city at night" --out dir [--kind video|photo] [--orientation portrait|landscape] [--n 3]
  assets.py commons "Geoffrey Hinton" --out dir [--n 3]              Creative Commons portraits
  assets.py deck DECK.pdf --out dir [--dpi 200]                       deck pages as crisp PNGs
"""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YUNET = ROOT / "models/face_detection_yunet_2023mar.onnx"
UA = {"User-Agent": "oneshot-video/1.0 (local video editing tool)"}


def env_key(name):
    if os.environ.get(name):
        return os.environ[name]
    for p in [Path.cwd() / ".env", ROOT / ".env", Path.home() / ".config/oneshot-video/.env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"')
    return None


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download(url, out):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
        f.write(r.read())
    return out


def portrait(args):
    import cv2

    im = cv2.imread(args.image)
    h, w = im.shape[:2]
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), 0.6, 0.3, 50)
    _, faces = det.detect(im)
    if faces is None:
        sys.exit("no face found")
    faces = sorted(faces, key=lambda f: -f[2] * f[3])
    x, y, fw, fh = faces[min(args.face, len(faces) - 1)][:4]
    cx, cy = x + fw / 2, y + fh * 0.55
    side = max(fw, fh) * args.scale
    x0, y0 = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
    x1, y1 = int(min(cx + side / 2, w)), int(min(cy + side / 2, h))
    s = min(x1 - x0, y1 - y0)
    crop = im[y0:y0 + s, x0:x0 + s]
    crop = cv2.resize(crop, (args.size, args.size), interpolation=cv2.INTER_AREA if s > args.size else cv2.INTER_LANCZOS4)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.out, crop)
    print(f"portrait {s}px -> {args.out}")


def frame(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(args.seconds), "-i", args.video, "-frames:v", "1",
                    "-vf", f"scale={args.width}:-2", args.out], check=True)
    print(args.out)


def pexels(args):
    key = env_key("PEXELS_API_KEY")
    if not key:
        sys.exit("PEXELS_API_KEY missing: get a free key at https://www.pexels.com/api/ and put it in .env")
    q = urllib.parse.quote(args.query)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.kind == "video":
        data = get_json(f"https://api.pexels.com/videos/search?query={q}&per_page={args.n * 2}&orientation={args.orientation}",
                        {"Authorization": key})
        got = 0
        for v in data.get("videos", []):
            files = sorted([f for f in v["video_files"] if f.get("width") and f["file_type"] == "video/mp4"],
                           key=lambda f: abs((f["width"] or 0) - (1080 if args.orientation == "portrait" else 1920)))
            if not files:
                continue
            f = files[0]
            path = out / f"pexels-{v['id']}.mp4"
            download(f["link"], path)
            meta = {"source": "Pexels", "url": v["url"], "author": v["user"]["name"], "license": "Pexels License",
                    "duration": v["duration"], "width": f["width"], "height": f["height"]}
            Path(str(path) + ".license.json").write_text(json.dumps(meta, indent=2))
            print(f"{path}  {v['duration']}s {f['width']}x{f['height']}  by {v['user']['name']}")
            got += 1
            if got >= args.n:
                break
    else:
        data = get_json(f"https://api.pexels.com/v1/search?query={q}&per_page={args.n}&orientation={args.orientation}",
                        {"Authorization": key})
        for p in data.get("photos", []):
            path = out / f"pexels-{p['id']}.jpg"
            download(p["src"]["large2x"], path)
            meta = {"source": "Pexels", "url": p["url"], "author": p["photographer"], "license": "Pexels License"}
            Path(str(path) + ".license.json").write_text(json.dumps(meta, indent=2))
            print(f"{path}  by {p['photographer']}")


def commons(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    q = urllib.parse.quote(f"{args.query} filetype:bitmap")
    data = get_json("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
                    f"&gsrnamespace=6&gsrsearch={q}&gsrlimit={args.n * 3}&prop=imageinfo"
                    "&iiprop=url|extmetadata|size&iiurlwidth=1200")
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    got = 0
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not re.search(r"CC|Public domain|PD", lic, re.I):
            continue
        url = ii.get("thumburl") or ii.get("url")
        name = re.sub(r"[^\w.-]", "_", p["title"].replace("File:", ""))[:80]
        path = out / name
        download(url, path)
        artist = re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        meta = {"source": "Wikimedia Commons", "page": ii.get("descriptionurl"), "author": artist, "license": lic,
                "credit": f"{artist}, {lic}, via Wikimedia Commons"}
        Path(str(path) + ".license.json").write_text(json.dumps(meta, indent=2))
        print(f"{path}  [{lic}] {artist}")
        got += 1
        if got >= args.n:
            break
    if not got:
        print("no freely licensed images found")


def deck(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-r", str(args.dpi), args.deck, str(out / "slide")], check=True)
    print(f"pages -> {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("portrait"); p.add_argument("image"); p.add_argument("--out", required=True)
    p.add_argument("--face", type=int, default=0); p.add_argument("--scale", type=float, default=2.6); p.add_argument("--size", type=int, default=512)
    p = sub.add_parser("frame"); p.add_argument("video"); p.add_argument("seconds", type=float); p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1920)
    p = sub.add_parser("pexels"); p.add_argument("query"); p.add_argument("--out", required=True)
    p.add_argument("--kind", default="video", choices=["video", "photo"]); p.add_argument("--orientation", default="portrait")
    p.add_argument("--n", type=int, default=3)
    p = sub.add_parser("commons"); p.add_argument("query"); p.add_argument("--out", required=True); p.add_argument("--n", type=int, default=3)
    p = sub.add_parser("deck"); p.add_argument("deck"); p.add_argument("--out", required=True); p.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    {"portrait": portrait, "frame": frame, "pexels": pexels, "commons": commons, "deck": deck}[args.cmd](args)


if __name__ == "__main__":
    main()
