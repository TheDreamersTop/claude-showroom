"""Concat scene videos in FILM order, mux out/mix.wav (loudness-normalised), encode out/film_<tag>.mp4.
usage: python assemble.py <tag> [crf]"""
import json, os, subprocess, sys
from scenes import FILM, ROOT, timeline

OUT = os.path.join(ROOT, "out")
tag = sys.argv[1] if len(sys.argv) > 1 else "v1"
crf = sys.argv[2] if len(sys.argv) > 2 else "21"
PRESET = sys.argv[3] if len(sys.argv) > 3 else "slow"
VF = sys.argv[4] if len(sys.argv) > 4 else "null"

_, durs, _ = timeline()
lst = os.path.join(OUT, "film_concat.txt")
with open(lst, "w") as f:
    for s in FILM:
        p = os.path.join(OUT, f"scene_{s}.mp4").replace(os.sep, "/")
        f.write(f"file '{p}'\n")
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                   capture_output=True, text=True).stdout)
        flag = "" if abs(dur - durs[s]) < 0.1 else "   <-- MISMATCH (stale render?)"
        print(f"{s:8s} video {dur:7.2f}s  timeline {durs[s]:7.2f}s{flag}")

# two-pass loudnorm to -16 LUFS / -1.5 dBTP
meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", os.path.join(OUT, "mix.wav"), "-af",
                       "loudnorm=I=-16:TP=-1.5:LRA=14:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
af = (f"loudnorm=I=-16:TP=-1.5:LRA=14:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo")
print("input loudness", j["input_i"], "LUFS, true peak", j["input_tp"])
out = os.path.join(OUT, f"film_{tag}.mp4")
inputs = ["-f", "concat", "-safe", "0", "-i", lst, "-channel_layout", "stereo", "-i", os.path.join(OUT, "mix.wav")]
common = ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", PRESET, "-vf", VF, "-pix_fmt", "yuv420p"]
if crf.startswith("b"):  # two-pass to a fixed video bitrate, e.g. b2900k
    br = crf[1:]
    plog = os.path.join(OUT, "x264pass")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + common + ["-b:v", br, "-pass", "1", "-passlogfile", plog,
                    "-an", "-f", "mp4", os.devnull], check=True)
    vopt = ["-b:v", br, "-maxrate", str(int(br[:-1]) * 2) + "k", "-bufsize", str(int(br[:-1]) * 4) + "k", "-pass", "2", "-passlogfile", plog]
else:
    vopt = ["-crf", crf]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + common + vopt +
               ["-movflags", "+faststart", "-af", af, "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
print("wrote", out, os.path.getsize(out) // 1_000_000, "MB")
