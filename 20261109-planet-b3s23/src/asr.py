import sys, numpy as np, soundfile as sf
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8")
def load16k(f):
    x, sr = sf.read(f, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    n = int(len(x) * 16000 / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
for f in sys.argv[1:]:
    segs, _ = m.transcribe(load16k(f), beam_size=5)
    import os; print(os.path.basename(f), "=>", " ".join(s.text.strip() for s in segs), flush=True)
