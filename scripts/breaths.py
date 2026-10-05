#!/usr/bin/env python3
"""Turn down breaths and the hiss between phrases (a speaker on a PA, a close lavalier).

  breaths.py SOURCE --words DIR/transcript.words.json --out DIR/voice-debreath.wav
             [--stream 0] [--from S --to S] [--depth 14] [--min-gap 0] [--fade 0.03] [--report DIR/breaths.json]

Ducking every gap between words leaves audible holes in fluent speech (the speaker heard "a weird
silence between each two words"); on a PA, use --min-gap 0.45 --depth 7 --tail 0.2 --fade 0.08 so
only the breaths between phrases go down and the words keep their room.

Writes the whole source audio (48 kHz, its own clock) so it can replace the audio source in
project.json. Every gap between two words (from the transcript) is lowered by --depth dB,
from 120 ms after the last word (its natural tail stays) to 40 ms before the next one, with
30 ms fades: inhales, lip noise and PA hiss go, the words keep their room. A gap that holds
something of its own (laughter, an answer from the room, applause: loud for most of a gap
longer than 0.9 s) is left alone and listed in the report as a reaction, so the editor can
keep its pause.
"""
import argparse, json, subprocess
import numpy as np
import soundfile as sf

SR = 48000
HOP = 480        # 10 ms frames for the level


def load(src, stream):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-map", f"0:a:{stream}", "-ac", "2", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--words", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stream", type=int, default=0)
    ap.add_argument("--from", dest="a", type=float, default=0)
    ap.add_argument("--to", dest="b", type=float, default=1e9)
    ap.add_argument("--depth", type=float, default=14)
    ap.add_argument("--tail", type=float, default=0.12)
    ap.add_argument("--min-gap", type=float, default=0.0, help="only gaps at least this long (s): short gaps between words stay untouched")
    ap.add_argument("--fade", type=float, default=0.03, help="fade length in seconds")
    ap.add_argument("--report")
    args = ap.parse_args()
    x = load(args.source, args.stream)
    mono = x.mean(1)
    n = len(mono) // HOP
    lvl = 10 * np.log10((mono[:n * HOP].reshape(n, HOP) ** 2).mean(1) + 1e-12)
    W = [w for w in json.load(open(args.words))["words"] if w["e"] > w["s"] and args.a <= w["s"] <= args.b]
    sp = np.zeros(n, bool)
    for w in W:
        sp[int(w["s"] * 100):int(w["e"] * 100) + 1] = True
    speech_med = np.median(lvl[sp])
    floor = np.percentile(lvl[int(args.a * 100):int(min(args.b, n / 100) * 100)], 5)
    g = np.ones(len(mono))
    lo = 10 ** (-args.depth / 20)
    ducked, reactions = [], []
    for k in range(len(W) - 1):
        a, b = W[k]["e"] + args.tail, W[k + 1]["s"] - 0.04
        if b - a < 0.08 or W[k + 1]["s"] - W[k]["e"] < args.min_gap:
            continue
        seg = lvl[int(a * 100):int(b * 100)]
        loud = (seg > floor + 0.5 * (speech_med - floor)).mean() if len(seg) else 0
        if W[k + 1]["s"] - W[k]["e"] > 0.9 and loud > 0.45:
            reactions.append({"from": round(W[k]["e"], 2), "to": round(W[k + 1]["s"], 2), "after": W[k]["i"],
                              "loud": round(float(loud), 2)})
            continue
        g[int(a * SR):int(b * SR)] = lo
        ducked.append(b - a)
    k = int(args.fade * SR)
    cs = np.concatenate([[0.0], np.cumsum(g)])
    sm = (cs[k:] - cs[:-k]) / k
    g = np.concatenate([np.full(k // 2, sm[0]), sm, np.full(len(g) - len(sm) - k // 2, sm[-1])]).astype(np.float32)
    sf.write(args.out, x * g[:, None], SR, subtype="PCM_24")
    if args.report:
        json.dump({"speechMedianDb": round(float(speech_med), 1), "floorDb": round(float(floor), 1),
                   "ducked": len(ducked), "duckedSeconds": round(sum(ducked), 1), "reactions": reactions},
                  open(args.report, "w"), indent=1)
    print(f"gaps ducked {args.depth:.0f} dB: {len(ducked)} ({sum(ducked):.1f} s); reactions kept: {len(reactions)} -> {args.out}")


if __name__ == "__main__":
    main()
