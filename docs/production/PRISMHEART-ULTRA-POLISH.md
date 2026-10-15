# Prismheart Ultra source polish — v11-ultra-folly-r1

Status: **source implemented; not built, played, rendered or published**. Owner: Ultra / buckwild-sol. Actual start: 2026-10-15 21:37:13 UTC. First gameplay source saved: 21:42:53 UTC. Coordination: START hub32396; saved checkpoint hub32398.

## Lineage and custody

The released handoff is main `9175723ad200b05558a2ea12470763c3b9432152`, published Prismheart demo v10, with the genre constraint in hub32388. This successor keeps its pixel JRPG identity. The primary checkout lacked `tools/rpg_demo/` and `data/rpg/`; the thirteen released source files were recovered from that exact commit before editing. The published v10 and D2-build originals are untouched. This is an uncommitted local source package, not a published v11.

| Evidence | Path / SHA-256 |
| --- | --- |
| Original thirteen-source archive | `artifacts/source-snapshots/prismheart-9175723ad200b05558a2ea12470763c3b9432152.tar` — `d4441ee9c092888b45896be9830fdb026607b570e717e226f6806293dd7329d5` |
| Original source extracted for review | `artifacts/source-snapshots/prismheart-v10-source/tools/rpg_demo/` |
| Frozen dependency archive | `artifacts/source-snapshots/prismheart-dependencies-9175723ad.tar` — `fb852b2436c18d8378a7e8878135cbdaff518daa7239f158a66a00820ee451d2` |
| Frozen dependencies | `artifacts/source-snapshots/prismheart-v10-dependencies/` — fifteen RPG JSONs and four controller/settings files |
| Before/after source diff | `artifacts/source-snapshots/prismheart-v11-ultra-folly-r1.patch` |
| File pins | `data/assets/prismheart-ultra-source-pins.json`, `prismheart-ultra-dependency-pins.json`, `prismheart-ultra-folly-art-pins.json` |

Only `tools/rpg_demo/index.html` and `tools/rpg_demo/build_demo.py` differ from the recovered source. The ten existing test scripts and bot.py remain byte-identical. Frozen controller v1 and linked settings are copied dependencies, not edited contracts. Other owners' source, current native intake, Reedwheel Haven and Blender production are outside this package.

## Implemented player loop

1. Talk to the existing Elder. The original shard directions remain; new dialogue points to Brannoc and the old northeastern AirshipPad. Discovery is a namespaced flag in the existing journey save.
2. Gather the original Fire, Gale and Light shards. The main CrystalShrine route and optional works both require three. Gearwright's Folly is appended as dungeon index4; original indices0–3 and their chest identities remain stable.
3. Enter the three-floor, castle-theme Gearwright's Folly through AirshipPad. Floors, sewer encounters, chests and Clockwork Colossus come from the frozen realm data. The boss retains its canonical stats and Tide weakness. Its shard is `-`: it never awards or counts a fourth shard.
4. Defeat the Colossus. Existing recruitment brings Brannoc the Gearwright into the party or reserve at the established party-average level. ORDER, equipment and reserve EXP use the original systems. CONTINUE restores owed recruits through the existing recruitment path.
5. Return to the Inn. Brannoc appears at unobstructed tile11,6 and offers a replayable calibration drill. His field representation reuses NPC_Merchant art; his battle sprite is the canonical Gearwright. No new character art is claimed.
6. Read pressure, timing and heat clues; choose a repair and receive explanatory feedback. Order and choice positions rotate by completed run. A completed drill records runs and personal best; B cancels a choice without recording that drill. The first perfect drill gives two existing Herb Tonics; later drills give practice and a score, without repeat item farming. Save the journey to retain records/reward.

The workshop stores bounded namespaced entries in the existing `opened` set, alongside an existing one-time reward flag. It uses the existing bag, dialogue and save format `prism.save.v1`. It adds no currency, token, payment, parallel inventory or server authority. It does not mutate combat randomness.

## Visual and dialogue polish in source

- Dark status pills and separated party/name/HP/MP columns fit the existing320×224 composition. Enemy pills draw after sprites and spell art so overlapping enemies do not hide them.
- Chronoseer Drowse/Lull add pixel motes and landed-status symbols; Beastcaller Gust adds wind ribbons. The original atlas effects remain. Symbol display uses this cast's recorded status result, so an already afflicted foe reporting MISS does not gain a new success symbol.
- Overlay positions use time and fixed indices rather than consuming combat random calls. No balance, hit chance, status immunity or spell cost changes are claimed.
- New journeys clear unfinished dialogue/fades/menus and reset encounter state. Delayed welcome/tutorial messages require the same journey, field mode and no active dialogue.
- Save summaries call total defeated bosses “bosses.” Optional Colossus bestiary/retreat/immunity/save text no longer calls it a shard Warden. Existing main quest text and ending remain.

The static canonical boss `phases` and special drop descriptions are not newly implemented mechanics. Colossus uses the existing boss combat system; steam-vent/overheat phases and master-wrench drops are not claimed.

## Source review and limits

Two independent source reviewers inspected story/save/recruitment and builder/data integration. A separate visuals implementation pass was followed by independent source review. Root closed findings about boss-count wording, stale welcome timers, Colossus terminology and cast-result FX. Direct file hashes and a source diff preserve the reviewed boundary. Added castle tile and Colossus sprite files were inventoried, not rendered.

No tests, syntax checks, imports, build, browser, runtime play, native editor operation, Blender authoring or render ran for this successor. The previous owner's green suites are historical v10 reports only. Packing, gameplay reachability, encounter balance, rendered legibility, controller use and save/reload remain unobserved for v11. No screenshot or playable v11 exists from this work.

The preserved `quest_test.py:46` expects exactly the original four dungeon names. A future validation owner must distinguish those unchanged four main routes from the appended optional fifth; the old literal count is not current acceptance evidence. The test source was deliberately left unchanged under the no-testing instruction.

## Next production step

The coordinator can review the two source files and diff now. Runtime/build work needs its own later authorized turn. Reuse the released art roots after checking their current pins; the castle/Colossus subset is inventoried, not a complete art freeze. Keep the original published output intact and write a new versioned output directory.

Prepared command shape, **not executed**:

```powershell
python tools/rpg_demo/build_demo.py "<released FX_DIR>" "artifacts/prismheart-v11-ultra-folly-r1" --sprites "<released SPRITES_DIR>" --source-root "artifacts/source-snapshots/prismheart-v10-dependencies"
```

On that later turn, inspect the preserved feature set plus the new discovery → three-shard gate → Folly → Brannoc → Inn drill → save/reload loop, including cancellation, repeat rewards and existing-status misses. Any later validation should run serially as the original handoff specifies. Browser/server exposure and production static allowlists remain with their owners. No external publishing occurred.

## Lessons for subsequent crews

Keep optional non-shard bosses out of shard counters, stable indexed save keys and Warden-specific wording. Append routes rather than reindexing old saves. Reuse existing state and item tables for small activities. Tie success visuals to the actual action result, not a status that may predate the cast. Preserve an immutable baseline before source polish. Distinguish source inspection from built, played and rendered evidence, and retain the original genre while deepening its own mechanics.
