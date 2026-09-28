#!/usr/bin/env python3
"""Resolve a plan's edit (word ranges) into frame-safe source cut points.

Claude never writes timestamps. A plan's "edit" lists word-index ranges from the
transcript ([#index] in transcript.txt); this script turns them into cuts:

  head: just before the first word, at the quietest point of the gap before it
  tail: after the last word has rung out, at the quietest point of the gap after it
  pauses inside a range longer than --max-pause are cut out (a jump cut the camera
  hides with its alternating cut zoom); "keepPauses": true on a part keeps them.

Writes plan["segments"] = [{a, b, w: [first, last]}] and prints the edit as text so
every head and tail can be read before anything renders.

Top-level "cut": [word indices] removes those words from the audio (fillers, a
stumble); captions.drop only hides words from the captions.

  edl.py clip/plan.json [--words work/<key>/transcript.words.json] [--max-pause 0.7]
"""
import argparse, json, re, subprocess
from pathlib import Path

import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audiosrc import AudioSrc  # noqa: E402

SR = 16000


def rms_window(src, t0, t1):
    """RMS envelope (10 ms hops) of the audio between t0 and t1 (picture time).
    `src` is an AudioSrc or a file path."""
    t0 = max(t0, 0)
    if isinstance(src, AudioSrc):
        a = src.pcm(t0, t1 - t0, SR)
    else:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", src, "-vn", "-ac", "1",
                              "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.float32)
    hop = SR // 100
    if len(a) < hop * 2:
        return t0, np.zeros(1)
    frames = np.lib.stride_tricks.sliding_window_view(a, hop * 2)[::hop]
    return t0, 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)


def quietest(src, lo, hi, prefer):
    """Quietest 10 ms point in [lo, hi], biased toward `prefer`."""
    if hi - lo < 0.04:
        return (lo + hi) / 2
    t0, db = rms_window(src, lo, hi)
    ts = t0 + np.arange(len(db)) * 0.01 + 0.01
    penalty = np.abs(ts - prefer) * 6  # dB per second away from the preferred point
    return float(ts[int(np.argmin(db + penalty))])


def gap_is_quiet(src, lo, hi, floor_db):
    """True when the audio between lo and hi is really a pause (word times can be off;
    a cut must never remove speech)."""
    if hi - lo < 0.05:
        return True
    _, db = rms_window(src, lo, hi)
    return float((db > floor_db + 7).mean()) < 0.12


def noise_floor(src, lo, hi):
    _, db = rms_window(src, lo, min(hi, lo + 60))
    return float(np.percentile(db, 15))


FILLER_WORDS = {"um", "uh", "uhm", "erm", "er", "ah", "hmm", "mm", "mhm"}


def merge_short(runs, W, min_run, max_gap=1.6):
    """Smoothness: a run shorter than min_run that was split off only by a pause or a
    filler (no cut word between) rejoins its neighbour, keeping the natural pause. A lone
    'But' followed by a cut sounds broken; the same 'But' and a breath sounds human."""
    if min_run <= 0:
        return runs
    changed = True
    while changed:
        changed = False
        for k in range(len(runs)):
            r0, r1 = runs[k]
            if W[r1]["e"] - W[r0]["s"] >= min_run:
                continue
            nxt = k + 1 < len(runs) and runs[k + 1][0] == r1 + 1 and W[runs[k + 1][0]]["s"] - W[r1]["e"] <= max_gap
            prv = k > 0 and runs[k - 1][1] == r0 - 1 and W[r0]["s"] - W[runs[k - 1][1]]["e"] <= max_gap
            if nxt:
                runs[k] = [r0, runs[k + 1][1]]
                del runs[k + 1]
            elif prv:
                runs[k - 1] = [runs[k - 1][0], r1]
                del runs[k]
            else:
                continue
            changed = True
            break
    return runs


def resolve(edit, W, src, cuts=(), max_pause=0.7, lead=0.10, tail=0.22, check_audio=True, fillers=(), min_run=0.0):
    """Word-range parts -> [{a, b, w}] source cut points (see module docstring).
    `fillers` are (start, end) times of fillers the word list does not contain (Parakeet
    hears "uh" where Whisper writes nothing); a gap holding one is always cut."""
    cuts = set(cuts)
    fill = sorted((float(f["s"]), float(f["e"])) for f in fillers)
    segs = []
    for part in edit:
        i, j = part["words"]
        keep = part.get("keepPauses", False)
        maxp = part.get("maxPause", max_pause)
        # Split the range wherever the speaker paused longer than max-pause.
        runs = [[i, i]]
        floor = None
        for k in range(i, j):
            gap = W[k + 1]["s"] - W[k]["e"]
            has_filler = any(W[k]["e"] - 0.05 <= fs and fe <= W[k + 1]["s"] + 0.05 for fs, fe in fill) if fill else False
            if k + 1 in cuts:
                runs.append([k + 1, k + 1])
            elif has_filler and not keep:
                runs.append([k + 1, k + 1])
            elif not keep and gap > maxp and k not in cuts:
                if check_audio:
                    if floor is None:
                        floor = noise_floor(src, W[i]["s"], W[j]["e"])
                    if not gap_is_quiet(src, W[k]["e"] + 0.08, W[k + 1]["s"] - 0.08, floor):
                        runs[-1][1] = k + 1
                        continue
                runs.append([k + 1, k + 1])
            else:
                runs[-1][1] = k + 1
        # Words listed in "cut" come out of the audio; drop runs made only of them.
        split = []
        for r0, r1 in runs:
            cur = None
            for k in range(r0, r1 + 1):
                if k in cuts:
                    if cur:
                        split.append(cur)
                    cur = None
                elif cur is None:
                    cur = [k, k]
                else:
                    cur[1] = k
            if cur:
                split.append(cur)
        split = merge_short(split, W, part.get("minRun", min_run))
        for r0, r1 in split:
            prev_e = W[r0 - 1]["e"] if r0 > 0 else W[r0]["s"] - 1.0
            next_s = W[r1 + 1]["s"] if r1 + 1 < len(W) else W[r1]["e"] + 1.0
            a_lo = max(prev_e + 0.03, W[r0]["s"] - 0.45)
            a_hi = W[r0]["s"] - 0.02
            b_lo = W[r1]["e"] + 0.06
            b_hi = min(next_s - 0.04, W[r1]["e"] + 0.6)
            if check_audio:
                a = quietest(src, a_lo, a_hi, W[r0]["s"] - lead) if a_hi > a_lo else W[r0]["s"] - 0.02
                b = quietest(src, b_lo, b_hi, W[r1]["e"] + tail) if b_hi > b_lo else max(W[r1]["e"], next_s - 0.04)
            else:
                a = max(a_lo, W[r0]["s"] - lead) if a_hi > a_lo else W[r0]["s"] - 0.02
                b = min(b_hi, W[r1]["e"] + tail) if b_hi > b_lo else max(W[r1]["e"], next_s - 0.04)
            segs.append({"a": round(a, 3), "b": round(b, 3), "w": [r0, r1]})
    return segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--words")
    ap.add_argument("--max-pause", type=float, default=0.7)
    ap.add_argument("--lead", type=float, default=0.10)
    ap.add_argument("--tail", type=float, default=0.22)
    ap.add_argument("--cut-fillers", action="store_true", help="also cut um/uh (full edits; plan \"cutFillers\": true)")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text())
    words_path = Path(args.words or plan["source"]["words"]).expanduser()
    if not words_path.is_absolute():
        for base in [plan_path.parent, plan_path.parent.parent.parent, Path.cwd(), Path(__file__).resolve().parent.parent]:
            if (base / words_path).exists():
                words_path = base / words_path
                break
    W = json.loads(words_path.read_text())["words"]
    src = AudioSrc(plan["source"])
    fixes = {int(k): v for k, v in plan.get("captions", {}).get("fixes", {}).items()}
    drop = set(plan.get("captions", {}).get("drop", []))

    def text(i, j):
        return " ".join(fixes.get(k, W[k]["w"]) for k in range(i, j + 1) if k not in drop and fixes.get(k, W[k]["w"]))

    wdata = json.loads(words_path.read_text())
    cut_fillers = args.cut_fillers or plan.get("cutFillers", False)
    cuts = set(plan.get("cut", []))
    if cut_fillers:
        cuts |= {w["i"] for w in W if re.sub(r"[^a-z]", "", w["w"].lower()) in FILLER_WORDS}
    segs = resolve(plan["edit"], W, src, cuts, plan.get("maxPause", args.max_pause), args.lead, args.tail,
                   fillers=wdata.get("fillers", []) if cut_fillers else (), min_run=plan.get("minRun", 0.0))
    plan["segments"] = segs
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))

    t = 0.0
    print(f"{'edit':>7}  {'source':>17}  {'dur':>5}  text")
    for s in segs:
        d = s["b"] - s["a"]
        print(f"{t:7.2f}  {s['a']:8.2f}-{s['b']:8.2f}  {d:5.2f}  {text(*s['w'])}")
        t += d
    heads = [W[s["w"][0]]["w"] for s in segs]
    weak = [h for h in heads[:1] if re.sub(r"\W", "", h).lower() in {"so", "and", "but", "or", "because", "like", "um", "uh"}]
    print(f"\n{len(segs)} segments, {t:.1f}s" + (f"  (opens on '{weak[0]}': consider starting one word later)" if weak else ""))


if __name__ == "__main__":
    main()
