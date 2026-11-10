"""Assemble graded frames + supers + end card, pipe to ffmpeg, mux with audio.

usage: python compose.py [out.mp4] [--preview]   (preview: half res, missing frames -> nearest available)"""

import os, sys, json, glob, subprocess, math

import numpy as np, cv2

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

E = json.load(open(os.path.join(ROOT, 'edit.json'), encoding='utf-8'))

PREVIEW = '--preview' in sys.argv

OUT = next((a for a in sys.argv[1:] if a.endswith('.mp4')), os.path.join(ROOT, 'out', 'vesper61.mp4'))

FPS = 24; W, H = 1920, 816; OH = 1080

sc = 0.5 if PREVIEW else 1.0

w, h, oh = int(W*sc), int(H*sc), int(OH*sc)

F = 'C:/Windows/Fonts/'

def font(name, size): return ImageFont.truetype(F + name, int(size*sc))



_cache = {}

def load_rgba(shot, idx):

    p = os.path.join(ROOT, 'renders', shot, f'{idx:04d}.png')

    if not os.path.exists(p):

        files = sorted(glob.glob(os.path.join(ROOT, 'renders', shot, '[0-9][0-9][0-9][0-9].png')))

        if not files: return np.zeros((h, w, 3), np.float32), np.zeros((h, w, 1), np.float32)

        nums = [int(os.path.basename(f)[:4]) for f in files]; p = files[int(np.argmin([abs(n - idx) for n in nums]))]

    raw = cv2.imread(p, cv2.IMREAD_UNCHANGED)

    if raw is None or raw.ndim < 3 or raw.shape[2] < 4:

        return np.zeros((h, w, 3), np.float32), np.zeros((h, w, 1), np.float32)

    im = raw.astype(np.float32)/255.0

    if im.shape[1] != w: im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)

    return im[..., 2::-1].copy(), im[..., 3:4]



def c5_rise(lt):

    # 0 until the jet crosses the disc (~4.6 s), then eases to 1

    u = min(1, max(0, (lt - 4.6)/4.2)); return u*u*(3 - 2*u)

def c5_el(lt):

    return 0.26*min(lt, 4.6)/4.6 + 1.05*c5_rise(lt)

def sun_layer(lt, dur):

    # c5: 300 mm camera pitched up 0.252 deg; sun rises from 0.25 to 1.4 deg elevation

    el = c5_el(lt)

    fpx = 300/36*W*sc

    cy = h/2 - math.tan(math.radians(el - 0.252))*fpx; cx = w/2

    r = math.tan(math.radians(0.313))*fpx

    d = np.sqrt((xx - cx)**2 + (yy - cy)**2)/r

    limb = np.clip(1 - d**2, 0, 1)**0.4

    disc = (d < 1).astype(np.float32)*(0.55 + 0.45*limb)

    disc = cv2.GaussianBlur(disc, (0, 0), 1.2*sc)

    col = np.stack([np.ones_like(d), 0.80 + 0.12*limb, 0.52 + 0.25*limb], -1)

    halo = np.exp(-np.clip(d - 1, 0, None)/2.2)*(d >= 1)*0.2 + np.exp(-np.clip(d - 1, 0, None)/9.0)*0.05

    return disc[..., None]*col*1.6, halo[..., None]*np.array([1.0, 0.62, 0.32], np.float32)



def load_shot(shot, idx, lt=0, dur=1):

    if shot.startswith('c'):

        bg = load(shot + '_bg', idx)

        if shot == 'c5':

            disc, halo = sun_layer(lt, dur)

            bg = np.clip(bg - 0.1, 0, None)*np.array([0.95, 0.82, 0.68], np.float32)*1.05 + halo*0.8

            bg = bg*(1 - np.clip(disc.max(-1, keepdims=True), 0, 1)) + disc

        fg, a = load_rgba(shot + '_fg', idx)

        if shot == 'c5': fg = fg*0.38          # backlit by the sun: read as a silhouette

        return fg*a + bg*(1 - a)

    return load(shot, idx)



def load(shot, idx):

    d = os.path.join(ROOT, 'renders', shot)

    p = os.path.join(d, f'{idx:04d}.png')

    if not os.path.exists(p):

        files = sorted(glob.glob(os.path.join(d, '[0-9][0-9][0-9][0-9].png')))

        if not files: return np.zeros((h, w, 3), np.float32)

        nums = [int(os.path.basename(f)[:4]) for f in files]

        p = files[int(np.argmin([abs(n - idx) for n in nums]))]

    if p in _cache: return _cache[p]

    raw = cv2.imread(p, cv2.IMREAD_COLOR)

    if raw is None:   # file still being written

        import time; time.sleep(2); raw = cv2.imread(p, cv2.IMREAD_COLOR)

        if raw is None: return np.zeros((h, w, 3), np.float32)

    im = raw[:, :, ::-1].astype(np.float32)/255.0

    if im.shape[1] != w: im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)

    if len(_cache) > 4: _cache.clear()

    _cache[p] = im

    return im



yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

vign = 1 - 0.28*(((xx - w/2)/(w/2))**2*0.7 + ((yy - h/2)/(h/2))**2*0.9)

rng = np.random.default_rng(1)

skyramp = (np.array([0.92, 0.95, 1.06], np.float32)*(1 - np.clip(yy/(h*0.55), 0, 1))[..., None]

           + np.array([1.08, 1.02, 0.92], np.float32)*np.clip(yy/(h*0.55), 0, 1)[..., None])

ndgrad = (1 - 0.5*np.clip((yy - h*0.58)/(h*0.42), 0, 1)**0.8)[..., None]

def grade(im, shot):

    x = im*1.12

    if shot == 'r1': x = x*ndgrad

    if shot.startswith('c') and shot != 'c5':

        lum0 = x.mean(2, keepdims=True)

        x = x*np.array([1.10, 1.0, 0.86], np.float32)*skyramp + (lum0 > 0)*0

        core = np.clip((lum0 - 0.93)*12, 0, 1)

        cs = cv2.resize(core, (w//4, h//4), interpolation=cv2.INTER_AREA)

        glow = cv2.resize(cv2.GaussianBlur(cs, (0, 0), 10*sc), (w, h))[..., None]

        x = x + glow*np.array([1.6, 0.95, 0.45], np.float32)

    # bloom from highlights

    lum = x.mean(2, keepdims=True)

    hi = np.clip(x - 0.72, 0, None)*2.0

    small = cv2.resize(hi, (w//4, h//4), interpolation=cv2.INTER_AREA)

    b1 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 3*sc), (w, h), interpolation=cv2.INTER_LINEAR)

    b2 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 12*sc), (w, h), interpolation=cv2.INTER_LINEAR)

    x = x + b1*0.4 + b2*0.7*np.array([1.0, 0.72, 0.45], np.float32)

    # warm split tone: shadows teal-navy, highlights amber

    x = x*np.array([1.03, 1.0, 0.95], np.float32) + (1 - lum)*np.array([-0.006, 0.0, 0.012], np.float32)

    # gentle s-curve

    x = np.clip(x, 0, None); x = x/(1 + 0.12*x)

    x = 0.5 + (x - 0.5)*1.06

    x = x*vign[..., None]

    x = x + rng.normal(0, 0.012, (h, w, 1)).astype(np.float32)

    return np.clip(x, 0, 1)



def text_layer(draw_fn):

    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img); draw_fn(d, img)

    a = np.asarray(img).astype(np.float32)/255.0

    return a[..., :3], a[..., 3:4]

def tracked(d, x, y, s, f, fill, track):

    for ch in s:

        d.text((x, y), ch, font=f, fill=fill); x += d.textlength(ch, font=f) + track*sc

    return x

def twidth(d, s, f, track): return sum(d.textlength(c, font=f) for c in s) + track*sc*(len(s) - 1)



FT = font('segoeuil.ttf', 84); FP = font('segoeui.ttf', 27)

_sup = {}

def super_layer(sp):

    k = (sp['time'], sp['place'], sp.get('sun'))

    if k not in _sup:

        if len(_sup) > 40: _sup.clear()

        def fn(d, img):

            x0, y0 = int(100*sc), int(h - 250*sc)

            d.text((x0, y0), sp['time'], font=FT, fill=(255, 246, 232, 255))

            d.line([(x0 + 4*sc, y0 + 118*sc), (x0 + 84*sc, y0 + 118*sc)], fill=(232, 188, 118, 255), width=max(1, int(3*sc)))

            xe = tracked(d, x0 + 3*sc, y0 + 136*sc, sp['place'], FP, (255, 246, 232, 245), 6)

            if sp.get('sun'):

                tracked(d, xe + 34*sc, y0 + 136*sc, sp['sun'], FP, (246, 200, 120, 255), 6)

        rgb, a = text_layer(fn)

        sh = cv2.GaussianBlur(a[..., 0], (0, 0), 10*sc)[..., None]

        sh = np.clip(sh*2.2, 0, 1)

        _sup[k] = (rgb, a, sh)

    return _sup[k]



FB = font('BOD_R.TTF', 132); FS = font('BOD_R.TTF', 40); FI = font('CormorantInfant-Italic.ttf', 46); FL = font('segoeuil.ttf', 15)

def end_layer(phase):

    def fn(d, img):

        gold = (214, 172, 108, 255)

        s = 'VESPER'; tw = twidth(d, s, FB, 38)

        tracked(d, (w - tw)/2, h*0.27, s, FB, (250, 244, 234, 255), 38)

        s2 = '6 1'; tw2 = twidth(d, s2, FS, 8)

        cy = h*0.27 + 175*sc

        d.line([(w/2 - 150*sc, cy + 24*sc), (w/2 - 50*sc, cy + 24*sc)], fill=gold, width=max(1, int(1.5*sc)))

        d.line([(w/2 + 50*sc, cy + 24*sc), (w/2 + 150*sc, cy + 24*sc)], fill=gold, width=max(1, int(1.5*sc)))

        tracked(d, (w - tw2)/2, cy, s2, FS, gold, 8)

        if phase > 0:

            t = 'Make the evening last.'; tw3 = d.textlength(t, font=FI)

            d.text(((w - tw3)/2, h*0.27 + 265*sc), t, font=FI, fill=(240, 228, 210, int(255*phase)))

        ft = 'VESPER 61 is a fictional aircraft. Every frame and sound in this film was generated in code.'

        tw4 = d.textlength(ft, font=FL)

        d.text(((w - tw4)/2, h - 48*sc), ft, font=FL, fill=(150, 140, 128, int(200*phase)))

    return text_layer(fn)



def sstep(a, b, x): t = min(1, max(0, (x - a)/(b - a))); return t*t*(3 - 2*t)



total = E['total']; nfr = int(round(total*FPS))

RANGE = None

if '--range' in sys.argv:

    i_ = sys.argv.index('--range'); RANGE = (float(sys.argv[i_ + 1]), float(sys.argv[i_ + 2]))

FR = None

if '--frames' in sys.argv:

    i_ = sys.argv.index('--frames'); FR = (int(sys.argv[i_ + 1]), int(sys.argv[i_ + 2]))

MUX = '--mux' in sys.argv

os.makedirs(os.path.dirname(OUT), exist_ok=True)

tmp = OUT.replace('.mp4', '_video.mp4')

enc = ['-c:v', 'libx264', '-preset', 'medium' if not PREVIEW else 'veryfast', '-crf', '17' if not PREVIEW else '23', '-pix_fmt', 'yuv420p']

p = None if MUX else subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{oh}', '-r', str(FPS), '-i', '-'] + enc + [tmp], stdin=subprocess.PIPE)

edl = E['edl']

endA = None

last_c6 = None

frames = range(nfr) if RANGE is None else range(int(RANGE[0]*FPS), int(RANGE[1]*FPS))

if FR: frames = range(FR[0], min(FR[1], nfr))

if MUX: frames = range(0)

for fi in frames:

    t = fi/FPS

    seg = max([s for s in edl if s['start'] <= t + 1e-6], key=lambda s: s['start'])

    lt = t - seg['start']

    if seg['shot'] == 'end':

        # fade from the last hero frame to black, logo resolves

        base = np.zeros((h, w, 3), np.float32)

        if last_c6 is None:

            c6 = [x for x in edl if x['shot'] == 'c6'][0]

            last_c6 = grade(load_shot('c6', c6['f0'] + int(round(c6['dur']*FPS)) - 1, c6['dur'], c6['dur']), 'c6')

        if last_c6 is not None:

            base = last_c6*(1 - sstep(0.0, 1.2, lt))

        if endA is None or (lt > 1.6 and endA[2] < 1):

            ph = sstep(2.0, 3.0, lt)

            rgb, a = end_layer(ph); endA = (rgb, a, ph)

        rgb, a, _ = endA

        la = sstep(0.6, 2.0, lt)*(1 - sstep(seg['dur'] - 0.8, seg['dur'], lt))

        frame = base*(1 - a*la) + rgb*a*la

    else:

        idx = seg['f0'] + int(round(lt*FPS))

        frame = grade(load_shot(seg['shot'], idx, lt, seg['dur']), seg['shot'])

        if seg['shot'] == 'c6': last_c6 = frame

        # fades: in from black at film start, h2->h3 dip

        if seg['shot'] == 'h1': frame = frame*sstep(0.0, 1.2, lt)

        for sp in E['supers']:

            if sp['t'] <= t < sp['t'] + sp['d']:

                al = sstep(sp['t'], sp['t'] + 0.25, t)*(1 - sstep(sp['t'] + sp['d'] - 0.4, sp['t'] + sp['d'], t))

                if sp.get('roll'):

                    lt5 = t - E['cuts']['c5']

                    q = (t - sp['t'])/sp['d']

                    m = int(round(sp['m0'] + (sp['m1'] - sp['m0'])*q))

                    rise = c5_rise(lt5); sv = sp['s0'] + (sp['s1'] - sp['s0'])*rise

                    spx = dict(time=f'{(m // 60) % 24:02d}:{m % 60:02d}', place=sp['place1'] if rise > 0.35 else sp['place0'],

                               sun=f'SUN  +{sv:.1f}' + chr(176) + ('  ' + chr(8593) if rise > 0.02 else ''))

                    rgb, a, sh = super_layer(spx)

                else:

                    rgb, a, sh = super_layer(sp)

                frame = frame*(1 - 0.7*sh*al)

                frame = frame*(1 - a*al) + rgb*a*al

    out = np.zeros((oh, w, 3), np.float32); top = (oh - h)//2; out[top:top + h] = frame

    p.stdin.write((np.clip(out, 0, 1)*255 + 0.5).astype(np.uint8).tobytes())

    if fi % 120 == 0: print('frame', fi, '/', nfr, flush=True)

if p: p.stdin.close(); p.wait()

if MUX: tmp = sys.argv[sys.argv.index('--mux') + 1]



# audio mix: score + sfx + VO (with gentle ducking handled by levels)

vo_inputs = []; filt = []

args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp,

        '-i', os.path.join(ROOT, 'audio', 'score.wav'), '-i', os.path.join(ROOT, 'audio', 'sfx.wav')]

for i, (name, at) in enumerate(E['vo']):

    args += ['-i', os.path.join(ROOT, 'audio', 'vo', name + '.mp3')]

    ms = int(at*1000)

    filt.append(f'[{3 + i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.6,adelay={ms}|{ms},apad[v{i}]')

nv = len(E['vo'])

vmix = ''.join(f'[v{i}]' for i in range(nv))

filt.append(f'{vmix}amix=inputs={nv},volume={nv}[vo]')

filt.append('[vo]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asplit=2[vo1][vo2]')

filt.append('[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=0.55[mus0]')

filt.append('[mus0][vo2]sidechaincompress=threshold=0.03:ratio=4:attack=60:release=600[mus]')

filt.append('[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=0.6[sfx]')

filt.append(f'[mus][sfx][vo1]amix=inputs=3,volume=3,afade=t=out:st={total - 1.5}:d=1.5,atrim=0:{total},alimiter=limit=0.9[a]')

args += ['-filter_complex', ';'.join(filt), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-t', str(total), OUT]

if MUX:

    subprocess.run(args, check=True)

elif RANGE is None and FR is None:

    subprocess.run(args, check=True); os.remove(tmp)

else:

    os.replace(tmp, OUT)

print('wrote', OUT)

