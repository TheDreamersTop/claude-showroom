"""Soundtrack: narration + synthesized score + births sonified as pentatonic notes + foley. Writes out/mix.wav."""
import os, json
import numpy as np, soundfile as sf
import look
from scenes import build, timeline, FILM, FPS, ROOT, ease

SR = 48000
rng = np.random.default_rng(3)
OUT = os.path.join(ROOT, "out")
CACHE = os.path.join(OUT, "cache")


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


N = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def m(name):  # "F#4" -> midi
    return 12 * (int(name[-1]) + 1) + N[name[:-1]]


# ---------------- buffers ----------------
class Bus:
    def __init__(self, dur):
        self.x = np.zeros((int(dur * SR) + SR * 6, 2), np.float32)

    def add(self, t0, sig, pan=0.0, gain=1.0):
        i = int(t0 * SR)
        if i < 0:
            sig = sig[-i:]; i = 0
        n = min(len(sig), len(self.x) - i)
        if n <= 0:
            return
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        if sig.ndim == 1:
            self.x[i:i + n, 0] += sig[:n] * l * gain * 1.414
            self.x[i:i + n, 1] += sig[:n] * r * gain * 1.414
        else:
            self.x[i:i + n] += sig[:n] * gain


def env_adsr(n, a, r, sustain_shape=None):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.minimum(1.0, (n / SR - t) / max(r, 1e-4))
    return np.clip(e, 0, 1).astype(np.float32)


# ---------------- instruments ----------------
def pad(freqs, dur, a=1.8, r=2.5, amp=0.05, trem=0.0, bright=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for f in freqs:
        for k, det in enumerate((-0.006, 0.0, 0.0065)):
            ph = rng.uniform(0, 6.28)
            vib = 1 + 0.0025 * np.sin(2 * np.pi * (0.2 + 0.07 * k) * t + ph)
            sig = np.zeros(n)
            for h in range(1, 7):
                if f * h > 9000: break
                sig += np.sin(2 * np.pi * f * h * (1 + det) * t * vib + ph * h) / h ** bright
            pan = (k - 1) * 0.5
            out[:, 0] += sig * np.cos((pan + 1) * np.pi / 4); out[:, 1] += sig * np.sin((pan + 1) * np.pi / 4)
    e = env_adsr(n, a, r)
    if trem:
        e = e * (1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * trem * t)))
    return out * (e * amp / max(1, len(freqs)) * 1.4)[:, None]


def pluck(f, amp=0.12, dur=1.2, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 9):
        if f * h > 12000: break
        sig += np.sin(2 * np.pi * f * h * t) * np.exp(-t * (3.5 + 2.6 * h * h / bright)) / h ** 1.2
    sig *= np.minimum(1, t / 0.003)
    return (sig * amp).astype(np.float32)


def bell(f, amp=0.08, dur=3.5):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 1.1) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 2.8)
           + 0.18 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t * 5.5) + 0.1 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 3))
    return (sig * np.minimum(1, t / 0.002) * amp).astype(np.float32)


def kalimba(f, amp=0.05, dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.25 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t * 26)
    return (sig * np.minimum(1, t / 0.0015) * amp).astype(np.float32)


def lead(notes, beat, amp=0.07):
    """notes: [(beat_offset, midi, beats)] -> soft flute-like legato line."""
    end = max(b + d for b, _, d in notes) * beat + 1.5
    n = int(end * SR); out = np.zeros(n, np.float32)
    for b, mi, d in notes:
        f = mf(mi); i0 = int(b * beat * SR); L = int((d * beat + 0.35) * SR)
        t = np.arange(L) / SR
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.35) / 0.4, 0, 1)
        ph = 2 * np.pi * f * np.cumsum(vib) / SR
        sig = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
        sig += 0.02 * rng.normal(size=L) * np.exp(-t * 8)  # breath at onset
        e = np.minimum(1, t / 0.09) * np.clip((d * beat + 0.35 - t) / 0.35, 0, 1)
        seg = (sig * e * amp).astype(np.float32)
        out[i0:i0 + L] += seg[:max(0, min(L, n - i0))]
    return out


def noise_lp(n, fc):
    x = rng.normal(size=n)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    X /= np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X, n).astype(np.float32) / max(1e-9, np.std(np.fft.irfft(X, n)))


def boom(amp=0.5, dur=4.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 * np.exp(-t * 0.6) + 28
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.1)
    sig += 0.5 * noise_lp(n, 180) * np.exp(-t * 3.5)
    return (sig * np.minimum(1, t / 0.01) * amp).astype(np.float32)


def timp_roll(dur, amp0=0.02, amp1=0.2, rate0=4, rate1=22):
    n = int(dur * SR); out = np.zeros(n, np.float32)
    t = 0.0
    while t < dur:
        u = t / dur
        a = amp0 + (amp1 - amp0) * u ** 2
        L = int(0.5 * SR); tt = np.arange(L) / SR
        hit = (np.sin(2 * np.pi * 73 * tt) * 0.8 + noise_lp(L, 300) * 0.4) * np.exp(-tt * 9) * a * rng.uniform(0.7, 1.0)
        i = int(t * SR); k = min(L, n - i); out[i:i + k] += hit[:k]
        t += 1.0 / (rate0 + (rate1 - rate0) * u ** 1.5)
    return out


def crunch(amp=0.35):
    n = int(1.2 * SR); t = np.arange(n) / SR
    out = 0.6 * np.sin(2 * np.pi * 70 * t) * np.exp(-t * 9)
    for k in range(14):
        i = int(rng.uniform(0, 0.35) * SR); L = int(0.03 * SR); tt = np.arange(L) / SR
        g = noise_lp(L, rng.uniform(1500, 4500)) * np.exp(-tt * 120) * rng.uniform(0.3, 1.0) * np.exp(-i / SR * 4)
        out[i:i + L] += g[:max(0, min(L, n - i))]
    return (out * amp).astype(np.float32)


def reverb(x, secs=3.2, wet=0.32, fc=4500):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = np.stack([noise_lp(n, fc) * np.exp(-t * 6.9 / secs) for _ in range(2)], 1)
    ir[: int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0))
    B = 1 << 18; L = B - n
    out = np.zeros((len(x) + n, 2), np.float32)
    IR = [np.fft.rfft(ir[:, c], B) for c in range(2)]
    for i in range(0, len(x), L):
        seg = x[i:i + L]
        for c in range(2):
            y = np.fft.irfft(np.fft.rfft(seg[:, c], B) * IR[c], B)[: len(seg) + n]
            out[i:i + len(y), c] += y
    return x * (1 - wet * 0.5) + out[: len(x)] * wet


# ---------------- births pass ----------------
def births_events(name):
    import hashlib
    cues, durs, _ = timeline()
    src = open(os.path.join(ROOT, "src", "scenes.py"), encoding="utf-8").read()
    i0 = src.find(f'    if name == "{name}":'); i1 = src.find("\n    if name == ", i0 + 10)
    block = src[i0:i1 if i1 > 0 else None]
    key = hashlib.md5(json.dumps([cues[name], durs[name], block]).encode()).hexdigest()[:8]
    path = os.path.join(CACHE, f"births_{name}_{key}.npz")
    sc = build(name)
    if os.path.exists(path):
        d = np.load(path, allow_pickle=True); return list(d["ev"])
    nf = int(round(sc.dur * FPS)); ev = []
    for f in range(nf):
        t = f / FPS
        if sc.black:
            ev.append((0, np.zeros((0, 2)), 1.0)); continue
        cam = sc.cam(t)
        _, _, _, b = sc.frame_state(t)
        if len(b):
            c, s = np.cos(cam["rot"]), np.sin(cam["rot"])
            dx, dy = b[:, 0] + 0.5 - cam["cx"], b[:, 1] + 0.5 - cam["cy"]
            px = look.W / 2 + cam["z"] * (c * dx - s * dy); py = look.H / 2 + cam["z"] * (s * dx + c * dy)
            ok = (px > -20) & (px < look.W + 20) & (py > -20) & (py < look.H + 20)
            pts = np.stack([px[ok], py[ok]], 1)
            n = len(pts)
            if n > 24:
                pts = pts[rng.choice(n, 24, replace=False)]
            ev.append((n, pts, cam["z"] * sc.exposure(t)))
        else:
            ev.append((0, np.zeros((0, 2)), cam["z"]))
    np.savez(path, ev=np.array(ev, dtype=object))
    return ev


PENTA = [m(x) for x in ["D4", "E4", "F#4", "A4", "B4", "D5", "E5", "F#5", "A5", "B5", "D6"]]


def sonify(bus, t0, ev, gain=1.0):
    for f, (n, pts, z) in enumerate(ev):
        if n == 0:
            continue
        a = 0.05 * gain / np.sqrt(max(1.0, n / 3.0))
        big = np.clip((z - 8) / 30, 0, 1)
        for (px, py) in pts:
            idx = int(np.clip((1 - py / look.H) * (len(PENTA) - 1) + rng.normal(0, 0.4), 0, len(PENTA) - 1))
            mi = PENTA[idx] - (12 if big > 0.5 else 0)
            tt = t0 + f / FPS + rng.uniform(0, 1 / FPS)
            bus.add(tt, kalimba(mf(mi), amp=a * (1 + 0.6 * big)), pan=float(np.clip((px / look.W - 0.5) * 1.4, -0.9, 0.9)))
        if n > 40:  # crackle for crowds
            L = int(SR / FPS); g = noise_lp(L, 6000) * (rng.random(L) < 0.004 * min(n, 400) / 40) * 0.05 * gain
            bus.add(t0 + f / FPS, g.astype(np.float32), pan=0)


# ---------------- score ----------------
BEAT = 0.75


def chord(names):
    return [mf(m(x)) for x in names.split()]


def score(mus, st, cues, durs, scenes):
    C = lambda s, i: st[s] + cues[s][i][0]
    E = lambda s, i: st[s] + cues[s][i][1]

    # OPEN — wonder
    s = "open"; t0 = st[s]
    mus.add(t0 + 0.0, pad(chord("D3 A3 E4 F#4"), 9.5, a=4, r=3, amp=0.07))
    mus.add(t0 + 0.0, pad(chord("D2"), 9.5, a=4, r=3, amp=0.05, bright=3))
    for k, n_ in enumerate(["A5", "F#5", "E6", "D6", "B5"]):
        mus.add(t0 + 2.2 + k * 1.45, bell(mf(m(n_)), 0.03), pan=rng.uniform(-0.6, 0.6))
    tt = E(s, 2) + 1.0
    mus.add(tt - 0.6, pad(chord("G2 D3 B3 F#4 A4"), st["law"] - tt + 2.0, a=2.0, r=2.4, amp=0.10))
    mus.add(tt + 0.5, bell(mf(m("D6")), 0.05)); mus.add(tt + 1.1, bell(mf(m("A5")), 0.035), pan=0.4)

    # LAW — curious plucks
    s = "law"; t0 = st[s]
    prog = ["B2 F#3 B3 D4", "G2 D3 G3 B3", "D3 A3 D4 F#4", "A2 E3 A3 C#4"]
    nb = int((durs[s]) / BEAT)
    for b in range(nb):
        ch = prog[(b // 8) % 4].split()
        nt = ch[[0, 2, 3, 2, 1, 2, 3, 2][b % 8]]
        mus.add(t0 + b * BEAT, pluck(mf(m(nt) + 12), 0.05), pan=0.3 * np.sin(b))
    for i in range(0, nb, 8):
        mus.add(t0 + i * BEAT, pad(chord(prog[(i // 8) % 4]), 8 * BEAT + 1.0, a=1.5, r=1.5, amp=0.035))
    mus.add(C(s, 1) + 0.15, bell(mf(m("D6")), 0.06))
    mus.add(E(s, 3) - 0.4, bell(mf(m("F#4")), 0.03))

    # STILL — comic pizzicato, the counter arpeggio
    s = "still"; t0 = st[s]
    patt = ["D4", "A4", "F#4", "A4"]
    for b in range(int((C(s, 1) - t0) / BEAT)):
        mus.add(t0 + b * BEAT, pluck(mf(m(patt[b % 4])), 0.06, dur=0.5, bright=0.6))
    a0, a1 = C(s, 1) - 0.1, E(s, 1) - 0.2
    t, k = a0, 0
    arp = [m(x) for x in ["D4", "F#4", "A4", "D5", "F#5", "A5", "D6"]]
    while t < a1:
        u = (t - a0) / (a1 - a0)
        mus.add(t, pluck(mf(arp[k % 7] + 12 * (k // 7 % 2)), 0.035 + 0.02 * u, dur=0.35, bright=0.8), pan=0.4 * np.sin(k * 0.7))
        t += 0.19 * (1 - 0.7 * u); k += 1
    mus.add(C(s, 2) + 1.65, pad(chord("D3 A3 D4 F#4 A4"), 3.0, a=0.05, r=2.0, amp=0.08))
    mus.add(C(s, 2) + 1.65, bell(mf(m("D6")), 0.05))
    for k, (dt, n_) in enumerate([(0.75, "D5"), (2.05, "F#5"), (3.05, "A5")]):
        mus.add(C(s, 3) + dt, pluck(mf(m(n_)), 0.07, bright=0.8), pan=-0.3 + 0.3 * k)
    mus.add(C(s, 4), pad(chord("G2 D3 B3 E4"), st["osc"] - C(s, 4) + 1.5, a=1.5, r=1.5, amp=0.05))

    # OSC — beat-locked
    s = "osc"; t0 = st[s]
    nb = int(durs[s] / BEAT)
    for b in range(nb):
        mus.add(t0 + b * BEAT, pluck(mf(m("D3") if b % 2 == 0 else m("A2")), 0.06, dur=0.8, bright=0.5))
    mus.add(t0, pad(chord("G3 B3 D4 F#4"), 6.0, a=1.0, r=2.0, amp=0.05))
    mus.add(t0 + 5.5, pad(chord("E3 G3 B3 D4"), C(s, 3) - t0 - 5.0, a=1.5, r=2.0, amp=0.05))
    mus.add(C(s, 3), pad(chord("A5"), st["glider"] - C(s, 3) + 1.0, a=1.0, r=2.0, amp=0.03))

    # GLIDER — the theme
    s = "glider"; t0 = st[s]
    th = C(s, 1) - 0.2
    theme = [(0, m("A4"), 1), (1, m("D5"), 1), (2, m("E5"), 1), (3, m("F#5"), 3), (6, m("E5"), 1), (7, m("D5"), 1),
             (8, m("B4"), 3), (11, m("A4"), 1), (12, m("D5"), 2), (14, m("E5"), 2), (16, m("A5"), 4), (20, m("G5"), 2),
             (22, m("F#5"), 2), (24, m("E5"), 6)]
    mus.add(th, lead(theme, BEAT, 0.06), pan=0.05)
    prog = ["D3 A3 D4 F#4", "B2 F#3 B3 D4", "G2 D3 G3 B3", "A2 E3 A3 C#4", "D3 A3 D4 F#4", "G2 D3 B3 F#4", "E3 B3 D4 G4", "A2 E3 A3 D4"]
    for i, ch in enumerate(prog):
        mus.add(th + i * 4 * BEAT - 0.3, pad(chord(ch), 4 * BEAT + 1.6, a=1.0, r=1.6, amp=0.06))
        mus.add(th + i * 4 * BEAT, pluck(mf(m(ch.split()[0]) - 12 if m(ch.split()[0]) > 40 else m(ch.split()[0])), 0.05, dur=2.5, bright=0.4))
    mus.add(t0, pad(chord("D3 A3"), th - t0 + 1, a=1.5, r=1.0, amp=0.04))

    # EATER — tension, silence, crunch, resolve
    s = "eater"; t0 = st[s]; sc = scenes["eater"]
    mus.add(t0, pad(chord("D2 A2 D#3"), E(s, 2) - t0 + 0.5, a=2.0, r=0.8, amp=0.05, trem=0.0, bright=2.2))
    mus.add(C(s, 1), pad(chord("C#5 D5"), E(s, 2) - C(s, 1) + 0.4, a=1.5, r=0.6, amp=0.012))
    tc = next(f / FPS for f in range(int(sc.dur * FPS)) if sc.gen_fn(f / FPS) >= sc.contact_gen - 0.5)
    scenes["_eater_contact"] = t0 + tc
    mus.add(C(s, 3) + 0.2, pad(chord("D3 A3 D4 F#4 A4"), durs[s] - cues[s][3][0] + 1.0, a=1.2, r=2.2, amp=0.07))
    mus.add(C(s, 4) + 1.9, bell(mf(m("A5")), 0.035))

    # GUN — melancholy
    s = "gun"; t0 = st[s]
    prog = [("B2 F#3 B3 D4", 6.0), ("G2 D3 G3 B3", 4.5), ("E2 B2 E3 G3", 4.5), ("F#2 C#3 F#3 A#3", durs[s] - 15 + 1.5)]
    t = t0
    for ch, d in prog:
        mus.add(t, pad(chord(ch), d + 1.5, a=1.5, r=1.8, amp=0.07)); t += d
    mel = [(0, m("F#5"), 3), (3, m("E5"), 1), (4, m("D5"), 3), (7, m("C#5"), 1), (8, m("B4"), 4), (13, m("D5"), 2), (15, m("C#5"), 6)]
    mus.add(C(s, 1) + 0.5, lead(mel, 0.85, 0.045), pan=-0.1)

    # RPENT — catastrophe
    s = "rpent"; t0 = st[s]
    mus.add(t0, pad(chord("A5"), E(s, 1) - t0 + 1, a=2, r=1.5, amp=0.02))
    tb = C(s, 2) + 1.0
    mus.add(E(s, 2) - 0.2, boom(0.55))
    sw0, sw1 = E(s, 2), C(s, 5) + 0.3
    D = sw1 - sw0
    for k, ch in enumerate(["B1 B2 F#3 B3 D4", "G1 G2 D3 B3 D4 G4", "D2 D3 A3 F#4 A4 D5", "A1 A2 E3 A3 C#4 E4 A4"]):
        seg0 = sw0 + k * D / 4
        p = pad(chord(ch), D / 4 + 1.8, a=0.4 if k else 1.0, r=1.4, amp=0.06 + 0.035 * k, trem=6 + 2 * k, bright=1.2)
        mus.add(seg0, p)
    mus.add(sw0, timp_roll(D, 0.01, 0.16, 3, 20))
    for k in range(int(D / (BEAT / 2))):  # rising high ostinato
        u = k * BEAT / 2 / D
        mus.add(sw0 + k * BEAT / 2, pluck(mf(m(["B5", "F#5", "D6", "A5"][k % 4]) + (12 if u > 0.6 else 0)), 0.02 + 0.03 * u, dur=0.4), pan=0.5 * np.sin(k))
    mus.add(C(s, 6) + 0.25, bell(mf(m("D5")), 0.07, dur=5))
    mus.add(C(s, 7) - 0.3, pad(chord("D3 A3 C#4 F#4 A4"), C(s, 8) - C(s, 7) + 1.5, a=2.0, r=1.8, amp=0.07))
    mus.add(C(s, 8) - 0.3, pad(chord("G2 D3 B3 F#4"), C(s, 9) - C(s, 8) + 1.5, a=1.5, r=1.8, amp=0.07))
    mus.add(C(s, 9) - 0.3, pad(chord("D3 A3 D4 E4 F#4"), st["end"] - C(s, 9) + 2.5, a=1.5, r=2.5, amp=0.07))

    # END — theme reprise, slower
    s = "end"; t0 = st[s]
    b2 = 1.0
    rep = [(0, m("A4"), 1), (1, m("D5"), 1), (2, m("E5"), 1), (3, m("F#5"), 3), (6, m("E5"), 1), (7, m("D5"), 1), (8, m("B4"), 4)]
    mus.add(t0 + 0.8, lead(rep, b2, 0.05))
    for i, ch in enumerate(["D3 A3 D4 F#4", "B2 F#3 B3 D4", "G2 D3 G3 B3", "A2 E3 G3 C#4"]):
        mus.add(t0 + 0.5 + i * 3.0, pad(chord(ch), 3.0 + 1.6, a=1.2, r=1.6, amp=0.06))
    tf = C(s, 4)
    mus.add(t0 + 12.5, pad(chord("A2 D3 E3 A3"), tf - t0 - 12.5 + 0.6, a=1.0, r=0.8, amp=0.05))
    mus.add(tf - 0.05, pad(chord("D2 D3 A3 D4 F#4 A4 E5"), 11.0, a=0.3, r=6.0, amp=0.10))
    mus.add(tf, bell(mf(m("D6")), 0.06, dur=6)); mus.add(tf + 0.02, bell(mf(m("A5")), 0.04, dur=6), pan=0.3)

    # STING — the glider's theme returns, and is cut off by the crunch
    s = "sting"; t0 = st[s]; tcut = t0 + scenes["sting"].t_contact
    ph = lead([(0, m("A4"), 1), (1, m("D5"), 1), (2, m("E5"), 1), (3, m("F#5"), 3)], 0.6, 0.055)
    n = int((tcut - t0 - 0.5) * SR)
    ph = ph[:n] * np.minimum(1, (n - np.arange(n)) / 240.0).astype(np.float32)  # hard (5 ms) cut
    mus.add(t0 + 0.5, ph, pan=0.05)

    # CREDITS — soft tail
    s = "credits"; t0 = st[s]
    mus.add(t0 + 0.3, pad(chord("G3 B3 D4 F#4"), 5.5, a=2.5, r=2.5, amp=0.05))
    mus.add(t0 + 5.0, pad(chord("D3 A3 E4 F#4"), 6.5, a=2.5, r=3.0, amp=0.05))
    for k, n_ in enumerate(["F#5", "A5", "E6", "D6"]):
        mus.add(t0 + 1.0 + k * 2.2, bell(mf(m(n_)), 0.025), pan=rng.uniform(-0.5, 0.5))


def main():
    cues, durs, vo = timeline()
    st, t = {}, 0.0
    for s in FILM:
        st[s] = t; t += durs[s]
    total = t
    print("total", round(total, 2), {k: round(v, 1) for k, v in st.items()})
    scenes = {s: build(s) for s in ["eater", "sting", "rpent"]}

    voice = Bus(total); mus = Bus(total); fol = Bus(total)
    for k, v in vo.items():
        s, i = k.split(":"); i = int(i)
        x, _ = sf.read(v["path"], dtype="float32")
        voice.add(st[s] + cues[s][i][0], x, pan=0.0)

    score(mus, st, cues, durs, scenes)

    for s in FILM:
        ev = births_events(s)
        sonify(fol, st[s], ev, gain=0.0 if s in ("still", "credits") else (0.7 if s == "rpent" else 1.0))
        print("births", s, sum(e[0] for e in ev), flush=True)
    fol.add(scenes["_eater_contact"], crunch(0.4), pan=0.1)
    fol.add(st["sting"] + scenes["sting"].t_contact, crunch(0.45), pan=0.1)
    for k, th in enumerate(scenes["rpent"].hit_times):
        fol.add(st["rpent"] + th, crunch(0.22), pan=(-0.3, 0.3, 0.0)[k])

    musr = reverb(mus.x, 3.4, 0.38)
    folr = reverb(fol.x, 2.2, 0.30)
    # duck music under narration
    v = np.abs(voice.x[:, 0])
    hop = 480
    envv = np.array([v[i:i + hop].max() for i in range(0, len(v), hop)])
    pres = (envv > 0.01).astype(float)
    win = np.hanning(60); win /= win.sum()
    pres = np.convolve(np.convolve(pres, np.ones(30), "same").clip(0, 1), win, "same")
    duck = 1 - 0.58 * pres
    duck = np.repeat(duck, hop)[: len(v)]
    mix = voice.x * 1.0 + musr * duck[:, None] * 1.0 + folr * (1 - 0.3 * pres.repeat(hop)[: len(v)])[:, None]
    n = int(total * SR)
    mix = mix[:n]
    peak = np.abs(mix).max()
    print("peak before norm", peak)
    mix = mix / max(peak, 1e-6) * 0.89
    sf.write(os.path.join(OUT, "mix.wav"), mix, SR, subtype="FLOAT")
    sf.write(os.path.join(OUT, "stem_vo.wav"), voice.x[:n], SR, subtype="FLOAT")
    json.dump(dict(starts=st, total=total), open(os.path.join(OUT, "layout.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
