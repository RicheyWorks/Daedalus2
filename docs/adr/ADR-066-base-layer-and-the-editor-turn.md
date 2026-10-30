# ADR-066: The base layer per realm, and the editor turn that lays it

Status: accepted, 2026-10-13 (unreal-team). Consumes ADR-063 (streaming), ADR-064 (islands.json), ADR-065 (grid).
Related: docs/production/BASE-LAYER.md (the live table), docs/AUTOMATION-LESSONS.md (why each rule exists).

## Why

Richmond, 2026-10-13: "shift building focus to get everything laid down in each realm then polish", "the
earlier we can launch the NFTs the more income we have", "speed up the ability to get great output from Unreal".
Before today a realm was a cast file, an inventory file and a folder of GLBs; nothing stood in the engine. The
islands were 60 km apart. Each editor change was a hand-run call that could crash the editor.

## Decision

1. **A realm's base layer is twelve rows**, each with an owner, a state and a proof (BASE-LAYER.md): grid+hub,
   terrain host, lands, mint row, cast, creatures, items, dialogue theme, mounts, docks/gates, server endpoints,
   Play proof. A realm is laid down when every row is at least partial and the mint row is done.
2. **Every row has a pure core first** (C++17 header + headless test, Python twin where the editor needs it),
   then the engine hook, then a Play scenario. Today's cores: DaedalusLandGrid, LandRegistryCore,
   RealmDirectoryCore, MountCore, BestiaryCore, CastScriptCore/world-zero.dcs; hooks: Hero::LandAt,
   WorldActor::TravelToRealm, Ghost::Wear, Target::DressSkeletal, ADaedalusRealmPortal; scenarios: realm_switch,
   realm_ground, realm_host, mounts, portals, bestiary.
3. **Realms share one persistent level at fixed origins 40 km apart** (daedalus_realm_ground.ORIGINS; Poot's
   terrains sit on the same origins). Everything a realm owns is labelled and tagged (`Realm:<R>`, `Deed:<n>`,
   `District:<d>`), so every tool is idempotent by label and the layout is data that can be dumped and reconciled
   with the server (daedalus_land_sync against Sol's district API).
4. **Lands stream by district** (daedalus_districts): Dynamic sublevels `Realms/<R>/D<dd>` and `<R>_Hub`, listed
   in islands.json for UDaedalusStreamer. Rings 1..6 are laid in the persistent level first and moved; rings
   7..49 are laid straight into their sublevels (lay_district_steps).
5. **Bulk editor work is one bridge call, one editor tick per item**: the `daedalus.steps` generator command.
   Imports, saves, reparents, spawns all go through it (import_cast.py, fix_materials.py, steps.py). A call that
   blocks the game thread for more than a few seconds is a crash (19:14, 22:19) and is not written any more.
6. **Saves are proven by the file**: save_levels/save_world/save_packages_proven raise unless the .umap mtime
   moved. A dirty flag is not a save (the islands reverted once).
7. **The editor turn runs unattended** (tools/unreal_play/night_run.py): wait for the running job, build, hot-copy
   and re-register, import, lay cast/portals/districts, run the Play suite, post one hub status with sha, n/m,
   errors=/warnings=. It stops and names the failing step; everything it runs is idempotent, so it resumes.

## Consequences

- A new realm costs: a .dcs, a .dic, Sol's three GLB folders, one line in ORIGINS, one row in the mount and
  bestiary tables; `lay()`, `lay_cast()`, `lay_portals()`, `place_creatures()` do the rest in under a minute.
- The engine is the last 10% of each slice; the first 90% is proven in milliseconds. This is what makes the
  code-writing fast enough to feed the engine.
- Open: the realm-aware mint (contract signs no realm field; Sol), district ground tiles on the 2 m snap, Ocean
  cast/creatures, rings 7..49 laid, the ~15 s play-mode error's caller (pie_guard will name it).

## Numbers (2026-10-13)

Four 3D realms laid: 4 x (hub + 5 markers + 24 kit props + 12 talkers + 19..22 creatures + 160 lands); World
Zero: 13 estates + 89 plots + 6 NPCs + 6 portals; PORTAL: 34 plots. Headless: land_grid 17, land_registry 19,
realm_directory 14, mount 9, bestiary 9, cast 47, inventory 43, realm 134, session 25; Python twins 114 + 9 + 18
+ 15 + 10 + 6. Play (b886df28): realm_switch 10/10, realm_ground 14/17, control 6/7. Material reparent: 11,000
instances in one steps() call at 2.3/s.
