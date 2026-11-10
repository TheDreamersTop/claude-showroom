"""The score: one melody passed through the decades. Writes audio/stems/music_<era>.wav (full film length each)."""
import os, numpy as np, soundfile as sf
import synth as S
from synth import SR, place, stereo
import timeline as TL

OUT = os.path.join(os.path.dirname(__file__), '..', 'audio', 'stems')
os.makedirs(OUT, exist_ok=True)
N = int(TL.END * SR) + SR

# theme: per bar list of (beat, dur, midi)
THEME = [
    [(0, 1, 64), (1, 1, 67), (2, 1.5, 72), (3.5, 0.5, 71)],
    [(0, 2, 69), (2, 1, 64), (3, 1, 67)],
    [(0, 1, 65), (1, 1, 69), (2, 1, 72), (3, 1, 74)],
    [(0, 1.5, 74), (1.5, 0.5, 72), (2, 2, 71)],
    [(0, 1, 64), (1, 1, 67), (2, 1, 72), (3, 1, 76)],
    [(0, 1, 74), (1, 1, 72), (2, 1, 71), (3, 1, 68)],
    [(0, 1.5, 69), (1.5, 0.5, 65), (2, 1, 72), (3, 1, 69)],
    [(0, 1, 67), (1, 1, 71), (2, 2, 72)],
    [],                                   # 8: rest bar, held dominant
]
# chords per theme bar: list of (beat, dur, root, tones)
C, Am, F, G, E7 = (48, [0, 4, 7]), (45, [0, 3, 7]), (41, [0, 4, 7]), (43, [0, 4, 7]), (40, [0, 4, 7, 10])
CHORDS = [[(0, 4, *C)], [(0, 4, *Am)], [(0, 4, *F)], [(0, 4, *G)], [(0, 4, *C)], [(0, 4, *E7)], [(0, 4, *F)], [(0, 2, *G), (2, 2, *C)], [(0, 4, *G)]]
# film bar -> theme bar
MAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 0, 9: 4, 10: 5, 11: 6, 12: 3, 13: 8, 14: 0, 15: 1, 17: 6, 18: 7}


def span(name):
    for e, b0, n in TL.ERAS:
        if e == name:
            return TL.bar(b0), TL.bar(b0 + n)


def voicing(root, tones, center=60):
    """close voicing of chord tones near center."""
    out = []
    for t in tones:
        m = root + t
        while m < center - 5:
            m += 12
        while m > center + 6:
            m -= 12
        out.append(m)
    return sorted(out)


def swing(beat, amount=0.62):
    b = int(beat)
    f = beat - b
    if abs(f - 0.5) < 1e-6:
        return b + amount
    return beat


def t_of(fb, beat):
    return TL.bar(fb, beat)


def era_bars(name):
    for e, b0, n in TL.ERAS:
        if e == name:
            return list(range(b0, b0 + n))


def gate(buf, t0, t1, fade_in=0.01, fade_out=0.04):
    """keep only [t0, t1) of a stem, short fades."""
    n = len(buf)
    g = np.zeros(n)
    i0, i1 = int(t0 * SR), min(int(t1 * SR), n)
    g[i0:i1] = 1
    fi, fo = int(fade_in * SR), int(fade_out * SR)
    g[i0:i0 + fi] = np.linspace(0, 1, fi)
    g[max(i1 - fo, 0):i1] = np.linspace(1, 0, min(fo, i1))
    return buf * g[:, None]


# ------------------------------------------------------------------ eras
def m1958():
    buf = np.zeros((N, 2))
    for fb in era_bars('1958'):
        tb = MAP[fb]
        for beat, dur, m in THEME[tb]:
            place(buf, S.reed(m - 12, dur * TL.BEAT * 0.95, 0.7), t_of(fb, swing(beat)), 0.9)
        for cb, cd, root, tones in CHORDS[tb]:
            v = voicing(root, tones, 58)
            for k in range(int(cd)):
                for off in (0.5,):
                    tt = t_of(fb, swing(cb + k + off))
                    for i, m in enumerate(v):
                        place(buf, S.pluck_fast(m, 0.18, 0.45, bright=0.6, decay=9), tt + i * 0.006, 0.6)
            # walking upright bass
            pat = [0, 7, 12, 9] if cd == 4 else [0, 7]
            for k, iv in enumerate(pat):
                place(buf, S.bass(root - 12 + iv + 12, TL.BEAT * 0.9, 0.8, upright=True), t_of(fb, cb + k), 1.0)
        for k in range(4):
            place(buf, S.kick(0.35), t_of(fb, k), 0.5)
            if k % 2:
                place(buf, S.snare(0.5, brush=True), t_of(fb, k), 0.8)
            place(buf, S.brush_swish(TL.BEAT * 0.9, 0.4), t_of(fb, k), 0.6)
    ir = S.make_ir(1.0, 6, 4000)
    buf = S.reverb(buf, ir, 0.18)
    buf = S.radio(buf, 280, 3800, 0.006)
    return gate(buf, 0.0, span('1958')[1])


def m1966():
    buf = np.zeros((N, 2))
    gtr = np.zeros((N, 2))
    for fb in era_bars('1966'):
        tb = MAP[fb]
        for beat, dur, m in THEME[tb]:
            x = S.pluck_fast(m - 12, dur * TL.BEAT, 0.8, bright=0.75, decay=1.6)
            tt = np.arange(len(x)) / SR
            x = x * (0.7 + 0.3 * np.sin(2 * np.pi * 6.2 * tt))
            place(gtr, stereo(x, 0.15), t_of(fb, beat))
        for cb, cd, root, tones in CHORDS[tb]:
            v = voicing(root, tones, 55)
            for k in range(int(cd)):
                if (cb + k) % 2 == 1:
                    for i, m in enumerate(v):
                        place(buf, stereo(S.pluck_fast(m, 0.25, 0.4, bright=0.5, decay=6), -0.4), t_of(fb, cb + k) + i * 0.008)
                for off in (0, 0.5):
                    place(buf, S.bass(root - 12 + 12, TL.BEAT * 0.45, 0.65), t_of(fb, cb + k + off), 0.9)
        for k in range(4):
            if k % 2 == 0:
                place(buf, S.kick(0.7), t_of(fb, k), 0.8)
            else:
                place(buf, stereo(S.snare(0.55), 0.1), t_of(fb, k), 0.7)
            for off in (0, 0.5):
                place(buf, stereo(S.hat(0.35), 0.35), t_of(fb, k + off), 0.8)
    gtr = S.reverb(gtr, S.spring_ir(), 0.35)
    buf = S.reverb(buf + gtr, S.make_ir(0.8, 7, 5000), 0.12)
    buf = S.bp(buf, 120, 7000, 1)
    return gate(buf, *span('1966'))


def m1974():
    buf = np.zeros((N, 2))
    for fb in era_bars('1974'):
        tb = MAP[fb]
        for beat, dur, m in THEME[tb]:
            place(buf, stereo(S.saw_ens(m, dur * TL.BEAT, 0.8, attack=0.06, release=0.4, cutoff=5000), 0.1), t_of(fb, beat))
        for cb, cd, root, tones in CHORDS[tb]:
            v = voicing(root, tones, 55)
            for m in v:
                place(buf, stereo(S.saw_ens(m, cd * TL.BEAT, 0.5, attack=0.3, release=0.8, cutoff=2500), -0.2), t_of(fb, cb))
            for k in range(int(cd)):
                place(buf, S.bass(root - 12 + 12, TL.BEAT * 0.8, 0.6), t_of(fb, cb + k), 0.8)
        for k in range(4):
            place(buf, stereo(S.hat(0.25, open_=(k % 2 == 1)), 0.3), t_of(fb, k + 0.5), 0.6)
            if k % 2 == 0:
                place(buf, S.kick(0.45), t_of(fb, k), 0.6)
    buf = S.reverb(buf, S.make_ir(2.4, 2.4, 6000), 0.35)
    return gate(buf, *span('1974'))


def m1987():
    buf = np.zeros((N, 2))
    for fb in era_bars('1987'):
        tb = MAP[fb]
        for beat, dur, m in THEME[tb]:
            x = S.epiano(m, dur * TL.BEAT, 0.6)
            place(buf, stereo(x, -0.15), t_of(fb, beat), 0.9)
            place(buf, stereo(x, 0.15), t_of(fb, beat) + 0.013, 0.6)
        for cb, cd, root, tones in CHORDS[tb]:
            v = voicing(root, tones, 52)
            arp = (v + [v[0] + 12])
            for k in range(int(cd * 2)):
                m = arp[k % len(arp)]
                place(buf, stereo(S.epiano(m, TL.BEAT * 0.45, 0.3), 0.3 * (1 if k % 2 else -1)), t_of(fb, cb + k * 0.5))
            place(buf, S.bass(root - 12 + 12, cd * TL.BEAT * 0.95, 0.4), t_of(fb, cb), 0.6)
    buf = S.reverb(buf, S.make_ir(2.0, 3.0, 5000), 0.3)
    return gate(buf, *span('1987'))


def piano_part(bars, vel_mel=0.7, vel_lh=0.45, octave=0):
    buf = np.zeros((N, 2))
    for fb in bars:
        tb = MAP[fb]
        for beat, dur, m in THEME[tb]:
            place(buf, stereo(S.piano(m + octave, dur * TL.BEAT * 1.05, vel_mel), 0.12), t_of(fb, beat))
        for cb, cd, root, tones in CHORDS[tb]:
            pat = [0, 7, 12 + tones[1], 7]
            for k in range(int(cd)):
                m = root + pat[k % 4] - 12 + 12
                place(buf, stereo(S.piano(m, TL.BEAT * 1.6, vel_lh * (1.15 if k == 0 else 0.85)), -0.15), t_of(fb, cb + k))
    return buf


def m2026():
    buf = piano_part(era_bars('2026'), 0.62, 0.38)
    buf = S.reverb(buf, S.make_ir(1.8, 3.2, 7000), 0.25)
    return gate(buf, span('2026')[0], span('2026')[1] + 0.5, fade_out=0.6)


def mhero():
    bars = era_bars('hero') + era_bars('end')
    buf = piano_part(bars, 0.8, 0.5)
    strings = np.zeros((N, 2))
    bells = np.zeros((N, 2))
    drums = np.zeros((N, 2))
    for j, fb in enumerate(bars):
        tb = MAP[fb]
        for cb, cd, root, tones in CHORDS[tb]:
            dur = cd * TL.BEAT
            if fb == bars[-1] and cb >= 2:
                dur = cd * TL.BEAT + 3.0     # final chord rings out
            for m in voicing(root, tones, 60):
                place(strings, stereo(S.saw_ens(m, dur, 0.45 + 0.08 * j, attack=0.5, release=1.5, cutoff=3000), -0.3), t_of(fb, cb))
            for m in voicing(root, tones, 72)[:2]:
                place(strings, stereo(S.saw_ens(m, dur, 0.25 + 0.05 * j, attack=0.6, release=1.5, cutoff=4000), 0.35), t_of(fb, cb))
            place(buf, S.bass(root - 12 + 12, dur * 0.95, 0.55), t_of(fb, cb), 0.9)
        for beat, dur, m in THEME[tb]:
            if j >= 1:
                place(bells, stereo(S.bell(m + 12, 1.5, 0.45), 0.25), t_of(fb, beat))
        if fb < bars[-1]:
            for k in range(4):
                if j >= 1:
                    place(drums, S.kick(0.5), t_of(fb, k), 0.6 if k % 2 == 0 else 0.0)
                    if k % 2:
                        place(drums, S.snare(0.4, brush=True), t_of(fb, k), 0.7)
    # final bell sparkle on last chord
    for i, m in enumerate([84, 88, 91, 96]):
        place(bells, stereo(S.bell(m, 3, 0.35), -0.4 + 0.27 * i), TL.bar(bars[-1], 2) + 0.12 * i)
    mix = buf + 0.7 * strings + 0.8 * bells + drums
    mix = S.reverb(mix, S.make_ir(2.8, 2.2, 7000), 0.3)
    # gentle swell into hero
    return gate(mix, span('hero')[0], TL.END, fade_in=0.02, fade_out=1.5)


if __name__ == '__main__':
    import sys
    want = sys.argv[1:] or ['1958', '1966', '1974', '1987', '2026', 'hero']
    fns = {'1958': m1958, '1966': m1966, '1974': m1974, '1987': m1987, '2026': m2026, 'hero': mhero}
    for k in want:
        x = fns[k]().astype(np.float32)
        sf.write(os.path.join(OUT, 'music_%s.wav' % k), x, SR)
        print(k, 'peak', float(np.abs(x).max()))
