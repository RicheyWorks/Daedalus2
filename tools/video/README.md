# tools/video: modular video pipeline (Daedalus / richeyworks)

Engine-free: Python 3 + Pillow (+ numpy for `branding.py`) and ffmpeg/ffprobe. Runs on the Grok box, BLACKBEARD, CI.
Nothing here talks to YouTube or any social site; uploads are a separate, manual step that needs Richey's ok.

| module | does |
|---|---|
| `brand.py` | the shared look: colours, 1920x1080 / 1280x720, 30 fps, fonts, the dragon stamp (`brand/dragon_white_1200.png`) |
| `cards.py <episode.json>` | title card, end card, transparent lower-third captions, YouTube thumbnail (optionally over a real frame) |
| `shots.py prepare` | builds a work folder from a shot list: real MRQ frames where they exist, labelled placeholder stills elsewhere |
| `shots.py stills` | **Daedalus tie-in**: turns a `tools/capture` (capture/v1) `manifest.json` into a stills shot list |
| `assemble.sh <shots> <out.mp4> [song]` | title -> shots (frames at 30 fps or held stills, fades, captions) -> end; song looped + loudnorm, or silence |
| `cut.sh <episode_dir> <out.mp4> [renders] [song]` | one command: cards + prepare + assemble + `<out>_thumb.png` |
| `branding.py` | channel art: profile logo, 2560x1440 banner (seeded reaction-diffusion), safe-area check |
| `episodes/<name>/` | one folder per video: `episode.json`, `shots.txt`, `METADATA.md` (draft) |

New video = new `episodes/<name>/` folder; no code change. Fonts: IBM Plex Mono (OFL) is the house font but is not
vendored; set `DAEDALUS_VIDEO_FONTS=<dir with plex-Regular.ttf, plex-Bold.ttf>`. Without it DejaVu Sans Mono is used.

## Daedalus tie-in
- Shot folder names = Level Sequence names written by `engines/unreal/ytm-island/ytm_flythrough_ue.py`
  (`WB_Flythrough_<Biome>`, `YTM_<Spot>`), rendered by `ytm_orbit_render_ue.py` / Movie Render Queue into `<Seq>/0000.jpg`.
- Stills: `tools/capture` jobs (capture/v1) write PNGs + `manifest.json`; `shots.py stills` turns them into a cut, so
  a proof capture doubles as a teaser. Editor work goes through codex-play-guard (sole Unreal writer).

## Tests
`python -m unittest discover -s tools/video -p "test_*.py"` (ffmpeg end-to-end test is skipped if ffmpeg is missing).
