"""Kokoro TTS lines -> audio/vo/<key>.wav (24 kHz mono)."""
import sys, os, soundfile as sf
from kokoro_onnx import Kokoro
T = '/home/pmli/workspace/claude-showroom/tools'
OUT = os.path.join(os.path.dirname(__file__), '..', 'audio', 'vo')
k = Kokoro(os.path.join(T, 'kokoro-v1.0.onnx'), os.path.join(T, 'voices-v1.0.bin'))
LINES = {
    'mom58':   ('af_sarah',  "Don't you spoil your supper!", 1.0, 'en-us'),
    'her66':   ('af_heart',  "Two straws?", 0.95, 'en-us'),
    'him66':   ('am_michael', "Two straws.", 0.9, 'en-us'),
    'kiss_a':  ('am_adam',   "Kiss! Kiss! Kiss!", 1.15, 'en-us'),
    'kiss_b':  ('af_bella',  "Kiss! Kiss! Kiss!", 1.12, 'en-us'),
    'kiss_c':  ('am_eric',   "Kiss! Kiss! Kiss!", 1.18, 'en-us'),
    'kiss_d':  ('af_nicole', "Kiss! Kiss! Kiss!", 1.1, 'en-us'),
    'kiss_e':  ('bm_lewis',  "Kiss! Kiss! Kiss!", 1.14, 'en-gb'),
    'kiss_f':  ('af_sky',    "Kiss! Kiss! Kiss!", 1.16, 'en-us'),
    'her87':   ('af_heart',  "She's asleep.", 0.85, 'en-us'),
    'him87':   ('am_michael', "Finally.", 0.85, 'en-us'),
    'her26':   ('af_heart',  "Two straws?", 0.82, 'en-us'),
    'him26':   ('am_michael', "Two straws.", 0.78, 'en-us'),
    'him26b':  ('am_michael', "Hasn't changed a bit.", 0.82, 'en-us'),
    'her26b':  ('af_heart',  "Neither have you.", 0.82, 'en-us'),
    'vo1':     ('bm_george', "Some things never go flat.", 0.88, 'en-gb'),
    'vo2':     ('bm_george', "Larkin's. Still fizzing.", 0.86, 'en-gb'),
}
if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    keys = sys.argv[1:] or list(LINES)
    print(k.get_voices())
    for key in keys:
        v, text, speed, lang = LINES[key]
        s, sr = k.create(text, voice=v, speed=speed, lang=lang)
        sf.write(os.path.join(OUT, key + '.wav'), s, sr)
        print(key, sr, round(len(s) / sr, 2))
