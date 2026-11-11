"""Score + sound design, keyed to film.T so retimes carry the sound with them.
Writes audio/mix_pre.wav (48 kHz stereo) and stems."""
import os, sys, numpy as np, soundfile as sf
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('MOTH_SCALE', '0.25')
import film
from film import T

SR = 48000
DUR = film.DUR + 1.0
N = int(DUR * SR)
AUD = os.path.join(HERE, '..', 'audio')
RAW = os.path.join(HERE, '..', 'assets', 'sfx_raw')
os.makedirs(AUD, exist_ok=True)
rng = np.random.default_rng(1)

stems = {k: np.zeros((N, 2), np.float32) for k in ('music', 'perc', 'sfx', 'amb', 'flutter')}


def put(stem, x, t, gain=1.0, pan=0.0):
    """Mix mono/stereo x into stem at time t with constant-power pan (-1..1)."""
    i = int(round(t * SR))
    if x.ndim == 1:
        a = (pan + 1) * np.pi / 4
        x = np.stack([x * np.cos(a), x * np.sin(a)], 1)
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), N - i)
    if n > 0:
        stems[stem][i:i + n] += gain * x[:n]


def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'highpass', fs=SR, output='sos'), x)


def load(name, sr_target=SR):
    x, sr = sf.read(os.path.join(RAW, name), always_2d=True)
    x = x.mean(1)
    if sr != sr_target:
        x = signal.resample_poly(x, sr_target, sr)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


# ------------------------------------------------------------------ instruments
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def hz(n):
    """'A4', 'F#5' -> Hz"""
    name = n[0]
    acc = 1 if '#' in n else (-1 if 'b' in n[1:] else 0)
    octv = int(n[-1])
    midi = 12 * (octv + 1) + NOTE[name] + acc
    return 440.0 * 2 ** ((midi - 69) / 12)


def zither(f, dur=2.5, vel=1.0, bright=1.0, bend=0.0, bend_at=0.25, vib=0.0, harmonic=False):
    """Guzheng-like pluck: additive partials, faster decay for higher partials, optional press-bend."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    # pitch envelope: bend (semitones) pressed in after bend_at, plus gentle vibrato
    pe = np.ones(n)
    if bend:
        u = np.clip((t - bend_at) / 0.18, 0, 1)
        pe *= 2 ** (bend * (u * u * (3 - 2 * u)) / 12)
    if vib:
        pe *= 2 ** (vib * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.3) / 0.4, 0, 1) / 12)
    ph = 2 * np.pi * f * np.cumsum(pe) / SR
    y = np.zeros(n)
    if harmonic:
        parts = [(2, 1.0, 2.2), (4, 0.18, 1.0), (6, 0.05, 0.5)]
        for k, a, d in parts:
            y += a * np.sin(k * ph / 2 * 1.0) * np.exp(-t / (d * 1.4))
    else:
        for k in range(1, 14):
            a = (1.0 / k ** (1.05 - 0.25 * bright)) * (0.6 + 0.4 * np.sin(k * 1.7) ** 2)
            d = 1.8 / (1 + 0.55 * (k - 1)) * (1.0 if f < 400 else 0.75)
            inh = 1 + 0.0004 * k * k
            y += a * np.sin(k * inh * ph + k) * np.exp(-t / d)
    att = np.minimum(1, t / 0.003)
    y *= att
    # pluck noise
    nn = int(0.03 * SR)
    y[:nn] += 0.25 * bright * rng.standard_normal(nn) * np.exp(-np.arange(nn) / (0.004 * SR))
    y = hp(y, 70)
    return (vel * 0.22 * y).astype(np.float32)


def woodblock(pitch=1.0, vel=1.0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 820 * pitch * t) * np.exp(-t / 0.035) + 0.6 * np.sin(2 * np.pi * 1930 * pitch * t) * np.exp(-t / 0.018)
         + 0.25 * np.sin(2 * np.pi * 3100 * pitch * t) * np.exp(-t / 0.008))
    y[:200] += 0.5 * rng.standard_normal(200) * np.exp(-np.arange(200) / 40)
    return (vel * 0.35 * y).astype(np.float32)


def bowed(f, dur, vel=1.0, trem=0.0, vib=0.25, att=0.25, rel=0.4):
    """Erhu-ish bowed tone (kept low in the mix): saw + formants + bow noise."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    pe = 2 ** (vib * np.sin(2 * np.pi * 5.5 * t + 1) * np.clip(t / 0.5, 0, 1) / 12)
    ph = np.cumsum(f * pe) / SR
    saw = 2 * (ph % 1.0) - 1
    y = bp(saw, 400, 3200) + 0.6 * bp(saw, 900, 1300, 1)
    y += 0.05 * bp(rng.standard_normal(n), 1500, 6000)
    e = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel)
    if trem:
        e *= 0.55 + 0.45 * np.abs(np.sin(np.pi * trem * t))
    return (vel * 0.12 * y * np.clip(e, 0, 1)).astype(np.float32)


def noise_burst(dur, lo, hi, a=0.005, d=0.1, vel=1.0):
    n = int(dur * SR)
    return (vel * bp(rng.standard_normal(n), lo, hi) * env_ad(n, a, d)).astype(np.float32)


# ------------------------------------------------------------------ helpers from the film itself
FR = np.arange(0, film.DUR, 1 / 24.0)


def lamp_curve():
    return np.array([film.lamp_at(t).power for t in FR])


def to_audio_rate(v):
    return np.interp(np.arange(N) / SR, FR, v, right=0.0).astype(np.float32)


def moth_curves():
    """Per-frame moth shadow size, screen x, flapping flag."""
    size = np.zeros(len(FR))
    x = np.zeros(len(FR))
    fly = np.zeros(len(FR))
    for i, t in enumerate(FR):
        ms = film.moth_state(t)
        if ms is None:
            continue
        if ms == 'net':
            if t < T['release'] + 1.2:
                size[i] = 0.5
                fly[i] = 0.35
                x[i] = 0.25
            continue
        sx, sy, z, flap, rot, sc = ms
        m = 150.0 / (150.0 - z)
        size[i] = m
        x[i] = np.clip(sx / 90.0, -1, 1)
        resting = (T['land'] <= t < T['takeoff']) or t < T['shadow1']
        fly[i] = 0.0 if resting else 1.0
    # moonlight escape
    for i, t in enumerate(FR):
        if T['release'] + 1.2 <= t < T['release'] + 9.0:
            size[i] = 1.0
            fly[i] = 0.7 * (1 - (t - T['release'] - 1.2) / 7.8)
            x[i] = np.clip(0.3 - (t - T['release'] - 1.2) / 6.0, -1, 1)
    return size, x, fly


# ------------------------------------------------------------------ build
def build():
    BAR = 2.3
    BEAT = BAR / 3
    B0 = T['boat_in']

    def bt(bar, beat=0.0):
        return B0 + (bar - 1) * BAR + beat * BEAT

    # ---------------- ambience: room tone + flame
    lampP = to_audio_rate(lamp_curve())
    room = lp(rng.standard_normal(N), 300) * 0.010
    stems['amb'][:, 0] += room
    stems['amb'][:, 1] += lp(rng.standard_normal(N), 300) * 0.010
    hiss = bp(rng.standard_normal(N), 2000, 9000) * 0.006 * np.clip(lampP, 0, 1.5)
    # crackles
    crk = np.zeros(N)
    for _ in range(int(DUR * 2.2)):
        i = rng.integers(0, N - 2000)
        crk[i:i + 600] += rng.standard_normal(600) * np.exp(-np.arange(600) / 60) * rng.uniform(0.2, 1)
    crk = hp(crk, 1500) * 0.05 * np.clip(lampP, 0, 1.5)
    # sputter where the lamp power wobbles fast (moth wind, blow)
    dl = np.abs(np.diff(lamp_curve(), prepend=0))
    sput = to_audio_rate(np.clip(dl * 6, 0, 1))
    sp = bp(rng.standard_normal(N), 150, 1200) * sput * 0.35
    cutm = to_audio_rate(np.array([1.0 if film.cutaway(t) is not None else 0.0 for t in FR]))
    cutm = lp(cutm, 8).astype(np.float32)
    flame = (hiss + crk + sp) * (1 + 1.8 * cutm)
    stems['amb'] += np.stack([flame, flame * 0.9], 1).astype(np.float32)

    # ---------------- match strike, flame catch, title gong
    put('sfx', noise_burst(0.18, 2500, 9000, a=0.002, d=0.05, vel=0.9), T['strike'] - 0.12, 0.8)
    put('sfx', noise_burst(0.12, 1500, 7000, a=0.002, d=0.03, vel=0.6), T['strike'] - 0.32, 0.6)
    ign = lp(rng.standard_normal(int(0.9 * SR)), 1800) * env_ad(int(0.9 * SR), 0.05, 0.25)
    put('sfx', ign.astype(np.float32), T['strike'] + 0.0, 0.5)
    gong = load('gong_horst.wav')
    put('perc', gong[:int(9 * SR)] * np.linspace(1, 0, int(9 * SR)) ** 1.5, T['open_cut'], 0.55)

    # ---------------- title pulled back: airy swell
    sw = bp(rng.standard_normal(int(2.2 * SR)), 300, 3000)
    sw *= np.sin(np.linspace(0, np.pi, len(sw))) ** 2
    put('sfx', sw.astype(np.float32), T['title_pull'], 0.16)
    # set pieces: slide rustle + woodblock on landing
    for k, (dt, pan, pit) in enumerate([(1.4, 0.0, 1.0), (1.8, -0.2, 0.84), (2.3, 0.2, 0.75), (2.8, -0.6, 1.12)]):
        r = bp(rng.standard_normal(int(0.6 * SR)), 800, 5000) * np.linspace(0, 1, int(0.6 * SR)) ** 2
        put('sfx', r.astype(np.float32), T['set_in'] + dt - 0.6, 0.05, pan)
        put('perc', woodblock(pit), T['set_in'] + dt, 0.6, pan)
    put('perc', woodblock(0.84, 0.8), T['set_in'] + 2.8 + 0.12, 0.5, 0.6)

    # ---------------- ACT 1 boat song (3/4, bar = rowing stroke)
    # drone
    for bar in range(1, 11):
        if bt(bar) >= T['shadow1'] - 0.6:
            break
        put('music', zither(hz('D3'), 2.6, 0.7, 0.6), bt(bar), 0.8, -0.2)
        put('music', zither(hz('A3'), 2.0, 0.45, 0.6), bt(bar, 1), 0.7, -0.1)
        put('music', zither(hz('D4'), 1.6, 0.35, 0.6), bt(bar, 2), 0.6, 0.0)
        # oar splash each stroke while rowing
        if bt(bar) < T['boat_stop']:
            s = noise_burst(0.5, 300, 2500, a=0.02, d=0.15, vel=0.5)
            put('sfx', s, bt(bar, 0.4), 0.18, -0.3)
            put('perc', woodblock(1.25, 0.4), bt(bar), 0.25, -0.4)
    mel = [  # (bar, beat, note, vel, bend, dur)
        (3, 0, 'A4', 1.0, 0, 2.5), (3, 1.5, 'B4', 0.7, 0, 1.2), (3, 2, 'A4', 0.8, 0, 1.6),
        (4, 0, 'F#4', 1.0, 0, 2.5), (4, 2, 'E4', 0.8, 0, 2.0),
        (5, 0, 'D4', 0.9, 0, 1.5), (5, 1, 'E4', 0.8, 0, 1.5), (5, 2, 'F#4', 0.9, 0, 1.6),
        (6, 0, 'A4', 1.0, 0, 3.0, 0.25),
        (7, 0, 'B4', 0.9, 0, 2.0), (7, 1.5, 'D5', 0.7, 0, 1.5), (7, 2, 'B4', 0.8, 0, 1.6),
        (8, 0, 'A4', 0.9, 0, 1.6), (8, 1, 'F#4', 0.8, 0, 1.6),
        (9, 0, 'E4', 0.9, 2, 2.6, 0.3), (9, 2, 'D4', 0.7, 0, 1.5),
    ]
    for m in mel:
        bar, beat, note, vel, bend, dur = m[:6]
        if bar > 6:
            continue
        vib = m[6] if len(m) > 6 else 0.12
        put('music', zither(hz(note), dur, vel, 1.0, bend=bend, vib=vib), bt(bar, beat), 1.0, 0.15)
    # scoop 1: a downward slide (the reflection slips away)
    put('music', zither(hz('A4'), 1.6, 0.8, 1.0, bend=-5, bend_at=0.08), T['scoop1'] + 0.05, 0.9, 0.3)
    # reach for the moon: rising run then a hopeful held note, then deflation
    R = T['reach']
    for k, n_ in enumerate(['D4', 'E4', 'F#4', 'A4', 'B4', 'D5', 'E5']):
        put('music', zither(hz(n_), 1.4, 0.55 + 0.06 * k, 1.0), R + 0.9 + k * 0.14, 0.85, 0.1 + 0.05 * k)
    put('music', zither(hz('F#5'), 2.6, 0.9, 1.0, vib=0.25), R + 1.95, 0.9, 0.4)
    put('music', bowed(hz('F#5'), 1.2, 0.5, vib=0.2), R + 2.0, 0.6, 0.4)
    put('music', zither(hz('E5'), 1.2, 0.6, 0.8, bend=-2, bend_at=0.25), T['shadow1'] - 0.45, 0.8, 0.2)
    put('music', zither(hz('A4'), 1.2, 0.55, 0.7, bend=-2, bend_at=0.3), T['shadow1'] + 0.05, 0.8, 0.1)
    # splashes
    for t0, v in ((T['scoop1'] - 0.05, 0.9),):
        sp_ = noise_burst(0.9, 400, 5000, a=0.004, d=0.18, vel=v)
        for _ in range(14):
            i = rng.integers(0, int(0.6 * SR))
            f0 = rng.uniform(400, 1400)
            nb = int(0.05 * SR)
            tt = np.arange(nb) / SR
            sp_[i:i + nb] += 0.25 * np.sin(2 * np.pi * f0 * (1 + 3 * tt / 0.05) * tt) * np.exp(-tt / 0.015)
        put('sfx', sp_, t0, 0.45, 0.35)
    for k in range(9):   # drips from the empty net
        put('sfx', zither(rng.uniform(1400, 2200), 0.15, 0.25, 0.3), T['scoop1'] + 1.3 + k * rng.uniform(0.12, 0.3), 0.35, 0.35)

    # ---------------- ACT 2: the shadow
    SH = T['shadow1']
    # choke: music stops; a low dissonant swell
    drone_len = T['land'] - SH
    d1 = bowed(hz('D2'), drone_len, 0.9, trem=5.0, vib=0.05, att=1.5, rel=0.08)
    d2 = bowed(hz('Eb2'), drone_len - 3, 0.6, trem=6.0, vib=0.05, att=2.0, rel=0.08)
    sw = np.linspace(0.6, 1.3, len(d1))
    put('music', d1 * sw, SH, 1.7, -0.3)
    put('music', d2 * sw[:len(d2)], SH + 3.0, 1.5, 0.3)
    put('perc', woodblock(0.6, 1.0), SH + 0.02, 0.6)    # single hard knock as the light dims
    low = lp(rng.standard_normal(int(drone_len * SR)), 120) * np.linspace(0.3, 1, int(drone_len * SR))
    put('amb', (low * 0.25).astype(np.float32), SH)

    # ---------------- moth wing flutter (driven by the film's moth)
    size, mx, fly = moth_curves()
    S = to_audio_rate(size)
    X = to_audio_rate(mx)
    F = to_audio_rate(fly)
    tt = np.arange(N) / SR
    big = np.clip((S - 1) / 8.0, 0, 1)
    rate = 7.0 + 4.0 * (1 - big)               # big shadow sounds slower/heavier
    phase = np.cumsum(rate) / SR
    am = (0.5 + 0.5 * np.sin(2 * np.pi * phase)) ** 3
    nlo = lp(rng.standard_normal(N), 220) * 2.5
    nhi = bp(rng.standard_normal(N), 900, 5000)
    flut = (nlo * big + nhi * (1 - big) * 0.35) * am * F * np.clip(S, 0, 1.0) ** 0.3
    flut *= 0.5 + 0.8 * big
    a = (X + 1) * np.pi / 4
    stems['flutter'] += np.stack([flut * np.cos(a), flut * np.sin(a)], 1).astype(np.float32)

    # ---------------- landing & reveal
    L = T['land']
    put('perc', woodblock(1.6, 0.25), L + 0.25, 0.4, 0.4)
    put('music', zither(hz('A5'), 4.0, 0.7, 0.5, harmonic=True), L + 1.85, 0.9, 0.4)   # the close-up
    put('music', zither(hz('E6'), 3.0, 0.4, 0.5, harmonic=True), L + 2.5, 0.7, 0.4)
    put('perc', woodblock(1.3, 0.6), L + 3.25, 0.45, 0.0)                               # he sees it
    # sneaky pizzicato as he raises the net
    sneak_t0 = L + 3.9
    seq = ['D3', 'F#3', 'A3', 'F#3', 'D3', 'F#3', 'B3', 'A3', 'D3', 'F#3', 'A3', 'D4', 'E4']
    for k, n_ in enumerate(seq):
        tk = sneak_t0 + k * 0.36
        if tk > T['takeoff'] - 0.05:
            break
        put('music', zither(hz(n_), 0.35, 0.6, 0.5) * np.exp(-np.arange(int(0.35 * SR)) / (0.08 * SR)).astype(np.float32), tk, 0.9, -0.1)
    # takeoff: flurry of woodblocks + swats
    TO = T['takeoff']
    for k in range(7):
        put('perc', woodblock([1.0, 1.25, 0.84][k % 3], 0.7), TO + 0.1 + k * 0.17, 0.45, 0.4 * np.sin(k))
    for k, tk in enumerate([TO + 0.75, TO + 1.25, TO + 1.75]):
        put('sfx', noise_burst(0.3, 500, 3500, a=0.03, d=0.08, vel=0.6), tk, 0.35, 0.1)

    # ---------------- bumps against the lamp: anxious tremolo climbing
    B = T['bumps']
    for k, n_ in enumerate(['A3', 'Bb3', 'B3', 'C4', 'C#4']):
        put('music', bowed(hz(n_), 1.1, 0.55 + 0.08 * k, trem=9, vib=0.1, att=0.08, rel=0.25), B + 0.3 + k * 0.92, 0.85, -0.2)
        put('music', bowed(hz(n_) / 2, 1.1, 0.4, trem=9, vib=0.1, att=0.08, rel=0.25), B + 0.3 + k * 0.92, 0.7, 0.2)
    # the moth hits the flame (cutaway): whoomp + sizzle + tick
    for tb in (B + 1.2 + 0.4, B + 1.2 + 1.2):
        put('sfx', (lp(rng.standard_normal(int(0.5 * SR)), 260) * env_ad(int(0.5 * SR), 0.01, 0.12)).astype(np.float32), tb, 0.9)
        put('sfx', noise_burst(0.35, 3000, 11000, a=0.002, d=0.08, vel=0.6), tb + 0.02, 0.5, 0.1)
        put('sfx', woodblock(2.4, 0.3), tb, 0.4, 0.0)
    # wing beats near the screen while it bumps around the lamp
    for k in range(4):
        put('sfx', (lp(rng.standard_normal(int(0.3 * SR)), 400) * env_ad(int(0.3 * SR), 0.01, 0.07)).astype(np.float32), B + 0.4 + k * 0.85, 0.5, 0.0)

    # ---------------- the catch
    C = T['catch']
    roll_t = C - 2.2
    tk = roll_t
    k = 0
    while tk < C - 0.1:
        gap = 0.22 * (1 - (tk - roll_t) / 2.4) + 0.05
        put('perc', woodblock(1.0 + 0.25 * (k % 2), 0.4 + 0.5 * (tk - roll_t) / 2.2), tk, 0.5, 0.2 * (-1) ** k)
        tk += gap
        k += 1
    put('sfx', noise_burst(0.5, 300, 2500, a=0.08, d=0.2, vel=0.7), C - 0.65, 0.4, 0.2)     # leap whoosh
    gong2 = load('gong55.wav')
    put('perc', gong2[:int(7 * SR)] * np.linspace(1, 0, int(7 * SR)) ** 1.2, C, 0.8, 0.1)
    cym = load('cymbals.wav')
    put('perc', cym[int(0.0 * SR):int(2.5 * SR)] * np.linspace(1, 0, int(2.5 * SR)) ** 2, C, 0.25, 0.3)
    put('sfx', noise_burst(0.6, 80, 600, a=0.004, d=0.12, vel=1.0), C + 0.62, 0.5)          # lands in the boat
    put('sfx', noise_burst(0.8, 400, 4000, a=0.01, d=0.2, vel=0.6), C + 0.66, 0.3, 0.2)
    # little victorious flourish
    for k, n_ in enumerate(['D4', 'F#4', 'A4', 'D5']):
        put('music', zither(hz(n_), 2.2, 0.7, 1.0), C + 0.9 + k * 0.09, 0.8, 0.2)
    put('music', zither(hz('A5'), 3.0, 0.6, 1.0, vib=0.2), C + 1.4, 0.7, 0.3)

    # ---------------- the hand, the breath, darkness
    H = T['hand']
    put('music', bowed(hz('D3'), T['dark'] - H + 0.1, 0.6, vib=0.08, att=1.0, rel=0.15), H, 0.7, 0.0)
    put('music', bowed(hz('A3'), T['dark'] - H - 0.6, 0.35, vib=0.08, att=1.0, rel=0.15), H + 0.7, 0.6, 0.2)
    put('music', bowed(hz('Eb4'), T['dark'] - H - 1.6, 0.25, vib=0.08, att=0.6, rel=0.1), H + 1.7, 0.5, -0.2)
    wl = int(1.0 * SR)
    wh = lp(rng.standard_normal(wl), 900) * np.linspace(0, 1, wl) ** 2.5
    put('sfx', wh.astype(np.float32), T['dark'] - 2.4, 0.35, 0.0)
    hiss = bp(rng.standard_normal(int(0.5 * SR)), 2500, 9000) * env_ad(int(0.5 * SR), 0.004, 0.09)
    put('sfx', hiss.astype(np.float32), T['dark'] - 0.5, 0.45)
    puff = lp(rng.standard_normal(int(0.4 * SR)), 300) * env_ad(int(0.4 * SR), 0.005, 0.08)
    put('sfx', puff.astype(np.float32), T['dark'] - 0.32, 0.3)

    # ---------------- night: crickets, window, moonlight music
    D = T['dark']
    cr = np.zeros(N)
    for c in range(5):
        f0 = rng.uniform(3800, 4700)
        per = rng.uniform(0.55, 0.85)
        t0 = D + 0.3 + rng.uniform(0, 1.0)
        pan = rng.uniform(-0.8, 0.8)
        y = np.zeros(N)
        tc = t0
        while tc < DUR - 0.5:
            for p in range(rng.integers(2, 5)):
                i = int((tc + p * 0.032) * SR)
                nb = int(0.018 * SR)
                if i + nb >= N:
                    break
                tt2 = np.arange(nb) / SR
                y[i:i + nb] += np.sin(2 * np.pi * f0 * tt2) * np.sin(np.pi * tt2 / 0.018) ** 2
            tc += per * rng.uniform(0.9, 1.1)
        fade = np.clip((np.arange(N) / SR - t0) / 1.5, 0, 1) * np.clip((DUR - 1.0 - np.arange(N) / SR) / 3.0, 0, 1)
        y *= fade * rng.uniform(0.5, 1.0)
        a = (pan + 1) * np.pi / 4
        stems['amb'] += (0.011 * np.stack([y * np.cos(a), y * np.sin(a)], 1)).astype(np.float32)
    win = lp(load('window_open.wav'), 6000)
    win *= np.minimum(1, np.arange(len(win)) / (0.05 * SR)) * np.minimum(1, (len(win) - np.arange(len(win))) / (0.6 * SR))
    put('sfx', win.astype(np.float32), T['window'] - 0.5, 0.3, -0.4)
    # moonlight theme in harmonics, slow
    W0 = T['window'] + 2.5
    slow = 1.55
    theme = [(0, 'A5'), (1.5, 'B5'), (2, 'A5'), (3, 'F#5'), (5, 'E5'), (6, 'D5'), (7, 'E5'), (8, 'F#5'), (9, 'A5')]
    for beat, n_ in theme:
        put('music', zither(hz(n_), 4.0, 0.65, 0.5, harmonic=True), W0 + beat * BEAT * slow, 0.9, 0.2)
    # soft low plucks underneath
    for k, n_ in enumerate(['D3', 'A3', 'D3', 'B2', 'D3']):
        put('music', zither(hz(n_), 3.5, 0.4, 0.3), W0 + k * 2.3 * slow * 0.66, 0.6, -0.2)
    # release: the moth's flight out, a rising line
    Rl = T['release'] + 1.2
    put('perc', load('gong_short.wav') * 1.0, Rl + 2.8, 0.13, 0.0)
    put('music', zither(hz('A5'), 4.0, 0.55, 0.4, harmonic=True), Rl + 2.85, 0.8, 0.0)
    put('music', zither(hz('E6'), 4.0, 0.35, 0.4, harmonic=True), Rl + 3.1, 0.7, -0.1)
    for k, n_ in enumerate(['D5', 'E5', 'F#5', 'A5', 'B5', 'D6']):
        put('music', zither(hz(n_), 3.0, 0.5, 0.4, harmonic=True), Rl + 4.0 + k * 0.45, 0.75, 0.1 - 0.15 * k)
    # final: he looks up into the moonlight
    put('perc', load('gong_short.wav') * 1.0, T['look'] + 2.6, 0.22, 0.0)
    g3 = load('gong_horst.wav')[:int(4.6 * SR)]
    put('perc', g3 * np.linspace(1, 0, len(g3)) ** 1.3, T['card'] + 0.1, 0.35, 0.0)
    put('music', zither(hz('D4'), 6.0, 0.5, 0.3), T['look'] + 2.6, 0.7, -0.1)
    put('music', zither(hz('A4'), 6.0, 0.4, 0.3), T['look'] + 2.75, 0.6, 0.1)
    put('music', zither(hz('F#5'), 6.0, 0.4, 0.3, harmonic=True), T['look'] + 2.9, 0.6, 0.25)

    # ---------------- stinger: lamp relit, the moth is back, facepalm
    ST = T['sting']
    put('sfx', noise_burst(0.18, 2500, 9000, a=0.002, d=0.05, vel=0.9), ST + 0.0, 0.8)
    ign2 = lp(rng.standard_normal(int(0.7 * SR)), 1800) * env_ad(int(0.7 * SR), 0.04, 0.2)
    put('sfx', ign2.astype(np.float32), ST + 0.35, 0.45)
    nfl = int(0.95 * SR)
    tt3 = np.arange(nfl) / SR
    fl3 = bp(rng.standard_normal(nfl), 700, 4500) * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * tt3)) ** 3 * np.sin(np.pi * tt3 / 0.95)
    put('flutter', fl3.astype(np.float32), ST + 0.55, 0.5, -0.2)
    sw2 = lp(rng.standard_normal(int(0.6 * SR)), 500) * np.sin(np.linspace(0, np.pi, int(0.6 * SR))) ** 2
    put('sfx', sw2.astype(np.float32), ST + 1.5, 0.5, -0.3)
    put('perc', woodblock(0.9, 0.9), ST + 2.35, 0.7, -0.1)


def mixdown():
    g = dict(music=0.9, perc=0.8, sfx=0.9, amb=0.9, flutter=0.75)
    mix = sum(stems[k] * g[k] for k in stems)
    # room reverb on music + percussion: synthetic impulse response (decorrelated noise, exp decay, darker tail)
    src = stems['music'] * g['music'] + stems['perc'] * g['perc'] + 0.4 * stems['sfx'] * g['sfx']
    n_ir = int(2.2 * SR)
    tt = np.arange(n_ir) / SR
    r2 = np.random.default_rng(77)
    ir = np.zeros((n_ir, 2))
    for ch in range(2):
        nse = r2.standard_normal(n_ir)
        early = lp(nse, 6000) * np.exp(-tt / 0.08)
        late = lp(nse, 2500) * np.exp(-tt * 6.9 / 1.6)
        ir[:, ch] = 0.5 * early + late
    ir[:int(0.018 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(src[:, ch], ir[:, ch])[:N] for ch in range(2)], 1).astype(np.float32)
    mix = mix + 0.32 * wet
    # silence after the end
    end = int(T['sting_end'] * SR)
    fo = int(0.04 * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    fade = np.ones(N)
    fade[end:] = 0
    mix *= fade[:, None]
    peak = np.abs(mix).max()
    mix = mix / peak * 0.7
    return mix.astype(np.float32)


if __name__ == '__main__':
    build()
    for k, v in stems.items():
        sf.write(os.path.join(AUD, f'stem_{k}.wav'), v, SR)
    m = mixdown()
    sf.write(os.path.join(AUD, 'mix_pre.wav'), m, SR)
    print('mix', m.shape, 'peak', np.abs(m).max())
