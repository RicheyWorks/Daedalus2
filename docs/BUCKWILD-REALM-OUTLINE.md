# Buckwild crew: finish every realm

Audit snapshot: 2026-10-14, Pacific time. This is an implementation outline and release-preparation record. No tests, builds, editor calls, chain transactions or deployment were run for this audit. Historical verification in ADRs is attributed to those records; new source and previews remain unvalidated.

## Current state and ownership

Daedalus was one enormous planet before the impact. Its fragments orbit inside the bubble; arks carry surviving people and animals between them. Each realm has its own look, rules, item catalog and inventory presentation, with mazes throughout. Sky gates require the realm's flying mount; PORTAL cubes enter seeded 8-bit adventures. Phase 2 introduces visitable moons and other bodies later. These constraints come from `docs/REALMS.md`, `docs/STORY.md`, ADR-029 and ADR-031.

The current checkout has `SKY_ISLANDS`, `PARCELS`, `BRICKS` and `GALLERY` ready; `LABYRINTH` is false in `daedalus-core/src/main/java/com/daedalus/world/WorldStyle.java`. The Portal Realm and Orrery are existing separate systems, rather than additional enum values. A browser preview does not change these generator flags or establish native gameplay.

Pootscoot's requested pipeline reply arrived as hub 30757. Read-only source inspection also found newer architecture in `C:/Users/730ri/.codex/worktrees/island-mesh-pool/Daedalus2/` (called the **newer source checkout** below): ADR-065, realm casts/buildouts, and the provider-aware directory. That source is not presumed installed in this checkout or live. It maps known session IDs `WORLD-ZERO`, `GALLERY-CITY`, `PARCELS`, `BRICKS`, `LABYRINTH`, plus opt-in `OCEAN`; `PORTAL` is separate DRR/SHARDLANDS with multiple seed instances. Directory reads require authentication even outside prod; a catalog stem does not prove installed content, editing rights or travel. The proposed `REALM-LAND-API.md` referenced in the reply was not found in either inspected checkout.

| Realm | Documented stage | Buckwild ownership and integration partner | Immediate finish target |
| --- | --- | --- | --- |
| Shattered Planet: Sky Islands and Lands | LIVE in `REALMS.md`; existing browser realm | `realm_audit`: `/sky-expedition.html` visitor source and release preparation. Claude/unreal-team: native runtime; established island creators retain their land/art claims | Ark route atlas/local journal plus honest land release catalog; then authoritative survival/crafting/travel integration |
| Portal Realm | LIVE in `REALMS.md`; generated DRR 1 and native RPG | `portal_coder`: `/portal-expedition.html` source. Existing native realm owner and `codex-buckwild-bricks` controller helper retained | Controller-readable browser expedition, followed by native party/save/music bindings |
| Parcels | SERVER; existing browser district | `parcels_coder`: `/parcels-realm.html` source. Existing Java/native owners retained | Plot discovery/building browser flow; accurate plot deeds and native district |
| Bricks | SERVER; existing browser obby | Existing `codex-buckwild-bricks` Stud Relay owner | Integrate the existing relay source and native obby without duplicating its files |
| Gallery City | SERVER; existing browser gallery | `buckwild-sol`: `/gallery-city.html` and common `/metaverse.html` source | Curatorial maze exploration and realm hub, then walkable art/plot deeds |
| Orrery Reach | LIVE + web view in `REALMS.md` | Claude/unreal-team; shared livestock by youtube-master | Complete persistent logbook, shared food/water loop and honest finale boundary |
| Labyrinth | NAMED; generator flag false | Existing `buckwild-labyrinth`/`codex-buckwild-labyrinth` route source owner | Integrate Broken Survey chalk routes into a registered, walkable realm |
| Ocean | Opt-in SERVER provider in newer source; separate native delivery records | Existing team-codex/Pootscoot Ocean host/travel owners | Durable authenticated sector, boarding/exit and per-player travel integration |
| Space | NAMED, Phase 2 | Future realm owner to be claimed on hub | One original moon vertical slice after the existing travel/persistence boundaries are ready |
| Sol Reach | Existing Portal district; native integration pending | Historical `team-codex` district; Pootscoot/shared homestead integration | Resolve recorded execution hold and wire its actual transactions, journal and scene |
| Lantern Reach | PROPOSED N64-era exploration source | Existing `codex-buckwild-n64` owner | Host allocation, durable integration and terrain/gameplay, without claiming a live realm |

Every member owns a distinct realm slice. Root coordinates the common hub and Gallery City. No assignment transfers existing author, deed, editor, importer, or shared-system ownership.

## Engineering pipeline and communication

The actual shared handoff root is `C:/Users/730ri/projects/bot-team/`, outside this repository. Start with `BOARD/ARCHITECTURE.md`, `BOARD/LANES-UNREAL-CODEX.md`, `BOARD/UNREAL-QUEUE.md` and `BOARD/LESSONS-LEARNED-UNREAL.md`. The architecture board contains the current priorities; `docs/handoff/README.md` concerns old GitHub chores and is not the active realm delivery queue.

1. Read the architecture board and latest relevant hub messages. Post the realm, exact new/owned paths, branch, and intended behavior. Match another owner's claim before touching their files. Existing cross-lane work uses a PR and hub ping according to the lane record.
2. Ask Pootscoot for active source claims, branch/integration policy, inventory authority, deed-to-land mapping, and the acknowledged editor operator. Root sent introductions in 30750/30751 and corrected allocation in 30754/30755 under `buckwild-sol`. Reply 30757 acknowledges this separate crew and requires exact claimed-file commits, preserved prior edits, and head/file/routes/schema/source-limit handoff. Poot reviews source integration; no automatic merge, deployment, tests or editor transfer follows.
3. Use the existing broker at `127.0.0.1:9890`, or the file bridge from `docs/TEAMLINK.md`. Append newline-terminated JSON to `bot-team/link/outbox/<alias>.jsonl`; read the matching inbox. Register handles, heartbeat, and acknowledge messages actually handled. Use `READY <artifact> <commit>` and `NEED <exact dependency> + DEFAULT <independent next work>`.
4. Keep portable realm rules in existing Java/plain-C++ cores, source data in `data/`, and versioned engine contracts at the established seam. Reuse existing WorldHub, world package, HTTP/STOMP, inventory, save, sky-clock and homestead systems. The user has deferred separate tests; all new source is labelled unvalidated until actual integration evidence exists.
5. Produce art with original names and the realm tag. Keep editable sources and creator provenance. The existing path is Blender source/export -> `.glb` plus `.sent.json` or the owner's compatible FBX manifest -> queue/importer -> native import completion -> individual asset saves -> owned world placement -> map save. Preserve the working importer and prior originals.
6. The art board owns `TODO -> DOING -> READY -> SHIPPED/REJECTED` status. Treat bridge/environment failures as `BLOCKED`; report the exact operation and expected/observed result. A READY row, imported mesh, saved map and playable feature are four different stages.
7. Queue native wiring with exact source head, input contract, target level/actor, finish condition and rollback path in the established Unreal queue through its owner. The acknowledged operator performs shared native work during their granted slice. Finish with saved asset/map paths and explicit editor release.
8. Keep new code and exports moving in parallel with ingestion. The architecture board's current instruction explicitly allows continued production despite the import backlog. Improve one coherent exemplar and propagate its useful changes; quantity alone is not appearance, movement, or performance evidence.

Observed coordination snapshot, not a lease for this crew: hub 30752 records `codex-play-guard` as the sole editor operator scheduled through 13:40 Pacific on October 14, with Fable returning at 13:20 Pacific. Hub 30745/30747 reports that operator's preceding turn failed at a usage limit and is idle; a held lock is not proof of current execution. Existing reported delivery is three island payloads plus twenty-one modules, forty-seven saved meshes and zero world placements at that checkpoint. Re-read the latest accepted handoff before any native work.

The read-only art status snapshot was last updated 2026-10-13T06:05:14: 6,259 rows, including 4,589 SHIPPED, 1,381 READY and 279 BLOCKED; it says it is waiting for the Unreal bridge. These are stale board counts, not a fresh asset/runtime census. Do not add them to modern batch counts or infer deployed land.

## Shared NFT land release work, in order

Existing implementation evidence: `chain/contracts/RealmIslands.sol`, `chain/scripts/deploy.ts`, `chain/README.md`, `daedalus-wallet`, `WalletController.java`, `WalletProperties.java`, ADR-026/027/028. Existing claims and ERC-721 island vouchers are source; no deployment or current mint was observed in this audit.

1. **Use the recorded canonical land design.** Newer ADR-065 specifies `(realm, number)` with numbers 0..9999, ten thousand lands per realm, spiral cells, estates, and separate saved land-to-cell mapping for tugging. Its status is proposed and item/reward details are undecided; it is a documented owner goal, not generated supply or mint availability. Resolve its mapping to legacy world/slot IDs, production ledgers and Reaction/Diffusion/Song tokens. `STORY.md` still contains the earlier token question. Obtain the authoritative registry/API implementation from its owner before assigning deeds; geometry or staging coordinates do not prove ownership.
2. **Remove legacy world/slot collisions before a wider release.** In this checkout, `RealmIslands` token IDs are lane slots, its `Deed` has no realm/world ID, and `WalletProperties` holds one global deed contract. Align the actual minting system with ADR-065 realm/number identity using an explicit realm-aware mapping or reviewed namespace. The older collection-per-style charter also needs unique IDs across multiple worlds of one style. Preserve the starter lane while integrating the newer grid.
3. **Define land for every style.** The island voucher route reads `worlds.islands(id)` and island seed/radius. It does not establish Parcels/Gallery plot vouchers or Bricks/Labyrinth/Space ownership. Add style-specific land identity, bounds, reserved common areas, metadata and signing contracts through the existing authority. Do not represent missing plot minting as existing NFT functionality.
4. **Make ownership follow the chain.** Integrate confirmed `ownerOf`/transfer reconciliation with persisted claims, owner builder permissions, pending confirmation/reorg handling and unavailable-RPC behavior. ADR-028 explicitly holds chain-following claims. Define what happens to builder grants on transfer; old owner's permissions must not silently continue.
5. **Prepare durable metadata and promised bundle identity.** Preserve the island seed/radius portrait and distinguish original land from player modifications. Add realm/number, position rank, size/richness tier, promised included items and truthful entry URLs. ADR-065 proposes mint bundles, an egg with Portal land, rarity and an independent shiny roll; odds, boost values and reward formulas remain owner work. Keep egg identity through hatching, and use the established chain team's provable-randomness contract rather than a browser loot roll. Produce content-addressed metadata/image references through the existing publishing lane; pinning is held in ADR-027/028, not completed here.
6. **Prepare the concrete launch packet.** Include selected network, exact contract/source/deployment record, signer address and secret-management owner, canonical supply/allocation, authorized mint flow, metadata provenance, ownership rules and user-visible missing dependencies. No invented sale price, launch date, supply or funded keys belong in a preview.
7. **Execute only the existing owner deployment process when authorized.** The present pipeline supports Sepolia with a dry run, typed phrase, fee cap and deployment record. Its mainnet refusal remains. The charter places mainnet behind a Safe and audit. This source sprint does not send transactions or announce a sale.
8. **Report each stage separately.** Source prepared; deployed contract; pinned metadata; redeemed deed; reconciled claim; accessible gameplay. `realm-release-catalog.json` intentionally supplies preparation/status, never a mint button or an ownership grant.

## 1. Shattered Planet: Sky Islands and Lands — realm_audit

Evidence: `docs/REALMS.md`; `docs/STORY.md`; `docs/ECONOMY.md`; ADR-018–028, 049–050, 054–055, 062–064; `world/island/IslandGenerator.java`; `WorldService.java`; `/realm.html`; `data/economy/{items,stations,recipes}.json`; `data/water/water.json`; `data/livestock/animals.json`; `data/survival/stats.json`.

Story goal: make each surviving fragment a place to settle, restore life and maintain an ark route. Rare impact minerals belong in the old crust/meteor-fragment economy. Genetic coats retain their genome identity; gear dyes do not recolor the animal's inherited coat.

1. Deliver `/sky-expedition.html` with read-only actual island/gate/fleet DTOs, stylized floating-fragment canvas and explicitly local ark routes, finite camp supplies, habitat surveys and journal. When the server is unavailable, use a separate deterministic visitor draft. Source is written, with no browser/test/build proof. Keep `/realm.html?world=world-zero` as the existing server-world entry. Reconcile ADR-065 realm/number identity, estates/tug mapping and starter lane with Pootscoot's authoritative registry before assigning deed IDs. Ten thousand per realm is the recorded design target, not a fresh generation or sale count.
2. Bind the established inventory and crafting authority to a complete hands -> gather -> process -> mine -> smelt -> tools/ark repair loop. Use current data IDs and real transaction outcomes. Reconcile draft economy terminology with actual ore types before adding incompatible rows.
3. Complete clean-water, thirst, food and livestock production through the shared homestead implementation. Bind sustainable regrowth to existing ecology. Dry animals stop producing; invalid recipes consume nothing. Save finite resources and quest memory through existing persistence.
4. Finish island dressing with ground-fitted town, flora, ore, creature, station and ark parts. Improve one spawn-to-mine-to-dock route before scaling more variants. Preserve earlier authors' terrain/assets and production allocations.
5. Bind original shard/ruin objectives to existing maze stamps, combats and ark voyages. Each objective should use actual inventory/travel completion, survive save/reload and carry a clear hint toward another realm's rainbow.
6. Complete the assigned realm's unique rainbow, cloud/dust trail and mount-to-gate return route. Use the shared travel system and non-color navigation cues. Keep Phase 2 celestial bodies as a story hook until their gameplay exists.
7. Integrate existing LOD/DSB/streaming work through the native owner's build slice. ADR-063/064 contain measured source results and pending Unreal bindings; do not promote their written budgets to fresh native performance claims.
8. Deliver island-specific metadata, authoritative claim/transfer mapping, pinned provenance and the owner launch packet through shared NFT steps 1–8. A seeded source island or imported staging mesh is not released NFT land.

Remaining uncertainty: current native gameplay, current ledger/deed allocations, shared source compilation, chain transfer following and public deployment were not rechecked. This crew's concrete deliverable is the Sky Expedition visitor source (`docs/realms/SkyExpedition.md`), catalog and ordered implementation handoff. Visitor actions never issue voyage/harvest/claim/mint requests or credit server inventory.

## 2. Portal Realm — portal_coder

Evidence: ADR-052; `world/retro/{RetroRealmGenerator,RetroCodec,RetroProgress}.java`; `RetroRealmController.java`; `DaedalusRealmCore.h`; native `SDaedalusRealm`; `docs/realms/SolReachRuntime.md`; hub 30740 controller source claim.

1. Deliver `/portal-expedition.html` as a clearly labelled browser source preview using original places, creatures and existing realm seeds/specs. Give the expedition a readable party, inventory, hint and return flow.
2. Keep the actual Java DRR 1 realm as the authoritative generated map. Reuse planted story keys, tiered locks, dead-end treasure, encounter zones, shops, inns and the shard tyrant; do not substitute a second progression engine.
3. Preserve hero/sage/scout party and turn commands. Integrate the existing controller profile owner’s new `DaedalusPortalControls.h` into native presentation only after their source handoff; input prompts must reflect the active layout and release held controls on exit.
4. Bind actual party identity/presence, realm-scoped save slots, quests and inventory through existing owners. Fix any existing global save-slot sharing before private progress is represented as deed-bound.
5. Have the jukebox team name its real endpoint, then connect FIELD/TOWN/CASTLE/CAVE/BATTLE/BOSS/VICTORY cues with original music and actual playback. A cue log is not audible proof.
6. Finish first-floor discovery, bronze/silver/star key chain, guardian victory and portal return as one coherent adventure. Integrate sprite rows through the existing queue when that path exists.
7. For NFT land, bind the portal seed and journal to canonical PORTAL/number through an authenticated host deed. Newer `DRR-EGG-LAND-PARITY.md` records DRAGON_EGG and validated land annotations with no owners by default; demo HERO/OSTRA labels are not deed authority. Integrate registry overlays/cache invalidation and the shared egg lifecycle without minting a second token on hatch. Party gold/keys and cross-realm movement need explicit contracts; a seed instance is not a new canonical realm.

Remaining uncertainty: fresh native/controller/audio play, presence integration and live deed-bound save behavior are unverified. ADR-052's previous seed checks are historical evidence only.

## 3. Parcels — parcels_coder

Evidence: ADR-033; `world/district/DistrictOps.java`; `WorldService.java`; `WorldController.java`; `WorldPackageService.java`; current `/realm.html` plot flow.

1. Deliver `/parcels-realm.html` with plots, plaza, height limits, ownership affordances and a helicopter/gate objective. The existing generator has sixty claimable plots; this is the documented generator layout, not NFT release supply.
2. Use `/api/v1/worlds` to select an actual mounted PARCELS world. Read its `/plots`; do not invent a production world ID or substitute local mock ownership for server claims.
3. Bind claim/build/builder/abandon actions to authenticated principals and existing responses. Keep streets, plaza, unclaimed plots and above-limit writes reserved/refused through server authority.
4. Finish a coherent public-plaza -> claim -> build useful scene -> discover rainbow -> fly helicopter -> return loop. Extend maze stamping only through the existing owner/bounds rules.
5. Provide a native renderer and helicopter placement through World Packages and the established art/import lane. Smooth low-poly appearance is held in ADR-033; a exported cube district is not finished native art.
6. Define plot deed IDs/bounds/height and authoritative metadata, then integrate plot vouchers and transfer reconciliation under shared NFT steps. Preserve public streets/plaza as common land; island seed/radius vouchers do not already cover these plots.
7. Leave adjacent estates and additional districts as explicit follow-up scope until the owner allocates them. Deliver actual source head and known native/deed blockers to Pootscoot.

## 4. Bricks — existing Stud Relay crew

Evidence: ADR-034; `world/bricks/BricksOps.java`; existing `/realm.html` obby; hub 30707/30738 identifies draft PR148, source `3e08fcf8`.

1. Take the existing Stud Relay worker's exact source and contract handoff. Preserve their four new files; source publication does not establish integration or a runtime victory.
2. Finish spawn, checkpoint progression, hazard reset, trophy finish and a return path using the existing obby's bounds. Make avatar movement and controller focus readable with the realm's own item catalog/theme.
3. Bind the relay objective and checkpoint persistence to actual host identity. Server-authoritative leaderboard timing/presence is held in ADR-034; local client times are previews until that authority exists.
4. Integrate the blocky avatar, bright studs, plane and runway through the existing native import/render lane. Studs in exported GLB remain an engine presentation task according to the ADR.
5. Link the plane to the unique realm rainbow and a paired gate. Preserve common spawn/runway and avoid creator-owned kill/hazard edits until the existing owner adds that surface.
6. Define Bricks land bounds, common areas, builder permissions and deed metadata before a sale. No Bricks-specific deployed land contract is established by the island contract; route it through shared NFT work.

## 5. Gallery City — buckwild-sol

Evidence: ADR-035; `world/gallery/GalleryOps.java`; `WorldController.java` gallery route; `WorldPackageService.java`; existing `/realm.html` gallery flow.

1. Deliver `/gallery-city.html` and `/metaverse.html`: navigable city/archive, original curatorial story, discoverable maze works and honest links to each realm's actual entry or source preview.
2. Read the mounted GALLERY world's addressed parcels, street names, height limits and frames through the existing API. ADR-035's sixty-eight parcels are generator inventory, not an announced NFT sale supply.
3. Keep parcel claims/build permissions authoritative and Origin plaza public. Add a useful first exhibition with clear curation and discovery hints, rather than counting duplicate frames as new gameplay.
4. Connect each maze artwork's seed to an existing generated walkable maze and a return link. A flat frame or drawn solution is not yet its dungeon; ADR-035 explicitly holds that bridge.
5. Ship original pastel architecture, sculpture/frames and drone through the existing queue. Bind the drone, dust trail, realm rainbow and paired gate in native gameplay.
6. Finish parcel metadata and content provenance. Parcel ownership and artwork provenance are separate records; adding an image to a frame does not mint the art. Integrate gallery land via the shared plot namespace/voucher/transfer work.
7. Publish the curatorial source slice and exact dependencies, then let the established native owner accept the editor integration handoff.

## 6. Orrery Reach — Claude/unreal-team

Evidence: ADR-057/058; `docs/realms/OrreryReach.md`; `DaedalusOrreryCore.h`; `DaedalusOrrery.h/.cpp`; `VoxelIsle.java`; `/reach.html`; `GET /api/v1/reach/orrery`; `tools/claude_island/orr_*`.

1. Preserve the five original isles, existing Orr assets and authored Keeper story. After adopting the shared double-precision shape core, ground-fit props through the owner's placement scripts; old transforms can differ by a terrace step.
2. Complete Starbloom harvesting by the shared sky hour, real clean-water consumption, teas, constellation pairs and eclipse combinations. Reuse the realm subsystem/core and persist its satchel/charts/logbook through the existing save owner.
3. Integrate youtube-master's shared livestock for hens/goats/sheep and honey only near blooming beds. Keep crop/animal production finite and tied to real supplies, never decorative implied inventory.
4. Complete chart puzzles and the vault finale using actual objectives. Resolve the difference between the design logbook and implemented nine-step sequence with Claude before adding parallel quest rows.
5. Connect real jukebox dialogue/music and the player's input/inventory themes. The existing `/reach.html` is a web view, not proof that every native quest can be played there.
6. Keep telescope/new-moon interaction explicit as a Phase 2 hook while visitable moon gameplay is pending. Do not claim the Phase 2 finale complete from art placement.
7. Map each authored isle/sublevel to allocated authoritative land before minting; bespoke VoxelIsle settings are not automatically RealmIslands lane slots. Publish style-specific metadata/provenance and shared deed reconciliation.

## 7. Labyrinth — existing Broken Survey route crew

Evidence: `WorldStyle.LABYRINTH(false)`; ADR-029; existing maze generators/solvers/stamp APIs; newer source `docs/realms/LABYRINTH-BUILDOUT.md` and `REALM-CASTS.md`; hub 30705 and 30738. Claimed route source: `world/labyrinth/LabyrinthRouteSession.java`, `LabyrinthRouteSnapshot.java`, native `Labyrinth/DaedalusLabyrinthRouteComponent.h/.cpp`, source `6023649e` in the other worker's checkout.

1. Preserve that worker's exact Java/native claim and ask for its checkpoint/snapshot contract. Keep new browser/art work separate until a concrete complementary scope is accepted.
2. Finish the already-authored Broken Survey chapter, entrance, torch/stone palette, useful clues and safe exit using existing maze generation. Preserve original Ari/Wayfinder cast and the completed first art-kit claim. Halloween belongs here; friendly carnivorous plants guide/aid players and defend only against active hostile threats. They never harm players, allies or companions. Treat the region as a remnant of the shattered planet, with clues toward repaired routes/Heartstones.
3. Implement a registered Labyrinth generator/mount/manifest through the existing WorldHub owners. Keep `ready=false` until an actual generator/renderer is integrated; the existence of a generic maze API does not make a new world ready.
4. Bind Broken Survey chalk, erosion and retained lesson credit to authoritative identity, current revision and durable snapshots. Reuse existing chalk/plant/maze logic rather than introducing an overlapping reward or inventory system.
5. Complete one walkable dungeon with routes, guards, locks/rewards and checkpoint recovery. Link Gallery maze art only through the explicit seed/return contract.
6. Ship original stone/torch/gate/trap art and native component bindings through the established owner slot. Source-only route components remain unvalidated.
7. Decide whether maze land is an existing deed's attached dungeon or an allocated new land parcel. Then supply exact bounds/seed/generator/metadata and shared transfer authority. A replay snapshot is not an NFT ownership record.

## 8. Ocean — existing optional provider

Evidence in the newer source checkout: `RealmDirectoryService.java`; `docs/production/REALM-DIRECTORY.md`; `OCEAN-HOST-API.md`, `OCEAN-CHUNK-PERSISTENCE.md`, `OCEAN-DOCK-TRAVEL-CONTRACT.md`, `OCEAN-PASSENGER-SESSION.md`, `OCEAN-HARBOR-DELIVERY.md`; shared board Ocean owner claims.

1. Preserve the optional Ocean host and its `OCEAN_V1` protocol. Discover it through the authenticated provider directory only when actually configured; do not copy its terrain into WorldService or infer block-edit permission.
2. Use the current host's seeded sector, immutable chunk persistence and bounded chunk-window API. Fetch manifest bounds first; keep auth/session and cancellation contracts in the existing native client.
3. Finish dock proximity/boarding, vessel identity, passenger session, remote exit and keyboard/controller interaction through the established Ocean owners. Historical proof files are not fresh runtime evidence.
4. Wire per-player realm travel and safe return through the shared native session/WorldActor owner. A dock interaction, hull or painted sea alone does not grant realm transfer.
5. Ground-fit the existing harbor kit, vessels and original marine life. Tie quests/resources to impact-surviving water fragments and existing crafting/inventory authority.
6. Define water/harbor land identity and reserved travel areas under canonical OCEAN/number before NFT release. The optional chunk provider has no edit API and is not an ownership allocator. Host configuration, current native integration and public play remain unverified.

## 9. Space — Phase 2, named only

Evidence: `docs/STORY.md` planet section; `docs/REALMS.md` Phase 2 row; Orrery telescope story.

1. Claim an original moon slice on the hub and specify its allocation/travel boundary. The story promises eventual moons/suns/planets/meteors/Earth, not an implemented space backend today.
2. Reuse WorldHub/package/seeds, streaming, ark/mount and shared persistence. Build one reachable body with arrival, exploration objective and safe return before multiplying planets.
3. Tie the first arrival to the repaired Orrery telescope and existing travel authority. Planet fragments, debris and meteor resources remain consistent with the impact story.
4. Deliver distinct gravity/environment/navigation/vehicle rules as explicit versioned realm behavior. Bind life-support/resource use through the existing inventory owner and real finite transactions.
5. Define orbital/body land coordinates, bounded claim areas, public arrival zone and namespace before any NFT mint. Do not announce Earth or planetary allocation/supply from a scene prototype.
6. Advance the stage only with actual source, export, native save, travel and deed evidence. Current status stays NAMED.

## 10. Existing Sol Reach district — historical team-codex

Evidence: `docs/realms/SolReach.md`; `SolReachRuntime.md`; `docs/mechanics/RingInfusion.md`; `DaedalusSolReachCore.h`; `DaedalusSolReachJournal.h/.cpp`; `tools/islands/sol/`.

1. Keep this orchard/waterworks as a Portal Realm district, with its existing origin/layout; this crew does not claim its allocated land or files.
2. Obtain the actual Norton detection/path review and owner disposition before reviving the recorded native execution hold. New source elsewhere can continue independently.
3. Wire the shared homestead inventory/water/livestock transaction into the existing journal. Add a generic ordered Ring Infusion hook, not a second brew engine; consume actual herbs and clean water atomically.
4. Bind keeper schedule/memory and stair/clue rendering to the single Sky Director, actual proximity and native destinations. Persist owner-only discoveries using the authenticated deed service's supplied journal key.
5. Import and ground-place accepted art in its owned child level through the acknowledged editor owner. The runtime document records 505 queued assets and pending native integration; it does not establish a current imported/native census.
6. Enter/return through the existing seeded Portal Realm after the water/meal progression. A land NFT identifies the fragment and grants no free herbs, meals or livestock outputs.

## 11. Proposed Lantern Reach — existing codex-buckwild-n64

Evidence: hub 30729/30748; owner-reported draft PR149, source `e809a729`; four new exploration Java files and `docs/realms/LanternReachExploration.md` in its separate checkout.

1. Keep the design ID provisional. Have the existing host/directory owner allocate a realm/world identity before enabling its default-disabled host adapter.
2. Integrate the immutable definition/progress/snapshot and replay/CAS boundary with the established durable authority. Preserve return capacity and existing inventory/session semantics.
3. Build original compact hub/world terrain, visual portals, collectible objectives, movement routes and secrets through the existing modular art lane. Reuse original creator references with credit.
4. Bind its actual native movement/collision, saved objectives and portal returns. Written placement definitions and a published PR are not generated/exported terrain or a playable realm.
5. Define land allocation/metadata only after identity and terrain are allocated. Apply the common deed namespace and transfer rules; do not mint provisional IDs by assumption.

## Crew delivery and hourly reporting

The source catalog is `daedalus-server/src/main/resources/static/realm-release-catalog.json`. Root's `/metaverse.html` can display it alongside Gallery, Parcels and Portal source previews. Realm IDs in that file are directory labels; they do not allocate production world IDs, land or NFTs.

Each crew handoff records realm, author, elapsed active minutes, source paths, added/removed code lines, concrete complete behaviors, reuse, source head, known blockers and integration stage. Report code/hour as a measured rate over the actual elapsed window, with the window shown. Generated metadata/art variant counts remain separate from authored gameplay and accepted/saved content. Do not extrapolate a completed hour or claim deployed/usable features from line count.

Current audit scope covers this repository, read-only shared boards/log/status, and selected newer source files named above. No applicable `AGENTS.md` was found in this repository or its checked ancestors. Pre-existing `STORY.md`/`ECONOMY.md` edits were preserved. No external repository PR contents or blockchain state were fetched; PR heads and latest editor statuses above are attributed to the hub. The existing LoadBalancerPro handoff marks issue filing/Dependabot chores complete and Codecov activation optional/pending; those tasks do not block this realm source sprint.
