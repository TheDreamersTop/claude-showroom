# VESPER 61 · 晚星 61

**▶ Watch:** https://thedreamerstop.github.io/claude-showroom/20261110-vesper-61/

A 63-second luxury commercial for a private jet that keeps the sunset.
一支 63 秒的私人噴射機廣告：一架追得上夕陽的飛機。

VESPER 61 is a fictional aircraft. Every frame and every sound was generated in code during one overnight session.
VESPER 61 是虛構機型，所有畫面與聲音都在一個晚上用程式生成。

## The idea · 點子

At 61° north the Earth's surface turns at about 811 km/h (1674 km/h × cos 61°).
A business jet at Mach 0.90 cruises at about 956 km/h. Fly west along that latitude
and you outrun the sunset. The supers in the film count real elapsed time along a
plausible route (Bergen → Faroe Islands → south of Iceland → Cape Farewell → Labrador Sea)
while the sun stays on the horizon and finally rises again in the west.

北緯 61 度地表自轉約 811 公里／小時，0.90 馬赫巡航約 956 公里／小時。沿這條緯度往西飛就能跑贏日落；
片中字幕的時間沿著卑爾根 → 法羅群島 → 冰島南方 → 格陵蘭法韋爾角 → 拉布拉多海一路往前，太陽卻一直停在地平線，最後從西邊升起。

## How it was made · 製作方式

| Part | Method |
|---|---|
| Jet | Procedural mesh (lofted fuselage, NACA-style wings, T-tail, nacelles), shader-drawn livery and windows — `src/jet.py` |
| Sky | Blender 5.1 multiple-scattering sky, low sun, AgX tone mapping — `src/env.py` |
| Clouds | numpy cumulus heightfield (stacked billows, blurred), 5M-triangle mesh, sky-matched aerial haze |
| Render | Cycles + OptiX on an RTX 2060. Cloud shots are two passes (clouds with camera-only motion + sub-frame blur, jet on transparent film with real motion blur) composited in Python |
| Rising sun | Composited 2D disc behind the jet in the 300 mm shot |
| Score & SFX | Synthesised in numpy: additive piano, detuned-saw string pads, sub, convolution reverb, engine roar, whooshes — `src/music.py` |
| Voice | Neural TTS (en-GB), five lines |
| Edit / grade | `src/compose.py`: bloom, split-tone, vignette, grain, supers, end card, audio mix with ducking |

## Files · 檔案

- `film.mp4` — the film (1920×1080, letterboxed 2.35:1, H.264 + AAC)
- `poster.jpg` — poster frame
- `src/` — all scripts used to make it
