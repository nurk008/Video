"""Step 2 — procedural cinematic sound design + final mix (NO musical instruments).

Every sound is synthesized from noise / physics-style models: wind, thunder, impacts,
hooves, steel, fire, furnace, water, banners, chainmail, eagle cry, and a low male
A-cappella vocal pad (formant synthesis of the human voice — no instrument timbres).
Fully license-free and reproducible (fixed random seed).

Usage:  python sfx.py <ru|kz|en>
Input:  build/<lang>/timeline.json, build/<lang>/voice.wav
Output: build/<lang>/sfx.wav, build/<lang>/mix.wav (−14 LUFS, TP −1.5 dB)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent
SR = 48000


# ───────────────────────── primitives ─────────────────────────
def n_(d, sr=SR):
    return max(1, int(round(d * sr)))


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) if x.size else 0.0
    return x * (peak / m) if m > 1e-9 else x


def _f(x, kind, f, o=2):
    return signal.sosfilt(signal.butter(o, f, kind, fs=SR, output="sos"), x)


def lp(x, f, o=2):
    return _f(x, "lowpass", f, o)


def hp(x, f, o=2):
    return _f(x, "highpass", f, o)


def bp(x, lo, hi, o=2):
    return _f(x, "bandpass", [lo, hi], o)


def white(rng, d):
    return rng.standard_normal(n_(d))


def brown(rng, d):
    return norm(hp(np.cumsum(rng.standard_normal(n_(d))), 15, 1))


def pink(rng, d):
    n = n_(d)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    return norm(np.fft.irfft(X / np.sqrt(f), n))


def smooth(rng, d, rate, sr=SR):
    """Smooth random control curve in [0, 1] with ~`rate` changes per second."""
    n = n_(d, sr)
    k = max(2, int(d * rate) + 2)
    p = rng.random(k)
    idx = np.arange(n) / max(1, n - 1) * (k - 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, k - 1)
    w = (1 - np.cos(np.pi * (idx - i0))) / 2
    return p[i0] * (1 - w) + p[i1] * w


def tt(d, sr=SR):
    return np.arange(n_(d, sr)) / sr


def expenv(d, tau, attack=0.002):
    t = tt(d)
    e = np.exp(-t / tau)
    return e * np.minimum(1, t / attack) if attack > 0 else e


def fade(x, fin=0.01, fout=0.05):
    x = x.copy()
    a, b = min(len(x), n_(fin)), min(len(x), n_(fout))
    if a > 1:
        x[:a] *= np.linspace(0, 1, a)
    if b > 1:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def fit(x, n):
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


def add(buf, x, t0):
    i = int(round(t0 * SR))
    if i >= len(buf):
        return
    if i < 0:
        x, i = x[-i:], 0
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]


def var_bp(x, fc, q=4.0, block=512):
    """Band-pass with a time-varying centre frequency `fc` (array, Hz)."""
    out, zi = np.zeros(len(x)), None
    for i in range(0, len(x), block):
        c = float(fc[min(i, len(fc) - 1)])
        lo, hi = max(30.0, c * (1 - 0.5 / q)), min(SR / 2 - 300, c * (1 + 0.5 / q))
        sos = signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[i:i + block], zi = signal.sosfilt(sos, x[i:i + block], zi=zi)
    return out


def st(x, pan=0.0):
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)


_IR = {}


def reverb(x, rt=2.2, wet=0.3, seed=7):
    """Stereo algorithmic reverb (decorrelated exponential-noise impulse responses)."""
    key = (rt, seed)
    if key not in _IR:
        rng = np.random.default_rng(seed)
        t = tt(rt * 1.1)
        irs = []
        for _ in range(2):
            ir = lp(rng.standard_normal(len(t)) * np.exp(-6.9 * t / rt), 6000, 1)
            ir = np.concatenate([np.zeros(n_(0.02)), ir])
            irs.append(ir / np.sqrt(np.sum(ir ** 2)))
        _IR[key] = irs
    L, R = _IR[key]
    wl, wr = signal.fftconvolve(x, L), signal.fftconvolve(x, R)
    dry = fit(x, len(wl))
    return np.stack([dry * (1 - wet) + wl * wet, dry * (1 - wet) + wr * wet], 1)


# ───────────────────────── sound sources ─────────────────────────
def thunder(rng, d=4.5):
    t = tt(d)
    crack = hp(white(rng, d), 1200) * expenv(d, 0.05) * 0.5
    bumps = np.zeros(len(t))
    for _ in range(int(rng.integers(4, 8))):
        c, w = rng.uniform(0.05, 2.2), rng.uniform(0.15, 0.6)
        bumps += rng.uniform(0.4, 1.0) * np.exp(-((t - c) / w) ** 2)
    rumble = norm(lp(brown(rng, d), 160, 4)) * (0.35 + bumps) * np.exp(-t / 1.6) * np.minimum(1, t / 0.02)
    boom = np.sin(2 * np.pi * np.cumsum(30 + 40 * np.exp(-t / 0.25)) / SR) * expenv(d, 0.7, 0.005)
    return norm(crack + norm(rumble) * 0.9 + boom * 0.6)


def impact_boom(rng, d=2.5):
    t = tt(d)
    sub = np.sin(2 * np.pi * np.cumsum(32 + 70 * np.exp(-t / 0.12)) / SR) * expenv(d, 0.55, 0.003)
    body = norm(lp(white(rng, d), 500)) * expenv(d, 0.12)
    crack = norm(hp(white(rng, d), 2500)) * expenv(d, 0.012)
    return norm(sub + body * 0.6 + crack * 0.35)


def metal(rng, f0, d=2.0, decay=1.0):
    t = tt(d)
    x = np.zeros(len(t))
    for r, a, tau in zip([1, 2.32, 4.25, 6.63, 9.38, 12.1], [1, .7, .5, .35, .25, .15],
                         [1.0, .7, .45, .3, .22, .15]):
        f = f0 * r * (1 + rng.normal(0, 0.004))
        if f > SR / 2 - 1000:
            continue
        for det in (-0.0015, 0.0015):
            x += a * 0.5 * np.sin(2 * np.pi * f * (1 + det) * t + rng.uniform(0, 6.28)) * np.exp(-t / (tau * decay))
    x *= np.minimum(1, t / 0.0015)
    return norm(norm(x) + 0.5 * norm(hp(white(rng, d), 3000) * expenv(d, 0.004)))


def sword_clash(rng):
    x = metal(rng, rng.uniform(1300, 1800), 1.6, 0.8)
    d = len(x) / SR
    scrape = norm(bp(white(rng, d), 2500, 8000)) * fit(np.hanning(n_(0.15)), len(x)) * 0.4
    return norm(x + scrape)


def sword_draw(rng, d):
    """Rising metallic scrape (riser) — ends abruptly at `d` for the seamless loop cut."""
    t = tt(d)
    u = t / d
    scrape = var_bp(white(rng, d), 1500 * (7000 / 1500) ** (u ** 1.5), q=3)
    amp = u ** 2.2
    ring = sum(np.sin(2 * np.pi * f * t) for f in (2400, 3900, 5600)) / 3
    return norm(norm(scrape) * (0.6 + 0.4 * smooth(rng, d, 25)) * amp + 0.25 * ring * amp)


def whoosh(rng, d=0.8):
    w = np.hanning(n_(d))
    x = var_bp(white(rng, d), 300 + 2500 * w, q=2.5) * w ** 1.5
    return norm(norm(x) + 0.4 * norm(lp(brown(rng, d), 300)) * w)


def riser(rng, d):
    u = tt(d) / d
    return norm(var_bp(white(rng, d), 400 * 20 ** (u ** 1.3), q=3) * u ** 2.5)


def hoof(rng):
    d = 0.25
    t = tt(d)
    f = rng.uniform(65, 100) * (1 + 0.6 * np.exp(-t / 0.02))
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045)
    click = norm(lp(white(rng, d), 2500)) * np.exp(-t / 0.006)
    dirt = norm(bp(white(rng, d), 300, 2500)) * np.exp(-t / 0.03)
    return norm(thump + click * 0.5 + dirt * 0.35)


def gallop(rng, d, horses=1, rate=2.3, accel=0.0):
    out = np.zeros(n_(d) + n_(0.4))
    near = [hoof(rng) for _ in range(8)]
    far = [lp(h, 900) * 0.8 for h in near]
    for h in range(horses):
        r = rate * (1 + rng.normal(0, 0.05))
        g = 1.0 if h == 0 else rng.uniform(0.25, 0.7)
        bank = near if h < 3 else far
        t = -rng.uniform(0, 1 / r)
        while t < d:
            per = 1 / (r * (1 + accel * max(t, 0) / d))
            for fr in (0.0, 0.18, 0.36):            # three-beat canter
                ti = t + fr * per + rng.normal(0, 0.005)
                if 0 <= ti < d:
                    add(out, bank[rng.integers(len(bank))] * g * rng.uniform(0.6, 1.0), ti)
            t += per
    return out


def herd(rng, d):
    return norm(norm(fit(gallop(rng, d, horses=26, rate=2.4), n_(d))) + 0.5 * norm(lp(brown(rng, d), 200, 3)))


def herd_far(rng, d):
    return norm(lp(herd(rng, d), 700))


def gallop_close(rng, d):
    return norm(norm(fit(gallop(rng, d, horses=4, rate=2.5), n_(d))) + 0.3 * norm(lp(brown(rng, d), 200, 3)))


def gallop_fast(rng, d):
    return norm(fit(gallop(rng, d, horses=2, rate=2.0, accel=0.8), n_(d)))


def jingle(rng, d, density=35):
    """Chainmail / weapon jingle: clusters of tiny metallic pings."""
    out = np.zeros(n_(d) + n_(0.08))
    tp = tt(0.06)
    for _ in range(rng.poisson(density * d)):
        f = rng.uniform(3500, 9000)
        add(out, np.sin(2 * np.pi * f * tp) * np.exp(-tp / rng.uniform(0.008, 0.025)) * rng.uniform(0.2, 1),
            rng.uniform(0, d))
    return fit(out, n_(d)) * (0.3 + 0.7 * smooth(rng, d, 4))


def march(rng, d, rate=1.8, men=18):
    out = np.zeros(n_(d) + n_(0.3))
    tp = tt(0.25)
    for m in range(men):
        t = rng.uniform(0, 1 / rate)
        g = 1.0 if m < 2 else rng.uniform(0.2, 0.6)
        while t < d:
            f = rng.uniform(55, 80)
            st_ = np.sin(2 * np.pi * f * tp) * np.exp(-tp / 0.05) + 0.3 * lp(rng.standard_normal(len(tp)), 400) * np.exp(-tp / 0.03)
            add(out, st_ * g, t + rng.normal(0, 0.02))
            t += 1 / rate
    return norm(fit(out, n_(d)))


def fire(rng, d):
    roar = norm(lp(brown(rng, d), 400)) * (0.6 + 0.4 * smooth(rng, d, 1.5))
    cr = np.zeros(n_(d) + n_(0.04))
    tc = tt(0.03)
    for _ in range(rng.poisson(14 * d)):
        lo = rng.uniform(800, 2500)
        c = bp(rng.standard_normal(len(tc)), lo, min(lo * 3, 20000)) * np.exp(-tc / rng.uniform(0.002, 0.008))
        add(cr, norm(c) * rng.uniform(0.3, 1), rng.uniform(0, d))
    return norm(roar * 0.5 + norm(fit(cr, n_(d))) * 0.8)


def furnace(rng, d):
    t = tt(d)
    roar = norm(lp(brown(rng, d), 220, 3)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.45 * t))
    return norm(roar + 0.3 * norm(bp(white(rng, d), 150, 700)) * smooth(rng, d, 2))


def sizzle(rng, d):
    return norm(bp(white(rng, d), 3500, 8500) * (0.4 + 0.6 * smooth(rng, d, 12)) * expenv(d, d * 0.5, 0.01))


def anvil(rng):
    d = 1.5
    t = tt(d)
    thump = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.06)
    return norm(metal(rng, rng.uniform(420, 520), d, 0.9) * 0.8 + thump)


def wheels(rng, d):
    t = tt(d)
    rumble = norm(lp(brown(rng, d), 140, 3)) * (0.7 + 0.3 * smooth(rng, d, 3))
    f = 180 + 80 * smooth(rng, d, 2)
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    gate = np.clip(np.sin(2 * np.pi * 0.8 * t + rng.uniform(0, 6)), 0, 1) ** 4
    return norm(rumble + 0.25 * norm(bp(saw, 500, 2500)) * gate)


def banners(rng, d):
    flap = norm(np.abs(lp(white(rng, d), 10, 2)))
    return norm(bp(white(rng, d), 250, 1600) * (0.25 + flap))


def wind(rng, d, howl=0.5):
    base = norm(lp(pink(rng, d), 700)) * (0.5 + 0.5 * smooth(rng, d, 0.4))
    whistle = var_bp(white(rng, d), 450 + 450 * smooth(rng, d, 0.35), q=10) * smooth(rng, d, 0.5)
    return norm(base + norm(whistle) * howl)


def water(rng, d):
    splash = bp(white(rng, d), 500, 6000) * (0.2 + 0.8 * smooth(rng, d, 9) ** 2)
    bub = np.zeros(n_(d) + n_(0.05))
    tb = tt(0.04)
    for _ in range(rng.poisson(25 * d)):
        f0 = rng.uniform(500, 900)
        add(bub, np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.5 * tb / 0.04)) / SR) * np.exp(-tb / 0.015) * rng.uniform(0.2, 1),
            rng.uniform(0, d))
    return norm(norm(splash) + 0.3 * norm(fit(bub, n_(d))))


def snort(rng):
    d = 0.6
    t = tt(d)
    env = np.minimum(1, t / 0.03) * np.exp(-t / 0.18)
    return norm(bp(white(rng, d), 300, 2200) * env * (0.75 + 0.25 * np.sin(2 * np.pi * 32 * t)))


def staff(rng):
    d = 2.0
    t = tt(d)
    thump = np.sin(2 * np.pi * np.cumsum(50 + 40 * np.exp(-t / 0.01)) / SR) * np.exp(-t / 0.14)
    knock = norm(bp(white(rng, d), 350, 1400)) * np.exp(-t / 0.025)
    crack = norm(hp(white(rng, d), 2500)) * np.exp(-t / 0.008)
    return norm(thump + knock * 0.7 + crack * 0.4 + metal(rng, 2100, d, 0.5) * 0.15)


def clasp(rng):
    d = 0.5
    t = tt(d)
    return norm(norm(lp(white(rng, d), 600)) * np.exp(-t / 0.03) + np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.06))


def thud(rng):
    d = 1.0
    t = tt(d)
    return norm(np.sin(2 * np.pi * 60 * t) * np.exp(-t / 0.09) + 0.6 * norm(bp(white(rng, d), 200, 1500)) * np.exp(-t / 0.15))


def army(rng, d):
    return norm(norm(lp(brown(rng, d), 260, 3)) * 0.8 + 0.4 * norm(bp(pink(rng, d), 180, 700)) * (0.5 + 0.5 * smooth(rng, d, 2)))


def heavy_steps(rng, d):
    out = np.zeros(n_(d) + n_(0.6))
    t = 0.12
    while t < d:
        add(out, lp(hoof(rng), 1400), t)
        add(out, metal(rng, rng.uniform(650, 950), 0.5, 0.25) * 0.18, t + 0.01)
        add(out, jingle(rng, 0.25, density=60) * 0.15, t)
        t += rng.uniform(0.38, 0.46)
    return norm(fit(out, n_(d)))


def eagle(rng):
    def cry(d):
        t = tt(d)
        u = t / d
        f = (2600 + 1100 * np.exp(-((u - 0.15) / 0.18) ** 2) - 500 * u) * (1 + 0.015 * np.sin(2 * np.pi * 28 * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph) + 0.15 * norm(bp(white(rng, d), 2000, 6000))
        return x * np.sin(np.pi * u) ** 0.6 * (1 - 0.3 * u)
    out = np.zeros(n_(2.0))
    add(out, cry(0.9), 0.0)
    add(out, cry(0.55) * 0.7, 1.15)
    return norm(lp(out, 7000))


FORMANTS = {  # male vowels: (freq, bandwidth, gain)
    "u": [(320, 80, 1.0), (800, 100, 0.35), (2300, 150, 0.08)],
    "o": [(420, 80, 1.0), (820, 90, 0.6), (2600, 150, 0.12)],
    "a": [(680, 90, 1.0), (1150, 110, 0.6), (2600, 160, 0.18)],
    "m": [(260, 60, 1.0), (1100, 200, 0.05), (2300, 250, 0.02)],   # closed-mouth hum
}


def vocal_pad(rng, d, notes, vowel="o", voices=4):
    """Low male A-cappella choir / hum via additive formant synthesis of the human voice."""
    sr = 24000
    n = n_(d, sr)
    t = np.arange(n) / sr
    out = np.zeros(n)
    for f0 in notes:
        H = int(4500 / f0)
        fh = np.arange(1, H + 1) * f0
        A = sum(a / (1 + ((fh - F) / (bw / 2)) ** 2) for F, bw, a in FORMANTS[vowel]) + 0.01
        A = A * np.arange(1, H + 1) ** -0.6
        A /= A.max()
        for _ in range(voices):
            det = 2 ** (rng.normal(0, 7) / 1200)
            vib = 1 + 0.0045 * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * t + rng.uniform(0, 6.28))
            drift = 1 + 0.004 * (smooth(rng, d, 0.7, sr) - 0.5)
            ph = 2 * np.pi * np.cumsum(f0 * det * vib * drift) / sr
            amp = 0.7 + 0.3 * smooth(rng, d, 0.5, sr)
            for k in range(H):
                out += A[k] * np.sin((k + 1) * ph + rng.uniform(0, 6.28)) * amp
    x = signal.resample_poly(out, 2, 1)
    x = norm(x) + 0.04 * norm(bp(white(rng, len(x) / SR), 300, 3000))
    return fade(norm(x), 0.8, 1.0)


# ───────────────────────── scene design (from the storyboard) ─────────────────────────
def scene_sfx(k, d, rng):
    N = n_(d)
    out = np.zeros((N + n_(4.0), 2))

    def put(x, t0=0.0, g=1.0, pan=0.0, rev=None):
        if t0 >= d:
            return
        s = reverb(x, *rev) if rev else (st(x, pan) if x.ndim == 1 else x)
        i = n_(t0) if t0 > 0 else 0
        m = min(len(s), len(out) - i)
        out[i:i + m] += s[:m] * g

    def bed(fn, g, **kw):
        a = fade(fit(fn(rng, d, **kw), N), 0.03, 0.12)
        b = fade(fit(fn(rng, d, **kw), N), 0.03, 0.12)
        put(np.stack([0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b], 1), 0, g)

    if k == 1:      # thunder hit + saber ring + horse snort
        put(impact_boom(rng), 0, 1.0, rev=(2.5, 0.25))
        put(thunder(rng), 0, 0.7, rev=(3.0, 0.3))
        put(sword_clash(rng), 0.22, 0.55, rev=(1.8, 0.25))
        put(snort(rng), min(1.0, d * 0.5), 0.45, pan=-0.3)
        bed(wind, 0.25)
    elif k == 2:    # cold wind + sub-bass vocal drone
        bed(wind, 0.6, howl=0.8)
        put(vocal_pad(rng, d + 0.5, [65.4, 98.0], "m"), 0, 0.45, rev=(3.0, 0.35))
    elif k == 3:    # foundry: furnace roar, sizzle, hammer
        bed(furnace, 0.55)
        put(sizzle(rng, min(d, 2.0)), 0.25, 0.18, pan=0.2)
        put(anvil(rng), 0.6, 0.7, rev=(1.6, 0.25))
        if d > 2.2:
            put(anvil(rng), d - 0.9, 0.6, rev=(1.6, 0.25))
    elif k == 4:    # cannon wheels, iron, marching
        bed(wheels, 0.5)
        bed(march, 0.55)
        bed(jingle, 0.2)
    elif k == 5:    # burning map + riser
        bed(fire, 0.6)
        put(riser(rng, d), 0, 0.45)
    elif k == 6:    # thunder roll + male A-cappella chord
        put(thunder(rng), 0, 0.8, rev=(3.5, 0.35))
        put(vocal_pad(rng, d + 1.0, [73.4, 110.0, 146.8], "a"), 0.1, 0.5, rev=(3.2, 0.4))
        bed(wind, 0.2)
    elif k == 7:    # thousands of hooves + banners
        bed(herd, 0.7)
        bed(banners, 0.4)
    elif k == 8:    # staff strike → silence
        put(staff(rng), 0, 1.0, rev=(2.8, 0.35))
    elif k == 9:    # three blades cross + fire
        for i, t0 in enumerate((0.0, 0.11, 0.22)):
            put(sword_clash(rng), t0, 0.7, rev=(1.8, 0.25))
        bed(fire, 0.45)
    elif k == 10:   # herd through river
        bed(herd, 0.65)
        bed(water, 0.5)
        put(snort(rng), d * 0.4, 0.35, pan=0.4)
    elif k == 11:   # weapons handed over, forearm clasp
        bed(jingle, 0.35, density=20)
        for t0 in (0.15, 0.7, 1.4):
            put(metal(rng, rng.uniform(1600, 2400), 0.8, 0.4), t0, 0.3, pan=rng.uniform(-0.5, 0.5))
        put(clasp(rng), d * 0.55, 0.7)
    elif k == 12:   # distant army + chainmail
        bed(army, 0.5)
        bed(jingle, 0.25, density=25)
        put(snort(rng), d * 0.6, 0.3, pan=-0.4)
    elif k == 13:   # cavalry wedge charge
        put(whoosh(rng, 0.8), 0, 0.45)
        bed(gallop_close, 0.8)
        bed(army, 0.25)
    elif k == 14:   # dry wind over two armies
        bed(wind, 0.6, howl=1.0)
        bed(herd_far, 0.4)
    elif k == 15:   # heavy armored steps, tense silence
        bed(heavy_steps, 0.75)
        bed(wind, 0.12, howl=0.2)
    elif k == 16:   # whoosh + explosive gallop
        put(whoosh(rng, 0.9), 0, 0.8)
        bed(gallop_fast, 0.8)
    elif k == 17:   # duel impact: steel + sparks + falling banner pole
        put(impact_boom(rng), 0, 1.0, rev=(3.0, 0.3))
        put(sword_clash(rng), 0, 0.9, rev=(2.5, 0.35))
        put(sizzle(rng, 0.8), 0.02, 0.2)
        put(thud(rng), min(d - 0.3, d * 0.6), 0.6, rev=(1.5, 0.2))
    elif k == 18:   # Tolgama: avalanche of hooves + male choir
        put(impact_boom(rng), 0, 0.5, rev=(2.5, 0.3))
        bed(herd, 0.8)
        put(vocal_pad(rng, d + 1.2, [73.4, 110.0, 146.8, 220.0], "a", voices=5), 0, 0.55, rev=(3.5, 0.4))
    elif k == 19:   # dawn: wind, distant thunder, eagle
        bed(wind, 0.45, howl=0.3)
        put(thunder(rng, 4.0), 0.15, 0.45, rev=(3.5, 0.4))
        put(eagle(rng), min(1.0, d * 0.35), 0.5, rev=(3.0, 0.45))
        put(vocal_pad(rng, d + 0.8, [65.4, 98.0, 130.8], "o"), 0, 0.35, rev=(3.5, 0.45))
    elif k == 20:   # saber drawn — riser cut exactly at the loop point
        put(sword_draw(rng, d), 0, 0.8)
        bed(wind, 0.15)
    return out


# ───────────────────────── mix ─────────────────────────
def frame_rms(x, win=0.05):
    k = n_(win)
    m = len(x) // k
    return np.sqrt(np.mean(x[:m * k].reshape(m, -1) ** 2, axis=1) + 1e-12)


def softclip(x, th=0.8):
    a = np.abs(x)
    return np.sign(x) * np.where(a < th, a, th + (1 - th) * np.tanh((a - th) / (1 - th)))


def loudnorm(src, dst, I=-14, TP=-1.5, LRA=11):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
                        f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:"
          f"offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", af,
                    "-ar", "48000", str(dst)], check=True)


def write(path, x):
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def run(lang):
    B = ROOT / "build" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    T = tl["T"]
    N = n_(T)
    rng = np.random.default_rng(1726)

    sfx = np.zeros((N + n_(4.0), 2))
    for sc in tl["scenes"]:
        s = scene_sfx(sc["id"], sc["t1"] - sc["t0"], rng)
        i = n_(sc["t0"]) if sc["t0"] > 0 else 0
        m = min(len(s), len(sfx) - i)
        sfx[i:i + m] += s[:m]
    sfx = sfx[:N]

    # continuous steppe ambience, dipped to silence after the staff strike (scene 8)
    amb = np.stack([fit(wind(rng, T, 0.3), N), fit(wind(rng, T, 0.3), N)], 1)
    g = np.ones(N)
    s8 = tl["scenes"][7]
    g[n_(s8["t0"]):n_(min(s8["t1"], s8["t0"] + 1.3))] = 0.12
    g = np.convolve(g, np.ones(n_(0.08)) / n_(0.08), "same")
    sfx += amb * 0.10 * g[:, None]
    write(B / "sfx.wav", norm(sfx, 0.9))

    sr, v = wavfile.read(B / "voice.wav")
    v = fit(v.astype(np.float64) / 32768.0, N)
    vr = frame_rms(v)
    v_level = np.mean(vr[vr > np.max(vr) * 0.05])
    sfx *= (v_level * 0.26) / np.mean(frame_rms(sfx.mean(1)))

    env = lp(np.abs(v), 6, 2)
    env /= np.percentile(env, 95) + 1e-9
    duck = 1 - 0.62 * np.clip(env, 0, 1)
    out = reverb(v, 0.32, 0.025, seed=3)[:N] + sfx * duck[:, None]
    out *= 0.85 / np.percentile(np.abs(out), 99.95)
    write(B / "mix_premaster.wav", softclip(out))
    loudnorm(B / "mix_premaster.wav", B / "mix.wav")
    print(f"[{lang}] mix ready: {T:.2f}s → {B / 'mix.wav'}")


if __name__ == "__main__":
    run(sys.argv[1])
