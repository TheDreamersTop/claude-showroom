"""Render film frames in parallel chunks -> out/<name>.mp4 (video only).
usage: python render.py NAME [t0 t1] [--scale 0.5] [--step N] [--jobs 10]"""
import os, sys, subprocess, argparse, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
ap = argparse.ArgumentParser()
ap.add_argument('name'); ap.add_argument('t0', nargs='?', type=float, default=0.0); ap.add_argument('t1', nargs='?', type=float, default=None)
ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--jobs', type=int, default=10); ap.add_argument('--crf', type=int, default=14)
a = ap.parse_args()
os.environ['MOTH_SCALE'] = str(a.scale)
import multiprocessing as mp
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')

_CARD = {}


def card(img, a, engine):
    from PIL import Image, ImageDraw, ImageFont
    if 'c' not in _CARD:
        W, H = engine.W, engine.H
        im = Image.new('RGB', (W, H), (0, 0, 0))
        d = ImageDraw.Draw(im)
        A = os.path.join(HERE, '..', 'assets')
        f1 = ImageFont.truetype(os.path.join(A, 'kaiu.ttf'), int(H * 0.15))
        f2 = ImageFont.truetype(os.path.join(A, 'PlayfairDisplay-Italicwght.ttf'), int(H * 0.05))
        f3 = ImageFont.truetype(os.path.join(A, 'PlayfairDisplay-Italicwght.ttf'), int(H * 0.03))
        for txt, f, y, col in (('撈月', f1, 0.40, (236, 214, 170)), ('Catching the Moon', f2, 0.575, (210, 196, 168)),
                               ('a shadow play, made entirely in code', f3, 0.67, (150, 142, 128))):
            w = d.textlength(txt, font=f)
            d.text(((W - w) / 2, H * y - f.size / 2), txt, font=f, fill=col)
        _CARD['c'] = np.asarray(im).astype(np.float32)
    return np.clip(img.astype(np.float32) * (1 - a) + _CARD['c'] * a, 0, 255).astype(np.uint8)


def work(args):
    idx, f0, f1 = args
    os.environ['MOTH_SCALE'] = str(a.scale)
    sys.path.insert(0, HERE)
    import cv2; cv2.setNumThreads(1)
    import engine, film, flame
    fn = os.path.join(OUT, 'chunks', f'{a.name}_{idx:04d}.mp4')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{engine.W}x{engine.H}', '-r', '24', '-i', '-',
           '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', fn]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        t = f / 24.0
        shapes, cam, lamp, moon, ms, st = film.scene(t)
        cs = film.cutaway(t)
        ex = film.exposure(t)
        if cs is not None:
            img = flame.render_flame(cs, t, f)
        elif ex > 0.002:
            img = engine.render(shapes, cam, lamp=lamp, moon=moon, moon_shapes=ms, grain_seed=f, exposure=ex, statics=st)
        else:
            img = engine.finish(np.zeros((engine.H, engine.W, 3), np.float32), f)
        ca = film.card_alpha(t)
        if ca > 0.002:
            img = card(img, ca, engine)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    return fn

if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import film
    t1 = a.t1 if a.t1 is not None else film.DUR
    F0, F1 = int(round(a.t0 * 24)), int(round(t1 * 24))
    os.makedirs(os.path.join(OUT, 'chunks'), exist_ok=True)
    n = F1 - F0
    csz = max(8, min(48, n // (a.jobs * 5) + 1))
    tasks = [(i, f, min(f + csz, F1)) for i, f in enumerate(range(F0, F1, csz))]
    T = time.time()
    with mp.get_context('fork').Pool(a.jobs) as pool:
        files = pool.map(work, tasks, chunksize=1)
    lst = os.path.join(OUT, 'chunks', f'{a.name}.txt')
    open(lst, 'w').write(''.join(f"file '{os.path.abspath(x)}'\n" for x in files))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', os.path.join(OUT, a.name + '.mp4')], check=True)
    for x in files: os.remove(x)
    print(f'{a.name}: {n} frames in {time.time()-T:.0f}s')
