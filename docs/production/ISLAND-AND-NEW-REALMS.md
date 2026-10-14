# Island production and new realm architecture — 2026-10-14

Owner: team-codex. Unreal integration handoff: unreal-team (acceptance pending). Existing art, realms, inventory and production interfaces stay additive. Component ownership remains in the canonical team registry.

## Shardstead: the Twakers' island activity

Talking to Twaker Prospector introduces **Shardstead**, surveys the island and opens the shared tab bar's **Production** page. The player explores on foot, claims authorized deposits, assigns workers, gathers cargo, befriends residents and trades. Twakers are Shard Lord allies: crystal collectors, cave chest keepers and guardians. Dialogue can resolve a guarded cache encounter; guardians must not all become disposable enemies.

Claims are gameplay leases subordinate to the existing land ownership table. A mining claim never mints a token, transfers an NFT, or grants permission to edit another owner's land. The server checks land permission, proximity and realm before accepting it. Immutable realm seed plus island number determine deposit makeup; surveyed deposits reveal remaining quantities and dominant ore. Finite veins deplete; food and energy use renewable island potential, with an emergency farmer ration when supplies are exhausted. Surface minerals, metals, underground crystal seams, salvage and craft inputs share canonical inventory identifiers; do not introduce competing catalogs.

M.U.L.E. reference: land development, assigned producers, food and energy dependencies, resource specialization and market bargaining. Its manual documents automatic production, energy requirements and supply/demand prices. Our implementation is original C++, not a port of proprietary source. Our extensions are explorable islands, ongoing host cycles, worker relationships, permit-based claims, guarded caves, ecology and physical cargo routes.

The portable Economy currently supports deterministic surveys, up to 256 crews and 10,000 claimed islands, one assignment per unique worker, bounded cargo, cycle sequencing, manual deposit extraction, consensual barter and explicit piracy-zone cargo raids. Production cycles are host-owned and sequential; missed cycles are not replayed from client time. Persist and restore cycles/ledger before enabling public play. Food and energy production precede mineral consumers. Food production precedes energy and mineral consumers; mineral-only manual extraction cannot mint food or power.

Piracy affects exposed cargo in designated conflict zones after host-confirmed combat. It does not steal deeds, shelter supplies, quest rewards, protected friendship items or blockchain assets. Friendly trade requires both authenticated acceptances; the in-memory barter validates both balances before mutation. Durable trades require a transactional host ledger and idempotent request IDs. No client should call the core using self-reported permission booleans.

Production tab: claims, deposit survey, assigned worker/job, remaining ore, current cargo, food/energy shortages, cycle, friendship and infamy. Reuse the existing realm-themed tab shell. Expedition: travel, prospect, extract, choose cargo to carry, return or negotiate; a failed extraction endangers carried goods rather than all inventory. Mining/building uses our existing persistent voxel layer and original recipes, with load-bearing cave supports, water-table changes, restorative tree tasks and faction permits as extensions.

## Talking-tree relic quests

Atari Raiders of the Lost Ark's manual describes exploration, inventory-gated access, a map-room clue and traversal hazards. Our **Root Atlas** chain uses original tree dialogue, a root compass, tide alignment, cliff traversal equipment and a submerged archive. No Indiana Jones characters, locations, film artifacts or copied maps. Talking trees remember island history, expose clue stages and ask for restoration before opening a route. The core mission catalog reuses DaedalusPortalQuest ordered authoritative events and replay protection; item gates and tide verification belong to host actor adapters.

## Unicorn missions: always helping

Use the pacing of open-world convoy, pursuit, escort and frontier rescue scenarios with original stories. Rescue captives, deliver medicine across a storm pass, protect refugees, recover stolen supplies and guide burning bulls safely to the sea. Unicorn rewards require successful good deeds; piracy and cruelty do not advance them. Keep the existing distinct-bull/legendary-pack reward component as the reward authority; the mission catalog does not replace that gate or issue items itself.

Coded island definitions: A Stake in Shardstead, Roots Remember the Tide, The Crystal Accord, The Midnight Rescue Run, Medicine over the Pass, Cool the Burning Herd and Shard Lord's Hidden Ledger. The last is a Twaker production task, not a unicorn mission. Giver actor adapters must bind dialogue, authorized events and per-player progress. Persist/award atomically through the existing host inventory seam.

## New spooky realm: Hushveil (working name)

Separate realm and identity. Halloween assets remain in Labyrinth as requested; Hushveil adds suspense-focused houses, abandoned lodges, crypt paths and cooperative escape expeditions. Granny is a gameplay reference for avoiding a pursuer, hiding and escaping a house; its developer's store page describes sound-sensitive danger and hiding places. Build original pursuers, characters, layout and story.

Core loop: enter a haunted estate, listen and scout, find tools and clues, open an escape route, help trapped visitors, leave through its unique rainbow or dock. Sound propagates through rooms and doors with attenuation; dropped items, sprinting and creaky boards create investigate targets. Pursuer states: patrol, investigate, search, chase, return. Entering a hiding place while observed preserves suspicion; hiding cannot magically erase an active sighting. Puzzle layouts must guarantee reachable keys and at least one solvable route. Optional practice mode, subtitle/audio cue alternatives, adjustable scare intensity and opt-in expeditions. Failure costs the expedition attempt, not permanent metaverse land or wallet assets.

Portable DaedalusHushveilCore now models attenuated sound targets, investigate/search/chase states, observed hiding suspicion and bounded search decay. Room graph, navigation, actual hiding actors and escape puzzles remain pending.

## New family-survival realm: Hearthwake (working name)

Scope: all life in the ecosystem; households/chosen crews are one subsystem. Confirmed reference: 60 Seconds! / Reatomized, whose developer describes gathering supplies and family before shelter survival. Our version is a metaverse settlement of original households and chosen crews weathering the **Shardstorm**, with physical shelters, neighbors, trade, expeditions and rescue routes. No copied McDoodle family, nuclear-era setting, art or source.

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

## Persistence protocol (next source slice)

DaedalusShardsteadCore exports versioned crew/claim/cycle snapshots and validates full restore candidates before mutation. Rejects cross-seed state, malformed identity, duplicate workers, unavailable owners, out-of-range islands/stock and deposits greater than their deterministic initial contents. Food and energy now use renewable island potential; minerals remain finite. Hungry farmers can produce one emergency ration; food runs before energy and mining. Manual mining accepts minerals only.

DaedalusShardsteadLedger wraps typed commands in a bounded request ledger and revision CAS protocol. Prepare operates on a copy, preserving committed state; export the pending snapshot, persist it transactionally at the expected old revision, and only then confirm the matching request/revision. Repeat request IDs require an identical payload; changed payload conflicts. Unknown storage outcomes remain pending. Cancellation requires confirmed absence of a commit. Snapshots retain requests and revisions across restore; receipt capacity fails closed instead of forgetting replay IDs. The first ledger supports 4,096 receipts; archival/partitioning is required for a long-lived district.

This is a storage protocol core, not a disk/database implementation. The existing Blueprint manager still operates the prototype Economy directly; replace that adapter with ledger-backed host transactions before public multiplayer. Bind canonical inventory within the same storage transaction, not a second grant after confirmation. No durable-backend acceptance is claimed.

## Richey's ecosystem and rescue refinement — 2026-10-14

Hearthwake is **for all life in the ecosystem**, not only households. Humans/chosen crews remain one part. Reuse existing Java SpeciesCanon, Species/Guild, Ecosystem/Community, ArkFleet/Voyage and Hold (ADR-019..023); do not create a second species catalog or fleet. Guild coverage includes MEADOW, CANOPY, POND, DECOMPOSER, STARBORN and MARINE. Rescue plants, fungi, pollinators, grazers, predators, freshwater animals, marine life and crystal-associated creatures into suitable habitats. Predators need segregated transport, plants/roots need propagation beds, fungi need moist substrate and marine passengers need tanks. Hearthwake is a survival realm and living sanctuary with biome restoration, not a warehouse of captured creatures.

Island arks carry out good-aligned unicorn quests: **All Life Aboard**, **The Sea Has a Heartbeat**, **Small Lives Count**. Boarding alone is not success: verify actual departure, safe arrival, suitable carrying capacity and restored destination habitat. Protect rescued passengers from cargo piracy. Quests, save statistics and payouts use one persisted rescue ledger; no awards for repeatedly loading/unloading the same life.

Existing Hold excludes MARINE founders on ordinary sky islands; keep that behavior. Explicit rescue missions can transport canonical MARINE life only with positive marine habitat capacity and deliver it to a prepared sanctuary. Java ArkRescue plans transfers against existing Community/Hold counts, validates canonical species and aggregate guild occupancy, debits the source on boarding and removes aboard counts on landing. It rejects stale balances and repeat event IDs; the host still needs atomic persistence, voyage validation and stable rescued-life identity binding before exposing it.

Daily survival now includes an island-rescue chance. **Daily chance** is configurable host policy (first code default 5%, a balance placeholder), sampled once after each completed day with survivors. A successful roll requests a rescue: the run keeps surviving until an actual island ark voyage safely arrives. Rescue luck never teleports the ecosystem or marks it saved by itself. Persist run seed and day so retries/reconnects cannot reroll. The host owns timing, authenticated settings and arrival verification.

Automatic rescue can be turned off. Turning it off before day one qualifies the run for **Longest Lived**; enabling it after survival begins permanently removes that run from the no-rescue ranking. Disabling later still changes play but does not retroactively erase prior assistance. Show this consequence before the toggle is applied. Longest Lived ranks best ongoing or completed no-rescue days per player. A separate **Most Saved** board ranks rescuers by distinct host-verified saved-life IDs across good rescue missions, including all ecosystem life. Re-saving the same life never increments it. Run records and both board maps have validated restore seams; actual public persistence/endpoints/widgets remain pending.

## Production display requirements and source

Supply display is a primary feature. SDaedalusShardstead is an embeddable Production page reusing DaedalusInventoryCore realm themes: six consistently ordered, labeled cards (food, energy, iron, copper, crystals, stone), prominent localized quantities, category labels, net-next-cycle forecast and text shortage warnings. A claims table names island, worker, job and remaining deposit; renewable habitats are labeled differently from finite ore. Missing host state displays --/waiting, never fake zero balances. Meaningful units and color-independent text keep counts legible. Forecast is simulated from the current authoritative snapshot and includes production input costs; it is not guaranteed yield. Refresh on host record updates/tab opening, not every render tick; forecast currently copies the bounded economy and should be cached by revision in the final host.

The actual Slate page is source-ready but not mounted into the existing global tab shell or runtime-verified. Claude owns native build/mounting and must show normal stock, shortage, unavailable state and large-number layouts in-game. No screenshot of an HTML mockup counts as proof of the Unreal UI.

Longest Lived also accepts host-persisted ongoing no-rescue runs after day one, so a living run can appear immediately. Day updates are monotonic; a finished run cannot reopen or gain more days. The board displays the best run per player and retains finished status. Turning rescue off mid-run only qualifies a new no-assistance run; settings and board updates share the same persisted host state.

Household daily core also exports and validates shelter snapshots (residents, ration stock, integrity and day). Persist shelter, all-life ecosystem state, run policy/day and leaderboards together; shelter restoration alone is not a complete survival save. Ledger restore now replays retained command history and checks exact final balances/deposits before accepting a snapshot.

## Local save storage and host transport source

RealmRecordStore follows the existing OceanChunkStore ownership/atomic-replacement pattern. A single process owns its configured directory for the store lifetime. Records bind realm/key/revision and payload with SHA-256, reject foreign/corrupt/trailing data, bound payloads to 16 MiB, clone mutable byte arrays, preserve old records on stale revisions and refuse non-atomic replacement. Same immediate revision plus identical bytes returns REPLAY; an incompatible write returns CONFLICT. File data is forced before rename; directory fsync and multi-machine database guarantees are not claimed.

DaedalusRefugeSaveCore encodes/decodes a bounded 4 KiB little-endian format for run policy/day/rescue state plus household snapshot. Decode validates the existing rule restore contracts before changing the output. Household day may lag an all-life run after that household is gone; a lost run cannot contain living household residents. This payload is one subsystem save, not the complete ecosystem or global rankings. Those must be bundled transactionally by the host before enabling public play.

RealmRecordService and RealmRecordController expose an explicitly enabled host-only transport at /api/v1/host/realm-records/{REALM}/{key}. GET returns payload bytes with X-Record-Revision and X-Payload-SHA256. PUT accepts application/octet-stream and X-Expected-Revision; UPDATED/REPLAY return 200, CONFLICT returns 409. Missing records return 404. Chunked input is bounded. A write I/O failure requires GET reconciliation; never assume no commit or create a fresh request solely after timeout.

Configuration: daedalus.realm-record.enabled=true, an explicit daedalus.realm-record.directory, and daedalus.realm-record.host-subjects listing trusted host JWT subjects. Disabled by default. Existing login tokens have subjects rather than a world-host role; this adapter uses the explicit server allowlist. Anonymous and ordinary player principals are rejected even in development. No issuer, role, login flow, public terrain route or live configuration was changed. New names here are storage namespaces; they do not register a new realm origin.

Evidence: portable MSVC compiled the save codec and generated a real native payload; Java stored it, observed same-write replay and incompatible-write conflict, closed the store, reopened it and read the exact bytes. Scratch evidence directory: C:/Users/730ri/Documents/Codex/2026-10-14/shardstead-source-check/refuge-record-proof-16325060455094580425. Maven server reactor compile passed with tests skipped. No live endpoint, native HTTP adapter or production restart proof is claimed.

The updated [production workbook](Realm-production.xlsx) retains the original registry and adds 18 island-pool meshes and six Shardstead worker prototypes, bringing it to 373 asset references. Source/export verification remains separate from native Play proof; the new island and live-survival rows are pending. This is a registry of asset references and scoped checks, not a count of the world's 49,000 land instances or completion of the 500-enemy/500-friendly population request.

Production display correction (2026-10-14): require exactly six nonnegative cargo quantities before showing a crew record as available. Incomplete forecasts are unavailable for all cards; unavailable crew records clear old claims and show a host-wait message. Zero stock remains a real shortage only for complete records. Shared-tab mounting, authenticated remote delivery, canonical inventory and native compilation remain pending; this source change does not assert gameplay proof.
