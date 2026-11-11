"""Backstage cutaway: the oil lamp behind the paper screen, in close-up.
render_flame(state, seed) -> uint8 frame. state keys:
  power (0..1 flame size), flare (0..1 burst), match (None or (x, y, head_glow)), moth (None or (x, y, flap, rot, scale)),
  hand (None or (x, y, pinch 0..1, blur)), smoke (0..1 amount, age), screen_glow (0..1)"""
import numpy as np, cv2
import engine
from engine import catmull, ellipse, mat, apply

W, H = engine.W, engine.H
S = W / 1920.0
FX, FY = 0.40 * W, 0.62 * H          # wick tip in pixels


def _grid():
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    return xs, ys


_G = {}


def grid():
    if 'g' not in _G:
        _G['g'] = _grid()
    return _G['g']


def nz(t, s):
    return np.sin(t * 1.7 + s * 3.1) * 0.5 + np.sin(t * 2.9 + s * 1.3 + 1.0) * 0.3 + np.sin(t * 5.3 + s * 7.7) * 0.2


def flame_layer(t, power, flare, squeeze=0.0):
    """Additive light (H,W,3) of the flame + halo."""
    xs, ys = grid()
    img = np.zeros((H, W, 3), np.float32)
    if power <= 0.01:
        return img
    h = (150 + 30 * nz(t * 6, 1) + 120 * flare) * S * power * (1 - 0.7 * squeeze)
    w = (34 + 4 * nz(t * 7, 2) + 20 * flare) * S * (0.4 + 0.6 * power) * (1 - 0.5 * squeeze)
    sway = (10 * nz(t * 4.5, 3) + 6 * nz(t * 9, 4)) * S
    # normalized coordinate along flame: u=0 base (wick) -> 1 tip
    u = (FY - ys) / max(h, 1)
    sx = xs - FX - sway * np.clip(u, 0, 1) ** 2
    prof = np.where((u > -0.25) & (u < 1.0), np.sin(np.pi * np.clip((u + 0.25) / 1.25, 0, 1)) ** 0.75 * (1 - np.clip(u, 0, 1)) ** 0.35, 0)
    half = w * prof + 1e-3
    d = np.abs(sx) / half                # 0 at axis, 1 at edge
    inside = np.clip(1 - d, 0, 1) * (prof > 0)
    core = np.clip(1 - d * 1.6, 0, 1) * np.clip(1 - np.abs(u - 0.32) * 1.9, 0, 1)
    edge = inside ** 0.6
    col_edge = np.array([1.0, 0.45, 0.10], np.float32)
    col_mid = np.array([1.0, 0.78, 0.35], np.float32)
    col_core = np.array([1.0, 0.97, 0.85], np.float32)
    img += edge[..., None] * col_edge * 1.6
    img += (inside ** 1.4)[..., None] * col_mid * 1.4
    img += (core ** 1.2)[..., None] * col_core * 2.4
    # blue base
    blue = np.clip(1 - np.hypot((xs - FX) / (w * 0.9), (ys - FY - 0.02 * h) / (0.12 * h + 1)), 0, 1)
    img += (blue ** 1.5)[..., None] * np.array([0.15, 0.25, 0.9], np.float32) * 0.8
    img = cv2.GaussianBlur(img, (0, 0), 2.2 * S)
    # halo
    r = np.hypot(xs - FX, ys - (FY - 0.45 * h)) / (W * 0.30)
    halo = (power * (0.9 + 0.6 * flare)) / (1 + 9 * r * r)
    img += halo[..., None] * np.array([1.0, 0.62, 0.28], np.float32) * 0.55
    return img


def lamp_body(alpha, glow):
    """Draw the clay oil lamp silhouette (dish on a stand) with a warm rim; returns (occlusion, rim light)."""
    pts = catmull([(-1, 0.0, 'c'), (1, 0.0, 'c'), (1.25, 0.18), (0.85, 0.42), (0.18, 0.5), (0.1, 0.62, 'c'),
                   (-0.1, 0.62, 'c'), (-0.18, 0.5), (-0.85, 0.42), (-1.25, 0.18)], n=8)
    sc = 150 * S
    P = np.stack([FX + pts[:, 0] * sc, FY + 0.62 * sc - pts[:, 1] * sc + 4 * S], 1)
    stand = np.array([[FX - 14 * S, FY + 0.62 * sc + 4 * S], [FX + 14 * S, FY + 0.62 * sc + 4 * S], [FX + 22 * S, H + 10], [FX - 22 * S, H + 10]])
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32(P * 16), np.int32(stand * 16)], 255, cv2.LINE_AA, 4)
    occ = m.astype(np.float32) / 255
    # rim: top edge of the dish catches the flame
    rim = np.zeros((H, W), np.uint8)
    top = P[np.argsort(P[:, 1])[:12]]
    cv2.polylines(rim, [np.int32(P[(P[:, 1] < FY + 0.62 * sc - 0.3 * sc)] * 16)], False, 255, max(1, int(3 * S)), cv2.LINE_AA, 4)
    rim = cv2.GaussianBlur(rim.astype(np.float32) / 255, (0, 0), 1.5 * S) * glow
    return occ, rim


def match_layer(x, y, head):
    """Match stick (dark) + head glow (light)."""
    m = np.zeros((H, W), np.uint8)
    L = 420 * S
    p0 = np.array([x, y])
    p1 = p0 + np.array([L * 0.94, L * 0.34])
    cv2.line(m, tuple(np.int32(p0 * 16)), tuple(np.int32(p1 * 16)), 255, max(2, int(9 * S)), cv2.LINE_AA, 4)
    occ = m.astype(np.float32) / 255
    xs, ys = grid()
    r = np.hypot(xs - x, ys - y) / (60 * S)
    light = (head / (1 + 4 * r * r))[..., None] * np.array([1.0, 0.7, 0.35], np.float32) * 1.4
    core = np.clip(1 - r * 2.5, 0, 1)[..., None] * head * np.array([1.0, 0.95, 0.8], np.float32) * 2.0
    return occ, light + core


def moth_layer(x, y, flap, rot, scale):
    import puppets as P
    sh = P.moth(0, 0, 0.0, flap=flap, rot=rot, scale=scale)
    m = np.zeros((H, W), np.uint8)
    for s in sh:
        q = np.stack([x + s.poly[:, 0], y - s.poly[:, 1]], 1)
        if s.line:
            cv2.polylines(m, [np.int32(q * 16)], False, 230, max(1, int(s.width * scale * 0.9)), cv2.LINE_AA, 4)
        else:
            cv2.fillPoly(m, [np.int32(q * 16)], 235, cv2.LINE_AA, 4)
            for hh in s.holes:
                qh = np.stack([x + hh[:, 0], y - hh[:, 1]], 1)
                cv2.fillPoly(m, [np.int32(qh * 16)], 120, cv2.LINE_AA, 4)
    return m.astype(np.float32) / 255


def hand_layer(x, y, pinch, blur):
    """Side view of a right hand coming down from the upper right; index finger and thumb close on the wick.
    (x, y) is where the fingertips meet when closed. pinch 0 = open, 1 = closed."""
    k = 26.0 * S
    gap = (1 - pinch) * 0.5
    m = np.zeros((H, W), np.uint8)

    def P(pts):
        return np.int32(np.stack([x + np.array(pts)[:, 0] * k, y - np.array(pts)[:, 1] * k], 1) * 16)

    def rot(pts, c, a):
        c = np.array(c); ca, sa = np.cos(a), np.sin(a)
        return [tuple(c + np.array([ca * (px - c[0]) - sa * (py - c[1]), sa * (px - c[0]) + ca * (py - c[1])])) for px, py in pts]

    index = rot([(0.2, 0.3), (1.9, 1.6), (3.7, 3.2), (6.2, 5.2)], (6.2, 5.2), gap)
    thumb = rot([(0.3, -0.2), (2.4, -1.0), (4.6, -1.1), (7.4, 0.4)], (7.4, 0.4), -gap)
    cv2.polylines(m, [P(index)], False, 255, int(1.8 * k), cv2.LINE_AA, 4)
    cv2.polylines(m, [P(thumb)], False, 255, int(2.0 * k), cv2.LINE_AA, 4)
    for c, r in (((7.6, 2.0), 1.3), ((8.6, 3.3), 1.35), ((9.4, 4.7), 1.3)):      # curled fingers
        cv2.circle(m, tuple(P([c])[0]), int(r * k * 16), 255, -1, cv2.LINE_AA, 4)
    palm = [(5.8, 6.2), (6.8, 1.6), (8.0, -0.6), (11.5, 0.8), (14.5, 4.5), (13.5, 10.5), (9.0, 9.0)]
    cv2.fillPoly(m, [P(catmull(palm, n=5))], 255, cv2.LINE_AA, 4)
    cv2.line(m, tuple(P([(13.0, 6.5)])[0]), tuple(P([(36.0, 20.0)])[0]), 255, int(7.0 * k), cv2.LINE_AA, 4)
    a = m.astype(np.float32) / 255
    if blur > 0.5:
        a = engine.blur_img(a, blur * S, blur * S)
    return a


def smoke_layer(t, amount, age):
    xs, ys = grid()
    out = np.zeros((H, W), np.float32)
    if amount <= 0:
        return out
    for k in range(5):
        yy = FY - (40 + 90 * k) * S * (0.4 + age)
        xx = FX + 18 * S * np.sin(age * 2.0 + k * 1.3) * (1 + k * 0.6)
        r = (14 + 12 * k) * S * (0.5 + age)
        out += np.exp(-((xs - xx) ** 2 + (ys - yy) ** 2) / (2 * r * r)) * (1 - k / 5)
    return np.clip(out * amount * 0.6, 0, 1)


def render_flame(st, t, seed):
    img = np.zeros((H, W, 3), np.float32)
    power, flare = st.get('power', 0.0), st.get('flare', 0.0)
    squeeze = st['hand'][2] if st.get('hand') else 0.0
    # backstage: dark wall; the back of the paper screen glows at the right edge
    xs, ys = grid()
    glow = st.get('screen_glow', power)
    scr = np.clip((xs - 0.78 * W) / (0.16 * W), 0, 1) ** 1.5
    img += (scr * glow * 0.55)[..., None] * np.array([1.0, 0.80, 0.55], np.float32) * (0.75 + 0.25 * np.exp(-((ys - FY * 0.8) / (0.6 * H)) ** 2))[..., None]
    img += np.array([0.035, 0.022, 0.014], np.float32) * glow
    fl = flame_layer(t, power, flare, squeeze)
    img += fl
    # lamp body occludes, rim catches light
    occ, rim = lamp_body(1.0, power)
    img *= (1 - occ * 0.96)[..., None]
    img += rim[..., None] * np.array([1.0, 0.6, 0.3], np.float32) * 0.9
    if st.get('match'):
        mx, my, head = st['match']
        o, li = match_layer(mx, my, head)
        img *= (1 - 0.95 * o)[..., None]
        img += li
    if st.get('moth'):
        x, y, flap, rot, sc = st['moth']
        a = moth_layer(x, y, flap, rot, sc)
        img = img * (1 - 0.93 * a)[..., None] + (a * 0.04)[..., None] * np.array([1.0, 0.6, 0.3], np.float32)
    if st.get('sparks'):
        for (sx, sy, b) in st['sparks']:
            r = np.hypot(xs - sx, ys - sy) / (5 * S)
            img += (b / (1 + r * r * 3))[..., None] * np.array([1.0, 0.75, 0.35], np.float32)
    if st.get('smoke'):
        amt, age = st['smoke']
        sm = smoke_layer(t, amt, age)
        img = img * (1 - 0.3 * sm)[..., None] + sm[..., None] * np.array([0.10, 0.09, 0.085], np.float32)
    if st.get('hand'):
        hx, hy, pinch, blur = st['hand']
        a = hand_layer(hx, hy, pinch, blur)
        img *= (1 - 0.97 * a)[..., None]
    return engine.finish(img * st.get('exposure', 1.0), seed)
