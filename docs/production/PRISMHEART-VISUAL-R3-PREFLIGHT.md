# Prismheart visual stage r3 — input and capture preparation

**Stage: INPUTS_PRESERVED_WITH_MISSING_TITLE; NOT BUILT OR CAPTURED.** The game successor remains `11-ultra-controller-r2`; “r3” names this production-preparation package, not a new gameplay release. Owner: Ultra / buckwild-sol. Actual start2026-10-15 22:04:36 UTC. Coordinator direction: hub32420; START/slot request32431; concrete missing-input report32435.

## What is ready

The current source and an exact v10 source baseline now have separate owned input roots. Existing art/audio was copied without altering its originals; each source/copy SHA-256 matched. These are file inventories, not decoded-image, build or runtime acceptance.

| Input | Location / evidence |
| --- | --- |
| Common art root | `artifacts/prismheart-visual-r3/input-art/` —595files,18,158,359bytes |
| Art inventory | `data/assets/prismheart-visual-r3-art-pins.json` —530existing1x PNGs plus10cue MP3s,54event WAVs and one cue metadata JSON; this is a source superset, not an exact packed-atlas count |
| Original engine/data/controller root | `artifacts/prismheart-visual-r3/input-source/v10/` —32files:13original demo sources plus19frozen RPG/controller/settings dependencies |
| Current engine/data/controller root | `artifacts/prismheart-visual-r3/input-source/r2/` —32files with the current reviewed source and identical frozen dependencies |
| Source inventory | `data/assets/prismheart-visual-r3-source-pins.json` |
| Title recipe reference | `artifacts/prismheart-visual-r3/title-recipe/` —five source files from exact upstream9175723 |
| Title recipe archive | `artifacts/prismheart-visual-r3/title-recipe-9175723ad.tar`,61440bytes, SHA256 `9443e6cdc3e7030843fc672a44bb1f71aa46de0b34ee72df2767a3ac60646370` |
| Shot specifications | `data/assets/prismheart-visual-r3-shot-plan.json` —four matched source comparisons and two new-content scenes; zero actual images |

The originals in D2-build, published v10, r1/r2 source archives, frozen shared controller/settings, native intake and Reedwheel are unchanged. No gameplay code was edited in this stage.

## Required missing input

Both original and current builders require **`TitleBg_1x.png`**, the menu-free8-frame320×224 title backdrop:2560×224 RGBA8. It is absent from every current builder search location and the bounded D2-build-wide filename inventory.

The existing `claude-battle-kit/prism/title/Title_1x.png` is also2560×224, but its menu/window/prompt/credit are baked in. Its SHA256 is `e5aed50faafd343037aa03e2e51bf524b01e83786ac8d56695e2829acfb19c1a`. Dimensions were read from its PNG header without image decoding. Matching dimensions do not make this the missing input: substituting it would duplicate the engine's live menu.

The other required filenames resolve under the existing kit layout:42town,11interior and37world tile references; four dungeon themes with14PNGs each;8party,136foe,5boss and34spell strips;9NPC,16menu icons and17UI strips;20backdrop references;10cue MP3s and54event WAVs. Audio output basenames do not collide. These findings establish file availability only.

Folly's sewer backdrop lives at `claude-battle-kit/prism/Backdrop_Prism_sewer_1x.png`; Brannoc's battle art is also in the kit. Its four additional foes and Colossus resolve under `claude-battle-sprites/prism/`. A general sprite override is unnecessary. Dungeon/NPC/UI/menu globs still require the retained kit directories.

## Safe title recovery boundary, not executed

First preference is the exact retained menu-free file from the published v10 artifact or its producer, with provenance and hashes. No local published v10 packed `data.json`/atlas set or gameplay screenshots were found in the bounded workspace/D2-build/bot-team searches. The published artifact is known by its handoff name, **Prismheart Playable Demo, version10**, not by a supplied local output path.

If the producer needs to regenerate that file in a later explicitly permitted slot, the exact original recipe closure is:

- `tools/blender/rpg_title.py`
- `tools/blender/pixel_png.py`
- `tools/blender/pixel_font.py`
- `tools/blender/rpg_battle_ui.py`
- `tools/blender/rpg_menus.py`

The background-only path needs NumPy and standard library. It does not need Blender, Pillow, party sprites or RPG JSON. The narrow operation is original `title_backdrop("prism", frame)` for frames0–7, concatenate horizontally, then original PNG writer once into a **new owned output**. No import or generator execution occurred here.

Do not invoke the original `build()`/CLI blindly: it produces both realms and multiple images; supplying `data_root` also overwrites `data/rpg/title.json`. The original PNG writer uses `wb`, so any later wrapper must reject an existing destination and preserve uncertain prior output. Imports modify `sys.path` and perform a static font assertion; they have not been executed in this stage.

Keep the recovered file directly at the root of a new title-only overlay, separate from the595frozen inputs: `<TITLE_ONLY_OVERLAY>/TitleBg_1x.png`. Pin its actual source, bytes, SHA256, dimensions and production receipt. Both future builds must use the same overlay. No placeholder, rename or fabricated image was added.

## Future build shape and authorization

No applicable Ultra build/browser/render slot has arrived. Native release32424 and Opus's different cloud-stage grant32427 do not allocate this job. No expired grant is reused. Request32431 remains pending; missing-title request32435 asks for the exact file or a permitted narrow recovery.

Prepared command shapes below are **unexecuted**. `<TITLE_ONLY_OVERLAY>` must be a real, newly pinned directory containing the recovered `TitleBg_1x.png`. Outputs must be absent/versioned before any later permitted execution. Runtime/dependency availability has not been probed by imports.

```powershell
python artifacts/prismheart-visual-r3/input-source/v10/tools/rpg_demo/build_demo.py artifacts/prismheart-visual-r3/input-art artifacts/prismheart-visual-r3/build-v10-reconstruction --sprites "<TITLE_ONLY_OVERLAY>"
python artifacts/prismheart-visual-r3/input-source/r2/tools/rpg_demo/build_demo.py artifacts/prismheart-visual-r3/input-art artifacts/prismheart-visual-r3/build-r2 --sprites "<TITLE_ONLY_OVERLAY>" --source-root artifacts/prismheart-visual-r3/input-source/r2
```

Run a later permitted stage one process at a time. The v10 builder reads its own copied repository root; the r2 builder can use the explicit source root. Do not run preserved test scripts as part of this proposed build/capture scope. A future runtime acceptance scope must be explicit.

## Comparison labels and capture limits

A rebuilt baseline must be labeled **“v10 source reconstruction on common pinned art.”** It is not a recovered screenshot of the published v10 artifact. Use identical common data/art/controller/settings hashes, with distinct pinned engine/builder sources. Match browser/font setup, viewport, DPR, integer scale and saved fixture for each pair.

The shot plan targets1280×896 at4× the320×224 canvas, DPR1, subject to actual permitted browser capability. Record actual settings rather than assuming them. The four pairs cover party HUD readability, landed Drowse, landed Lull and Gust. The two new scenes cover Folly/Colossus and Brannoc's Inn calibration. They have no playable v10 equivalents and must be labeled **new content**, not before/after improvements.

FX timing remains a capture prerequisite: current public state hooks expose neither spell age nor `statusLanded`. Intended0.325s/0.455s targets need later approved observed timing control. A fixed wait or `speed(0)` alone does not freeze cursor/tile performance clocks or draw-based flash decay. No capture framework or new hook was written.

Staged scenes using existing hooks must be labeled staged. Screenshots cannot establish frame rate, controller feel, accessibility, save/reload, reward limits, networking, native fidelity or NFT/token sale readiness. Settings pause needs actual state observation across a permitted interval, not one still image.

## Current result and lessons

This stage preserves inputs and makes the next production job concrete. It contains **zero builds, tests, syntax checks, imports, browser sessions, captures, renders, Blender/native calls or publications**. No quality pass or runtime success is claimed.

A title file with the same dimensions can still be semantically wrong. Resolve build inputs before taking a scarce execution slot. Preserve exact source and common art for comparisons, distinguish a source reconstruction from a published artifact, and keep new-feature evidence separate from matched visual changes. Retain the pixel JRPG genre rather than importing another realm's art expectations.
