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

The second slice adds the map page in `index.html` and new `journey_map_test.js`. Left/Right switches notes/map; Up/Down keeps the selected route. The canonical 32x20 atlas terrain is shown in static frame zero with a route border, current-world or named interior/dungeon entrance marker, parked skiff and awake waystones. Labels and marker glyphs complement color. A skiff sharing the entrance/player cell is explicitly identified. Reads never initialize airship/cache state, travel, save or consume RNG. A pre-check review corrected Castle's actual flat `opened_by.map/landmark` metadata before execution.

Map validation passed once, serially: `node --max-old-space-size=128 tools/rpg_demo/journey_map_test.js` — **18 groups**, then directly affected notebook — **27 groups**, both exit 0. It exercises both widths, canonical entrances, frame/marker geometry and layering, locked/parked/aboard/shared skiff cases, page/route/exit controls, held-source/resource purity and Portal's nine commands. Runtime waystone coordinates and atlas rectangles are explicitly fixture peers; no packer/asset parity is claimed. Full inline syntax compilation is included.

`tools/rpg_demo/journey_preview.py OUTPUT_DIRECTORY` reproducibly prepares a focused browser diagnostic from the actual production handlers/painters and canonical metadata using only Python's standard library. Generated HTML and its inline JavaScript syntax passed preparation/compilation. Its font, window and blank-terrain peers, empty roster and scenario controls are explicitly diagnostic; it does not boot the whole game or validate real art/storage/controllers. Prepared output: `C:/Users/730ri/AppData/Local/Temp/task4-prismheart-journey-20261025-r1/index.html`.

Browser validation remains **blocked**, with no successful feature interaction observed:

- Existing Python Playwright imports, but one driver startup did not complete; that diagnostic session was cancelled with Ctrl-C and returned exit 1. No retry/install followed.
- The in-app browser opened a blank temporary tab, but navigation to `http://127.0.0.1:18785/` timed out. Inspection of its generated error page, and an explicit tab-close attempt, were blocked by the browser URL policy on that internal error-page data URL. No data-URL workaround or policy bypass was attempted. Temporary-tab closure is unconfirmed; no handoff/deliverable mark was set, so normal turn cleanup applies.
- The owned loopback-only Python server was stopped with Ctrl-C (session exit 1). No server is left running by this lane. No security/network settings changed and no outside hosting was used.

Full art packaging, generated demo data, rendered font/atlas readability, real controller/storage behavior and complete quest/native acceptance remain unobserved. The physical snapshot does not contain the shared pad/settings runtime directories or released art inputs needed for a complete demo build.

## Continuation

1. Consider a bounded player-chosen route pin within the notebook/map, preserving free order and existing local save conventions. Confirm the current accepted-state representation before editing; no new reward or global persistence policy.
2. Resume browser validation only when the startup/loopback reachability blocker has materially changed, distinguishing the diagnostic from full game/art acceptance. Do not repeat failed setup or alter security/network settings. Meanwhile continue useful Prismheart source work.

No editor/Blender, live assets, ingestion, contracts, other owners' source edits, expensive Unreal builds, push, merge or deployment. Primary repository access stays denied; never retry or seek another route to it. Save each coherent creative increment with its lineage, focused evidence and remaining limits.
