"""Phosphor renderer. Reads a stereo wav (L = X, R = Y) and draws what an XY oscilloscope would show.

Usage: python render.py audio.wav out_dir [--start s] [--end s] [--fps 30] [--size 1080] [--every n]
Writes PNG frames out_dir/f_%05d.png (frame index is absolute from t=0).
"""
import sys, os, argparse
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from scipy.ndimage import gaussian_filter
from PIL import Image
from numba import njit
from multiprocessing import Pool

U = 8            # DAC reconstruction oversampling
SCALE = 0.44     # unit amplitude -> fraction of screen size (the "volts/div" knob, fixed for whole film)


@njit(cache=True)
def splat(xs, ys, w, buf):
    H, W = buf.shape
    for i in range(xs.shape[0]):
        x = xs[i]; y = ys[i]
        ix = int(np.floor(x)); iy = int(np.floor(y))
        if ix < 0 or iy < 0 or ix >= W - 1 or iy >= H - 1:
            continue
        fx = x - ix; fy = y - iy
        buf[iy, ix] += w * (1 - fx) * (1 - fy)
        buf[iy, ix + 1] += w * fx * (1 - fy)
        buf[iy + 1, ix] += w * (1 - fx) * fy
        buf[iy + 1, ix + 1] += w * fx * fy


def background(S, SCALE=SCALE):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = (S - 1) / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (S / 2)
    # dark glass with a faint green cast, vignette
    base = 0.018 * (1 - 0.55 * np.clip(r, 0, 1.4) ** 2)
    bg = np.stack([base * 0.55, base * 0.9, base * 0.7], -1)
    # graticule: 10 x 10 divisions spanning the unit square * SCALE*2
    g = np.zeros((S, S), np.float32)
    span = SCALE * S  # pixels per unit
    for k in range(-5, 6):
        p = int(round(cx + k * span / 5 * 1.0))
        if 0 <= p < S:
            lw = 1
            g[:, p:p + lw] += 0.5
            g[p:p + lw, :] += 0.5
    # minor ticks on centre axes
    for k in range(-25, 26):
        p = int(round(cx + k * span / 25))
        if 0 <= p < S:
            c = int(cx)
            g[c - 4:c + 5, p] += 0.6
            g[p, c - 4:c + 5] += 0.6
    g = np.clip(g, 0, 1)
    mask = (np.abs(xx - cx) <= span + 1) & (np.abs(yy - cy) <= span + 1)
    g *= mask * (1 - 0.6 * np.clip(r, 0, 1))
    g = gaussian_filter(g, 0.6)
    # faint reflection on the glass, top-left
    hl = np.exp(-(((xx - 0.3 * S) / (0.28 * S)) ** 2 + ((yy - 0.22 * S) / (0.16 * S)) ** 2))
    bg += (hl * 0.010)[..., None] * np.array([0.8, 0.9, 1.0], np.float32)
    bg += g[..., None] * np.array([0.020, 0.040, 0.034], np.float32)
    return bg.astype(np.float32)


PHOS = np.array([0.30, 1.0, 0.52], np.float32)   # P31 green; saturates toward white


def tonemap(v, bg, gain):
    # v: energy per pixel (float). Compress so a parked dot doesn't nuke the frame.
    vc = v / (1 + v / 40.0)
    core = gaussian_filter(vc, 0.9 * v.shape[0] / 1080 + 0.35)
    S = v.shape[0]; k = 4
    small = vc.reshape(S // k, k, S // k, k).mean((1, 3))
    h = gaussian_filter(small, 5.0 * S / 1080 / k) * 0.35 + gaussian_filter(small, 18.0 * S / 1080 / k) * 0.18
    halo = np.asarray(Image.fromarray(h.astype(np.float32), 'F').resize((S, S), Image.BILINEAR))
    e = (core + halo) * gain
    rgb = 1 - np.exp(-e[..., None] * PHOS[None, None, :])
    out = bg + rgb * (1 - bg)
    return out


def load(path):
    sr, a = wavfile.read(path)
    if a.dtype == np.int16:
        a = a.astype(np.float32) / 32768
    elif a.dtype == np.int32:
        a = a.astype(np.float32) / 2147483648
    return sr, a.astype(np.float32)


def render_chunk(args):
    path, out, f0, f1, fps, S, gain, every, scale, power, vid = args
    import subprocess
    enc = None
    if vid:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (S, S),
                                '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'fast',
                                '-pix_fmt', 'yuv420p', os.path.join(out, 'seg_%05d.mp4' % f0)], stdin=subprocess.PIPE)
    sr, a = load(path)
    spf = sr / fps
    warm = 60
    fs = max(0, f0 - warm)
    s0 = int(fs * spf); s1 = min(len(a), int(f1 * spf) + 64)
    seg = a[s0:s1]
    pad = 32
    seg = np.concatenate([np.repeat(seg[:1], pad, 0), seg, np.repeat(seg[-1:], pad, 0)])
    up = resample_poly(seg, U, 1, axis=0).astype(np.float32)[pad * U:-pad * U]
    bg = background(S, scale)
    grain = np.random.default_rng(f0)
    fast = np.zeros((S, S), np.float32)
    slow = np.zeros((S, S), np.float32)
    c = (S - 1) / 2
    span = scale * S
    w = 1.0 / U
    for f in range(fs, f1):
        a0 = int(f * spf) - s0; a1 = int((f + 1) * spf) - s0
        pts = up[a0 * U:a1 * U]
        new = np.zeros((S, S), np.float32)
        if len(pts):
            xs = (c + pts[:, 0] * span).astype(np.float64)
            ys = (c - pts[:, 1] * span).astype(np.float64)
            splat(xs, ys, w, new)
        fast = fast * 0.30 + new
        slow = slow * 0.90 + new * 0.011
        if f >= f0 and (f - f0) % every == 0:
            pw = np.interp(f / fps, power[0], power[1]) if power else 1.0
            img = tonemap((fast + slow) * pw, bg * min(1, pw * 3), gain)
            img = np.clip(img, 0, 1) ** (1 / 1.1)
            img = img + grain.normal(0, 0.0022, (S, S, 1)).astype(np.float32)  # film grain, also stops banding
            b = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
            if enc:
                enc.stdin.write(b.tobytes())
            else:
                Image.fromarray(b).save(os.path.join(out, 'f_%05d.png' % f))
    if enc:
        enc.stdin.close(); enc.wait()
    return f1


def main():
    p = argparse.ArgumentParser()
    p.add_argument('wav'); p.add_argument('out')
    p.add_argument('--start', type=float, default=0); p.add_argument('--end', type=float, default=None)
    p.add_argument('--fps', type=int, default=30); p.add_argument('--size', type=int, default=1080)
    p.add_argument('--gain', type=float, default=6.0); p.add_argument('--every', type=int, default=1)
    p.add_argument('--jobs', type=int, default=9)
    p.add_argument('--scale', type=float, default=SCALE)
    p.add_argument('--video', action='store_true', help='write mp4 segments + concat list instead of PNGs')
    p.add_argument('--power', default='', help='t:v,t:v brightness automation (the scope power/intensity knob)')
    A = p.parse_args()
    os.makedirs(A.out, exist_ok=True)
    sr, a = load(A.wav)
    dur = len(a) / sr
    end = dur if A.end is None else min(A.end, dur)
    F0 = int(A.start * A.fps); F1 = int(end * A.fps)
    pw = None
    if A.power:
        kv = [tuple(map(float, x.split(':'))) for x in A.power.split(',')]
        pw = ([k for k, v in kv], [v for k, v in kv])
    n = max(1, min(A.jobs, (F1 - F0) // 30))
    edges = np.linspace(F0, F1, n + 1).astype(int)
    jobs = [(A.wav, A.out, edges[i], edges[i + 1], A.fps, A.size, A.gain, A.every, A.scale, pw, A.video) for i in range(n)]
    with Pool(n) as pool:
        for r in pool.imap_unordered(render_chunk, jobs):
            pass
    if A.video:
        with open(os.path.join(A.out, 'list.txt'), 'w') as fh:
            for i in range(n):
                fh.write("file 'seg_%05d.mp4'\n" % edges[i])
    print('frames', F0, F1)


if __name__ == '__main__':
    main()
