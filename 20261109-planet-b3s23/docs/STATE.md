# Overnight film — working state

Start: 2026-11-09 10:03 UTC (18:03 Taipei). Budget ~8 h → hard stop for delivery ~17:30 UTC.

## Direction
PLANET B3/S23 — a hushed British wildlife documentary filmed inside Conway's Game of Life.
All events are real simulation (B3/S23). Still lifes "thriving", the glider, the eater, the Gosper gun
("she will not see any of them again"), the R-pentomino catastrophe (1103 gens), callback ending.
Pivoted away from first idea (oscilloscope X-Y film) because the showroom already has one (20261108-left-and-right).

## Tools
- Narration: Kokoro TTS (models/), voice bm_george. Intelligibility checked with faster-whisper small.en (src/asr.py).
- Python 3.13 + numpy + opencv + ffmpeg (libx264, aac). No GPU renderer.
- Delivery: TheDreamersTop/claude-showroom (GitHub Pages live, push OK with PAT). Folder 20261109-<slug>.
- Can't listen to audio or watch video directly: checks = frames/contact sheets, ASR, loudness/spectral stats.

## Files
- src/life.py engine (verified: rpent 116 @1103, eater, gun) · src/look.py renderer (720p internal, per-cell bodies at z>=9)
- src/script.py narration · src/tts.py → out/vo · src/scenes.py all scenes + timing from VO cues
- src/render.py (parallel, → out/seg, out/scene_*.mp4; `--stills` for checks) · src/audio.py → out/mix.wav
- FILM = open, law, still, osc, glider, eater, gun, rpent, end, credits, sting (~3:50 total)

## Strongest cut
- v1 (review only): out/film_v1.mp4, 4:02, 720p denoised. Reviewed by independent subagent (notes adopted below).
- v2 full re-render launched 13:54 UTC (render_log4.txt), 3:48.

## v1 → v2 revisions
- Grain cut 4x (v0 was 1 GB / 33 Mbps; GitHub limit 100 MB). Test: 6 Mbps at crf 23 on busiest scene.
- R-pentomino now destroys three earlier cast members (blinker/beehive/block on escaping-glider paths), shown in
  three hard-cut close-ups during "It consumes everything it touches". Verified core still identical at gen 1103.
- Trims (~15 s), bigger counter/credits/title, glider walks across a held frame, ending island in focus,
  sting gets the glider theme cut off by the crunch, 3 narration lines swapped (reviewer suggestions).
- Kept the final "thriving" callback (reviewer suggested replacing; I judged the callback + sting stronger).

## Next action
When render done: python audio.py → python assemble.py v2 <crf> slow → check size <95 MB → review → deliver.
