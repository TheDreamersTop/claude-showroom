"""Dialogue, sfx, ambience and music mix -> audio/mix.wav"""
import os, numpy as np, soundfile as sf
from scipy.signal import resample_poly
import synth as S
from synth import SR, place, stereo
import timeline as TL

ROOT = os.path.join(os.path.dirname(__file__), '..', 'audio')
N = int(TL.END * SR) + SR
rng = np.random.default_rng(7)


def vo(key):
    x, sr = sf.read(os.path.join(ROOT, 'vo', key + '.wav'), dtype='float32')
    x = resample_poly(x, SR // 1000, sr // 1000)
    # trim leading/trailing silence
    a = np.abs(x)
    idx = np.where(a > 0.01)[0]
    x = x[max(idx[0] - 600, 0): idx[-1] + 2400]
    return x


def aged(x, shift=0.955, trem_hz=5.5, trem=0.012, breath=0.05):
    """older voice: a little lower and slower, with a slight waver and breath."""
    n = len(x)
    t = np.arange(int(n / shift)) / SR
    rate = shift * (1 + trem * np.sin(2 * np.pi * trem_hz * t) + 0.004 * np.sin(2 * np.pi * 2.1 * t))
    pos = np.cumsum(rate)
    pos = pos[pos < n - 1]
    y = np.interp(pos, np.arange(n), x)
    env = S.lp(np.abs(y), 30)
    y = y * (1 + 0.06 * np.sin(2 * np.pi * trem_hz * np.arange(len(y)) / SR))
    y = y + S.bp(rng.normal(0, 1, len(y)), 1500, 7000) * env * breath * 4
    y = S.lp(y, 7500)
    return y


def room(x, wet=0.12, ir=None):
    ir = ir if ir is not None else S.make_ir(0.6, 9, 5000)
    return S.reverb(stereo(x), ir, wet)


def claps(dur, n_people=14, seed=11):
    r = np.random.default_rng(seed)
    out = np.zeros((int(dur * SR) + SR, 2))
    for p in range(n_people):
        pan = r.uniform(-0.9, 0.9)
        rate = r.uniform(4.5, 6.5)
        t = r.uniform(0, 0.2)
        f = r.uniform(900, 2200)
        while t < dur:
            m = int(0.03 * SR)
            tl = np.arange(m) / SR
            c = S.bp(r.normal(0, 1, m), f * 0.6, f * 2.5, 1) * np.exp(-tl * 160)
            place(out, stereo(c, pan), t, r.uniform(0.3, 0.6))
            t += 1 / rate * r.uniform(0.85, 1.15)
    e = np.ones(len(out))
    k = int(0.6 * SR)
    e[-k - SR:-SR] = np.linspace(1, 0, k)
    e[-SR:] = 0
    return out * e[:, None] * 0.25


def build():
    dia = np.zeros((N, 2))
    sfx = np.zeros((N, 2))
    amb = np.zeros((N, 2))
    small = S.make_ir(0.5, 10, 5000)
    cut = [TL.bar(b) for _, b, _ in TL.ERAS]   # 1958,1966,1974,1987,2026,hero,end starts

    # ---- pops: cold open + every era cut
    place(sfx, S.pop_pssht(1, 1.0), 0.55, 1.0)
    for i, t in enumerate(cut[1:5]):
        place(sfx, S.pop_pssht(10 + i, 0.9), t - 0.06, [0.75, 0.6, 0.55, 0.8][i])
    place(sfx, S.bubble_rise(0.55, seed=50), cut[4] - 0.10, 0.9)
    for i, t in enumerate([cut[0] + 0.35, cut[1] + 0.3, cut[3] + 0.32, cut[4] + 0.3]):
        place(sfx, S.cap_clink(20 + i), t, 0.6)
    # hero: slow-motion pop (pitched down, stretched)
    big = S.pop_pssht(31, 1.3)
    slow = np.stack([resample_poly(big[:, c], 3, 2) for c in range(2)], 1)
    place(sfx, slow, cut[6] + 0.25, 1.1)
    place(sfx, S.whoosh(1.4, up=True), cut[7] - 1.5, 0.8)
    place(sfx, S.fizz_bed(TL.END - cut[6], 1.0), cut[6] + 0.5, 0.9)

    # ---- 1958: summer porch
    seg = cut[1] - cut[0]
    place(amb, S.cicadas(seg + 0.3), cut[0], 1.0)
    place(amb, S.birds(seg + 0.3, density=0.6), cut[0], 1.0)
    place(amb, S.room_tone(seg + 0.2, 0.6, color=1200), cut[0])
    place(dia, room(vo('mom58'), 0.3, S.make_ir(0.9, 6, 4000)) * 0.55, TL.bar(0, 3.2))  # from inside the house
    # ---- 1966: diner
    seg = cut[2] - cut[1]
    place(amb, S.murmur(seg + 0.2, level=1.0), cut[1])
    place(amb, S.room_tone(seg, 1.0, color=900), cut[1])
    for k in range(3):
        place(sfx, stereo(S.glass_clink(3300 + 200 * k, k) * 0.25, -0.6 + 0.5 * k), cut[1] + 1.1 + k * 1.9)
    place(dia, room(vo('her66'), 0.1, small), TL.bar(3, 0.8))
    place(dia, room(vo('him66'), 0.1, small), TL.bar(4, 0.2))
    # ---- 1974: wedding
    seg = cut[3] - cut[2]
    place(amb, S.murmur(seg, seed=21, level=1.4), cut[2])
    for k, f in enumerate([2500, 2750, 2350, 2900]):
        place(sfx, stereo(S.glass_clink(f, 40 + k) * 0.5, -0.5 + 0.33 * k), cut[2] + 0.5 + 0.13 * k + (0.9 if k > 1 else 0))
    hall = S.make_ir(1.4, 4, 5000)
    for i, (k, dt, g, pan) in enumerate([('kiss_a', 0.00, 0.8, -0.5), ('kiss_b', 0.06, 0.7, 0.4), ('kiss_c', 0.11, 0.6, -0.2), ('kiss_d', 0.03, 0.6, 0.7), ('kiss_e', 0.09, 0.6, -0.8), ('kiss_f', 0.14, 0.5, 0.1)]):
        x = S.reverb(stereo(vo(k), pan), hall, 0.15)
        place(dia, x * g * 0.62, TL.bar(5, 2.0) + dt)
    place(sfx, claps(2.2), TL.bar(6, 1.6), 1.0)
    # ---- 1987: night kitchen
    seg = cut[4] - cut[3]
    place(amb, S.crickets(seg + 0.2), cut[3])
    place(amb, S.clock_tick(seg + 0.2), cut[3])
    place(amb, S.room_tone(seg, 0.6, color=400), cut[3])
    place(dia, room(S.lp(vo('her87'), 6000) * 0.8, 0.12, small), TL.bar(7, 1.6))
    place(dia, room(vo('him87') * 0.8, 0.12, small), TL.bar(8, 1.0))
    # ---- 2026: today
    seg = cut[5] - cut[4]
    place(amb, S.clock_tick(seg + 0.3, seed=9), cut[4])
    place(amb, S.birds(seg, seed=12, density=0.25) * 0.6, cut[4])
    place(amb, S.room_tone(seg, 0.7, color=500), cut[4])
    place(dia, room(aged(vo('her26'), 0.95), 0.1, small), TL.bar(10, 0.3))
    place(dia, room(aged(vo('him26'), 0.94, trem=0.015), 0.1, small), TL.bar(11, 0.9))
    # ---- hero/end narration and button
    place(dia, stereo(vo('vo1')) * 1.05, TL.bar(14, 1.0))
    place(dia, stereo(vo('vo2')) * 1.05, TL.bar(17, 0.5))
    place(dia, room(aged(vo('him26b'), 0.94, trem=0.015), 0.1, small), TL.bar(12, 0.9))
    place(dia, room(aged(vo('her26b'), 0.95), 0.1, small), TL.bar(13, 0.3))

    # ---- music
    mus = np.zeros((N, 2))
    gains = {'1958': 0.9, '1966': 0.75, '1974': 0.8, '1987': 0.95, '2026': 0.95, 'hero': 0.85}
    for k, g in gains.items():
        x, _ = sf.read(os.path.join(ROOT, 'stems', 'music_%s.wav' % k), dtype='float32')
        m = min(len(x), N)
        mus[:m] += x[:m] * g
    # duck music under dialogue (sidechain on dialogue envelope)
    env = S.lp(np.abs(dia).max(1), 4)
    env = np.minimum(env / 0.02, 1.0)
    duck = 1 - 0.72 * S.lp(env, 2)
    mus *= duck[:, None]
    mix = mus * 0.75 + dia * 1.9 + sfx * 1.3 + amb * 4.5
    # gentle bus compression (soft clip) and fade
    mix = np.tanh(mix * 1.1) / 1.1
    fo = int(0.5 * SR)
    end = int(TL.END * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mix = mix[:end]
    for name, buf in [('mix', mix), ('dia', dia[:end]), ('sfx', sfx[:end]), ('amb', amb[:end]), ('mus', mus[:end])]:
        sf.write(os.path.join(ROOT, name + '.wav'), buf.astype(np.float32), SR)
    print('mix written', len(mix) / SR, 's peak', float(np.abs(mix).max()))


if __name__ == '__main__':
    build()
