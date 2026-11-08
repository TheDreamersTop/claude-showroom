"""Audio checks without ears: clicks (sample jumps), per-second RMS level per channel, DC steps."""
import sys, json
import numpy as np
from scipy.io import wavfile
sr, a = wavfile.read(sys.argv[1])
meta = json.load(open(sys.argv[1] + '.json'))
d = np.abs(np.diff(a, axis=0)).max(1)
idx = np.where(d > 0.08)[0]
# group clicks
groups = []
for i in idx:
    if not groups or i - groups[-1][-1] > sr * 0.05:
        groups.append([i])
    else:
        groups[-1].append(i)
print('big jumps (>0.08/sample):', len(groups))
for g in groups[:40]:
    print('  t=%.3f  n=%d  max=%.3f' % (g[0] / sr, len(g), d[g].max()))
sec = len(a) // sr
hp = a - np.array([np.convolve(a[:, c], np.ones(2400) / 2400, mode='same') for c in range(2)]).T
rms = [20 * np.log10(np.sqrt((hp[i * sr:(i + 1) * sr] ** 2).mean(0)) + 1e-9) for i in range(sec)]
tl = dict((round(s), n) for n, s in meta['timeline'])
print('sec   L dB   R dB')
for i, r in enumerate(rms):
    print('%3d %6.1f %6.1f %s' % (i, r[0], r[1], tl.get(i, '')))
