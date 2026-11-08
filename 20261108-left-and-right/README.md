# Left & Right · 左與右

A short film for headphones, made by Claude during an ~8-hour autonomous video challenge (2026-11-08, Taipei time).

> Two voices on one oscilloscope.
> 一台示波器上的兩個聲音。

▶ **Watch:** https://thedreamerstop.github.io/claude-showroom/20261108-left-and-right/

Current file: `film.mp4` (112 s, 1080×1080, H.264 / AAC 320k, about −16 LUFS). Poster: `poster.jpg`.

## The idea (spoilers, watch first)

Every sound in the film draws the picture. The left audio channel moves the beam across the screen, the right
channel moves it up and down, like an analog oscilloscope in X-Y mode. A silent beam is a dot. One voice alone
can only draw a straight line. Two voices in tune draw a still circle; out of tune, a tangle. Together they can
draw anything, and the shape you see is the timbre you hear.

## How it was made

- **Score as code** (`docs/src/score.py`, `sig.py`, `drawings.py`): every scene is a stereo signal built in
  NumPy. Melodies, Lissajous intervals (each figure is the chord you hear), and line drawings traced at the pitch
  of the tune. Stick figures are single closed loops so the beam never jumps inside a body; jumps between figures
  run along a drawn floor so they vanish into it.
- **Picture from sound** (`docs/src/render.py`): a simulated P31 phosphor screen renders every frame from that
  same audio file: DAC oversampling, beam dwell to brightness, fast and slow phosphor decay, bloom.
  Nothing is animated separately.
- **No samples, no voices, no generated footage.** Only the signal, Python, and ffmpeg.
- **Encode:** AAC's stereo shortcuts (intensity stereo, noise substitution, mid/side) smear an X-Y picture,
  so the film uses AAC 320k with all three switched off.
- **Own an oscilloscope?** Feed `soundtrack.flac` (lossless) into X-Y mode, left = X, right = Y.

## Revisions

Five rounds of independent review on the actual cuts (contact sheets and full-resolution frames). Scores rose
5 → 6 → 6.5 → 7 → 7 as the film went from 184 s to 112 s. Notes in `docs/reviews/`, working log in `docs/STATE.md`.

## Files

- `film.mp4`, `poster.jpg`, `soundtrack.flac`, `index.html`
- `docs/src/`: every script (score, signal library, drawings, renderer, assembly, checks)
- `docs/reviews/`, `docs/STATE.md`

Made by Claude (Anthropic) in one autonomous session.
