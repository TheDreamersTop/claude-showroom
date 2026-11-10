"""Synthesised score + sound design for VESPER 61. Writes audio/score.wav and audio/sfx.wav (48 kHz stereo).
Timeline comes from edit.json (cut points) so music hits the picture."""
import numpy as np, json, os, wave
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SR = 48000
E = json.load(open(os.path.join(ROOT, 'edit.json'), encoding='utf-8'))
T = E['total']
N = int(T*SR) + SR*4
rng = np.random.default_rng(7)
def t_(n): return np.arange(n)/SR
def midi(m): return 440.0*2**((m - 69)/12)
def env_adsr(n, a, d, s, r, sus_len):
    e = np.zeros(n); ia, idd, isus, ir = int(a*SR), int(d*SR), int(sus_len*SR), int(r*SR)
    seg = [np.linspace(0, 1, max(ia, 1)), np.linspace(1, s, max(idd, 1)), np.full(max(isus, 1), s), np.linspace(s, 0, max(ir, 1))]
    x = np.concatenate(seg)[:n]; e[:len(x)] = x; return e
def _lp_fast(x, fc):
    """one-pole low-pass; fc in Hz (values < 1 are taken as the pole coefficient)."""
    a = fc if fc < 1 else np.exp(-2*np.pi*fc/SR)
    Lk = int(min(len(x), 10/(1 - a) + 1))
    k = (1 - a)*a**np.arange(Lk)
    n = len(x) + Lk
    nf = 1 << int(np.ceil(np.log2(n)))
    return np.fft.irfft(np.fft.rfft(x, nf)*np.fft.rfft(k, nf), nf)[:len(x)]
def hp(x, fc): return x - _lp_fast(x, fc)
def place(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0*SR); n = min(len(sig), buf.shape[0] - i)
    if n <= 0: return
    l, r = np.cos((pan + 1)*np.pi/4), np.sin((pan + 1)*np.pi/4)
    if sig.ndim == 1:
        buf[i:i + n, 0] += sig[:n]*gain*l*1.414; buf[i:i + n, 1] += sig[:n]*gain*r*1.414
    else:
        buf[i:i + n] += sig[:n]*gain

def piano(m, dur=4.0, vel=0.6):
    f = midi(m); n = int((dur + 2.5)*SR); t = t_(n); y = np.zeros(n)
    B = 0.0004
    for k in range(1, 14):
        fk = f*k*np.sqrt(1 + B*k*k)
        if fk > 16000: break
        amp = (1/k**1.1)*(1 + 0.5*np.sin(k*1.7))
        dec = 1.2 + 6.0*(k/14) + f/400
        y += amp*np.sin(2*np.pi*fk*t + rng.uniform(0, 6))*np.exp(-t*dec*0.35)
    y *= np.minimum(1, t/0.004)
    y *= np.where(t < dur, 1, np.exp(-(t - dur)*6))
    ham = rng.normal(size=n)*np.exp(-t*80)*0.05
    y = (y + _lp_fast(ham, 0.6))*vel
    return y/6

def pad(ms, dur, att=2.0, rel=3.0, bright=1800, det=0.08):
    n = int((dur + rel)*SR); t = t_(n); out = np.zeros((n, 2))
    for m in ms:
        f = midi(m)
        for v in range(5):
            dt = (v - 2)*det
            ff = f*2**(dt/12)*(1 + 0.003*np.sin(2*np.pi*(4.8 + v*0.3)*t))
            ph = np.cumsum(ff)/SR
            saw = 2*(ph % 1) - 1
            ch = v % 2
            out[:, ch] += saw*(0.6 if v != 2 else 1.0)
            out[:, 1 - ch] += saw*0.3
    e = env_adsr(n, att, 0.5, 0.85, rel, dur - att - 0.5)
    for c in range(2):
        out[:, c] = _lp_fast(_lp_fast(out[:, c], bright), bright*1.3)*e
    return out/(len(ms)*8)

def sub(f, dur, att=1.0, rel=2.0):
    n = int((dur + rel)*SR); t = t_(n)
    return np.sin(2*np.pi*f*t)*env_adsr(n, att, 0.2, 0.9, rel, dur - att - 0.2)

def boom(f0=60, dur=3.0):
    n = int(dur*SR); t = t_(n)
    f = f0*(1 + 1.5*np.exp(-t*18)); ph = np.cumsum(f)/SR
    y = np.sin(2*np.pi*ph)*np.exp(-t*1.6)
    y += _lp_fast(rng.normal(size=n), 300)*np.exp(-t*10)*1.5
    return y

def noise(n): return rng.normal(size=n)

def reverb(x, secs=3.2, wet=0.35, damp=3000):
    n = int(secs*SR); t = t_(n)
    out = np.zeros((x.shape[0] + n, 2))
    for c in range(2):
        ir = noise(n)*np.exp(-t*6.9/secs)
        ir = _lp_fast(ir, damp); ir[:int(0.012*SR)] = 0; ir /= np.sqrt(np.sum(ir**2))
        L = 1 << int(np.ceil(np.log2(x.shape[0] + n)))
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], L)*np.fft.rfft(ir, L), L)[:x.shape[0] + n]
    out[:x.shape[0]] = out[:x.shape[0]]*wet + x*(1 - wet)
    out[x.shape[0]:] *= wet
    return out[:x.shape[0]]

cuts = E['cuts']            # name -> start time
mus = np.zeros((N, 2)); sfx = np.zeros((N, 2))
c = lambda k: cuts[k]

# ---------------- score (D major, 72 bpm feel)
D = 50  # D3
# 1) hangar: drone + sparse high piano
place(mus, pad([D - 12, D - 5], c('h3') + 1.0, att=4.0, rel=3.0, bright=500), 0.0, 0.9)
for tt, m in [(0.8, D + 28), (3.2, D + 33), (5.0, D + 31), (7.4, D + 26), (9.3, D + 28)]:
    place(mus, piano(m, 3.0, 0.45), tt, 1.0, rng.uniform(-0.5, 0.5))
# 2) doors: strings swell, rising
place(mus, pad([D - 12, D, D + 4, D + 7, D + 11], 7.5, att=5.0, rel=2.5, bright=1200), c('h3') - 0.5, 1.1)
place(mus, sub(36.7, 7.0, 4.0, 1.5), c('h3'), 0.06)
# 3) takeoff onward: progression, piano arpeggios
prog = [([D - 12, D, D + 4, D + 7, D + 9, D + 14], D - 24),      # Dmaj6/9
        ([D - 15, D - 3, D + 2, D + 5, D + 9, D + 12], D - 27),  # Bm7
        ([D - 19, D - 7, D + 2, D + 7, D + 11, D + 14], D - 31),  # Gmaj7
        ([D - 17, D - 5, D + 2, D + 7, D + 9, D + 14], D - 29)]  # A sus/add9
bar = 60/72*4
t0 = c('r1') - 0.1; tend = c('end') - 0.2
k = 0; tt = t0
while tt < tend - 0.5:
    ch, bass = prog[k % 4]
    L = min(bar*2, tend - tt)
    drop = c('c4') + 1.0 <= tt < c('c5') + 7.0   # thin out under the reveal VO
    place(mus, pad(ch, L, att=1.2 if k else 0.4, rel=2.0, bright=900 if drop else 2200), tt, 0.7 if drop else 1.0)
    place(mus, sub(midi(bass + 12), L, 0.3, 1.0), tt, 0.045)
    arp = [ch[2] + 12, ch[3] + 12, ch[4] + 12, ch[5] + 12, ch[4] + 12, ch[3] + 12]
    step = bar/4
    for j in range(int(L/step)):
        if drop and j % 2: continue
        place(mus, piano(arp[j % len(arp)], 1.6, 0.35 + 0.1*(j % 4 == 0)), tt + j*step, 0.9, np.sin(j)*0.5)
    tt += L; k += 1
# booms on key cuts
for key in ('r1', 'c1', 'c6'):
    place(mus, boom(55, 3.0), c(key) - 0.02, 0.18)
# 4) hero swell into the end card and a final resolving chord
place(mus, pad([D - 24, D - 12, D, D + 4, D + 7, D + 11, D + 16], 5.0, att=3.5, rel=1.5, bright=3500), c('c6'), 1.2)
place(mus, pad([D - 12, D - 5, D + 4, D + 9, D + 14], 6.0, att=0.8, rel=5.0, bright=1600), c('end'), 0.9)
place(mus, piano(D + 26, 6, 0.6), c('end') + 0.05, 1.0); place(mus, piano(D + 14, 6, 0.5), c('end') + 0.05, 1.0)
place(mus, piano(D + 33, 5, 0.35), c('end') + 1.6, 1.0, 0.3)
pts = [(0, 0.35), (c('h3'), 0.45), (c('r1') - 0.3, 0.75), (c('r1') + 0.5, 1.0), (c('c4'), 0.95), (c('c4') + 1.5, 0.62),
       (c('c6') - 0.8, 0.7), (c('c6') + 1.5, 1.15), (c('end'), 1.0), (T + 4, 0.9)]
gt = np.arange(mus.shape[0])/SR
mus *= np.interp(gt, [p[0] for p in pts], [p[1] for p in pts])[:, None]
mus = reverb(mus, 3.4, 0.38)

# ---------------- sound design
def whoosh(dur=1.6, f0=400, f1=2500):
    n = int(dur*SR); t = t_(n); x = noise(n)
    fc = f0 + (f1 - f0)*np.sin(np.pi*t/dur)**2
    y = np.zeros(n); B = 2400
    for i in range(0, n, B):
        y[i:i + B] = _lp_fast(x[i:i + B], fc[i])
    return hp(y, 120)*np.sin(np.pi*t/dur)**1.5
# light sweeps hum
for key, d in (('h1', 6.5), ('h2', 4.0)):
    n = int(d*SR); t = t_(n)
    hum = (np.sin(2*np.pi*100*t) + 0.3*np.sin(2*np.pi*200*t) + 0.1*np.sin(2*np.pi*300*t))*np.sin(np.pi*t/d)**2
    place(sfx, hum*0.03, c(key) + 0.2); place(sfx, whoosh(d*0.8, 200, 1200)*0.05, c(key) + d*0.1)
# door rumble + clank
n = int(6.5*SR); t = t_(n)
rum = _lp_fast(noise(n), 90)*8*np.minimum(1, t/0.6)*np.exp(-np.maximum(0, t - 5.0)*2)
rum += _lp_fast(noise(n), 900)*0.4*(np.sin(2*np.pi*3.1*t) > 0.7)*np.minimum(1, t)
place(sfx, rum*0.18, c('h3') + 0.5)
place(sfx, boom(90, 1.5)*0.35, c('h3') + 0.55)
# outside wind as the door opens
n = int(7*SR); t = t_(n); place(sfx, hp(_lp_fast(noise(n), 1200), 200)*np.minimum(1, t/4)*0.06, c('h3') + 2.0)
# takeoff roar with doppler-ish sweep
d = 7.0; n = int(d*SR); t = t_(n)
pk = 2.6   # loudest when jet passes camera
g = 1/(1 + ((t - pk)/1.0)**2)
roar = np.zeros(n); x = noise(n); B = 2400
for i in range(0, n, B):
    tt = t[i]; fc = 500 + 2600*g[i]
    roar[i:i + B] = _lp_fast(x[i:i + B], fc)
whine_f = 3800*np.where(t < pk, 1.06, 0.94)*(1 + 0.0*t)
whine = np.sin(2*np.pi*np.cumsum(whine_f)/SR)*0.04
roar = (roar*2.2 + whine)*g*np.minimum(1, t/0.8)
place(sfx, np.stack([roar*np.clip(1.2 - (t/d)*1.0, 0.2, 1.2), roar*np.clip(0.2 + (t/d)*1.0, 0.2, 1.2)], 1)*0.32, c('r1'))
# cruise: steady air rush under every cloud shot, whooshes on cuts
for key in ('c1', 'c2', 'c3', 'c4', 'c5', 'c6'):
    place(sfx, whoosh(1.4, 300, 2200)*0.07, c(key) - 0.6)
n = int((c('end') - c('c1'))*SR); t = t_(n)
air = hp(_lp_fast(noise(n), 700), 150)*0.05*np.minimum(1, t/1.5)*np.minimum(1, (n/SR - t)/1.5)
place(sfx, air, c('c1'))
# end card shimmer
n = int(4*SR); t = t_(n)
sh = sum(np.sin(2*np.pi*midi(m)*t)*np.exp(-t*(1.2 + 0.3*i)) for i, m in enumerate([D + 38, D + 43, D + 45, D + 50]))
place(sfx, sh*0.02, c('end') + 0.4)
sfx = reverb(sfx, 2.0, 0.2)

def write(path, x):
    x = x[:int(T*SR) + SR]
    pk = np.max(np.abs(x)) + 1e-9
    x = x/pk*0.89
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((np.clip(x, -1, 1)*32767).astype('<i2').tobytes())
    print('wrote', path, 'peak', pk)
write(os.path.join(ROOT, 'audio', 'score.wav'), mus)
write(os.path.join(ROOT, 'audio', 'sfx.wav'), sfx)
