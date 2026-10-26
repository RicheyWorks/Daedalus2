# SALMON01 — Salmon Run (contest G71)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/SalmonRun.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/SalmonRunTest.java` (9)
Links: BEAVER01 Beaver Waters (rearing ponds), CASCADE01 Trophic Cascade (the same river), ASH01 Ashfall Regrowth
(the forest the salmon feed).

## Story

The salmon are the one ark cargo that came home on its own. The fry were dropped into the sea before the planet
shattered, and each autumn the survivors climb the river to the gravel where they hatched. The islanders are hungry
and want to net the run. The river wants the salmon too: after spawning, the dead fish feed the bears, the bears
drag them into the trees, and the forest grows on nitrogen that came from the ocean. An old weir from before the
shattering still blocks most of the upper gravel.

Net-keeper Ysolde Marrow remembers the last time the run was netted to nothing. Nobody on the island has eaten
salmon since.

## Quest `q_salmon_run` — "What the River Is Owed"

1. **Count the run.** Ysolde shows the first returns (150 spawners).
2. **Plan the works.** You can build a fish ladder at the weir, keep up to 3 beaver rearing ponds (from BEAVER01) and set the island's catch.
3. **Run 40 years.** The outcome:
   - **RESTORED**: mean escapement over the last 8 years is at least 1000 and the island caught at least 12,000 fish in total. Reward: a salmon-fed PINE/OAK riverside forest band.
   - **HOLDING**: the run survives but misses a goal.
   - **FISHED_OUT**: mean escapement below 50.

NPC lines (Ysolde Marrow):
- Start: "Take a fish, leave a fish, and leave the river's share on top."
- Ladder: "Above that weir is twice the gravel we fish below it."
- Overfished: "Every net full this year is an empty river in four."
- Restored: "Smell that? Rotting salmon under the pines. That's a healthy river."

## Rules (deterministic from the seed and the plan)

- The return in year y comes from the escapement in year y − 4, by the Ricker curve: R = alpha·S·e^(−S/capacity)·ocean·(1 + 0.1·ponds), with alpha 4.
- Ocean survival is lognormal with mean 1 and sigma 0.4, seeded.
- Capacity is 400 (lower gravel) plus 800 (upper gravel), but without the ladder only 25% of the upper gravel counts.
- The catch is a fraction of each run, and the rest spawn.
- Past a catch of 1 − 1/alpha (0.75 with no ponds), the stock cannot replace itself (`replacementLimit()`).
- Bears carry 50% of the spawned-out carcasses into the forest. The forest band is OAK for at least 1.5× the target per year, PINE for at least 0.5×, SCRUB for at least the collapse level, and MEADOW below that.

## What the tests pin

- A calm ocean reaches the Ricker equilibrium capacity·ln(alpha).
- The ladder opens the upper gravel.
- Ladder plus ponds plus a 0.4 catch restores the run on seeds 1–5. The same catch without the works only holds.
- A catch of 0.85 fishes the run out, and the forest drops to MEADOW.
- Carcass bookkeeping adds up.
- Each return is the child of the run 4 years before.
- Determinism, and seed-dependent oceans.
- Budgets and refused bad input.

## Host seam

- `SalmonRun.river(Settings, seed)`, then `buildLadder()` / `pond()` / `harvest(f)`, then `run()` → `Report`.
- `years()` drives the run counter UI: spawners back, run, caught, escapement, carcasses carried.
- `Report.forest(settings)` sets the riverside band on the BattlefieldEcology grid.
- Assets: salmon (school + carcass), fish ladder segment, weir, and a net rack (see UNREAL-QUEUE / BLENDER-ASKS).
