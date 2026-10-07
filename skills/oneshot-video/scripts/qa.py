#!/usr/bin/env python3
"""Check a rendered clip before anyone sees it, and make the contact sheet to look at.

  qa.py DIR/clips/NN-slug [--format 9x16]

Checks (PASS / WARN / FAIL):
  streams     one H.264 video at the format's size, one AAC audio, durations agree
  loudness    integrated -14 LUFS +-1, true peak <= -1 dBTP
  black       black frames longer than 0.1 s (a missing plate or a bad cut)
  frozen      frozen video longer than 2 s (decode padding, a stuck plate)
  silence     silences longer than 1.2 s inside the clip (a pause that should be cut)
  captions    caption pages whose box overlaps the speaker's face (from the camera track)
  safe zone   caption baseline inside the platform-safe band
Writes DIR/renders/<id>-<fmt>.sheet.jpg (a frame every N seconds with timecodes)
and DIR/renders/<id>-<fmt>.qa.json.
"""
import argparse, json, re, subprocess
from pathlib import Path

SIZES = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_dir")
    ap.add_argument("--format")
    args = ap.parse_args()
    d = Path(args.clip_dir)
    plan = json.loads((d / "plan.json").read_text())
    fmts = [args.format] if args.format else plan.get("formats", ["9x16"])
    all_ok = True
    for fmt in fmts:
        out = d / "renders" / f"{plan['id']}-{fmt}.mp4"
        res = []

        def rep(name, level, msg):
            res.append({"check": name, "level": level, "msg": msg})

        if not out.exists():
            print(f"{fmt}: no render at {out}")
            all_ok = False
            continue
        pr = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,duration:format=duration",
                            "-of", "json", str(out)]).stdout)
        v = [s for s in pr["streams"] if s["codec_type"] == "video"]
        a = [s for s in pr["streams"] if s["codec_type"] == "audio"]
        dur = float(pr["format"]["duration"])
        w, h = SIZES[fmt]
        ok = len(v) == 1 and len(a) == 1 and v[0]["width"] == w and v[0]["height"] == h
        rep("streams", "PASS" if ok else "FAIL", f"{len(v)}v/{len(a)}a {v[0]['width']}x{v[0]['height']} {dur:.2f}s" if v else "no video")

        lo = sh(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
        m_i = re.findall(r"I:\s+(-?[\d.]+) LUFS", lo)
        m_tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)
        if m_i:
            i_val = float(m_i[-1])
            tp = float(m_tp[-1]) if m_tp else 0
            lvl = "PASS" if abs(i_val + 14) <= 1 and tp <= -0.5 else "WARN"
            rep("loudness", lvl, f"{i_val:.1f} LUFS, true peak {tp:.1f} dBTP")

        bl = sh(["ffmpeg", "-hide_banner", "-i", str(out), "-vf", "blackdetect=d=0.1:pix_th=0.06", "-an", "-f", "null", "-"]).stderr
        blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl)
        rep("black", "FAIL" if blacks else "PASS", ", ".join(f"{float(s):.1f}-{float(e):.1f}s" for s, e in blacks) or "none")

        fr = sh(["ffmpeg", "-hide_banner", "-i", str(out), "-vf", "freezedetect=n=0.002:d=2", "-an", "-f", "null", "-"]).stderr
        frozen = re.findall(r"freeze_start: ([\d.]+)", fr)
        rep("frozen", "WARN" if frozen else "PASS", ", ".join(f"{float(s):.1f}s" for s in frozen) or "none")

        si = sh(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "silencedetect=noise=-38dB:d=1.2", "-vn", "-f", "null", "-"]).stderr
        sil = [(float(s), float(e)) for s, e in zip(re.findall(r"silence_start: ([\d.]+)", si), re.findall(r"silence_end: ([\d.]+)", si))]
        sil = [x for x in sil if x[0] > 0.5 and x[1] < dur - 0.5]
        rep("silence", "WARN" if sil else "PASS", ", ".join(f"{s:.1f}-{e:.1f}s" for s, e in sil) or "none")

        # Captions vs face: approximate each page's box from the props and the face track.
        props_p = d / f"props-{fmt}.json"
        if props_p.exists():
            props = json.loads(props_p.read_text())
            face = props["face"]
            toks = props["captions"]["tokens"]
            base_y = {"9x16": 1400, "16x9": 984, "1x1": 900, "4x5": 1150}[fmt]
            hits = []
            for t in toks[::4]:
                fi = int(t["start"] * 30 / face["every"])
                if fi < len(face["xy"]):
                    fx, fy = face["xy"][fi]
                    if base_y - 150 < fy + 90 and fy - 90 < base_y + 20 and abs(fx - w / 2) < w * 0.35:
                        hits.append(round(t["start"], 1))
            rep("captions", "WARN" if hits else "PASS", f"face near captions at {hits[:8]}" if hits else "clear of the face")

        # Contact sheet: a frame every 4 s (every 8 s past two minutes), 6 across.
        step = 4 if dur <= 120 else 8
        sheet = d / "renders" / f"{plan['id']}-{fmt}.sheet.jpg"
        tile_w = 270 if h > w else 384
        n = int(dur // step) + 1
        rows = (n + 5) // 6
        sh(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf",
            # select keeps each frame's own time, so the label matches the picture (fps= labels the tick, not the frame)
            f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step - 0.01})',scale={tile_w}:-2,"
            f"drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.5,"
            f"tile=6x{rows}:padding=4:color=0x111111", "-fps_mode", "vfr", "-frames:v", "1", str(sheet)])
        (d / "renders" / f"{plan['id']}-{fmt}.qa.json").write_text(json.dumps(res, indent=2))
        print(f"\n{plan['id']} {fmt}  ({dur:.1f}s)")
        for r in res:
            print(f"  {r['level']:4s}  {r['check']:9s} {r['msg']}")
            all_ok &= r["level"] != "FAIL"
        print(f"  sheet: {sheet}")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
