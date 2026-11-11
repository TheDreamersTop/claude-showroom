"""Decode the AAC in a final mp4 and cross-correlate against the mastered wav at several points.
usage: python check_sync.py film.mp4 film_mix.wav"""
import sys, subprocess, numpy as np, soundfile as sf
mp4, wav = sys.argv[1], sys.argv[2]
ref, sr = sf.read(wav)
ref = ref.mean(1) if ref.ndim > 1 else ref
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'], capture_output=True).stdout
dec = np.frombuffer(raw, np.float32)
print(f'ref {len(ref)/sr:.2f}s  decoded {len(dec)/sr:.2f}s')
for t in (5, 20, 40, 60, 78):
    i = int(t * sr); n = int(0.5 * sr); w = int(0.05 * sr)
    a = ref[i:i + n]
    b = dec[i - w:i + n + w]
    if len(a) < n or len(b) < n + 2 * w or np.abs(a).max() < 1e-4:
        print(t, 'skip'); continue
    c = np.correlate(b, a, 'valid')
    k = int(np.argmax(c)) - w
    corr = np.corrcoef(a, b[w + k:w + k + n])[0, 1]
    print(f't={t:3d}s lag={k / sr * 1000:6.2f} ms corr={corr:.4f}')
