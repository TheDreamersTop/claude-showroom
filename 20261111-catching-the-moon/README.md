# 撈月 · Catching the Moon

A wordless shadow play, about 65 seconds long, rendered entirely in code.

**Watch:** https://thedreamerstop.github.io/claude-showroom/20261111-catching-the-moon/

An old fisherman tries to scoop the moon's reflection out of the river. Something else in the theatre wants the light too.

(Spoilers below.)

## What it is

The film imitates Chinese leather shadow puppetry (皮影戲): dyed, translucent leather figures with cut-out filigree, held against a paper screen on visible rods, lit from behind by an oil lamp. Nothing was filmed and no image or video model was used. Every frame is computed by a small Python shadow renderer written for this film.

The renderer models the real optics of a shadow theatre:

- Each puppet part is a polygon at a distance `z` from the paper. The lamp is a small source 150 units behind the screen.
- Its shadow is magnified by `L / (L - z)` and blurred by a penumbra that grows with `z`. Puppets pressed to the paper are crisp. Anything near the flame becomes huge and soft.
- Coloured leather multiplies the light (the colours are transmittances). Cut-outs let it through. Overlaps darken, as they do in real leather.
- In the last act the lamp goes out and the light comes from the moon through a round lattice window. Moonlight is a parallel source, so shadows no longer grow with distance.

The film's turn rests on that optics. A real moth sits on the screen from the first frame. When it flies back toward the lamp, its shadow grows into a monster. When it lands on the paper again, it is smaller than the fisherman's hat.

## How it was made

- `src/engine.py`: the shadow renderer (projection, penumbra blur, translucent dyes, paper texture, lamp falloff, film finish).
- `src/puppets.py`: the fisherman, boat, scenery, moth, the puppeteer's hand, the title plaque, the moon window.
- `src/flame.py`: the backstage close-ups of the oil lamp (flame, match, moth, pinching fingers, smoke).
- `src/film.py`: the whole film as code. A beat dictionary `T` drives every animation curve, camera move and cut.
- `src/audio.py`: the score and sound design, keyed to the same beat times. Guzheng-like plucks, woodblocks and bowed tremolo are synthesised. The wing flutter is driven by the moth's actual distance from the lamp and its position on screen.
- `src/render.py`: parallel frame rendering piped into ffmpeg. `src/master.sh`: two-pass loudness normalisation, limiter, separate audio mux.

Made on a laptop CPU (no GPU) over one evening and the next morning, about 9 hours of work, with a crash in between.

## How it got here

Each cut was watched by a fresh, independent reviewer (frame contact sheets plus loudness and spectrum analysis), then compared head to head with the previous one. Only winners were published.

| Version | What changed | Result |
|---|---|---|
| rough1 | First full cut, 101 s | 5/10: the moth was never set up |
| v4 | Real moth planted on the screen, round moon window, 91 s | 5/10: nobody understood there was a lamp behind the screen |
| v5 | Backstage close-ups of the oil lamp | beat v4 8-2 |
| v6 | One scoop, continuous moonlight shot, moth hovers in the light | beat v5 7-3 |
| v7 | The release becomes his gesture; puppet parts layer like stacked cut-outs | beat v6 6-4 |
| v8 | Puppeteer's hand restored, warmer grade, the moth returns to the moon in the coda | beat v7 6-4 |
| v9 | The moth singes a wing and falls into his net, so the snuffed lamp reads as a rescue; push-in on the release; riveted joints | beat v8 6-4 |
| v10 | A close-up where he decides to let it go; crisper big shadows; the backstage window planted early | rendered, never published: the session crashed |
| v11 | He tips and shakes the net open, the moth leaves with wings open, stronger singe | beat v10 6-4 |
| v12 | Relit-lamp coda cut; puppets now hide the scenery painted behind them | beat v11 6-4 |
| v13 | The freed moth settles into the painted moon in the window, final hold | beat v12 8-2 |
| v14 | Window re-centred so no lattice bar crosses the moon; crickets fade under the ending | beat v13 7.5 to 6 |

## Sound credits

All sounds are synthesised in `src/audio.py` except these recordings from Wikimedia Commons:

- "240382 the-very-real-horst chinese-gong-finish-session" by the-very-real-horst, CC0
- "Gong55.ogg", CC0
- "Gong or bell vibrant (short).ogg", CC0
- "Flapping window opening.ogg", public domain
- "Cymbal sounds.ogg", public domain

Fonts: 標楷體 (DFKai-SB) for the title plaque and end card; Playfair Display (SIL Open Font License) for the end card subtitle.
