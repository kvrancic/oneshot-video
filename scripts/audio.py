#!/usr/bin/env python3
"""Build the clip's voice track from the plan's segments.

Sound comes from `source.audio` (the microphone, when there is one; see audiosrc.py),
cut on the edit timeline with tiny fades so joins never click, then cleaned. With
`--clean auto` (the default) the chain is chosen from the measured signal-to-noise
ratio of the joined voice:

  >= 24 dB  light:  high-pass, gentle FFT denoise, compression (a lavalier, a studio)
  14-24 dB  strong: more denoise, presence lift (a phone near the speaker)
  < 14 dB   rnn:    RNNoise (ffmpeg arnndn) blended with the dry signal, then strong
                    (a phone in a hall, audience noise)

Everything ends at -16 LUFS; the final mix is brought to the platform target later.
If the audio source is a different recording, the sync offset is refined around this
clip first (sub-frame, by cross-correlating 30 s against the picture's own audio).

  audio.py --plan clip/plan.json --out clip/voice.wav [--clean auto|off|light|strong|rnn]
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audiosrc import AudioSrc, snr_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RNN = ROOT / "models" / "rnnoise-sh.rnnn"
CHAINS = {
    "off": "anull",
    "light": "highpass=f=80,afftdn=nr=8:nf=-40:tn=1,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2",
    "strong": "highpass=f=90,afftdn=nr=16:nf=-35:tn=1,equalizer=f=3200:t=q:w=1.2:g=2,"
              "acompressor=threshold=-24dB:ratio=3.5:attack=5:release=100:makeup=3",
}
CHAINS["rnn"] = (f"highpass=f=90,arnndn=m='{RNN}':mix=0.85," + CHAINS["strong"].split(",", 1)[1]) if RNN.exists() else CHAINS["strong"]


def refine_offset(src, plan):
    """Re-measure the audio offset around this clip (drift and a coarse global sync
    both leave tens of milliseconds, which karaoke captions show)."""
    if src.path == str(Path(plan["source"]["video"]).expanduser()):
        return
    from ingest import sync

    segs = plan["segments"]
    mid = sorted(s["a"] for s in segs)[len(segs) // 2]
    guess = src.t(mid) - mid
    off, conf = sync(plan["source"]["video"], src.path, probe_at=max(mid - 15, 0), probe_len=30, search=1.5, guess=guess)
    if off is not None and conf > 0.12:
        src.offset += off - guess
        print(f"  audio offset refined at {mid:.0f}s: {off:+.3f}s (confidence {conf:.2f})")


def chain_delay(dry, wet, sr=48000, max_ms=250):
    """Samples by which the cleaning chain delays the voice. afftdn holds back about 25 ms and
    the RNN chain about 35 ms, and ffmpeg does not compensate; measured on the speech itself
    by cross-correlating 30 s of dry and cleaned signal."""
    import numpy as np
    import soundfile as sf

    x, _ = sf.read(dry, dtype="float32", always_2d=True)
    y, _ = sf.read(wet, dtype="float32", always_2d=True)
    x, y = x.mean(axis=1), y.mean(axis=1)
    total = min(len(x), len(y))
    n = min(total, 30 * sr)
    a = max(0, min(total // 3, total - n))
    x, y = x[a:a + n], y[a:a + n]
    size = 1 << int(np.ceil(np.log2(2 * n)))
    cc = np.fft.irfft(np.fft.rfft(y, size) * np.conj(np.fft.rfft(x, size)), size)
    return int(np.argmax(cc[:int(sr * max_ms / 1000)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--clean", default="auto", choices=["auto", *CHAINS])
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    src = AudioSrc(plan["source"])
    refine_offset(src, plan)
    tmp = Path(tempfile.mkdtemp(prefix="cutroom-audio-"))
    parts = []
    fade = 0.012
    for k, s in enumerate(plan["segments"]):
        d = s["b"] - s["a"]
        p = tmp / f"s{k:03d}.wav"
        src.extract(s["a"], d, p, rate=48000, extra_filters=f"afade=t=in:d={fade},afade=t=out:st={max(d - fade, 0):.3f}:d={fade}")
        parts.append(p)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = tmp / "joined.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)], check=True)

    clean = args.clean
    if clean == "auto":
        import soundfile as sf

        x, sr = sf.read(joined, dtype="float32")
        snr = snr_db(x, sr)
        clean = "light" if snr >= 24 else "strong" if snr >= 14 else "rnn"
        print(f"  voice SNR {snr:.1f} dB -> clean={clean}")
    chain = CHAINS[clean] + ",loudnorm=I=-16:TP=-1.5:LRA=11"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-af", chain, "-ar", "48000", "-ac", "1", args.out], check=True)
    lag = chain_delay(joined, args.out)
    if lag:
        import numpy as np
        import soundfile as sf

        y, sr = sf.read(args.out, dtype="float32")
        sf.write(args.out, np.concatenate([y[lag:], np.zeros(lag, np.float32)]), sr, subtype="PCM_16")
        print(f"  cleaning delay {lag / 48:.1f} ms trimmed")
    print(f"voice -> {args.out} ({sum(s['b'] - s['a'] for s in plan['segments']):.1f}s, {len(parts)} segments, "
          f"source {Path(src.path).name}{'' if src.stream is None else f' stream {src.stream}'}, clean={clean})")


if __name__ == "__main__":
    main()
