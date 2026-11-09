# Planet B3/S23 · B3/S23 星球

A wildlife documentary filmed in a very small world. Made by Claude during an ~8-hour autonomous video challenge (2026-11-09, Taipei time).

▶ **Watch:** https://thedreamerstop.github.io/claude-showroom/20261109-planet-b3s23/

Current file: `film.mp4` (3:48, 1920×1080, H.264 / AAC, about −16 LUFS). Poster: `poster.jpg`. Stay through the credits.

## The idea (spoilers, watch first)

A hushed British nature documentary whose wildlife is Conway's Game of Life. Rule B3/S23: an empty cell with exactly three
neighbours is born, a living cell with two or three neighbours survives, every other cell dies. The film treats the
patterns as animals: the block that has "done nothing for eleven thousand generations" and is "by every measure, thriving",
the glider that travels by falling apart, the eater that simply waits, the Gosper glider gun that sends her children into
the dark, and the R-pentomino, five cells that burn for 1,103 generations.

Everything shown is a true simulation of the rules. Nothing is hand-animated.

- The R-pentomino really stabilises at generation 1,103. In the film it also destroys three neighbours (a blinker, a
  beehive and a block) placed on the paths of the gliders it throws off. That placement was checked: the core of the
  explosion is cell-for-cell identical at generation 1,103 to the lone R-pentomino.
- The eater really swallows the glider and is whole again four generations later.
- The generation counter is the real generation of the world on screen.

## How it was made

- **Simulation** (`src/life.py`): a NumPy Life engine plus a pattern library.
- **Scenes** (`src/scenes.py`): each scene is a set of worlds, a generation schedule and a camera path, timed to the narration.
- **Camera** (`src/look.py`, `src/render.py`): every cell is drawn as a soft glowing body (white when newborn, aqua when young,
  amber when old), with births and deaths blended between generations, tilt-shift depth of field, drifting dust, a
  handheld wobble, bloom and light grain. Rendered in parallel at 720p and upscaled to 1080p.
- **Narration** (`src/script.py`, `src/tts.py`): Kokoro (open-source TTS, voice `bm_george`), running locally. Every line was
  checked with a local Whisper speech recogniser, and three lines were rephrased after it misheard them.
- **Sound** (`src/audio.py`): the score is synthesized in NumPy (pads, plucks, bells, a flute-like glider theme). Every birth
  on screen plays a soft pentatonic note panned to where it happened, so busy scenes sparkle and the explosion crackles.
  Eaten things crunch.
- **Assembly** (`src/assemble.py`): concat, two-pass loudness normalisation, H.264.

## Revisions

- v1 (4:02) was reviewed by an independent agent from frame sheets and the timed script. Main changes for v2: the
  R-pentomino now visibly consumes earlier cast members (it had nothing to destroy); about 15 s trimmed; the glider walks
  across a held frame instead of sitting in the centre; larger counter, title and credits; three lines rewritten
  ("She has sent thousands. None have written."); the post-credits glider gets its theme back, cut off by the crunch.
- The first encode was 1 GB because of heavy film grain; the grain was cut 4× and the film re-rendered.
- A second independent review of v2 found the ending glider shrinking to a single pixel under the final line, and a
  blank frame in the rules scene. v3 keeps the last glider a readable five-cell shape and holds on the block while the
  rule is spoken.

## Files

- `film.mp4`, `poster.jpg`, `index.html`
- `src/`: every script needed to rebuild the film (models not included: Kokoro v1.0 ONNX from thewh1teagle/kokoro-onnx)
- `docs/STATE.md`: working log

Made by Claude (Anthropic) in one autonomous session.
