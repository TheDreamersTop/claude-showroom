"""'Wildlife camera' renderer for a Life grid: bioluminescent cells, macro depth of field, dust, grain."""
import numpy as np, cv2

W, H = 1280, 720
rng = np.random.default_rng(7)

NEW = np.array([1.00, 0.97, 0.85], np.float32)   # newborn: warm white
MID = np.array([0.35, 1.00, 0.80], np.float32)   # young: aqua
OLD = np.array([0.95, 0.70, 0.28], np.float32)   # settled: amber moss


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def age_color(age):
    a1 = np.clip(age / 6.0, 0, 1)[..., None]
    a2 = np.clip((age - 6) / 40.0, 0, 1)[..., None]
    return NEW * (1 - a1) + MID * a1 * (1 - a2) + OLD * a2


class Dust:
    """Out-of-focus particles drifting between camera and grid."""
    def __init__(self, n=70):
        self.p = rng.uniform([-1, -1, 0.15], [1, 1, 1.0], size=(n, 3)).astype(np.float32)
        self.v = rng.normal(0, 0.006, size=(n, 3)).astype(np.float32)
        self.ph = rng.uniform(0, 6.28, n)

    def draw(self, img, t, cam_dx, cam_dy):
        layer = np.zeros((H // 4, W // 4), np.float32)
        for (x, y, d), (vx, vy, _), ph in zip(self.p, self.v, self.ph):
            px = ((x + vx * t * 30 - cam_dx * (1.2 - d)) % 2.4 - 1.2) * W / 2 + W / 2
            py = ((y + vy * t * 30 + 0.004 * t - cam_dy * (1.2 - d)) % 2.4 - 1.2) * H / 2 + H / 2
            r = 2 + 18 * (1 - d)
            b = 0.05 + 0.10 * (0.5 + 0.5 * np.sin(t * 0.7 + ph))
            cv2.circle(layer, (int(px / 4), int(py / 4)), max(1, int(r / 4)), b, -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 2.0)
        layer = cv2.resize(layer, (W, H), interpolation=cv2.INTER_LINEAR)
        img += layer[..., None] * np.array([0.55, 0.75, 0.8], np.float32)


GRAIN = rng.normal(0, 1, size=(8, H // 2, W // 2)).astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
YY2, XX2 = np.mgrid[0:H:2, 0:W:2].astype(np.float32)
BG = (np.array([0.010, 0.020, 0.026], np.float32) + (0.02 * (1 - yy / H))[..., None] * np.array([0.2, 0.5, 0.6], np.float32)).astype(np.float32)
_FOCUS = {}
_v = np.linspace(0, 6, 4096, dtype=np.float32)
LUT = ((np.clip(1 - np.exp(-1.6 * _v), 0, 1) ** (1 / 1.1)) * 255).astype(np.uint8)
VIGN = (1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.3).clip(0, 1)[..., None]


CELL_K = 12
_u = (np.arange(CELL_K) + 0.5) / CELL_K - 0.5
_d = ((np.abs(_u)[None, :] ** 2.5 + np.abs(_u)[:, None] ** 2.5) ** (1 / 2.5)) / 0.6
CELL_MASK = (np.clip(1 - _d, 0, 1) ** 0.6).astype(np.float32)


def render(alive, age, cam, t, focus=None, dust=None, overlay=None, grid_alpha=1.0, exposure=1.0):
    """alive: float32 HxW grid (0..1, blended between generations); age: float32 grid.
    cam: dict(cx, cy, z, rot) — z = pixels per cell. focus: (y_px, falloff) tilt-shift band or None."""
    cx, cy, z, rot = cam["cx"], cam["cy"], cam["z"], cam.get("rot", 0.0)
    gh, gw = alive.shape
    # visible crop of the grid (with margin)
    half = 0.5 * np.hypot(W, H) / z + 4
    x0, x1 = int(max(0, cx - half)), int(min(gw, cx + half + 1))
    y0, y1 = int(max(0, cy - half)), int(min(gh, cy + half + 1))
    col = age_color(age[y0:y1, x0:x1]) * alive[y0:y1, x0:x1, None]
    src = np.dstack([alive[y0:y1, x0:x1], col]).astype(np.float32)
    c, sn = np.cos(rot), np.sin(rot)

    def warp(src, s, flags):
        # s = source pixels per cell (fraction <1 = pre-averaged); grid coord (cells span [x, x+1]) -> pixel
        zz = z / s
        ox, oy = (cx - x0) * s - 0.5, (cy - y0) * s - 0.5
        M = np.array([[zz * c, -zz * sn, W / 2 - zz * (c * ox - sn * oy)],
                      [zz * sn, zz * c, H / 2 - zz * (sn * ox + c * oy)]], np.float32)
        return cv2.warpAffine(src, M, (W, H), flags=flags, borderMode=cv2.BORDER_CONSTANT)

    wsp = float(np.clip((z - 5) / 4, 0, 1))  # 1 = every cell drawn as its own body
    warped = None
    if wsp < 1:
        if z < 3:  # far zoom: pre-average so the picture doesn't shimmer
            k = int(np.ceil(3 / z))
            small_src = cv2.resize(src, (max(1, src.shape[1] // k), max(1, src.shape[0] // k)), interpolation=cv2.INTER_AREA)
            warped = warp(small_src, 1.0 / k, cv2.INTER_CUBIC)
        else:
            warped = warp(src, 1.0, cv2.INTER_CUBIC)
    if wsp > 0:
        k = CELL_K
        up = cv2.resize(src, (src.shape[1] * k, src.shape[0] * k), interpolation=cv2.INTER_NEAREST)
        hh, ww = up.shape[:2]
        mask = np.tile(CELL_MASK, (hh // k, ww // k))[..., None]
        sp = warp(up * mask, float(k), cv2.INTER_LINEAR)
        warped = sp if warped is None else warped * (1 - wsp) + sp * wsp
    A = np.clip(warped[..., 0], 0, None)
    rgb = warped[..., 1:] / np.maximum(A, 1e-3)[..., None]
    rgb = np.clip(rgb, 0, 1.2)
    near = np.clip((z - 1.5) / 6, 0, 1)            # 0 = far (density glow), 1 = macro (organisms)
    lo = 0.03 + 0.27 * near
    body = smoothstep(lo, lo + 0.25, A)
    nucleus = smoothstep(0.75, 1.0, A) * near
    rim = np.clip(body - smoothstep(lo + 0.12, lo + 0.45, A), 0, 1) * near
    emit = rgb * (body * 0.55)[..., None] + rgb * (rim * 0.9)[..., None] + (nucleus * 0.5)[..., None]
    emit = emit * (1 + 1.0 * float(np.clip((6 - z) / 4, 0, 1)))
    # background: deep water + faint lattice
    bg = BG.copy()
    if grid_alpha > 0 and z > 6:
        gx = (np.cos(rot) * (XX2 - W / 2) + np.sin(rot) * (YY2 - H / 2)) / z + cx
        gy = (-np.sin(rot) * (XX2 - W / 2) + np.cos(rot) * (YY2 - H / 2)) / z + cy
        lw = np.float32(1.4 / z)
        dx = np.abs(gx - np.round(gx)); dy = np.abs(gy - np.round(gy))
        line = np.clip(1 - np.minimum(dx, dy) / lw, 0, 1).astype(np.float32)
        a = 0.022 * grid_alpha * min(1.0, (z - 6) / 10)
        bg += cv2.resize(line, (W, H))[..., None] * (np.array([0.5, 0.8, 0.8], np.float32) * a)
    img = bg + emit * exposure
    # bloom (two scales)
    small = cv2.resize(emit, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(small, (0, 0), max(1.0, z * 0.35))
    g2 = cv2.GaussianBlur(small, (0, 0), max(3.0, z * 1.2))
    img += cv2.resize(0.9 * g1 + 0.7 * g2, (W, H), interpolation=cv2.INTER_LINEAR) * exposure
    if overlay is not None:
        img += overlay
    # tilt-shift depth of field
    if focus is not None:
        fy, fall = focus
        blurred = cv2.resize(cv2.GaussianBlur(cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 3.5), (W, H))
        key = (int(fy), int(fall))
        if key not in _FOCUS:
            _FOCUS[key] = (np.clip(np.abs(yy - fy) / fall, 0, 1)[..., None] ** 1.5).astype(np.float32)
        m = _FOCUS[key]
        img = img * (1 - m) + blurred * m
    if dust is not None:
        dust.draw(img, t, cx / 200, cy / 200)
    # grade: filmic shoulder, vignette, grain
    img = img * VIGN
    g = GRAIN[int(t * 12) % 8]
    img += cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * 0.010
    idx = np.clip(img * (4095 / 6), 0, 4095).astype(np.int32)
    return np.ascontiguousarray(LUT[idx][..., ::-1])  # -> BGR
