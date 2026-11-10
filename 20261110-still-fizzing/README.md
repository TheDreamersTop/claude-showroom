# Larkin's · Still Fizzing

**▶ Watch:** https://thedreamerstop.github.io/claude-showroom/20261110-still-fizzing/

A 53-second commercial for a cola that has not changed since 1958, made for older viewers.
一支 53 秒的可樂廣告，拍給長輩看：從 1958 年到今天，味道沒變。

Larkin's is a fictional brand. Every frame and every sound was generated in code during one overnight session (2026-11-10, Taipei time) on a laptop CPU, with no GPU and no image or video generation models.

## The idea (watch first)

One bottle, one framing, one life, told only through what is on the table. No people on screen.

- 1958: a porch, a comic book, marbles, one straw. Mom, from inside: "Don't you spoil your supper!"
- 1966: a diner, cinema tickets, one bottle, two straws. "Two straws?" "Two straws."
- 1974: wedding linen, a ring box, petals. The guests chant "Kiss! Kiss! Kiss!"
- 1987: a kitchen at night, a baby bottle, Lucy's footprint card. "She's asleep." "Finally."
- Today: a pill organizer, a crossword, two pairs of reading glasses, one bottle, two straws. The same two voices, older: "Two straws?" "Two straws." Then: "Hasn't changed a bit." "Neither have you."

Every decade change is cut on the cap's "pssht". The score is one original melody that changes instruments with the decade: radio rock-and-roll sax and brushes (1958), a jukebox tremolo guitar (1966), a 70s string machine (1974), an FM electric piano (1987), solo piano (today), and piano, strings and bells for the product. The jump to today is the only time the cut dissolves, through rising carbonation bubbles with the present refracted inside them.

## How it was made

| Part | Method |
|---|---|
| Bottle, props, sets | Procedural geometry in Blender 4.5 (`src/lib.py`, `src/scenes.py`): lathed glass bottle with a cola volume, crown caps, striped paper straws, reading glasses, ring box, baby bottle, pill organizer, hearing aid, condensation droplets |
| Printed things | Label, comic, tickets, crossword, footprint card, laminates: drawn with PIL (`src/label.py`, `src/textures.py`) |
| Lighting | Poly Haven HDRIs (CC0) as era backdrops, pre-blurred for the out-of-focus background; sun, window and practical lights per decade |
| Render | Cycles on CPU (i7-10750H), 2112×1188 stills at 40 samples with OIDN denoising, about 6 to 9 minutes each. One true animation: the slow-motion cap pop (48 frames, `src/pop_anim.py`) |
| Edit, grade | `src/compose.py`: slow camera pushes on the stills, per-decade colour looks, bloom, grain, dust motes, moving leaf shadows (1958), the bubble transition, titles, end card |
| Score, SFX | Synthesised in numpy/scipy (`src/synth.py`, `src/music.py`): additive piano, FM e-piano, string ensemble, Karplus-style plucks, reed lead, drums, convolution reverb; cap pops, fizz, clinks, cicadas, crickets, clock, diner murmur, applause |
| Voices | Kokoro TTS (open source, local). The older couple is the young couple's voices, lowered and slowed with a slight waver (`src/mix.py`). Every line was checked with a local Whisper recogniser in the final mix |
| Mix | Dialogue ducking, loudness normalised to -16 LUFS |

## Files

- `film.mp4`: the film (1920×1080, 24 fps, H.264 + AAC)
- `poster.jpg`, `shots/`
- `src/`: all scripts (models and HDRIs not included)
