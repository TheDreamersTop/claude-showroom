"""Procedural prop textures (PIL). Run once: writes assets/tex/*.png"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os, math, random
import numpy as np

A = os.path.join(os.path.dirname(__file__), '..', 'assets')
T = os.path.join(A, 'tex')
os.makedirs(T, exist_ok=True)


def font(n, s, w=None):
    f = ImageFont.truetype(os.path.join(A, 'fonts', n), s)
    if w:
        try:
            f.set_variation_by_axes([w] if 'Inter' not in n else [14, w])
        except Exception:
            pass
    return f


def aged(im, amount=0.10, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(im.convert('RGB')).astype(np.float32) / 255
    h, w = a.shape[:2]
    n = rng.normal(0, 1, (h // 8 + 1, w // 8 + 1)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
    a = a * (1 - amount * n[..., None]) + amount * 0.5 * np.array([0.9, 0.8, 0.6]) * n[..., None]
    a += rng.normal(0, 0.012, a.shape)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def comic():
    W, H = 1024, 1536
    im = Image.new('RGB', (W, H), (250, 214, 60))
    d = ImageDraw.Draw(im)
    # starburst sky
    cx, cy = W * 0.55, H * 0.58
    for i in range(36):
        a0, a1 = i * math.tau / 36, (i + 0.5) * math.tau / 36
        d.polygon([(cx, cy), (cx + 2000 * math.cos(a0), cy + 2000 * math.sin(a0)), (cx + 2000 * math.cos(a1), cy + 2000 * math.sin(a1))], fill=(245, 160, 40))
    # planet + rocket
    d.ellipse([W * 0.08, H * 0.62, W * 0.62, H * 1.08], fill=(70, 120, 190), outline=(20, 20, 40), width=10)
    d.ellipse([W * 0.15, H * 0.70, W * 0.30, H * 0.78], fill=(50, 95, 160))
    rx, ry = W * 0.62, H * 0.50
    d.polygon([(rx, ry - 330), (rx + 90, ry - 130), (rx + 90, ry + 170), (rx - 90, ry + 170), (rx - 90, ry - 130)], fill=(220, 40, 40), outline=(20, 20, 30), width=10)
    d.ellipse([rx - 50, ry - 120, rx + 50, ry - 20], fill=(150, 220, 255), outline=(20, 20, 30), width=9)
    d.polygon([(rx - 90, ry + 60), (rx - 190, ry + 230), (rx - 90, ry + 170)], fill=(40, 40, 60))
    d.polygon([(rx + 90, ry + 60), (rx + 190, ry + 230), (rx + 90, ry + 170)], fill=(40, 40, 60))
    d.polygon([(rx - 60, ry + 175), (rx, ry + 420), (rx + 60, ry + 175)], fill=(255, 240, 120))
    # masthead
    d.rectangle([0, 0, W, 300], fill=(200, 30, 40))
    d.text((W / 2, 140), 'ROCKET', font=font('Lobster-Regular.ttf', 210), fill=(255, 245, 200), anchor='mm', stroke_width=8, stroke_fill=(30, 20, 40))
    d.text((W / 2, 300), 'RANGER', font=font('Lobster-Regular.ttf', 150), fill=(255, 230, 60), anchor='mm', stroke_width=8, stroke_fill=(30, 20, 40))
    d.rectangle([40, 30, 190, 150], fill=(255, 255, 255), outline=(0, 0, 0), width=5)
    d.text((115, 70), '10¢', font=font('Inter.ttf', 56, 800), fill=(0, 0, 0), anchor='mm')
    d.text((115, 122), 'No. 12', font=font('Inter.ttf', 30, 700), fill=(0, 0, 0), anchor='mm')
    d.rectangle([60, H - 210, W - 60, H - 90], fill=(255, 255, 240), outline=(0, 0, 0), width=6)
    d.text((W / 2, H - 150), 'TO THE MOON BY SUPPERTIME!', font=font('Inter.ttf', 54, 900), fill=(20, 20, 30), anchor='mm')
    aged(im, 0.18, 1).save(os.path.join(T, 'comic.png'))


def ticket(path, color, line1, line2, num):
    W, H = 900, 400
    im = Image.new('RGB', (W, H), color)
    d = ImageDraw.Draw(im)
    d.rectangle([18, 18, W - 18, H - 18], outline=(60, 30, 20), width=5)
    d.rectangle([34, 34, W - 34, H - 34], outline=(60, 30, 20), width=2)
    d.text((W / 2, 110), line1, font=font('PlayfairDisplaywght.ttf', 64, 800), fill=(50, 25, 15), anchor='mm')
    d.text((W / 2, 205), 'ADMIT ONE', font=font('Inter.ttf', 78, 900), fill=(50, 25, 15), anchor='mm')
    d.text((W / 2, 290), line2, font=font('Inter.ttf', 34, 600), fill=(50, 25, 15), anchor='mm')
    d.text((W - 70, H / 2), num, font=font('Inter.ttf', 30, 600), fill=(50, 25, 15), anchor='mm')
    d.text((70, H / 2), num, font=font('Inter.ttf', 30, 600), fill=(50, 25, 15), anchor='mm')
    aged(im, 0.16, 2).save(path)


def formica():
    """60s boomerang laminate, aqua."""
    W = 2048
    rng = random.Random(3)
    im = Image.new('RGB', (W, W), (128, 196, 190))
    d = ImageDraw.Draw(im)
    for _ in range(2600):  # speckle
        x, y = rng.uniform(0, W), rng.uniform(0, W)
        r = rng.uniform(1, 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rng.choice([(90, 150, 148), (230, 240, 230), (60, 110, 110)]))
    for _ in range(140):
        x, y = rng.uniform(0, W), rng.uniform(0, W)
        a = rng.uniform(0, math.tau)
        s = rng.uniform(40, 80)
        col = rng.choice([(240, 236, 215), (225, 120, 70), (40, 80, 90), (250, 205, 90)])
        pts = []
        for k in range(16):
            t = k / 15
            ang = a + (t - 0.5) * 2.2
            rr = s * (1.0 + 0.0 * t)
            pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
        d.line(pts, fill=col, width=int(s * 0.16), joint='curve')
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    im.save(os.path.join(T, 'formica.png'))


def gingham():
    W = 1024
    a = np.zeros((W, W, 3), np.float32)
    n = 16
    x = (np.arange(W) // (W // n)) % 2
    X, Y = np.meshgrid(x, x)
    base = np.array([0.97, 0.95, 0.88])
    col = np.array([0.92, 0.70, 0.18])
    k = 0.45 * X + 0.45 * Y
    a = base * (1 - k[..., None]) + col * k[..., None]
    # weave noise
    rng = np.random.default_rng(4)
    a *= 1 - 0.05 * rng.random((W, W, 1))
    Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)).save(os.path.join(T, 'gingham.png'))


def doily():
    W = 1536
    im = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = W / 2
    ivory = (245, 240, 226, 255)
    R = W / 2 - 10
    # scalloped outer edge
    pts = []
    for i in range(720):
        a = i / 720 * math.tau
        r = R * (0.94 + 0.06 * abs(math.cos(a * 18)))
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=ivory)
    # holes in rings
    for ring, (rr, n, hs) in enumerate([(0.82, 54, 0.035), (0.68, 44, 0.04), (0.53, 34, 0.04), (0.38, 24, 0.045), (0.22, 12, 0.05)]):
        for i in range(n):
            a = (i + 0.5 * (ring % 2)) / n * math.tau
            x, y = c + R * rr * math.cos(a), c + R * rr * math.sin(a)
            h = R * hs
            d.ellipse([x - h, y - h * 0.7, x + h, y + h * 0.7], fill=(0, 0, 0, 0))
    for rr in (0.75, 0.60, 0.45, 0.30):
        d.ellipse([c - R * rr, c - R * rr, c + R * rr, c + R * rr], outline=(0, 0, 0, 0), width=6)
    d.ellipse([c - R * 0.12, c - R * 0.12, c + R * 0.12, c + R * 0.12], fill=ivory)
    im.save(os.path.join(T, 'doily.png'))


def pills():
    """lid strip for a 7-day organiser: 7 tiles in a row."""
    W, H = 2100, 300
    im = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(im)
    cols = [(236, 150, 160), (250, 200, 120), (250, 236, 140), (160, 220, 170), (140, 200, 230), (170, 160, 225), (225, 170, 220)]
    for i, ch in enumerate('SMTWTFS'):
        x0 = i * 300
        d.rectangle([x0, 0, x0 + 300, H], fill=cols[i])
        d.text((x0 + 150, 150), ch, font=font('Inter.ttf', 170, 800), fill=(255, 255, 255), anchor='mm')
    im.save(os.path.join(T, 'pills.png'))


def crossword():
    W, H = 1600, 1200
    im = Image.new('RGB', (W, H), (236, 230, 214))
    d = ImageDraw.Draw(im)
    rng = random.Random(7)
    # columns of fake text
    tf = font('PlayfairDisplaywght.ttf', 22, 500)
    words = 'the and town of council mayor rain weekend market garden new old river bridge school library choir fair bake sale bus route harbor'.split()
    for col in range(2):
        x = 40 + col * 330
        for row in range(44):
            y = 140 + row * 24
            line = ' '.join(rng.choice(words) for _ in range(6))
            d.text((x, y), line[:34], font=tf, fill=(70, 66, 60))
    d.text((40, 60), 'THE MORNING HERALD', font=font('PlayfairDisplaywght.ttf', 48, 900), fill=(30, 28, 25))
    # crossword grid
    gx, gy, cs, n = 760, 160, 56, 13
    rng2 = random.Random(11)
    blocks = set()
    for _ in range(34):
        i, j = rng2.randrange(n), rng2.randrange(n)
        blocks.add((i, j)); blocks.add((n - 1 - i, n - 1 - j))
    hand = font('Yesteryear-Regular.ttf', 44)
    letters = 'STILLFIZZINGLOVEFIFTYEIGHTYEARSTWOSTRAWS'
    k = 0
    for i in range(n):
        for j in range(n):
            x, y = gx + j * cs, gy + i * cs
            if (i, j) in blocks:
                d.rectangle([x, y, x + cs, y + cs], fill=(25, 25, 25))
            else:
                d.rectangle([x, y, x + cs, y + cs], outline=(25, 25, 25), width=2)
                if i < 7 and rng2.random() < 0.7:
                    d.text((x + cs / 2, y + cs / 2 + 4), letters[k % len(letters)], font=hand, fill=(40, 50, 110), anchor='mm')
                    k += 1
    d.text((gx, gy - 60), 'CROSSWORD  No. 4,112', font=font('Inter.ttf', 34, 800), fill=(30, 28, 25))
    aged(im, 0.10, 5).save(os.path.join(T, 'crossword.png'))


def card_just_married():
    W, H = 1000, 640
    im = Image.new('RGB', (W, H), (250, 246, 236))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, W - 24, H - 24], outline=(196, 160, 90), width=6)
    d.text((W / 2, 250), 'Just Married', font=font('Yesteryear-Regular.ttf', 150), fill=(150, 110, 50), anchor='mm')
    d.text((W / 2, 420), 'JUNE  8,  1974', font=font('PlayfairDisplaywght.ttf', 52, 600), fill=(120, 90, 50), anchor='mm')
    d.text((W / 2, 500), 'R  &  E', font=font('PlayfairDisplaywght.ttf', 52, 600), fill=(120, 90, 50), anchor='mm')
    aged(im, 0.06, 6).save(os.path.join(T, 'justmarried.png'))


def planks():
    """weathered white-painted porch planks"""
    W, H = 2048, 2048
    rng = np.random.default_rng(8)
    y = np.arange(H)[:, None]
    x = np.arange(W)[None, :]
    plank = (y // 256)
    grain = np.sin((x * 0.012 + np.sin(y * 0.05 + plank * 3) * 2.5 + plank * 7)) * 0.5 + 0.5
    noise = rng.random((H // 12, W // 160)).astype(np.float32)
    noise = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    fine = rng.random((H // 6, W // 40)).astype(np.float32)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    paint = (noise * 0.7 + fine * 0.3 > 0.30).astype(np.float32)
    paint = np.asarray(Image.fromarray((paint * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))) / 255.0
    wood = np.stack([0.55 + 0.15 * grain, 0.40 + 0.12 * grain, 0.27 + 0.08 * grain], -1)
    white = np.array([0.88, 0.90, 0.88]) * (0.96 + 0.04 * grain[..., None])
    a = wood * (1 - paint[..., None]) + white * paint[..., None]
    gap = ((y % 256) < 6).astype(np.float32)
    a = a * (1 - 0.8 * gap[..., None])
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(T, 'planks.png'))


def walnut():
    W, H = 2048, 1024
    rng = np.random.default_rng(9)
    y = np.arange(H)[:, None].astype(np.float32)
    x = np.arange(W)[None, :].astype(np.float32)
    n = rng.random((H // 32, W // 32)).astype(np.float32)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255.0
    g = np.sin(y * 0.09 + n * 9 + np.sin(x * 0.004) * 3) * 0.5 + 0.5
    g = g ** 3
    base = np.array([0.20, 0.105, 0.055])
    dark = np.array([0.09, 0.045, 0.025])
    a = base * (1 - g[..., None]) + dark * g[..., None]
    a *= 0.92 + 0.16 * n[..., None]
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(T, 'walnut.png'))


def linen():
    W = 1024
    rng = np.random.default_rng(10)
    a = np.ones((W, W), np.float32)
    a -= 0.05 * np.abs(np.sin(np.arange(W) * 1.3))[None, :]
    a -= 0.05 * np.abs(np.sin(np.arange(W) * 1.3))[:, None]
    a -= 0.04 * rng.random((W, W))
    c = np.stack([a * 0.96, a * 0.95, a * 0.92], -1)
    Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(T, 'linen.png'))


def polaroid():
    W, H = 880, 1060
    im = Image.new('RGB', (W, H), (246, 244, 236))
    d = ImageDraw.Draw(im)
    # blurry warm photo: a window, a crib silhouette suggestion; intentionally soft
    ph = Image.new('RGB', (800, 800), (180, 140, 100))
    pd = ImageDraw.Draw(ph)
    pd.rectangle([0, 0, 800, 800], fill=(200, 160, 120))
    pd.ellipse([150, 200, 650, 700], fill=(240, 205, 170))
    pd.ellipse([260, 300, 540, 580], fill=(250, 220, 190))
    pd.rectangle([0, 620, 800, 800], fill=(120, 150, 190))
    ph = ph.filter(ImageFilter.GaussianBlur(28))
    im.paste(ph, (40, 40))
    d.text((W / 2, 960), 'Lucy, 3 days', font=font('Yesteryear-Regular.ttf', 74), fill=(40, 40, 90), anchor='mm')
    aged(im, 0.08, 12).save(os.path.join(T, 'polaroid.png'))


def footprints():
    W, H = 880, 1060
    im = Image.new('RGB', (W, H), (248, 245, 238))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, W - 24, H - 24], outline=(210, 170, 185), width=5)
    ink = (60, 70, 120)
    def foot(cx, cy, flip):
        s_ = 1 if not flip else -1
        d.ellipse([cx - 70, cy - 40, cx + 70, cy + 190], fill=ink)                       # sole
        d.ellipse([cx - 62, cy + 150, cx + 58, cy + 290], fill=ink)                       # heel
        d.polygon([(cx - 70, cy + 80), (cx + 70, cy + 80), (cx + 55, cy + 200), (cx - 50, cy + 200)], fill=ink)
        for k, (dx, dy, r) in enumerate([(-55, -70, 30), (-12, -92, 22), (22, -90, 19), (50, -78, 16), (72, -55, 13)]):
            x = cx + s_ * dx
            d.ellipse([x - r, cy + dy - r, x + r, cy + dy + r], fill=ink)
    foot(W / 2 - 150, 330, True)
    foot(W / 2 + 150, 330, False)
    im = im.filter(ImageFilter.GaussianBlur(1.5))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 800), 'Lucy', font=font('Yesteryear-Regular.ttf', 120), fill=(60, 60, 110), anchor='mm')
    d.text((W / 2, 920), 'MARCH 3, 1987  ·  7 LB 2 OZ', font=font('PlayfairDisplaywght.ttf', 38, 600), fill=(110, 100, 120), anchor='mm')
    aged(im, 0.05, 13).save(os.path.join(T, 'footprints.png'))


if __name__ == '__main__':
    footprints(); comic(); formica(); gingham(); doily(); pills(); crossword(); card_just_married(); planks(); walnut(); linen(); polaroid()
    ticket(os.path.join(T, 'ticket1.png'), (232, 150, 120), 'THE RIALTO', 'SAT  JUN 18 1966  ·  7:30', '0421')
    ticket(os.path.join(T, 'ticket2.png'), (232, 150, 120), 'THE RIALTO', 'SAT  JUN 18 1966  ·  7:30', '0422')
    print('textures ok')
