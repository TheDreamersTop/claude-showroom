"""Small numpy synth: instruments, effects, sfx. All stereo float32 at SR."""
import numpy as np
from scipy import signal

SR = 48000
rng = np.random.default_rng(1958)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.2, sus_len=None):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    sus_n = max(n - a_n - d_n - r_n, 0) if sus_len is None else int(sus_len * SR)
    e = np.concatenate([np.linspace(0, 1, max(a_n, 1)), np.linspace(1, s, max(d_n, 1)), np.full(sus_n, s), np.linspace(s, 0, max(r_n, 1))])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def stereo(x, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1).astype(np.float32)


def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), 'low')
    return signal.lfilter(b, a, x, axis=0)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high')
    return signal.lfilter(b, a, x, axis=0)


def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), min(f2 / (SR / 2), 0.99)], 'band')
    return signal.lfilter(b, a, x, axis=0)


# ------------------------------------------------------------------ instruments (mono, return array)
def piano(m, dur, vel=0.8):
    f = mtof(m)
    n = int((dur + 2.5) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    B = 0.0004
    for k in range(1, 14):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > SR / 2.2:
            break
        amp = (1 / k ** 1.1) * (0.6 + 0.4 * vel) ** (k * 0.25)
        dec = 1.2 + 4.0 * (k - 1) ** 0.7 + f / 600
        out += amp * np.exp(-t * dec / (1 + 1.6 * (60 - min(m, 60)) / 30)) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    # two-stage decay + damper at note off
    damp = np.ones(n)
    off = int(dur * SR)
    damp[off:] = np.exp(-np.arange(n - off) / SR * 9)
    hammer = rng.normal(0, 1, n) * np.exp(-t * 300) * 0.25
    hammer = bp(hammer, f, min(f * 8, 12000))
    return (out * damp + hammer) * vel * 0.35


def epiano(m, dur, vel=0.7):
    """2-op FM tine (DX7-ish)."""
    f = mtof(m)
    n = int((dur + 1.8) * SR)
    t = np.arange(n) / SR
    I = (2.2 * vel) * np.exp(-t * 4.5) + 0.25
    mod = np.sin(2 * np.pi * f * 14.0 * t) * 0.18 * np.exp(-t * 30) + np.sin(2 * np.pi * f * t) * I
    car = np.sin(2 * np.pi * f * t + mod)
    e = np.exp(-t * 1.4)
    off = int(dur * SR)
    e[off:] *= np.exp(-np.arange(n - off) / SR * 6)
    return car * e * vel * 0.3


def pluck(m, dur, vel=0.7, bright=0.5, decay=0.996):
    """Karplus-Strong."""
    f = mtof(m)
    n = int((dur + 1.2) * SR)
    N = int(SR / f)
    buf = rng.uniform(-1, 1, N)
    buf = lp(buf, 1500 + 8000 * bright, 1)
    out = np.zeros(n)
    idx = 0
    prev = 0.0
    b = buf.copy()
    for i in range(n):
        v = b[idx]
        nv = decay * 0.5 * (v + prev)
        prev = v
        b[idx] = nv
        out[i] = v
        idx = (idx + 1) % N
    off = int(dur * SR)
    out[off:] *= np.exp(-np.arange(n - off) / SR * 12)
    return out * vel * 0.5


def pluck_fast(m, dur, vel=0.7, bright=0.5, decay=4.0):
    """cheap plucked string: harmonic series with per-partial decay (vectorised)."""
    f = mtof(m)
    n = int((dur + 1.0) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 18):
        fk = f * k
        if fk > SR / 2.3:
            break
        amp = (1 / k) * np.exp(-k * (1 - bright) * 0.35) * abs(np.sin(np.pi * k * 0.23))
        out += amp * np.exp(-t * decay * (1 + 0.35 * k)) * np.sin(2 * np.pi * fk * t)
    off = int(dur * SR)
    out[off:] *= np.exp(-np.arange(n - off) / SR * 14)
    return out * vel * 0.5


def saw_ens(m, dur, vel=0.6, attack=0.25, release=0.6, voices=5, cutoff=3500):
    """string machine / ensemble: detuned band-limited saws with slow attack and chorus."""
    f = mtof(m)
    n = int((dur + release + 0.1) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(voices):
        det = 1 + (v - (voices - 1) / 2) * 0.0035
        vib = 1 + 0.003 * np.sin(2 * np.pi * (5.2 + v * 0.3) * t + v)
        ph = 2 * np.pi * np.cumsum(f * det * vib) / SR
        for k in range(1, 12):
            if f * k > SR / 2.5:
                break
            out += np.sin(k * ph + v) / k
    out /= voices
    out = lp(out, cutoff, 2)
    return out * env_adsr(n, attack, 0.2, 0.85, release, sus_len=dur - attack - 0.2) * vel * 0.25


def reed(m, dur, vel=0.6, vib_depth=0.006):
    """sax-ish lead: pulse + saw, vibrato that grows in, formant-ish filtering."""
    f = mtof(m)
    n = int((dur + 0.25) * SR)
    t = np.arange(n) / SR
    vib = 1 + vib_depth * np.minimum(t / 0.35, 1) * np.sin(2 * np.pi * 5.4 * t)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = np.zeros(n)
    for k in range(1, 20):
        if f * k > SR / 2.5:
            break
        x += np.sin(k * ph) / k * (1.0 if k % 2 else 0.55)
    x = bp(x, 400, 3200, 1) + 0.3 * bp(x, 1100, 1700, 2)
    x += rng.normal(0, 0.02, n) * np.minimum(t / 0.05, 1)
    return x * env_adsr(n, 0.03, 0.1, 0.8, 0.12, sus_len=dur - 0.13) * vel * 0.5


def organ(m, dur, vel=0.5):
    f = mtof(m)
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in [(0.5, 0.5), (1, 1), (2, 0.6), (3, 0.3), (4, 0.25)])
    x *= 1 + 0.15 * np.sin(2 * np.pi * 6.5 * t)
    return x * env_adsr(n, 0.01, 0.05, 0.9, 0.1, sus_len=dur - 0.06) * vel * 0.18


def bass(m, dur, vel=0.7, upright=False):
    f = mtof(m)
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) + 0.2 * np.sin(6 * np.pi * f * t) * np.exp(-t * 10)
    if upright:
        e = np.exp(-t * 3.5)
        x += rng.normal(0, 1, n) * np.exp(-t * 120) * 0.3
    else:
        e = env_adsr(n, 0.004, 0.15, 0.7, 0.08, sus_len=dur - 0.16)
    off = int(dur * SR)
    e[off:] *= np.exp(-np.arange(n - off) / SR * 25)
    return lp(x * e, 1800) * vel * 0.55


def bell(m, dur=2.0, vel=0.5):
    f = mtof(m)
    n = int((dur + 2) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for r, a, d in [(1, 1, 1.2), (2.76, 0.5, 2.5), (5.4, 0.3, 4), (8.93, 0.15, 6), (4.07, 0.2, 3)]:
        x += a * np.exp(-t * d) * np.sin(2 * np.pi * f * r * t)
    return x * vel * 0.2


# ------------------------------------------------------------------ drums
def kick(vel=0.8):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * vel


def snare(vel=0.6, brush=False):
    n = int((0.35 if brush else 0.25) * SR)
    t = np.arange(n) / SR
    if brush:
        x = bp(rng.normal(0, 1, n), 1500, 9000) * np.exp(-t * 14) * np.minimum(t / 0.01, 1)
        return x * vel * 0.35
    x = bp(rng.normal(0, 1, n), 900, 9000) * np.exp(-t * 22) + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.6
    return x * vel * 0.5


def hat(vel=0.4, open_=False):
    n = int((0.3 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    return hp(rng.normal(0, 1, n), 7000) * np.exp(-t * (10 if open_ else 70)) * vel * 0.3


def brush_swish(dur, vel=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return bp(rng.normal(0, 1, n), 2000, 8000) * np.sin(np.pi * t / dur) ** 2 * vel * 0.12


# ------------------------------------------------------------------ effects
def make_ir(seconds=2.0, decay=3.0, bright=6000, predelay=0.012, seed=3):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        x = r.normal(0, 1, n) * np.exp(-t * decay)
        x = lp(x, bright, 1)
        ir[:, c] = x
    pd = int(predelay * SR)
    ir = np.concatenate([np.zeros((pd, 2)), ir])
    # early reflections
    for d, g in [(0.011, 0.5), (0.019, 0.35), (0.027, 0.3), (0.041, 0.2)]:
        k = int(d * SR)
        ir[k, 0] += g
        ir[k + 37, 1] += g
    return ir / np.sqrt((ir ** 2).sum() / 2)


def reverb(x, ir, wet=0.25):
    """x stereo (n,2)."""
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)[:len(x)]
    return x * (1 - wet) + y * wet


def spring_ir():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        x = rng.normal(0, 1, n) * np.exp(-t * 3.5)
        # metallic chirps: comb-ish
        for d in (0.033, 0.047, 0.061):
            k = int(d * SR)
            x[k:] += 0.6 * x[:-k]
        ir[:, c] = bp(x, 400, 5000, 2)
    return ir / np.sqrt((ir ** 2).sum() / 2)


def radio(x, lo=320, hi=3600, crackle=0.004, seed=5):
    y = bp(x, lo, hi, 2)
    y = np.tanh(y * 1.8) / 1.8
    r = np.random.default_rng(seed)
    n = len(y)
    c = (r.random(n) < 0.0009) * r.normal(0, 1, n) * 0.2
    c = lp(c, 6000)
    hiss = hp(r.normal(0, crackle, n), 2000)
    m = y.mean(1) if y.ndim == 2 else y
    m = m + c + hiss
    return stereo(m, 0.0)


def place(buf, x, t, gain=1.0):
    """add stereo or mono x into stereo buf at time t."""
    i = int(t * SR)
    if i >= len(buf):
        return
    if x.ndim == 1:
        x = stereo(x)
    j = min(len(buf), i + len(x))
    buf[i:j] += x[:j - i] * gain


# ------------------------------------------------------------------ sfx
def pop_pssht(seed=0, size=1.0):
    """crown cap opening: metal snap, the 'pssht' gas burst, then fizz."""
    r = np.random.default_rng(seed)
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    # snap: short inharmonic metal tick
    snap = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in [(2300, 0.6, 90), (3900, 0.4, 120), (5200, 0.3, 150), (1250, 0.35, 70)])
    snap += r.normal(0, 1, n) * np.exp(-t * 400) * 0.6
    # pssht: noise burst, fast attack, band 1.5-9 kHz with a falling resonance
    burst = r.normal(0, 1, n)
    e = np.minimum(t / 0.004, 1) * np.exp(-t * 7.5) * size
    burst = bp(burst, 1400, 10000, 2) * e
    res = bp(r.normal(0, 1, n), 2800, 4200, 2) * np.exp(-t * 14) * 0.6
    gas = burst + res
    # fizz: sparse tiny clicks (bubbles) decaying over 2.5 s
    fz = np.zeros(n)
    rate = 1800 * np.exp(-t * 1.1) + 150
    hits = r.random(n) < rate / SR
    fz[hits] = r.normal(0, 1, hits.sum()) * (0.4 + 0.6 * r.random(hits.sum()))
    fz = hp(fz, 3000) * 0.5
    fz = fz * np.exp(-t * 0.9)
    x = 0.55 * snap + 0.9 * gas + 0.45 * fz
    L = x + 0.15 * np.roll(fz, 211)
    R = x + 0.15 * np.roll(fz, 397)
    return np.stack([L, R], 1).astype(np.float32) * 0.5


def cap_clink(seed=0):
    """cap landing on a table: two small bounces."""
    r = np.random.default_rng(seed)
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, (tt, g) in enumerate([(0.0, 1.0), (0.11, 0.45), (0.17, 0.25), (0.205, 0.12)]):
        i = int(tt * SR)
        tl = t[:n - i]
        hit = sum(a * np.sin(2 * np.pi * f * (1 + 0.02 * k) * tl) * np.exp(-tl * d) for f, a, d in [(3100, 0.5, 60), (5400, 0.4, 80), (7600, 0.25, 90), (1800, 0.2, 50)])
        out[i:] += g * hit
    return stereo(out * 0.25, 0.2)


def glass_clink(f0=2400, seed=0):
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f0 * r_ * t) * np.exp(-t * d) for r_, a, d in [(1, 1, 2.2), (2.32, 0.5, 3.5), (4.25, 0.35, 5), (6.63, 0.2, 7)])
    x += np.random.default_rng(seed).normal(0, 1, n) * np.exp(-t * 500) * 0.3
    return x * 0.15


def fizz_bed(dur, level=1.0, seed=2):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for c in range(2):
        hits = r.random(n) < 260 / SR
        x = np.zeros(n)
        x[hits] = r.normal(0, 1, hits.sum())
        out[:, c] = hp(x, 3500)
    return out * 0.08 * level


def cicadas(dur, seed=1):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for c in range(2):
        x = bp(r.normal(0, 1, n), 4300, 6800, 2)
        am = 0.55 + 0.45 * np.sin(2 * np.pi * 38 * t + c) ** 2
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 5.5 + c * 1.3)
        out[:, c] = x * am * swell
    return out * 0.05


def crickets(dur, seed=3):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for c, (f, rate, ph) in enumerate([(4600, 2.1, 0.0), (4950, 2.6, 0.7)]):
        chirp_gate = (np.sin(2 * np.pi * rate * t + ph) > 0.55).astype(float)
        pulses = (np.sin(2 * np.pi * 52 * t) > 0).astype(float)
        g = lp(chirp_gate * pulses, 900)
        out[:, c] = np.sin(2 * np.pi * f * t) * g
    return out * 0.018


def birds(dur, seed=4, density=0.5):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2))
    tt = 0.3
    while tt < dur - 0.5:
        k = int(r.integers(2, 5))
        base = r.uniform(2600, 4200)
        pan = r.uniform(-0.8, 0.8)
        for j in range(k):
            ln = r.uniform(0.05, 0.12)
            m = int(ln * SR)
            tl = np.arange(m) / SR
            f = base * (1 + r.uniform(-0.25, 0.35) * tl / ln)
            ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tl / ln) ** 2
            place(out, stereo(ch, pan), tt + j * (ln + 0.04), 0.03)
        tt += r.exponential(1.0 / density) + 0.4
    return out


def clock_tick(dur, period=1.0, seed=6):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    t = np.arange(int(0.05 * SR)) / SR
    for k in range(int(dur / period)):
        f = 2600 if k % 2 else 2200
        tk = (np.sin(2 * np.pi * f * t) * np.exp(-t * 180) + 0.3 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 120))
        place(out, stereo(tk * 0.05, -0.5), k * period + 0.2)
    return out


def room_tone(dur, level=1.0, seed=7, color=600):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = np.stack([lp(r.normal(0, 1, n), color, 2), lp(r.normal(0, 1, n), color, 2)], 1)
    return x * 0.012 * level


def murmur(dur, seed=8, level=1.0):
    """indistinct diner chatter: band-limited noise with syllabic AM, a few voices."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for v in range(6):
        x = bp(r.normal(0, 1, n), 250 + 60 * v, 1600 + 150 * v, 2)
        syl = lp((r.random(n // 600 + 2) > 0.45).astype(float).repeat(600)[:n], 9)
        phr = (np.sin(2 * np.pi * t / r.uniform(2.5, 4.5) + r.uniform(0, 6)) > -0.2).astype(float)
        phr = lp(phr, 3)
        out += stereo(x * syl * phr, r.uniform(-0.8, 0.8))
    return out * 0.02 * level


def whoosh(dur=1.2, seed=9, up=True):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = r.normal(0, 1, n)
    e = (t / dur) ** 2 if up else (1 - t / dur) ** 2
    y = np.zeros(n)
    # sweep a bandpass by chunks
    ch = 2048
    for i in range(0, n, ch):
        frac = i / n if up else 1 - i / n
        fc = 300 + 5000 * frac
        y[i:i + ch] = bp(x[i:i + ch], fc * 0.6, fc * 1.6, 1)
    return stereo(lp(y, 9000) * e * 0.2)


def bubble_rise(dur=0.5, n=26, seed=0):
    """carbonation rising: many tiny resonant 'blips' whose pitch climbs (Minnaert-style chirps)."""
    r = np.random.default_rng(seed)
    out = np.zeros((int((dur + 0.2) * SR), 2))
    for i in range(n):
        t0 = (i / n) ** 0.8 * dur + r.uniform(-0.02, 0.02)
        f0 = r.uniform(900, 2600) * (1 + 0.8 * i / n)
        m = int(r.uniform(0.02, 0.05) * SR)
        tl = np.arange(m) / SR
        f = f0 * (1 + 6 * tl)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tl * r.uniform(60, 120))
        place(out, stereo(x, r.uniform(-0.6, 0.6)), max(t0, 0), r.uniform(0.3, 0.8))
    return out * 0.18
