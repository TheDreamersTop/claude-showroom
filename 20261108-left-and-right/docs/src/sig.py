"""Signal building blocks. Every signal is an (N, 2) float array: column 0 = left = X, column 1 = right = Y."""
import numpy as np

SR = 48000
A4 = 440.0
_NAMES = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}


def hz(name):
    """'A4' -> 440, 'C#5', 'Bb3'."""
    if isinstance(name, (int, float)):
        return float(name)
    n = _NAMES[name[0]]
    i = 1
    if name[i] == '#':
        n += 1; i += 1
    elif name[i] == 'b':
        n -= 1; i += 1
    octv = int(name[i:])
    return A4 * 2 ** ((n + 12 * (octv - 4)) / 12)


def N(d):
    return int(round(d * SR))


def tt(d):
    return np.arange(N(d)) / SR


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def auto(t, pts, ease=True):
    """Piecewise automation. pts = [(time, value), ...]. Smoothstep between points if ease."""
    pts = sorted(pts)
    out = np.full(t.shape, float(pts[0][1]))
    for (t0, v0), (t1, v1) in zip(pts[:-1], pts[1:]):
        m = (t >= t0) & (t < t1)
        u = (t[m] - t0) / max(t1 - t0, 1e-9)
        if ease:
            u = smooth(u)
        out[m] = v0 + (v1 - v0) * u
    out[t >= pts[-1][0]] = pts[-1][1]
    return out


def cycles(freq):
    """Integrate a frequency array (Hz per sample) into phase in cycles."""
    return np.cumsum(freq) / SR


def melody(t, notes, glide=0.04, att=0.03, rel=0.12, floor=0.0):
    """notes = [(start, dur, freq_or_name, amp)]. Returns (freq, amp) arrays.
    Frequency holds the last note between notes and glides into the next one.
    Amplitude has attack/release envelopes (amplitude = size on screen = loudness)."""
    freq = np.zeros_like(t)
    amp = np.full_like(t, floor)
    notes = sorted(notes, key=lambda n: n[0])
    if not notes:
        return freq, amp
    f_prev = hz(notes[0][2])
    freq[:] = f_prev
    for i, (s, d, f, a) in enumerate(notes):
        f = hz(f)
        m = t >= s
        g = np.clip((t[m] - s) / max(glide, 1e-6), 0, 1)
        freq[m] = f_prev + (f - f_prev) * smooth(g)
        f_prev = f
        # envelope
        e = np.clip((t - s) / att, 0, 1) * np.clip((s + d - t) / rel + 1, 0, 1)
        e = np.where(t < s, 0, e)
        e = np.where(t > s + d + rel, 0, e)
        amp = np.maximum(amp, smooth(e) * a)
    return freq, amp


# ---------------------------------------------------------------- shapes

class Path:
    """Closed path sampled uniformly by (weighted) arclength into M points."""

    def __init__(self, pts, M=2048, jumps=None, lowpass=None, jump_w=0.0004):
        pts = np.asarray(pts, float)
        if jumps is None:
            jumps = np.zeros(len(pts), bool)
        # close
        P = np.vstack([pts, pts[:1]])
        J = np.append(jumps, True if jumps.any() else False)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        jw = np.broadcast_to(np.asarray(jump_w, float), (len(pts),))
        jw = np.append(jw, jw[-1])         # closing jump (last stroke back to the first) uses the last stroke's weight
        w = np.where(J[1:], seg * jw[1:], seg) + 1e-9
        s = np.concatenate([[0], np.cumsum(w)])
        u = np.linspace(0, s[-1], M, endpoint=False)
        x = np.interp(u, s, P[:, 0]); y = np.interp(u, s, P[:, 1])
        self.p = np.stack([x, y], 1)
        if lowpass:
            self.p = _lowpass(self.p, lowpass)
        self.M = M

    def at(self, ph):
        """ph in cycles (any real) -> (n, 2) positions, linear interpolation around the loop."""
        u = (ph % 1.0) * self.M
        i0 = np.floor(u).astype(int) % self.M
        i1 = (i0 + 1) % self.M
        f = (u - np.floor(u))[:, None]
        return self.p[i0] * (1 - f) + self.p[i1] * f


def _lowpass(p, K):
    z = p[:, 0] + 1j * p[:, 1]
    Z = np.fft.fft(z)
    M = len(z)
    k = np.fft.fftfreq(M, 1 / M)
    # soft roll-off keeps corners rounded without ringing
    g = np.exp(-(k / K) ** 2)
    z = np.fft.ifft(Z * g)
    return np.stack([z.real, z.imag], 1)


def strokes_path(strokes, M=2048, lowpass=None, retrace=True, greedy=True, jump_w=0.0004):
    """Several open strokes -> one closed tour. Each stroke is drawn forward then back (no visible jump),
    then the beam jumps to the next stroke (fast, nearly invisible). greedy: visit strokes nearest-first,
    entering each at its nearest end (or nearest point, for closed loops) so the jumps stay short."""
    S = [np.asarray(st, float) for st in strokes]
    if greedy and len(S) > 1:
        s0 = S[0]
        if np.linalg.norm(s0[0] - s0[-1]) < 1e-3:
            others = np.vstack(S[1:])
            dmin = np.min(np.linalg.norm(s0[:, None, :] - others[None, ::max(1, len(others) // 400), :], axis=2), axis=1)
            i = int(np.argmin(dmin)); s0 = np.vstack([s0[i:-1], s0[:i + 1]])
        order = [s0]; rest = S[1:]
        cur = s0[0]
        while rest:
            best = None
            for k, st in enumerate(rest):
                closed = np.linalg.norm(st[0] - st[-1]) < 1e-3
                d = np.linalg.norm(st - cur, axis=1)
                if closed:
                    i = int(np.argmin(d)); cand = np.vstack([st[i:-1], st[:i + 1]]); dd = d[i]
                else:
                    if d[0] <= d[-1]:
                        cand = st; dd = d[0]
                    else:
                        cand = st[::-1]; dd = d[-1]
                if best is None or dd < best[0]:
                    best = (dd, k, cand)
            order.append(best[2]); rest.pop(best[1]); cur = best[2][0]
        S = order
    jws = list(jump_w) if np.ndim(jump_w) else [jump_w] * len(S)
    pts = []; jumps = []; jwp = []
    for st, jwv in zip(S, jws):
        seq = np.vstack([st, st[::-1][1:]]) if retrace else st
        for k, q in enumerate(seq):
            pts.append(q); jumps.append(k == 0 and len(pts) > 1); jwp.append(jwv)
    return Path(np.array(pts), M=M, jumps=np.array(jumps), lowpass=lowpass, jump_w=np.array(jwp))


def align(pa, pb):
    """Rotate pb's sample order (and direction) to best match pa for morphing."""
    best = None
    for cand in (pb, pb[::-1]):
        Za = np.fft.fft(pa[:, 0] + 1j * pa[:, 1]); Zb = np.fft.fft(cand[:, 0] + 1j * cand[:, 1])
        cc = np.fft.ifft(Za * np.conj(Zb)).real
        sh = int(np.argmax(cc))
        c2 = np.roll(cand, sh, axis=0)
        d = np.sum((c2 - pa) ** 2)
        if best is None or d < best[0]:
            best = (d, c2)
    return best[1]


def trace(path, ph, scale=1.0, off=(0, 0), rot=0.0):
    p = path.at(ph)
    return xform(p, scale, off, rot)


def xform(p, scale=1.0, off=(0, 0), rot=0.0):
    scale = np.asarray(scale, float)
    rot = np.asarray(rot, float)
    if np.any(rot != 0):
        c = np.cos(rot); s = np.sin(rot)
        x = p[:, 0] * c - p[:, 1] * s
        y = p[:, 0] * s + p[:, 1] * c
        p = np.stack([x, y], 1)
    sx = scale if scale.ndim == 0 else scale
    p = p * (sx[:, None] if np.ndim(sx) else sx)
    ox = np.asarray(off[0], float); oy = np.asarray(off[1], float)
    return np.stack([p[:, 0] + ox, p[:, 1] + oy], 1)


def morph_trace(pa, pb, w, ph):
    """Trace a path that morphs from pa to pb as w goes 0->1 (w per sample)."""
    A = pa.at(ph); B = pb.at(ph)
    w = np.asarray(w)[:, None] if np.ndim(w) else w
    return A * (1 - w) + B * w


def morph_paths(pa, pb):
    """Return a copy of pb whose points are aligned to pa (call once before morph_trace)."""
    q = Path.__new__(Path)
    q.M = pb.M
    q.p = align(pa.p, pb.p)
    return q


def mux(sigs, period, weights=None):
    """Time-multiplex several equal-length signals: the beam visits each in turn for `period` samples
    (scaled by weights). Two figures on screen at once, each heard as its own voice."""
    n = len(sigs[0])
    if weights is None:
        weights = [1] * len(sigs)
    lens = [max(1, int(period * w)) for w in weights]
    cyc = sum(lens)
    idx = np.arange(n) % cyc
    out = np.zeros_like(sigs[0])
    acc = 0
    for s, L in zip(sigs, lens):
        m = (idx >= acc) & (idx < acc + L)
        out[m] = s[m]
        acc += L
    return out


def xfade(a, b, d):
    """Concatenate a and b with a d-second positional crossfade (beam glides between figures)."""
    k = N(d)
    if k == 0:
        return np.vstack([a, b])
    w = smooth(np.linspace(0, 1, k))[:, None]
    mid = a[-k:] * (1 - w) + b[:k] * w
    return np.vstack([a[:-k], mid, b[k:]])


def project3d(P, ax, ay, dist=3.0):
    """P (n,3) rotated about y by ay then x by ax (per-sample arrays allowed); perspective project."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    c, s = np.cos(ay), np.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    c, s = np.cos(ax), np.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    f = dist / (dist + z)
    return np.stack([x * f, y * f], 1)
