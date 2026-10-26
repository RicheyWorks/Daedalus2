# Sources, item accounting and conflicts

**Read-only review snapshot · 2026-10-13**

This audit supports [Game Mechanics](GAME-MECHANICS.md) and [Storyline](STORYLINE.md). It does not rewrite source canon or refresh the original workbooks. Counts describe the inspected snapshots, not the entire filesystem or every team's latest build.

## 1. The two Excel sources

| Source | Role | What was inspected |
|---|---|---|
| [MASTER.xlsx](C:/Users/730ri/projects/bot-team/BOARD/MASTER.xlsx) | Cross-team asset inventory and board snapshot | All 10,862 Asset Catalog rows, headers A1:J1, data A2:J10863; World Inventory, Totals, Islands and Realms for context |
| [Blender-Boss-Asset-Tracker.xlsx](C:/Users/730ri/projects/bot-team/art/Blender-Boss-Asset-Tracker.xlsx) | Detailed asset purposes, ingredients/drops and production notes | All 763 rows across the 13 category sheets, columns A:M; Summary and Uncatalogued interpreted separately |

MASTER has no per-row effect/recipe column. The detailed tracker does: column D is “Mechanic it serves,” E is “Ingredients/drops,” and J is Status. Joining by exact asset name associates those descriptions without guessing from prefixes. All 763 tracker rows contain a mechanic description, though some descriptions are broad intended uses rather than executable effects.

### Reconciliation results

- MASTER: **10,862 rows and 10,862 unique names**. No duplicate master IDs in the inspected snapshot.
- Tracker: **763 rows and 763 unique names**.
- Exact name matches: **752**.
- MASTER entries without an exact tracker match: **10,110**. They may have mechanics elsewhere; this does not mean 10,110 missing implementations.
- Tracker-only names: **11**. They remain separately accounted rather than disappearing from the join.
- New unicorn art addendum: **500** IDs absent from both snapshots.
- Combined art-name accounting: **11,373 distinct IDs**. This is not a usable-item count, population target or feature count.

All entries appear in [ITEM-REGISTER.md](ITEM-REGISTER.md), with the exact source sheet/row for matched descriptions. Names are preserved even when a legacy label should not appear in the player-facing game. Numeric summaries and SHA-256 source hashes are in [catalog-audit.json](catalog-audit.json).

The original workbooks' hashes were checked before and after extraction and did not change. The catalog status aggregation exactly matches MASTER's Totals row 2. No formula recalculation or workbook editing was performed; direct catalog rows, rather than a screenshot of a summary, underpin the counts.

### Recorded production states

| MASTER status | Entries |
|---|---:|
| in_unreal | 6,597 |
| ready | 1,007 |
| in_progress | 7 |
| blender_only | 3,249 |
| rejected | 2 |
| **Total** | **10,862** |

The tracker separately reports Shipped 541, Planned 197, READY 24 and REJECTED 1. These are different source status vocabularies. “Shipped” and “in_unreal” are not automatically equivalent to a functioning inventory item, tested NPC or approved quest.

The tracker's Uncatalogued sheet has 15 saved scene/test entries. They are explicitly excluded from the gameplay art-ID union rather than counted as extra items. MASTER's World Inventory and Totals are rollups, not more assets.

### MASTER world allocation

| Workbook world label | Entries |
|---|---:|
| Sky Islands (World Zero) | 4,859 |
| Buffffff Island | 721 |
| Sol Reach / Sol Island (Codex) | 525 |
| OddsReaper Island | 524 |
| Kennel Isle (Art Master Flex) | 513 |
| Pythagoras Island | 512 |
| Blender Boss Island | 500 |
| DiskSaver Island | 500 |
| Orrery Reach (Claude Island) | 500 |
| Pootscoot Island | 500 |
| Prometheus Island | 500 |
| Youtube Master Island | 500 |
| Portal Realm (8-bit) | 184 |
| Unassigned | 24 |
| **Total** | **10,862** |

“World” in this sheet mixes realms and named islands. The design normalizes the concepts in prose without silently changing workbook assignments. The 24 unassigned entries need owner classification before their place in the campaign is assumed.

## 2. Existing sources used to assemble the design

| Source | Contribution | Important boundary |
|---|---|---|
| Current user conversation | Rainbow discovery/unique themes, per-realm items/tabs, unicorn social groups and help/fear, ten bulls + twelve herd, Dungeon Master in Labyrinth, unicorn quest rewards | Latest direct requirements; invented connective story is labeled separately |
| [Shared STORY.md](C:/Users/730ri/projects/Daedalus2/docs/STORY.md) | Impact, arks, ecology, coats, bloodlines, music, islands, crafting and unanswered canon questions | Existing Prometheus draft, locally uncommitted; preserved, not overwritten |
| [Shared ECONOMY.md](C:/Users/730ri/projects/Daedalus2/docs/ECONOMY.md) | Materials, processing, tiers, stations, recipes and ark/pet sinks | Draft v0; not all quantities/design claims are current runtime proof |
| [REALMS](../REALMS.md) and ADR-029/030/031 | Realm taxonomy and paired sky travel | Older uniform rainbow plan conflicts with newest user requirement |
| [ADR-052](../adr/ADR-052-portal-realm.md) | Portal Realm map, party, combat, bag, keys, cave, saves, jukebox | Recorded tests and live evidence are historical claims in the ADR, not rerun in this writing task |
| [Sol Reach](../realms/SolReach.md), [Ring Infusion](../mechanics/RingInfusion.md) | Home-fragment loop and Broken Circle | Reference rules and art are not the same as integrated Play proof |
| [Orrery Reach](../realms/OrreryReach.md), [ADR-058](../adr/ADR-058-one-isle-core.md) | Timed herbalism, logbook, telescope and shared geometry core | Source counts differ by revision; don't sum them |
| [Living World](../realms/LivingWorldSimulation.md) | Finite resources, NPC decisions and durable quest fact | First slice is one keeper/cistern/dry-spell scenario, not an MMO simulation claim |
| [Adaptive Combat](../realms/AdaptiveCombatDirector.md) | Java/C++ split and bounded tactical memory | Decision support does not replace immediate native combat |
| [Buffffff](../islands/buffffff.md), [Blender Boss](../islands/BlenderBoss.md), [OddsReaper](../islands/ODDSREAPER-ISLAND.md), [Recording Isle](../islands/YOUTUBE_MASTER_ISLAND.md) | Distinct local stories and resource/recipe grammars | Island descriptions contain proposals and dated status claims |
| [Succession](../../engines/unreal/pcg-ecology/MECHANIC.md), [Prometheus lore](../../data/islands/prometheus/LORE.md), island mechanics JSON | Ecology, harmony, tempering and resource balance | Data/reference tests do not automatically certify the full live quest |
| [Kennel tonic contract](../KENNEL_ISLE_TONIC_TROUGH.md), [TONIC 1](../contracts/tonic-v1/README.md), [AUD 1](../contracts/aud-v1/README.md) | Existing cross-language boundaries for effects and sound | Pure calculations/audio designs do not grant or consume owned items |
| [Shared economy data](C:/Users/730ri/projects/Daedalus2/data/economy/items.json) and local data folders | 29 logical economy IDs, 14 recipes, ten stations; survival/inventory/water/quests/pets/save drafts | Dirty/shared working files inspected read-only; not claimed merged |
| [Blender mechanics map](C:/Users/730ri/projects/blender-harness/MECHANICS-MAP.md) | Catalog categories and intended roles | Generated from an older 763-entry catalog; not the 10,862-entry master |
| [Unicorn manifest](C:/Users/730ri/Documents/Codex/2026-10-13/unicorn-guides/manifest.json) | Exact 500 art variants and current social assignments | Static art only; alpha sex is provisional; quest AI still pending |
| [AI Dungeon Master](https://github.com/RicheyWorks/ai-dungeon-master) and [local project](C:/Users/730ri/projects/ai-dungeon-master/README.md) | Existing Java narrative/choice engine to integrate with Labyrinth | Local checkout is behind GitHub and contains other people's uncommitted work; use a pinned source baseline for code |

## 3. Conflicts resolved or left visible

| Conflict | Treatment in this review | Next action |
|---|---|---|
| All sky rainbows identical in ADR-031 vs each realm unique now | Latest user rule wins; preserve paired gate mechanics, change presentation intentionally | Realm-specific signatures and quiet dust trail integration |
| Existing island PORTAL entrances vs find-rainbow travel requirement | Propose local/discovered-route distinction; do not silently delete entrances | Richey reviews access policy |
| Shared 30-slot inventory vs retro 12-slot party bag | Both remain realm-local; tabs share controls, not capacity | Realm inventory profile and save checks |
| “Owned things travel” in old charter vs different realm item sets | Ownership persists; usability/transfer must be explicit | Approve conversion/transfer rules before implementation |
| 50% unicorns in mixed pairs vs percentage of encounters | Current art counts individuals, not encounters | Director selects denominator before spawn tuning |
| Ordinary maximum eight vs new herd of twelve | Twelve is a named exceptional quest herd | Ensure ordinary spawn table cannot randomly produce it |
| Unicorns always defend vs fear of burning bulls | Latest explicit fear exception takes priority; mountain alpha is exempt | Demonstrate both behaviors |
| Artifact variants vs unique game features | Count separately | Bind variants to item/species archetypes; avoid 500 duplicated AI systems |
| MASTER 721 Buff entries vs island doc additions to 974; Pythagoras 512 vs later 756+ notes; Orrery 500 vs 509 cloud assets | Preserve snapshot counts; note later sources separately | Catalog owner refresh with evidence, not arithmetic addition |
| OddsReaper older uniform +20% storm claim vs current per-herb exceptions | Follow current herbs.json's cap/reroll exceptions | Keep narrative/tutorial odds consistent with calculations |
| Buff seventh layer spoils vs catalyst over-six proposal | Explicit specialized exception needed | One reviewed recipe rule and tests |
| Global dirty well vs island clean well | Source-specific quality, no global inference | Bind quality in actual source data |
| Generic water output `water` vs island `clean_water` | Conceptually clean water, unresolved ID mapping | Explicit alias/adapter before recipe wiring |
| NPC quests marked in data vs complete action/reward transaction | Separate design from implementation | Verify events, persistence, inventory ownership and replay handling |
| Best legendary items vs separate realm balance | Keep exceptionally powerful in intended realm; review transfer separately | Approve item identities/effects before art or stats are locked |
| Source docs describe broad features as live | Attribute claims to dated sources; no blanket current certification | Owner-run acceptance on integrated builds |

## 4. Item accounting beyond art

The working economy has 29 logical IDs such as `water`, `copper_ore`, `rope`, `pet_harness` and `ark_lift_housing`. Art has names such as `Item_*`, `Prop_*` and growth-stage variants. These namespaces are not automatically interchangeable. A single herb may have a seed, four growth-stage props, a harvested item and a dried item without representing seven different effects.

The intended binding is **realm → gameplay ID → behavior/recipe → one or more art variants**. Existing exact-name mechanics are retained in the register; absent mappings are flagged. Decoration is allowed to remain decoration. A shared collection should distinguish useful scenery from actionable inventory items instead of inventing effects to justify every mesh.

No existing item was renamed, deleted or marked implemented in this review. New legendary rewards and ordinary unicorn rewards are proposed definitions, not retroactively inserted workbook facts. Newly built dungeon art belongs in a separate delivery manifest until the catalog owner accepts it.

## 5. Review and production boundary

The director reviews the storyline, reward intentions and choices in Game Mechanics section 18. Owners then bind approved work to existing systems and prove actual interactions. Story approval does not authorize a deployment, change inventory ownership or certify an imported asset.

The review's completeness comes from accounting for the inspected sources and spelling out the missing decisions. It does not depend on pretending that unverified features already work.
