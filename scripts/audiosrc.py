"""Where a clip's sound comes from.

The picture and the sound are chosen separately: the sharpest camera is rarely the one
with the microphone. A plan's `source.audio` is either absent (use the picture file's
audio), a path (same timeline), or

  {"path": "...", "stream": 0, "offset": -76.29, "drift": -1.7e-5, "ref": 1800}

meaning: audio_time = picture_time + offset + drift * (picture_time - ref).
"""
import json
import subprocess
from pathlib import Path


class AudioSrc:
    def __init__(self, plan_source):
        a = plan_source.get("audio")
        if not a:
            a = {"path": plan_source["video"]}
        elif isinstance(a, str):
            a = {"path": a}
        self.path = str(Path(a["path"]).expanduser())
        self.stream = a.get("stream")
        self.offset = float(a.get("offset", 0.0))
        self.drift = float(a.get("drift", 0.0))
        self.ref = float(a.get("ref", 0.0))

    def t(self, picture_time):
        """Picture timeline seconds -> seconds in the audio file."""
        return picture_time + self.offset + self.drift * (picture_time - self.ref)

    def map_args(self):
        return ["-map", f"0:a:{self.stream}"] if self.stream is not None else ["-vn"]

    def extract(self, t0, dur, out, rate=16000, channels=1, extra_filters=None):
        """Cut [t0, t0 + dur] (picture time) from the audio source into `out`."""
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(self.t(t0), 0):.3f}", "-t", f"{dur:.3f}", "-i", self.path,
               *self.map_args(), "-ac", str(channels), "-ar", str(rate)]
        if extra_filters:
            cmd += ["-af", extra_filters]
        subprocess.run(cmd + [str(out)], check=True)

    def pcm(self, t0, dur, rate=16000):
        """Mono float32 samples of [t0, t0 + dur] (picture time)."""
        import numpy as np

        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(self.t(t0), 0):.3f}", "-t", f"{dur:.3f}", "-i", self.path,
                              *self.map_args(), "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32)

    def to_json(self):
        return json.dumps({"path": self.path, "stream": self.stream, "offset": self.offset, "drift": self.drift, "ref": self.ref})


def snr_db(x, rate=16000):
    """Speech level (90th percentile of 50 ms RMS) minus the noise floor (10th percentile)."""
    import numpy as np

    hop = int(0.05 * rate)
    if len(x) < hop * 4:
        return 0.0
    fr = x[: len(x) // hop * hop].reshape(-1, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    return float(np.percentile(db, 90) - np.percentile(db, 10))
