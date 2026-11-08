"""Assemble the final film: intro card + scope film + end card.
python assemble.py NAME [size] -> renders/NAME_final_SIZE.mp4
Expects renders/NAME.wav (+ .json from score.py). The scope picture is rendered from that wav."""
import sys, os, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

name = sys.argv[1]
S = int(sys.argv[2]) if len(sys.argv) > 2 else 1080
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
meta = json.load(open('renders/%s.wav.json' % name))
dur = meta['dur']
g = meta['gain']
scale = 0.44 / g if g < 1 else 0.44
FPS = 30
INTRO = 3.0
OUTRO = 5.5
FONT_L = '/usr/share/fonts/truetype/ubuntu/Ubuntu-L.ttf'
FONT_M = '/usr/share/fonts/truetype/ubuntu/Ubuntu-M.ttf'
for f in (FONT_L, FONT_M):
    if not os.path.exists(f):
        r = subprocess.run(['fc-match', '-f', '%{file}', 'Ubuntu:light' if f == FONT_L else 'Ubuntu:medium'], capture_output=True, text=True)
        if f == FONT_L: FONT_L = r.stdout
        else: FONT_M = r.stdout

BG = (2, 4, 3)
INK = np.array([170, 235, 200], float)


def card(lines, t, fade_in, hold, fade_out):
    """lines: [(text, size, font, dy, delay)]; returns RGB frame at time t."""
    im = Image.new('RGB', (S, S), BG)
    d = ImageDraw.Draw(im)
    k = S / 1080
    for text, size, font, dy, delay in lines:
        a = np.clip((t - delay) / fade_in, 0, 1) * np.clip((fade_in + hold + fade_out - t) / fade_out, 0, 1)
        if a <= 0:
            continue
        f = ImageFont.truetype(font, int(size * k))
        col = tuple(int(BG[i] + (INK[i] - BG[i]) * a) for i in range(3))
        w = d.textlength(text, font=f)
        d.text(((S - w) / 2, S / 2 + dy * k), text, font=f, fill=col)
    return im


def write_card(path, lines, total, fi, hold, fo):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (S, S),
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', path],
                         stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(np.asarray(card(lines, i / FPS, fi, hold, fo)).tobytes())
    p.stdin.close(); p.wait()


fr = 'frames/%s_%d' % (name, S)
os.makedirs('renders', exist_ok=True)
# power knob: scope switches on, and off after the final dot
ds = meta.get('dot_start', dur - 3.0)
# the final dot holds 1.5 s, then the power is cut (a fast 0.12 s collapse, not a slow fade)
power = '0:0,0.8:0,1.6:1,%.2f:1,%.2f:0' % (ds + 1.5, ds + 1.62)
if not os.environ.get('SKIP_SCOPE'):
    subprocess.run(['rm', '-rf', fr])
    subprocess.run([sys.executable, 'src/render.py', 'renders/%s.wav' % name, fr, '--video', '--size', str(S),
                    '--scale', '%.4f' % scale, '--power', power], check=True)

write_card(fr + '/intro.mp4', [('Headphones on.', 56, FONT_L, -36, 0.3)], INTRO, 0.6, 1.2, 0.8)
write_card(fr + '/outro.mp4', [
    ('LEFT & RIGHT', 96, FONT_M, -120, 0.0),
    ('Every sound you heard', 46, FONT_L, 30, 1.4),
    ('drew the picture you saw.', 46, FONT_L, 92, 1.4),
], OUTRO, 0.9, 3.6, 1.0)

with open(fr + '/all.txt', 'w') as fh:
    fh.write("file 'intro.mp4'\n")
    for line in open(fr + '/list.txt'):
        fh.write(line)
    fh.write("file 'outro.mp4'\n")
out = 'renders/%s_final_%d.mp4' % (name, S)
af = 'adelay=%d|%d,apad=pad_dur=%.2f' % (INTRO * 1000, INTRO * 1000, OUTRO)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', fr + '/all.txt', '-i', 'renders/%s.wav' % name,
                '-map', '0:v', '-map', '1:a', '-af', af, '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '320k', '-aac_is', '0', '-aac_pns', '0', '-aac_ms', '0', '-cutoff', '20000', '-t', '%.2f' % (INTRO + dur + OUTRO), out], check=True)
print(out)
