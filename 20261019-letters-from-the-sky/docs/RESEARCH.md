# RESEARCH — visual references & Visual Quality Benchmark

(09:40–10:00 UTC. Web search used for facts; analysis from studying these works.)

## References analysed

| # | Work | Why the first frame lands | Lesson to steal |
|---|---|---|---|
| 1 | **Igloo Inc** (Awwwards SOTY 2024, Bureaux/abeto) | One crystalline object in a near-black void; frosted ice, refraction, a slow fluid sim. Restraint, a single subject, almost no UI. | One hero object, centred, lit from behind. Ice reads "premium" when it has thickness, inner edges and caustic glints, not when it is a flat white shape. |
| 2 | **Lusion.co / Active Theory** | Cinematic camera, depth of field, film grain, slow eased motion. Nothing moves linearly. | Bokeh + grain + vignette make CG feel photographic. Every motion is eased; cameras breathe. |
| 3 | **Bruno Simon's portfolio** | You *do* something in the first 2 s (drive) and the world responds physically. | Instant agency beats instructions. |
| 4 | **teamLab installations** | The world reacts to your presence and *grows* (flowers bloom, scatter). Kids get it instantly. | Growth triggered by the visitor is universally readable. |
| 5 | **Nervous System – Floraform / Hyphae** | Generative growth that *looks like nature* because it IS a model of nature. | Scientific models produce forms with credibility you can't fake with noise. |
| 6 | **Gravner–Griffeath "snowfakes" (2008–09)** | A 7-parameter lattice model of vapour diffusion + attachment produces flakes that are indistinguishable from Libbrecht's photos: ridges, sector plates, ribs, dendrites. | A real physical model gives endless, plausible variety. |
| 7 | **Kenneth Libbrecht / Alexey Kljatov snow macro photos** | Backlit ice on dark wool or glass: crystals glow with inner ridges, colour fringes from thickness and chromatic aberration, shallow DOF. Every viewer has felt "no two are alike". | The look target: macro photography, not 3D-modelling. Inner relief (thickness) catches light; the outline alone is boring. |
| 8 | **Nakaya ("hieroglyphs sent from the sky")** | A snowflake's shape is a record of the temperature & humidity it fell through: plates near −2 °C, needles −5 °C, plates/dendrites −15 °C. | Narrative hook: *the path you steer IS the shape you get*. |
| 9 | **Evan Wallace WebGL Water / Shadertoy (iq)** | Light-transport tricks (caustics, refraction) are what make people stop. | Use light physics (refraction, dispersion, glints) as the main visual language. |
| 10 | **Inigo Quilez "Happy Jumping", Rainforest** | Composition & lighting matter more than polycount: key/fill/rim, fog, colour grading. | Strict palette + colour grade. |

## Distilled design principles
1. **One subject, framed like a photograph.** Centre the hero on a dark field, shallow depth, warm/cool contrast.
2. **Light is the material.** Refraction, glints, chromatic fringes, bloom-but-restrained.
3. **Growth the user causes.** The thing in front of you is being made *by you*, live, and is unique.
4. **Science gives credibility.** Use the real model, and show it subtly (e.g. the conditions being "recorded").
5. **No text walls.** One line of hint; the rest is discovered.
6. **Cinematic finishing:** grain, vignette, eased camera, DOF, sound-free but rhythmic motion.

## Visual Quality Benchmark (what "good enough" means for this project)
- B1: A screenshot of the hero frame could pass, at a glance, as a stylised macro photograph / premium title card. Not a "WebGL demo".
- B2: Hero object has ≥3 levels of detail visible at 1600×900 (silhouette → branches → inner ridges/relief).
- B3: Palette is controlled (≤3 hues + neutrals), consistent across all states.
- B4: Motion: nothing pops; all transitions eased ≥300 ms; camera has subtle life.
- B5: First interaction within 3 s without reading anything.
- B6: Each session produces a different, collectable result (memorability/shareability).
- B7: 60 fps-class on a desktop GPU; graceful in SwiftShader for validation.

## Insights gained while building (for whoever continues this)
- **GG parameter sets are not labelled by what they grow.** The famous "ρ=.38 β=1.06 …" set grows *open stellar dendrites*, and "ρ=.8 β=2.6" grows the *plate*. Always sweep (tools/explore.html) before mapping weather to parameters.
- **Blends of very different parameter sets grow mush.** Sharpened weights (w^2.2, normalised) keep each region of the pointer space in one habit, and transitions then happen in time (as you steer), not in parameter space.
- **The scissored active region is a boundary condition**, not just an optimisation. Its edge acts as a vapour source at ρ. If its size depends on frame timing, growth rate and morphology do too. Make it a deterministic function of the crystal radius (measured on the GPU at least every 128 steps) and fill newly activated cells with the current ρ.
- **Dark-field lighting is what makes clear ice visible.** A transparent plate on a smooth backlight shows nothing (physically right, visually dead). Let the edge orientation pick between off-axis coloured lamps.
- **Hexagonal lattices need triangle interpolation.** Bilinear sampling in skewed axial coordinates staircases every facet that isn't on one axis.
- **Twins are a superb test oracle.** Replaying a journey with a different noise seed should give a near-identical crystal. When it didn't, the comparison exposed two physics bugs: clipping by the active region, and starved or over-fed vapour.
