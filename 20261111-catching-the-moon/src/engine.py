"""Shadow-theatre renderer.

World units: the paper screen is the plane z=0, 176 x 99 units, centred at origin, y up.
Objects live between light and screen at depth z>0 (distance from the screen).
Lamp: point-ish source at distance L behind the screen -> magnification + penumbra blur.
Moon: parallel source -> no magnification, offset by z*dir, tiny blur.
Each Shape is a polygon in its own plane coords (x, y) at depth z, with a dye (RGB
transmittance), dark leather edge, optional holes (cut-outs). Layers multiply.
"""
import numpy as np, cv2, os

_S = float(os.environ.get('MOTH_SCALE', '1'))
W, H = int(1920 * _S), int(1080 * _S)
PX = W / 192.0            # px per unit at zoom 1
SCR_W, SCR_H = 176.0, 99.0
ASSET = os.path.join(os.path.dirname(__file__), '..', 'assets')


# ---------------------------------------------------------------- geometry helpers
def catmull(points, closed=True, n=8):
    """Smooth closed curve through points. A point given as (x, y, 'c') is a hard corner."""
    P = np.array([[float(p[0]), float(p[1])] for p in points])
    C = np.array([len(p) > 2 for p in points])
    N = len(P)
    idx = np.arange(N) if closed else np.arange(N - 1)
    i0 = (idx - 1) % N if closed else np.maximum(idx - 1, 0)
    i2 = (idx + 1) % N
    i3 = (idx + 2) % N if closed else np.minimum(idx + 2, N - 1)
    a1, a2 = P[idx], P[i2]
    a0 = np.where(C[idx][:, None], a1, P[i0])
    a3 = np.where(C[i2][:, None], a2, P[i3])
    t = (np.arange(n) / n)[None, :, None]
    t2, t3 = t * t, t * t * t
    a0, a1, a2, a3 = (v[:, None, :] for v in (a0, a1, a2, a3))
    v = 0.5 * ((2 * a1) + (-a0 + a2) * t + (2 * a0 - 5 * a1 + 4 * a2 - a3) * t2 + (-a0 + 3 * a1 - 3 * a2 + a3) * t3)
    out = v.reshape(-1, 2)
    if not closed:
        out = np.vstack([out, P[-1:]])
    return out


def circle(cx, cy, r, n=40):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)


def ellipse(cx, cy, rx, ry, n=40, rot=0.0):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = rx * np.cos(a), ry * np.sin(a)
    c, s = np.cos(rot), np.sin(rot)
    return np.stack([cx + c * x - s * y, cy + s * x + c * y], 1)


def mat(tx=0.0, ty=0.0, rot=0.0, sx=1.0, sy=None):
    sy = sx if sy is None else sy
    c, s = np.cos(rot), np.sin(rot)
    return np.array([[c * sx, -s * sy, tx], [s * sx, c * sy, ty], [0, 0, 1.0]])


def apply(M, P):
    P = np.asarray(P, dtype=np.float64)
    return P @ M[:2, :2].T + M[:2, 2]


class Shape:
    __slots__ = ('poly', 'z', 'dye', 'edge', 'edge_t', 'holes', 'kind', 'line', 'width', 'paint')

    def __init__(self, poly, z=0.5, dye=(0.05, 0.05, 0.05), edge=0.0, edge_t=0.06, holes=(), kind='fill',
                 line=False, width=0.3):
        self.poly = np.asarray(poly, dtype=np.float64)
        self.z = z
        self.dye = np.array(dye, dtype=np.float32)
        self.edge = edge          # outline width in units (0 = none)
        self.edge_t = edge_t      # outline transmittance
        self.holes = [np.asarray(h, dtype=np.float64) for h in holes]
        self.kind = kind          # 'fill' multiplies; 'cut' resets the group buffer to clear
        self.line = line          # open polyline (rods, strings, antennae)
        self.width = width
        self.paint = False        # True: covers what is behind it in its own group (stacked cut-outs) instead of multiplying


# ---------------------------------------------------------------- light models
class Lamp:
    def __init__(self, x=0.0, y=6.0, L=150.0, size=1.8, power=1.0, color=(1.0, 0.80, 0.52)):
        self.x, self.y, self.L, self.size, self.power, self.color = x, y, L, size, power, color

    def project(self, P, z):
        m = self.L / max(self.L - z, 1e-3)
        c = np.array([self.x, self.y])
        return c + (P - c) * m, m

    def blur(self, z):
        return 0.25 * self.size * z / max(self.L - z, 1e-3)   # sigma ~ half the penumbra radius


class Moon:
    def __init__(self, dx=0.35, dy=-0.55, ang=0.012, power=0.0, color=(0.55, 0.70, 1.0)):
        self.dx, self.dy, self.ang, self.power, self.color = dx, dy, ang, power, color

    def project(self, P, z):
        return P + np.array([self.dx, self.dy]) * z, 1.0

    def blur(self, z):
        return self.ang * z


# ---------------------------------------------------------------- camera
class Cam:
    def __init__(self, x=0.0, y=0.0, zoom=1.0, rot=0.0):
        self.x, self.y, self.zoom, self.rot = x, y, zoom, rot

    def to_px(self, P):
        s = self.zoom * PX
        c, sn = np.cos(self.rot), np.sin(self.rot)
        x, y = P[:, 0] - self.x, P[:, 1] - self.y
        xr, yr = c * x - sn * y, sn * x + c * y
        return np.stack([W / 2 + xr * s, H / 2 - yr * s], 1)

    def affine_from_units(self):
        """2x3 matrix mapping unit coords -> pixel coords."""
        s = self.zoom * PX
        c, sn = np.cos(self.rot), np.sin(self.rot)
        # px = W/2 + s*(c*(x-cx) - sn*(y-cy)); py = H/2 - s*(sn*(x-cx) + c*(y-cy))
        A = np.array([[s * c, -s * sn], [-s * sn, -s * c]])
        b = np.array([W / 2, H / 2]) - A @ np.array([self.x, self.y])
        return np.hstack([A, b[:, None]])


# ---------------------------------------------------------------- paper & frame textures
_TEX = {}
PAPER_PPU = 14.0


def _noise(h, w, scale, seed):
    r = np.random.default_rng(seed)
    small = r.standard_normal((max(2, int(h / scale)), max(2, int(w / scale)))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


def paper_texture():
    if 'paper' in _TEX:
        return _TEX['paper']
    fn = os.path.join(ASSET, 'paper.npy')
    if os.path.exists(fn):
        _TEX['paper'] = np.load(fn)
        return _TEX['paper']
    # covers x in [-110, 110], y in [-62, 62] units
    w, h = int(220 * PAPER_PPU), int(124 * PAPER_PPU)
    r = np.random.default_rng(7)
    a = np.ones((h, w), np.float32)
    a += 0.035 * _noise(h, w, 90, 1) + 0.02 * _noise(h, w, 25, 2) + 0.012 * _noise(h, w, 6, 3)
    # fibres
    fib = np.zeros((h, w), np.float32)
    for _ in range(9000):
        x0, y0 = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, np.pi)
        ln = r.uniform(8, 60)
        pts = []
        for k in range(6):
            t = k / 5 * ln
            ang += r.normal(0, 0.15)
            pts.append((x0 + np.cos(ang) * t, y0 + np.sin(ang) * t))
        cv2.polylines(fib, [np.int32(pts)], False, float(r.choice([-1, 1]) * r.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.7)
    a += 0.05 * fib
    # paper sheet seams (vertical), slightly darker overlaps
    for sx in (-58.0, 0.5, 59.0):
        px = int((sx + 110) * PAPER_PPU)
        a[:, px - 6:px + 6] *= 0.93
        a[:, px - 6:px - 4] *= 0.96
    a = np.clip(a, 0.6, 1.2)
    col = np.stack([a * 0.96, a * 0.90, a * 0.80], -1).astype(np.float32)
    np.save(fn, col)
    _TEX['paper'] = col
    return col


def wood_texture():
    if 'wood' in _TEX:
        return _TEX['wood']
    w, h = int(220 * 6), int(124 * 6)
    yy = np.linspace(0, 1, h)[:, None]
    g = np.sin(yy * 220 + 6 * _noise(h, w, 60, 11)) * 0.5 + 0.5
    v = 0.6 + 0.25 * g + 0.15 * _noise(h, w, 8, 12)
    col = np.stack([v * 0.20, v * 0.11, v * 0.06], -1).astype(np.float32)
    _TEX['wood'] = col
    return col


def sample_tex(tex, ppu, cam, ox=110.0, oy=62.0, border=None):
    """Sample a texture defined in unit space (origin at tex pixel (ox*ppu, oy*ppu), y up) into the frame."""
    A = cam.affine_from_units()                     # units -> px
    # texture px -> units: u = (tx/ppu - ox), v = (oy - ty/ppu)
    T = np.array([[1 / ppu, 0, -ox], [0, -1 / ppu, oy], [0, 0, 1]])
    M = np.vstack([A, [0, 0, 1]]) @ T
    if border is None:
        return cv2.warpAffine(tex, M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return cv2.warpAffine(tex, M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=border)


_STATIC = {}


def static_layer(key, shapes_fn, ppu=14.0, box=(-125.0, 125.0, -75.0, 85.0)):
    """Pre-render sharp, unmoving scenery (z ~ 0) once into a world-space transmittance texture."""
    global W, H
    if key in _STATIC:
        return _STATIC[key]
    x0, x1, y0, y1 = box
    sW, sH = W, H
    W, H = int((x1 - x0) * ppu), int((y1 - y0) * ppu)
    try:
        cam = Cam((x0 + x1) / 2, (y0 + y1) / 2, zoom=ppu / PX)
        T = shadow_transmittance(shapes_fn(), cam, Lamp(power=1.0))
    finally:
        W, H = sW, sH
    _STATIC[key] = (T, ppu, -x0, y1)
    return _STATIC[key]


def statics_T(statics, cam):
    T = None
    for (tex, ppu, ox, oy), dy in statics:
        s = sample_tex(tex, ppu, Cam(cam.x, cam.y - dy, cam.zoom, cam.rot), ox=ox, oy=oy, border=(1.0, 1.0, 1.0))
        T = s if T is None else T * s
    return T


# ---------------------------------------------------------------- rasterising
SUB = 4  # subpixel bits for cv2


def _poly_px(cam, light, sh):
    P, m = light.project(sh.poly, sh.z)
    return cam.to_px(P), m


def draw_group(shapes, cam, light, sigma_units):
    """Render a set of shapes sharing (roughly) one depth; returns (buf, x0, y0) transmittance patch."""
    s = cam.zoom * PX
    sig = sigma_units * s * 1.0
    # bounding box in px
    allp = []
    proj = []
    for sh in shapes:
        P, m = light.project(sh.poly, sh.z)
        px = cam.to_px(P)
        holes = [cam.to_px(light.project(hh, sh.z)[0]) for hh in sh.holes]
        proj.append((sh, px, holes, m))
        allp.append(px)
    allp = np.concatenate(allp)
    pad = 3.2 * sig * 1.8 + 6
    x0 = int(max(0, np.floor(allp[:, 0].min() - pad)))
    x1 = int(min(W, np.ceil(allp[:, 0].max() + pad)))
    y0 = int(max(0, np.floor(allp[:, 1].min() - pad)))
    y1 = int(min(H, np.ceil(allp[:, 1].max() + pad)))
    if x1 <= x0 or y1 <= y0:
        return None
    bw, bh = x1 - x0, y1 - y0
    # supersample small buffers is too costly; cv2 AA is good enough at 1080p
    buf = np.ones((bh, bw, 3), np.float32)
    off = np.array([x0, y0])
    for sh, px, holes, m in proj:
        lw = 0
        if sh.line:
            lw = max(1, int(round(sh.width * s * m)))
        elif sh.edge > 0:
            lw = max(1, int(round(sh.edge * s * m)))
        lp = px - off
        sx0 = int(max(0, np.floor(lp[:, 0].min() - lw - 2)))
        sx1 = int(min(bw, np.ceil(lp[:, 0].max() + lw + 2)))
        sy0 = int(max(0, np.floor(lp[:, 1].min() - lw - 2)))
        sy1 = int(min(bh, np.ceil(lp[:, 1].max() + lw + 2)))
        if sx1 <= sx0 or sy1 <= sy0:
            continue
        sw, shh = sx1 - sx0, sy1 - sy0
        o2 = off + np.array([sx0, sy0])
        q = np.int32(np.round((px - o2) * (1 << SUB)))
        sub = buf[sy0:sy1, sx0:sx1]
        if sh.line:
            msk = np.zeros((shh, sw), np.uint8)
            cv2.polylines(msk, [q], False, 255, lw, cv2.LINE_AA, SUB)
            a = msk.astype(np.float32)[..., None] / 255.0
            sub *= (1 - a) + a * sh.dye
            continue
        msk = np.zeros((shh, sw), np.uint8)
        cv2.fillPoly(msk, [q], 255, cv2.LINE_AA, SUB)
        a = msk.astype(np.float32)[..., None] / 255.0
        if sh.kind == 'cut':
            sub[:] = sub * (1 - a) + a
            continue
        if sh.paint:
            cov = a
            col = np.broadcast_to(sh.dye, a.shape[:2] + (3,)).astype(np.float32)
            if holes:
                hm = np.zeros((shh, sw), np.uint8)
                cv2.fillPoly(hm, [np.int32(np.round((h_ - o2) * (1 << SUB))) for h_ in holes], 255, cv2.LINE_AA, SUB)
                cov = cov * (1 - hm.astype(np.float32)[..., None] / 255.0)
            if sh.edge > 0:
                em = np.zeros((shh, sw), np.uint8)
                cv2.polylines(em, [q], True, 255, lw, cv2.LINE_AA, SUB)
                e = em.astype(np.float32)[..., None] / 255.0
                col = col * (1 - e) + e * sh.edge_t
                cov = np.maximum(cov, e)
            sub[:] = sub * (1 - cov) + cov * col
            continue
        part = (1 - a) + a * sh.dye
        if sh.edge > 0:
            em = np.zeros((shh, sw), np.uint8)
            cv2.polylines(em, [q], True, 255, lw, cv2.LINE_AA, SUB)
            e = em.astype(np.float32)[..., None] / 255.0
            part = part * (1 - e) + e * sh.edge_t
        if holes:
            hm = np.zeros((shh, sw), np.uint8)
            cv2.fillPoly(hm, [np.int32(np.round((h_ - o2) * (1 << SUB))) for h_ in holes], 255, cv2.LINE_AA, SUB)
            hh = hm.astype(np.float32)[..., None] / 255.0
            part = part * (1 - hh) + hh
        sub *= part
    # penumbra blur (flame is taller than wide)
    if sig > 0.35:
        buf = blur_img(1 - buf, sig, sig * 1.3)
        buf = 1 - buf
    return buf, x0, y0


def blur_img(img, sx, sy):
    if max(sx, sy) <= 10:
        return cv2.GaussianBlur(img, (0, 0), sx, sigmaY=sy)
    f = max(sx, sy) / 5.0
    h, w = img.shape[:2]
    sw, sh = max(2, int(w / f)), max(2, int(h / f))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sx / f, sigmaY=sy / f)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def shadow_transmittance(shapes, cam, light):
    """Group shapes by depth bin and multiply their blurred transmittance."""
    T = np.ones((H, W, 3), np.float32)
    groups = {}
    for sh in shapes:
        key = round(sh.z * 4) / 4 if sh.z < 6 else round(sh.z, 1)
        groups.setdefault(key, []).append(sh)
    # keep insertion order for cut ops within group
    for z, grp in groups.items():
        g = draw_group(grp, cam, light, light.blur(grp[0].z))
        if g is not None:
            buf, x0, y0 = g
            T[y0:y0 + buf.shape[0], x0:x0 + buf.shape[1]] *= buf
    return T


# ---------------------------------------------------------------- full frame
def light_field(cam, lamp, moon, moon_mask=None):
    """Illumination on the paper (H,W,3)."""
    hw, hh = W // 4, H // 4
    ys, xs = np.mgrid[0:hh, 0:hw].astype(np.float32)
    # px -> units (inverse of cam)
    s = cam.zoom * PX / 4
    c, sn = np.cos(cam.rot), np.sin(cam.rot)
    xr = (xs - hw / 2) / s
    yr = -(ys - hh / 2) / s
    ux = c * xr + sn * yr + cam.x
    uy = -sn * xr + c * yr + cam.y
    L = np.zeros((hh, hw, 3), np.float32)
    if lamp is not None and lamp.power > 0:
        r2 = (ux - lamp.x) ** 2 + (uy - lamp.y) ** 2
        fall = (1.0 / (1.0 + r2 / (95.0 ** 2))) ** 1.6
        warm = np.clip(fall, 0, 1)
        col = np.array(lamp.color, np.float32)
        edge = np.array([1.0, 0.62, 0.30], np.float32)
        mixc = warm[..., None] * col + (1 - warm[..., None]) * edge * col
        L += lamp.power * fall[..., None] * mixc
    L = cv2.resize(L, (W, H), interpolation=cv2.INTER_LINEAR)
    return L


def screen_mask(cam):
    rect = np.array([[-SCR_W / 2, -SCR_H / 2], [SCR_W / 2, -SCR_H / 2], [SCR_W / 2, SCR_H / 2], [-SCR_W / 2, SCR_H / 2]])
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(cam.to_px(rect) * 16))], 255, cv2.LINE_AA, 4)
    return m.astype(np.float32)[..., None] / 255.0


_GRAIN_RNG = np.random.default_rng(3)


_COMB = {}


def paper_statics(statics, cam):
    """paper albedo x static scenery transmittance, sampled for this camera.
    When the scenery is at rest (dy == 0) both are baked into one world-space texture: one warp per frame."""
    if statics and all(dy == 0 for _, dy in statics):
        key = tuple(id(s[0]) for s, _ in statics)
        if key not in _COMB:
            tex0, ppu, ox, oy = statics[0][0]
            h, w = tex0.shape[:2]
            comb = np.ones((h, w, 3), np.float32)
            for (tex, p2, ox2, oy2), _ in statics:
                assert p2 == ppu and ox2 == ox and tex.shape[:2] == (h, w)
                comb *= tex
            # paper resampled onto the same grid (paper origin at (110, 62) units, PAPER_PPU)
            ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
            ux = xs / ppu - ox
            uy = oy - ys / ppu
            mx = (ux + 110.0) * PAPER_PPU
            my = (62.0 - uy) * PAPER_PPU
            pap = cv2.remap(paper_texture(), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            _COMB.clear()
            _COMB[key] = (comb * pap, ppu, ox, oy)
        tex, ppu, ox, oy = _COMB[key]
        return sample_tex(tex, ppu, cam, ox=ox, oy=oy, border=(0.9, 0.85, 0.75))
    paper = sample_tex(paper_texture(), PAPER_PPU, cam)
    if statics:
        paper = paper * statics_T(statics, cam)
    return paper


def render(shapes, cam, lamp=None, moon=None, moon_shapes=None, grain_seed=0, exposure=1.0, extra_light=None, statics=None):
    img = np.zeros((H, W, 3), np.float32)
    if lamp is not None and lamp.power > 0:
        T = shadow_transmittance(shapes, cam, lamp)
        img += light_field(cam, lamp, None) * T
    if moon is not None and moon.power > 0:
        T2 = shadow_transmittance(moon_shapes if moon_shapes is not None else shapes, cam, moon)
        img += moon.power * np.array(moon.color, np.float32) * T2
    if extra_light is not None:
        img += extra_light
    img *= paper_statics(statics, cam)
    sm = screen_mask(cam)
    if sm.min() < 1:
        wood = sample_tex(wood_texture(), 6.0, cam)
        glow = blur_img(img * sm, 40, 40) * 0.25
        lit = (lamp.power if lamp is not None else 0.0)        # the moonlight never reaches the front of the stage
        img = img * sm + (1 - sm) * (wood * 0.32 * min(lit, 1.2) + glow)
    return finish(img * exposure, grain_seed)


_FIN = {}


def finish(img, seed):
    if 'vig' not in _FIN:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        r = ((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2
        _FIN['vig'] = np.ascontiguousarray(np.repeat((1 - 0.22 * r)[..., None], 3, 2).astype(np.float32))
    img = img.astype(np.float32, copy=False)
    # bloom
    bright = cv2.max(cv2.subtract(img, (0.75, 0.75, 0.75, 0)), 0.0)
    img = cv2.scaleAdd(blur_img(bright, 30, 30), 0.35, img)
    img = cv2.multiply(img, _FIN['vig'])
    # filmic shoulder + gamma: x/(1+x/4), then ^(1/1.9)
    den = cv2.add(cv2.multiply(img, (0.25, 0.25, 0.25, 0)), (1.0, 1.0, 1.0, 0))
    img = cv2.divide(img, den)
    img = cv2.max(img, 0.0)
    img = cv2.pow(img, 1 / 1.9)
    r = np.random.default_rng(seed)
    g = r.standard_normal((H // 2, W // 2)).astype(np.float32)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    g3 = cv2.merge([g, g, g])
    out = cv2.scaleAdd(g3, 0.012, img)
    return cv2.convertScaleAbs(cv2.max(out, 0.0), alpha=255.0, beta=0.5)
