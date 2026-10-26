# The Orrery Reach: Claude Island

**Builder:** unreal-team (Claude).
**Cell:** ARK_ORIGIN 0,0,0; the island sits 4 km east, in sublevel `/Game/Claude/ClaudeIsland_Sub`.
**Realm tag:** `Orr`.
**Style:** Sky Islands, warm brass and night-blue.

## The story hook

When the meteor broke Daedalus apart, one piece kept its clocks running: the Orrery, the old observatory that once
tracked the planet's seasons. Its Keepers stayed on to chart where every fragment drifts, and they noticed that the
herbs on their island bloom by the sky, each at its own hour, as if they remember where the stars used to stand.

Then the Long Storm tore the observatory roof open and scattered the Keepers' star charts across the rim. Without
them the herbs can't be read, the brews fail, and the telescope can't find its way.

You land at the ark dock with a satchel and a dew flask.

## The mechanic: Starbloom Steeping (original)

1. **Every herb blooms at its own sky hour.** There are 24 starbloom species, one for each hour of the Sky
   Director's clock (ADR-056): Dawnthistle at 6:00, Noonspire at 12:00, Midnightmint at 0:00, and so on. A herb
   can be harvested only in its bloom hour. Outside it, it is a bud.
2. **Harvested herbs carry their constellation.** The 24 species belong to 12 constellations (Keeper, Lantern, Ark,
   Shard, Wanderer, Hearth, Spindle, Crown, Tide, Forge, Kite, Loom), two herbs each, one day bloom and one night
   bloom.
3. **Steep at a steeping kettle, with clean water.**
   - **One herb → a tea.** It gives a small effect: heal, warmth, light, swiftness and so on.
   - **The constellation's two herbs → its brew,** a set bonus. A Lantern brew lights caves; a Tide brew lets you
     drink from the sea.
   - **A day bloom plus a night bloom from different constellations → an eclipse brew.** There are 8 eclipse brews,
     each a strong, rare effect such as Totality (become unseen for a minute) or Corona (shield burst).
   - **Dirty water ruins any brew.** Water must pass a filter first, which ties the mechanic to the water system.
4. **Bonus at the true hour.** A brew steeped during its constellation's sky hour gets double duration.

What it teaches: reading the sky, planning a day around bloom hours, keeping water clean.

## Livestock and the food loop

| Animal | Eats | Gives | Feeds into |
|---|---|---|---|
| Lumewool sheep (glow wool) | hay, herb stems | fleece, then yarn, then blankets | warmth at night, trade |
| Comet hens | seed, driftberries | comet eggs | omelette, starbread |
| Orbit goats | hay, sunfruit | milk | cheese, butter |
| Nebula bees | blooming starblooms | honey, wax | honey-glazed roots, candles (light) |

Crops grow in the south fields: sunfruit, moonmelon, driftberry, starbarley, cometcorn and dewroot, each in three
stages. Bees only make honey while a starbloom is in bloom nearby, which ties them to the herb clock.

## Water: drinkable, in a closed loop

1. **Dew nets** on the rim catch night dew.
2. The **summit spring** rises under the observatory.
3. The **aqueduct** carries water down the west spoke.
4. Water passes a **sand filter** and then a **charcoal filter**.
5. It is stored in **cisterns**.
6. People draw it at the **well**, **hand pump** or **drinking fountain**, and animals drink at the **troughs**.

Unfiltered water makes you sick and ruins brews. Filtered water is drinkable and is the only water a steeping kettle
accepts.

## The adventure: the Keeper's Logbook

| Quest | You do | You learn |
|---|---|---|
| 1. Dock day | Meet the Keeper at the ark dock and fill your dew flask at a net | the dew nets; thirst |
| 2. Clean water | Fix the broken sand filter so the aqueduct's water is drinkable | filtration |
| 3. The first chart | Find the Lantern chart in the herb rings at dusk; harvest Duskmallow at its hour | bloom hours |
| 4. Kettle lessons | Steep your first tea, then the Lantern brew, and light the old cave under the rim | teas and brews |
| 5. The pens | Feed the Lumewool flock and the comet hens; make starbread for the Keeper | the food loop |
| 6. The honey hour | Lead the nebula bees to a blooming bed and collect honey before the hour ends | bees and the herb clock |
| 7. Scattered stars | Recover all 12 constellation charts around the rim, each guarded by a sky puzzle or a foe | every brew recipe |
| 8. Eclipse | Steep your first eclipse brew to reach the vault of the dome | eclipse brews |
| 9. The new moon | Repair the great telescope with the recovered lenses and point it at the sky | phase 2: a moon to visit |

Discovery is gentle: the Keeper never gives a recipe outright. Charts show star patterns, and the herb beds are laid
out in the same patterns.

## Items (500, all original, tag Orr)

- 96 starbloom herbs: 24 species × 4 stages.
- 24 teas, 12 constellation brews and 8 eclipse brews.
- 12 creatures: 4 livestock with their young, and 4 wild ones (star moth, dew newt, lens owl, gear fox).
- 46 goods and food.
- 40 buildings: the observatory dome and tower, keeper cottages, barn, coop, apiary, steeping house, cistern house,
  well house, windmill, lighthouse and others.
- 40 water pieces.
- 74 astronomy pieces: armillaries, orreries of 2 to 11 planets, telescopes, star charts, sundials, moon-phase lamps,
  meteorites and lenses.
- 62 decor pieces.
- 20 interior pieces, 20 tools, 12 weapons, 6 vehicles, 10 sky pieces and 18 crop stages.

The generator is `tools/claude_island/orr_build.py`, the checker is `orr_check.py` and the layout is `orr_place.py`.
