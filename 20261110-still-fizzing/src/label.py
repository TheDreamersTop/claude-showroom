"""Applied-colour label (ACL) for the Larkin's bottle. RGBA, wraps the full circumference.
Front of the bottle is u=0.5. Output: assets/tex/label.png"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
A = os.path.join(os.path.dirname(__file__), '..', 'assets')
F = lambda n, s: ImageFont.truetype(os.path.join(A, 'fonts', n), s)
W, H = 3072, 1000
CREAM = (246, 236, 214, 255)
ORANGE = (236, 112, 52, 255)

def star(d, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)

def ctext(d, x, y, s, font, fill, spacing=0):
    if spacing:
        widths = [d.textlength(c, font=font) for c in s]
        tot = sum(widths) + spacing * (len(s) - 1)
        cx = x - tot / 2
        for c, w in zip(s, widths):
            d.text((cx, y), c, font=font, fill=fill, anchor='lm')
            cx += w + spacing
    else:
        d.text((x, y), s, font=font, fill=fill, anchor='mm')

def make(path):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # thin orange bands top and bottom, full wrap
    d.rectangle([0, 40, W, 62], fill=ORANGE)
    d.rectangle([0, H - 62, W, H - 40], fill=ORANGE)
    d.rectangle([0, 80, W, 88], fill=CREAM)
    d.rectangle([0, H - 88, W, H - 80], fill=CREAM)
    cx = W * 0.5
    # front panel
    ctext(d, cx, 395, "Larkin's", F('Yesteryear-Regular.ttf', 360), CREAM)
    pf = ImageFont.truetype(os.path.join(A, 'fonts', 'PlayfairDisplaywght.ttf'), 120)
    try: pf.set_variation_by_axes([800])
    except Exception: pass
    ctext(d, cx, 650, "COLA", pf, ORANGE, spacing=48)
    small = ImageFont.truetype(os.path.join(A, 'fonts', 'PlayfairDisplaywght.ttf'), 54)
    try: small.set_variation_by_axes([600])
    except Exception: pass
    ctext(d, cx, 800, "SINCE  1958", small, CREAM, spacing=14)
    for dx in (-330, 330):
        star(d, cx + dx, 650, 34, CREAM)
    # back panel (u = 0 / 1 seam): small print, centred on seam by drawing twice
    for bx in (0, W):
        ctext(d, bx, 420, "RETURN FOR DEPOSIT", small, CREAM, spacing=10)
        ctext(d, bx, 520, "6½ FL. OZ.", small, CREAM, spacing=10)
        star(d, bx, 640, 40, ORANGE)
    # slight paint softness
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(path)

if __name__ == '__main__':
    os.makedirs(os.path.join(A, 'tex'), exist_ok=True)
    make(os.path.join(A, 'tex', 'label.png'))
    print('ok')
