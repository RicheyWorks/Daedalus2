# META01 — Fritillary Meadows (contest G183)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/Metapopulation.java` (tests: `MetapopulationTest`, 9).*

## Story

The ashfall valley regrew (ASH01), and with the meadows came the **ember fritillaries**, orange butterflies that live in
loose colonies, one to a meadow patch. Colonies wink out all the time; new ones start when a stray butterfly finds an
empty patch. The valley's farmers want the meadows for fields. Each patch ploughed looks harmless, since the butterflies
were only ever in some of them anyway. Botanist Wren Hollis has run the numbers and knows better: the butterflies need
enough patches for new colonies to start as fast as old ones die. Plough past that line and they are doomed, even while
plenty of meadow is left and butterflies are still flying over it for decades.

## Quest `q_fritillary_meadows`: "How Many Fields?"

1. The valley has 100 meadow patches, 80 with colonies. Decide how many to plough and when (`plough(year, count)`).
2. Run 200 years (`run()`).
   - **FLOURISHING**: over the last 50 years the butterflies hold at least half of Levins' unploughed equilibrium.
     The valley stays MEADOW (`band()`).
   - **DWINDLING**: they are still there, but thin.
   - **LOST**: no colony is left.
3. The twist is the **extinction debt**. Plough 85 patches in year 0 and every seed ends LOST, but the butterflies are
   still flying in year 10 in 99 of 100 seeds and in year 20 in 88. On average the last colony dies in about year 48.

Results with the defaults (c 0.5, e 0.1) over 100 seeds, ploughing in year 0:

| Ploughed | Mean occupancy, last 50 years | Levins 1 − D − e/c | FLOURISHING / DWINDLING / LOST |
|---|---|---|---|
| 0 | 0.757 | 0.80 | 100 / 0 / 0 |
| 20 | 0.568 | 0.60 | 100 / 0 / 0 |
| 40 | 0.375 | 0.40 | 11 / 89 / 0 |
| 60 | 0.180 | 0.20 | 0 / 99 / 1 |
| 75 | 0.014 | 0.05 | 0 / 20 / 80 |
| 80 (threshold) | 0.001 | 0.00 | 0 / 2 / 98 |
| 90 | 0.000 | 0.00 | 0 / 0 / 100 |

## Rules (seeded Levins model)

1. Each year, each occupied patch loses its colony with chance e = 0.1.
2. Each empty, unploughed patch gains a colony with chance `1 − (1 − c/N)^occupied`, c = 0.5, N = 100.
3. Ploughed patches lose their colony in the year they are ploughed and stay empty.
4. Equilibrium occupancy `p* = 1 − D − e/c` (`equilibrium(D)`); the butterflies cannot persist past
   `D = 1 − e/c` = 0.8 (`ploughThreshold()`).

Every roll is a splitmix hash of (seed, year, patch). `Settings.DEFAULT = (100, 0.5, 0.1, 200, 80)`.

## What the tests pin

- The equilibrium and threshold match Levins (0.8 threshold, 0.4 at D = 0.4, 0 past the line, 0 with no colonisation).
- Long-run occupancy is within 0.05 of 1 − D − e/c for 0, 20, 40 and 60 patches ploughed.
- Ploughing 80 or 90 loses the butterflies in at least 95 of 100 seeds, with 20 or 10 patches of meadow left. Ploughing 0
  or 20 never does.
- Extinction debt: ploughing 85 always ends LOST, yet the butterflies are still flying in year 10 in at least 90 seeds
  and in year 20 in at least 70.
- Less ploughing never means fewer butterflies.
- Ploughed patches stay empty, including a second ploughing in year 50.
- `band()` is MEADOW exactly when FLOURISHING. The same seed and plan give the same valley, and bad plans and settings
  are refused.

## Host seam

- `Metapopulation.valley(Settings, seed)`, then `plough(year, count)` from the farmers' field-plan UI, then `run()`.
- `Report.years()` drives a valley scrub (colonies lit per patch, fields drawn on ploughed patches). `Report.outcome()`
  and `band()` drive Wren's lines and the valley cover.
- Ties: the meadows are ASH01's regrowth. The bramble meadow kit is BEE01's. The threshold idea is the same as CRANE01
  (too few to replace themselves) and ISLES01 (arrival against extinction), here across patches instead of islands.
- Assets: `Mob_Ember_Fritillary` (butterfly, Idle/Flutter, instanced over a patch), `Prop_Field_Furrows` (ploughed
  patch decal/mesh), and reuse of the regrowth meadow and BEE01 bramble kit (see UNREAL-QUEUE / BLENDER-ASKS).
