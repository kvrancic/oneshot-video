#!/usr/bin/env python3
"""Collect finished clips into a clean export folder with everything needed to post.

  package.py DIR [--clips 01,03] [--date 2026-09-27]

DIR/exports/<date>/
  NN-slug/
    slug.9x16.mp4, slug.16x9.mp4     the renders (clean: no watermark, native per format)
    cover.9x16.jpg ...                cover still (plan "cover": edit seconds, default 1.0)
    captions.srt                      sentence-level subtitles for platforms that take a sidecar
    post.md                           title, hook, per-platform copy (plan "post"), transcript
    credits.txt                       the source footage's credit (project.json "credit", for footage
                                      the user does not own), licences for third-party images, flags
  index.html                          review page: every clip, every format, side by side
"""
import argparse, datetime, html, json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(tokens):
    cues, cur = [], []
    for t in tokens:
        cur.append(t)
        text = " ".join(x["text"] for x in cur)
        if re.search(r"[.!?]$", t["text"]) or len(text) > 38 or len(cur) >= 8:
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    out = []
    prev_end_sentence = True
    for i, c in enumerate(cues, 1):
        text = " ".join(x["text"] for x in c)
        if prev_end_sentence and text:
            text = text[0].upper() + text[1:]
        prev_end_sentence = bool(re.search(r"[.!?][\"')\]]?$", c[-1]["text"]))
        end = c[-1]["end"] + 0.2
        if i < len(cues):
            end = min(end, cues[i][0]["start"] - 0.05)
        out.append(f"{i}\n{srt_time(c[0]['start'])} --> {srt_time(max(end, c[0]['start'] + 0.3))}\n{text}\n")
    return "\n".join(out)


def find_assets(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("photo", "src", "image") and isinstance(v, str):
                acc.append(v)
            else:
                find_assets(v, acc)
    elif isinstance(o, list):
        for x in o:
            find_assets(x, acc)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--clips")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    proj = Path(args.project)
    exp = proj / "exports" / args.date
    exp.mkdir(parents=True, exist_ok=True)
    want = set(args.clips.split(",")) if args.clips else None
    cards = []
    for cd in sorted((proj / "clips").iterdir()):
        if not (cd / "plan.json").exists():
            continue
        if want and not any(cd.name.startswith(w) for w in want):
            continue
        plan = json.loads((cd / "plan.json").read_text())
        slug = re.sub(r"^\d+-", "", cd.name)
        od = exp / cd.name
        od.mkdir(exist_ok=True)
        files = []
        for fmt in plan.get("formats", ["9x16"]):
            r = cd / "renders" / f"{plan['id']}-{fmt}.mp4"
            if not r.exists():
                continue
            dst = od / f"{slug}.{fmt}.mp4"
            shutil.copy2(r, dst)
            cover = od / f"cover.{fmt}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(plan.get("cover", 1.0)), "-i", str(dst), "-frames:v", "1",
                            "-q:v", "2", str(cover)], check=True)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                                       capture_output=True, text=True).stdout.strip())
            files.append((fmt, dst.name, cover.name, dur))
        if not files:
            continue
        tokens = json.loads((cd / "tokens.json").read_text()) if (cd / "tokens.json").exists() else []
        (od / "captions.srt").write_text(srt(tokens))
        transcript = " ".join(t["text"] for t in tokens)

        credits = []
        pj = proj / "project.json"
        src_credit = json.loads(pj.read_text()).get("credit") if pj.exists() else None
        if src_credit:  # e.g. a Creative Commons talk: the attribution its licence requires
            credits += [src_credit] if isinstance(src_credit, str) else list(src_credit)
        for a in sorted(set(find_assets(plan, []))):
            p = (cd / a) if (cd / a).exists() else Path(a)
            lic = Path(str(p) + ".license.json")
            if lic.exists():
                m = json.loads(lic.read_text())
                credits.append(f"{p.name}: {m.get('credit') or m.get('author', '')} ({m.get('license', '')}) {m.get('page') or m.get('url', '')}")
            elif p.exists():
                credits.append(f"{p.name}: source-derived (the speaker's own material); check rights to any photo inside it")
        flags = plan.get("flags", [])
        (od / "credits.txt").write_text("\n".join(credits + [""] + [f"FLAG: {f}" for f in flags]) + "\n")

        post = plan.get("post", {})
        md = [f"# {plan.get('title', slug)}\n", f"Length: {files[0][3]:.0f}s. Formats: {', '.join(f[0] for f in files)}.\n"]
        if plan.get("hook"):
            md.append(f"Hook on screen: {plan['hook'].get('text', '').replace(chr(10), ' ')}\n")
        for k, label in [("x", "X"), ("linkedin", "LinkedIn"), ("tiktok", "TikTok"), ("reels", "Instagram Reels"),
                         ("shorts_title", "YouTube Shorts title"), ("youtube_title", "YouTube title"), ("youtube", "YouTube description")]:
            if post.get(k):
                md.append(f"\n## {label}\n\n{post[k]}\n")
        if flags:
            md.append("\n## Flags\n\n" + "".join(f"- {f}\n" for f in flags))
        md.append(f"\n## Transcript\n\n{transcript}\n")
        (od / "post.md").write_text("".join(md))
        cards.append((cd.name, plan, files, flags, post))
        print(f"{cd.name}: {', '.join(f'{f[0]} {f[3]:.0f}s' for f in files)} -> {od}")

    # Review page.
    items = []
    for name, plan, files, flags, post in cards:
        vids = "".join(
            f'<figure class="{"v" if f[0] in ("9x16", "4x5") else "h"}"><video src="{name}/{f[1]}" poster="{name}/{f[2]}" controls preload="metadata"></video>'
            f"<figcaption>{f[0]} · {int(f[3] // 60)}:{int(f[3] % 60):02d}</figcaption></figure>" for f in files)
        fl = "".join(f"<li>{html.escape(x)}</li>" for x in flags)
        items.append(f'<section><h2>{html.escape(plan.get("title", name))}</h2>'
                     f'<p class="hook">{html.escape((plan.get("hook") or {}).get("text", "").replace(chr(10), " "))}</p>'
                     f'<div class="row">{vids}</div>{"<ul class=flags>" + fl + "</ul>" if fl else ""}'
                     f'<p class="files"><a href="{name}/post.md">post.md</a> · <a href="{name}/captions.srt">captions.srt</a> · '
                     f'<a href="{name}/credits.txt">credits.txt</a></p></section>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clips {args.date}</title><style>
:root{{--bg:#111;--fg:#f4f1ea;--mut:#a8a39a;--acc:#ff7a4d}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 Inter,system-ui,sans-serif;padding:32px 16px}}
main{{max-width:1400px;margin:0 auto}} h1{{font-weight:700;letter-spacing:-.02em;margin:0 0 24px}}
section{{border-top:1px solid #2a2a2a;padding:28px 0}} h2{{margin:0 0 6px;font-size:24px;letter-spacing:-.01em}}
.hook{{color:var(--mut);margin:0 0 18px}} .row{{display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start}}
figure{{margin:0}} figure.v video{{width:300px;aspect-ratio:9/16}} figure.h video{{width:min(640px,100%);aspect-ratio:16/9}}
video{{background:#000;border-radius:10px;display:block}} figcaption{{color:var(--mut);font-size:13px;margin-top:6px}}
.flags{{color:var(--acc);font-size:14px}} .files a{{color:var(--mut)}}
</style></head><body><main><h1>Clips · {args.date}</h1>{''.join(items)}</main></body></html>"""
    (exp / "index.html").write_text(page)
    print(f"review page -> {exp / 'index.html'}")


if __name__ == "__main__":
    main()
