#!/usr/bin/env python3
"""Synthesize the house sound kit into assets/sfx/ (48 kHz mono WAV, peak -1 dBFS).

Everything is generated, so there is no licence question and nothing to download.
The kit is deliberately quiet and short: sounds that support an edit, never meme
sounds. Levels are applied at mix time (plan "sfx": [{"at", "file", "gain"}]).

  sfx.py            (re)build the kit
  sfx.py --list     names and one-line descriptions
"""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"
rng = np.random.default_rng(7)


def env(n, attack, release, curve=3.0):
    a = int(attack * SR)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a) ** 2 if a else 1
    r = n - a
    e[a:] = (1 - np.linspace(0, 1, r)) ** curve
    return e


def norm(x, peak_db=-1.0):
    return x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)


def sweep_filter(noise, f0, f1, q=1.2):
    """Band-pass noise whose centre glides from f0 to f1 (block-wise biquads)."""
    out = np.zeros_like(noise)
    block = 256
    zi = None
    n = len(noise)
    for i in range(0, n, block):
        u = i / n
        fc = f0 * (f1 / f0) ** u
        b, a = signal.iirpeak(min(fc, SR / 2 - 100), q, SR)
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        out[i:i + block], zi = signal.lfilter(b, a, noise[i:i + block], zi=zi)
    return out


def whoosh(dur=0.45, f0=500, f1=3500, q=0.9, peak=0.55):
    n = int(dur * SR)
    x = sweep_filter(rng.standard_normal(n), f0, f1, q)
    t = np.linspace(0, 1, n)
    shape = np.exp(-((t - peak) ** 2) / 0.045)
    return norm(x * shape)


def tick():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 1850 * t) * np.exp(-t * 90)
    click = rng.standard_normal(n) * np.exp(-t * 900)
    b, a = signal.butter(2, 900, "hp", fs=SR)
    return norm(signal.lfilter(b, a, 0.7 * body + 0.5 * click))


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 420 * np.exp(-t * 28) + 180
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(np.sin(ph) * env(n, 0.002, 0.118, 4))


def thud():
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 95 * np.exp(-t * 7) + 42
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7)
    b, a = signal.butter(2, 400, "lp", fs=SR)
    air = signal.lfilter(b, a, rng.standard_normal(n)) * np.exp(-t * 30) * 0.4
    return norm(body + air)


def riser(dur=1.4):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = sweep_filter(rng.standard_normal(n), 300, 6000, 1.4)
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (t * 2)) / SR) * 0.15
    return norm((x + tone) * t ** 2.2 * env(n, 0.001, 0.02, 1))


def paper():
    n = int(0.32 * SR)
    t = np.linspace(0, 1, n)
    b, a = signal.butter(2, [1800, 7000], "bp", fs=SR)
    x = signal.lfilter(b, a, rng.standard_normal(n))
    grain = 1 + 0.6 * np.sin(2 * np.pi * 38 * t * 0.32)
    return norm(x * grain * np.sin(np.pi * t) ** 1.5)


def marker():
    n = int(0.42 * SR)
    t = np.linspace(0, 1, n)
    b, a = signal.butter(2, [2500, 9000], "bp", fs=SR)
    x = signal.lfilter(b, a, rng.standard_normal(n))
    strokes = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 7 * t))
    return norm(x * strokes * np.sin(np.pi * t) ** 0.8)


KIT = {
    "whoosh-soft": ("soft air whoosh, 0.45 s: hook card, headline, zoom to slide", lambda: whoosh()),
    "whoosh-long": ("slower whoosh, 0.8 s: whip or section change", lambda: whoosh(0.8, 300, 2600, 0.8, 0.5)),
    "tick": ("short tick: chips, list items, counters landing", tick),
    "pop-soft": ("rounded pop: a chip or badge appearing", pop),
    "thud-soft": ("low soft impact: takeover last word, a reveal", thud),
    "riser": ("1.4 s rise into a reveal (ends on it)", riser),
    "paper": ("paper slide: quote card or document card", paper),
    "marker": ("marker scratch: an annotation drawing on a slide", marker),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for k, (d, _) in KIT.items():
            print(f"{k:12s} {d}")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for k, (_, fn) in KIT.items():
        x = fn().astype(np.float32)
        fade = int(0.004 * SR)
        x[-fade:] *= np.linspace(1, 0, fade)
        sf.write(OUT / f"{k}.wav", x, SR)
    print(f"{len(KIT)} sounds -> {OUT}")


if __name__ == "__main__":
    main()
