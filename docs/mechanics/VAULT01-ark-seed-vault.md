# VAULT01 Ark Seed Vault (minigame core)

Owner: pythagoras (contest gap G43, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/SeedVault.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/SeedVaultTest.java` (11 cases).
At landfall it feeds ASH01 Ashfall Regrowth (G20): `SeedVault.forRegrowth(settings)` sets the number of ark seed caches.
Each lot grows one succession band (`Species.grows()`: meadow, bramble/scrub, pine, oak, willow/wetland).

## Story (shattered-planet canon)

Before the meteor struck, the arks (ADR-019) loaded a seed vault: one lot for each band of the old forest. The
voyage to a safe fragment takes twelve years, and seed is alive. It ages, and it ages faster when it is warm and
damp. Seed keeper Ilsa has a cold room, a drying rack and too little power for both. When the ark finally berths
beside a scorched fragment, whatever seed is still alive is everything the fragment gets.

## Quest `q_seed_vault`

| Step | Trigger (what the core reports) | NPC line |
| --- | --- | --- |
| 1 Departure | `stock(...)` | **Seed keeper Ilsa** (`npc_ark_seedkeeper`): "Five lots, six thousand seeds each. Warm and damp, they will not last the first year." |
| 2 The rack | a `dry` returns true | Ilsa: "Dry seed lives longer. Not the acorns, though. Dry an acorn and you have a pebble." |
| 3 The cold room | `year(t)` with `t` below ambient | **Ark engineer** (`npc_ark_engineer`): "Every degree costs power. Drying costs power too. Pick." |
| 4 Ice | a moist lot below 0 C | Ilsa: "The acorns froze. Ice inside the seed. That lot is gone." |
| 5 Stopover | `regrowsLeft() > 0` | Ilsa: "A green fragment below us. Two lots can go in the ground and come back as fresh seed." |
| 6 The count | `germinationTest` | Ilsa: "A hundred seeds on wet cloth. What comes up tells us what is left, but those hundred are spent." |
| Landfall | `landed()` | Ilsa: "Every thousand live seeds is one cache." Then hand off `forRegrowth(...)` to `q_ashfall_regrowth`. |

## Rules (the science)

1. **Ellis and Roberts (1980) seed viability equation.** A lot has a probit viability `v`, and the share of its seeds
   alive is the normal CDF of `v`. Fresh seed starts at Ki = 2.0, which is 97.7% alive. Each year in store subtracts
   `365 / sigma`, where `log10 sigma = KE - CW log10 m - 0.0329 T - 0.000478 T^2` (m is moisture in % fresh weight,
   T is temperature in C, KE and CW are species constants).

   | Species (grows) | KE | CW | fresh moisture |
   | --- | --- | --- | --- |
   | Meadow grass (meadow) | 8.6 | 4.9 | 15% |
   | Bramble (scrub) | 9.4 | 5.0 | 15% |
   | Pine | 8.8 | 4.6 | 15% |
   | Oak (recalcitrant) | 6.0 | 2.0 | 40% |
   | Willow (wetland) | 7.2 | 4.5 | 15% |

   These constants are game-tuned, but the equation and the universal temperature constants are the published ones.
2. **Power.** The vault has 40 power a year. Cooling costs 1 per degree below the 20 C hold for the year, and drying
   costs 1 per moisture point per lot. A move that costs more than the power left is refused.
3. **Recalcitrant oak.** Acorns dried below 30% moisture die.
4. **Ice.** Any lot moister than 20% dies if it is kept below 0 C. Moist oak and a deep freeze cannot share the vault.
5. **Stopovers.** Every 3 years, two lots can be regrown. A regrown lot's live seed is planted and harvested at 5 per
   live seed, up to 6000, as fresh seed (Ki 2.0, fresh moisture, so it has to be dried again).
6. **Germination test.** n seeds are spent, and you get back a seeded binomial count of how many germinate.
7. **Landfall** comes after 12 years. Every 1000 live seeds of a lot fill one ark seed cache.

## What the tests prove

The equation and the normal CDF match the formula. A neglected vault lands with nothing. Dried, 2 C storage brings
the four orthodox lots through the voyage but not the oak. Regrowing the oak at every stopover lands all five bands
with more caches. Drying oak kills it, and freezing moist seed kills it. Power limits drying and cooling and comes
back every year. Regrowing works only at stopovers, two lots per stop, and harvests fresh seed. A germination test
spends seed and gives a seeded, plausible count. Landfall caches carry into AshfallRegrowth. Bad input is refused.

## Host seam

This is pure UI and data, so it needs no editor work: an ark hold screen with the five lots, a temperature dial, the
drying rack and a stopover prompt. Reuse the ark hold props and `Prop_Ash_SeedCache` (staged by blender-team) for the
caches at landfall.
