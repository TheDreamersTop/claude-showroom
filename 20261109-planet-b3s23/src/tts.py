"""Render every narration line to out/vo/<scene>_<i>.wav (48 kHz mono), cached by text hash. Writes out/vo/index.json."""
import hashlib, json, os, sys
import numpy as np, soundfile as sf
from script import SCRIPT, ORDER, VOICE, SPEED

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "vo")
os.makedirs(OUT, exist_ok=True)


def resample(x, sr, to=48000):
    n = int(round(len(x) * to / sr))
    X = np.fft.rfft(x)
    Y = np.zeros(n // 2 + 1, complex)
    m = min(len(X), len(Y))
    Y[:m] = X[:m]
    return (np.fft.irfft(Y, n) * (n / len(x))).astype(np.float32)


def trim(x, thr=0.004):
    idx = np.nonzero(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] - 480), min(len(x), idx[-1] + 2400)
    return x[a:b]


def main():
    k = None
    index = {}
    for sc in ORDER:
        for i, (pause, line) in enumerate(SCRIPT[sc]):
            key = hashlib.md5(f"{VOICE}|{SPEED}|{line}".encode()).hexdigest()[:10]
            path = os.path.join(OUT, f"{sc}_{i}_{key}.wav")
            if not os.path.exists(path):
                if k is None:
                    from kokoro_onnx import Kokoro
                    k = Kokoro(os.path.join(ROOT, "models/kokoro-v1.0.onnx"), os.path.join(ROOT, "models/voices-v1.0.bin"))
                s, sr = k.create(line, voice=VOICE, speed=SPEED, lang="en-gb")
                x = trim(resample(np.asarray(s, np.float32), sr))
                sf.write(path, x, 48000, subtype="FLOAT")
            x, _ = sf.read(path, dtype="float32")
            index[f"{sc}:{i}"] = dict(path=path, dur=len(x) / 48000, pause=pause, line=line)
            print(f"{sc}:{i} {len(x)/48000:5.2f}s  {line}", flush=True)
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
