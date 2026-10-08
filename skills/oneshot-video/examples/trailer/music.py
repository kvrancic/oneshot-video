# The trailer's music: 128 BPM, original and synthesized (no licence). Sections follow the beat sheet:
# bars 0-1 pad (cold open) · bar 2 roll into the drop · bars 3-10 groove · bars 11-14 silent (the opener plays
# its own song) · bar 15 build · hit at bar 16 (30.0 s) · payoff groove · tail.
import sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
SR = 48000; BPM = 128; B = 60 / BPM; BAR = 4 * B; T = 34.0; N = int(SR * T)
L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(11)
def add(x, t, gl=1.0, gr=None):
    i = int(t * SR); j = min(N, i + len(x))
    if i < N: L[i:j] += x[:j - i] * gl; R[i:j] += x[:j - i] * (gl if gr is None else gr)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def env(n, k): return np.exp(-np.arange(n) / SR * k)
def kick():
    n = int(0.4 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(48 + 140 * np.exp(-t * 32)) / SR) * env(n, 7.5) * 1.0
def clap(): n = int(0.22 * SR); return bp(rng.standard_normal(n), 1000, 5000) * env(n, 24) * 0.55
def hat(o=False):
    n = int((0.16 if o else 0.045) * SR)
    return sosfilt(butter(4, 7500, "highpass", fs=SR, output="sos"), rng.standard_normal(n)) * env(n, 13 if o else 80) * 0.2
def saw(f, dur, cut, det=(0.995, 1, 1.005)):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(((t * f * d) % 1 * 2 - 1) for d in det) / len(det)
    x = sosfilt(butter(2, cut, "lowpass", fs=SR, output="sos"), x)
    return x * np.minimum(1, t / 0.008) * np.minimum(1, (dur - t) / 0.04)
roots = {"E": 41.2, "C": 32.7, "G": 49.0, "D": 36.71}
chords = {"E": [164.8, 196.0, 246.9], "C": [130.8, 164.8, 196.0], "G": [196.0, 246.9, 293.7], "D": [146.8, 185.0, 220.0]}
prog = ["E", "C", "G", "D"]
groove_bars = list(range(3, 11)) + [16, 17]
for bar in range(19):
    t0 = bar * BAR; ch = prog[bar % 4]
    if 11 <= bar <= 14: continue
    pad = sum(saw(f, BAR, 900 if bar < 3 else 1800) for f in chords[ch]) / 3 * 0.09
    pump = 1 - 0.55 * np.exp(-((np.arange(len(pad)) / SR) % B) * 9) if bar in groove_bars else 1
    add(pad * pump, t0, 1.0, 0.92)
    for b in range(4):
        tb = t0 + b * B
        if bar in groove_bars:
            add(kick(), tb)
            if b in (1, 3): add(clap(), tb, 0.85, 1.0)
            add(saw(roots[ch] * (2 if b % 2 else 1), B * 0.4, 600) * 0.4, tb + 0.5 * B)
            add(saw(roots[ch] * 4, B * 0.18, 1400) * 0.12, tb + 0.75 * B)
        if bar >= 2 and bar not in (15,):
            add(hat(False), tb + 0.5 * B, 0.6, 0.75); add(hat(b == 3), tb + 0.25 * B, 0.4, 0.3)
    if bar in (2, 15):  # roll and riser into the next downbeat
        for k in range(16): add(clap() * (0.25 + 0.75 * k / 16), t0 + k * B / 4)
        n = int(BAR * SR); t = np.arange(n) / SR
        add(bp(rng.standard_normal(n), 300, 7000) * (t / BAR) ** 2.5 * 0.4, t0)
for hit in (3 * BAR, 16 * BAR):  # the drop and the payoff
    n = int(2.2 * SR); t = np.arange(n) / SR
    add(np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t * 10)) / SR) * np.exp(-t * 2.4) * 1.1, hit)
    add(bp(rng.standard_normal(int(1.2 * SR)), 2000, 12000) * env(int(1.2 * SR), 3) * 0.25, hit)
fade = np.ones(N); i = int(32.8 * SR); fade[i:] = np.linspace(1, 0, N - i)
mix = np.stack([L * fade, R * fade], 1); mix /= np.abs(mix).max() / 0.89
sf.write(sys.argv[1], mix, SR, subtype="PCM_24")
