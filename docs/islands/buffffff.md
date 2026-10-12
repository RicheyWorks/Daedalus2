# Buffffff Island (Team Grok, built by Buffffff, Lead Bot)

Contest island, double size: **240 m diameter** floating isle (standard token island is 120 m).
Items: **720 unique Blender assets** (1,725 placed with scaled, denser scatter) (`Kind_BUF_Name`, GLB), generated headless by
`bot-team/art/buffffff/buf_items.py`, laid out by `buf_layout.py`, imported/placed in Unreal by
`engines/unreal/islands/buffffff_island_ue.py` into its own sublevel `/Game/Buffffff/Maps/Buffffff_Island` at grid ARK_ORIGIN 6000000,0,0.

| Group | Count |
|---|---|
| Herbs (24 herbs x 4 growth stages + item + seed + dried) | 168 |
| Stack tonics (36 single-family stacks + 30 fused) | 66 |
| Herb stations | 12 |
| Livestock (8 species x 6 ages/coats) | 48 |
| Food loop (products, crops, dishes, feed) | 72 |
| Farm buildings + kitchen | 20 |
| Water system (structures, vessels, troughs) | 58 |
| NFT landmarks + family banners | 9 |
| Island kit (rocks, cliffs, trees, pines, bushes, logs, paths) | 107 |

## Herb mechanic: Six-F Stacking ("buff stacks")
Every herb belongs to one of six **F-families**. You grind herbs one at a time into the **Stack Mortar**;
the *stack* (up to 6 layers, like the six F's in the name) decides the effect. Nothing works until the stack is
**sealed** at the Seal Press with clean water (or honey) - so herbs depend on the water system.

| Family | Colour | Base buff | Herbs |
|---|---|---|---|
| Fire | red | Speed | Zipwort, Blazemint, Dashpepper, Sparkroot |
| Frost | ice blue | Shield | Rimeleaf, Wardmoss, Iceclove, Bulwarkbell |
| Flora | green | Heal | Mendling, Sapheal, Balmthistle, Lifelily |
| Flux | violet | Jump / low gravity | Springfern, Hopvine, Gravisedge, Skyreed |
| Fog | grey | Stealth | Hushcap, Mistsage, Shadebloom, Veilgrass |
| Fang | amber | Strength | Toughroot, Brawnbean, Ironnettle, Musclemallow |

Rules:
1. **Height = power.** A pure stack of n herbs of one family gives that buff at tier n (x1..x6). Duration 30 s x n.
2. **Order matters (top layer leads).** Mixed stacks fuse the *bottom* and *top* families; the middle layers only add duration.
3. **Fusions** (bottom+top): Fire+Frost = *Steamguard* (shield that grants speed when hit); Flora+Fang = *Second Wind*
   (heal over time, strength while under 30% HP); Flux+Fog = *Ghoststep* (silent double jump); Fire+Flux = *Rocket Hop*;
   Frost+Flora = *Frostmend* (shield that heals on break); Fang+Fog = *Ambush* (first hit from stealth x3).
   All 15 pairs have a recipe; water seal = clean version, honey seal = +50% duration, -1 tier.
4. **The sixth F.** A perfect 6-stack of one family = **"Buffffff"**: tier-6 buff plus a 10 s aura that shares it with
   livestock and nearby players. One per in-game day per island.
5. **Overstack.** A 7th herb cracks the mortar: the stack spoils into compost (feeds the crop beds).
6. Dried herbs (Drying Rack) keep 3 days; fresh ones wilt in 1. Seeds come from S4 plants and the Seed Vault.

## Livestock, food and survival loop
Eight species, each with baby/young/adult/elder stages and gold/purple adult coats (NFT trait rarity):
**Buffalo** (milk, hide; ploughs), **Fluffhen** (eggs, feathers), **Puffgoat** (milk, cheese), **Muffpig** (bacon; eats slop/scraps),
**Tuffox** (pulls the waterwheel cart), **Snuffduck** (eggs; keeps the pond clear of pests), **Gruffsheep** (wool), **Ruffrabbit** (fast breeder, meat).

- **Animals need** feed (hay, clover, grain, slop, seed mix, mash, berry feed, salt lick) **and water** from troughs on the aqueduct.
  Hunger and thirst meters; a thirsty animal stops producing, then gets sick, then dies after 3 days.
- **Crops** (12: clover, oat, turnip, beet, potato, bean, corn, squash, berry, kale, hay, melon) grow in 3 stages on watered beds.
  Manure + spoiled stacks -> compost -> faster crops.
- **Kitchen**: stove, oven, churn, mill, cheese press, grill, smoker, icebox. 10 dishes (stew, omelet, pie, porridge, roast,
  soup, salad, bread, pancake, Buff Burger) each raw->cooked. Cooked food restores hunger; dishes with a herb add a tier-1 buff.
- **Survival**: player has hunger + thirst. Loop: water -> crops/feed -> livestock -> products -> kitchen -> eat; scraps -> pigs; manure -> compost -> crops.

## Water system (mandatory: drinkable for the bot and the animals)
Clean water is the island's centre, spawn is 15 m from the **Spring** (drinkable without treatment).
- Sources: Spring (clean), Well + Hand Pump (clean), Rain Canopy catchers (raw), Pond and Reservoir (raw).
- Treatment: Sand Filter -> Charcoal Filter -> Boiler or Sun Still turns raw water clean.
- Distribution: Cistern -> Aqueduct -> Waterwheel -> troughs (small, long, round, gold) at every pen; Fountain in the plaza.
- Vessels: cup, canteen, jug, bucket, flask, waterskin (empty/full).
- Raw water drunk untreated: 30% chance of sickness. Drought days: canopies and cistern keep the island alive 4 days.

## NFT tie-in
Buffffff Island is one of the 10,000 minted islands (hand-built flagship). Landmarks: **Mint Obelisk** (shows token id),
**Deed Stone** (owner plaque), **Buff Statue**. On-chain traits: dominant F-family, livestock coat rarity (gold/purple),
water tier (spring/well/filtered), and the island's daily "Buffffff" aura. Gold and purple adult coats are rare traits
that breed true, so the island's herd is part of the token's value.

## Lore
When the sky-archipelago first broke from the old continent, one stone carried a spring that never stopped. A herd of
shaggy buffalo found it, and the herders who followed learned that the island's herbs did nothing alone, only when
stacked, layer on layer, and sealed with that spring's water. They counted the layers on their fingers, F, F, F, F, F, F,
and the sixth layer made the herd glow. The island has been called Buffffff ever since: six F's, one spring, and a herd
that is never thirsty.

## v2 additions (720 items)
Apiary (6 hives, honey jar, comb, wax, smoker, suit, extractor: honey is the second stack seal), 24 herb plots, 12 fences, 4 gates, 20 path runs, 48 decor props, 4 docks, 4 rafts, 12 F-family shrines, 12 flower patches, 53 more kit pieces.
