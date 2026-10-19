# BEE01 — Bee Bloom (contest G48)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/BeeBloom.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/BeeBloomTest.java` (11)
Links: ASH01 Ashfall Regrowth (the meadow it pollinates), VAULT01 Ark Seed Vault (where its seed goes), BEAVER01 Beaver Waters (the wetland the willows need).

## Story

The shattered planet's fragments regrow, but a meadow that does not set seed is only one summer deep. The ark carried
three skeps of bees sealed in wax and cold. On a regrown fragment the keeper, old Wenna Skep, wakes them in the thaw.
The bees and the flowers have to meet: catkins and crocus for the first warm days, clover and bramble for summer,
heather to fatten the hives for winter. A late frost on the fragment's thin air can burn the first blooms off in one
night, and a hive that wakes to nothing in flower starves in a week.

## Quest `q_bee_bloom` — "A Summer Deep"

1. **Wake the skeps.** Talk to Wenna Skep at the ark landing. Place up to 3 hives.
2. **Sow the calendar.** 6 beds. Choose flowers so something is in bloom from the thaw to autumn.
3. **Keep the syrup.** The keeper holds syrup for a few days without bloom (default 10 days).
4. **Run the season.** The outcome:
   - **THRIVING**: every placed hive is alive and the mean seed set is at least 0.7. Reward: seed into the vault (VAULT01) and a meadow cache for ASH01.
   - **PATCHY**: seed set short, or some hives lost.
   - **COLLAPSED**: every hive starved.

NPC lines (Wenna Skep):
- Wake: "They've slept since the sky broke. Give them something sweet the first warm day."
- Frost: "Frost on the crocus. That's this year's early seed gone. Hope you planted for June."
- Collapse: "Nothing in flower and nothing in the jar. They ate the comb and then they ate nothing."
- Thriving: "Listen to that. The meadow will come back on its own next year."

## Rules (all deterministic from the seed)

- Daily mean temperature is a warm arc from `coldC` 3 °C to `peakC` 23 °C plus ±`noiseC` 3 °C noise.
  With `frostChance` (0.5) there is one frost day (below 0 °C) between days 15 and 40.
- Growing degree days add up `max(0, temp − baseC)`, with base 5 °C.
- Flora bloom windows (GDD, from–to, visits needed per bed, band):

  | Flora | GDD from–to | Visits needed | Band |
  |---|---|---|---|
  | WILLOW_CATKIN | 15–120 | 800 | WETLAND |
  | CROCUS | 30–160 | 800 | MEADOW |
  | CLOVER | 140–600 | 2500 | MEADOW |
  | BRAMBLE | 450–950 | 2500 | SCRUB |
  | HEATHER | 900–1600 | 3000 | MEADOW |

- Bees wake at 25 GDD and fly on days of at least 10 °C. Each hive makes 100 visits a flying day, shared evenly by the open beds.
- A bed's seed set is visits / visits needed, capped at 1.
- A frost kills every bloom open that day for the rest of the season.
- On a flying day with nothing open, a hive eats a syrup day if any are left. Otherwise it goes hungry. After 6 hungry days in a row, the hive dies.

## What the tests pin

- The temperature arc and its one bounded frost.
- The GDD sums.
- A gap-free calendar thrives on seeds 1–5.
- Heather alone collapses the hives.
- Frost cuts the early seed and empties the open beds.
- Syrup saves hives through the frost gap.
- More hives set more seed.
- Bees fly only on warm, awake days.
- No hives means no seed.
- The same seed gives the same report.
- Bed and hive budgets, and refused bad input.

## Host seam

- `BeeBloom.season(Settings, seed)`, then `sow(Flora, n)` / `hive(n)`, then `run()` → `Report`. The host reads `days()` for the timeline UI: temperature, GDD, frost, flying, open beds and hives alive.
- `Flora.band()` maps each flower onto the `Vegetation` band of the BattlefieldEcology grid, so the host can place the beds on matching cells (willow catkin on WETLAND from BEAVER01).
- Assets: hive skep prop and flower bed props (see UNREAL-QUEUE / BLENDER-ASKS G48).
