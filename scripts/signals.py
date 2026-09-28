#!/usr/bin/env python3
"""Timeline signals for a multicam edit, all in picture time.

  signals.py DIR/project.json --out DIR/signals.json [--from S --to S]

speech   who is talking, every 0.25 s: the speaker (the lavalier is loud relative to
         the room) or the audience (the room is loud, the lavalier barely hears it).
         Threshold found per recording (two-cluster split of the level difference).
screen   what the screen recording does, every 0.5 s: `change` (fraction of pixels
         that changed since the last sample), with slide changes (a jump after a
         still stretch) and busy stretches (typing, scrolling, a demo) marked.
The room track is the picture camera's own audio; the lavalier is project.json's audio.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audiosrc import AudioSrc  # noqa: E402

HOP = 0.25


def envelope_db(src, t0, dur, rate=8000):
    x = src.pcm(t0, dur, rate)
    hop = int(HOP * rate)
    n = len(x) // hop
    if n == 0:
        return np.zeros(0)
    fr = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-7)


def two_means(v):
    """Split a 1-D sample into two clusters; return the threshold between them."""
    lo, hi = np.percentile(v, 20), np.percentile(v, 80)
    for _ in range(30):
        t = (lo + hi) / 2
        a, b = v[v < t], v[v >= t]
        if len(a) == 0 or len(b) == 0:
            break
        lo, hi = a.mean(), b.mean()
    return (lo + hi) / 2


def screen_activity(path, offset, t0, dur, fps=2):
    """Fraction of changed pixels between consecutive samples of the screen recording."""
    w, h = 320, 180
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(t0 + offset, 0):.3f}", "-t", f"{dur:.3f}", "-i", path,
           "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)
    ch = np.zeros(len(frames))
    ch[1:] = (np.abs(np.diff(frames, axis=0)) > 12).mean(axis=(1, 2))
    return ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="a", type=float)
    ap.add_argument("--to", dest="b", type=float)
    args = ap.parse_args()
    proj = json.loads(Path(args.project).read_text())
    picture = proj["primary"]
    dur_pic = next(s["duration"] for s in proj["sources"] if s.get("path") == picture)
    lav = AudioSrc({"video": picture, "audio": proj["audio"]})
    room = AudioSrc({"video": picture})
    # Only where the lavalier exists: its file starts later / ends earlier than the picture.
    lav_dur = next((s["duration"] for s in proj["sources"] if s.get("path") == lav.path), dur_pic)
    a = max(args.a or 0.0, -lav.offset if lav.offset < 0 else 0.0)
    b = min(args.b or dur_pic, dur_pic, lav_dur - lav.offset)
    dur = b - a

    lav_db = envelope_db(lav, a, dur)
    room_db = envelope_db(room, a, dur)
    n = min(len(lav_db), len(room_db))
    lav_db, room_db = lav_db[:n], room_db[:n]
    diff = lav_db - room_db
    # The speaker: the lavalier is clearly loud. Learn their usual lav-minus-room level
    # from those moments; the audience is speech the room hears while the lavalier is
    # far below that usual difference.
    lav_speech = two_means(lav_db)                      # valley between lav silence and lav speech
    room_floor = float(np.percentile(room_db, 10))
    loud = lav_db > np.percentile(lav_db[lav_db > lav_speech], 30) if (lav_db > lav_speech).sum() > 20 else lav_db > lav_speech
    spk_diff = float(np.median(diff[loud]))
    thr = spk_diff - 7.0
    room_speech = room_db > room_floor + 9
    who = np.full(n, "silence", dtype=object)
    who[(lav_db > lav_speech) & (diff > thr)] = "speaker"
    who[room_speech & (diff <= thr) & (lav_db < lav_speech + 6)] = "audience"
    # Smooth: a turn lasts at least 0.75 s.
    k = 3
    for i in range(len(who)):
        win = who[max(0, i - k):i + k + 1]
        vals, counts = np.unique(win, return_counts=True)
        who[i] = vals[np.argmax(counts)]
    turns = []
    for i, w in enumerate(who):
        t = a + i * HOP
        if turns and turns[-1]["who"] == w:
            turns[-1]["b"] = round(t + HOP, 2)
        else:
            turns.append({"who": str(w), "a": round(t, 2), "b": round(t + HOP, 2)})
    audience = [t for t in turns if t["who"] == "audience" and t["b"] - t["a"] >= 1.5]

    out = {"from": a, "to": b, "hop": HOP, "threshold": round(float(thr), 2), "speakerDiff": round(spk_diff, 2),
           "speech": [t for t in turns if t["who"] != "silence"], "audience": audience}

    screens = proj.get("screens", [])
    if screens:
        sc = screens[0]
        ch = screen_activity(sc["path"], sc["offset"], a, dur)
        t = a + np.arange(len(ch)) * 0.5
        # A slide change: a jump after at least 2 s of stillness. Busy: sustained change.
        slides, busy = [], []
        still = 0.0
        for i, c in enumerate(ch):
            if c > 0.08 and still >= 2.0:
                slides.append(round(float(t[i]), 2))
            still = still + 0.5 if c < 0.01 else 0.0
        run = None
        for i, c in enumerate(ch):
            on = c > 0.004
            if on and run is None:
                run = [float(t[i]), float(t[i])]
            elif on:
                run[1] = float(t[i])
            elif run is not None:
                if run[1] - run[0] >= 6:
                    busy.append([round(run[0], 1), round(run[1] + 0.5, 1)])
                run = None
        out["screen"] = {"path": sc["path"], "offset": sc["offset"], "slides": slides, "busy": busy}
    Path(args.out).write_text(json.dumps(out))
    spk = sum(t["b"] - t["a"] for t in out["speech"] if t["who"] == "speaker")
    aud = sum(t["b"] - t["a"] for t in audience)
    print(f"{dur / 60:.1f} min analysed: speaker {spk / 60:.1f} min, audience {aud / 60:.1f} min in {len(audience)} turns "
          f"(speaker's lav-minus-room {spk_diff:.1f} dB, audience below {thr:.1f} dB)" + (f"; screen: {len(out['screen']['slides'])} slide changes, "
                                                           f"{len(out['screen']['busy'])} busy stretches" if screens else ""))


if __name__ == "__main__":
    main()
