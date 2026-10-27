# Gearwright's Folly source continuation

This ports the authored optional quest and inn calibration drill onto the Prismheart continuation at `17fd25043`. The original four quest indices and chest namespaces remain fixed; Folly is index 4, requires the three existing shards, and awards no fourth shard.

The producer source is Daedalus2 checkpoint `caf1b103f6cf5a3a66a3c718c139a7091b727b9d` (2026-10-15, `Checkpoint Prismheart Ultra polish and visual preflight`), including:

- `docs/production/PRISMHEART-ULTRA-POLISH.md`
- `data/assets/prismheart-ultra-handoff.json` and the Ultra source/dependency pins
- `docs/production/CONTROLLER-CONSUMER-ULTRA-R2.md` and its source pins
- `tools/rpg_demo/index.html` and `tools/rpg_demo/build_demo.py`

The authenticated r2 index SHA256 is `0c4ed03f9c66b38df28eaae45205e82de8b11bac002a2168ada01e526c91220f`; its builder is `8dba79c338d5f3f886eb3acb41dacf639da589af708c0f99fb1b247ebb9e7008`. The current canonical dungeon, party and boss JSON bytes match the producer dependency pins. Exact extracted blob provenance is recorded locally in the task's `gearwright-producer-caf1/EVIDENCE.json`. The historical producer packet described source implementation and review without runtime acceptance; later title-recovery evidence does not change that acceptance boundary.

## Authored behavior retained

Folly uses the canonical three castle floors, sewer encounters, chests and Clockwork Colossus stats/rewards. Its Tide weakness, existing boss resistance/special-turn rules and Brannoc recruit are unchanged. No named phase or described item drop is invented. Brannoc uses the existing Merchant field sprite and his existing Gearwright battle sprite. The original three shards still open the final shrine independently of Folly.

The inn workshop keeps `story/folly/*` and `workshop/folly/*` in the existing v1 `opened` set. Three deterministic readings rotate by completed run count. Back cancels without recording a score or reward; only the first perfect drill grants two existing Herb Tonics. Runs/best remain bounded; no new save format, currency or recurring reward is introduced.

## Adaptations to the current continuation

- Original skiff walk-on and current-tile Confirm boarding remain first. On foot, face the AirshipPad from an adjacent tile and Confirm to examine the optional route. Shared dungeon entry applies the same gates and first-entry introduction.
- Seven or eight companions use 22-pixel compact rows, keeping the last row above the ORDER feedback panel; five or six retain 30-pixel rows and four retain 52-pixel rows. ORDER and reserve rules remain unchanged.
- The inn NPC derives from the validated candidate save during detached Continue preparation. Invalid Continue preserves the current journey and pending callbacks. Accepted New/Continue invalidates earlier workshop/entry/tutorial callbacks.
- Generic dialog Back still selects option 1 and consumes concurrent Confirm. Only workshop reading questions supply the optional cancellation callback.
- Existing input, storage, controls, combat, fishing, sky-cache, clock, waystone, shop and Portal projection fixes are retained. The old r2 controller and visual changes are not copied.

## Focused verification plan

Before execution, review the production diff. Then use two bounded DOM-free Node VM fixtures extracting actual production functions and canonical catalogs: optional gates and dock coexistence; original route/chest indices; three-floor stairs and boss progression; normal boss rewards and no fourth shard; Brannoc recruitment/ORDER/equipment and eight-row bounds; workshop cancellation/rotation/once-only reward; actual v1 save writer/reader and detached Continue; legacy journeys and stale callback invalidation. Check builder projection with standard-library AST evaluation only, without importing Pillow or calling the build entry point. Compile the inline script without executing it. Run only directly affected existing snippet fixtures after supplying their actual new dependencies, including the generic dialog input check.

This is a source and offline-check continuation. It does not certify generated assets, a browser playthrough, native integration, performance, or runtime acceptance. No editor, native build or artifact build is part of this slice.

## Offline results

The focused progress fixture passed 13 groups, including bounded reachability through the three canonical floor grids, actual stair/boss/recruit/ORDER handlers, ordinary skiff/cache behavior and Windmere's once-only request. The workshop/save fixture passed 20 groups, including directly stale Folly entry callbacks, both accepted journey choices, all workshop callback stages and actual v1 serialization/restoration. The AST-only builder check passed original route indices, optional projection, unchanged final scaling and bossless Portal isolation. Both new VM fixtures compile the complete inline script without executing it.

Directly affected existing checks passed serially with Node's heap capped at 128 MiB: journey saves 44, name entry 14, intro controls 15, skiff reboarding 22, shard hints 15, generic dialog input 20, and storage failures 18. Existing fixture edits only supply actual new source dependencies/accepted-journey UI seams or update the controlled dialog source witness. The old browser quest check's route-list assertion now permits the appended fifth route; that browser suite was not run. Initial new-fixture failures were setup issues (an unused missing export and the real Quill/Drowse action shape); production remained unchanged during verification.
