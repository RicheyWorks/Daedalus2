# ADR-022: Island ecology core

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks

## Question

The shattered islands are barren; arks and the sky are the only way life gets back (ADR-019, 021).
What rules decide whether it takes hold, and how do we know the rules are ecology and not a game
designer's guess?

## Decision

**Port the theory, then build a stepper the theory can judge.** `Biogeography` is CSRBT's
`TheoreticalModels` closed forms — MacArthur–Wilson S* = c/(c+e)·P and its approach curve, logistic
growth, and the `Environment` (colonization c·wind·temp·e^(−distance), extinction e/area). The world
itself runs on `Community` and `Ecosystem`, a seeded per-day stepper. Tests hold the stepper to the
textbook results, not to fixed numbers.

**Habitat is read off the island's own terrain** (`Habitat.of(traits)`): canopy 12 cells per tree,
pond every pond and stream column, meadow the open ground left over, soil a third of the footprint,
starborn 6 cells per crystal, marine none. A forested island and a pond island host different life.

**A day on an island** (`Community.day`):
- logistic growth r·N·(1 − F), where F is how full the species' **guild** is (Σ N/K over members) —
  a guild shares its habitat, so four grazers fill the meadow once, not four times;
- K = guild cells × a density by body size (tiny 8, small 1.5, medium 0.3, large 0.05, rooted 0.8);
- r = 0.6/day r-selected, 0.12/day K-selected; ±5% seeded noise;
- a population under 1 is gone; under 3 it risks a 12% daily loss — a single founder usually fails.

**A day in the world** (`Ecosystem.step`):
- **drift**: every dispersing kind on an island sends drifters to every other island with chance
  0.08·e^(−distance/120);
- **wild-sky rain**: one disperser from the whole canon, at 0.15/day × area/1000 (bigger target,
  more landings);
- **local catastrophe**: each kind is wiped out with chance 0.004 × 1000/area, capped at 0.2.

Only fliers and spores arrive without an ark. Everything replays exactly from the world's seed.

## What it found

**The first stepper had no species–area relationship.** Small and big isolated islands under the
same rain ended with 45 and 47 kinds. Once established, even a small island's populations sat far
above the fragile threshold, so nothing went extinct and richness just accumulated arrivals. That is
MacArthur–Wilson with both of its area terms missing. Adding e/area (local catastrophe) and the
target effect (rain ∝ area) gives it back:

| Island | Habitat cells | Richness at equilibrium (6 seeds, 600 days) |
|---|---|---|
| radius 9 | 385 | 3.7 |
| radius 26 | 2,953 | 11.7 |

7.7× the area holds 3.2× the kinds: S ∝ A^0.57. Real archipelagos usually run z ≈ 0.2–0.35, so this
world is steeper than nature — a tunable (CATASTROPHE, WILD_RAIN), recorded here rather than hidden.

**The distance test first counted rain as drift.** Rain lands equally on near and far islands, so
mixed in it masked the distance effect (392 vs 92). Reports now keep `drifted` (from neighbours)
and `rained` apart.

## Verified (`EcologyTest`, 11)

Closed forms match CSRBT; habitat read from traits; a lone hamster saturates at K within 10% without
overshooting 15%; four grazers fill their guild 0.85–1.15 times; marine kinds cannot land; most
single bear founders die out; bigger islands hold > 1.3× the kinds; a 96-cube neighbour gets > 5× the
drift of a 480-cube one; without arks only dispersers ever arrive; exact replay from a seed, different
from the next seed; Shannon/Pielou/Simpson against hand values.

## Held

- Live on the server, persisted, ticked (ADR-023), and ark cargo (ADR-023).
- Predation and food webs: guilds compete only within themselves today.
