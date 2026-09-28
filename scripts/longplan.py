#!/usr/bin/env python3
"""Build a full-edit plan (edit.json) from the story editor's structure.json and the cuts
the owner approved.

  longplan.py DIR --approve x01,x03,x07 [--teaser] [--title "THE AI LECTURE"] [--subtitle "..."] [--byline "..."]

Keeps talkStart..talkEnd, removes the approved section cuts and the listed stumbles,
optionally puts the teaser lines first (a cold open), and writes:
  edit        word ranges in playing order
  cut         stumble words (fillers are cut by edl.py with cutFillers)
  chapters    from structure.json (the ones whose first word survived)
  inserts     the opening title behind the speaker, a chapter title per chapter, a note
              where an approved cut carries one, and the B-roll graphics
  source      picture, microphone, cameras (close, wide, screen) from project.json
Then run: edl.py DIR/edit.json && multicam.py DIR/edit.json && grade.py DIR/edit.json &&
longrender.py DIR/edit.json --preview 0-180 && longrender.py DIR/edit.json
"""
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--approve", default="")
    ap.add_argument("--teaser", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--byline", default="")
    ap.add_argument("--palette", default="paper")
    args = ap.parse_args()
    d = Path(args.dir)
    st = json.loads((d / "structure.json").read_text())
    proj = json.loads((d / "project.json").read_text())
    W = json.loads((d / "transcript.words.json").read_text())["words"]
    approved = {x.strip() for x in args.approve.split(",") if x.strip()}
    cuts = [c for c in st.get("proposedCuts", []) if c["id"] in approved]

    # Kept ranges: the talk minus approved cuts.
    keep = [[st["talkStart"], st["talkEnd"]]]
    for c in sorted(cuts, key=lambda c: c["from"]):
        nxt = []
        for a, b in keep:
            if c["to"] < a or c["from"] > b:
                nxt.append([a, b])
                continue
            if c["from"] > a:
                nxt.append([a, c["from"] - 1])
            if c["to"] < b:
                nxt.append([c["to"] + 1, b])
        keep = nxt
    edit = []
    if args.teaser:
        edit += [{"words": [t["from"], t["to"]], "keepPauses": True, "note": "teaser"} for t in st.get("teaser", [])]
    edit += [{"words": [a, b]} for a, b in keep if b >= a]
    kept = set()
    for a, b in keep:
        kept.update(range(a, b + 1))
    stumbles = sorted({i for a, b in st.get("stumbles", []) for i in range(a, b + 1) if i in kept})

    chapters = [c for c in st.get("chapters", []) if c["at"] in kept]
    first_main = keep[0][0]
    opener_at = f"#{first_main}@2" if args.teaser else f"#{first_main}"

    sources = {s["path"]: s for s in proj["sources"] if "error" not in s}
    cams = [{"id": "close", "path": proj["primary"], "offset": 0.0, "track": str(d / "track-close.json")}]
    for s in proj["sources"]:
        if s.get("role") == "camera":
            cams.append({"id": "wide", "path": s["path"], "offset": s["offset"]})
            break
    if proj.get("screens"):
        cams.append({"id": "screen", "path": proj["screens"][0]["path"], "offset": proj["screens"][0]["offset"]})

    inserts = []
    angles = []
    if args.title:
        inserts.append({"kind": "title", "from": opener_at, "to": f"{opener_at}+5.5", "overlays": [
            {"type": "TextBehind", "from": 0.3, "to": 5.2, "props": {"text": args.title}},
            *([{"type": "NameTag", "from": 1.8, "to": 5.4, "props": {"name": args.byline or args.subtitle, "role": args.subtitle if args.byline else ""}}]
              if (args.byline or args.subtitle) else [])]})
        angles.append({"from": f"#{first_main}", "to": f"#{min(first_main + 25, len(W) - 1)}", "angle": "close.medium"})
    # Chapter openings: the title behind the speaker, with a small part kicker.
    for c in (chapters[1:] if args.title else chapters):
        kicker, _, name = c["title"].partition("·")
        name = (name or kicker).strip()
        kicker = kicker.strip() if name != kicker.strip() else ""
        ovs = [{"type": "TextBehind", "from": 0.2, "to": 3.8, "props": {"text": name}}]
        if kicker:
            ovs.append({"type": "KeywordChip", "from": 0.3, "to": 3.7, "props": {"text": kicker, "x": 96, "y": 90, "dot": True}})
        inserts.append({"kind": "chapter", "from": f"#{c['at']}", "to": f"#{c['at']}+4.0", "overlays": ovs})
        angles.append({"from": f"#{c['at']}", "to": f"#{min(c['at'] + 18, len(W) - 1)}", "angle": "close.medium"})
    for c in cuts:
        if c.get("note") and c["to"] + 1 in kept:
            at = c["to"] + 1
            chip = {"type": "KeywordChip", "from": 0.2, "to": 4.3, "props": {"text": c["note"], "x": 96, "y": 90}}
            end = f"#{at}+4.5"
            # A chapter title starting within the note's time: the note leaves just before it.
            nxt = min((ch["at"] for ch in chapters if ch["at"] >= at), default=None)
            if nxt is not None and W[nxt]["s"] - W[at]["s"] < 4.8:
                end = f"#{nxt}-0.3"
                del chip["to"]
            inserts.append({"kind": "note", "from": f"#{at}", "to": end, "overlays": [chip]})
    for b in st.get("broll", []):
        if b["from"] not in kept or b["to"] not in kept or not b.get("props"):
            continue  # the editor fills props (with word-reference beats) before rendering
        end = f"#{b['to']}.e+{b.get('toPad', 0.4)}"
        if b["kind"] == "QuoteCard":
            inserts.append({"kind": "broll", "from": f"#{b['from']}", "to": end,
                            "overlays": [{"type": "QuoteCard", "props": b["props"]}]})
        elif b["kind"] in ("BigNumber", "Timeline", "Tokens", "NextToken", "Steps"):
            inserts.append({"kind": "broll", "from": f"#{b['from']}", "to": end,
                            "layout": [{"mode": "visual", "visual": {"kind": "graphic", "graphic": b["kind"], "props": b["props"]}}]})

    plan = {
        "id": d.name, "title": args.title or d.name, "palette": args.palette,
        "source": {"video": proj["primary"], "audio": {k: v for k, v in proj["audio"].items() if k != "snr"},
                   "words": str(d / "transcript.words.json"), "cameras": cams},
        "edit": edit, "cut": stumbles, "cutFillers": True, "maxPause": 0.8, "minRun": 1.2,
        "captions": {"fixes": st.get("fixes", {})},
        "chapters": [{"title": c["title"], "at": f"#{c['at']}" + ("@2" if args.teaser and c["at"] == first_main else "")} for c in chapters],
        "inserts": inserts,
        "angles": angles,
        "audience": [{"from": f"#{a}", "to": f"#{b}"} for a, b in st.get("audience", [])],
        "approvedCuts": sorted(approved),
    }
    if args.teaser:
        # The teaser plays some sentences twice; everything but the teaser means the main body.
        import re as _re
        spans = [t for t in st.get("teaser", [])]

        def later(o):
            if isinstance(o, dict):
                return {k: later(v) for k, v in o.items()}
            if isinstance(o, list):
                return [later(x) for x in o]
            if isinstance(o, str):
                m = _re.match(r"^#(\d+)(\.e)?(@[^+-]+)?([+-][\d.]+)?$", o)
                if m and not m.group(3) and any(t["from"] <= int(m.group(1)) <= t["to"] for t in spans):
                    return f"#{m.group(1)}{m.group(2) or ''}@last{m.group(4) or ''}"
            return o
        plan["chapters"], plan["inserts"] = later(plan["chapters"]), later(plan["inserts"])
    (d / "edit.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    kept_s = sum(W[b]["e"] - W[a]["s"] for a, b in keep)
    print(f"edit.json: {len(edit)} ranges, {len(stumbles)} stumble words, {len(chapters)} chapters, {len(inserts)} inserts; "
          f"~{kept_s / 60:.1f} min before filler and pause removal")


if __name__ == "__main__":
    main()
