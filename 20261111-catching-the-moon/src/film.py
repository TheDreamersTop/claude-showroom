"""The film as code: scene(t) -> (shapes, cam, lamp, moon, moon_shapes)."""
import numpy as np
from engine import Shape, Cam, Lamp, Moon, mat, apply, circle, ellipse, catmull
import puppets as P
import engine

FPS = 24
DUR = 71.0

# ------------------------------------------------------------------ beat times (seconds)
T = dict(
    strike=0.6, open_cut=2.8, title_pull=4.8, set_in=6.4, boat_in=8.4, boat_stop=12.6,
    notice=13.0, scoop1=15.6, reach=18.8, shadow1=22.0, land=29.2,
    takeoff=34.4, bumps=37.0, bumps_end=38.8, catch=41.2, hand=43.8, dark=47.6, window=48.2,
    release=53.4, look=59.4, fade=60.8, card=62.2, end=66.0, sting=66.6, sting_end=70.4)
BUMP_DUR = T['bumps_end'] - T['bumps']
PLANT0 = np.array([-48.0, 30.0])     # the real moth sits on the screen from the start
PLANT1 = np.array([-30.0, 27.0])

MOON_C = np.array([40.0, 33.0])
REFL_C = np.array([40.0, -28.5])
P.MOON_C = MOON_C


# ------------------------------------------------------------------ animation helpers
def ss(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def lin(x):
    return np.clip(x, 0.0, 1.0)


def kf(t, keys, ease=ss):
    """Piecewise interpolation over [(time, value), ...]."""
    if t <= keys[0][0]:
        return np.asarray(keys[0][1], float)
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t <= t1:
            u = ease((t - t0) / max(t1 - t0, 1e-6))
            return np.asarray(v0, float) * (1 - u) + np.asarray(v1, float) * u
    return np.asarray(keys[-1][1], float)


def spline(t, keys):
    """Catmull-Rom through keyframes (time, vec)."""
    ts = [k[0] for k in keys]
    vs = [np.asarray(k[1], float) for k in keys]
    if t <= ts[0]:
        return vs[0]
    if t >= ts[-1]:
        return vs[-1]
    i = int(np.searchsorted(ts, t) - 1)
    i = max(0, min(i, len(ts) - 2))
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    p0 = vs[max(i - 1, 0)]
    p1, p2 = vs[i], vs[i + 1]
    p3 = vs[min(i + 2, len(vs) - 1)]
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def nz(t, seed=0.0):
    """Smooth pseudo-noise in [-1, 1]."""
    return (np.sin(t * 1.7 + seed * 3.1) * 0.5 + np.sin(t * 2.9 + seed * 1.3 + 1.0) * 0.3 + np.sin(t * 5.3 + seed * 7.7) * 0.2)


def impulse(t, t0, amp, freq=1.6, decay=1.4):
    if t < t0:
        return 0.0
    d = t - t0
    return amp * np.exp(-d * decay) * np.sin(2 * np.pi * freq * d)


# ------------------------------------------------------------------ lamp
def lamp_at(t):
    if t < T['strike']:
        return Lamp(power=0.0)
    # match flare then flame catching
    p = 1.12 * ss((t - T['strike'] - 0.2) / 1.6)
    flare = 0.5 * np.exp(-max(t - T['strike'], 0) * 6.0) if t >= T['strike'] else 0
    fl = 1 + 0.035 * nz(t * 4.0, 1) + 0.02 * nz(t * 11.0, 2)
    jx, jy = 0.18 * nz(t * 6, 3), 0.25 * nz(t * 5, 4)
    # moth wing-wind gutters the flame during the bumps
    ms = moth_state(t)
    if isinstance(ms, tuple) and ms[2] > 118:
        close = ss((ms[2] - 124) / 18.0)
        fl *= 1 - 0.3 * close * (0.6 + 0.4 * np.sin(t * 37))
        jx += 1.2 * close * nz(t * 19, 5)
        jy += 1.0 * close * nz(t * 23, 6)
    # the puppeteer's fingers pinch the flame
    if t >= T['dark'] - 0.35:
        u = (t - (T['dark'] - 0.35)) / 0.35
        fl *= max(0.0, 1 - ss(u)) * (0.7 + 0.3 * np.sin(t * 61))
    if t >= T['dark']:
        fl = 0.0
    if t >= T['sting']:
        u = t - T['sting']
        fl = (1 + 0.035 * nz(t * 4.0, 1)) * ss(u / 0.5)
        p, flare = 1.12, 0.4 * np.exp(-u * 6)
    return Lamp(x=jx, y=6.0 + jy, power=1.12 * (p + flare) * fl)       # warmer, brighter screen (v8 grade)


# ------------------------------------------------------------------ moth
def scr2world(S, z, lamp_xy=(0.0, 6.0), L=150.0):
    m = L / (L - z)
    c = np.array(lamp_xy)
    return c + (np.asarray(S, float) - c) / m


SH_ = T['shadow1']
MOTH_KEYS = [
    (SH_, (PLANT1[0], PLANT1[1], 0.3)),
    (SH_ + 0.45, (PLANT1[0] + 2, PLANT1[1] + 3, 3.0)),
    (SH_ + 1.0, (PLANT1[0] + 6, PLANT1[1], 30.0)),
    (SH_ + 1.8, (-15, 20, 104)),
    (SH_ + 2.6, (4, 16, 126)),
    (SH_ + 3.6, (62, 14, 124)),
    (SH_ + 4.4, (20, 32, 100)),
    (SH_ + 5.3, (8, 40, 58)),
    (SH_ + 6.2, (52, 30, 16)),
    (SH_ + 6.8, (MOON_C[0] - 5, MOON_C[1] - 1, 3.5)),
    (T['land'], (MOON_C[0], MOON_C[1] - 0.5, 0.3)),
    (T['takeoff'], (MOON_C[0], MOON_C[1] - 0.5, 0.3)),
    (T['takeoff'] + 0.45, (31, 26, 1.0)),
    (T['takeoff'] + 1.0, (21, 9, 1.6)),
    (T['takeoff'] + 1.5, (30, 4, 1.4)),
    (T['takeoff'] + 1.8, (12, 10, 5.0)),
    (T['takeoff'] + 2.3, (2, 16, 55)),
    (T['bumps'], (4, 10, 126)),
]


def plant_pos(t):
    """Crawling a few steps now and then while the play goes on."""
    steps = [(6.2, 7.0), (12.6, 13.3), (24.8, 25.6)]
    u = 0.0
    for a, b in steps:
        u += ss((t - a) / (b - a)) / len(steps)
    return PLANT0 + (PLANT1 - PLANT0) * u, any(a <= t < b for a, b in steps)


def moth_state(t):
    """(screen x, screen y, z, flap, rot, scale)."""
    if t >= T['sting']:
        if t < T['sting'] + 1.5:
            return None
        ST = T['sting']
        v = spline(t, [(ST + 1.5, (MOON_C[0] - 34, MOON_C[1] - 12, 40)), (ST + 2.2, (MOON_C[0] - 8, MOON_C[1] - 2, 6)),
                       (ST + 2.8, (MOON_C[0], MOON_C[1] - 0.5, 0.3)), (T['sting_end'], (MOON_C[0], MOON_C[1] - 0.5, 0.3))])
        if t >= ST + 2.8:
            return v[0], v[1], v[2], 0.35 + 0.35 * (0.5 + 0.5 * np.sin((t - ST) * 1.3)), 0.0, 0.62
        return v[0], v[1], v[2], np.arccos(0.74 + 0.26 * np.cos(t * 2 * np.pi * 7.0)), 0.2 * nz(t, 60), 0.62
    if t < MOTH_KEYS[0][0]:
        p, crawling = plant_pos(t)
        ph = 0.95 + (0.12 * np.sin(t * 21) if crawling else 0.0)
        if 17.0 < t < 17.9:
            ph = 0.95 - 0.6 * np.sin(np.pi * (t - 17.0) / 0.9)       # one slow wing flex
        return p[0], p[1], 0.3, ph, -0.5 + 0.3 * u_rot(t), 0.62
    if t < T['bumps']:
        v = spline(t, MOTH_KEYS)
        sx, sy, z = v
        resting = T['land'] <= t < T['takeoff']
        if resting:
            # slow wing breathing while resting
            ph = 0.35 + 0.35 * (0.5 + 0.5 * np.sin((t - T['land']) * 1.3))
            if T['land'] + 2.0 < t < T['land'] + 3.2:
                ph = 0.2 + 1.0 * np.sin(np.pi * (t - T['land'] - 2.0) / 1.2)  # a big slow flex
            return sx, sy, z, ph, 0.0, 0.62
        flap = np.arccos(0.74 + 0.26 * np.cos(t * 2 * np.pi * 7.0))
        sx += 4.0 * nz(t * 3, 11) * (1 + z / 40)
        sy += 3.0 * nz(t * 3.4, 12) * (1 + z / 40)
        return sx, sy, z, flap, 0.25 * nz(t * 2, 13), 0.62
    if t < T['bumps_end']:
        u = t - T['bumps']
        sx = 4 + 18 * nz(u * 1.1, 14)
        sy = 10 + 12 * nz(u * 1.3, 15)
        z = 128 + 10.0 * np.sin(2 * np.pi * 1.15 * u) * (0.65 + 0.35 * nz(u, 16))
        return sx, sy, z, np.arccos(0.75 + 0.25 * np.cos(t * 2 * np.pi * 7.5)), 0.3 * nz(u * 3, 17), 0.62
    # swoop down toward the screen to be caught
    keys = [(T['bumps_end'], (4 + 18 * nz(BUMP_DUR * 1.1, 14), 10 + 12 * nz(BUMP_DUR * 1.3, 15), 131.0)),
            (T['catch'] - 2.0, (-24, 14, 80)), (T['catch'] - 1.0, (2, 4, 18)),
            (T['catch'] - 0.35, tuple(net_center(T['catch']) + [-7.0, 2.0]) + (3.0,)),
            (T['catch'], tuple(net_center(T['catch'])) + (0.6,))]
    if t < T['catch']:
        v = spline(t, keys)
        return v[0], v[1], v[2], np.arccos(0.6 + 0.4 * np.cos(t * 2 * np.pi * 7.0)), 0.2, 0.62
    return 'net'


def u_rot(t):
    p, _ = plant_pos(t)
    return (p[0] - PLANT0[0]) / (PLANT1[0] - PLANT0[0])


# ------------------------------------------------------------------ fisherman animation curves
def rowing(t):
    return np.sin(2 * np.pi * (t - T['boat_in']) / 2.3)


def boat_state(t):
    x = kf(t, [(T['boat_in'], -125.0), (T['boat_stop'], 17.0)], ease=lambda u: 1 - (1 - lin(u)) ** 2.2)
    x = float(x)
    bob = 0.45 * np.sin(1.25 * t) + 0.2 * np.sin(2.1 * t + 1)
    rock = 0.02 * np.sin(1.05 * t + 0.4)
    rock += impulse(t, T['scoop1'] + 0.1, -0.07)
    rock += impulse(t, T['catch'] + 0.65, 0.12, freq=1.4, decay=1.1)
    if T['set_in'] <= t < T['boat_in']:
        pass
    return x, -21.5 + bob, rock


# pose keys: (time, [lean, head, aNs, aNe, aFs, aFe, tool_rot, crouch, jump, tiptoe])
REST = [0.05, 0.0, 0.6, 1.25, -0.45, 0.5, 0.3, 0.0, 0.0, 0.0]


def pose_keys():
    S1, R, SH, L = T['scoop1'], T['reach'], T['shadow1'], T['land']
    TO, B, C = T['takeoff'], T['bumps'], T['catch']
    k = []
    add = lambda tt, **kw: k.append((tt, kw))
    add(0.0)
    add(T['notice'] + 0.0, head=0.0)
    add(T['notice'] + 0.6, head=-0.32, lean=0.12)                 # notices reflection
    add(T['notice'] + 1.2, head=-0.36, lean=0.15)
    add(T['notice'] + 1.7, head=0.12, lean=0.0)                   # glance up at the moon
    add(S1 - 0.9, head=-0.3, lean=0.05, aNs=0.9, aNe=0.9, tool_rot=1.2)   # wind-up
    add(S1 - 0.15, head=-0.35, lean=0.32, aNs=1.25, aNe=0.15, tool_rot=2.45, crouch=0.15)  # plunge
    add(S1 + 0.5, head=-0.35, lean=0.35, aNs=1.25, aNe=0.15, tool_rot=2.5, crouch=0.15)
    add(S1 + 1.2, head=0.05, lean=0.05, aNs=1.4, aNe=0.9, tool_rot=0.85)  # lift: empty net in front of face
    add(S1 + 2.4, head=0.12, lean=0.0, aNs=1.4, aNe=0.95, tool_rot=0.8)   # stares at it
    add(S1 + 2.8, head=-0.3, lean=0.1, aNs=0.9, aNe=0.9, tool_rot=1.1)
    add(R - 0.2, head=0.0, lean=0.0)
    add(R + 0.6, head=0.55, lean=-0.1)                                 # looks up at the moon
    add(R + 1.2, head=0.55, lean=-0.12, aNs=2.5, aNe=0.15, tool_rot=0.45, aFs=0.4)  # reach
    add(R + 1.9, head=0.6, lean=-0.16, aNs=2.65, aNe=0.05, tool_rot=0.42, tiptoe=2.2, aFs=1.0, aFe=0.3)
    add(R + 2.6, head=0.62, lean=-0.18, aNs=2.7, aNe=0.0, tool_rot=0.40, tiptoe=2.6, aFs=1.1, aFe=0.3)
    add(SH - 0.3, head=0.2, lean=0.12, aNs=0.7, aNe=1.15, tool_rot=0.3, tiptoe=0.0, aFs=-0.45, aFe=0.5)  # slump
    add(SH + 1.2, head=0.3, lean=0.05)
    add(SH + 2.0, head=0.55, lean=-0.12)                                # looks up as the shadow swells
    add(SH + 2.8, head=0.6, lean=-0.28, aFs=1.5, aFe=1.7)              # recoils, arm up
    add(SH + 3.9, head=-0.45, lean=0.55, crouch=1.0, aFs=2.6, aFe=2.2, aNs=0.4, aNe=1.6, tool_rot=0.5)  # ducks, arm over hat
    add(L + 1.2, head=-0.45, lean=0.55, crouch=1.0, aFs=2.6, aFe=2.2, aNs=0.4, aNe=1.6, tool_rot=0.5)
    add(L + 2.0, head=0.2, lean=0.25, crouch=0.6, aFs=1.6, aFe=1.8)     # peeks
    add(L + 2.6, head=0.42, lean=0.1, crouch=0.2, aFs=0.0, aFe=0.8, aNs=0.6, aNe=1.2, tool_rot=0.35)
    add(L + 3.2, head=0.55, lean=0.0, crouch=0.0)                       # sees the tiny moth in the moon
    add(L + 3.6, head=0.75, lean=-0.05)                                 # head tilt
    add(TO - 1.1, head=0.6, lean=-0.05, aNs=1.9, aNe=0.4, tool_rot=0.65, tiptoe=1.0)  # sneaks the net up
    add(TO + 0.2, head=0.6, lean=-0.1, aNs=2.3, aNe=0.2, tool_rot=0.75, tiptoe=1.6)
    add(TO + 0.8, head=0.2, lean=0.1, aNs=1.0, aNe=1.0, tool_rot=0.2, tiptoe=0.0, aFs=1.8, aFe=1.4)   # swats
    add(TO + 1.3, head=-0.2, lean=-0.2, aFs=2.6, aFe=0.4)
    add(TO + 1.8, head=0.3, lean=0.2, aFs=0.6, aFe=1.2)
    add(TO + 2.6, head=0.4, lean=0.0, aFs=-0.1, aFe=0.8)
    add(B + 0.6, head=0.35, lean=0.0)
    add(B + 1.4, head=0.25, lean=0.05, aFs=1.7, aFe=2.3)       # hand to face: worried
    add(C - 1.6, head=0.1, lean=0.15, aFs=-0.3, aFe=0.8, aNs=0.6, aNe=1.2, tool_rot=0.3, crouch=0.35)  # gathers
    add(C - 0.6, head=0.4, lean=-0.15, aNs=2.6, aNe=0.2, tool_rot=0.2, crouch=0.0, jump=9.0, aFs=1.0)  # leaps
    add(C, head=0.2, lean=0.2, aNs=1.9, aNe=0.1, tool_rot=1.1, jump=11.0, aFs=0.4)                     # swing
    add(C + 0.6, head=-0.05, lean=0.15, aNs=1.3, aNe=0.4, tool_rot=1.35, jump=0.0, crouch=0.4)       # lands
    add(C + 1.4, head=0.15, lean=0.0, aNs=1.3, aNe=1.0, tool_rot=0.75, crouch=0.0, aFs=-0.45, aFe=0.5)  # admires catch
    add(T['hand'] + 0.7, head=0.55, lean=-0.1)                         # looks up at the hand
    add(T['dark'], head=0.6, lean=-0.1)
    add(T['dark'] + 0.8, head=0.1, lean=0.05, aNs=1.0, aNe=0.9, tool_rot=1.6)      # (in the dark) net lowered
    add(T['release'] - 0.6, head=0.1, lean=0.05, aNs=1.0, aNe=0.9, tool_rot=1.6)
    RL = T['release']
    add(RL + 0.6, head=0.35, lean=-0.05, aNs=1.55, aNe=0.55, tool_rot=0.85)            # lifts the net toward the light
    add(RL + 0.8, tool_rot=0.93)
    add(RL + 1.0, tool_rot=0.80)                                                         # a gentle shake: go on
    add(RL + 1.25, tool_rot=0.87, head=0.45)
    add(RL + 2.6, head=0.6, lean=-0.08)                                                 # watches it climb into the light
    add(RL + 4.3, head=0.72, lean=-0.1, aNs=1.55, aNe=0.55, tool_rot=0.87)             # holds it up, an offering
    add(RL + 5.4, head=0.74, lean=-0.1, aNs=0.6, aNe=1.25, tool_rot=0.25)              # stands the net upright
    add(T['look'], head=0.76, lean=-0.1, aNs=0.6, aNe=1.25, tool_rot=0.25)
    add(T['look'] + 2.0, head=0.8, lean=-0.12, aNs=0.6, aNe=1.25, tool_rot=0.25)       # still looking up
    ST = T['sting']
    add(ST - 0.5, head=0.0, lean=0.05, aNs=0.6, aNe=1.25, aFs=-0.45, aFe=0.5, tool_rot=0.3, crouch=0.0, jump=0.0, tiptoe=0.0)
    add(ST + 1.9, head=0.05, lean=0.05)
    add(ST + 2.7, head=0.6, lean=-0.12)                                  # looks up: it's back in the moon
    return k


_PK = None
NAMES = ['lean', 'head', 'aNs', 'aNe', 'aFs', 'aFe', 'tool_rot', 'crouch', 'jump', 'tiptoe']


def pose(t):
    global _PK
    if _PK is None:
        keys = pose_keys()
        cur = dict(zip(NAMES, REST))
        tracks = {n: [] for n in NAMES}
        for tt, kw in keys:
            cur.update(kw)
            for n in NAMES:
                tracks[n].append((tt, cur[n]))
        _PK = tracks
    out = {n: float(kf(t, _PK[n])) for n in NAMES}
    # leather-puppet looseness: limbs lag and swing a little, head nods with the boat
    dt = 0.12
    prev = {n: float(kf(t - dt, _PK[n])) for n in ('lean', 'aNs', 'aFs')}
    vel_lean = (out['lean'] - prev['lean']) / dt
    out['aFs'] += -0.25 * vel_lean + 0.06 * np.sin(1.25 * t + 0.8)
    out['aFe'] += 0.05 * np.sin(1.25 * t + 1.6) + 0.15 * abs(vel_lean)
    out['aNe'] += -0.04 * (out['aNs'] - prev['aNs']) / dt
    out['head'] += 0.035 * np.sin(1.25 * t + 0.3) + 0.02 * nz(t * 1.7, 50)
    # rowing while the boat travels
    if t < T['notice'] + 0.4:
        r = rowing(t)
        w = 1.0 if t < T['boat_stop'] - 0.6 else max(0.0, 1 - (t - T['boat_stop'] + 0.6) / 1.4)
        out['aNs'] = 0.9 + 0.45 * r * w
        out['aNe'] = 0.7 - 0.3 * r * w
        out['aFs'] = 0.6 + 0.4 * r * w
        out['aFe'] = 0.8 - 0.2 * r * w
        out['tool_rot'] = -0.45 - 0.35 * r * w
        out['lean'] = 0.08 + 0.1 * r * w
    return out


# ------------------------------------------------------------------ splash particles
def splash(t, t0, at, n=22, seed=1, power=1.0):
    if t < t0 or t > t0 + 1.6:
        return []
    rng = np.random.default_rng(seed)
    d = t - t0
    out = []
    for i in range(n):
        vx = rng.uniform(-9, 9) * power
        vy = rng.uniform(8, 20) * power
        x = at[0] + vx * d
        y = at[1] + vy * d - 0.5 * 42 * d * d
        if y < at[1] - 2:
            continue
        r = rng.uniform(0.25, 0.6)
        out.append(Shape(ellipse(x, y, r, r * 1.4, 10, rot=np.arctan2(vy - 42 * d, vx) + np.pi / 2), z=0.5, dye=P.TEAL_D, edge=0.1, edge_t=0.2))
    return out


def drips(t, t0, src_fn, n=10, seed=3, dur=2.2):
    if t < t0 or t > t0 + dur:
        return []
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        st = t0 + rng.uniform(0, dur * 0.7)
        if t < st:
            continue
        d = t - st
        p = src_fn(st) + np.array([rng.uniform(-2.5, 2.5), -3.5])
        y = p[1] - 0.5 * 40 * d * d
        if y < -19:
            continue
        out.append(Shape(ellipse(p[0], y, 0.22, 0.4, 8), z=0.5, dye=P.TEAL_D))
    return out


# ------------------------------------------------------------------ camera
_HEAD = {}


def head_at(t):
    k = round(t, 3)
    if k not in _HEAD:
        _HEAD[k] = fisher_at(t)[2]['head']
    return _HEAD[k]


def cam_at(t):
    S1, SH, L, C = T['scoop1'], T['shadow1'], T['land'], T['catch']
    W_ = 1.12
    segs = [
        (0.0, T['boat_in'], lambda u: (0.0, 0.0, 0.9 + (W_ - 0.9) * ss(u))),
        (T['boat_in'], T['notice'], lambda u: (-2.0 + 4 * u, -2.0, W_)),
        (T['notice'], S1 + 1.0, lambda u: (2 + 14 * ss(u), -2 - 6 * ss(u), W_ + 0.26 * ss(u))),
        (S1 + 1.0, S1 + 2.8, lambda u: tuple(0.5 * (head_at(S1 + 1.8) + net_center(S1 + 1.8)) + [0.6 * u, 0]) + (2.4 + 0.08 * u,)),  # empty net
        (S1 + 2.8, T['reach'], lambda u: (16.0, -6.0, 1.38)),
        (T['reach'], SH, lambda u: (16 + 2 * ss(u * 1.5), -6 + 14 * ss(u * 1.5), 1.38 - 0.14 * ss(u * 1.5))),
        (SH, SH + 3.0, lambda u: (-6.0, 4.0, W_)),                                                     # the moth takes off
        (SH + 3.0, SH + 4.6, lambda u: tuple(head_at(SH + 3.6) + [0, 3.0]) + (2.6 + 0.1 * u,)),         # darkness passes over him
        (SH + 4.6, L, lambda u: (14 * ss(u), 4 + 4 * ss(u), W_ + 0.18 * ss(u))),
        (L, L + 1.8, lambda u: (24.0, 6.0, 1.3)),
        (L + 1.8, L + 3.2, lambda u: (MOON_C[0], MOON_C[1], 3.4 + 0.15 * u)),                    # moth close-up
        (L + 3.2, L + 4.4, lambda u: tuple(head_at(L + 3.8) + [2.0, 1.0]) + (2.3,)),                # fisherman sees it
        (L + 4.4, T['bumps'], lambda u: (22.0, 6.0, 1.28)),
        (T['bumps'], T['bumps_end'], lambda u: (0.0, 2.0, W_)),
        (T['bumps_end'], C + 0.9, lambda u: (14.0, -2.0, 1.22)),
        (C + 0.9, C + 2.6, lambda u: tuple(0.6 * net_center(C + 1.7) + 0.4 * head_at(C + 1.7)) + (2.5 + 0.1 * u,)),  # the catch
        (C + 2.6, T['hand'], lambda u: (14.0, 0.0, 1.18)),
        (T['hand'], T['dark'], lambda u: tuple(net_center(T['hand'] + 1.0) * 0.6 + np.array([14.0, 0.0]) * 0.4 + [0, 6]) + (1.35,)),
        (T['dark'], DUR, lambda u: moon_cam(T['dark'] + u * (DUR - T['dark']))),
    ]
    for a, b, f in segs:
        if a <= t < b:
            x, y, z = f((t - a) / (b - a))
            break
    else:
        x, y, z = 0, 0, 1
    # breathing hand-held drift
    x += 0.25 * nz(t * 0.4, 21)
    y += 0.2 * nz(t * 0.35, 22)
    # keep the frame inside the paper screen (consistent crop) once the opening shot is over
    if t >= T['boat_in']:
        mx = max(0.0, 88.0 - 96.0 / z)
        my = max(0.0, 49.5 - 54.0 / z)
        x = float(np.clip(x, -mx, mx))
        y = float(np.clip(y, -my, my))
    return Cam(x, y, z)


# ------------------------------------------------------------------ the scene
def fisher_at(t):
    bx, by, br = boat_state(t)
    b, BM = P.boat(bx, by, br, z=0.6)
    po = pose(t)
    base = BM @ mat(1.2, 5.7)
    root = apply(base, [[0, 0]])[0]
    root = root + np.array([0, po['jump'] + po['tiptoe'] * 0.5])
    tool = 'oar' if t < T['notice'] + 0.4 else 'net'
    legs = None
    if po['jump'] > 0.5:
        legs = [(0.5 * np.sin(t * 9), 0), (-0.4 - 0.5 * np.sin(t * 9 + 1), 0)]
    f, info = P.fisherman(root[0], root[1], rot=br, lean=po['lean'], head=po['head'],
                          armN=(po['aNs'], po['aNe']), armF=(po['aFs'], po['aFe']), tool=tool,
                          tool_rot=po['tool_rot'] + (br if tool == 'net' else 0), tool_len=24.0,
                          crouch=po['crouch'], legs=legs)
    return b, f, info, tool, po


_NETC = {}


def net_center(t):
    k = round(t, 3)
    if k not in _NETC:
        info = fisher_at(t)[2]
        _NETC[k] = apply(info['netM'], [[0.0, -2.0]])[0]
    return _NETC[k]


def scene(t):
    shapes = []
    lamp = lamp_at(t)
    # title plaque: on the bare screen, then pulled back toward the lamp
    if t < T['title_pull'] + 2.2:
        u = (t - T['title_pull']) / 2.0
        z = 0.5 + 125 * ss(u) ** 1.6 if t > T['title_pull'] else 0.5
        S = (0.0, 4.0 + 3 * ss(u))
        wpos = scr2world(S, z)
        shapes += P.title_plaque(wpos[0], wpos[1], z, scale=1.0, rot=0.06 * ss(u))
        shapes.append(P.rod((wpos[0] - 6, wpos[1] - 12), z=z + 1.5))
    # set pieces slide in
    si = T['set_in']
    sky_dy = 75 * (1 - ss((t - si) / 1.4))
    mtn_dy = -50 * (1 - ss((t - si - 0.5) / 1.3))
    wat_dy = -50 * (1 - ss((t - si - 1.0) / 1.3))
    reed_dx = 40 * (1 - ss((t - si - 1.6) / 1.2))
    statics = []
    cam = cam_at(t)
    if t >= si:
        if cam.zoom <= 1.45:
            statics.append((engine.static_layer('sky', lambda: P.sky(moon_c=MOON_C)), sky_dy))
            statics.append((engine.static_layer('mtn', lambda: P.mountains()), mtn_dy))
        else:
            for sh in P.sky(moon_c=MOON_C):
                sh.poly = sh.poly + [0, sky_dy]
                sh.holes = [h + [0, sky_dy] for h in sh.holes]
                shapes.append(sh)
            for sh in P.mountains():
                sh.poly = sh.poly + [0, mtn_dy]
                shapes.append(sh)
        for sh in P.water(t):
            sh.poly = sh.poly + [0, wat_dy]
            sh.holes = [h + [0, wat_dy] for h in sh.holes]
            shapes.append(sh)
        # moon reflection (shatters on each scoop)
        sh_amt = 0.0
        for t0, amp in ((T['scoop1'], 1.2),):
            if t >= t0:
                d = t - t0
                sh_amt = max(sh_amt, amp * np.exp(-d * 1.1) * min(1, d * 8))
        refl_alive = True
        if refl_alive:
            for sh in P.reflection(t, center=REFL_C + [0, wat_dy], shatter=min(sh_amt, 1.3), seed=int(t // 0.25) % 3 if sh_amt > 0.4 else 0):
                shapes.append(sh)
        for sh in P.reeds(-94 - reed_dx, t) + P.reeds(78 + reed_dx, t, seed=4, n=5):
            shapes.append(sh)
    # boat + fisherman
    if t >= T['boat_in'] - 0.1:
        b, f, info, tool, po = fisher_at(t)
        hull, canopy = b
        hull.paint = True
        canopy.paint = True
        shapes += [canopy] + f + [hull]          # stacked cut-outs: canopy behind him, hull in front of his robe
        # splashes & drips
        if tool == 'net':
            shapes += splash(t, T['scoop1'] - 0.05, REFL_C + [-4, 1], seed=1)
            shapes += drips(t, T['scoop1'] + 1.0, net_center, seed=3)
        # moth in the net
        ms = moth_state(t)
        if ms == 'net' and t < T['release'] + 1.2 and t < T['sting']:
            NM = info['netM']
            c = apply(NM, [[0.0, -2.0]])[0]
            wig = 0.6 * nz(t * 9, 30)
            fade_flap = (1.8 if T['hand'] + 0.6 < t < T['dark'] - 1.6 else 1.0) if t < T['dark'] else 0.5
            shapes += P.moth(c[0] + wig, c[1] + 0.5 * nz(t * 11, 31), 0.6, flap=t * 2 * np.pi * 5 * fade_flap,
                             rot=0.4 * nz(t * 4, 32), scale=0.5)
    ms = moth_state(t)
    if ms is not None and ms != 'net':
        sx, sy, z, flap, rot, sc = ms
        if t < T['release'] or t >= T['sting']:
            wp = scr2world((sx, sy), z)
            shapes += P.moth(wp[0], wp[1], z, flap=flap, rot=rot, scale=sc, legs_out=1.0 if z < 1 else 0.0)
    # puppeteer's hand: reaches toward the netted moth, then goes back to the lamp and pinches the flame
    if T['hand'] <= t < T['dark'] - 1.6:
        u = t - T['hand']
        nc = net_center(T['hand'] + 1.0)
        H, D = T['hand'], T['dark']
        S = kf(t, [(H, (nc[0] + 4, 100)), (H + 1.0, (nc[0] - 1, nc[1] + 15)), (H + 1.45, (nc[0], nc[1] + 17)), (H + 1.6, (nc[0] + 1, nc[1] + 21)),
                   (D - 1.6, (nc[0] + 10, nc[1] + 60))])
        z = float(kf(t, [(H, 40.0), (H + 1.6, 41.0), (D - 1.6, 90.0)], ease=lambda x: lin(x) ** 1.4))
        wp = scr2world(S, z)
        shapes += P.hand(wp[0], wp[1], z, rot=0.25 + 0.05 * nz(t, 33), scale=1.0, curl=0.2 + 0.15 * np.sin(u * 1.5) + 0.5 * ss((t - D + 0.5) / 0.5))
    moon = None
    moon_shapes = None
    if T['window'] <= t < T['sting']:
        moon, moon_shapes = moonlight(t, shapes)
    return shapes, cam, lamp, moon, moon_shapes, statics



MOON_DIR = np.array([-0.33, -0.10])
WIN_Z = 320.0
WIN_C = np.array([16.0, -3.0])
WIN_R = 50.0


def moonlight(t, shapes):
    u = t - T['window']
    shutter = ss(u / 2.6)
    power = 1.05 * min(1.0, 0.35 + ss(u / 1.5))
    moon = Moon(dx=MOON_DIR[0], dy=MOON_DIR[1], ang=0.0016, power=power, color=(0.50, 0.66, 1.0))
    # window positioned so its light lands centred on the screen
    wc = WIN_C - MOON_DIR * WIN_Z
    ms = list(shapes)
    ms += P.moon_window(wc[0], wc[1], WIN_Z, R=WIN_R, shutter=shutter)
    # moth escaping through the moonlight: parallel light keeps its shadow crisp and constant
    if t >= T['release'] + 1.2:
        sx, sy, z = moon_moth(t)
        wx, wy = sx - MOON_DIR[0] * z, sy - MOON_DIR[1] * z      # world pos so its moonlight shadow lands at (sx, sy)
        ms += P.moth(wx, wy, z, flap=t * 2 * np.pi * 6.0, rot=0.6 + 0.2 * nz(t * 2, 43), scale=0.62)
    return moon, ms


def cutaway(t):
    """State for the backstage flame close-up, or None when we are on the screen."""
    import flame as F
    S, FX, FY = F.S, F.FX, F.FY
    SH, B, D, ST = T['shadow1'], T['bumps'], T['dark'], T['sting']
    cuts = [(0.0, T['open_cut'], 'open'), (SH + 1.1, SH + 2.5, 'moth'), (B, T['bumps_end'], 'bump'),
            (D - 1.6, D + 0.25, 'pinch'), (ST, ST + 1.5, 'relight')]
    for a, b, kind in cuts:
        if a <= t < b:
            u = t - a
            break
    else:
        return None
    rel = lambda dx, dy: (FX + dx * S, FY + dy * S)
    st = dict(power=1.0, flare=0.0)
    flick = 0.0
    if kind in ('open', 'relight'):
        t_strike = 0.6 if kind == 'open' else 0.1
        head = 0.0 if u < t_strike else (1.0 * np.exp(-(u - t_strike) * 2.5) + 0.45)
        mx, my = kf(u, [(0.0, rel(330, 70)), (t_strike - 0.05, rel(16, -12)), (t_strike + 0.5, rel(16, -12)), (t_strike + 1.3, rel(420, 120))])
        st['match'] = (mx, my, head) if u < t_strike + 1.3 else None
        st['power'] = float(ss((u - t_strike - 0.25) / 0.9))
        st['flare'] = 0.6 * np.exp(-max(u - t_strike - 0.3, 0) * 4) if u > t_strike + 0.3 else 0.0
        st['screen_glow'] = st['power']
        st['exposure'] = 1.0 if kind == 'relight' else float(ss(u / 0.25))
        if kind == 'relight' and u > 0.55:
            p = spline(u, [(0.55, (-620, -420)), (0.95, (-220, -260)), (1.25, (60, -230)), (1.5, (210, -300))])
            st['moth'] = rel(*p) + (np.arccos(0.6 + 0.4 * np.cos(u * 2 * np.pi * 9)), -0.4, 16.0 * S)
    elif kind == 'moth':
        p = spline(u, [(0.0, (-640, -460)), (0.45, (-250, -300)), (0.85, (70, -215)), (1.15, (210, -260)), (1.4, (120, -380))])
        st['moth'] = rel(*p) + (np.arccos(0.6 + 0.4 * np.cos(u * 2 * np.pi * 9)), 0.4 * np.sin(u * 3), 16.0 * S)
        flick = 0.3
    elif kind == 'bump':
        p = spline(u, [(0.0, (-260, -330)), (0.4, (12, -150)), (0.8, (150, -270)), (1.2, (-14, -140)), (1.8, (-230, -320))])
        st['moth'] = rel(*p) + (np.arccos(0.6 + 0.4 * np.cos(u * 2 * np.pi * 10)), 0.5 * np.sin(u * 4), 16.0 * S)
        fl = 0.0
        for tb in (0.4, 1.2):
            if u >= tb:
                fl = max(fl, np.exp(-(u - tb) * 5))
        st['flare'] = fl
        st['sparks'] = [rel(10 + 160 * (u - 0.4) * np.cos(k * 1.7), -170 - 200 * (u - 0.4) + 60 * np.sin(k)) + (max(0, 1 - (u - 0.4) * 2.5),)
                        for k in range(5)] if 0.4 <= u < 0.8 else None
        if u >= 1.2:
            st['smoke'] = (0.35 * np.exp(-(u - 1.2) * 1.5), (u - 1.2) * 0.8)
        flick = 0.5
    elif kind == 'pinch':
        hp = kf(u, [(0.0, rel(700, -760)), (1.0, rel(4, -70))], ease=lambda x: 1 - (1 - lin(x)) ** 2.5)
        pinch = float(ss((u - 1.0) / 0.3))
        blur = float(kf(u, [(0.0, 9.0), (1.0, 2.5)]))
        st['hand'] = (hp[0], hp[1], pinch, blur)
        st['power'] = float(1 - ss((u - 1.05) / 0.3))
        st['screen_glow'] = st['power']
        if u >= 1.3:
            st['smoke'] = (min(1.0, (u - 1.3) * 3), (u - 1.3) * 0.9)
        st['exposure'] = float(1 - ss((u - 1.55) / 0.3))
    st['power'] *= 1 + flick * 0.15 * np.sin(t * 41) + 0.04 * np.sin(t * 13)
    return st


def moon_cam(t):
    """Continuous camera through the moonlight act (no cuts): wide on the waxing window, push in for the release,
    rise with the moth, settle on the old man looking up."""
    if t >= T['sting']:
        return (24.0, 6.0, 1.3)
    R = T['release']
    nc = net_center(R + 1.2)
    keys = [(T['dark'], (WIN_C[0], WIN_C[1] + 2, 1.0)), (T['window'] + 3.2, (WIN_C[0], WIN_C[1] + 2, 1.02)),
            (R - 0.5, (0.5 * nc[0] + 0.5 * WIN_C[0], nc[1] + 2, 1.45)), (R + 1.6, (0.6 * nc[0] + 0.4 * WIN_C[0], nc[1] + 6, 1.55)),
            (R + 3.6, (MOON_HOVER[0] + 4, MOON_HOVER[1] - 8, 1.6)), (R + 5.6, (MOON_HOVER[0] - 6, MOON_HOVER[1] - 6, 1.4)),
            (T['look'], (WIN_C[0] + 2, WIN_C[1] + 3, 1.12)), (T['fade'] + 1.4, (WIN_C[0] + 5, WIN_C[1] + 1, 1.32))]
    return tuple(spline(t, keys))


MOON_HOVER = np.array([8.0, 22.0])


def moon_moth(t):
    v = t - T['release'] - 1.2
    nc = net_center(T['release'] + 1.2)
    hx, hy = MOON_HOVER
    keys = [(0.0, (nc[0], nc[1], 0.6)), (1.0, (nc[0] - 5, nc[1] + 8, 2)), (2.2, (hx + 6, hy - 3, 4)), (2.8, (hx, hy, 5)),
            (3.8, (hx - 1, hy + 1, 5.5)), (5.0, (hx - 18, hy + 12, 12)), (6.4, (-40, 42, 30)), (8.4, (-80, 70, 60))]
    sx, sy, z = spline(v, keys)
    return sx + 2.5 * nz(t * 3, 41), sy + 2.0 * nz(t * 3.3, 42), z


def moon_moth_xy(t):
    return np.array(moon_moth(max(t, T['release'] + 1.2))[:2])


def exposure(t):
    if t >= T['sting']:
        return 1.0 if t < T['sting_end'] else 0.0
    return 1.0 - ss((t - T['fade']) / 1.4)


def card_alpha(t):
    return ss((t - T['card']) / 0.8) * (1 - ss((t - (T['end'] - 1.2)) / 1.0))


def branches(t, c, z):
    out = []
    rng = np.random.default_rng(12)
    sway = 0.03 * np.sin(t * 0.7) + 0.015 * np.sin(t * 1.9)
    base = np.array(c)
    for k in range(5):
        a = -2.4 + k * 0.28 + sway
        L = rng.uniform(25, 45)
        p0 = base
        p1 = base + L * np.array([np.cos(a), np.sin(a)])
        out.append(Shape(np.array([p0, (p0 + p1) / 2 + rng.uniform(-3, 3, 2), p1]), z=z, dye=(0.0, 0.0, 0.0), line=True, width=2.4 - 0.3 * k))
        for j in range(5):
            q = p0 + (p1 - p0) * (0.3 + 0.14 * j)
            lf = ellipse(q[0] + rng.uniform(-3, 3), q[1] + rng.uniform(-3, 3), 4.5, 1.8, 10, rot=rng.uniform(0, np.pi) + sway * 3)
            out.append(Shape(lf, z=z, dye=(0.0, 0.0, 0.0)))
    return out
