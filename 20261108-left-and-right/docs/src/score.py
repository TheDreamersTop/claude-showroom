"""The film as one stereo signal. Left = X, Right = Y.
python score.py out.wav  -> writes the wav and a timeline json (section start times)."""
import sys, json
import numpy as np
from scipy.io import wavfile
from sig import *
import drawings as D

BEAT = 60 / 76.0
rng = np.random.default_rng(7)
TIMELINE = []


def silence(d, pos=(0.0, 0.0)):
    s = np.zeros((N(d), 2)); s[:, 0] = pos[0]; s[:, 1] = pos[1]
    return s


def voice_wave(ph, bright=0.12):
    """A singing line: sine with a little odd harmonic, normalised to ~[-1,1]."""
    w = np.sin(2 * np.pi * ph) + bright * np.sin(6 * np.pi * ph)
    return w / (1 + bright * 0.7)


def vibrato(t, rate=5.2, depth=0.006, delay=0.25, starts=()):
    v = np.sin(2 * np.pi * rate * t) * depth
    return v


# ------------------------------------------------------------------ sections

def wander(d, amp=0.012, rate=0.7, seed=3):
    """Slow (infrasonic) drift: the dot is alive but silent. Smooth noise below ~2 Hz is below hearing."""
    r = np.random.default_rng(seed)
    n = N(d); k = max(4, int(d * rate * 2) + 4)
    from scipy.interpolate import CubicSpline
    xs = np.linspace(0, d, k)
    t = tt(d)
    out = np.stack([CubicSpline(xs, r.normal(0, 1, k))(t), CubicSpline(xs, r.normal(0, 1, k))(t)], 1) * amp
    env = smooth(np.clip(t / 1.0, 0, 1)) * smooth(np.clip((d - t) / 0.8, 0, 1))
    return out * env[:, None]


def s_dot(d=5.0):
    """The scope warms up. A dot. Silence. It drifts a little, as if looking around."""
    w = wander(d, 0.014, 0.6)
    t = tt(d)
    w *= smooth(np.clip((t - 2.0) / 1.2, 0, 1))[:, None]
    return silence(d) + w


LEFT_MOTIF = [  # (beat, beats, note, amp)  slow, lonely, A minor
    (0, 2.0, 'A3', .55), (2, 1.0, 'C4', .5), (3, 2.0, 'B3', .55), (5, 1.0, 'G3', .45),
    (6, 3.0, 'A3', .6),
    (10, 1.0, 'E3', .4), (11, 1.0, 'G3', .45), (12, 1.5, 'A3', .5), (13.5, .5, 'B3', .45), (14, 3.5, 'C4', .55),
    (18, 1.0, 'B3', .45), (19, 1.0, 'G3', .4), (20, 4.0, 'A3', .5),
]
RIGHT_MOTIF = [  # quicker, curious, staccato, higher
    (0, .5, 'E5', .45), (.5, .5, 'G5', .4), (1, 1.0, 'A5', .5), (2.5, .5, 'G5', .4), (3, .5, 'E5', .4),
    (3.5, 1.5, 'D5', .5),
    (5.5, .5, 'E5', .4), (6, .5, 'G5', .4), (6.5, .5, 'A5', .45), (7, .5, 'C6', .5), (7.5, 1.5, 'B5', .5),
    (9.5, .5, 'A5', .4), (10, .5, 'G5', .4), (10.5, 2.0, 'E5', .5),
]


def notes_at(motif, t0=0.0, beat=BEAT, amp=1.0, transpose=1.0, gap=0.92):
    return [(t0 + b * beat, l * beat * gap, hz(n) * transpose, a * amp) for b, l, n, a in motif]


def solo(t, motif_notes, axis, wander=None, vib=0.006, bright=0.12, glide=0.05, rel=0.18, drift_pos=None):
    f, a = melody(t, motif_notes, glide=glide, rel=rel)
    f = f * (1 + vibrato(t, depth=vib))
    ph = cycles(f)
    s = np.zeros((len(t), 2))
    s[:, axis] = a * voice_wave(ph, bright)
    if wander is not None:
        s[:, axis] += wander
    if drift_pos is not None:
        ramp = np.clip(t / 0.3, 0, 1) * np.clip((t[-1] - t) / 0.3, 0, 1)
        s[:, 1 - axis] += drift_pos * smooth(ramp)
    return s


def s_left_alone():
    """Left, alone: one lonely phrase. At the end its line slides right, as if listening for someone."""
    d = 7.2 * BEAT
    t = tt(d)
    mot = [(0, 2.0, 'A3', .55), (2, 1.0, 'C4', .5), (3, 1.5, 'B3', .55), (4.5, 2.2, 'A3', .5)]
    notes = notes_at(mot, 0.35)
    wander = auto(t, [(0, 0), (2.5, -0.05), (4.5, 0.03), (d, 0.0)])
    return solo(t, notes, 0, wander=wander)


def s_right_alone():
    d = 7 * BEAT
    t = tt(d)
    notes = notes_at([n for n in RIGHT_MOTIF if n[0] < 5.5], 0.25)
    hop = np.zeros_like(t)
    for s_, l, f, a in notes:
        m = (t >= s_) & (t < s_ + l + 0.2)
        hop[m] += 0.06 * np.sin(np.pi * np.clip((t[m] - s_) / (l + 0.2), 0, 1))
    side = np.full_like(t, 0.25)
    return solo(t, notes, 1, wander=hop, vib=0.004, bright=0.2, glide=0.02, rel=0.08, drift_pos=side)


RSOLO = dict(vib=0.004, bright=0.2, glide=0.02, rel=0.08)


def s_crossing():
    """They take turns, faster, then sing at once by accident: the beam writhes, a clash. Both freeze."""
    segs = []
    L1 = [(0, .75, 'A3', .5), (.75, .75, 'C4', .5), (1.5, 1.2, 'B3', .5)]
    R1 = [(0, .35, 'E5', .45), (.4, .35, 'G5', .45), (.8, .8, 'A5', .5)]
    t = tt(1.9); segs.append(solo(t, notes_at(L1, 0.05, beat=BEAT * 0.7), 0))
    t = tt(1.4); segs.append(solo(t, notes_at(R1, 0.05, beat=BEAT * 0.7), 1, drift_pos=0.25 * np.ones(len(t)), **RSOLO))
    # the clash: both at once; Right's pitch lurches around, the figure thrashes
    d = 3.5
    t = tt(d)
    fl = hz('A3') * (1 + 0.02 * np.sin(2 * np.pi * 3.1 * t)) * auto(t, [(0, 1), (1.5, 1), (3.3, 0.94)])
    bend = auto(t, [(0, 1.0), (0.4, 1.06), (0.8, 0.97), (1.1, 1.11), (1.4, 1.02), (1.7, 1.15), (2.0, 1.04),
                    (2.4, 1.18), (2.7, 0.99), (3.0, 1.21), (3.3, 1.1)], ease=True)
    fr = hz('Bb3') * bend * (1 + 0.012 * np.sin(2 * np.pi * 6.3 * t))
    aL = auto(t, [(0, 0), (0.1, .5), (3.25, .62), (3.35, 0)])
    aR = auto(t, [(0, 0), (0.25, 0), (0.35, .45), (3.25, .62), (3.35, 0)])
    # they fight: jagged (saw-like) voices, wild vibrato, the size lurching; the beam scribbles
    fl = fl * (1 + 0.05 * np.sin(2 * np.pi * 9.0 * t) * smooth(np.clip(t / 1.0, 0, 1)))
    fr = fr * (1 + 0.07 * np.sin(2 * np.pi * 11.3 * t + 1.0) * smooth(np.clip(t / 1.0, 0, 1)))
    def saw(ph, k=8):
        return sum(((-1) ** (n + 1)) * np.sin(2 * np.pi * n * ph) / n for n in range(1, k + 1)) * 0.6
    lurchL = 1 + 0.25 * np.sin(2 * np.pi * 2.7 * t) * np.sin(2 * np.pi * 0.9 * t)
    lurchR = 1 + 0.3 * np.sin(2 * np.pi * 3.4 * t + 2) * np.sin(2 * np.pi * 1.1 * t)
    s_ = np.stack([aL * lurchL * saw(cycles(fl)), aR * lurchR * saw(cycles(fr), 10)], 1)
    segs.append(s_)
    segs.append(silence(1.3))
    return np.vstack(segs)


def s_tuning():
    """Left offers a note. Right slides toward it. The tangle slows to an ellipse, and locks: a circle."""
    d = 10.4
    t = tt(d)
    f0 = hz('A3')
    phL = cycles(np.full_like(t, f0))
    aL = auto(t, [(0, 0), (0.4, .32), (d, .32)])
    u = np.clip((t - 1.5) / 6.4, 0, 1)
    slip = 20.0 * (1 - u) ** 2.2
    phR = phL + 0.25 + slip
    aR = auto(t, [(0, 0), (1.4, 0), (2.0, .32), (d, .32)])
    grow = auto(t, [(0, 1), (8.2, 1), (10.2, 1.6)])
    x = aL * grow * np.sin(2 * np.pi * phL)
    y = aR * grow * np.sin(2 * np.pi * phR)
    y = np.where(aR < 1e-4, 0, y)
    return np.stack([x, y], 1)


# the interval dance: short, building. (left root, right ratio, beats, detune for 3D spin)
DANCE = [
    ('A2', 2, 2, 0.0008), ('C3', 3 / 2, 2, 0.0015), ('F2', 3, 2, 0.003), ('E2', 5, 2.5, 0.006),
]


def s_dance():
    """Together they find intervals. Each figure is the chord you hear. It builds and spins faster, then resolves."""
    beat = 60 / 84.0
    nb = sum(b for _, _, b, _ in DANCE)
    d = nb * beat + 1.2
    t = tt(d)
    fL = np.zeros_like(t); fR = np.zeros_like(t)
    ks = []; acc = 0
    for root, q, b, dt in DANCE:
        ks.append((acc * beat, hz(root), hz(root) * q * (1 + dt))); acc += b
    ks.append((nb * beat, hz('E3'), hz('E3')))
    prev = ks[0]
    for k, (t0, l, r) in enumerate(ks):
        m = t >= t0
        g = smooth(np.clip((t[m] - t0) / 0.07, 0, 1))
        pl, pr = (ks[k - 1][1], ks[k - 1][2]) if k else (l, r)
        fL[m] = pl + (l - pl) * g
        fR[m] = pr + (r - pr) * g
    phL = cycles(fL); phR = cycles(fR) + 0.25
    diff = phR - phL
    target = np.round(diff[-1] - 0.25) + 0.25
    lock = smooth(np.clip((t - nb * beat - 0.1) / 0.6, 0, 1))
    phR = phL + diff * (1 - lock) + target * lock
    pulse = 1 - 0.10 * np.exp(-((t % beat) / 0.05)) * (t < nb * beat)
    sw = auto(t, [(0, .52), (nb * beat * .3, .55), (nb * beat * .85, .68), (nb * beat, .66), (d, .55)])
    x = sw * pulse * np.sin(2 * np.pi * phL)
    y = sw * pulse * np.sin(2 * np.pi * phR)
    return np.stack([x, y], 1)


SONG = [  # the shared tune for the drawing montage (beats), C major / A minor, 84 bpm
    (0, 1, 'E4'), (1, 1, 'G4'), (2, 2, 'A4'), (4, 1, 'G4'), (5, 1, 'E4'), (6, 2, 'D4'),
    (8, 1, 'C4'), (9, 1, 'D4'), (10, 1, 'E4'), (11, 1, 'G4'), (12, 4, 'E4'),
    (16, 1, 'E4'), (17, 1, 'G4'), (18, 2, 'A4'), (20, 1, 'C5'), (21, 1, 'B4'), (22, 2, 'A4'),
    (24, 1, 'G4'), (25, 1, 'E4'), (26, 1, 'D4'), (27, 1, 'E4'), (28, 4, 'C4'),
]
SONG_TAIL = [(32, 2, 'A3'), (34, 1.5, 'B3'), (35.5, 1.5, 'G3')]
LIFE_BEATS = 37
LIFE_BOUNDS = [0, 4, 12, 18, 26]
FIG_LP = 100


def hold_hands(xl, xr, hold, meet, sh_y=0.12):
    sh_l = np.array([xl, sh_y]); sh_r = np.array([xr, sh_y])
    meet = np.asarray(meet)
    hl = tuple(sh_l + np.array([0.19, -0.19]) * (1 - hold) + (meet - sh_l) * hold)
    hr = tuple(sh_r + np.array([-0.19, -0.19]) * (1 - hold) + (meet - sh_r) * hold)
    return hl, hr


_CIRCLE = None
_HEART = None


def circle_heart(w):
    """A circle that becomes a heart as w goes 0 -> 1 (paths aligned once)."""
    global _CIRCLE, _HEART
    if _CIRCLE is None:
        _HEART = D.heart(3072)
        c = D.circle(3072); c.p = c.p * 0.85
        _CIRCLE = morph_paths(_HEART, c)
    q = Path.__new__(Path); q.M = 3072
    q.p = _CIRCLE.p * (1 - w) + _HEART.p * w
    return q


# a floor: every beam jump between figures runs along it, so the jumps vanish into the ground
FLOOR = np.stack([np.linspace(-0.92, 0.92, 60), np.full(60, -0.57)], 1)


def life_scene(tb, beat):
    """Return (Path, scale, octave) for absolute time tb within the life montage."""
    b = tb / beat
    M = 3072
    if b < 4:  # A: the circle becomes a heart, and it beats
        w = smooth(np.clip(b / 1.2, 0, 1))
        hb = 1 + (0.07 * np.exp(-((b % 1) * 6)) + 0.04 * np.exp(-(((b - 0.3) % 1) * 6))) * (b > 1.2)
        return circle_heart(w), 0.62 * hb, 0.5
    if b < 12:  # B: two people walk in from either side and take hands; a heart grows above them
        u = smooth(np.clip((b - 4.4) / 5.4, 0, 1))
        xl = -0.78 + 0.45 * u; xr = 0.78 - 0.45 * u
        walking = 0.42 * (1 - smooth(np.clip((b - 9.4) / 0.6, 0, 1)))
        wp = b * 0.75
        hold = smooth(np.clip((b - 9.6) / 0.8, 0, 1))
        hl, hr = hold_hands(xl, xr, hold, (0.0, -0.02))
        if hold == 0:
            hl = hr = None
        ends = ('hr', 'hl') if hold > 0.5 else ('fr', 'fl')
        st = (D.walker(xl, wp, hand_r=hl, swing=walking, start=ends[0])
              + D.walker(xr, wp + 0.5, hand_l=hr, swing=walking, start=ends[1]))
        hs = smooth(np.clip((b - 10.0) / 1.6, 0, 1))
        if hs > 0.01:
            st.append(D.heart_strokes(0.0, 0.62, 0.17 * hs))
        return strokes_path(st, M=M, lowpass=FIG_LP, greedy=False), 0.84, 0.5
    if b < 18:  # C: a home on a hill; smoke from the chimney
        return D.home_path(tb, M=M, lowpass=FIG_LP), 0.82, 0.5
    if b < 26:  # D: a child between them, growing up
        g = smooth(np.clip((b - 18.4) / 6.8, 0, 1))
        sc = 0.32 + 0.36 * g
        cy = -0.57 + 0.57 * sc
        hl = (-0.2 * (0.6 + sc), cy + 0.02 * sc); hr = (0.2 * (0.6 + sc), cy + 0.02 * sc)
        st = (D.walker(-0.45, 0, hand_r=hl, swing=0, start='fr') + [FLOOR]
              + D.walker(0.0, 0, s=sc, cy=cy, hand_l=hl, hand_r=hr, head_r=0.16, swing=0, start='fl')
              + D.walker(0.45, 0, hand_l=hr, swing=0, start='fl'))
        return strokes_path(st, M=M, lowpass=FIG_LP, greedy=False, jump_w=1.0), 0.82, 0.5
    # E: the child lets go and walks out to the right; stops, turns, waves (a big slow wave);
    #    then walks away into the distance, getting smaller until it is gone. The two step together.
    u = b - 26
    sc0 = 0.68
    walk1 = smooth(np.clip(u / 2.4, 0, 1))
    away = smooth(np.clip((u - 6.2) / 3.4, 0, 1))
    cx = 0.0 + 0.86 * walk1 + 0.06 * away
    sc = sc0 * (1 - away) + 0.001 * away
    horizon = -0.08
    feet = -0.57 * (1 - away) + horizon * away
    cy = feet + 0.57 * sc
    moving = (0.3 < u < 2.4) or (u > 6.2)
    swing_c = 0.42 if moving else 0.0
    hr_c = None
    if 2.8 < u < 6.0:
        up = smooth(np.clip((u - 2.8) / 0.5, 0, 1)) * smooth(np.clip((6.0 - u) / 0.4, 0, 1))
        w = np.sin(2 * np.pi * (u - 2.8) * 0.9)
        shc = np.array([cx, cy + 0.12 * sc])
        down = np.array([0.19, -0.19]) * sc
        ang = 0.95 + 0.38 * w                      # radians from straight up: up and out, swinging
        raised = 0.3 * sc * np.array([np.sin(ang), np.cos(ang)])
        hr_c = tuple(shc + down * (1 - up) + raised * up)
    v = smooth(np.clip((u - 6.5) / 3.0, 0, 1))
    xl = -0.45 + 0.12 * v; xr = 0.45 - 0.12 * v
    hold = smooth(np.clip((u - 9.4) / 0.8, 0, 1))
    hl, hr = hold_hands(xl, xr, hold, (0.0, -0.05))
    if hold == 0:
        hl = hr = None
    rel = 1 - smooth(np.clip(u / 0.9, 0, 1))      # still holding the child's hands, then letting go
    if rel > 0 and hold == 0:
        cyc_ = -0.57 + 0.57 * sc0
        chl = np.array([cx - 0.2 * (0.6 + sc0), cyc_ + 0.02 * sc0]); chr_ = np.array([cx + 0.2 * (0.6 + sc0), cyc_ + 0.02 * sc0])
        dl = np.array([xl, 0.12]) + np.array([0.19, -0.19]); dr = np.array([xr, 0.12]) + np.array([-0.19, -0.19])
        hl = tuple(dl + (chl - dl) * rel); hr = tuple(dr + (chr_ - dr) * rel)
    st = D.walker(xl, 0, hand_r=hl, swing=0, start='fr') + [FLOOR] + D.walker(xr, 0, hand_l=hr, swing=0, start='fl')
    jws = [1.0] * len(st)
    sc = max(sc, 0.004)      # the child never leaves the drawing: far away it is a speck at the horizon
    if True:
        st = st + D.walker(cx, u * 0.8, s=sc, cy=cy, head_r=0.16, swing=swing_c, hand_r=hr_c, start='fl')
        # on the floor the jump to the child is traced along the ground; once it walks into the distance
        # (feet leave the floor line) the jump is made nearly instant instead
        jws.append(float(np.exp(np.log(1.0) * (1 - min(1, away / 0.25)) + np.log(0.0004) * min(1, away / 0.25))))
    return strokes_path(st, M=M, lowpass=FIG_LP, greedy=False, jump_w=jws), 0.82, 0.5


def dissolve_mask(n, w, k0=0, chunk=96):
    """Per-sample choice between two drawings: the beam spends a share w of its time on the new one."""
    idx = (np.arange(n) + k0) // chunk
    h = (np.sin(idx * 12.9898) * 43758.5453) % 1.0
    return h < w


def s_life():
    """Together they can draw. Each picture is traced at the pitch of their song."""
    beat = 60 / 84.0
    total = LIFE_BEATS * beat
    t = tt(total)
    notes = [(b * beat, l * beat * 0.95, n, 1.0) for b, l, n in SONG + SONG_TAIL]
    f, a = melody(t, notes, glide=0.05, att=0.02, rel=0.25, floor=0.8)
    bounds = LIFE_BOUNDS[:4]      # the goodbye continues the family scene: no dissolve there
    blk = 800
    out = np.zeros((len(t), 2))
    octv = np.zeros(len(t))
    info = []
    for k0 in range(0, len(t), blk):
        tb = t[min(k0 + blk // 2, len(t) - 1)]
        info.append(life_scene(tb, beat))
        octv[k0:k0 + blk] = info[-1][2]
    from scipy.ndimage import uniform_filter1d
    octv = uniform_filter1d(octv, N(0.25))
    ph = cycles(f * octv)
    nb = (len(t) + blk - 1) // blk
    cache = {}

    def prev_scene(B):
        if B not in cache:
            cache[B] = life_scene((B - 0.01) * beat, beat)
        return cache[B]

    def block_pos(bi, phs, k0):
        tb = t[min(bi * blk, len(t) - 1)]
        P, sc, _ = info[bi]
        bnow = tb / beat
        for B in bounds[1:]:
            if B <= bnow < B + 1.2:
                w = smooth((bnow - B) / 1.2)
                Pp, scp, _ = prev_scene(B)
                m = dissolve_mask(len(phs), w, k0)
                A = Pp.at(phs) * scp; Bq = P.at(phs) * sc
                return np.where(m[:, None], Bq, A)
        return P.at(phs) * sc

    for bi in range(nb):
        k0 = bi * blk; k1 = min(k0 + blk, len(t))
        phs = ph[k0:k1]
        cur = block_pos(bi, phs, k0)
        if bi > 0:
            prv = block_pos(bi - 1, phs, k0)
            r = (np.arange(k1 - k0) / blk)[:, None]
            cur = prv * (1 - r) + cur * r
        out[k0:k1] = cur * a[k0:k1, None]
    return out


def s_drift():
    """They let go. Each slides toward its own edge, falls out of tune, and flattens back into a line:
    the left one into a horizontal line (its partner's channel gone), the right one into a vertical line."""
    d = 10.0
    t = tt(d)
    blk = 800
    f = hz('G3') * 0.5
    phL = cycles(np.full_like(t, f))
    detune = auto(t, [(0, 1.0), (0.8, 1.0), (6.5, 1.075), (d, 1.09)])
    phR = cycles(f * detune)
    out = np.zeros((len(t), 2))
    sq = auto(t, [(0, 0), (4.4, 0), (6.0, 1.0), (d, 1.0)])     # squash: 1 = flattened into a line
    sep = auto(t, [(0, 0), (0.6, 0), (6.0, 1.0), (d, 1.0)])
    letgo = auto(t, [(0, 1), (0.2, 1), (1.0, 0)])
    amp = auto(t, [(0, 0.82), (d - 0.6, 0.82), (d, 0.0)])
    fadeR = auto(t, [(0, 1), (8.0, 1), (8.9, 0)])     # the right line goes quiet first
    fadeL = auto(t, [(0, 1), (8.9, 1), (9.8, 0)])
    nbk = (len(t) + blk - 1) // blk
    cyc = int(SR / f)          # switch figures once per full trace, so the beam jumps rarely

    def figs(k):
        i = min(k * blk, len(t) - 1)
        xl = -0.33 - 0.19 * sep[i]; xr = 0.33 + 0.19 * sep[i]
        hold = letgo[i]
        hl, hr = hold_hands(xl, xr, hold, (0.0, -0.05))
        PL = strokes_path(D.walker(xl, 0, hand_r=hl, swing=0, start='fr'), M=2048, lowpass=FIG_LP, greedy=False)
        PR = strokes_path(D.walker(xr, 0, hand_l=hr, swing=0, start='fl'), M=2048, lowpass=FIG_LP, greedy=False)
        return PL, PR, xl, xr

    for k in range(nbk):
        k0 = k * blk; k1 = min(k0 + blk, len(t))
        PL, PR, xl, xr = figs(k)
        A = PL.at(phL[k0:k1]); B = PR.at(phR[k0:k1])
        s_ = sq[k0:k1, None]
        # each figure unfolds into a plain line: its voice becomes a pure tone again, in one ear
        lineA = np.stack([xl + 0.36 * np.sin(2 * np.pi * phL[k0:k1]), np.zeros(k1 - k0)], 1)
        lineB = np.stack([np.full(k1 - k0, xr), 0.5 * np.sin(2 * np.pi * phR[k0:k1])], 1)
        A = A * (1 - s_) + lineA * s_
        B = B * (1 - s_) + lineB * s_
        m = (((np.arange(k0, k1)) // cyc) % 2 == 0)[:, None]
        # each line shrinks where it stands: the right one first, then the left one
        B[:, 1:2] = B[:, 1:2] * fadeR[k0:k1, None]
        A[:, 0:1] = xl + (A[:, 0:1] - xl) * fadeL[k0:k1, None]
        m = m | (fadeR[k0:k1, None] < 0.02)            # once the right one is gone, only the left is drawn
        out[k0:k1] = np.where(m, A, B) * amp[k0:k1, None]
    segs = [out, silence(1.2)]
    return np.vstack(segs)


ENDING = {}


def s_together_again():
    """Left, alone, sings the first notes of their song. Right answers: one circle again.
    They try to draw the heart again, lopsided and shaky, and laugh it back into a circle.
    Years. One voice falters (the circle sags toward a line); the other holds the note; it comes back
    for one breath. Then both shrink together into a dot."""
    beat = 60 / 72.0
    ph1 = [(b, l, n) for b, l, n in SONG if b < 4]
    notes = [(0.25 + b * beat, l * beat * .95, hz(n) / 2, .5) for b, l, n in ph1]
    d1 = 0.25 + 4 * beat + 0.3
    t = tt(d1)
    segA = solo(t, notes, 0)
    # ---- one continuous take to the end
    T_join = 0.0
    T_heart0 = 4.6; T_heart1 = 7.6          # the shaky heart
    T_hold = 9.6                             # melody over; steady circle
    T_falter0 = 11.4; T_falter1 = 13.8       # right voice sags
    T_back = 15.2                            # restored, one breath
    T_shrink0 = 16.8; T_shrink1 = 21.3       # both shrink together
    d2 = T_shrink1 + 1.5
    t = tt(d2)
    ph2 = [(b - 4, l, n) for b, l, n in SONG if 4 <= b < 12]
    nts = [(b * beat, l * beat * .97, hz(n) / 2, 1.0) for b, l, n in ph2]
    f_mel, a_mel = melody(t, nts, glide=0.06, rel=0.4, floor=0.85)
    t_m = 8 * beat
    f_old = auto(t, [(0, hz('E3') / 2), (T_hold, hz('E3') / 2), (T_falter0, hz('E3') / 2), (T_shrink1, hz('A2') / 2.4), (d2, hz('A2') / 2.4)])
    wmel = auto(t, [(0, 1), (t_m - 0.4, 1), (t_m + 0.6, 0)])
    f = f_mel * wmel + f_old * (1 - wmel)
    a = a_mel * wmel + 1.0 * (1 - wmel)
    phL = cycles(f)
    # right voice: enters, and later falters
    aR = auto(t, [(0, 0), (1.0 * beat, 0), (2.6 * beat, 1.0), (T_falter0, 1.0), (T_falter1, 0.7), (T_back, 1.0), (d2, 1.0)])
    # the falter: the right voice stutters (drop-outs, more and more often), then flatlines, then comes back
    gate = np.ones_like(t)
    gaps = [(T_falter0 + 0.30, 0.07), (T_falter0 + 0.85, 0.09), (T_falter0 + 1.25, 0.12), (T_falter0 + 1.55, 0.10),
            (T_falter0 + 1.80, 0.16), (T_falter0 + 2.05, 0.12), (T_falter1, 0.75)]
    for g0, gl in gaps:
        e = smooth(np.clip((t - g0) / 0.02, 0, 1)) * smooth(np.clip((g0 + gl - t) / 0.03, 0, 1))
        gate = np.minimum(gate, 1 - e)
    aR = aR * gate
    slip = 3.0 * (1 - smooth(np.clip(t / (4 * beat), 0, 1)))
    # the falter also lets Right drift a little out of tune, so the figure wobbles
    wob = 0.6 * auto(t, [(0, 0), (T_falter0, 0), (T_falter1, 1), (T_back, 0)]) * np.sin(2 * np.pi * 0.7 * t)
    phR = phL + 0.25 + slip + wob
    # shape: circle, then the heart attempt (lopsided, trembling), back to circle
    hw = auto(t, [(0, 0), (T_heart0, 0), (T_heart0 + 0.9, 1), (T_heart1 - 0.7, 1), (T_heart1, 0)])
    size = auto(t, [(0, .44), (T_hold, .42), (T_shrink0, .40), (T_shrink1, 0.0), (d2, 0)])
    out = np.zeros((len(t), 2))
    blk = 800
    rng_ = np.random.default_rng(11)
    for k0 in range(0, len(t), blk):
        k1 = min(k0 + blk, len(t))
        w = hw[k0]
        if w <= 0:
            X = np.sin(2 * np.pi * phL[k0:k1]); Y = np.sin(2 * np.pi * phR[k0:k1])
        else:
            P = circle_heart(w)
            q = Path.__new__(Path); q.M = P.M
            # a failed attempt: the left lobe comes out, the right lobe stays pinched, the tip never closes,
            # and the whole outline shakes
            C = _CIRCLE.p; Hh = _HEART.p
            wpt = np.full(len(C), w)
            right_lobe = (Hh[:, 0] > 0.05) & (Hh[:, 1] > -0.1)
            tip = Hh[:, 1] < -0.35
            wpt = np.where(tip, w * 0.35, wpt)
            p = C * (1 - wpt[:, None]) + Hh * wpt[:, None]
            p[right_lobe] = p[right_lobe] * (1 - 0.22 * w)
            ph_ = np.arange(len(C)) / len(C)
            shake = 0.035 + 0.03 * w
            p[:, 0] += w * shake * np.sin(2 * np.pi * (ph_ * 5 + t[k0] * 7.0))
            p[:, 1] += w * shake * np.sin(2 * np.pi * (ph_ * 3 - t[k0] * 5.3))
            q.p = p / 0.85
            # heart is drawn at the same rate on both channels (one voice), the circle by phase offset
            X = q.at(phL[k0:k1])[:, 0]; Y = q.at(phL[k0:k1])[:, 1]
            Xc = np.sin(2 * np.pi * phL[k0:k1]); Yc = np.sin(2 * np.pi * phR[k0:k1])
            X = X * w + Xc * (1 - w); Y = Y * w + Yc * (1 - w)
        out[k0:k1, 0] = X; out[k0:k1, 1] = Y * aR[k0:k1]
    out *= (size * a)[:, None]
    segB = out
    ENDING['dot_start'] = d1 + T_shrink1
    ENDING['len'] = d1 + d2
    return xfade(segA, segB, 0.05)


def xdissolve(a, b, d):
    """Join a and b: for d seconds the beam spends a growing share of its time on b (a dissolve)."""
    k = N(d)
    w = smooth(np.linspace(0, 1, k))
    m = dissolve_mask(k, w)[:, None]
    mid = np.where(m, b[:k], a[-k:])
    return np.vstack([a[:-k], mid, b[k:]])


def build():
    secs = [
        ('dot', s_dot(2.5), 0.0),
        ('left', s_left_alone(), 0.0),
        ('rest1', silence(0.6), 0.0),
        ('right', s_right_alone(), 0.0),
        ('crossing', s_crossing(), 0.0),
        ('tuning', s_tuning(), 0.0),
        ('dance', s_dance(), 0.12),
        ('life', s_life(), -0.6),
        ('drift', s_drift(), -0.8),
        ('together', s_together_again(), 0.0),
        ('end', silence(0.6), 0.0),
    ]
    out = None; tl = []
    for name, s_, xf in secs:
        if out is None:
            tl.append((name, 0.0)); out = s_; continue
        start = len(out) / SR - xf
        tl.append((name, round(start, 3)))
        if xf < 0:
            start = len(out) / SR + xf
            tl[-1] = (name, round(start, 3))
            out = xdissolve(out, s_, -xf)
        else:
            out = xfade(out, s_, xf) if xf > 0 else np.vstack([out, s_])
    return out, tl


if __name__ == '__main__':
    out, tl = build()
    path = sys.argv[1] if len(sys.argv) > 1 else 'renders/audio.wav'
    g = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    peak = np.abs(out).max()
    print('dur %.2f s  peak %.3f' % (len(out) / SR, peak))
    wavfile.write(path, SR, (out * g).astype(np.float32))
    tog = dict(tl)['together']
    meta = {'timeline': tl, 'gain': g, 'dur': len(out) / SR, 'dot_start': tog + ENDING['dot_start']}
    json.dump(meta, open(path + '.json', 'w'), indent=1)
    print('dot starts at %.2f' % meta['dot_start'])
    for n, s_ in tl:
        print('%6.2f  %s' % (s_, n))
