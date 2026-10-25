# Prismheart exploration campaign — 25 October 2026

Active campaign ends **2026-10-26 06:56:50 UTC**. Stop starting new slices at that time and finish a safe checkpoint. The new parent assignment supersedes the earlier lane shutdown and deadline. This remains the existing HTML/JavaScript/Python browser game; no native Unreal feature or engine acceptance is implied.

## Preserved starting state

- Original checkout and all previous packets remain unchanged: `../prismheart-source`, saved ref `e7266e67b98df853ea32eb0ea9e2721990d47a9c`, complete prior incremental packet `../prismheart-patches-r12`.
- Direct own-store verification confirmed that ref's loose commit object and the current physical `index.html`, `build_demo.py` and `folly_test.py` blobs. Other baseline objects are absent locally; the original Git alternates point to the denied primary repository. No Git command was run in that checkout and no alternate store was followed.
- New independent repository: `prismheart-campaign-20261025`, branch `codex/prismheart-exploration-20261025`, physical snapshot baseline commit `93f61eeb2af70db9cb516cd73516f276d203b542`. Its 87 permitted regular source files were copied and SHA256-compared with the physical predecessor. `SOURCE-BASELINE.json` records every source hash and the verification limit. No remotes or alternates were configured.
- Preserve the earlier base, all six inherited fixes and 27 continuation commits. Do not apply this snapshot root commit as a replacement repository tree. Future incremental patches are relative to the physical snapshot and intended to follow the preserved Prismheart work, with integration applicability reviewed by its owner.

## Current useful slice

JOURNEY notebook: a Prism-only field menu entry with current shard objective, route completion, Shrine/Folly readiness and practical landmark/entry guidance. The menu scrolls when necessary, preserving the original nine command indices. Existing quest data and accepted journey state drive the view; looking around does not travel, consume items, award rewards, or change the save schema. Portal and shared controller/settings modules retain their existing behavior.

Exact implementation: `tools/rpg_demo/index.html`. Focused regression: `tools/rpg_demo/journey_notebook_test.js`. Independent source review caught the pad action name and clarified on-foot Folly entry and small-width copy before checks. The current objective counts remaining Wardens; route choice stays free.

## Validation and current limits

Notebook checks passed once, serially, on 2026-10-25: `node --max-old-space-size=128 tools/rpg_demo/journey_notebook_test.js` — **27 groups**; directly affected existing `field_menu_test.js` — **11 checks**. Both exit 0. The new fixture uses actual production functions and canonical route/party/menu catalogs, all shard subsets and orders, final/optional progress, actual command-window geometry, 320/256 bounds, shared pad action labels, persistent input edges, viewing/resource purity and controlled former behaviors. Full inline JavaScript syntax compilation is included. These are DOM-free source regressions, not browser/rendered-art acceptance.

Actual browser validation is authorized where available. The existing Python Playwright module imports, but its driver startup did not complete; the single diagnostic session was cancelled with Ctrl-C and returned exit 1. No browser opened and no retry/install was attempted. Full art packaging, generated data, real controller/storage behavior and complete quest/native acceptance remain unobserved. The physical snapshot does not contain the shared pad/settings runtime directories or released art inputs needed for a complete demo build.

## Continuation

1. Add a world-map page inside JOURNEY using the canonical map and existing player/entrance, skiff and awake-waystone state. Preserve free route choice and avoid new auto-travel, fog, reward or save policy.
2. Use an available browser interface for focused validation, distinguishing a feature diagnostic from full game/art acceptance. If blocked, checkpoint the exact dependency and continue another useful Prismheart slice.

No editor/Blender, live assets, ingestion, contracts, other owners' source edits, expensive Unreal builds, push, merge or deployment. Primary repository access stays denied; never retry or seek another route to it. Save each coherent creative increment with its lineage, focused evidence and remaining limits.
