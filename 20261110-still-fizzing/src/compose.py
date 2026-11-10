"""Edit + grade + titles -> film.mp4. Usage: python compose.py [out.mp4] [--fast]"""
import os, sys, subprocess, math, glob
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import timeline as TL

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REN = os.path.join(ROOT, 'renders')
PREV = os.path.join(ROOT, '..', '_tmp', 'output', 'prev')
FONTS = os.path.join(ROOT, 'assets', 'fonts')
W, H, FPS = 1920, 1080, 24
CREAM = (246, 236, 214)
ORANGE = (236, 120, 60)
B = TL.bar

# (start, end, source, zoom0, zoom1, (panx0, pany0), (panx1, pany1), super)
# pan in fractions of the frame, zoom relative to a full-frame fit
EDL = [
    (B(0), B(1, 2), '1958-main', 1.00, 1.07, (0, 0), (0, -0.01), '1958'),
    (B(1, 2), B(2), '1958-detail', 1.02, 1.07, (0.01, 0), (-0.01, 0), None),
    (B(2), B(3), '1966-main', 1.00, 1.06, (0, 0), (0, -0.01), '1966'),
    (B(3), B(5), 'straws66', 1.0, 1.08, (0, 0.01), (0, -0.01), None),
    (B(5), B(6), '1974-main', 1.00, 1.06, (0, 0), (0, -0.01), '1974'),
    (B(6), B(7), '1974-detail', 1.02, 1.09, (0, 0), (0.01, 0), None),
    (B(7), B(8), '1987-main', 1.00, 1.06, (0, 0), (0, -0.01), '1987'),
    (B(8), B(9), '1987-detail', 1.02, 1.08, (0, 0), (-0.01, 0), None),
    (B(9), B(11), '2026-main', 1.00, 1.12, (0, 0), (0, -0.015), 'Today'),
    (B(11), B(12), 'straws26', 1.0, 1.07, (0, 0.01), (0, -0.01), None),
    (B(12), B(14), '2026-detail', 1.00, 1.12, (0, 0), (0.012, 0), None),
    (B(14), B(15, 1.5), 'hero-main', 1.0, 1.08, (0, 0.01), (0, -0.01), None),
    (B(15, 1.5), B(16), 'hero-macro', 1.02, 1.08, (0, 0), (0, 0), None),
    (B(16), B(16, 2.6), 'pop', 1.0, 1.0, (0, 0), (0, 0), None),
    (B(16, 2.6), TL.END, 'hero-pack2', 1.0, 1.05, (0, 0), (0, 0), 'ENDCARD'),
]
ALIAS = {'straws66': '1966-detail', 'straws26': '2026-straws'}


def load(name):
    name = ALIAS.get(name, name)
    for d in (REN, PREV):
        p = os.path.join(d, name + '.png')
        if os.path.exists(p):
            return Image.open(p).convert('RGB'), d == REN
    return None, False


class Fizz:
    """rising carbonation bubbles; the next decade shows through them, then they swallow the frame."""
    PRE, POST = 0.10, 0.42

    def __init__(self, n=55):
        self.n = n
        self.rs = None
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        self.yy, self.xx = yy * 4, xx * 4

    def bubbles(self, seed):
        r = np.random.default_rng(seed)
        x = np.clip(r.normal(0.5, 0.17, self.n), 0.02, 0.98) * W
        delay = r.uniform(0, 0.22, self.n)
        speed = r.uniform(1.6, 3.2, self.n) * H
        r0 = r.choice([8, 12, 18, 26, 40, 60], self.n, p=[0.25, 0.25, 0.2, 0.14, 0.1, 0.06]).astype(float)
        wob = r.uniform(0, 6.28, self.n)
        return x, delay, speed, r0, wob

    def blend(self, a, b, dt, seed):
        """dt: time relative to the cut (negative = before)."""
        u = (dt + self.PRE) / (self.PRE + self.POST)        # 0..1 over the transition
        if u <= 0:
            return a
        if u >= 1:
            return b
        x, delay, speed, r0, wob = self.bubbles(seed)
        tt = np.maximum(dt + self.PRE - delay, 0)
        y = H + 60 - speed * tt
        grow = 1 + 9 * max(u - 0.5, 0) ** 2 * 6
        rad = r0 * (1 + 2.0 * tt) * grow
        xs = x + 14 * np.sin(wob + tt * 18)
        best = np.zeros_like(self.xx)       # coverage mask
        dxm = np.zeros_like(self.xx)
        dym = np.zeros_like(self.xx)
        rim = np.zeros_like(self.xx)
        for xi, yi, ri, lv in zip(xs, y, rad, tt > 0):
            if not lv or yi < -ri:
                continue
            ex, ey = self.xx - xi, self.yy - yi
            d = np.sqrt(ex * ex + ey * ey) / ri
            m = np.clip((1 - d) / max(3.0 / ri, 0.06), 0, 1)
            sel = m > best
            best = np.where(sel, m, best)
            k = 0.45 * np.clip(1 - d * d, 0, 1)          # lens: magnify toward the centre
            dxm = np.where(sel, -ex * k, dxm)
            dym = np.where(sel, -ey * k, dym)
            if ri < 140:
                ang = np.arctan2(ey, ex)
                light = 0.35 + 0.65 * np.clip(np.cos(ang + 2.3), 0, 1)   # brighter on the upper left
                rim = np.maximum(rim, np.exp(-((d - 0.93) / 0.045) ** 2) * light)
                hx, hy = xi - 0.38 * ri, yi - 0.38 * ri                  # specular dot
                rim = np.maximum(rim, np.exp(-((self.xx - hx) ** 2 + (self.yy - hy) ** 2) / (2 * (0.09 * ri + 1) ** 2)))
        m = cv2.resize(best, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        mx = cv2.resize(dxm, (W, H), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(dym, (W, H), interpolation=cv2.INTER_LINEAR)
        gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        bl = cv2.remap(b.astype(np.float32), (gx + mx * (1 - u)).astype(np.float32), (gy + my * (1 - u)).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        rr = cv2.resize(rim, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        out = a * (1 - m) + bl * m
        return np.clip(out + rr * 0.30 * (1 - u) ** 1.5, 0, 1.5)


LOOKS = {  # sat, contrast, exposure, shadow tint, highlight tint, black lift
    '1958': (1.18, 1.18, -0.06, (0.00, -0.004, 0.012), (0.035, 0.012, -0.03), 0.00),
    '1966': (1.08, 1.15, -0.12, (-0.010, 0.006, 0.016), (0.02, -0.004, 0.0), 0.00),
    '1974': (0.88, 1.06, -0.04, (0.010, 0.004, -0.006), (0.04, 0.018, -0.03), 0.035),
    '1987': (1.00, 1.15, 0.00, (-0.012, 0.0, 0.025), (0.035, 0.012, -0.02), 0.00),
    '2026': (1.05, 1.12, -0.04, (-0.004, 0.0, 0.006), (0.02, 0.008, -0.012), 0.00),
    'hero': (0.86, 1.10, -0.04, (0.0, 0.0, 0.0), (0.012, 0.004, -0.004), 0.00),
}
EXPO = {'1966-detail': -0.40, '1966-main': -0.08, '1974-detail': -0.10}


def grade(im, src='hero'):
    """applied once per still: soft bloom, warm split-tone, slight contrast."""
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    hi = np.clip((lum - 0.65) / 0.35, 0, 1) * a
    small = Image.fromarray((hi * 255).astype(np.uint8)).resize((im.width // 8, im.height // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    bloom = np.asarray(small.resize(im.size, Image.BILINEAR)).astype(np.float32) / 255
    a = a + 0.22 * bloom
    sat, con, ex, sh, hl, lift = LOOKS[src.split('-')[0] if src.split('-')[0] in LOOKS else 'hero']
    a = a * 2 ** (ex + EXPO.get(src, 0.0))
    l = a.mean(2, keepdims=True)
    a = l + (a - l) * sat
    a = 0.5 + (a - 0.5) * con
    l = np.clip(a.mean(2, keepdims=True), 0, 1)
    a = a + (1 - l) * np.array(sh) + l * np.array(hl)
    a = np.clip(a, 0, 1)
    a = a * a * (3 - 2 * a) * 0.22 + a * 0.78
    a = lift + a * (1 - lift)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return (1 - 0.28 * np.clip(r - 0.45, 0, 1) ** 1.6)[..., None]


def font(n, s, wght=None):
    f = ImageFont.truetype(os.path.join(FONTS, n), s)
    if wght:
        try:
            f.set_variation_by_axes([wght] if 'Inter' not in n else [14, wght])
        except Exception:
            pass
    return f


def year_super(text):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font('PlayfairDisplay-Italicwght.ttf', 104, 500)
    x, y = 110, H - 225
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.text((x + 3, y + 4), text, font=f, fill=(0, 0, 0, 200))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(sh)
    d = ImageDraw.Draw(im)
    d.text((x, y), text, font=f, fill=(*CREAM, 255))
    tw = d.textlength(text, font=f)
    d.rectangle([x + 4, y + 140, x + 4 + tw * 0.35, y + 144], fill=(*ORANGE, 240))
    return im.filter(ImageFilter.GaussianBlur(0.4))


def endcard_layers():
    """three layers fading in at different times: logo, line, small print."""
    layers = []
    L1 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L1)
    cx = 640
    d.text((cx, 400), "Larkin's", font=font('Yesteryear-Regular.ttf', 210), fill=(*CREAM, 255), anchor='mm')
    L2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L2)
    f = font('PlayfairDisplaywght.ttf', 80, 900)
    text = 'STILL  FIZZING.'
    sp = 10
    ws = [d.textlength(c, font=f) for c in text]
    x = cx - (sum(ws) + sp * (len(text) - 1)) / 2
    for c, w in zip(text, ws):
        d.text((x, 575), c, font=f, fill=(250, 142, 72, 255), anchor='lm')
        x += w + sp
    L3 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L3)
    d.text((cx, 690), 'Same recipe since 1958.', font=font('PlayfairDisplay-Italicwght.ttf', 58, 500), fill=(*CREAM, 235), anchor='mm')
    return [L1, L2, L3]


class Motes:
    """soft dust motes drifting through a sunbeam; some in focus, most as bokeh."""
    def __init__(self, n, seed, color=(1.0, 0.85, 0.6), region=(0.0, 1.0, 0.0, 1.0), level=0.10):
        r = np.random.default_rng(seed)
        x0, x1, y0, y1 = region
        self.p = np.stack([r.uniform(x0, x1, n) * W, r.uniform(y0, y1, n) * H], 1)
        self.v = np.stack([r.normal(6, 5, n), r.normal(-4, 4, n)], 1)
        self.size = r.choice([2.0, 3.0, 5.0, 9.0, 16.0], n, p=[0.3, 0.3, 0.2, 0.12, 0.08])
        self.ph = r.uniform(0, 6.28, n)
        self.col = np.array(color, np.float32)
        self.level = level
        self.sprites = {}

    def sprite(self, s):
        if s not in self.sprites:
            k = int(s * 3) | 1
            y, x = np.mgrid[-k:k + 1, -k:k + 1]
            g = np.exp(-(x * x + y * y) / (2 * s * s)) if s < 6 else np.clip(1.2 - np.sqrt(x * x + y * y) / s, 0, 1) ** 0.7 * 0.5
            self.sprites[s] = g.astype(np.float32)
        return self.sprites[s]

    def draw(self, frame, t):
        for (px, py), (vx, vy), s, ph in zip(self.p, self.v, self.size, self.ph):
            x = int(px + vx * t + 8 * np.sin(t * 0.7 + ph))
            y = int(py + vy * t + 6 * np.sin(t * 0.5 + ph * 2))
            sp = self.sprite(s)
            k = sp.shape[0] // 2
            if k < x < W - k - 1 and k < y < H - k - 1:
                a = self.level * (0.5 + 0.5 * np.sin(t * 1.3 + ph)) * (1.0 if s < 6 else 0.6)
                frame[y - k:y + k + 1, x - k:x + k + 1] += sp[..., None] * self.col * a
        return frame


def dapple(frame, t, strength=0.09):
    """moving leaf shadows over the bright, sunlit parts of the frame."""
    h, w = 34, 60
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n = (np.sin(xx * 0.55 + t * 0.9) * np.sin(yy * 0.7 - t * 0.6) + np.sin(xx * 0.23 - yy * 0.31 + t * 0.4) + 0.6 * np.sin(xx * 0.9 + yy * 0.5 + t * 1.3))
    n = (n - n.min()) / (n.max() - n.min() + 1e-6)
    m = cv2.resize(n.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)[..., None]
    lum = frame.mean(2, keepdims=True)
    mask = np.clip((lum - 0.45) / 0.35, 0, 1)
    return frame * (1 - strength * mask * (1 - m) * 2)


def ease(u):
    u = min(max(u, 0), 1)
    return u * u * (3 - 2 * u)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(ROOT, 'out', 'film_video.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    nframes = int(round(TL.END * FPS))
    vig = vignette()
    rng = np.random.default_rng(5)
    grains = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
    grains = [np.asarray(Image.fromarray(g).resize((W, H), Image.BILINEAR))[..., None] for g in grains]
    cache = {}
    npcache = {}
    ovcache = {}
    supers = {}
    pop_frames = sorted(glob.glob(os.path.join(REN, 'pop', '*.png')))
    ec = endcard_layers()
    missing = set()
    motes = {'1958-main': Motes(70, 1, region=(0.0, 1.0, 0.0, 0.8)), '2026-main': Motes(80, 2, (1.0, 0.8, 0.55)), '2026-detail': Motes(50, 3, (1.0, 0.8, 0.55)), 'hero-main': Motes(40, 4, (1.0, 0.7, 0.45), level=0.06), 'hero-macro': Motes(30, 5, (1.0, 0.7, 0.45), level=0.06)}
    cuts = [e[0] for e in EDL]
    ff = None if os.environ.get('FRAMES') else subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', os.environ.get('PRESET', 'medium'), '-crf', os.environ.get('CRF', '19'), '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    def get_img(src, t, t0):
        if src == 'pop' and pop_frames:
            k = min(max(int((t - t0) * FPS), 0), len(pop_frames) - 1)
            key = 'pop%d' % k
            if key not in cache:
                cache[key] = grade(Image.open(pop_frames[k]).convert('RGB'), 'hero')
            return cache[key]
        s2 = 'hero-main' if src == 'pop' else src
        if s2 not in cache:
            im, final = load(s2)
            if im is None:
                missing.add(s2)
                im = Image.new('RGB', (W, H), (30, 20, 15))
            elif not final:
                missing.add(s2 + '(preview)')
            cache[s2] = grade(im, ALIAS.get(s2, s2))
        return cache[s2]

    def shot_frame(shot, t):
        t0, t1, src, z0, z1, p0, p1, sup = shot
        u = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
        if src == 'pop' and pop_frames:
            # stretch the rendered frames over the shot with linear frame blending
            fpos = min(max((t - t0) / (t1 - t0), 0), 1) * (len(pop_frames) - 1)
            k0 = int(fpos); k1 = min(k0 + 1, len(pop_frames) - 1); w = fpos - k0
            i0 = get_img(src, t0 + k0 / FPS + 1e-4, t0); i1 = get_img(src, t0 + k1 / FPS + 1e-4, t0)
            for ii in (i0, i1):
                if id(ii) not in npcache:
                    npcache[id(ii)] = np.asarray(ii).astype(np.float32) / 255
            arr = npcache[id(i0)] * (1 - w) + npcache[id(i1)] * w
            fit = max(arr.shape[1] / W, arr.shape[0] / H)
            return cv2.resize(arr, (W, H), interpolation=cv2.INTER_CUBIC)
        img = get_img(src, t, t0)
        ue = 0.5 - 0.5 * math.cos(math.pi * u) if src in ('hero-pack', 'hero-pack2') else u
        z = z0 + (z1 - z0) * ue
        px = p0[0] + (p1[0] - p0[0]) * ue
        py = p0[1] + (p1[1] - p0[1]) * ue
        fit = max(img.width / W, img.height / H)
        sc = fit / z
        cx = img.width / 2 + px * img.width
        cy = img.height / 2 + py * img.height
        key = id(img)
        if key not in npcache:
            npcache[key] = np.asarray(img).astype(np.float32) / 255
        M = np.array([[sc, 0, cx - sc * W / 2], [0, sc, cy - sc * H / 2]], np.float32)
        frame = cv2.warpAffine(npcache[key], M, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        if src.startswith('1958'):
            frame = dapple(frame, t)
        if src in motes:
            frame = motes[src].draw(frame, t - t0)
        return frame

    # fizz transitions on the era cuts (index of incoming shot in EDL)
    trans_in = {i for i, e in enumerate(EDL) if e[7] == 'Today'}
    hard_in = {i for i, e in enumerate(EDL) if e[7] in ('1966', '1974', '1987')}
    fizz = Fizz()
    only = [int(float(x) * FPS) for x in os.environ.get('FRAMES', '').split(',') if x]
    for fi in range(nframes):
        if only and fi not in only:
            continue
        t = (fi + 0.5) / FPS
        idx = None
        for i, e in enumerate(EDL):
            if e[0] <= t < e[1]:
                idx = i
                break
        if idx is None:
            frame = np.zeros((H, W, 3), np.float32)
        else:
            shot = EDL[idx]
            t0, t1, src, z0, z1, p0, p1, sup = shot
            frame = shot_frame(shot, t)
            # fizz transition: starts 0.10 s before the cut, finishes 0.40 s after
            nxt = idx + 1
            if nxt in trans_in and t > EDL[nxt][0] - Fizz.PRE:
                frame = fizz.blend(frame, shot_frame(EDL[nxt], t), t - EDL[nxt][0], seed=nxt)
            elif idx in trans_in and t < t0 + Fizz.POST:
                frame = fizz.blend(shot_frame(EDL[idx - 1], t), frame, t - t0, seed=idx)
            frame = frame * vig
            dt = t - t0
            if idx in hard_in and dt < 0.2:
                frame = frame * (1 + 0.12 * (1 - dt / 0.2) ** 2)
            if fi / FPS < TL.T0 + 0.25:
                frame *= ease((t - TL.T0) / 0.25)
            if t > TL.END - 0.9:
                frame *= ease((TL.END - t) / 0.9)
            ov = None
            if sup and sup != 'ENDCARD':
                if sup not in supers:
                    supers[sup] = year_super(sup)
                a_ = ease((dt - 0.25) / 0.4) * ease((t1 - t - 0.15) / 0.35)
                if a_ > 0:
                    ov = [(supers[sup], a_)]
            elif sup == 'ENDCARD':
                tv = [TL.bar(17, 0.3), TL.bar(17, 2.0), TL.bar(17, 3.2)]
                ov = []
                for L, ts in zip(ec, tv):
                    a_ = ease((t - ts) / 0.8)
                    if a_ > 0:
                        ov.append((L, a_))
            if ov:
                for L, a_ in ov:
                    if id(L) not in ovcache:
                        la = np.asarray(L).astype(np.float32) / 255
                        ys, xs = np.where(la[..., 3] > 0)
                        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
                        ovcache[id(L)] = (y0, y1, x0, x1, la[y0:y1, x0:x1, :3].copy(), la[y0:y1, x0:x1, 3:4].copy())
                    y0, y1, x0, x1, rgb, al = ovcache[id(L)]
                    al = al * a_
                    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + rgb * al
        g = grains[fi % 8]
        frame = frame + g * 0.011 * (0.6 + 0.4 * (1 - frame.mean(2, keepdims=True)))
        if fi % 120 == 0:
            print('frame', fi, '/', nframes, flush=True)
        if only:
            Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8)).save(os.path.join(ROOT, '..', '_tmp', 'review', 'f_%06.2f.jpg' % t), quality=88)
            continue
        ff.stdin.write((np.clip(frame, 0, 1) * 255).astype(np.uint8).tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    print('video written', out, 'missing/preview:', sorted(missing))


if __name__ == '__main__':
    main()
