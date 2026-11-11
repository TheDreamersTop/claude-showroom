"""Puppet and scenery definitions (Chinese leather shadow-puppet style)."""
import numpy as np, cv2
from engine import Shape, catmull, circle, ellipse, mat, apply

# ---------------------------------------------------------------- palette (transmittance)
GREEN = (0.32, 0.66, 0.40)
GREEN_D = (0.24, 0.52, 0.30)
RED = (0.92, 0.28, 0.14)
YELLOW = (0.95, 0.78, 0.32)
STRAW = (0.88, 0.66, 0.28)
FACE = (0.97, 0.92, 0.80)
DARK = (0.06, 0.05, 0.05)
AMBER = (0.80, 0.46, 0.18)
INDIGO = (0.16, 0.26, 0.72)
TEAL = (0.22, 0.55, 0.62)
TEAL_D = (0.14, 0.40, 0.52)
REED = (0.14, 0.22, 0.10)
MOTH = (0.07, 0.055, 0.045)
EDGE_T = 0.07

_PAT_CACHE = {}


def _inside(poly, pts, margin):
    c = np.float32(poly).reshape(-1, 1, 2)
    return np.array([cv2.pointPolygonTest(c, (float(x), float(y)), True) > margin for x, y in pts], bool)


def pattern(poly, kind, sp=1.0, r=0.25, margin=0.5, seed=0, angle=0.0, key=None):
    """Cut-out hole polygons inside poly (local coords). Cached by key."""
    if key is not None and key in _PAT_CACHE:
        return _PAT_CACHE[key]
    poly = np.asarray(poly)
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    holes = []
    if kind in ('dots', 'diamonds', 'mesh', 'cross'):
        xs = np.arange(x0, x1 + sp, sp)
        ys = np.arange(y0, y1 + sp, sp * (0.87 if kind != 'mesh' else 1.0))
        cand = []
        for j, y in enumerate(ys):
            off = sp / 2 if (j % 2 and kind != 'mesh') else 0
            for x in xs:
                cand.append((x + off, y))
        cand = np.array(cand)
        ok = _inside(poly, cand, margin + r)
        for (x, y) in cand[ok]:
            if kind == 'dots':
                holes.append(circle(x, y, r, 10))
            elif kind == 'diamonds':
                holes.append(np.array([[x, y - r * 1.3], [x + r, y], [x, y + r * 1.3], [x - r, y]]))
            elif kind == 'mesh':
                holes.append(np.array([[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r]]))
            elif kind == 'cross':
                a, b = r, r * 0.35
                holes.append(np.array([[x - b, y - a], [x + b, y - a], [x + b, y - b], [x + a, y - b], [x + a, y + b], [x + b, y + b],
                                       [x + b, y + a], [x - b, y + a], [x - b, y + b], [x - a, y + b], [x - a, y - b], [x - b, y - b]]))
    elif kind == 'slits':      # parallel thin slits along direction angle
        ca, sa = np.cos(angle), np.sin(angle)
        L = max(x1 - x0, y1 - y0) * 1.5
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for k in np.arange(-L, L, sp):
            # walk along the line, emit short slits where inside
            ts = np.arange(-L, L, r * 6)
            for t in ts:
                px = cx + ca * t - sa * k
                py = cy + sa * t + ca * k
                q = np.array([[px, py], [px + ca * r * 4, py + sa * r * 4]])
                if _inside(poly, q, margin).all():
                    w = r * 0.45
                    nx, ny = -sa * w, ca * w
                    holes.append(np.array([[q[0, 0] + nx, q[0, 1] + ny], [q[1, 0] + nx, q[1, 1] + ny],
                                           [q[1, 0] - nx, q[1, 1] - ny], [q[0, 0] - nx, q[0, 1] - ny]]))
    elif kind == 'crescents':   # wave curls
        rng = np.random.default_rng(seed)
        xs = np.arange(x0, x1 + sp, sp)
        ys = np.arange(y0, y1 + sp, sp * 0.7)
        for j, y in enumerate(ys):
            for x in xs:
                x_ = x + (sp / 2 if j % 2 else 0)
                a = np.linspace(0.2 * np.pi, 1.25 * np.pi, 9)
                outer = np.stack([x_ + r * np.cos(a), y + r * np.sin(a)], 1)
                inner = np.stack([x_ + r * 0.62 * np.cos(a[::-1]) + r * 0.15, y + r * 0.62 * np.sin(a[::-1]) + r * 0.05], 1)
                q = np.vstack([outer, inner])
                if _inside(poly, q, margin).all():
                    holes.append(q)
    if key is not None:
        _PAT_CACHE[key] = holes
    return holes


def leather(poly, M, z, dye, holes=(), edge=0.32, kind='fill'):
    return Shape(apply(M, poly), z=z, dye=dye, edge=edge, edge_t=EDGE_T, holes=[apply(M, h) for h in holes], kind=kind)


def rod(p, z=1.4, bottom=-75.0, lean=-0.18):
    p = np.asarray(p, float)
    q = np.array([p[0] + (bottom - p[1]) * lean, bottom])
    return Shape(np.array([p, q]), z=z, dye=(0.10, 0.08, 0.07), line=True, width=0.2)


# ================================================================= FISHERMAN
_F = {}


def _fisher_geo():
    if _F:
        return _F
    _F['torso'] = catmull([(-3.2, -0.5, 'c'), (-3.6, 4), (-3.4, 8.5), (-2.8, 11.4), (-1.2, 12.7), (1.0, 12.8), (2.6, 12.0),
                           (3.4, 9.5), (3.9, 6), (3.6, 2.0), (3.0, -0.5, 'c')])
    _F['torso_h'] = pattern(_F['torso'], 'diamonds', sp=1.15, r=0.3, margin=0.55)
    _F['belt'] = catmull([(-3.5, -0.2, 'c'), (3.3, -0.2, 'c'), (3.5, 1.5, 'c'), (-3.6, 1.5, 'c')])
    _F['belt_h'] = [circle(x, 0.65, 0.28, 10) for x in np.arange(-2.6, 3.0, 1.0)]
    _F['collar'] = catmull([(0.3, 12.8, 'c'), (2.0, 12.2), (2.9, 9.6, 'c'), (2.2, 9.4), (1.2, 11.6, 'c')])
    _F['skirt'] = catmull([(-3.4, 0.6, 'c'), (3.2, 0.6, 'c'), (4.2, -5), (5.2, -10.5, 'c'), (-4.8, -10.5, 'c'), (-4.0, -5)])
    _F['skirt_h'] = pattern(_F['skirt'], 'slits', sp=1.3, r=0.35, margin=0.6, angle=np.pi / 2 - 0.06)
    _F['leg'] = catmull([(-0.9, 0.5, 'c'), (0.9, 0.5, 'c'), (0.8, -5.6, 'c'), (2.2, -6.0), (2.4, -7.0, 'c'), (-1.0, -7.0, 'c'), (-0.8, -5.6, 'c')])
    face = [(-0.7, -0.2, 'c'), (-1.3, 1.6), (-1.0, 3.7, 'c'), (1.2, 4.0), (1.9, 3.4), (2.1, 3.0), (2.95, 2.3, 'c'),
            (2.2, 2.05, 'c'), (2.45, 1.75), (2.0, 1.45, 'c'), (2.25, 0.95), (1.2, 0.25), (0.9, -0.3, 'c')]
    _F['face'] = catmull(face, n=6)
    _F['eye'] = ellipse(1.35, 2.95, 0.42, 0.17, 16, rot=0.1)
    _F['brow'] = np.array([[0.75, 3.35], [1.85, 3.45]])
    _F['beard'] = catmull([(2.05, 1.35), (2.4, 0.6), (2.2, -1.4), (1.7, -3.6), (1.05, -4.6, 'c'), (0.7, -2.4), (0.1, -0.2), (0.6, 0.9)])
    _F['beard_h'] = pattern(_F['beard'], 'slits', sp=0.42, r=0.22, margin=0.12, angle=np.pi / 2 + 0.25)
    _F['hat'] = catmull([(-5.4, 3.5, 'c'), (6.6, 3.3, 'c'), (6.3, 3.85), (1.0, 6.9, 'c'), (-5.0, 4.1)])
    hh = []
    for a in np.linspace(-0.95, 0.85, 9):   # radial slits from the peak
        d = np.array([np.sin(a), -np.cos(a)])
        n = np.array([d[1], -d[0]]) * 0.13
        p0 = np.array([1.0, 6.9]) + d * 1.0
        p1 = np.array([1.0, 6.9]) + d * (2.6 + 0.2 * abs(a))
        hh.append(np.array([p0 + n, p1 + n, p1 - n, p0 - n]))
    _F['hat_h'] = hh
    _F['uarm'] = catmull([(-1.1, 0.7, 'c'), (1.1, 0.7, 'c'), (1.4, -5.2), (-1.0, -5.5)])
    _F['farm'] = catmull([(-1.0, 0.4, 'c'), (1.0, 0.4, 'c'), (1.7, -4.3, 'c'), (-1.4, -4.7, 'c')])
    _F['cuff'] = catmull([(1.75, -3.6, 'c'), (1.7, -4.3, 'c'), (-1.4, -4.7, 'c'), (-1.3, -4.0, 'c')])
    _F['hand'] = catmull([(-0.6, 0.3), (0.7, 0.4), (1.0, -0.4), (0.4, -1.2), (-0.6, -0.9)])
    _F['oar'] = catmull([(-0.25, 0, 'c'), (0.25, 0, 'c'), (0.25, -16, 'c'), (0.9, -17, 'c'), (0.7, -21.5), (0, -22.5), (-0.7, -21.5), (-0.9, -17, 'c'), (-0.25, -16, 'c')], n=4)
    # net: hoop + bag (local: origin at pole tip, opening facing +y when rot=0)
    bag = catmull([(-3.2, 0, 'c'), (3.2, 0, 'c'), (2.6, -2.6), (0.6, -4.6), (-1.2, -4.2), (-2.8, -2.2)])
    _F['net'] = bag
    _F['net_h'] = pattern(bag, 'mesh', sp=0.62, r=0.22, margin=0.15)
    _F['hoop'] = np.array([[-3.4, 0], [3.4, 0]])
    return _F


def fisherman(x, y, z=0.6, rot=0.0, lean=0.0, head=0.0, armN=(0.4, -0.6), armF=(-0.3, -0.5), legs=None,
              tool='net', tool_rot=0.0, tool_len=20.0, net_bulge=0.0, scale=1.0, rods=True, crouch=0.0, flip=False,
              catch=None):
    """Returns (shapes, info). armN/armF: (shoulder angle, elbow angle) radians, 0 = hanging straight down.
    tool: 'net' | 'oar' | None. tool_rot: angle of pole relative to vertical-up from the near hand (world)."""
    g = _fisher_geo()
    out = []
    sx = -scale if flip else scale
    root = mat(x, y, rot, sx, scale)
    hip = root @ mat(0, -crouch * 4.0, 0)
    torsoM = hip @ mat(0, 0, -lean)
    # lower body
    if legs is not None:
        for i, (a, k) in enumerate(legs):
            LM = hip @ mat(0.6 - 1.2 * i, -8.5, a)
            out.append(leather(g['leg'], LM, z + 0.02, (0.20, 0.20, 0.26) if i else (0.16, 0.16, 0.22)))
    out.append(leather(g['skirt'], hip, z, GREEN_D, g['skirt_h']))
    out.append(leather(g['torso'], torsoM, z, GREEN, g['torso_h']))
    out.append(leather(g['belt'], torsoM, z, RED, g['belt_h'], edge=0.22))
    out.append(leather(g['collar'], torsoM, z, YELLOW, edge=0.2))
    headM = torsoM @ mat(0.8, 12.5, head)
    out.append(Shape(apply(headM, g['face']), z=z, dye=FACE, edge=0.26, edge_t=EDGE_T))
    out.append(Shape(apply(headM, g['eye']), z=z, dye=DARK))
    out.append(Shape(apply(headM, g['brow']), z=z, dye=DARK, line=True, width=0.22))
    out.append(leather(g['beard'], headM, z, (0.93, 0.9, 0.84), g['beard_h'], edge=0.2))
    out.append(leather(g['hat'], headM, z, STRAW, g['hat_h'], edge=0.3))
    info = {}
    hands = []
    for i, (sh, el) in enumerate((armF, armN)):
        dye_s = (0.40, 0.72, 0.50) if i == 0 else GREEN     # far arm lighter so overlaps stay readable
        SM = torsoM @ mat(0.9 - 0.6 * i * 0, 11.2, sh)
        out.append(leather(g['uarm'], SM, z, dye_s))
        EM = SM @ mat(0.2, -5.1, el)
        out.append(leather(g['farm'], EM, z, dye_s))
        out.append(leather(g['cuff'], EM, z, YELLOW if i else (0.8, 0.62, 0.25), edge=0.18))
        HM = EM @ mat(0.15, -4.9, 0)
        out.append(Shape(apply(HM, g['hand']), z=z, dye=FACE, edge=0.2, edge_t=EDGE_T))
        hands.append(apply(HM, [[0.2, -0.4]])[0])
    info['handF'], info['handN'] = hands
    info['neck'] = apply(headM, [[0.0, 0.0]])[0]
    info['head'] = apply(headM, [[1.0, 2.5]])[0]
    hn = info['handN']
    # tool, world-oriented from near hand
    if tool == 'net':
        d = np.array([np.sin(tool_rot), np.cos(tool_rot)]) * (1 if not flip else 1)
        tip = hn + d * tool_len * scale
        butt = hn - d * 3.0 * scale
        out.append(Shape(np.array([butt, tip]), z=z, dye=(0.35, 0.22, 0.10), line=True, width=0.45 * scale))
        NM = mat(tip[0], tip[1], -tool_rot + np.pi, scale, scale * (1 + net_bulge))
        # the hoop sits on the pole tip, perpendicular to it; the bag hangs beyond (a hand net seen side-on)
        out.append(Shape(apply(NM, g['net']), z=z, dye=(0.42, 0.40, 0.36), edge=0.12, edge_t=0.2,
                         holes=[apply(NM, h) for h in g['net_h']]))
        out.append(Shape(apply(NM, g['hoop']), z=z, dye=(0.3, 0.2, 0.1), line=True, width=0.4 * scale))
        info['tip'] = tip
        info['netM'] = NM
    elif tool == 'oar':
        OM = mat(hn[0], hn[1], tool_rot, scale) @ mat(0, 4.0, 0)
        out.append(leather(g['oar'], OM, z, AMBER, edge=0.22))
    if rods:
        out.append(rod(info['neck'] + np.array([0, -1.0]), z=z + 2.5))
        out.append(rod(info['handN'], z=z + 3.0, lean=-0.05))
        out.append(rod(info['handF'], z=z + 3.2, lean=-0.32))
    return out, info


# ================================================================= BOAT
_B = {}


def _boat_geo():
    if _B:
        return _B
    hull = catmull([(-17.5, 3.0, 'c'), (-14.5, 0.6), (-8, -2.8), (0, -3.5), (9, -2.8), (15, 0), (19.0, 3.6, 'c'), (17.6, 3.3),
                    (13, 1.5), (0, 1.0), (-13, 1.6), (-16.2, 3.2, 'c')])
    _B['hull'] = hull
    holes = []
    for x in np.arange(-12, 13.5, 2.6):
        holes.append(ellipse(x, -1.0, 0.75, 0.42, 14))
    for x in np.arange(-10.7, 12.5, 2.6):
        holes.append(circle(x, 0.1, 0.18, 8))
        holes.append(circle(x, -2.0, 0.18, 8))
    _B['hull_h'] = holes
    can = catmull([(-14.0, 1.2, 'c'), (-14.3, 5.2), (-12, 8.0), (-7.5, 8.2), (-5.2, 5.6), (-5.0, 1.2, 'c')])
    _B['canopy'] = can
    _B['canopy_h'] = pattern(can, 'cross', sp=1.05, r=0.36, margin=0.5)
    return _B


def boat(x, y, rot=0.0, z=0.7, scale=1.25):
    g = _boat_geo()
    M = mat(x, y, rot, scale)
    return [leather(g['hull'], M, z, AMBER, g['hull_h'], edge=0.36),
            leather(g['canopy'], M, z, (0.70, 0.52, 0.24), g['canopy_h'], edge=0.3)], M


# ================================================================= SCENERY
MOON_C = np.array([44.0, 27.0])
MOON_R = 8.5


SKY_DYE = (0.72, 0.80, 0.98)


def sky(z=0.25, moon_c=MOON_C, moon_r=MOON_R, stars=True, t=0.0):
    holes = [circle(moon_c[0], moon_c[1], moon_r, 90)]
    rng = np.random.default_rng(5)
    if stars:
        for _ in range(55):
            sx, sy = rng.uniform(-88, 88), rng.uniform(8, 49)
            if np.hypot(sx - moon_c[0], sy - moon_c[1]) < moon_r + 4:
                continue
            r = rng.choice([0.16, 0.2, 0.26, 0.34])
            holes.append(circle(sx, sy, r, 8))
    for (cx, cy, sc) in [(-52, 34, 1.0), (-22, 41, 0.75), (16, 36, 0.6), (66, 42, 0.8)]:
        holes += cloud_cut(cx, cy, sc)
    out = []
    for k, (bot, amp, ph) in enumerate([(-34, 0.0, 0.0), (2, 2.0, 1.0), (22, 2.5, 2.3), (38, 2.0, 4.0)]):
        xs = np.linspace(-120, 120, 60)
        edge = bot + amp * np.sin(xs * 0.05 + ph) + amp * 0.5 * np.sin(xs * 0.13 + ph * 2)
        poly = np.vstack([[[-120, 70]], np.stack([xs, edge], 1)[::-1][::-1], [[120, 70]]])
        poly = np.vstack([np.stack([xs, edge], 1), [[120, 70], [-120, 70]]])
        hs = [h for h in holes if h[:, 1].min() > edge.min() - 1] if k else holes
        out.append(Shape(poly, z=z + 0.01 * k, dye=SKY_DYE, holes=hs))
    return out


def cloud_cut(cx, cy, s):
    """Spiral cloud motif as a set of thin crescent strokes."""
    out = []
    for (ox, oy, r, a0, a1) in [(0, 0, 2.6, 0.0, 1.7), (-4.4, -0.6, 2.0, 0.2, 1.6), (4.2, -0.8, 1.9, -0.1, 1.5), (-1, -2.2, 6.5, 0.4, 0.62)]:
        a = np.linspace(a0 * np.pi, a1 * np.pi, 18)
        w = 0.23 if r < 5 else 0.2
        outer = np.stack([cx + s * (ox + (r + w) * np.cos(a)), cy + s * (oy + (r + w) * np.sin(a))], 1)
        inner = np.stack([cx + s * (ox + (r - w) * np.cos(a[::-1])), cy + s * (oy + (r - w) * np.sin(a[::-1]))], 1)
        out.append(np.vstack([outer, inner]))
        # inner curl
        if r < 5:
            a2 = np.linspace(a1 * np.pi, (a1 + 0.9) * np.pi, 10)
            rr = np.linspace(r, r * 0.45, 10)
            o2 = np.stack([cx + s * (ox + (rr + w) * np.cos(a2)), cy + s * (oy + (rr + w) * np.sin(a2))], 1)
            i2 = np.stack([cx + s * (ox + (rr - w) * np.cos(a2))[::-1], cy + s * (oy + (rr - w) * np.sin(a2))[::-1]], 1)
            out.append(np.vstack([o2, i2]))
    return out


def mountains(z=0.3):
    rng = np.random.default_rng(9)
    shapes = []
    for k, (base, amp, dye, seed) in enumerate([(-6, 14, (0.66, 0.73, 0.84), 1), (-12, 10, (0.55, 0.66, 0.72), 2)]):
        r = np.random.default_rng(seed)
        xs = np.linspace(-110, 110, 23)
        pts = [(-110, -60, 'c')]
        for i, x in enumerate(xs):
            hgt = base + amp * (0.35 + 0.65 * abs(np.sin(i * 1.3 + seed))) * r.uniform(0.5, 1.0)
            pts.append((x, hgt))
        pts.append((110, -60, 'c'))
        shapes.append(Shape(catmull(pts, n=6), z=z + 0.02 * k, dye=dye))
    shapes += pagoda(-58.0, -9.5, z=z + 0.03)
    return shapes


def pagoda(x, y, z=0.33, s=1.0, dye=(0.50, 0.60, 0.66)):
    """Five-tier pagoda with upturned eaves on the far shore."""
    out = []
    yy = y
    w = 3.2 * s
    for k in range(5):
        h = (2.6 - 0.25 * k) * s
        body = np.array([[x - w * 0.62, yy], [x + w * 0.62, yy], [x + w * 0.62, yy + h * 0.55], [x - w * 0.62, yy + h * 0.55]])
        out.append(Shape(body, z=z, dye=dye, holes=[np.array([[x - 0.25 * s, yy + 0.2 * s], [x + 0.25 * s, yy + 0.2 * s], [x + 0.25 * s, yy + h * 0.45], [x - 0.25 * s, yy + h * 0.45]])]))
        ry = yy + h * 0.55
        roof = catmull([(x - w * 1.25, ry + 0.55 * s, 'c'), (x - w * 0.9, ry + 0.05 * s), (x + w * 0.9, ry + 0.05 * s), (x + w * 1.25, ry + 0.55 * s, 'c'),
                        (x + w * 0.75, ry + 0.45 * s), (x + w * 0.45, ry + h * 0.45), (x - w * 0.45, ry + h * 0.45), (x - w * 0.75, ry + 0.45 * s)], n=5)
        out.append(Shape(roof, z=z, dye=dye))
        yy = ry + h * 0.45
        w *= 0.84
    out.append(Shape(np.array([[x, yy], [x, yy + 2.6 * s]]), z=z, dye=dye, line=True, width=0.25 * s))
    return out


def water_top(x, t, layer):
    if layer == 0:
        return -18 + 1.1 * np.sin(x * 0.11 + t * 0.9) + 0.6 * np.sin(x * 0.27 - t * 1.3)
    return -24 + 1.3 * np.sin(x * 0.09 - t * 0.7 + 1.0) + 0.7 * np.sin(x * 0.23 + t * 1.6)


_W = {}


def water(t, z=0.35, slide=0.0):
    out = []
    for layer, (dye, zz) in enumerate([(TEAL, z), (TEAL_D, z + 0.01)]):
        xs = np.linspace(-110, 110, 90)
        top = water_top(xs, t, layer)
        poly = np.vstack([[[-110, -70]], np.stack([xs, top], 1), [[110, -70]]])
        key = ('wh', layer)
        if key not in _W:
            box = np.array([[-130, -68], [130, -68], [130, -28 - 6 * layer], [-130, -28 - 6 * layer]])
            _W[key] = pattern(box, 'crescents', sp=7.0 + layer, r=1.25, margin=0.2, seed=layer)
        sh = (slide * (1.0 + 0.6 * layer) + t * (1.2 if layer else -0.8)) % (7.0 + layer)
        holes = [h + [sh, 0.0] for h in _W[key]]
        out.append(Shape(poly, z=zz, dye=dye, edge=0.3, edge_t=0.2, holes=holes))
    return out


def reflection(t, center=(44.0, -34.0), shatter=0.0, seed=0, z=0.36):
    """Moon reflection as cut strips in the water. shatter 0..1 scatters them."""
    rng = np.random.default_rng(seed)
    out = []
    widths = [3.0, 6.0, 7.6, 7.0, 5.4, 3.6, 1.8]
    for i, w in enumerate(widths):
        yy = center[1] + 2.4 - i * 1.15
        wob = 0.8 * np.sin(t * 1.9 + i * 1.3) + 0.4 * np.sin(t * 3.1 + i * 2.1)
        ox = wob + shatter * rng.uniform(-12, 12)
        oy = shatter * rng.uniform(-3, 3)
        ww = w * (1 - 0.6 * shatter) * (0.9 + 0.1 * np.sin(t * 2.3 + i))
        poly = ellipse(center[0] + ox, yy + oy, ww, 0.36 * (1 - 0.3 * shatter), 24)
        out.append(Shape(poly, z=z, kind='cut'))
    return out


def reeds(x0, t, z=0.45, n=7, seed=3, side=1, wind=1.0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        bx = x0 + side * rng.uniform(0, 14)
        h = rng.uniform(26, 44)
        lean = side * rng.uniform(-0.05, 0.12)
        sway = 0.035 * wind * np.sin(t * rng.uniform(0.6, 1.0) + i)
        pts = []
        for k in range(9):
            s = k / 8
            a = lean + sway * s * s
            pts.append((bx + np.sin(a) * h * s + 0.4 * side * s * s * h * 0.1, -52 + h * s))
        pts = np.array(pts)
        out.append(Shape(pts, z=z, dye=REED, line=True, width=0.38))
        # leaves
        for k in (3, 5, 6):
            p = pts[k]
            d = side * (1 if (k + i) % 2 else -1)
            lf = catmull([(0, 0, 'c'), (d * 3, 2.2), (d * 7, 3.0 + rng.uniform(-1, 1), 'c'), (d * 3.2, 1.2)], n=5)
            ang = sway * 1.5
            out.append(Shape(apply(mat(p[0], p[1], ang), lf), z=z, dye=REED, edge=0.0))
        # seed head (plume)
        tip = pts[-1]
        out.append(Shape(ellipse(tip[0], tip[1] + 2.0, 0.55, 2.6, 16, rot=-(lean + sway)), z=z, dye=(0.22, 0.18, 0.10)))
    return out


# ================================================================= MOTH
_M = {}


def _moth_geo():
    if _M:
        return _M
    r = np.random.default_rng(2)
    fw = catmull([(0.3, 0.7, 'c'), (2.6, 1.6), (5.2, 2.3), (7.2, 2.3, 'c'), (6.6, 0.6), (5.6, -1.4, 'c'), (3.0, -1.1), (0.4, -0.6, 'c')], n=7)
    # scalloped outer margin
    _M['fw'] = fw
    _M['fw_h'] = [ellipse(4.6, 0.9, 0.42, 0.30, 12, rot=0.3),
                  np.vstack([np.stack([np.linspace(2.0, 5.6, 12), -0.15 + 0.35 * np.sin(np.linspace(0, 9, 12))], 1),
                             np.stack([np.linspace(5.6, 2.0, 12), -0.38 + 0.35 * np.sin(np.linspace(9, 0, 12))], 1)])]
    _M['hw'] = catmull([(0.3, -0.3, 'c'), (2.4, -0.9), (3.9, -1.6), (3.7, -2.8), (2.2, -3.4), (0.8, -2.6), (0.3, -1.2, 'c')], n=7)
    _M['hw_h'] = [circle(2.4, -2.1, 0.32, 10)]
    body = catmull([(0, 1.6), (0.75, 1.0), (0.85, -0.3), (0.65, -2.2), (0.35, -3.6), (0, -4.0), (-0.35, -3.6), (-0.65, -2.2), (-0.85, -0.3), (-0.75, 1.0)], n=10)
    # fur: jitter the outline
    c = body.mean(0)
    d = body - c
    body = c + d * (1 + 0.07 * r.standard_normal(len(body)))[:, None]
    _M['body'] = body
    _M['head'] = circle(0, 1.85, 0.62, 12)
    return _M
    _M['fw'] = catmull([(0.2, 0.5, 'c'), (2.4, 1.9), (4.8, 2.9), (6.4, 3.0, 'c'), (6.0, 1.6), (5.0, -0.4), (2.6, -0.9), (0.3, -0.3, 'c')], n=7)
    _M['fw_h'] = [ellipse(4.3, 1.4, 0.55, 0.45, 14), ellipse(2.4, 0.4, 0.28, 0.22, 10)]
    _M['hw'] = catmull([(0.2, -0.2, 'c'), (2.6, -0.9), (4.2, -1.8), (3.9, -3.4), (2.4, -4.0), (0.7, -2.6), (0.15, -0.9, 'c')], n=7)
    _M['hw_h'] = [circle(2.6, -2.4, 0.42, 12)]
    _M['body'] = catmull([(0, 1.6), (0.55, 0.8), (0.6, -0.5), (0.45, -2.6), (0, -3.6), (-0.45, -2.6), (-0.6, -0.5), (-0.55, 0.8)])
    _M['head'] = circle(0, 1.75, 0.5, 12)
    return _M


def moth(x, y, z, flap=0.0, rot=0.0, scale=1.0, legs_out=0.0):
    """flap: wing phase angle; projected wing span = cos(flap). Seen from the lamp side (dorsal-ish)."""
    g = _moth_geo()
    out = []
    base = mat(x, y, rot, scale)
    c = np.cos(flap)
    c_h = np.cos(flap * 0.92 + 0.12)
    for sgn in (1, -1):
        Mw = base @ mat(0, 0.2, 0, sgn * max(c, 0.06), 1.0)
        out.append(Shape(apply(Mw, g['fw']), z=z, dye=MOTH, edge=0.12, edge_t=0.03, holes=[apply(Mw, h) for h in g['fw_h']]))
        Mh = base @ mat(0, 0.0, 0, sgn * max(c_h, 0.06), 1.0)
        out.append(Shape(apply(Mh, g['hw']), z=z, dye=MOTH, edge=0.12, edge_t=0.03, holes=[apply(Mh, h) for h in g['hw_h']]))
        # feathered antenna
        ant = np.array([[sgn * 0.2, 2.1], [sgn * 0.9, 3.4], [sgn * 1.9, 4.3], [sgn * 2.9, 4.7]])
        aw = apply(base, ant)
        out.append(Shape(aw, z=z, dye=MOTH, line=True, width=0.14))
        for k in np.linspace(0.15, 0.9, 7):
            i = int(k * 3)
            f = k * 3 - i
            p = ant[i] * (1 - f) + ant[min(i + 1, 3)] * f
            for s2 in (1, -1):
                q = p + np.array([sgn * 0.25 + s2 * 0.18, 0.35 * s2 + 0.15]) * (1 - k * 0.5)
                out.append(Shape(apply(base, np.array([p, q])), z=z, dye=MOTH, line=True, width=0.07))
        if legs_out > 0:
            for k, a in enumerate((0.4, 0.0, -0.4)):
                p0 = np.array([sgn * 0.4, 0.6 - k * 0.6])
                p1 = p0 + np.array([sgn * 1.6 * legs_out, (a - 0.25) * 1.2])
                p2 = p1 + np.array([sgn * 0.5, -0.6])
                out.append(Shape(apply(base, np.array([p0, p1, p2])), z=z, dye=MOTH, line=True, width=0.1))
    out.append(Shape(apply(base, g['body']), z=z, dye=(0.08, 0.07, 0.06)))
    out.append(Shape(apply(base, g['head']), z=z, dye=(0.08, 0.07, 0.06)))
    return out


# ================================================================= PUPPETEER HAND
def hand(x, y, z, rot=0.0, scale=1.0, curl=0.0, flip=False):
    """Open human hand reaching down (fingers toward -y). curl 0..1 closes the fingers."""
    out = []
    M = mat(x, y, rot, -scale if flip else scale, scale)
    palm = catmull([(-4.2, 9, 'c'), (-4.4, 3.0), (-3.6, -0.5), (3.8, -0.6), (4.4, 2.5), (4.0, 9, 'c'), (3.6, 26, 'c'), (-3.8, 26, 'c')])
    out.append(Shape(apply(M, palm), z=z, dye=(0.05, 0.045, 0.04)))
    fingers = [(-2.9, 6.4), (-0.95, 7.6), (0.95, 7.2), (2.9, 5.8)]
    for i, (fx, L) in enumerate(fingers):
        segs = [0.45, 0.32, 0.23]
        p = np.array([fx, 0.0])
        a = 0.0 + (fx * 0.02)
        pts_l, pts_r = [], []
        w = 0.95 - 0.06 * abs(i - 1.5)
        cur = p.copy()
        for k, s in enumerate(segs):
            a += curl * (0.7 + 0.2 * k)
            d = np.array([np.sin(a), -np.cos(a)])
            n = np.array([-d[1], d[0]])
            ww = w * (1 - 0.12 * k)
            pts_l.append(cur + n * ww)
            pts_r.append(cur - n * ww)
            cur = cur + d * L * s
        tip = cur
        poly = np.vstack([pts_l, [tip + np.array([0, 0])], pts_r[::-1]])
        poly = catmull([tuple(q) for q in poly], n=4)
        out.append(Shape(apply(M, poly), z=z, dye=(0.05, 0.045, 0.04)))
    # thumb
    th = catmull([(3.6, 4.5), (6.4, 2.6), (8.2, 0.4), (8.0, -0.6), (6.6, 0.0), (4.0, 0.8)])
    out.append(Shape(apply(M, th), z=z, dye=(0.05, 0.045, 0.04)))
    return out


# ================================================================= TEXT / TITLE PLAQUE
_TXT = {}


def text_polys(text, font='kaiu.ttf', height=10.0, key=None):
    """Glyph outlines as (outer polygons, hole polygons) in units, centred on origin."""
    import os
    from PIL import Image, ImageDraw, ImageFont
    k = (text, font, height)
    if k in _TXT:
        return _TXT[k]
    fp = os.path.join(os.path.dirname(__file__), '..', 'assets', font)
    px = 400
    f = ImageFont.truetype(fp, px)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 40
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), text, font=f, fill=255)
    a = np.array(im)
    cs, hier = cv2.findContours((a > 127).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    sc = height / (bb[3] - bb[1])
    outers, holes = [], []
    for c, hh in zip(cs, hier[0]):
        c = c[:, 0, :].astype(np.float64)
        if len(c) < 3:
            continue
        P = np.stack([(c[:, 0] - w / 2) * sc, -(c[:, 1] - h / 2) * sc], 1)
        (holes if hh[3] >= 0 else outers).append(P)
    _TXT[k] = (outers, holes)
    return outers, holes


def title_plaque(x, y, z, scale=1.0, rot=0.0):
    M = mat(x, y, rot, scale)
    out = []
    plate = catmull([(-30, -13, 'c'), (30, -13, 'c'), (32, -11), (32, 11), (30, 13, 'c'), (-30, 13, 'c'), (-32, 11), (-32, -11)], n=4)
    o_big, h_big = text_polys('撈月', height=13.0)
    o_sm, h_sm = text_polys('CATCHING  THE  MOON', font='kaiu.ttf', height=3.2)
    holes = [g + [0, 2.2] for g in o_big] + [g + [0, -9.0] for g in o_sm]
    # border dots
    for xx in np.arange(-28, 28.1, 2.0):
        holes.append(circle(xx, 11.2, 0.35, 8))
        holes.append(circle(xx, -11.2, 0.35, 8))
    out.append(Shape(apply(M, plate), z=z, dye=RED, edge=0.5, edge_t=EDGE_T, holes=[apply(M, h) for h in holes]))
    # islands inside letters (counters) are leather again
    for g in h_big:
        out.append(Shape(apply(M, g + [0, 2.2]), z=z, dye=RED))
    for g in h_sm:
        out.append(Shape(apply(M, g + [0, -9.0]), z=z, dye=RED))
    return out


def window_wall(cx, cy, z, w=46.0, h=40.0, open_=1.0):
    """Opaque wall with a four-pane window (for moonlight). open_ scales the light opening."""
    wall = np.array([[-400, -400], [400, -400], [400, 400], [-400, 400]]) + [cx, cy]
    holes = []
    bar = 3.2
    pw, ph = (w - 3 * bar) / 2, (h - 3 * bar) / 2
    for i in range(2):
        for j in range(2):
            x0 = cx - w / 2 + bar + i * (pw + bar)
            y0 = cy - h / 2 + bar + j * (ph + bar)
            ww = pw * (open_ if i == 1 else 1.0)
            holes.append(np.array([[x0, y0], [x0 + ww, y0], [x0 + ww, y0 + ph], [x0, y0 + ph]]))
    return [Shape(wall, z=z, dye=(0.0, 0.0, 0.0), holes=holes)]


def lamp_silhouette(x, y, z):
    """Oil lamp on a stand, seen against moonlight."""
    pts = catmull([(-1.2, 0, 'c'), (1.2, 0, 'c'), (2.6, 1.2), (2.0, 2.4), (0.5, 2.8), (0.4, 3.6, 'c'), (0.2, 4.6), (0, 5.2, 'c'),
                   (-0.2, 4.6), (-0.4, 3.6, 'c'), (-0.5, 2.8), (-2.0, 2.4), (-2.6, 1.2)])
    stand = np.array([[-0.35, -18], [0.35, -18], [0.35, 0], [-0.35, 0]])
    base = np.array([[-4, -19.5], [4, -19.5], [3, -18], [-3, -18]])
    return [Shape(pts * 1.6 + [x, y], z=z, dye=(0.02, 0.02, 0.03)), Shape(stand * 1.6 + [x, y], z=z, dye=(0.02, 0.02, 0.03)),
            Shape(base * 1.6 + [x, y], z=z, dye=(0.02, 0.02, 0.03))]


def moon_window(cx, cy, z, R=44.0, shutter=1.0):
    """Opaque wall with a round lattice window (moon gate). shutter 0..1 slides a disc off the opening,
    so the light grows like a waxing moon."""
    K = (0.0, 0.0, 0.0)
    wall = np.array([[-500, -500], [500, -500], [500, 500], [-500, 500]]) + [cx, cy]
    out = [Shape(wall, z=z, dye=K, holes=[circle(cx, cy, R, 160)])]
    ri = 0.70 * R
    # inner ring + outer rim bars
    for r_, w in ((ri, 2.6), (R - 0.8, 2.2)):
        out.append(Shape(circle(cx, cy, r_, 160), z=z, dye=K, line=True, width=w))
    # middle ring in the band
    out.append(Shape(circle(cx, cy, (ri + R) / 2, 160), z=z, dye=K, line=True, width=1.4))
    # radial spokes in the band, with little fret hooks
    for k in range(24):
        a = 2 * np.pi * k / 24 + 0.06
        d = np.array([np.cos(a), np.sin(a)])
        p0 = np.array([cx, cy]) + d * ri
        p1 = np.array([cx, cy]) + d * R
        out.append(Shape(np.array([p0, p1]), z=z, dye=K, line=True, width=1.5))
        if k % 2 == 0:
            n = np.array([-d[1], d[0]])
            pm = np.array([cx, cy]) + d * (ri + R) / 2
            hook = np.array([pm + d * 2.2, pm + d * 2.2 + n * 2.4, pm - d * 0.6 + n * 2.4])
            out.append(Shape(hook, z=z, dye=K, line=True, width=1.1))
    # sliding shutter (a disc slightly bigger than the opening)
    if shutter < 1.0:
        off = shutter * 2.15 * R
        out.append(Shape(circle(cx + off, cy + 0.1 * off, R * 1.06, 120), z=z - 4.0, dye=K))
    return out
