# FINAL REPORT — 天空寄來的信 · Letters from the Sky

**Live:** https://thedreamerstop.github.io/claude-showroom/20261019-letters-from-the-sky/

**Run locally:**
`cd /home/user/showroom && npx http-server -p 8080 -c-1` → open **http://localhost:8080/20261019-letters-from-the-sky/** in desktop Chrome.
(In this session the server is already running on :8080; nothing was pushed anywhere.)

## What I built
A desktop WebGL2 piece in which **you are the weather**. A single ice crystal grows in front of you from a real physical
model of snow growth, the Gravner–Griffeath vapour-diffusion/attachment lattice model. It runs as thousands of steps on a
768² hexagonal lattice on the GPU. Pointer x is the temperature (−1…−25 °C) and pointer y is the humidity. Each region of the
Nakaya diagram grows a different habit. Every ice cell remembers the air it froze in, so the finished crystal is a
legible record of the path you steered, Nakaya's "letter from the sky".

When you let it land (Space), it settles on dark knitted wool under a rack focus and a beam of light sweeps across it.
It then *re-reads itself*: it regrows in four seconds while its path redraws on the Nakaya diagram and a bilingual letter
writes itself. After that the camera pulls back to every letter you have caught. From there you can:
- grow a crystal's **twin** (the exact same weather, different molecular noise, laid beside the original);
- **share** the journey as a link that regrows it for someone else;
- **save a postcard**.

## The Hero Moment
Click the opening crystal. It **rewinds into a seed** and then starts growing under your hand. Push the pointer up into
humid −15 °C air and six fern arms shoot out of the hexagonal plate. Drag it down into dry air and every tip flares into a
small hexagonal plate. The weather is visibly written into the ice: arms, plate tips and growth bands, each tinted by the
air it froze in. It is grown by physics, it has never existed before, and it is *yours*.

## Evolution (see shots/)
- **Prototypes**: A snow model (`shots/a1.jpg`, `a23.jpg`), B Lichtenberg (`b1.jpg`), C pop-up (`c12.jpg`), compared in
  `prototype-sheet.jpg`. A won on scientific depth, universality and how much rendering headroom it had.
- **V1** (`v1-flow.jpg`, code in `v1/`): the end-to-end loop works. REVIEW-01 scored it 5/10: "pretty screensaver, not a letter".
- **V2** (`v2-flow-sheet.jpg`, `v2-landing-sheet.jpg`): the habit map re-derived from parameter sweeps; a birth-weather
  timeline for every cell; dark-field ice; hex-triangle interpolation; slab side walls; adaptive pace; landing on wool with
  replay, letter text and gallery; twins; share links; breath; sound. REVIEW-02: 6.5/10.
- **V3** (`v3-sheet.jpg`): card and minimap redesign, habit-tinted ice, a radius GPU reduction (fixed clipped crystals),
  wool v3, the intro chosen by a journey sweep, and **the clipping bug that the twin test exposed** (fixed). REVIEW-03: 7/10.
- **V4** (`v4-sheet.jpg`): gallery letters rendered with the live crystal's material, single soft shadows, a finer knit,
  the light-sweep landing, growth contours and the postcard. REVIEW-04: 7.5/10.
- **V5**: the polish list from REVIEW-04 (see REVIEW.md), a light pool and specimen labels in the gallery, and
  discoverability hints.
- **Physics passes** (found by chasing visual anomalies the reviewers flagged):
  1. The active region clipped fast-growing crystals.
  2. The vapour field was over-fed (reset to the plate preset's ρ).
  3. The vapour boundary depended on frame timing.
  4. A slow nucleus phase ate each journey.

  After these fixes growth is deterministic (an in-page probe gives the same radius for any chunking or read-back cadence),
  and crystals respond to the weather as designed (`v6-sheet.jpg`). REVIEW-05 scored it **8/10**.
- **Final** (`shots/final-*`, `final-sheet.jpg`):
  - The REVIEW-06 fixes: a shape classifier for the specimen labels ("plate-tipped dendrite"), every segment of the path
    narrated, a postcard layout with Latin word wrapping, softer ridges, haloed minimap labels.
  - The REVIEW-05 fixes:
    - letters narrate each crystal's own path (birth → middle → end), with no duplicate headlines;
    - the wool's per-stitch colour seams are removed;
    - magnified crystals are lit and anti-aliased properly;
    - display sizes are equalised in the gallery.

## Actual work
- Start: 2026-10-19 09:35 UTC. End: 2026-10-19 15:45 UTC. **Elapsed: about 6 h 10 min** of continuous work, out of the
  8 h budget. I stopped when the sixth independent review's release blockers were fixed and verified; the remaining items
  were low-leverage or needed hardware I don't have (see limitations). All shots came from headless Chromium with
  SwiftShader, which is slow (seconds per frame), so a large share of the wall-clock went to automated rendering and
  verification runs. Some intermediate PROGRESS timestamps were estimated in flight; they are marked "~" where I later
  corrected them against the clock.
- Six independent adversarial reviews (Opus subagents, rendered frames only): **5 → 6.5 → 7 → 7.5 → 8 → 8.5**. The last
  one was a pre-release check; its blockers (habit label, skipped segment, postcard) were fixed and re-rendered.
- Significant redesigns:
  - **Shading:** naive backlight → dark-field orientation lamps.
  - **Weather map:** re-labelled from the sweeps.
  - **Gallery material:** rebuilt to match the live crystal.
  - **Wool:** rebuilt three times.
  - **Intro:** a plain plate → a journey picked from a sweep.

## Validation performed
All validation used headless Chromium 1194 with SwiftShader WebGL2 (software GPU) in this container, served by
`http-server` on :8080:
- **Full-loop automation** (`tools/qa/fullflow.sh`, `final.sh`): intro → click → rewind → steer → breathe → vapour view →
  land (sweep, replay, letter) → gallery → hover → focus → rise → second crystal. Screenshots of every phase are in `shots/`.
- **Console and network audit** (`tools/qa/audit.mjs`): load, click, steer, V, B, Space, Space, reload. **0 errors, 0 failed
  requests.** The only notice is SwiftShader's "GPU stall due to ReadPixels" performance message.
- **Features:**
  - twins: replayed with the exact timeline and laid beside the original (`shots/v3-twins.jpg`);
  - shared link (`#letter=…`): gift banner, scripted regrowth, automatic landing (`v3-shared-letter-*`);
  - postcard: the PNG download is intercepted and inspected (`final-postcard.jpg`);
  - refresh works; the opening and the intro bloom work in a fresh session.
- **Physics:** parameter and journey sweeps (`explore1`, `grid1–3`, `journey1`, `introJ`, `introJ2`). A determinism probe
  (`tools/simprobe.html`) gives R = 115 after 3000 fern steps for every initial density, chunk size and read-back cadence.
- **Viewports:** 1600×900, 1920×1080 and 1440×900 (audit).
- **Six independent adversarial reviews** by Opus subagents, on rendered frames only: 5 → 6.5 → 7 → 7.5 → 8 → 8.5.

## Known limitations
- **No real-GPU measurement.** Everything was rendered with a software GPU (seconds per frame). Frame rate on real hardware is
  unknown. Mitigations: dynamic resolution (0.55–1.5× scale, from measured frame time), an adaptive simulation step budget
  (4–90 steps per frame) and `?stats=1` to inspect it. A weak integrated GPU will grow crystals more slowly, not stutter.
- **Sound** (wind and pentatonic chimes, WebAudio) was never heard. I throttled and level-capped it by reasoning only. Use
  `?mute=1` to disable it.
- **Shared links are similar, not identical.** The link encodes the weather at 250-step resolution, so the regrown crystal is
  a close relative. Twins use the exact per-16-step timeline but only exist within a session.
- **The gallery is not persisted.** Reloading starts a new sky.
- **Physics limits:**
  - The Gravner–Griffeath model is 2-D, so the −5 °C needle/column region of the Nakaya diagram grows plates.
  - The 768² lattice caps a crystal at about 2.6 mm (R ≈ 314 cells). It then lands by itself.
- **Deployment came after the run.** During the overnight run it stayed local, by your instruction. It was published
  afterwards to the `claude-showroom` repository (GitHub Pages).
- **Desktop only,** by design. It needs WebGL2 with `EXT_color_buffer_float`.

## What makes it exceptional rather than merely competent
- **The shape is computed.** Nothing about the crystal is drawn: thousands of vapour-diffusion steps grow every branch.
- **It is a record.** Every cell keeps the weather it froze in, so the ice, the tint and the growth bands read as the path
  you steered, and the letter narrates that specific path.
- **The ending re-reads the beginning.** On landing, the crystal regrows in four seconds, in sync with its path on the
  Nakaya diagram.
- **Twins make "no two are alike" testable.** Same weather, different molecular noise, near-identical results side by side.
- **It is shareable.** A journey becomes a URL that makes the same snow fall for someone else, or a postcard.
