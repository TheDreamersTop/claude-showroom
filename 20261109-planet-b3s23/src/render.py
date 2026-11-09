"""Render scenes to video segments in parallel.  usage: python render.py [scene ...] [--preview N] [--stills]"""
import os, sys, subprocess, time
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"
import numpy as np, cv2
cv2.setNumThreads(1)
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont

import look
from scenes import build, timeline, FPS, ROOT, ease, FILM
from script import ORDER

OW, OH = 1920, 1080
SEG = os.path.join(ROOT, "out", "seg")
os.makedirs(SEG, exist_ok=True)
FONT_L = "C:/Windows/Fonts/segoeuil.ttf"
FONT_SL = "C:/Windows/Fonts/segoeuisl.ttf"
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def cell_px(cam, x, y):
    c, s = np.cos(cam["rot"]), np.sin(cam["rot"])
    dx, dy = x - cam["cx"], y - cam["cy"]
    return look.W / 2 + cam["z"] * (c * dx - s * dy), look.H / 2 + cam["z"] * (s * dx + c * dy)


def spaced(draw, xy, text, fnt, fill, tracking, anchor_center=True):
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking


def fade_alpha(t, t0, t1, fi=1.2, fo=1.0):
    return ease((t - t0) / fi) * ease((t1 - t) / fo)


def draw_text(img, items, t):
    texts = [o for o in items if o[0] in ("title", "counter", "caption")]
    if not texts:
        return img
    pil = Image.fromarray(img[..., ::-1])
    layer = Image.new("RGBA", pil.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for o in texts:
        if o[0] == "title":
            _, txt, t0, t1 = o
            a = fade_alpha(t, t0, t1, 2.0, 1.4)
            if a > 0:
                spaced(d, (OW / 2, OH / 2 - 66), txt, font(FONT_L, 96), (244, 240, 230, int(255 * a)), 20)
        elif o[0] == "counter":
            _, label, val, t0, t1 = o
            a = fade_alpha(t, t0, t1, 0.6, 0.6)
            if a > 0:
                spaced(d, (96, OH - 168), label, font(FONT_SL, 26), (210, 222, 218, int(220 * a)), 7, False)
                d.text((92, OH - 136), f"{val:,}", font=font(FONT_L, 76), fill=(240, 236, 226, int(245 * a)))
        elif o[0] == "caption":
            _, txt, t0, t1, y, size = o
            a = fade_alpha(t, t0, t1, 1.0, 1.0)
            if a > 0:
                spaced(d, (OW / 2, y), txt, font(FONT_L, size), (242, 240, 232, int(255 * a)), 4)
    pil = Image.alpha_composite(pil.convert("RGBA"), layer).convert("RGB")
    return np.asarray(pil)[..., ::-1].copy()


def ring_overlay(items, cam, t):
    rs = [o for o in items if o[0] == "ring"]
    sp = [o for o in items if o[0] == "spark"]
    if not rs and not sp:
        return None
    ov = np.zeros((look.H, look.W, 3), np.float32)
    for _, x, y, t0, t1 in sp:
        a = float(np.clip((12 - cam["z"]) / 8, 0, 1))  # only once the glider is too small to see
        if a > 0:
            px, py = cell_px(cam, x, y)
            tmp = np.zeros_like(ov)
            cv2.circle(tmp, (int(px), int(py)), 3, (0.9 * a, 1.0 * a, 0.95 * a), -1, cv2.LINE_AA)
            ov += tmp * 0.8 + cv2.GaussianBlur(tmp, (0, 0), 3) * 6 + cv2.GaussianBlur(tmp, (0, 0), 12) * 14
    for _, x, y, t0, t1, r, col in rs:
        a = fade_alpha(t, t0, t1, 0.35, 0.35)
        if a <= 0:
            continue
        px, py = cell_px(cam, x + 0.5, y + 0.5)
        rad = cam["z"] * (0.62 + 0.05 * np.sin(t * 6.0)) * r
        tmp = np.zeros_like(ov)
        cv2.circle(tmp, (int(px * 4), int(py * 4)), int(rad * 4), (col[0] * a * 0.55, col[1] * a * 0.55, col[2] * a * 0.55), 6, cv2.LINE_AA, 2)
        ov += cv2.GaussianBlur(tmp, (0, 0), 1.2)
    return ov


def render_frames(scene, f0, f1, sink):
    dust = look.Dust() if scene.dust else None
    for f in range(f0, f1):
        t = f / FPS
        cam = scene.cam(t)
        if scene.black:
            items = scene.overlays(t, cam, [])
            img = np.zeros((OH, OW, 3), np.uint8)
        else:
            alive, age, gens, _ = scene.frame_state(t)
            items = scene.overlays(t, cam, gens)
            img = look.render(alive, age, cam, t, focus=scene.focus(t), dust=dust, overlay=ring_overlay(items, cam, t), exposure=scene.dim(t))
            img = cv2.resize(img, (OW, OH), interpolation=cv2.INTER_CUBIC)
        img = draw_text(img, items, t)
        e = scene.exposure(t)
        if e < 0.999:
            img = cv2.convertScaleAbs(img, alpha=e)
        sink(f, img)


def job(args):
    name, f0, f1, path = args
    scene = build(name)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    render_frames(scene, f0, f1, lambda f, img: p.stdin.write(img.tobytes()))
    p.stdin.close(); p.wait()
    return path


def jobs_for(names, chunk=90):
    _, durs, _ = timeline()
    out = []
    for n in names:
        nf = int(round(durs[n] * FPS))
        for i, f0 in enumerate(range(0, nf, chunk)):
            out.append((n, f0, min(nf, f0 + chunk), os.path.join(SEG, f"{n}_{i:03d}.mp4")))
    return out


def stills(names, per=6):
    os.makedirs(os.path.join(ROOT, "out", "stills"), exist_ok=True)
    _, durs, _ = timeline()
    for n in names:
        sc = build(n)
        nf = int(round(durs[n] * FPS))
        picks = set(int(x) for x in np.linspace(0, nf - 1, per))
        def sink(f, img):
            cv2.imwrite(os.path.join(ROOT, "out", "stills", f"{n}_{f:05d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        for f in sorted(picks):
            render_frames(sc, f, f + 1, sink)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or FILM
    if "--stills" in sys.argv:
        stills(names)
        sys.exit()
    js = jobs_for(names)
    t0 = time.time()
    with Pool(11) as pool:
        for i, p in enumerate(pool.imap_unordered(job, js)):
            print(f"[{i + 1}/{len(js)}] {os.path.basename(p)}  {time.time() - t0:.0f}s", flush=True)
    for n in names:
        segs = sorted(x[3] for x in js if x[0] == n)
        lst = os.path.join(SEG, f"{n}.txt")
        open(lst, "w").write("".join(f"file '{s.replace(os.sep, '/')}'\n" for s in segs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        os.path.join(ROOT, "out", f"scene_{n}.mp4")], check=True)
    print("done", time.time() - t0)
