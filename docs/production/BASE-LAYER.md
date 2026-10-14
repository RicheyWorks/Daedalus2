# Base layer per realm — what must be laid down before polish

Richey, 2026-10-13 19:30: *"review all the excel and md and make sure they are detailed enough to build out each
realm... the base layer of the architecture... shift building focus to get everything laid down in each realm then
polish"* and *"the earlier we can launch the NFTs for sale the more income we have to build and upgrade."*

This is the merge of `Realm-production-2026-10-13.xlsx` (Production, Assets, Mechanics, Unreal verification),
`docs/production/*.md`, `docs/realms/REALM-CASTS.md`, `docs/adr/ADR-065`, the shipped `.dic`/`.dcs` files and the
live editor. One table per realm; every row says **done / partial / missing**, who owns it, and where the evidence
is. A realm is "laid down" when every row is at least *partial* and the mint row is *done*. Owners: **Fable** (UE
plugin C++, editor Python, live editor, hero/WorldActor/Streamer), **Sol** (Java server, Blender art, Ocean*,
merge queue), **Poot** (cabinets, photo/image objects).

## The base layer, defined (the same 12 rows for every realm)

| # | Layer | What "laid down" means | Spec |
|---|-------|------------------------|------|
| 1 | Grid + hub | 100x100 spiral cells, pitch 256 m, hub cell (50,50) at the realm's spawn; districts 10x10 | ADR-065, `DaedalusLandGrid.h`, `daedalus_land_grid.py` |
| 2 | Terrain host | the ground the lands sit on, streamed by district | ADR-063 streamer, EXPLORATION-TERRAIN.md (LAND01) |
| 3 | Lands laid down | plot markers for every mintable cell/estate, deed number visible, nothing overlapping | `daedalus_layout.spiral_*` (step 1 done), plot markers (step 2) |
| 4 | Mint row | server knows the realm's lands: number, estate size, contents, owner; contract signs realm+number | ADR-065 rule 7 bundles, PORT06/PORT12, Sol audit 29124 |
| 5 | Cast (DCS) | the realm's speaking roles in `Content/Casts/<realm>.dcs`, Talkers bound to imported meshes | DCS-1, REALM-CASTS.md |
| 6 | Creatures / foes | the realm's enemies and friendlies spawned by Encounters, with art | GALLERY-CREATURES.md, CAST01 (50x10 each side) |
| 7 | Items (DIC) | the realm's catalog in `Content/Inventory/<realm>.dic` with its UI era | DIC-1 |
| 8 | Dialogue theme | the realm's box style (FF1 / Animal Crossing / ARC tabs) | DaedalusDialogueCore Style |
| 9 | Mounts / vehicles | the realm's ride, possessable | REALM-CASTS (drone, helicopter, plane, sky-strider), BRK03 |
| 10 | Docks / gates | how you arrive and leave: gate from World Zero, docks to Ocean, portal cubes | DaedalusRealmSessionCore Realms() table |
| 11 | Server endpoints | `/api/v1/realms` row with `realm` + `catalog`; lands/deeds endpoints | REALM-DIRECTORY.md (PR80), Sol |
| 12 | Play proof | one `run_scenarios.py` scenario that walks the realm: spawn, talk, pick up, fight, leave | `daedalus_play.py` |

## WORLD-ZERO (hub, catalog `world-zero`, theme `zero`)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | hub = persistent level footprint centre (14850,-9500) cm, 432 m square; cells 49..51 reserved |
| 2 | Terrain host | **done** | Fable | DaedalusWorld persistent level, 1863 static meshes, PCG |
| 3 | Lands laid down | **partial** | Fable | 14 team islands on estates deeds 9..59 (dab971586, 7552 actors, undo table saved). Missing: plot markers for the rest of ring 1..N |
| 4 | Mint row | **missing** | Sol | contract signs `to,slot,seed,radius,deadline` only, 64 slots, no realm/estate/egg fields (29124). Needs realm-aware mint design |
| 5 | Cast | **partial** | Fable/Sol | Keeper Ostra speaks via dialogue; no `world-zero.dcs` (cross-realm NPCs in REALM-CASTS §165 unbound) |
| 6 | Creatures | **partial** | Fable | Encounters spawn foes (AlwaysSpawn); 10 enemy candidates validated of 500 |
| 7 | Items | **done** | Fable | `world-zero.dic` 14 items |
| 8 | Dialogue theme | **done** | Fable | `zero` |
| 9 | Mounts | **partial** | Sol | boats/subs at docks (OCE01..03), no land mount |
| 10 | Docks / gates | **partial** | Fable | rainbow gates to 4 realms (ADR-053) as TargetPoints; HasDocks=true in Session table, no dock actors placed |
| 11 | Server endpoints | **partial** | Sol/Fable | `/api/v1/realms` merged (PR80); land districts `/api/v1/realms/{R}/lands?district=` in PR85; consumers `DaedalusRealmDirectoryCore.h` (WorldActor LoadDirectory/TravelToRealm: a gate makes the actor host the directory's world) + `DaedalusLandRegistryCore.h` + `daedalus_land_sync.py` (bridge `daedalus.land_sync`): agree/moved/only-server/only-editor/reserved, editor follows the server's cell, nothing deleted |
| 12 | Play proof | **done** | Fable | realm 10/10, inventory 10/10, dialogue 7/7, realm_switch 9/9 |

## GALLERY-CITY (catalog `gallery-city`, theme `gallery`, mount drone)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | origin in `daedalus_realm_ground.ORIGINS` (40 km from World Zero), 3x3 hub estate (768 m slab), markers Spawn/Gate/Dock/SubDock/Mount (2ec591291) |
| 2 | Terrain host | **partial** | Fable/Sol | hub slab + the whole environment kit imported to `/Game/Daedalus/Art/Env/<Realm>/` and standing on it (24 modular props validated (GAL02), no streamed ground ); district ground tiles still to lay |
| 3 | Lands | **partial** | Fable | 160 plots laid down (rings 1-6, deeds 9..168) as `Land_<Realm>_<n>` slabs + signs; rings 7-49 to follow once the mint shape is known |
| 4 | Mint row | **missing** | Sol | see WORLD-ZERO 4 |
| 5 | Cast | **done** | Fable | `gallery-city.dcs` 12 roles/44 steps; 13 Mob_Gallery_* imported, Talkers bound (CAST-IMPORT) |
| 6 | Creatures | **partial** | Sol | 19 creature/mount/pet visuals validated (GAL01); not spawned |
| 7 | Items | **done** | Fable | `gallery-city.dic` 13 items |
| 8 | Dialogue theme | **done** | Fable | `gallery` |
| 9 | Mounts | **missing** | Sol/Fable | drone art validated, no possession |
| 10 | Docks / gates | **partial** | Fable | RainbowFrame at the gate marker, BoatDock/Airlock at the dock markers, mount station at the west edge; hero SwitchRealm must teleport to `Gate_<Realm>` (next) |
| 11 | Server endpoints | **partial** | Sol | PR80 row |
| 12 | Play proof | **partial** | Fable | cast 8/8 (talk), no walk-the-realm scenario |

## PARCELS (catalog `parcels`, theme `parcels`, mount helicopter)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | origin in `daedalus_realm_ground.ORIGINS` (40 km from World Zero), 3x3 hub estate (768 m slab), markers Spawn/Gate/Dock/SubDock/Mount (2ec591291) |
| 2 | Terrain host | **partial** | Fable/Sol | hub slab + the whole environment kit imported to `/Game/Daedalus/Art/Env/<Realm>/` and standing on it (23 props + AMF trough (PAR02), no ground ); district ground tiles still to lay |
| 3 | Lands | **partial** | Fable | 160 plots laid down (rings 1-6, deeds 9..168) as `Land_<Realm>_<n>` slabs + signs; rings 7-49 to follow once the mint shape is known |
| 4 | Mint row | **missing** | Sol | |
| 5 | Cast | **partial** | Fable | `parcels.dcs` 12/46; GLBs in `Codex\2026-10-13\parcels-buildout\cast` NOT imported yet |
| 6 | Creatures | **partial** | Sol | 32 role models validated (PAR01) |
| 7 | Items | **done** | Fable | `parcels.dic` 13 |
| 8 | Dialogue theme | **done** | Fable | `parcels` |
| 9 | Mounts | **missing** | Sol/Fable | helicopter + helipad art only |
| 10 | Docks / gates | **partial** | Fable | RainbowFrame at the gate marker, BoatDock/Airlock at the dock markers, mount station at the west edge; hero SwitchRealm must teleport to `Gate_<Realm>` (next) |
| 11 | Server endpoints | **partial** | Sol | |
| 12 | Play proof | **missing** | Fable | |

## BRICKS (catalog `bricks`, theme `bricks`, mount plane)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | origin in `daedalus_realm_ground.ORIGINS` (40 km from World Zero), 3x3 hub estate (768 m slab), markers Spawn/Gate/Dock/SubDock/Mount (2ec591291) |
| 2 | Terrain host | **partial** | Fable/Sol | hub slab + the whole environment kit imported to `/Game/Daedalus/Art/Env/<Realm>/` and standing on it (24 modular props (BRK02): meadow, road, runway, workshop ); district ground tiles still to lay |
| 3 | Lands | **partial** | Fable | 160 plots laid down (rings 1-6, deeds 9..168) as `Land_<Realm>_<n>` slabs + signs; rings 7-49 to follow once the mint shape is known |
| 4 | Mint row | **missing** | Sol | |
| 5 | Cast | **partial** | Fable | `bricks.dcs` 12/45; `bricks-buildout\cast` NOT imported yet |
| 6 | Creatures | **partial** | Sol | 32 role models (BRK01) |
| 7 | Items | **done** | Fable | `bricks.dic` 13 |
| 8 | Dialogue theme | **done** | Fable | `bricks` |
| 9 | Mounts | **missing** | Sol/Fable | plane, hover cart (BRK03) art only |
| 10 | Docks / gates | **partial** | Fable | RainbowFrame at the gate marker, BoatDock/Airlock at the dock markers, mount station at the west edge; hero SwitchRealm must teleport to `Gate_<Realm>` (next) |
| 11 | Server endpoints | **partial** | Sol | |
| 12 | Play proof | **missing** | Fable | |

## LABYRINTH (catalog `labyrinth`, theme `labyrinth`, mount sky-strider)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | origin in `daedalus_realm_ground.ORIGINS` (40 km from World Zero), 3x3 hub estate (768 m slab), markers Spawn/Gate/Dock/SubDock/Mount (2ec591291) |
| 2 | Terrain host | **partial** | Fable/Sol | hub slab + the whole environment kit imported to `/Game/Daedalus/Art/Env/<Realm>/` and standing on it (32 props (incl. 12 Halloween, LAB09), Wall4m, FoldingMaze ); district ground tiles still to lay |
| 3 | Lands | **partial** | Fable | 160 plots laid down (rings 1-6, deeds 9..168) as `Land_<Realm>_<n>` slabs + signs; rings 7-49 to follow once the mint shape is known |
| 4 | Mint row | **missing** | Sol | |
| 5 | Cast | **partial** | Fable | `labyrinth.dcs` 12/46; 35 Mob_Lab_* GLBs exported, not imported |
| 6 | Creatures | **partial** | Sol | plants LAB10 policy tested |
| 7 | Items | **done** | Fable | `labyrinth.dic` 10 (chalk charges LAB01 core tested) |
| 8 | Dialogue theme | **done** | Fable | `labyrinth` |
| 9 | Mounts | **missing** | Sol/Fable | sky-strider (LAB05) |
| 10 | Docks / gates | **partial** | Fable | RainbowFrame at the gate marker, BoatDock/Airlock at the dock markers, mount station at the west edge; hero SwitchRealm must teleport to `Gate_<Realm>` (next) |
| 11 | Server endpoints | **partial** | Sol | |
| 12 | Play proof | **missing** | Fable | |

## PORTAL (the 8-bit realm, theme `retro`, no DIC catalog)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **done** | Fable | DRR maps; `land <n> <map> <x> <y> <w> <h> <owner>` rows (realm-7: lands 0/1/2) |
| 2 | Terrain host | **done** | Fable | DRR tile maps |
| 3 | Lands | **partial** | Fable | 3 lands in realm-7; the rest of the maps need `land` rows |
| 4 | Mint row | **partial** | Sol/Fable | PORT12 Java egg + DRR parity tested; ownership authority pending; DRAGON_EGG→DRAKE done in core |
| 5 | Cast | **done** | Fable | 12 town NPCs (PORT03), queen, inn, shops in DRR |
| 6 | Creatures | **done** | Fable | 15 RetroMonster keys, shiny, 77 character exports validated |
| 7 | Items | **done** | Fable | DRR items incl. EGG |
| 8 | Dialogue theme | **done** | Fable | FF1 boxes, title card |
| 9 | Mounts | **n/a** | | |
| 10 | Docks / gates | **done** | Fable | portal cubes both ways (Session Via::Portal) |
| 11 | Server endpoints | **partial** | Sol | PR80 row |
| 12 | Play proof | **done** | Fable | realm 10/10, stage 3 checks (needs c7ff1dcb build), shiny |

## OCEAN (catalog `ocean`, theme `ocean`)

| # | Layer | State | Owner | Evidence / gap |
|---|-------|-------|-------|----------------|
| 1 | Grid + hub | **partial** | Sol | seeded sea chunks (OCE04), sectors; no spiral grid (sea lands are chunks, not cells) |
| 2 | Terrain host | **done** | Sol | server chunks → native procedural mesh (OCE09, HARBOR-RENDER 64 chunks) |
| 3 | Lands | **missing** | Sol | floating docks/drowned settlements as mintable? decide |
| 4 | Mint row | **missing** | Sol | |
| 5 | Cast | **missing** | Sol | role target not set (Production sheet) |
| 6 | Creatures | **missing** | Sol | |
| 7 | Items | **missing** | Fable | no `ocean.dic` (Session table names catalog `ocean`; server loads 5 catalogs) |
| 8 | Dialogue theme | **partial** | Fable | `ocean` theme name only |
| 9 | Mounts | **partial** | Sol | skiff + submarine: boarding, propulsion, hull, exit verified in network tests; rendered piloting pending |
| 10 | Docks / gates | **partial** | Sol | dock interaction verified headless; REALM transfer pending; shore return rule in Session core |
| 11 | Server endpoints | **done** | Sol | OCEAN-HOST-API (auth sector reads, quotas, URL check) |
| 12 | Play proof | **partial** | Sol | 27 verified runs, 5 pending (HW, REALM, ART, AUTH, HOST) |

## Are the xlsx/md detailed enough to build from?

- **Yes** for art (Assets sheet: id, kind, realm, role, triangles, rig, clips, file, SHA) and for Ocean (12 OCE
  docs with proofs).
- **Yes** for cast and items (dcs/dic files are the spec).
- **No** for the four 3D realms' *ground*: no document says where a realm's hub is, how big its terrain is, which
  props make its ground, or where its gate lands. Add to each `*-CAST.md`/`EXPLORATION-TERRAIN.md`: hub spawn,
  terrain extent in cells, prop kit, gate landing cell, dock cells. Fable drafts the UE side as a `REALM-<X>-GROUND.md`
  with the first district (10x10 cells) laid out.
- **No** for the mint: nothing describes a land NFT beyond ADR-065's bundle rule; the contract has no realm field
  (29124). Sol designs the realm-aware mint (realm id + land number + estate size + contents hash) before any
  "NFT ready" claim; the 13 World Zero deeds above are its first real rows.
- **Stale**: Production sheet says "Play proven 0" for every realm; Gallery cast is now imported and Talkers
  speak in Play (cast 8/8). Mechanics PORT10 "live binding pending" is now wired (c7ff1dcb4). Sol to re-issue.

## Laid down 2026-10-13 19:50 (2ec591291, editor turn)

| Realm | Hub | Markers | Kit props | Lands | Actors |
|-------|-----|---------|-----------|-------|--------|
| WORLD-ZERO | existing island | PlayerStart | 1863 meshes | 13 estates (deeds 9..59) + 89 plots (60..168) | +178 |
| GALLERY-CITY | 768 m slab | 5 | 24 | 160 plots | 190 |
| PARCELS | 768 m slab | 5 | 24 | 160 plots | 190 |
| BRICKS | 768 m slab | 5 | 24 | 160 plots | 190 |
| LABYRINTH | 768 m slab | 5 | 24 (12 maze + 12 Halloween) | 160 plots | 190 |

Every tool is idempotent (second run: 0 made) and saved; editor log after the imports: 0 new errors, 1 new
warning (Prop_Gallery_Ramp degenerate tangents, Sol's export).

## Order of work (lay down, then polish)

1. ~~World Zero plot markers~~ done; ~~Gallery/Parcels/Bricks/Labyrinth hub + kit + lands~~ done (table above).
1b. Hero `SwitchRealm` lands at `Gate_<Realm>`/`Spawn_<Realm>`; WorldActor streams by realm origin. Fable.
2. Realm-aware mint design + `/api/v1/lands?realm=` endpoint. Sol. Fable consumes it in WorldActor.
3. District sublevels: `daedalus_districts.steps(realm)` moves each realm's lands into `Realms/<R>/D<dd>` Dynamic sublevels and the hub kit into `<R>_Hub`, listed in islands.json for UDaedalusStreamer — the prerequisite for rings 7..49. Fable (tool on main, editor turn pending).
3b. District ground tiles (floor/field/meadow/road modules on the 2 m snap) over the hub districts. Fable + Sol.
4. Import Parcels/Bricks/Labyrinth casts (tool exists: `tools/unreal_play/import_cast.py`). Fable.
5. Repeat 3 for Parcels, Bricks, Labyrinth. Mounts after ground.
6. `ocean.dic` + Ocean role target. Fable / Sol.
7. One walk-the-realm Play scenario per realm. Fable.
