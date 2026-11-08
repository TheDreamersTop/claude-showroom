# STATE (resume here after a context reset)

Start: 2026-11-08 11:13 UTC+8. Budget ~8h, deadline ~19:00.

## Idea: "LEFT & RIGHT" (working title)
An oscilloscope love story. The soundtrack IS the picture: stereo audio, left channel = beam X,
right channel = beam Y. Picture is rendered FROM the final wav, so every sound draws what you see.
- Alone, each channel is only a line (Left = horizontal line, Right = vertical line). Headphones: each lives in one ear.
- Together they can draw anything. Consonant intervals = stable Lissajous figures, dissonance = tangles.
- Arc: dot/silence -> Left alone -> Right alone -> awkward meeting (tangle) -> tuning (circle, intervals)
  -> drawing a life together -> drift/dissonance/separation -> reconcile -> old age, circle shrinks to a dot together -> CRT off.
- End card: every sound you heard drew what you saw.

## Pipeline
- src/sig.py: signal building blocks (numpy, 48 kHz stereo)
- src/score.py: the film, scene by scene -> renders/audio.wav
- src/render.py: phosphor renderer, reads wav -> frames -> mp4
- no hosting creds: no gh auth, no Cloudflare token. Deliver via SendUserFile + claude.ai Artifact; prepare showroom folder locally.

## Status / next
(see PROGRESS below)

## PROGRESS
- 11:20 env checked, idea chosen, starting engine.
- 11:35 v1 rough cut (178 s, 540p preview). Arc reads. Opening lines too long.
- 11:45 v2: tighter openers, DC ramps (no clicks), animated life montage (walk in, hold hands, heart balloon,
  home w/ smoke + sunrise, child grows, child walks off, couple), single-loop stick figures, greedy stroke order.
  Global gain 0.47 (-16 LUFS target), render scale 0.44/0.47. Full build: `python src/score.py renders/vN.wav 0.47`
  then `python src/assemble.py vN 1080` -> renders/vN_final_1080.mp4 (~6 min).
- 12:05 review round 1 on v2 (2 reviewers, 5/10 each), notes in docs/reviews/REVIEW-01-v2.md.
- 12:15 v4 restructure (124 s + cards): short opening, 10 s building interval dance, dissolves instead of morphs,
  fixed stroke order (hands/feet routing), child walks clear + waves + leaves, drift = figures separate and flatten
  into their own lines at opposite edges, return+old age one continuous take (no pop), shorter bigger end card.
  Blender bookend dropped: running a downloaded binary was blocked by the permission system.
- Delivery plan: no gh auth, no Cloudflare token. SendUserFile the mp4 + claude.ai artifact page (assets capability,
  video <= 15 MB web encode). Showroom folder prepared locally in showroom/ for the user to push.
- 12:45 v6: child waves + walks into distance, shaky-heart callback, falter, hard power-off. v7 trims.
- 13:00 review 3 on v7 (6.5/10). AAC finding: default AAC smears XY picture; final encode uses
  320k with -aac_is 0 -aac_pns 0 -aac_ms 0 (SNR 26.7 -> 32.2 dB in the drawing section).
- 13:20 v8/v9: heart attempt really fails (pinched lobe, open tip, shaking); falter = stutter + flatline;
  drift lines shrink in place (no extra solos); floor line in family scenes hides all beam jumps;
  child stays in the route as a speck (no structure pop). Current best: renders/v9_final_1080.mp4
