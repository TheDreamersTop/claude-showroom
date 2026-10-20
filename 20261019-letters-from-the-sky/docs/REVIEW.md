# REVIEW — adversarial critiques & quality gaps

## REVIEW-01 (10:20 UTC) — independent subagent (Opus), "Hostile Creative Director + Principal Engineer", on V1 screenshots
**Score 5/10** — "the model is real and the hero hexagon is lovely, but shading, aliasing and invisible weather history make it read as a pretty screensaver, not a letter."
Key points (condensed):
1. Growth history invisible → the crystal doesn't read as a record of the path. Fix: per-cell attach time → thickness bands/terraces, visible step where habit changed.
2. Ice shading = sprite outline (constant-width glow stroke, uniform pink rim, flat body). Fix: thickness field normals, brightness ∝ |∇h|, refraction with RGB offsets, kill uniform rim.
3. Lattice staircase aliasing, perfect 6-fold symmetry = CG tell. Fix: smooth reconstruction, tiny noise.
4. Early frame: crystal fills the screen, blown out, mushy — worst frame right after click. Fix: lock framing so the crystal starts small and grows into frame; luminance-capped bloom.
5. Background/bokeh/HUD compete: cut bokeh ~70%, near-black or deep-cyan field, HUD text too small (~7 px), Nakaya box needs labelled regions.
Hero: weather effect slow & ~70% of parameter space looks the same → remap so every screen region gives a distinct tip behaviour within ~2 s, and make it scar the crystal.
Landing: broken (black thumbnail, identical next crystal) → fall onto black wool with rack focus, replay growth synced with the Nakaya path, generated caption decoding the letter, zoom out into a Bentley-style plate grid of all crystals; postcard export.

### My response plan
- [done before review landed] thumbnail fix (snapshot after render), zoom floor (≤~2.8 px/cell) so the crystal starts small, nucleation prism, triangle interpolation (straight facets), slab thickness side-walls, weather anchors re-labelled from sweeps.
- V2 visual: timeline texture (attach step → weather at birth) → growth rings/terraces + birth-temperature tint; brightness from slope not mask; symmetry noise; darker field, fewer bokeh; bigger HUD with labelled Nakaya regions.
- V2 experience: landing on procedural knitted wool with rack focus; growth replay; letter caption; gallery of all letters; share/regrow via URL-encoded journey.

## REVIEW-02 (~11:20 UTC) — independent subagent (Opus) on V2 flow screenshots
**Score 6.5/10** — "the simulation is now genuinely beautiful mid-growth, but the frame around it (bokeh, glow, wool, HUD) still looks like a template."
Improved vs V1: real morphology (plate tips on dendrite arms, sectored ribs), aliasing & blow-out gone, minimap path + letter text tell the journey, thumbnails fixed.
Still AI-demo: uniform white rim glow, stair-step chevrons inside branches, hexagon bokeh, thin uppercase UI everywhere, breath = lens-flare bloom.
Ranked weaknesses: (1) wool reads as smudged marble (veins), gallery = pastel heart wallpaper; (2) ice shading: rim glow −60%, thickness absorption, one-sided Fresnel, smooth height field; (3) breath should be local haze + visible retreat, no screen bloom; (4) minimap = debug panel (box fill, colliding labels) → no fill, labels outside, thick habit-coloured path; (5) letter card has no surface: scrim, lead with the one-line poem large, log small, text-link buttons.
Hero: cause→effect abstract (meaning lives in a 260 px corner box) → make the whole screen the Nakaya diagram (faint tinted regions, label near cursor), tint the growth front with the habit colour and let it persist in the ice.
Landing: anticlimax; gallery should be overhead, letters 8–12% of frame height, constellation scatter, raking cold key light with sparkles & soft shadows on fibres, slow drift, hover lift with shadow separation.
First change: wool + gallery rescale.

### Response plan (V3)
1. card scrim + hierarchy (poem first), text-link buttons · 2. minimap redesign · 3. breath → local haze + retreat · 4. rim glow down, smoother height field, intro = big dendrite, bokeh 2–3 tiny discs ·
5. wool: remove veins, real fibre fuzz, darker charcoal/oxblood, raking light; crystal shadows on wool; gallery fit/scatter, hover lift, drift ·
6. full-screen faint habit field + cursor label; habit-coloured growth front persisting in ice.

## REVIEW-03 (~12:38 UTC) — independent subagent (Opus) on v3-sheet.jpg
**Score 7/10** — "The live simulation is now gallery-grade, but the payoff (the landed letters and the gallery) is rendered worse than the moment before it."
Exceptional frame to protect: live mid-growth (grow2) — translucent bevelled plate tips, internal ridges, soft teal backlight, visible weather change at the tips.
Weakest: (1) landed/gallery letters: 2–3 ghost shadows, per-crystal tints (twins blue vs white), smeared dendrites, faint quad; (2) boundary clipping (pre-fix shot); (3) wool scale wrong (cushions) → 2.5× finer, −40% contrast; (4) hex bokeh + white rim stroke + matte grey hub; (5) card collides with crystals; card surface generic; postcard composition weak (bleed crystal, text bottom, minimap as postmark).
Red flags: lighting conflict (shadow direction vs backlit), pink fringe looks like an effect, vapour bloom.
### Response (V4)
- gallery letters now use the live crystal's material (lamp-orientation edges, habit tint, growth rings, terraces, glints), one soft shadow (no caustic rim), hover lift; live crystal thins to 1.2 cells when lying (no ghost side-wall), same single shadow.
- wool stitch 2.4× finer, contrast lower; bokeh round, 9+1 faint discs; growth-contour ridges inside plates (hexagons) and bands across arms; bevel 0.6; vapour dimmer.
- gallery framing reserves the right ~30% for the card; postcard redesigned (bleed, low text, postmark ring with the Nakaya path).
- landing flash replaced by a light beam sweeping across the crystal.

## REVIEW-04 (~13:02 UTC) — independent subagent (Opus) on v4-sheet.jpg
**Score 7.5/10** — "The landing now reads as the same object as the live crystal, but the gallery still looks like a contact sheet of stickers on a sweater, not a wall of letters."
Issues: faint quads behind gallery crystals & behind the growing crystal (habit tint), gallery letters dim/flat at small size, contours look like topo/posterize, grey hard hexagon "bokeh" on landing (wool sparkles defocused), sweep blows centre, card dominates the gallery, postcard oval ring, too much bilingual text, CJK orphan, discoverability (11 px hint bar; nobody learns Space).
### Response (V5)
habit tint removed; shadow edge falloff (fix landed after v4 shots); gallery edge gain ×(1–1.8) by screen size and tint reduced when small; contours −60% and hidden when denser than ~3 px; wool sparkles soft, round, dim; near bokeh layer deleted; sweep peak halved; card hidden in gallery overview (centered collection + hint bar "click a letter to read it · space = catch another"); postcard ring removed; letter log rows Chinese only (English as tooltip), poem bilingual; text-wrap: balance; one-time centred "按空白鍵，讓它落下 / press space to let it land" after 8 s; hint bar 13 px @70%.

## REVIEW-05 (~14:33 UTC) — independent subagent (Opus) on v6-sheet.jpg (after the physics fixes)
**Score 8/10** — "The physics fix shows: the crystals are now varied, real-looking and worth looking at. What still holds it back is the letter text and the gallery."
(a) letters repeat (two journeys → same headline) — the text collapses history into one habit; (b) rectangular seams in the wool around crystals; (c) small crystals blown out / pixel-stepped, gallery sizes uneven (3×).
Good enough, stop: intro, card typography, minimap, wool/sparkles/sweep/hint, large-crystal material.
"Until the letter text is as specific to each crystal as the ice is, it stays a very good simulation with captions rather than letters."
### Response (V6→final)
(a) headline now narrates the path: birth air + first form → longest middle segment → final air & form (+ breath), bilingual, de-duplicated within a session; (b) seam root cause = per-stitch flat dye colour from integer stitch id (hard steps at macro zoom) → continuous dye field, fibres fade at yarn edges; (c) edge light scaled by magnification, wider AA when cells > 1 px; gallery display scale k = clamp(N/4 / R, 1, 1.6) threaded through packing, hover, framing, labels, live crystal and its shadow.

## REVIEW-06 (~15:30 UTC) — pre-release review (Opus subagent) on final-sheet.jpg
**Score 8.5/10** — "the letter now reads like it was written for this one crystal." Verdict: don't ship until the habit label stops contradicting the picture and the postcard is checked.
Blockers: specimen label "PLATE" under a plate-tipped fern dendrite (label came from the longest segment); postcard unverified with narrative text; narrative skipped a middle segment.
Improvements: growth-ring terracing at hero scale; gallery sizes / composition; minimap path over labels; faint streaks (stray hairs) in the gallery.
### Response
label = shape classifier (any dendritic stretch ending in plate/sector → 端板樹枝 plate-tipped dendrite; else the dominant dendritic habit); narrative includes every middle segment and mentions temperature only when it changes; postcard re-rendered and fixed (header overlap, Latin word wrapping); weather-change ridges softened & scaled by magnification; minimap labels on a haloed layer above the path; stray hairs −50%; gallery display scale cap 1.6 → 2.0.
