from PIL import Image, ImageDraw, ImageFont
import os
D = os.path.join(os.path.dirname(__file__), '..', 'tex'); os.makedirs(D, exist_ok=True)
F = 'C:/Windows/Fonts/'
def tracked(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill); x += draw.textlength(ch, font=font) + track
def width(draw, text, font, track): return sum(draw.textlength(c, font=font) for c in text) + track*(len(text)-1)
# side wordmark: 3.2m x 0.8m -> 2048x512
im = Image.new('RGBA', (2048, 512), (0,0,0,0)); d = ImageDraw.Draw(im)
f = ImageFont.truetype(F+'BOD_R.TTF', 230)
w = width(d, 'VESPER', f, 60); tracked(d, ((2048-w)/2, 120), 'VESPER', f, (255,255,255,255), 60)
im.save(os.path.join(D, 'side.png'))
# fin: 4.4m x 3.6m -> 2048x1676 ; '61' gold, plus a small four-point star
im = Image.new('RGBA', (2048, 1676), (0,0,0,0)); d = ImageDraw.Draw(im)
f = ImageFont.truetype(F+'BOD_R.TTF', 640)
gold = (205, 160, 92, 255)
w = d.textlength('61', font=f); d.text((1024 - w/2 - 60, 380), '61', font=f, fill=gold)
cx, cy, r = 1024+330, 560, 110
d.polygon([(cx, cy-r), (cx+r*0.18, cy-r*0.18), (cx+r, cy), (cx+r*0.18, cy+r*0.18), (cx, cy+r), (cx-r*0.18, cy+r*0.18), (cx-r, cy), (cx-r*0.18, cy-r*0.18)], fill=gold)
im.save(os.path.join(D, 'fin.png'))
print('ok')
