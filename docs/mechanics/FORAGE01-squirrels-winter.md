# FORAGE01 — Squirrel's Winter (contest G129)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/PatchForager.java` (tests: `PatchForagerTest`, 10).*

## Story

Two days before the first frost, Pip the red squirrel still has an empty hoard. The bramble patches on the Pythagoras
meadow are uneven: some sag with fruit, others were stripped by the bees' late visitors. Every patch is quick to pick at
first and slower the longer Pip stays. Old Hazel's advice is: "Don't stay till the bush is bare, and don't run off while
it's still giving. Leave when it gives you less than the meadow does."

## Quest `q_squirrels_winter`: "Leave When the Bush Gives Less Than the Meadow"

1. Choose Pip's leaving rule:
   - a **rate threshold** θ (berries/min): leave when picking drops to θ (`rate(θ)`), or
   - a **fixed stay** per bush (`fixed(minutes)`).
2. Pip forages for 1200 minutes of daylight across 120 seeded patches, visited in order (the order wraps).
3. Hazel compares the hoard with Charnov's best day (`optimalRate()`):
   - **HOARDED**: at least 97% of it.
   - **SHORT**: at least 70%.
   - **STARVED**: anything less.

What happens with the defaults (seed 1):

| Rule | Berries | Share | Outcome |
|---|---|---|---|
| θ* ≈ 4.23/min | 5150 | 1.000 | HOARDED |
| 0.75 θ* (too patient) | 4912 | 0.954 | SHORT |
| 2 θ* (too greedy) | 4164 | 0.808 | SHORT |
| 4 θ* | 139 | 0.027 | STARVED |
| best fixed stay (11.5 min) | 4710 | 0.915 | SHORT |

## Rules

- Patch amounts are uniform in `amount · (1 ± spread)`. Travel times are uniform in `travel · (1 ± travelSpread)`.
- Picking follows `G(t) = A(1 − e^{−t/τ})`, so the instant rate is `(A/τ)e^{−t/τ}`. The rate rule stays
  `τ ln(A/(τθ))`, or zero for a bush that never reaches θ.
- **Marginal value theorem**: θ* is the fixed point `θ = E[G]/(E[t] + E[T])` over the amount distribution (200-bin
  midpoint rule). Leaving every bush at the same marginal rate beats any fixed stay on uneven patches.
- `Settings.DEFAULT = (120, 1200, 120, 0.9, 12, 8, 0.5, 0.97)`.

## What the tests pin

- θ* hoards on 10 seeds.
- 0.25θ*, 2θ* and 4θ* never beat θ*; 4θ* starves.
- No fixed stay from 0.5 to 60 minutes beats θ* or hoards (20 seeds).
- θ* is Charnov's fixed point, and the leave rate equals θ exactly.
- Picking time never runs past dusk.
- Patch amounts stay in their spread.
- Bands: a stripped patch reads SCRUB.
- The same seed gives the same day, and invalid input is refused.

## Host seam

- `PatchForager.meadow(Settings, seed)`, then `rate(θ)` or `fixed(min)` → `Report` (berries, best, share, visits).
- `visits()` drives Pip's route and a hoard counter. `band(patch, held(patch))` turns a stripped patch to SCRUB.
- Ties: the brambles are BEE01's BRAMBLE flora (late summer bloom, autumn fruit). The hoard can feed the island winter
  stores. Uses the battlefield `Vegetation` bands.
- Assets: `Mob_Red_Squirrel` (Idle/Run/Forage), `Prop_Hoard_Cache` (a log hollow whose fill level follows the share),
  and reuse of the bramble clumps (see UNREAL-QUEUE / BLENDER-ASKS).
