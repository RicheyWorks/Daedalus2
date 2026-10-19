# MOTH01 — Soot Moths (contest G103)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/SootMoths.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/SootMothsTest.java` (10)
Links: Hephaestus forge islands (the smoke), LICHEN01 Lichen Clock (lichens need clean bark), WEB01 Wood Wide Web (the
same trees).

## Story

A century of forge smoke from the Hephaestus islands blackened every trunk downwind. The peppered moths rest on that
bark by day, and the birds eat whatever shows. A pale moth on black bark is a meal. Now the moths are nearly all
dark. The forge still has to make iron for the arks, but the island's naturalist, Dr. Wren Kettle, wants the old pale
moths back on lichen-grey bark.

"You can't tell a bird what to eat," she says. "You can change what it sees."

## Quest `q_soot_moths` — "What the Bird Sees"

1. **Count the moths.** There are 500 adults and the dark allele is at 0.6 (most moths look dark). The bark is at 0.8 soot.
2. **Plan the forge.** Set a burn level (0–1) for each of the 4 decades. The arks need 24 level-years of iron.
3. **Fit filters.** You have up to 3 smoke filters, each removing 25% of the soot.
4. **Run 40 years.** The outcome:
   - **RESTORED**: at least half the moths are pale at the end, the iron goal is met, and both morphs survive. Reward: clean OAK-band bark and the lichens return (LICHEN01).
   - **DARKENED**: a goal missed.
   - **MORPH_LOST**: drift or selection wiped out one morph.

NPC lines (Dr. Wren Kettle):
- Start: "Every dark moth you see is one the birds missed."
- Full burn: "Black bark, black moths. The forge wins again."
- Restored: "A pale one on grey bark. I almost walked past it, and so did the thrush."

## Rules (deterministic from the seed and the plan)

- Bark soot changes by −20% (rain) + 0.2·level·(1 − filters·0.25) each year, so it settles at level·(1 − filter share).
- Birds take 20% of visible moths: dark moths with chance 0.2·(1 − bark), pale moths with chance 0.2·bark.
- Dark (D) is dominant, and mating is random (Hardy-Weinberg), so the dark share is 1 − (1 − q)².
- The next q comes from selection and then seeded sampling of 2N gene copies (genetic drift).

## What the tests pin

- A full forge darkens bark and moths.
- 3 filters with a 0.6 forge restore the moths on seeds 1–6.
- A cold forge misses the iron goal.
- Bark settles at the soot/rain balance.
- Birds favour the moth that matches the bark (very large population, no drift).
- Without birds only drift moves q, and the mean stays put.
- A tiny population loses a morph to drift more often.
- The dark share follows Hardy-Weinberg.
- Determinism, budgets and bad input.

## Host seam

- `SootMoths.population(Settings, seed)`, then `forge(decade, level)` / `filter()`, then `run()` → `Report`.
- `years()` drives the moth chart: forge, bark, q, dark share, eaten.
- `Report.bark()` sets the trunk band (BARE soot / SCRUB / OAK clean).
- Assets: moth pair (dark and pale, ~4 cm, resting pose), a bark soot material param, and a smoke filter prop on the forge chimney (see UNREAL-QUEUE / BLENDER-ASKS). Staged by blender-team (NOT READY) in `bot-team\staging\g103-soot-moths-20261019`: `Mob_Moth_Peppered` (4.5 cm, 332 tris, 10 bones, clips Idle + Flutter, rig from `tools/blender/creatures/insect_rig.py`; slot 0 `Morph` takes `MI_Mob_Moth_Peppered_Pale` or `_Dark`, and a swarm spawns Dark at share 1-(1-q)^2), `Prop_Forge_SmokeFilter` (1.1 m hood for a 0.6 m flue, `SOCKET_Chimney` + `SOCKET_Smoke`, UCX) and `M_Bark_Soot` with a `Soot` scalar (`MI_Bark_Clean` 0.0 for OAK bark, `MI_Bark_Sooted` 0.8 for BARE).
