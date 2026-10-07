#!/usr/bin/env python3
"""Music timing for from-scratch films: the beat grid, cut points on transients, the song edit.

  beats.py track SONG --out beats.json [--bpm 120]        tempo and every beat time (numpy/scipy, no librosa)
  beats.py transient SONG --at 28.45 [--window 0.06]      the drum hit nearest a time (steepest rise of high-passed energy)
  beats.py onset SONG --near 36.2 [--band 300-3400]       a vocal onset near a time (sung words: whisper's times are off by 1 s or more)
  beats.py splice SONG --keep 0-28.446 45.039-63.2 --out music_edit.wav [--beats beats.json]
                                                          cut the song into an edit, each seam on a transient, 6 ms crossfades;
                                                          with --beats, writes the beat grid in edit time (one list per part)

Plan seams an exact number of bars apart (a 40-beat jump is a clean cut; a 41-beat one stumbles), then
check the seam: track the edit again and the beat interval must stay even across it.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks

SR = 22050
HOP = 256


def load(path, sr=SR, start=None, dur=None):
    cmd = ["ffmpeg", "-v", "error", *(["-ss", str(start)] if start is not None else []), "-i", str(path),
           *(["-t", str(dur)] if dur is not None else []), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def flux(x):
    """Spectral flux onset strength, one value per HOP samples."""
    n = 2048
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(x, (n // 2, n // 2)), n)[::HOP] * np.hanning(n)
    mag = np.log1p(10 * np.abs(np.fft.rfft(frames, axis=1)))
    d = np.maximum(np.diff(mag, axis=0, prepend=mag[:1]), 0).sum(axis=1)
    d -= np.convolve(d, np.ones(16) / 16, mode="same")  # remove the slow level so quiet and loud parts count alike
    return np.maximum(d, 0)


def tempo(env, lo=70, hi=180, prior=None):
    fr = SR / HOP
    ac = np.correlate(env - env.mean(), env - env.mean(), mode="full")[len(env) - 1:]
    lags = np.arange(int(fr * 60 / hi), int(fr * 60 / lo) + 1)
    score = ac[lags] * (np.exp(-0.5 * (np.log2(60 * fr / lags / prior)) ** 2 / 0.1) if prior else 1)
    lag = lags[np.argmax(score)]
    # parabolic refinement of the peak
    if 1 <= lag - lags[0] < len(lags) - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        lag = lag + 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else lag
    return 60 * fr / lag


def track_beats(env, bpm, tight=100.0):
    """Dynamic-programming beat tracker (Ellis 2007): beats on strong onsets, spaced near the period."""
    fr = SR / HOP
    period = 60 * fr / bpm
    score = env / (env.std() or 1)
    best = score.copy()
    back = -np.ones(len(env), int)
    lo, hi = int(round(period / 2)), int(round(period * 2))
    for t in range(hi, len(env)):
        prev = np.arange(t - hi, t - lo + 1)
        cost = -tight * np.log((t - prev) / period) ** 2
        k = np.argmax(best[prev] + cost)
        best[t] = score[t] + best[prev[k]] + cost[k]
        back[t] = prev[k]
    t = int(np.argmax(best[-hi:]) + len(env) - hi)
    beats = []
    while t >= 0:
        beats.append(t)
        t = back[t]
    return np.array(beats[::-1]) / fr


def highpassed_energy(x, sr, cutoff=4000):
    hp = sosfiltfilt(butter(4, cutoff, "highpass", fs=sr, output="sos"), x)
    win = max(1, int(sr * 0.002))
    return np.convolve(hp ** 2, np.ones(win) / win, mode="same")


def transient_near(path, t, window=0.06):
    sr = 48000
    a = max(0.0, t - window)
    x = load(path, sr, a, 2 * window)
    e = np.log10(highpassed_energy(x, sr) + 1e-10)
    rise = np.diff(e[:: int(sr * 0.001)])  # per millisecond
    return a + (np.argmax(rise) + 1) / 1000.0


def band_onset(path, near, band=(300, 3400), window=0.6):
    sr = 16000
    a = max(0.0, near - window)
    x = load(path, sr, a, 2 * window)
    y = sosfiltfilt(butter(4, band, "bandpass", fs=sr, output="sos"), x)
    rms = np.sqrt(np.convolve(y ** 2, np.ones(int(sr * 0.02)) / int(sr * 0.02), mode="same"))
    db = 20 * np.log10(rms + 1e-9)
    peaks, props = find_peaks(np.diff(db[:: int(sr * 0.005)]), prominence=0.5)
    if not len(peaks):
        return near
    k = peaks[np.argmax(props["prominences"])]
    return a + (k + 1) * 0.005


def cmd_track(args):
    x = load(args.song)
    env = flux(x)
    bpm = tempo(env, prior=args.bpm)
    beats = track_beats(env, bpm)
    onsets = np.flatnonzero((env[1:-1] > env[:-2]) & (env[1:-1] >= env[2:]) & (env[1:-1] > env.mean() + 2 * env.std())) + 1
    out = {"tempo": round(float(bpm), 2), "period": round(60 / bpm, 4), "beats": [round(float(b), 3) for b in beats],
           "onsets": [round(float(o) * HOP / SR, 3) for o in onsets]}
    Path(args.out).write_text(json.dumps(out))
    iv = np.diff(beats)
    print(f"{args.out}: {bpm:.1f} BPM ({60 / bpm:.3f} s), {len(beats)} beats from {beats[0]:.2f} s; interval sd {iv.std() * 1000:.0f} ms")


def cmd_splice(args):
    parts = [tuple(float(v) for v in k.split("-")) for k in args.keep]
    snapped = [(transient_near(args.song, a) if a > 0 else 0.0, transient_near(args.song, b) if args.snap_ends or k < len(parts) - 1 else b)
               for k, (a, b) in enumerate(parts)]
    tmp = Path(args.out).with_suffix(".parts")
    tmp.mkdir(exist_ok=True)
    files = []
    for k, (a, b) in enumerate(snapped):
        f = tmp / f"p{k}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.song, "-af", f"atrim={a:.6f}:{b:.6f},asetpts=N/SR/TB", "-ar", "48000", "-ac", "2", str(f)], check=True)
        files.append(f)
    if len(files) == 1:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", files[0], "-c:a", "pcm_s16le", args.out], check=True)
    else:
        inputs = sum((["-i", str(f)] for f in files), [])
        chain, last = [], "[0]"
        for k in range(1, len(files)):
            lab = f"[x{k}]"
            chain.append(f"{last}[{k}]acrossfade=d=0.006:c1=tri:c2=tri{lab}")
            last = lab
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", last, "-c:a", "pcm_s16le", args.out], check=True)
    for f in files:
        f.unlink()
    tmp.rmdir()
    print(f"{args.out}")
    t = 0.0
    seams = []
    for k, (a, b) in enumerate(snapped):
        print(f"  part {k}: song {a:.3f}-{b:.3f} -> edit {t:.3f}-{t + b - a:.3f}" + (f"  (asked {parts[k][0]:.3f}-{parts[k][1]:.3f})" if (a, b) != parts[k] else ""))
        seams.append((a, b, t))
        t += b - a - (0.006 if k < len(snapped) - 1 else 0)
    if args.beats:
        grid = json.loads(Path(args.beats).read_text())["beats"]
        edit = [[round(bt - a + off, 3) for bt in grid if a <= bt < b] for a, b, off in seams]
        bp = Path(args.out).with_suffix(".beats.json")
        bp.write_text(json.dumps({"parts": edit, "seams": [round(s[2], 3) for s in seams[1:]]}))
        print(f"  beat grid in edit time -> {bp} ({', '.join(str(len(p)) for p in edit)} beats per part)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("track")
    p.add_argument("song")
    p.add_argument("--out", required=True)
    p.add_argument("--bpm", type=float, help="expected tempo, to break half/double ambiguity")
    p = sp.add_parser("transient")
    p.add_argument("song")
    p.add_argument("--at", type=float, required=True)
    p.add_argument("--window", type=float, default=0.06)
    p = sp.add_parser("onset")
    p.add_argument("song")
    p.add_argument("--near", type=float, required=True)
    p.add_argument("--band", default="300-3400")
    p = sp.add_parser("splice")
    p.add_argument("song")
    p.add_argument("--keep", nargs="+", required=True, help="song ranges a-b in seconds, in playing order")
    p.add_argument("--out", required=True)
    p.add_argument("--beats", help="beats.json of the song, remapped to edit time")
    p.add_argument("--snap-ends", action="store_true", help="snap the last part's end to a transient too")
    args = ap.parse_args()
    if args.cmd == "track":
        cmd_track(args)
    elif args.cmd == "transient":
        print(f"{transient_near(args.song, args.at, args.window):.4f}")
    elif args.cmd == "onset":
        lo, hi = (float(v) for v in args.band.split("-"))
        print(f"{band_onset(args.song, args.near, (lo, hi)):.3f}")
    else:
        cmd_splice(args)


if __name__ == "__main__":
    sys.exit(main())
