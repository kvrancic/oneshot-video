#!/usr/bin/env python3
"""Gate clip candidates before anyone sees them.

Resolves each candidate's word ranges to cut points (same logic as edl.py, without
the audio refinement, so it is instant), then prints its exact first and last
sentence, its length, and warnings:

  OPENER   first word is a dangling connective (so, and, but, then, because ...)
  DANGLING a pronoun or "this/that" in the first sentence with nothing before it
  TAIL     last word ends on a comma or connective (the thought is not finished)
  DOUBT    words both ASR models disagreed on (check against context)
  LENGTH   over a platform ceiling for the formats it asks for
  OVERLAP  shares source material with a stronger candidate

  candidates.py DIR/candidates.json [--words DIR/transcript.words.json] [--md DIR/candidates.md]
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from edl import resolve  # noqa: E402

OPENERS = {"so", "and", "but", "then", "also", "because", "however", "anyway", "therefore", "or", "like", "um", "uh", "yeah", "okay"}
PRONOUNS = {"he", "she", "they", "it", "this", "that", "these", "those", "him", "her", "them", "his", "their"}
CEILING = {"9x16": 180, "1x1": 140, "4x5": 180, "16x9": 600}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates")
    ap.add_argument("--words")
    ap.add_argument("--md")
    args = ap.parse_args()

    cpath = Path(args.candidates)
    cands = json.loads(cpath.read_text())
    wpath = Path(args.words) if args.words else cpath.parent / "transcript.words.json"
    W = json.loads(wpath.read_text())["words"]

    def clean(w):
        return re.sub(r"[^\w']", "", w).lower()

    lines_md = ["# Candidates\n"]
    used = {}
    for c in cands:
        segs = resolve(c["edit"], W, None, c.get("cut", []), check_audio=False)
        dur = sum(s["b"] - s["a"] for s in segs)
        idx = [k for s in segs for k in range(s["w"][0], s["w"][1] + 1)]
        text = [W[k]["w"] for k in idx]
        first_end = next((n for n, k in enumerate(idx) if W[k].get("eos")), len(idx) - 1)
        first = " ".join(text[:first_end + 1])
        last_start = max((n + 1 for n, k in enumerate(idx[:-1]) if W[k].get("eos")), default=0)
        last = " ".join(text[last_start:])
        warn = []
        if clean(text[0]) in OPENERS:
            warn.append(f"OPENER '{text[0]}'")
        early = [clean(t) for t in text[:6]]
        if any(p in PRONOUNS for p in early) and not re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", first):
            warn.append("DANGLING? check who/what the first sentence refers to")
        if re.search(r"[,;:]$", text[-1]) or clean(text[-1]) in OPENERS:
            warn.append(f"TAIL ends on '{text[-1]}'")
        doubt = [W[k]["w"] for k in idx if W[k].get("?")]
        if doubt:
            warn.append(f"DOUBT {len(doubt)}: {' '.join(doubt[:8])}")
        for f in c.get("format", ["9x16"]):
            if dur > CEILING.get(f, 600):
                warn.append(f"LENGTH {dur:.0f}s > {CEILING[f]}s for {f}")
        ov = [o for o, ks in used.items() if len(set(ks) & set(idx)) > 0.3 * len(idx)]
        if ov:
            warn.append(f"OVERLAP with {', '.join(ov)}")
        used[c["id"]] = idx
        c["_resolved"] = {"duration": round(dur, 1), "segments": len(segs), "first": first, "last": last, "warnings": warn}

        m, s = divmod(int(round(dur)), 60)
        print(f"\n{c['id']}  {c.get('title', '')}  ({m}:{s:02d}, {len(segs)} segments)")
        print(f"  first: {first}")
        print(f"  last:  {last}")
        for w in warn:
            print(f"  ! {w}")
        lines_md.append(f"## {c['id']}: {c.get('title', '')} ({m}:{s:02d})\n")
        lines_md.append(f"- hook: \"{c.get('hook', first)}\"\n- first: {first}\n- last: {last}\n"
                        + "".join(f"- **{w}**\n" for w in warn) + (f"- why: {c['why']}\n" if c.get("why") else "") + "\n")
    cpath.write_text(json.dumps(cands, indent=2, ensure_ascii=False))
    md = Path(args.md) if args.md else cpath.with_suffix(".md")
    md.write_text("".join(lines_md))
    print(f"\n{len(cands)} candidates -> {md}")


if __name__ == "__main__":
    main()
