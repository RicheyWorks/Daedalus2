# RUT01 — Rut on the Ridge (contest G188)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/HawkDove.java` (tests: `HawkDoveTest`, 9).*

## Story

Every autumn the Hornback bulls (LAB06) climb to the high ridge to contest the best grazing. Some bulls fight every
challenge. Others posture, bellow and walk away. The herders argue about which kind to breed from: "Fighters win the
grass," says one. "Fighters break their horns," says the other. Old herder Brannoch Vey has watched the ridge for forty
autumns and says the herd sorts it out on its own, as long as fights cost more than the grass is worth.

## Quest `q_rut_on_the_ridge`: "Fighters and Bluffers"

1. Choose the herd you start with: how many of the 200 bulls are fighters (HAWK) and how many bluffers (DOVE)
   (`run(hawks)`).
2. Watch 150 seasons of rut. Each season, each bull has 10 contests over grazing worth V = 4. Losing a real fight costs
   C = 10. Bulls breed in proportion to 10 + their mean payoff.
3. Brannoch's prediction: the herd settles at V/C = 40% fighters whatever you start with (`ess()`).
   - **MIXED**: both kinds are still on the ridge. Unless fighters are over 80% of the herd, the grazing holds (MEADOW).
   - **ALL_HAWK**: fights are too cheap and fighters take over; the ridge is trampled BARE (`band()`).
   - **ALL_DOVE**: only if you start with no fighters.

Measured over 50 seeds (mean hawk share over the last 50 seasons):

| Ridge | Start (hawks of 200) | Late hawk share | ESS V/C |
|---|---|---|---|
| V 4, C 10 | 20 | 0.389 | 0.40 |
| V 4, C 10 | 100 | 0.400 | 0.40 |
| V 4, C 10 | 180 | 0.401 | 0.40 |
| V 4, C 8 | 100 | 0.498 | 0.50 |
| V 4, C 5 | 100 | 0.854 | 0.80 |
| V 4, C 3 (cheap fights) | 20 | 0.999 (all hawk in 50 of 50) | 1 |

## Rules (seeded)

1. Each contest pairs the bull with a random rival. Hawk vs hawk: a coin flip; the winner gets V and the loser pays C.
   Hawk vs dove: the hawk gets V. Dove vs dove: a coin flip for V, nobody gets hurt.
2. Expected payoffs at hawk share h: hawk `h(V − C)/2 + (1 − h)V`, dove `(1 − h)V/2` (`expectedPayoff`). They are equal
   at h = V/C.
3. Breeding: each calf picks its sire with chance proportional to `base + mean payoff` and inherits his strategy
   (a seeded Wright-Fisher draw).

Every roll is a splitmix hash of (seed, season, bull, round, salt). `Settings.DEFAULT = (200, 4, 10, 10, 10, 150)`.

## What the tests pin

- The ESS is V/C = 0.4 and hawk and dove expected payoffs are equal there. Below it hawks do better, and above it
  doves do. With C ≤ V the ESS is all hawk.
- From 20, 100 or 180 starting hawks, the herd settles within 0.04 of 0.4 (30 seeds).
- Costlier fights mean fewer hawks: C = 8 settles within 0.05 of 0.5.
- Cheap fights (C = 3) let hawks take over in at least 27 of 30 seeds, and the ridge goes BARE.
- At the ESS, the realised hawk and dove payoffs are within 0.25 of each other.
- Pure herds stay pure, and a mixed ridge keeps its grazing.
- The same seed and start give the same rut, and bad input is refused.

## Host seam

- `HawkDove.ridge(Settings, seed)`, then `run(hawks)` from Brannoch's herd-mix slider.
- `Report.seasons()` drives a season scrub (share of fighters, each kind's mean payoff). `Report.outcome()` and
  `band()` drive the ridge cover and Brannoch's lines.
- Ties: the bulls are G03's Hornbacks (LAB06) and the ridge grazing uses the battlefield `Vegetation` bands. It sits
  beside BLIGHT01 (the herd's health) and HornbackHerd (the herd's movement) as the herd's behaviour chapter.
- Assets: `Anim_Hornback_Clash` and `Anim_Hornback_Display` (fight and bluff clips on the staged `Mob_Lab_Hornback`),
  and `Prop_Ridge_Cairn` (the ridge-top marker), with reuse of the regrowth meadow kit (see UNREAL-QUEUE /
  BLENDER-ASKS).
