# The trailer's music and 8-bit sound effects, synthesized (no licence). 128 BPM chiptune: pulse-wave
# lead and arps, a triangle bass, noise drums. Sections follow src/timing.ts bar by bar.
import sys, os
import numpy as np, soundfile as sf
SR = 48000; BPM = 128; B = 60 / BPM; BAR = 4 * B; T = 40.0; N = int(SR * T)
L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(7)
def add(x, t, gl=1.0, gr=None):
    i = int(round(t * SR)); j = min(N, i + len(x))
    if 0 <= i < N: L[i:j] += x[:j - i] * gl; R[i:j] += x[:j - i] * (gl if gr is None else gr)
def hz(n): return 440 * 2 ** ((n - 69) / 12)
def env(n, a=0.004, d=0.0, r=0.03):
    t = np.arange(n) / SR; dur = n / SR
    e = np.minimum(1, t / a) * np.minimum(1, (dur - t) / r).clip(0)
    return e * (np.exp(-t * d) if d else 1)
def pulse(n_, dur, duty=0.25, vib=0.0, d=0.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(n_) * (1 + vib * np.sin(2 * np.pi * 6 * t) * np.minimum(1, t / 0.15))
    ph = np.cumsum(f) / SR % 1
    return np.where(ph < duty, 1.0, -1.0) * env(n, d=d)
def tri(n_, dur, d=0.0):
    n = int(dur * SR); ph = np.cumsum(np.full(n, hz(n_))) / SR % 1
    x = 4 * np.abs(ph - 0.5) - 1
    return np.round(x * 8) / 8 * env(n, d=d)  # 4-bit stepped like the NES
def noise(dur, d, lp=1.0):
    n = int(dur * SR); x = rng.choice([-1.0, 1.0], n)
    step = max(1, int(1 / lp)); x = np.repeat(x[::step], step)[:n]
    return x * env(n, a=0.001, d=d)
def kick():
    n = int(0.22 * SR); t = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * np.cumsum(55 + 300 * np.exp(-t * 40)) / SR)) * np.exp(-t * 18) * 0.9
def snare(): return noise(0.18, 22, 0.5) * 0.5
def hat(): return noise(0.04, 90) * 0.18

# A minor: Am F C G, one chord per bar
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOT = [45, 41, 36, 43]
LEAD = [  # (beat, note, beats) per 4-bar phrase
    (0, 76, 1), (1, 74, 0.5), (1.5, 72, 0.5), (2, 74, 1), (3, 76, 1),
    (4, 77, 1.5), (5.5, 76, 0.5), (6, 72, 2),
    (8, 72, 1), (9, 74, 0.5), (9.5, 76, 0.5), (10, 79, 1.5), (11.5, 76, 0.5),
    (12, 74, 1), (13, 72, 1), (14, 71, 2)]
SEC = {}  # bar -> set of parts
def parts(bars, *p):
    for b in bars: SEC.setdefault(b, set()).update(p)
parts([0], "tick", "arpsoft"); parts([1], "tick", "arpsoft", "roll")
parts([2, 3], "kick", "snare", "hat", "bass", "arp", "lead")
parts([4, 5], "pad", "basssoft", "hat")
parts([6], "pad", "basssoft", "roll")
parts([7, 8], "kick", "snare", "hat", "bass")
parts([9, 10, 11], "kick", "snare", "hat", "bass", "arp", "lead")
parts([12, 13, 14, 15], "kick", "hat", "bass", "arpsoft")
parts([18, 19], "pad", "arpsoft")
parts([20], "final")
for bar in range(21):
    p = SEC.get(bar, set()); t0 = bar * BAR; c = bar % 4
    for b in range(4):
        tb = t0 + b * B
        if "kick" in p and b in (0, 2): add(kick(), tb)
        if "kick" in p and b == 3 and bar % 2: add(kick(), tb + B / 2)
        if "snare" in p and b in (1, 3): add(snare(), tb)
        if "hat" in p: add(hat(), tb + B / 2, 0.7, 1.0); add(hat() * 0.6, tb, 1.0, 0.7)
        if "tick" in p: add(noise(0.02, 120) * 0.12, tb)
        if "bass" in p:
            for k in range(2): add(tri(ROOT[c] + (12 if k else 0), B / 2 * 0.9) * 0.55, tb + k * B / 2)
        if "basssoft" in p: add(tri(ROOT[c], B * 0.95) * 0.4, tb)
    if "arp" in p or "arpsoft" in p:
        g = 0.13 if "arp" in p else 0.07
        for k in range(16):
            n = CH[c][k % 3] + 12 * (k % 6 >= 3)
            add(pulse(n, B / 4 * 0.85, 0.125) * g, t0 + k * B / 4, 0.7, 1.0)
    if "pad" in p:
        for n in CH[c]: add(pulse(n, BAR * 0.98, 0.5, vib=0.004) * 0.035 * env(int(BAR * 0.98 * SR), a=0.25, r=0.4), t0)
    if "lead" in p:
        ph = (bar - (2 if bar < 9 else 9)) % 4
        for beat, n, ln in LEAD:
            if ph * 4 <= beat < ph * 4 + 4:
                add(pulse(n, ln * B * 0.92, 0.5, vib=0.006) * 0.12, t0 + (beat - ph * 4) * B, 1.0, 0.8)
    if "roll" in p:
        for k in range(8): add(snare() * (0.2 + 0.8 * k / 8), t0 + 2 * B + k * B / 4)
        n = int(BAR * SR); t = np.arange(n) / SR  # pitch riser
        add(np.where((np.cumsum(200 + 1400 * (t / BAR) ** 2) / SR) % 1 < 0.5, 1.0, -1.0) * (t / BAR) ** 2 * 0.08, t0)
    if "final" in p:
        add(kick() * 1.2, t0); add(noise(1.2, 3, 0.5) * 0.2, t0)
        for n in [57, 64, 69, 72, 76]: add(pulse(n, 2.4, 0.25, vib=0.008, d=1.1) * 0.08, t0)
        add(tri(33, 2.4, d=1.4) * 0.6, t0)
for hit in (2 * BAR, 9 * BAR):  # the drop and the long-form lift: crash
    add(noise(1.4, 3.2, 1.0) * 0.22, hit)
mix = np.stack([L, R], 1); mix /= np.abs(mix).max() / 0.89
sf.write(sys.argv[1], mix, SR, subtype="PCM_24")

# 8-bit sound effects
out = os.path.join(os.path.dirname(sys.argv[1]), "..", "sfx")
def save(name, x): x = x / np.abs(x).max() * 0.85; sf.write(os.path.join(out, name), np.stack([x, x], 1), SR, subtype="PCM_24")
def sweep(f0, f1, dur, duty=0.5, d=0.0):
    n = int(dur * SR); t = np.arange(n) / SR; f = f0 * (f1 / f0) ** (t / dur)
    return np.where(np.cumsum(f) / SR % 1 < duty, 1.0, -1.0) * env(n, d=d)
save("blip.wav", pulse(84, 0.06, 0.25))
save("blip2.wav", np.concatenate([pulse(79, 0.05, 0.25), pulse(86, 0.07, 0.25)]))
save("coin.wav", np.concatenate([pulse(83, 0.07, 0.5), pulse(88, 0.35, 0.5, d=6)]))
save("zap.wav", sweep(1800, 120, 0.16, 0.25))
save("boom.wav", noise(0.5, 7, 0.25) + 0.6 * sweep(160, 40, 0.5, 0.5, d=6))
save("powerup.wav", np.concatenate([pulse(n, 0.045, 0.25) for n in [60, 64, 67, 72, 64, 67, 72, 76, 67, 72, 76, 79]]))
save("buzz.wav", sweep(110, 90, 0.35, 0.5) * 0.8)
save("jump.wav", sweep(300, 900, 0.14, 0.25))
k = kick(); k[:7200] += noise(0.15, 30, 0.5) * 0.5; save("stamp.wav", k)
