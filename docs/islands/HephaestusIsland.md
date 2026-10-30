# Hephaestus Island: the forge island

Contest entry by hephaestus. Twice normal size (**1024 x 1024 m**). Manifest: `data/islands/hephaestus.json`. Island data pack: `data/islands/hephaestus/` (`layout.json`, `water.json`, `herbs.json`, `livestock.json`).

**ARK_ORIGIN:** `6000000, 2000000, 0` (cm). Unreal placement: `bot-team/art/NOTES/hephaestus/heph_island_ue.py` (ORIGIN Z+2000 for platform).

**Story (canon):** the 10,000 islands are fragments of one shattered planet, the biggest world ever known. Hephaestus Island is the fragment whose core took the asteroid's direct strike. The impact melted its heart into a living forge. The first ark crews tamed that molten core and built the Great Forge on it, so every ark hull since has been riveted here.

## REALM: Forge Reach
Volcanic planet-shard forge-yards where asteroid iron meets living magma. Survival through tempering, quenching, and ark drydock trade. Heat shimmer and ash wind shape discovery; riveters keep daily schedules.

## MECHANIC: Forge Temper
Herb tonics are tempered by **quench path** after brewing (mortar / hand-mix, then quench):

| Path | Strength | Duration | Station |
|------|----------|----------|---------|
| **magma** | x2 | x0.5 | `Prop_ForgeQuenchTub_Basalt` (hot) |
| **spring** | x0.5 | x2 | `HotSpring_Clean` or cooled quench trough |
| **dual** | base + **dual effect** | base | magma then spring (or reverse) within 10s — primary essence-pair effect **and** next-best pair both land |

Shared essence-pair table: `data/herbs/combos.json` (Forge Temper rule in `rules[]`). Island herb list + quench detail: `data/islands/hephaestus/herbs.json`. Livestock slag-grass grit fertilises herb beds.

## Zones
1. **Caldera Forge:** Great Forge (`Prop_HephaestusForge_Great`), anvil ring (`Prop_HephaestusAnvil_Great`), bellows (forgeox works them), quench tub.
2. **Meteor Scar:** impact scar; `Item_Shard_Asteroid` fused with `Item_Shard_Planet`; starmetal + emberite.
3. **Ark Drydock:** half-built ark on stilts; rivet crates (`Prop_ArkRivetCrate`); repair / upgrade arks.
4. **Ash Fields:** herb beds + ranch pens (emberhen, ashgoat, forgeox, lavaboar, cinderwool, vent_bees).
5. **Hot Springs:** **YES water** — clean hot springs, steam vents, rain catch, cistern.
6. **Basalt Coast:** black sand, salt still (`Prop_WaterStill_Copper`), lava tubes.

## Water (YES)
Island-specific: `data/islands/hephaestus/water.json`. Global schema: `data/water/water.json`.

Drinkable sources (tagged): HotSpring_Clean, SteamVentCatch, RainCatch_Ash, SaltStill_Basalt, QuenchTrough_Forge (cooled clean fill), RanchTrough_Ash. Ash well is dirty (boil/filter). Thirst x2 in caldera heat. Quench troughs double as livestock drink.

## Livestock / food loop
Island pens + feed + products: `data/islands/hephaestus/livestock.json`. Canonical animals: `data/livestock/animals.json`. Cooking: `data/food/cooking.json`.

## Layout / editor
Blockout placements (m relative to ARK_ORIGIN): `data/islands/hephaestus/layout.json` — forge cluster, meteor shard, drydock, ash ranch, herb beds, water chain.

**Editor build (2Hot2Trot / Grok turn only):** run `heph_island_ue.py` via `ue_send.py`. Idempotent `HEPH_Island` tag; saves only `/Game/Hephaestus/Maps/Island_Hephaestus`. Do not run without a granted editor slot.

## Assets
All 500 procedural items: `art\QUEUE.md` rows tagged [heph], from `tools/blender/heph_gen.py`. Landmark props: `Prop_HephaestusAnvil_Great`, `Prop_HephaestusForge_Great`, `Item_Shard_Asteroid`, `Item_Shard_Planet`, `Tool_HephaestusHammer`, `Prop_ArkRivetCrate`, `Prop_LavaLantern`.

## Editor turn (3-minute slot)

Run only on a slot granted by the referee: `python tools\islands\hephaestus\heph_turn.py` (add `--now` to skip waiting).
It waits for the previous slot's HANDOFF on the team link, then through the Claude Unreal Bridge runs
`heph_island_ue.py` inside the editor: imports the 7 hero glbs not yet shipped (Great Forge, Great Anvil, hammer,
shards, rivet crate, lava lantern), creates and streams the sublevel `/Game/Hephaestus/Maps/HephaestusIsland` under
DaedalusWorld, lays a 1024 m basalt blockout disc at ARK_ORIGIN 6000000,2000000, places all 102 layout entries
(hot-spring water as an engine plane), adds a forge-glow light and hero camera, takes a hero shot, stops Play, saves
only its own sublevel, and posts DONE plus HANDOFF. Editor work is capped at 150 s. Safe to rerun: it clears only
actors in its own `Hephaestus` outliner folder.

## Hero meshes (procedural, no Blender)

The 7 landmark glbs used to be 3-box placeholders (about 3.8 KB, 36 tris, all the same silhouette), so the island
would have read as a field of identical blocks. `tools/islands/hephaestus/heph_hero_glb.py` now builds real
low-poly versions with numpy and trimesh, in the art queue's glb format (one node, one mesh, one primitive per
material, Y-up, metres, base at y=0, emissive factors on ember/magma/crystal so Lumen picks up the glow):

| Asset | Tris | Size (m) | Shape |
|---|---|---|---|
| Prop_HephaestusForge_Great | 696 | 9.7 x 8.4 x 12.6 | octagonal basalt firebox, 8 buttresses, glowing hearth ring and firemouths, iron hood on 4 legs, chimney with ember lip |
| Prop_HephaestusAnvil_Great | 104 | 3.2 x 1.1 x 1.4 | stone block, foot, waist, face (top 1.22 m), horn, heel, hot billet |
| Tool_HephaestusHammer | 120 | 0.5 x 0.2 x 1.5 | wood haft, bronze collar, iron head with hot face |
| Item_Shard_Asteroid | 860 | 1.8 x 1.9 x 2.0 | pitted meteor rock with nickel nodules and crystal spikes |
| Item_Shard_Planet | 152 | 1.8 x 2.1 x 2.0 | wedge of the shattered world: glowing core, mantle, crust, crystals |
| Prop_ArkRivetCrate | 316 | 1.1 x 1.1 x 1.1 | wooden crate, iron bands, rivet heads |
| Prop_LavaLantern | 228 | 0.7 x 0.7 x 2.4 | basalt foot, iron post, caged magma core, cap |

Run `python heph_hero_glb.py <bot-team>\art\glb` (needs numpy + trimesh). The turn's import step picks them up
because none of the 7 has been shipped to `/Game/Daedalus/Art` yet.
