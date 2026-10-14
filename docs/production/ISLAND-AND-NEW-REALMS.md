# Island production and new realm architecture — 2026-10-14

Owner: team-codex. Unreal integration handoff: unreal-team (acceptance pending). Existing art, realms, inventory and production interfaces stay additive. Component ownership remains in the canonical team registry.

## Shardstead: the Twakers' island activity

Talking to Twaker Prospector introduces **Shardstead**, surveys the island and opens the shared tab bar's **Production** page. The player explores on foot, claims authorized deposits, assigns workers, gathers cargo, befriends residents and trades. Twakers are Shard Lord allies: crystal collectors, cave chest keepers and guardians. Dialogue can resolve a guarded cache encounter; guardians must not all become disposable enemies.

Claims are gameplay leases subordinate to the existing land ownership table. A mining claim never mints a token, transfers an NFT, or grants permission to edit another owner's land. The server checks land permission, proximity and realm before accepting it. Immutable realm seed plus island number determine deposit makeup; surveyed deposits reveal remaining quantities and dominant ore. Finite veins deplete; renewable farming and energy need separate regeneration rules before release. Surface minerals, metals, underground crystal seams, salvage and craft inputs share canonical inventory identifiers; do not introduce competing catalogs.

M.U.L.E. reference: land development, assigned producers, food and energy dependencies, resource specialization and market bargaining. Its manual documents automatic production, energy requirements and supply/demand prices. Our implementation is original C++, not a port of proprietary source. Our extensions are explorable islands, ongoing host cycles, worker relationships, permit-based claims, guarded caves, ecology and physical cargo routes.

The portable Economy currently supports deterministic surveys, up to 256 crews and 10,000 claimed islands, one assignment per unique worker, bounded cargo, cycle sequencing, manual deposit extraction, consensual barter and explicit piracy-zone cargo raids. Production cycles are host-owned and sequential; missed cycles are not replayed from client time. Persist and restore cycles/ledger before enabling public play. Energy production precedes consumers. First slice uses finite resource quantities for all tasks; farming renewal is backlog work.

Piracy affects exposed cargo in designated conflict zones after host-confirmed combat. It does not steal deeds, shelter supplies, quest rewards, protected friendship items or blockchain assets. Friendly trade requires both authenticated acceptances; the in-memory barter validates both balances before mutation. Durable trades require a transactional host ledger and idempotent request IDs. No client should call the core using self-reported permission booleans.

Production tab: claims, deposit survey, assigned worker/job, remaining ore, current cargo, food/energy shortages, cycle, friendship and infamy. Reuse the existing realm-themed tab shell. Expedition: travel, prospect, extract, choose cargo to carry, return or negotiate; a failed extraction endangers carried goods rather than all inventory. Mining/building uses our existing persistent voxel layer and original recipes, with load-bearing cave supports, water-table changes, restorative tree tasks and faction permits as extensions.

## Talking-tree relic quests

Atari Raiders of the Lost Ark's manual describes exploration, inventory-gated access, a map-room clue and traversal hazards. Our **Root Atlas** chain uses original tree dialogue, a root compass, tide alignment, cliff traversal equipment and a submerged archive. No Indiana Jones characters, locations, film artifacts or copied maps. Talking trees remember island history, expose clue stages and ask for restoration before opening a route. The core mission catalog reuses DaedalusPortalQuest ordered authoritative events and replay protection; item gates and tide verification belong to host actor adapters.

## Unicorn missions: always helping

Use the pacing of open-world convoy, pursuit, escort and frontier rescue scenarios with original stories. Rescue captives, deliver medicine across a storm pass, protect refugees, recover stolen supplies and guide burning bulls safely to the sea. Unicorn rewards require successful good deeds; piracy and cruelty do not advance them. Keep the existing distinct-bull/legendary-pack reward component as the reward authority; the mission catalog does not replace that gate or issue items itself.

Initial coded definitions: A Stake in Shardstead, Roots Remember the Tide, The Crystal Accord, The Midnight Rescue Run, Medicine over the Pass, Cool the Burning Herd and Shard Lord's Hidden Ledger. The last is a Twaker production task, not a unicorn mission. Giver actor adapters must bind dialogue, authorized events and per-player progress. Persist/award atomically through the existing host inventory seam.

## New spooky realm: Hushveil (working name)

Separate realm and identity. Halloween assets remain in Labyrinth as requested; Hushveil adds suspense-focused houses, abandoned lodges, crypt paths and cooperative escape expeditions. Granny is a gameplay reference for avoiding a pursuer, hiding and escaping a house; its developer's store page describes sound-sensitive danger and hiding places. Build original pursuers, characters, layout and story.

Core loop: enter a haunted estate, listen and scout, find tools and clues, open an escape route, help trapped visitors, leave through its unique rainbow or dock. Sound propagates through rooms and doors with attenuation; dropped items, sprinting and creaky boards create investigate targets. Pursuer states: patrol, investigate, search, chase, return. Entering a hiding place while observed preserves suspicion; hiding cannot magically erase an active sighting. Puzzle layouts must guarantee reachable keys and at least one solvable route. Optional practice mode, subtitle/audio cue alternatives, adjustable scare intensity and opt-in expeditions. Failure costs the expedition attempt, not permanent metaverse land or wallet assets.

Portable DaedalusHushveilCore now models attenuated sound targets, investigate/search/chase states, observed hiding suspicion and bounded search decay. Room graph, navigation, actual hiding actors and escape puzzles remain pending.

## New family-survival realm: Hearthwake (working name)

Confirmed reference: 60 Seconds! / Reatomized, whose developer describes gathering supplies and family before shelter survival. Our version is a metaverse settlement of original households and chosen crews weathering the **Shardstorm**, with physical shelters, neighbors, trade, expeditions and rescue routes. No copied McDoodle family, nuclear-era setting, art or source.

Prepare: rescue residents, salvage supplies and reach a refuge before a locally scheduled storm. Sustain: allocate food/water, treat injuries, repair shelter, maintain morale and decide expeditions. Rebuild: connect neighbors, establish rain catchers/gardens, recover radio parts and open a safe route. Each household's daily decision is a revision-checked host command; pauseable/opt-in sessions avoid starving a family while the player is offline. Public persistent settlement time and personal survival-run time are separate.

Stats tab: days survived, residents' health/hunger/thirst/morale, food/water/medicine/parts, shelter integrity, expedition status and journal. Score days with surviving residents and community rescues; long-term success means a functioning community, not endless hoarding. Authenticated cooperative supply exchanges integrate Shardstead cargo without duplicating it. Inventory rewards and purchases never directly mint assets.

DaedalusRefugeCore currently implements a four-resident daily ration/health/morale/repair simulation, expected-day rejection, bounded supply receipts and all-residents-lost outcome. Multiplayer state, persistence, expedition lifecycle, selectable households, shelters, UI and actor adapters remain backlog work. Do not present this first source slice as a complete playable realm.

## Arcade Minesweeper

Added to the existing native DesktopGames catalog and factory. Original implementation supports 9x9/10, 16x16/40 and 30x16/99 boards; first-reveal neighbourhood safety, flags, zero-cell flood reveal, chord, win/loss, deterministic seed, restart and simulated active time. Uses existing cabinet rendering/input/options; no parallel cabinet or Java service. Native UE build and cabinet placement remain Claude's acceptance steps. Active seconds count accepted fixed simulation steps, not a benchmark wall clock.

## Blender delivery and Unreal acceptance

Six actual rigged GLBs plus editable blend and hash manifest: Twaker Prospector, Cachekeeper, Trader, Farmer, Energywright and Rescuer. Reused the owned shared humanoid builder, 14-bone rig and Idle/Walk/Attack/Hurt clips. These are art prototypes, not a claim of final character polish. Attack clip is available for tool motion; dedicated Mine/Trade/Repair clips are next. Actual files: C:/Users/730ri/Documents/Codex/2026-10-14/shardstead-workers.

Claude: review exact source head, build UHT/native plugin, add/verify Minesweeper cabinet choice, import the six GLBs using the existing skinned-cast pipeline, bind roles to existing cast IDs or agreed new IDs, then provide in-game screenshots/video. No asset is runtime-proven until visible evidence and registry status are recorded. Neither new realm is deployed by this document.

## Research sources

- Original M.U.L.E. manual mirror: https://www.niksula.hut.fi/~eesko/kamaa/mulemanual/Muleman.htm
- Original Atari Raiders manual mirror: https://www.atariage.com/manual_html_page.php?SoftwareLabelID=394
- Granny developer store page: https://store.steampowered.com/app/962400/Granny/
- Robot Gentleman 60 Seconds! page: https://robotgentleman.com/60seconds/

Research extracts inform mechanics, not copying names/art/code. Repository reuse found native DesktopGames registry, shared humanoid/rig builders, PortalQuest ordered progress, existing inventory and persistent voxel architecture. No unlicensed game source was imported.


UDaedalusShardsteadComponent supplies a Blueprint-visible host manager seam for crew registration, seed binding, claim/assignment/extraction/cycle commands and Production-tab DTOs. No tick, client RPC or replication is added. Host permission/proximity flags must come from trusted world checks; no client boolean is authoritative. This seam remains native-build pending and does not implement durable transactions or frontend widgets. Shared per-crew Economy cargo is provisional simulation stock; bind canonical inventory before live collection to avoid duplication.

Validation: MSVC C++17 /W4 /WX with exceptions disabled compiled the portable arcade registry, Shardstead economy/mission catalog, Hushveil and Hearthwake source; a small disposable smoke exercised first-reveal safety, duplicate-cycle rejection, stale-day rejection and valid mission definitions. This is portable source evidence, not UHT, client networking or live realm proof.
