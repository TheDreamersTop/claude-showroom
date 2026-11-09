"""Scene definitions: sim layers, generation schedules, cameras and overlays, all timed to narration cues."""
import json, os
import numpy as np
from life import World, pattern
from script import ORDER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "out", "cache")
os.makedirs(CACHE, exist_ok=True)
FPS = 30
FILM = ORDER + ["credits", "sting"]
STING_START_GEN, STING_RATE = None, 7.0
TAIL = dict(open=5.2, law=1.2, still=1.2, osc=1.4, glider=1.4, eater=1.1, gun=2.0, rpent=2.2, end=2.8)


def _sting_geom():
    w = World(200, 200).place("glider", 40, 40).place("eater", 60, 60)
    pops = []
    for _ in range(200):
        w.step(); pops.append(int(w.cells.sum()))
    contact = next(i for i, p in enumerate(pops) if p != 12) + 1
    return contact


STING_CONTACT = None
STING_DUR = 6.4


# ---------- interpolation helpers ----------
def pchip(xs, ys):
    """Monotone cubic interpolant (Fritsch–Carlson). Returns f(x) clamped at the ends."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = min(np.searchsorted(xs, x, side="right") - 1, len(h) - 1)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def keycam(keys):
    """keys: [(t, cx, cy, z, rot)] -> eased segment-by-segment camera (z interpolated in log space)."""
    keys = sorted(keys)
    def cam(t):
        if t <= keys[0][0]:
            k = keys[0]; return dict(cx=k[1], cy=k[2], z=k[3], rot=k[4])
        for a, b in zip(keys, keys[1:]):
            if t <= b[0]:
                u = ease((t - a[0]) / max(1e-6, b[0] - a[0]))
                return dict(cx=a[1] + (b[1] - a[1]) * u, cy=a[2] + (b[2] - a[2]) * u,
                            z=float(np.exp(np.log(a[3]) + (np.log(b[3]) - np.log(a[3])) * u)),
                            rot=a[4] + (b[4] - a[4]) * u)
        k = keys[-1]; return dict(cx=k[1], cy=k[2], z=k[3], rot=k[4])
    return cam


def handheld(cam, amp=1.2, seed=0):
    """Add slow 'handheld' drift (amp in screen pixels)."""
    r = np.random.default_rng(seed); ph = r.uniform(0, 6.28, 6); fr = r.uniform(0.07, 0.23, 6)
    def c(t):
        d = dict(cam(t))
        dx = amp * (np.sin(t * fr[0] * 6.28 + ph[0]) + 0.5 * np.sin(t * fr[1] * 6.28 + ph[1]))
        dy = amp * (np.sin(t * fr[2] * 6.28 + ph[2]) + 0.5 * np.sin(t * fr[3] * 6.28 + ph[3]))
        d["cx"] += dx / d["z"]; d["cy"] += dy / d["z"]
        d["rot"] += 0.004 * np.sin(t * fr[4] * 6.28 + ph[4])
        return d
    return c


# ---------- layers ----------
class Layer:
    """A World pasted into the scene canvas at (ox, oy), advanced by gen_fn(t) -> float generation."""
    def __init__(self, make_world, ox, oy, gen_fn, age0=0.0):
        self.make_world, self.ox, self.oy, self.gen_fn, self.age0 = make_world, ox, oy, gen_fn, age0
        self.w = None

    def reset(self):
        self.w = self.make_world()
        self.w.age += self.age0
        self.base = self.w.gen
        self.prev = (self.w.cells.copy(), self.w.age.copy())
        self.w.step()
        self.births = self.w.births

    def at(self, t):
        if self.w is None:
            self.reset()
        g = self.base + max(0.0, self.gen_fn(t))
        n = int(np.floor(g))
        if n + 1 < self.w.gen:  # time went backwards: rebuild
            self.reset()
        nb = np.zeros_like(self.w.cells)
        while self.w.gen < n + 1:
            self.prev = (self.w.cells.copy(), self.w.age.copy())
            self.w.step()
            nb |= self.w.births
        self.births = nb
        f = ease(g - n)
        pc, pa = self.prev
        alive = pc * (1 - f) + self.w.cells * f
        age = np.where(self.w.cells, self.w.age, pa)
        return alive.astype(np.float32), age.astype(np.float32), int(self.w.gen - 1 - self.base + (1 if f >= 0.5 else 0))


def ash(seed, w=420, h=300, gens=4000, density=0.34, margin=60):
    path = os.path.join(CACHE, f"ash_{seed}_{w}x{h}_{gens}.npz")
    if os.path.exists(path):
        d = np.load(path); wd = World(w, h); wd.cells = d["c"]; wd.age = d["a"]; wd.gen = gens; return wd
    r = np.random.default_rng(seed)
    wd = World(w, h)
    wd.cells[margin:h - margin, margin:w - margin] = r.random((h - 2 * margin, w - 2 * margin)) < density
    for _ in range(gens):
        wd.step()
    np.savez_compressed(path, c=wd.cells, a=wd.age)
    return wd


def cleared(wd, x0, y0, x1, y1):
    wd.cells[y0:y1, x0:x1] = False; wd.age[y0:y1, x0:x1] = 0
    return wd


def rate(r, t0=0.0, g0=0.0):
    return lambda t: g0 + max(0.0, t - t0) * r


def keys_gen(keys):
    xs, ys = zip(*keys)
    f = pchip(xs, ys)
    return lambda t: float(f(t))


def held(*steps):
    """steps: (t_switch, g_from, g_to, dur) -> piecewise: hold, then ease between gens."""
    def f(t):
        g = steps[0][1]
        for ts, a, b, d in steps:
            if t >= ts:
                g = a + (b - a) * min(1.0, (t - ts) / d)
        return g
    return f


# ---------- scene container ----------
class Scene:
    def __init__(self, name, canvas, layers, cam, dur, cues, focus=None, overlays=None, fade_in=0.5, fade_out=0.5, dust=True):
        self.name, self.canvas, self.layers, self.cam, self.dur, self.cues = name, canvas, layers, cam, dur, cues
        self.focus = focus or (lambda t: (360, 300))
        self.overlays = overlays or (lambda t, cam, gens: [])
        self.fade_in, self.fade_out, self.dust = fade_in, fade_out, dust
        self.black = False
        self.dim = lambda t: 1.0

    def frame_state(self, t):
        W, H = self.canvas
        alive = np.zeros((H, W), np.float32); age = np.zeros((H, W), np.float32)
        gens, births = [], []
        for L in self.layers:
            a, g, gen = L.at(t)
            h, w = a.shape
            y0, x0 = max(0, L.oy), max(0, L.ox)
            y1, x1 = min(H, L.oy + h), min(W, L.ox + w)
            if y1 > y0 and x1 > x0:
                a = a[y0 - L.oy:y1 - L.oy, x0 - L.ox:x1 - L.ox]; g = g[y0 - L.oy:y1 - L.oy, x0 - L.ox:x1 - L.ox]
                sl = (slice(y0, y1), slice(x0, x1))
                alive[sl] = np.maximum(alive[sl], a); age[sl] = np.where(a > 0.01, g, age[sl])
            gens.append(gen)
            if L.births is not None and L.births.any():
                ys, xs = np.nonzero(L.births); births.append(np.stack([xs + L.ox, ys + L.oy], 1))
        births = np.concatenate(births) if births else np.zeros((0, 2), int)
        return alive, age, gens, births

    def exposure(self, t):
        e = 1.0
        if self.fade_in > 0: e *= ease(t / self.fade_in)
        if self.fade_out > 0: e *= ease((self.dur - t) / self.fade_out)
        return e


def timeline():
    vo = json.load(open(os.path.join(ROOT, "out", "vo", "index.json")))
    cues, durs = {}, {}
    for sc in ORDER:
        t, c, i = 0.0, [], 0
        while f"{sc}:{i}" in vo:
            v = vo[f"{sc}:{i}"]; t += v["pause"]; c.append((t, t + v["dur"])); t += v["dur"]; i += 1
        cues[sc] = c; durs[sc] = t + TAIL[sc]
    cues["credits"], durs["credits"] = [], 9.5
    cues["sting"], durs["sting"] = [], STING_DUR
    return cues, durs, vo


# ---------- the scenes ----------
def ring(x, y, t0, t1, r=1.0, color=(1.0, 0.95, 0.75)):
    return ("ring", x, y, t0, t1, r, color)


def build(name):
    cues, durs, _ = timeline()
    c, dur = cues[name], durs[name]
    S = lambda i: c[i][0]
    E = lambda i: c[i][1]

    if name == "open":
        L = Layer(lambda: ash(11), 0, 0, rate(0.9))
        cam = handheld(keycam([(0, 150, 120, 13.0, 0.10), (dur, 196, 146, 21.0, 0.03)]), 1.5, 1)
        t_title = E(2) + 0.6
        ov = lambda t, cam, gens: [("title", "PLANET  B3/S23", t_title, dur - 0.3)]
        sc = Scene(name, (420, 300), [L], cam, dur, c, focus=lambda t: (380, 260), overlays=ov, fade_in=3.0, fade_out=0.8)
        sc.dim = lambda t: 1.0 - 0.5 * ease((t - t_title) / 1.5)
        return sc

    if name == "law":
        def L_world(nm, rows):
            def mk():
                w = World(12, 12); a = np.array([[ch == "O" for ch in r] for r in rows]); w.cells[4:4 + a.shape[0], 4:4 + a.shape[1]] = a; return w
            return mk
        A = Layer(L_world("L", ["O.", "OO"]), 14, 24, held((0, 0, 0, 1), (S(1) + 0.15, 0, 1, 0.7)))
        B = Layer(L_world("dom", ["OO"]), 44, 24, held((0, 0, 0, 1), (E(3) - 0.5, 0, 1, 0.9)))
        Cc = Layer(L_world("plus", [".O.", "OOO", ".O."]), 74, 23,
                   lambda t: 0 if t < S(4) + 1.3 else min(1.0, (t - S(4) - 1.3) / 0.8) + max(0.0, t - S(4) - 2.6) * 1.4)
        # cell centres in canvas coords (layer offset + 4 + local)
        ax, ay = 14 + 4, 24 + 4
        bx, by = 44 + 4, 24 + 4
        cx_, cy_ = 74 + 4, 23 + 4
        cam = handheld(keycam([
            (0, ax + 1, ay + 1, 36, 0.0), (S(0), ax + 1, ay + 1, 46, 0.0), (E(1) + 0.5, ax + 1, ay + 1, 50, 0.0),
            (S(2) + 0.2, ax + 1, ay + 1, 50, 0.0), (S(3) - 0.2, bx + 1, by + 0.5, 48, 0.0), (E(3) + 0.4, bx + 1, by + 0.5, 50, 0.0),
            (S(4) - 0.1, cx_ + 1, cy_ + 1, 46, 0.0), (E(4) + 0.6, cx_ + 1, cy_ + 1, 48, 0.0),
            (S(5) + 0.4, (ax + cx_) / 2 + 1, ay + 1, 15, 0.0), (dur, (ax + cx_) / 2 + 1, ay + 1, 13, 0.0)]), 1.0, 2)
        rings = [ring(ax + 1, ay, S(0) + 0.4, S(1) + 0.6), ring(ax, ay + 1, S(2) + 0.6, E(2) + 0.3),
                 ring(bx, by, S(3) + 0.3, E(3) - 0.3), ring(bx + 1, by, S(3) + 0.3, E(3) - 0.3),
                 ring(cx_ + 1, cy_ + 1, S(4) + 0.2, S(4) + 1.6, color=(1.0, 0.55, 0.45))]
        ov = lambda t, cam, gens: rings
        # background ash, kept dim and far: only a strip far below the vignettes
        bgL = Layer(lambda: cleared(ash(23, 300, 200), 0, 0, 300, 140), -60, -40, rate(0.9))
        return Scene(name, (200, 120), [bgL, A, B, Cc], cam, dur, c, overlays=ov)

    if name == "still":
        def objs():
            w = World(80, 50)
            w.place("block", 20, 22).place("beehive", 34, 16).place("loaf", 46, 24).place("boat", 58, 18)
            return w
        objL = Layer(objs, 60, 50, keys_gen([(0, 0), (S(1), 4), (E(1) - 0.2, 11000), (dur, 11010)]), age0=200)
        bgL = Layer(lambda: cleared(ash(31, 260, 180), 50, 40, 150, 110), 0, 0, rate(0.8))
        bx, by = 60 + 21, 50 + 23
        cam = handheld(keycam([
            (0, bx, by, 60, 0.0), (E(2), bx, by, 78, 0.0), (S(3) + 0.1, bx, by, 70, 0.0),
            (S(3) + 0.7, 60 + 35.5, 50 + 17, 52, 0.0), (S(3) + 1.6, 60 + 35.5, 50 + 17, 54, 0.0),
            (S(3) + 2.0, 60 + 47.5, 50 + 25.5, 52, 0.0), (S(3) + 2.6, 60 + 47.5, 50 + 25.5, 54, 0.0),
            (S(3) + 3.0, 60 + 59, 50 + 19, 52, 0.0), (S(4) + 0.3, 60 + 59, 50 + 19, 52, 0.0),
            (dur, 60 + 42, 50 + 22, 14, 0.06)]), 1.2, 3)
        ov = lambda t, cam, gens: [("counter", "GENERATION", gens[1], S(1) - 0.4, E(2) + 0.6)]
        return Scene(name, (260, 180), [bgL, objL], cam, dur, c, overlays=ov)

    if name == "osc":
        beat = 0.75
        def objs():
            w = World(140, 60)
            w.place("blinker", 14, 30).place("toad", 26, 29).place("beacon", 40, 28).place("pentadecathlon", 56, 30)
            w.place("pulsar", 110, 24)
            return w
        objL = Layer(objs, 60, 60, lambda t: t / beat)
        bgL = Layer(lambda: cleared(ash(41, 320, 200), 50, 50, 300, 140), 0, 0, rate(0.8))
        blx, bly = 60 + 15.5, 60 + 30.5
        px, py = 60 + 116.5, 60 + 30.5
        cam = handheld(keycam([
            (0, 60 + 30, 60 + 30, 12, 0.08), (S(1) - 0.3, 60 + 36, 60 + 31, 13, 0.05), (S(1) + 0.4, blx, bly, 52, 0.0),
            (S(2) - 0.2, blx + 1, bly, 54, 0.0), (S(2) + 1.4, px, py, 24, 0.0), (S(3), px, py, 27, 0.0),
            (dur, px, py, 6, -0.04)]), 1.2, 4)
        return Scene(name, (320, 200), [bgL, objL], cam, dur, c)

    if name == "glider":
        gx0, gy0 = 236, 166  # glider spawn (canvas), at the ash edge
        gen = keys_gen([(0, 0), (S(2), 10), (S(3), 26), (E(3), 40), (S(4), 46), (dur, 46 + 13 * (dur - S(4)))])
        def gw():
            w = World(500, 420); w.place("glider", gx0, gy0); return w
        gL = Layer(gw, 0, 0, gen)
        bgL = Layer(lambda: cleared(ash(53, 300, 240), 220, 150, 300, 240), 0, 0, rate(0.9))
        def gpos(t):
            g = gen(t); return gx0 + 1 + g / 4, gy0 + 1 + g / 4
        track_until = S(4) + 0.4
        base = keycam([(0, 0, 0, 12, 0.10), (S(1), 0, 0, 40, 0.02), (S(3), 0, 0, 66, 0.0), (E(3), 0, 0, 60, 0.0), (S(4) + 1.0, 0, 0, 34, 0.0), (dur, 0, 0, 30, 0.0)])
        def cam(t):
            d = base(t)
            if t < track_until:
                x, y = gpos(t)
                x -= (1 - ease(t / max(S(1), 1e-3))) * 30; y -= (1 - ease(t / max(S(1), 1e-3))) * 22  # open wide on the ash
                if t >= S(2) - 0.3:  # hold still and let it walk across the frame, then catch up
                    ax, ay = gpos(S(2) - 0.3); ax += 1.2; ay += 1.2
                    u = ease((t - S(3) + 0.2) / 1.2)
                    x, y = ax * (1 - u) + x * u, ay * (1 - u) + y * u
            else:
                x, y = gpos(track_until)
            d["cx"], d["cy"] = x, y
            return d
        return Scene(name, (500, 420), [bgL, gL], handheld(cam, 1.0, 5), dur, c)

    if name == "eater":
        ex, ey = 70, 70
        gx, gy = ex - 12, ey - 12
        def mk():
            w = World(140, 140); w.place("glider", gx - 40, gy - 40).place("eater", ex, ey); return w
        # find contact/recovery gens by pre-simulation
        w = mk(); pops = []
        for _ in range(260):
            w.step(); pops.append(int(w.cells.sum()))
        contact = next(i for i, p in enumerate(pops) if p != 12) + 1
        recover = next(i for i in range(contact, 260) if all(p == 7 for p in pops[i:i + 8])) + 1
        approach_end = contact - 3
        gen = keys_gen([(0, 0), (S(2), approach_end - 18), (E(2) + 1.2, approach_end), (E(2) + 2.0, contact),
                        (S(3) - 0.2, recover), (dur, recover + 6)])
        L = Layer(mk, 0, 0, gen)
        def gpos(t):
            g = gen(t); return gx - 40 + 1 + g / 4, gy - 40 + 1 + g / 4
        def cam(t):
            x0, y0 = gpos(t)
            mx, my = (x0 + ex + 1.5) / 2, (y0 + ey + 1.5) / 2
            u1 = ease((t - S(0) - 0.2) / 2.2)          # pull back: reveal the eater ahead
            u2 = ease((t - S(1) - 0.1) / 2.0)          # push in on the eater
            x = x0 * (1 - u1) + mx * u1; y = y0 * (1 - u1) + my * u1
            x1, y1 = ex + 1.5, ey + 1.5 - 1.5 * ease((t - E(2)) / 1.5)
            x = x * (1 - u2) + x1 * u2; y = y * (1 - u2) + y1 * u2
            z = float(np.exp(np.log(42) * (1 - u1) + np.log(10) * u1))
            z = float(np.exp(np.log(z) * (1 - u2) + np.log(50) * u2))
            z *= 1 + 0.25 * ease((t - E(2) - 3.0) / max(1.0, dur - E(2) - 3.0))
            return dict(cx=x, cy=y, z=z, rot=0.0)
        sc = Scene(name, (140, 140), [L], handheld(cam, 0.8, 6), dur, c)
        sc.contact_gen, sc.gen_fn = contact, gen
        return sc

    if name == "gun":
        pre = 1200
        L = Layer(lambda: World(900, 900).place("gosper", 20, 20), 0, 0, lambda t: pre + t * 8)
        gcx, gcy = 38, 25
        def front(t):
            g = pre + t * 8; return 20 + 24 + g / 4 * 0.98, 20 + 8 + g / 4 * 0.98
        def cam(t):
            k = keycam([(0, gcx, gcy, 22, 0.0), (S(1), gcx + 2, gcy + 2, 22, 0.0), (E(1), gcx + 10, gcy + 10, 18, 0.0),
                        (S(2) + 2.2, 170, 160, 2.1, 0.0), (S(3), 190, 180, 2.0, 0.0), (dur, 0, 0, 5.0, 0.0)])(t)
            if t > S(3):
                fx, fy = front(t); u = ease((t - S(3)) / (dur - S(3)))
                k["cx"] = 190 * (1 - u) + (fx - 25) * u; k["cy"] = 180 * (1 - u) + (fy - 25) * u
            return k
        return Scene(name, (900, 900), [L], handheld(cam, 1.0, 7), dur, c)

    if name == "rpent":
        cx_, cy_ = 600, 600
        g_end = 1103
        ta, tb = S(4) - 0.3, S(5) + 0.2      # the close-ups of the neighbours being hit
        gen = keys_gen([(0, 0), (S(2) + 0.3, 0), (E(2), 12), (S(3), 300), (ta, 634), ((ta + tb) / 2, 689.5), (tb, 745),
                        (S(6) + 0.3, g_end), (S(6) + 2.0, g_end + 2), (dur, g_end + 2 + 1.4 * (dur - S(6) - 2))])
        def t_of(gv):
            lo, hi = 0.0, dur
            for _ in range(40):
                mid = (lo + hi) / 2
                if gen(mid) < gv: lo = mid
                else: hi = mid
            return hi
        HITS = [("blinker", 648), ("beehive", 691), ("block", 731)]
        shots = [(ta, 471 + 1.5, 483 + 0.5), (t_of(677), 735 + 2, 440 + 1.5), (t_of(717), 742 + 1, 750 + 1)]
        hit_times = [t_of(g) for _, g in HITS]
        # the neighbours: earlier cast members placed on the paths of escaping gliders (verified: the core still
        # settles exactly as the lone R-pentomino does at gen 1103; each neighbour is hit between gen 645 and 725)
        CAST = {"beehive": (735, 440), "blinker": (471, 483), "block": (742, 750)}
        def mk():
            w = World(1200, 1200).place("rpent", cx_ - 1, cy_ - 1)
            for nm, (x, y) in CAST.items():
                w.place(nm, x, y); w.age[y - 1:y + 5, x - 1:x + 5] = 200
            return w
        L = Layer(mk, 0, 0, gen)
        # find a blinker in the final debris for the push-in
        w = World(1200, 1200).place("rpent", cx_ - 1, cy_ - 1)
        for _ in range(g_end):
            w.step()
        a = w.cells.copy()
        w2 = World(1200, 1200); w2.cells = a.copy(); w2.step()
        changing = np.argwhere(a != w2.cells)
        near = changing[np.argsort(np.hypot(changing[:, 0] - cy_, changing[:, 1] - cx_))]
        by, bx = (near[0] if len(near) else (cy_, cx_))
        live = np.argwhere(a); ccy, ccx = live.mean(0) if len(live) else (cy_, cx_)
        dyy, dxx = np.argwhere(a[cy_ - 150:cy_ + 150, cx_ - 150:cx_ + 150]).mean(0) + np.array([cy_ - 150, cx_ - 150])
        cam = handheld(keycam([
            (0, cx_ + 0.5, cy_ + 0.5, 56, 0.0), (S(2), cx_ + 0.5, cy_ + 0.5, 60, 0.0), (E(2) + 0.4, cx_ + 2, cy_ + 2, 13.0, 0.0),
            (S(3) - 0.5, dxx, dyy, 6.5, 0.0), (ta, dxx, dyy, 5.4, 0.0), (tb, dxx, dyy, 4.6, 0.0), (S(6), dxx, dyy, 4.4, 0.0),
            (S(7) + 0.2, bx + 0.5, by + 0.5, 16, 0.0), (E(7) + 0.4, bx + 0.5, by + 0.5, 18, 0.0),
            (S(8) + 2.2, dxx, dyy, 3.6, 0.0), (dur, dxx, dyy, 3.2, 0.0)]), 1.2, 8)
        base_cam = cam
        def cam2(t):
            if ta <= t < tb:  # hard cuts between three close-ups
                i = max(k for k in range(3) if t >= shots[k][0])
                t0 = shots[i][0]; t1 = shots[i + 1][0] if i < 2 else tb
                u = (t - t0) / max(1e-3, t1 - t0)
                d = base_cam(t)
                d.update(cx=shots[i][1] - 0.6 * (1 - u), cy=shots[i][2] - 0.6 * (1 - u), z=19 + 5 * u, rot=0.0)
                return d
            return base_cam(t)
        ov = lambda t, cam, gens: [("counter", "GENERATION", gens[0], E(2) - 0.5, S(7) + 0.4)]
        sc = Scene(name, (1200, 1200), [L], cam2, dur, c, overlays=ov, fade_out=1.0)
        sc.hit_times = hit_times
        return sc

    if name == "end":
        def island():
            path = os.path.join(CACHE, "island_v1.npz")
            if os.path.exists(path):
                d = np.load(path); w = World(300, 300); w.cells = d["c"]; w.age = d["a"]; return w
            r = np.random.default_rng(77); w = World(300, 300)
            yy, xx = np.mgrid[0:300, 0:300]
            ang = np.arctan2(yy - 150, xx - 150)
            rad = 78 + 12 * np.sin(3 * ang + 1) + 8 * np.sin(5 * ang)
            w.cells = (np.hypot(xx - 150, yy - 150) < rad) & (r.random((300, 300)) < 0.34)
            for _ in range(2500):
                w.step()
            w.cells[:20] = False; w.cells[-20:] = False; w.cells[:, :20] = False; w.cells[:, -20:] = False
            np.savez_compressed(path, c=w.cells, a=w.age)
            return w
        gx0, gy0 = 262, 262
        ix, iy = 0, 0
        L = Layer(lambda: World(1600, 1600).place("glider", gx0, gy0), 0, 0, rate(7.0, 0, 560))
        I = Layer(island, ix, iy, rate(0.9))
        def cam(t):
            g = 560 + 7.0 * t
            u = ease(t / dur)
            z = float(np.exp(np.log(44) + (np.log(1.1) - np.log(44)) * u))
            gx, gy = gx0 + 1 + g / 4, gy0 + 1 + g / 4
            k = 0.55 * u ** 2.6  # the island (centre 150,150) drifts in from the upper left
            return dict(cx=gx * (1 - k) + 150 * k, cy=gy * (1 - k) + 150 * k, z=z, rot=0.0)
        def ov(t, cam_, gens):
            g = 560 + 7.0 * t
            return [("spark", gx0 + 1 + g / 4, gy0 + 1 + g / 4, 0.0, dur + 1)]
        return Scene(name, (1600, 1600), [I, L], handheld(cam, 1.0, 9), dur, c, overlays=ov, fade_out=2.6, focus=lambda t: None)

    if name == "credits":
        items = [("title", "PLANET  B3/S23", 0.5, 4.3),
                 ("caption", "The law  ·  John Horton Conway, 1970", 4.6, dur - 0.2, 440, 52),
                 ("caption", "No cells were harmed.  Several thousand died of loneliness.", 5.6, dur - 0.2, 540, 44)]
        sc = Scene(name, (8, 8), [], lambda t: dict(cx=4, cy=4, z=10, rot=0), dur, c, overlays=lambda t, cam, g: items, fade_in=0, fade_out=0, dust=False)
        sc.black = True
        return sc

    if name == "sting":
        contact = _sting_geom()
        g0 = contact - 23
        gen = lambda t: g0 + STING_RATE * t
        L = Layer(lambda: World(200, 200).place("glider", 40, 40).place("eater", 60, 60), 0, 0, gen)
        t_contact = (contact - g0) / STING_RATE
        def cam(t):
            g = min(gen(t), contact - 2)
            u = ease((t - t_contact + 1.2) / 1.6)
            gx, gy = 40 + 1 + g / 4, 40 + 1 + g / 4
            return dict(cx=gx * (1 - u) + 61.5 * u, cy=gy * (1 - u) + 61.5 * u, z=34 + 8 * u, rot=0.0)
        sc = Scene(name, (200, 200), [L], handheld(cam, 0.8, 10), dur, c, fade_in=0.6, fade_out=0.0)
        sc.t_contact = t_contact
        return sc

    raise KeyError(name)
