# Kennel Isle — art-master-flex (Team Grok)
Companion and pet island, home of the world Cane Corso (`Mob_CaneCorso`, Richey's decision; `Mob_CaneCorso_Blocky` is a spare).
Sublevels: `/Game/AMF/Maps/WildBiomes_AMF_Pets` (wild pets, `amf_pets_ue.py`) and `/Game/AMF/Maps/Island_AMF` (this island, `amf_island_ue.py`).
Art: 500 Blender assets, `amf_items.py` -> `art\glb\amf\*.glb` -> `/Game/AMF/Art/<Kind>/<Group>/`.

## 1. Fresh water (hard rule)
A gravity loop with three independent sources, so it survives drought and no-rain days.

| Stage | In-world actor | Asset | What it does |
|---|---|---|---|
| W1 Spring | `W1_Spring` + `W1_SpringPool` | Prop_Water_AMF_SpringBasin | Main source: 40 L/min fed by the island's aquifer, never runs dry |
| W2 Stream | `W2_Stream_0..5` | water planes | Carries spring water downhill to the filter |
| W3 Rain catch | `W3_RainCatch_0..2` | Prop_Water_AMF_RainCatcher | Cloth funnels + copper barrels, 15 L per rain tick each |
| W4 Filter | `W4_SandCharcoalFilter` | Prop_Water_AMF_Filter | Hay/charcoal/sand layers: raw -> drinkable (removes "Murky") |
| W5 Cistern | `W5_Cistern` | Prop_Water_AMF_Cistern | 2,000 L store; everything drinks from here |
| W6 Solar still | `W6_SolarStill_Backup` | Prop_Water_AMF_SolarStill | Backup: distils sea/brackish water, 5 L/day in sun |
| W7 Well | `W7_Well_Backup` | Prop_Water_AMF_Well | Backup bucket well into the same aquifer |
| W8 Pipes | `W8_Pipe_*`, `W8_PipeTee` | Prop_Water_AMF_Pipe* | Cistern -> trough line |
| W9 Troughs | `W9_Trough_0..3`, `W9_Trough_Pen` | Prop_Water_AMF_Trough | Pets (kennel row) and livestock (goat pen) drink; also the herb brew vessel |

Daily demand: player 3 L, Corso 4 L, pup 1 L, each goat 4 L, capybara 3 L, others 1 L ≈ 30 L/day. Spring alone gives far more; rain + still + well cover a blocked spring.

## 2. Herb mechanic: Trough-Brew Pet Tonics (unique to AMF)
Herbs are never eaten raw. You **steep** up to 3 herbs in a pet water trough. Any pet that drinks from it gets the brew.
1. **Base note** (1st herb) picks the effect family; **heart note** (2nd) picks the stat; **finish** (3rd, optional) sets duration.
2. **Coat resonance:** the pet's Turing coat pattern scales the result: Spots ×1.25 on burst effects (heal, dash), Stripes ×1.25 on sustained effects (shield, regen), Labyrinth ×1.1 on everything plus a 10% chance of a second roll.
3. **Charm tie-in:** a pet wearing a charm-slot gear piece (`Item_PetCharm_*`, see companions\pet-gear-recipes.json) of the matching element doubles duration.
4. **Trough decay:** a brew lasts 3 drinks or 10 minutes, then the water turns plain again (water system keeps refilling it).
5. Shared drinking: the Corso drinking first gets full strength; pack members get 50% (pack bond).

| Herb | Note role | Effect |
|---|---|---|
| Barkbalm | base | Heal family (HP restore) |
| Guardthistle | base | Shield family (temp armour) |
| Wagwort | base | Speed family (move/dash) |
| Howlroot | base | Fury family (bite/attack) |
| Dozeleaf | base | Calm family (taming, breeding mood) |
| Pawmint | heart | Stamina |
| Ironfang | heart | Defense |
| Snoutsage | heart | Perception (finds herbs/ore) |
| Starkibble | heart | Glow/luck (rare drop chance) |
| Furfern | finish | Long (+100% duration) |
| Dewclaw | finish | Swim (also lets livestock cross water) |
| Coppercap | finish | Instant (pulse instead of over-time) |

Example brews -> tonic items (`Item_Tonic_AMF_*`): Barkbalm+Pawmint = **Mend** (heal 40% + stamina); Guardthistle+Ironfang+Furfern = **Bulwark** (shield 30 for 2 min); Wagwort+Pawmint+Coppercap = **Dash**; Howlroot+Ironfang = **Fury**; Dozeleaf+Starkibble = **Bond** (breeding chance +20%, ties to pet breeding #14). Bottled tonics (T1–T4 tiers) carry a brew off-island.
Stat hooks map onto the companion schema fields in `art\NOTES\companions\companion-rules.schema.json` (hp, armor, speed, attack, stamina).

## 3. Livestock and survival loop
- Goats (Mob_PygmyGoat) graze bushes and hay; give milk (food) and fibre for pet beds. Capybaras keep the herb garden weeded.
- Hay bales come from mown meadow; herbs regrow 1 day after harvest when watered from the trough line.
- Player eats milk, berries (from Bush variants) and Mend tonics; pets eat kibble crafted from milk + Starkibble.
- Every animal needs trough water daily; no water = stats drain, which is why the loop has three sources.

## 4. Items (500)
Herbs 60 plants + 60 bundles, tonics 40, water parts 84 (wells, spring basins, rain catchers, stills, cisterns, filters, troughs, pipes), pet props 100 (bowls, beds, kennels, feeders, toys), livestock 60 (fences, gates, hay, goat shelters), dressing 96 (rocks, bushes, crates, lanterns). All ≤ 108 tris, 1–3 flat-colour slots, origin at bottom centre.

## 5. Working loop in-world (`amf_loop_ue.py`, v3)
Run after `amf_island_ue.py`. Everything sits in `Island_AMF`, tagged `AMF_Loop`, and is safe to re-run.
- **Water_Drinkable**: troughs W9_0..3 and W9_Trough_Pen, the cistern, the well and the spring pool are tagged, and each has a `TriggerSphere` (`Drink_*`, tags `Interact_Drink`). Stream, rain, filter, still and pipes are tagged `Water_Chain`.
- **Food_Source**: goats → `F1_MilkPail` (`Collect_Milk`) → `F2_KibbleBin` (`Craft_Kibble`, `Recipe_Milk+Starkibble`) → 4 bowls / feeders (`Feed_0..3`, `Pet_Feeder`). Hay bales are `Food_Hay`.
- **Herbs → brew**: every herb plant is tagged `Herb_Source`/`Interact_Harvest` with `Brew_Target_W9_Trough_3`. `W9_Trough_3` is the `Brew_Trough` (`Brew_W9_Trough_3`, max 3 herbs). A stepping-stone path (`Link_HerbToBrew_*`) runs between them.
- **Signs**: `TextRender` labels: water 1–7 plus the backups (blue), food A–D (amber), herb/brew (green), and a big KENNEL ISLE title.
- What's real now: tags and overlap volumes that judges and gameplay code can query (`GetAllActorsWithTag`). Drinking or feeding stat effects need the shared survival component to read these tags. No custom C++/BP is added here, so no other team's code is touched.

## 6. Fixes (v3)
- `amf_pets_ue.py` now only takes meshes from the asset's own folder named `<asset>` or `<asset>_<Part>`, and drops `Wing*` parts on non-flying mobs. All parts share one pivot and the assembly sits on the ground by combined bounds. This fixes the stray `WingL/WingR` on the pup and camp props.
- Wild Biomes fallback: if there are no `WB_Label_*` and no ground ring, animals go on Kennel Isle's meadow (5 clusters, 150–500 cm spread). There is also a ground fallback onto the island cube.
- KNOWN: `/Game/Daedalus/Art/Mob/Mob_CorsoPup` really contains a cairn rock (`Prop_Island_Cairn_K6V2`, live-scene export bug). The pup needs a Blender re-ship from `NOTES\amf\t20\Mob_CorsoPup.glb`.

## 7. Story: Kennel Isle, a fragment of the shattered planet
When the planet broke, most shards kept their cities and lost their water. Kennel Isle kept the opposite: one living aquifer and no one left to use it. The spring still runs 40 L a minute into a basin cut by people who didn't come back.
The animals did. Goats, capybaras and stray pets drifted in on wreckage and stayed for the water. The Cane Corso was there first, guarding the spring like it was still on a curb waiting for pickup, and the pack formed around it. That's why the Corso always drinks first and gets the full brew.
The old keepers left one trick behind: herbs steeped in trough water. Barkbalm for wounds, Guardthistle for storms, Dewclaw for animals that have to cross open water between fragments. The player arrives, rebuilds the filter and cistern, earns the pack's trust with Bond tonics, and turns the island into the kennel every other fragment sends its companions to.
