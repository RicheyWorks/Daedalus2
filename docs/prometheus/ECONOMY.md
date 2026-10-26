# Daedalus Economy and Crafting (v0)

**Status:** Draft v0, by Prometheus. Companion to `STORY.md` §7. Team Codex owns the data engine and tables; Team Claude owns the Unreal stations and ore nodes.
**Design rules:** data-driven (every item, node and recipe is a row), modular (a package other projects can load), deterministic (spawns come from the island seed), and grounded in real ecology, ethnobotany and metallurgy.

## 1. The loop
```
gather flora ──► process (cook / dry / ferment / distill / press / dye-vat) ──► food · medicine · dye · fuel · fiber · resin
prospect ──► mine ore ──► smelt (needs fuel) ──► metal ──► refine (rare) ──► alloy / rare metal
                                     all of it ──► craft ──► tools · ark parts · pet gear
tools ──► faster or deeper gathering and mining (progression)
```

## 2. Resource tiers
| Tier | Name | Examples | Gate |
|---|---|---|---|
| T0 | Forage | wild greens, berries, grasses, deadwood, clay, flint | hands |
| T1 | Cultivated | grain, oilseed, flax, dye plants, herbs | stone and wood tools, a garden plot |
| T2 | Base ore | copper, tin, lead, zinc, iron ore (bog iron, hematite) | pick, campfire kiln |
| T3 | Metals and alloys | copper, bronze, wrought iron, steel, brass | bloomery or smelter plus charcoal |
| T4 | Refined and rare | nickel-iron, platinum-group, iridium, lift crystal | starborn island, refinery, steel tools |

## 3. Flora (process to product), ethnobotany-grounded
| Plant group (asset tags) | Process | Product | Use | Real basis |
|---|---|---|---|---|
| Willow / meadowsweet | dry, decoct | pain tonic | pet medicine T1 | salicylates |
| Yarrow | dry, poultice | wound salve | pet medicine | traditional styptic |
| Woad / indigo | ferment vat | blue dye | gear and coat-safe dyes | indigotin |
| Madder | dry root, vat | red dye | gear | alizarin |
| Weld | boil | yellow dye | gear | luteolin |
| Flax / nettle | ret, scutch, spin | fiber, rope | rigging, harness | bast fibers |
| Oak bark | soak | tannin | leather tanning | tannins |
| Grain / tubers | mill, cook | flour, bread, mash | food | staple carbohydrate |
| Berries / fruit | ferment | preserves, vinegar | food, preservation | fermentation |
| Oilseed (flax, sunflower) | press | oil | lamp fuel, wood finish | linseed oil |
| Hardwood | char in a kiln | charcoal | smelting fuel | carbon reducing agent |
| Conifer | tap, distill | resin, pitch, turpentine | hull sealing | naval stores |
| Mushrooms (edible) | cook, dry | food | food | (toxic look-alikes exist: identification skill) |

**Sustainability:** each flora node has a regrowth rate. Harvesting past the max sustainable yield (roughly half of carrying capacity, logistic MSY) slows regrowth, and an island can be overharvested.

## 4. Ores and metals
| Ore | Found on (habitat traits) | Smelt | Metal | Notes |
|---|---|---|---|---|
| Malachite / chalcopyrite | rocky, boulders | bloomery + charcoal | copper | first metal |
| Cassiterite | streams (placer) | panning, then smelter | tin | + copper → bronze |
| Bog iron | ponds, wetland | bloomery | wrought iron | real wetland bog ore |
| Hematite | high rocky cores | blast smelter | iron → steel | needs bellows |
| Galena | boulders | smelter | lead | toxic: handling gear |
| Sphalerite | boulders | smelter | zinc | + copper → brass |
| Meteoric nickel-iron | starborn crystals | refinery | nickel-iron | asteroid fragment |
| Platinum-group nuggets | starborn, waterfall placers | refinery | platinum | rare |
| Iridium dust | starborn crater rims | refinery + flux | iridium | the impact signature |
| Lift crystal | starborn crystals | cut and set | lift crystal | ark lift (story material) |

## 5. Recipes (sample)
| id | Station | Inputs | Output | Use |
|---|---|---|---|---|
| charcoal | kiln | hardwood ×4 | charcoal ×2 | fuel |
| copper_ingot | bloomery | copper_ore ×2, charcoal ×1 | copper ×1 | T3 |
| bronze_ingot | smelter | copper ×3, tin ×1 | bronze ×4 | tools |
| steel_ingot | smelter | wrought_iron ×2, charcoal ×2 | steel ×1 | T4 gate |
| pitch | still | resin ×3, charcoal ×1 | pitch ×2 | hull seal |
| rope | spinning wheel | fiber ×4 | rope ×1 | rigging |
| pain_tonic | cookpot | willow_bark ×2, water ×1 | pain_tonic ×1 | pet care |
| wound_salve | cookpot | yarrow ×2, oil ×1 | wound_salve ×2 | pet care |
| blue_dye | dye vat | woad ×3, water ×1 | blue_dye ×1 | gear color |
| bronze_pick | anvil | bronze ×2, hardwood ×1 | bronze_pick | mine T2 |
| steel_pick | anvil | steel ×2, hardwood ×1 | steel_pick | mine T4 |
| pet_harness | workbench | leather ×2, rope ×1, bronze ×1 | pet_harness | pet gear |
| ark_hull_plank | workbench | hardwood ×3, pitch ×1 | ark_hull_plank | ark parts |
| ark_lift_housing | refinery | nickel_iron ×2, lift_crystal ×1, platinum ×1 | ark_lift_housing | ark range upgrade |

## 6. Spawns from the island seed
Spawns are deterministic: `SplittableRandom(seed ^ SALT_ECON)` is drawn in a fixed order, after the terrain draws, so terrain goldens (seed 11) do not move.
- Flora nodes go on meadow, canopy and pond cells. The plant group mix is weighted by the island's habitat (`Habitat.of(traits)`).
- Ore nodes go by trait: boulders → copper, lead, zinc; streams → tin placers; pond → bog iron; crystals → the starborn set; waterfall → platinum placers.
- Rarity scales with radius and crystal count. Every island gets at least one T0–T1 food source and one fuel source, so no island is a dead start.
- An island with a Turing maze (`TuringGenerator`) gets extra dye flora. (Flavor link, optional.)

## 7. Data schema (portable JSON)
```json
{
  "schema": "daedalus.economy/v0",
  "items":   [{"id":"copper","tier":3,"kind":"metal","stack":64,"tags":["metal","conductive"]}],
  "nodes":   [{"id":"node_bog_iron","yields":[{"item":"bog_iron_ore","min":1,"max":3}],
               "tool":{"kind":"pick","minTier":1},"regrowDays":6,
               "spawn":{"habitat":"pond","weight":0.4,"minRadius":8}}],
  "stations":[{"id":"bloomery","tier":2,"fuel":["charcoal"]}],
  "recipes": [{"id":"copper_ingot","station":"bloomery","seconds":20,
               "in":[{"item":"copper_ore","n":2},{"item":"charcoal","n":1}],
               "out":[{"item":"copper","n":1}],"unlock":{"tier":2}}]
}
```
Suggested files: `data/economy/{items,nodes,stations,recipes}.json`, which map 1:1 onto Unreal DataTables (`FDaedalusItemRow` and so on). Core validates on load: unknown ids, cycles, and items with no source all stop the build, like `build_species.py`.

## 8. Uses and sinks
- **Arks:** hull planks, pitch, rope, lift housings. Upgrades give range and hold size (ADR-023's hold of 12 kinds could grow).
- **Pets:** food, medicine (raises survival of low founder counts), harness and bedding, dyes for gear only. A coat is genetic and is never dyed.
- **Tools:** gates on node tier, and gather speed.
- **Trade:** surplus between islands by ark. Open question: whether any of it goes on chain.

## Open questions
1. Are crafted items on-chain or off-chain? (The default here is off-chain game state.)
2. Can medicine change breeding outcomes, or only survival?
3. Lift crystal: is it canon as the thing that keeps arks and islands aloft?
