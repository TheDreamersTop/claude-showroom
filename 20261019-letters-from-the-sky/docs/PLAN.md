# PLAN — Overnight autonomous creative challenge
Start: 2026-10-19 09:35 UTC (17:35 Taipei). Budget ≈ 8 h.

## Deployment decision (user, mid-session)
No remote repo push, no public deploy. Everything stays local in `/home/user/showroom/20261019-<slug>/`
(local clone of the showroom; nothing is pushed). "Deployment" = a static server in this container
(`http-server`) + validation in headless Chromium (SwiftShader WebGL2): fresh session, console errors,
asset loads, interactions, refresh.

## Objective
One single-page, no-build, desktop WebGL2 experience that makes AI experts, adults and kids go "wow" on first sight.
Must differ from the showroom's earlier works (stellar particles, shadow sculpture, erosion canyon, ink vortex).

## Milestones
1. Research + Visual Quality Benchmark (RESEARCH.md)
2. ≥5 candidate concepts → 3 rendered prototypes with screenshots → pick one
3. Hero Moment definition
4. V1 end-to-end + local "deploy" + screenshots
5. Pass 1 Visual escalation (before/after)
6. Pass 2 Experience escalation (before/after)
7. Pass 3 Exceptional polish (before/after)
8. Independent adversarial review(s) by subagent on actual screenshots
9. Final QA + FINAL_REPORT

## Acceptance criteria
See challenge §14. Plus: no console errors, ≥3 meaningful interactions, hero moment captured, ≥3 before/after passes.

## Current state
(updated in PROGRESS.md)

## Phase B — candidate concepts (10:00 UTC)

| # | Concept | Hero Moment | Visual identity | Core interaction | Technical challenge | Emotion | Expansion | Risks |
|---|---|---|---|---|---|---|---|---|
| A | **Hieroglyphs from the Sky** (snowflake) — you steer a newborn ice crystal down through a cloud; temperature & humidity along your path are physically written into its shape (Gravner–Griffeath model on GPU). | The camera pulls back from a single tiny hexagon and a full stellar dendrite crystallises in front of you, branch by branch, in backlit macro light — then it lands on dark wool beside the others you made. | Kljatov/Libbrecht macro photography: indigo night, backlit ice, chromatic fringes, bokeh. | Drag to move through the cloud (altitude = temperature, sideways = humidity); flake responds live. Collect, compare, catch. | GG lattice CA on GPU (thousands of steps), hex lattice, relief/refraction shading from mass fields. | Wonder; "this one is mine and unique". | Collection on a mitten, Nakaya diagram, share code (seeded path), melt with breath. | Parameter tuning to get beautiful flakes; rendering ice convincingly in 2.5D. |
| B | **Lightning in Glass** (Lichtenberg) — charge an acrylic block, touch it with a nail: a 3D fractal discharge burns into it. | Darkness → a crack of white-violet light branching through a glass cube in 300 ms, then it glows and cools to a frozen tree. | Electric violet in black glass; long exposure. | Pick discharge point; pump voltage; rotate block. | 3D dielectric-breakdown model, volumetric glow rendering. | Shock & awe. | Multiple discharges, sculptures. | Interaction ends after the zap; hard to sustain depth. |
| C | **Pop-up Atlas** — a paper book whose pages fold up into 3D paper worlds. | Turning the page: a whole paper city unfolds with real fold mechanics and soft shadows. | Warm paper, papercut, lamp light. | Turn pages, pull tabs. | Constrained fold kinematics, paper shading. | Nostalgia, delight. | Many pages. | Content heavy (needs authored scenes); kinematics hard. |
| D | **Bioluminescent Shore** — night beach, waves glow where touched. | Running finger in surf: blue fire. | Teal glow on black. | Wave touch. | Shallow-water sim. | Calm. | Footprints, boats. | Seen before; similar to ink/fluid works. |
| E | **Murmuration** — 100k starlings at dusk; you are the falcon. | Flock folding like smoke around you. | Dusk gradient, silhouettes. | Fly. | GPU boids. | Awe. | Weather. | Common GPGPU demo. |
| F | **Rose Window** — design a cathedral rose window, sun sweeps the day, coloured light beams cross a dusty nave. | Sunrise through your glass. | Gothic, volumetric light. | Draw tracery. | Volumetric scattering. | Reverence. | Times of day. | Static; not novel enough. |

**Shortlist for prototypes: A, B, C.** (A strongest on universality + science + uniqueness; B on shock; C on charm.)

## Prototype comparison (09:43 UTC) — sheet: `20261019-letters-from-the-sky/shots/prototype-sheet.jpg`
- **A (snow, GG model on GPU)**: worked first try at 384² — the real physics yields fern dendrites, stellar plates with tip plates, sectored plates (a1.jpg, a23.jpg). Shading is naive (aliasing, flat). *Ceiling: very high*: endless unique forms, scientific story, kid-readable, rendering headroom (refraction/dispersion/macro DOF). Risk: render quality and parameter mapping.
- **B (Lichtenberg)**: instantly striking (b1.jpg) but it is a single event; after the zap there is nothing to explore. Looks like "bloom demo". Ceiling: medium.
- **C (pop-up)**: kinematics prototype exposes how much authored art it needs (c12.jpg: geometry orientation wrong, papercraft reads as flat CG). Ceiling high but content-bound; not feasible to reach exceptional in this budget.
**Decision: A.** Title: **天空寄來的信 · Letters from the Sky** (Nakaya Ukichirō: 「雪は天から送られた手紙である」 — "Snow crystals are letters sent from the sky"). Folder `20261019-letters-from-the-sky/`.

## HERO MOMENT
**What you see:** near-black indigo sky; one speck of ice, a tiny hexagonal prism, glints in the middle. You press and hold. The six corners shoot out arms, and each arm sprouts side branches in real time. The crystal is not a white flat icon: it is clear ice lit from behind, so ridges refract the coloured backlight into fringes, and glints sweep across the facets as it slowly tilts. Your mouse is the weather. Slide toward −15 °C and humid and it explodes into ferny dendrites. Slide toward dry and the new growth turns into flat, faceted plates at the tips. Within 30 s you have a crystal that has never existed before, whose shape *is* the record of where you steered.
**Then, the second beat:** release → it tumbles and lands on dark wool beside every other letter you made; camera pulls back to the macro "collection" with shallow depth of field; each flake carries its postmark (its journey on the Nakaya diagram).
**Why surprising:** people know "no two snowflakes are alike" but have never *made* one, watched physics decide its branches, or seen that the shape is a diary of the weather.
**Why not a normal WebGL demo:** a real, 7-parameter vapour-diffusion lattice model (Gravner–Griffeath) running thousands of steps on the GPU; the form isn't drawn, it's grown, and each one is unique and caused by you.
**Verification:** screenshots at t≈2 s (seed), ≈10 s (arms + side branches), ≈30 s (full crystal), landing/collection view.

## Current state (14:40 UTC)
Milestones 1–8 done: research, 6 candidates, 3 prototypes, hero defined, V1 end-to-end, Pass 1 (visual: dark-field ice, triangle interpolation, slab walls, habit tint), Pass 2 (experience: landing/replay/letter/gallery, twins, share links, breath, vapour view, postcard, sound), Pass 3 (polish: gallery material parity, wool, framing, hints, typography) + two physics-correctness passes; five independent reviews (5 → 6.5 → 7 → 7.5 → 8).
Remaining: verify REVIEW-05 fixes (v8), final QA (console audit, refresh, 1440×900 & 1920×1080, shared link, twins), docs + FINAL_REPORT.
