"""Hand-made line drawings, coordinates in [-1, 1] (y up)."""
import numpy as np
from sig import Path, strokes_path


def circle_pts(cx, cy, r, n=64, a0=0.0, a1=2 * np.pi):
    a = np.linspace(a0, a1, n)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)


def heart(M=2048):
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return Path(np.stack([x, y + 2], 1) / 17.0, M=M, lowpass=40)


def circle(M=2048):
    return Path(circle_pts(0, 0, 1, 256, 0, 2 * np.pi)[:-1], M=M)


def stick(cx, s=1.0, hand_l=None, hand_r=None, head_r=0.13):
    """A stick person centred at x=cx. Returns strokes."""
    hy = 0.38 * s
    head = circle_pts(cx, hy, head_r * s, 40)
    neck = 0.38 * s - head_r * s
    body = [(cx, neck), (cx, -0.15 * s)]
    legs = [(cx - 0.16 * s, -0.55 * s), (cx, -0.15 * s), (cx + 0.16 * s, -0.55 * s)]
    hl = hand_l if hand_l is not None else (cx - 0.24 * s, -0.05 * s)
    hr = hand_r if hand_r is not None else (cx + 0.24 * s, -0.05 * s)
    arms = [hl, (cx, 0.12 * s), hr]
    return [head, body, legs, arms]


def couple(M=3072, gap=0.33):
    a = stick(-gap, hand_r=(0, -0.02))
    b = stick(gap, hand_l=(0, -0.02))
    return strokes_path(a + b, M=M, lowpass=60)


def family(M=3072):
    a = stick(-0.42, hand_r=(-0.17, -0.08))
    b = stick(0.42, hand_l=(0.17, -0.08))
    c = stick(0.0, s=0.55, hand_l=(-0.17, -0.08), hand_r=(0.17, -0.08), head_r=0.16)
    c = [np.asarray(st) + [0, -0.25] for st in c]
    # child's arms reach the parents' hands: rebuild arms
    return strokes_path(a + b + c, M=M, lowpass=60)


def house(M=3072):
    body = [(-0.5, -0.6), (0.5, -0.6), (0.5, 0.1), (-0.5, 0.1), (-0.5, -0.6)]
    roof = [(-0.62, 0.05), (0.0, 0.6), (0.62, 0.05)]
    door = [(-0.1, -0.6), (-0.1, -0.22), (0.1, -0.22), (0.1, -0.6)]
    win = [(0.22, -0.12), (0.4, -0.12), (0.4, -0.3), (0.22, -0.3), (0.22, -0.12)]
    win2 = [(-0.22, -0.12), (-0.4, -0.12), (-0.4, -0.3), (-0.22, -0.3), (-0.22, -0.12)]
    chim = [(0.28, 0.32), (0.28, 0.55), (0.4, 0.55), (0.4, 0.2)]
    return strokes_path([body, roof, door, win, win2, chim], M=M, lowpass=70)


def tree(M=3072):
    trunk = [(-0.07, -0.65), (-0.05, -0.1), (-0.25, 0.05), (-0.05, -0.05), (0.0, 0.1),
             (0.05, -0.05), (0.27, 0.08), (0.05, -0.1), (0.07, -0.65)]
    # canopy: bumpy closed curve
    a = np.linspace(0, 2 * np.pi, 300)
    r = 0.42 + 0.05 * np.sin(7 * a)
    can = np.stack([r * np.cos(a), 0.3 + 0.8 * r * np.sin(a)], 1)
    ground = [(-0.8, -0.65), (0.8, -0.65)]
    return strokes_path([ground, trunk, can], M=M, lowpass=70)


def sun(M=2048, cx=0.0, cy=0.0, r=0.2):
    pts = []
    n = 12
    for k in range(n):
        a = 2 * np.pi * k / n
        for b in np.linspace(a, a + 2 * np.pi / n, 12, endpoint=False):
            pts.append((cx + r * np.cos(b), cy + r * np.sin(b)))
        pts.append((cx + 1.6 * r * np.cos(a + np.pi / n), cy + 1.6 * r * np.sin(a + np.pi / n)))
    return Path(np.array(pts), M=M, lowpass=50)


def moon(M=2048):
    outer = circle_pts(0, 0, 0.5, 120, -0.6 * np.pi, 0.6 * np.pi)
    inner = circle_pts(0.22, 0, 0.42, 120, 0.62 * np.pi, -0.62 * np.pi)[::-1]
    inner = inner[::-1]
    return Path(np.vstack([outer, inner]) - [0.1, 0], M=M, lowpass=40)


def hills_house(M=4096):
    """Small house on a hill with a tree: the 'home' picture."""
    s = 0.55
    body = np.array([(-0.5, -0.6), (0.5, -0.6), (0.5, 0.1), (-0.5, 0.1), (-0.5, -0.6)]) * s + [-0.25, 0.05]
    roof = np.array([(-0.62, 0.05), (0.0, 0.6), (0.62, 0.05)]) * s + [-0.25, 0.05]
    door = np.array([(-0.1, -0.6), (-0.1, -0.22), (0.1, -0.22), (0.1, -0.6)]) * s + [-0.25, 0.05]
    win = np.array([(0.2, -0.12), (0.38, -0.12), (0.38, -0.3), (0.2, -0.3), (0.2, -0.12)]) * s + [-0.25, 0.05]
    x = np.linspace(-0.95, 0.95, 80)
    hill = np.stack([x, -0.28 - 0.12 * np.cos(x * 1.6)], 1)
    a = np.linspace(0, 2 * np.pi, 160)
    can = np.stack([0.55 + 0.17 * np.cos(a) * (1 + 0.06 * np.sin(6 * a)), 0.12 + 0.2 * np.sin(a)], 1)
    trunk = [(0.53, -0.37), (0.54, -0.08), (0.57, -0.08), (0.58, -0.37)]
    return strokes_path([hill, body, roof, door, win, trunk, can], M=M, lowpass=90)


# ---------------------------------------------------------------- animated figures

def walker(cx, walk_ph, s=1.0, cy=0.0, hand_l=None, hand_r=None, head_r=0.13, swing=0.42, stance=0.32, start=None):
    """Stick person at x=cx as ONE continuous loop (the beam never has to jump inside a body).
    walk_ph in cycles drives the stride; stance = leg spread when standing."""
    a = swing * np.sin(2 * np.pi * walk_ph)
    sp = stance * (1 - min(1, swing / 0.42)) + 0.0
    bob = 0.015 * s * abs(np.cos(2 * np.pi * walk_ph)) * (swing > 0)
    hip = np.array([cx, cy - 0.15 * s + bob])
    sh = np.array([cx, cy + 0.12 * s + bob])
    hc = np.array([cx, cy + 0.38 * s + bob])
    neck = hc + [0, -head_r * s]
    ang = np.linspace(-np.pi / 2, 3 * np.pi / 2, 48)
    head = np.stack([hc[0] + head_r * s * np.cos(ang), hc[1] + head_r * s * np.sin(ang)], 1)
    L = 0.42 * s
    l1 = a + sp; l2 = -a - sp
    leg1 = hip + L * np.array([np.sin(l1), -np.cos(l1)])
    leg2 = hip + L * np.array([np.sin(l2), -np.cos(l2)])
    al = 0.27 * s
    hl = np.array(hand_l) if hand_l is not None else sh + al * np.array([np.sin(-a * 0.8 - 0.5), -np.cos(-a * 0.8 - 0.5)])
    hr = np.array(hand_r) if hand_r is not None else sh + al * np.array([np.sin(a * 0.8 + 0.5), -np.cos(a * 0.8 + 0.5)])
    tour = np.vstack([head, [sh, hl, sh, hr, sh, hip, leg1, hip, leg2, hip, sh, neck]])
    if start in ('hl', 'hr', 'fr', 'fl'):
        i = len(head) + {'hl': 1, 'hr': 3, 'fr': 6, 'fl': 8}[start]
        tour = np.vstack([tour[i:-1], tour[:i + 1]])
    return [tour]


def heart_strokes(cx, cy, r):
    t = np.linspace(0, 2 * np.pi, 120)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return np.stack([cx + r * x / 17, cy + r * (y + 2) / 17], 1)


def smoke(x0, y0, t, n=40):
    u = np.linspace(0, 1, n)
    x = x0 + 0.05 * u * np.sin(2 * np.pi * (u * 1.5 - t * 0.6)) + 0.12 * u
    y = y0 + 0.32 * u
    return np.stack([x, y], 1)


def home_path(t, M=3072, lowpass=100):
    """The house on a hill as ONE hand-routed loop: the beam walks along the drawing's own lines
    (hill, walls, roof, chimney, smoke, door), so there are no visible jumps. Only the window needs two
    tiny hops from the wall."""
    from sig import Path
    s = 0.55
    hx = -0.25
    hill_y = lambda xx: -0.36 - 0.05 * np.cos(xx * 1.6)
    base = hill_y(hx) + 0.006
    off = np.array([hx, base + 0.6 * s])
    P = lambda x, y: np.array([x, y]) * s + off
    BL, BR, TR, TL = P(-0.5, -0.6), P(0.5, -0.6), P(0.5, 0.1), P(-0.5, 0.1)
    eL, apex, eR = P(-0.62, 0.05), P(0.0, 0.6), P(0.62, 0.05)
    roofy = lambda x: 0.6 - 0.55 * x / 0.62
    c0, c1, c2, c3 = P(0.28, roofy(0.28)), P(0.28, 0.52), P(0.4, 0.52), P(0.4, roofy(0.4))
    sm = smoke(c1[0] + 0.03, c1[1] + 0.02, t)
    pts = []; jumps = []

    def go(seq, jump_first=False):
        seq = np.atleast_2d(np.asarray(seq, float))
        for k, q in enumerate(seq):
            pts.append(q); jumps.append(jump_first and k == 0)

    def line(a, b, n=12):
        return np.linspace(a, b, n)[1:]

    # hill, left part: from the house corner out to the left end and back
    xl = np.linspace(BL[0], -0.95, 30)
    go([BL]); go(np.stack([xl, hill_y(xl)], 1)[1:]); go(np.stack([xl[::-1], hill_y(xl[::-1])], 1)[1:])
    # left wall up, roof to the chimney, chimney up, smoke out and back, chimney down, roof to the right eave
    go(line(BL, TL)); go(line(TL, eL, 4)); go(line(eL, apex)); go(line(apex, c0, 8))
    go(line(c0, c1, 6)); go(np.vstack([sm, sm[::-1]])); go(line(c1, c2, 4)); go(line(c2, c3, 6))
    go(line(c3, eR, 6)); go(line(eR, TR, 4))
    # right wall down, hopping into the window and back on the way
    w_y = P(0, -0.12)[1]
    go(line(TR, np.array([TR[0], w_y]), 6))
    win = [P(0.38, -0.12), P(0.38, -0.3), P(0.2, -0.3), P(0.2, -0.12), P(0.38, -0.12)]
    go(win[0], jump_first=True)
    for a_, b_ in zip(win[:-1], win[1:]):
        go(line(a_, b_, 6))
    go(np.array([TR[0], w_y]), jump_first=True)
    go(line(np.array([TR[0], w_y]), BR, 8))
    # base line leftwards through the door
    d0, d1, d2, d3 = P(0.1, -0.6), P(0.1, -0.22), P(-0.1, -0.22), P(-0.1, -0.6)
    go(line(BR, d0, 6)); go(line(d0, d1, 6)); go(line(d1, d2, 4)); go(line(d2, d3, 6)); go(line(d3, BL, 6))
    # hill, right part, with the tree on it, and back to the corner
    tx = 0.55; ty = hill_y(tx); cy = ty + 0.48
    xr = np.linspace(BL[0], tx, 30)
    go(np.stack([xr, hill_y(xr)], 1)[1:])
    aa = np.linspace(-np.pi / 2, 3 * np.pi / 2, 120)
    can = np.stack([tx + 0.17 * np.cos(aa) * (1 + 0.06 * np.sin(6 * aa)), cy + 0.2 * np.sin(aa)], 1)
    go(line(np.array([tx, ty]), can[0], 8)); go(can[1:]); go(line(can[-1], np.array([tx, ty]), 8))
    xe = np.linspace(tx, 0.95, 16)
    go(np.stack([xe, hill_y(xe)], 1)[1:]); go(np.stack([xe[::-1], hill_y(xe[::-1])], 1)[1:])
    xb = np.linspace(tx, BL[0], 30)
    go(np.stack([xb, hill_y(xb)], 1)[1:-1])
    return Path(np.array(pts), M=M, jumps=np.array(jumps), lowpass=lowpass, jump_w=0.0004)
