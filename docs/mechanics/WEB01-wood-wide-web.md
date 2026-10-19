# WEB01 — Wood Wide Web (contest G82)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/WoodWideWeb.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/WoodWideWebTest.java` (11)
Links: ASH01 Ashfall Regrowth (the forest bands), SALMON01 Salmon Run (the forest the salmon feed), VAULT01 Seed Vault
(the seedlings came from it).

## Story

The ark seed came up, but a pine seedling under a closed canopy cannot make enough sugar on its own. Under the soil
of the regrown fragment, fungal threads (mycorrhizae) join tree roots into one web, and the big old mother trees pass
carbon down it to the shaded young. The island needs timber, and the biggest trees are the mothers.

Forester Hesper Ngaio walks the stand with a spore pouch and a marking axe. "Cut what the web can spare. Never the
hub."

## Quest `q_wood_wide_web` — "Never the Hub"

1. **Read the stand.** It is an 8×8 seeded grid of mothers, mature trees, seedlings and gaps. Mothers and half the mature trees start colonized.
2. **Mark the timber.** The island needs 10 timber: a mature tree gives 1, a mother gives 3.
3. **Inoculate.** You have 6 spore doses; each colonizes one tree.
4. **Run 12 years.** The outcome:
   - **OLD_GROWTH**: at least 60% of the starting seedlings raised, timber met, and a mother still standing. Reward: an old-growth band (OAK mothers) on the ecology grid.
   - **THINNED**: a goal missed.
   - **COLLAPSED**: no seedling raised, or nothing left alive.

NPC lines (Hesper Ngaio):
- Start: "The big ones are the easy timber. They're also the ones feeding the rest."
- Felled mother: "There goes the hub. Watch the little ones go yellow."
- Old growth: "Ten timber and a forest still standing. That's forestry."

## Rules (deterministic from the seed and the plan)

- Each year a mother makes 4 carbon, a mature tree 1, and a shaded seedling needs 1. A drought (30% of years, seeded) costs every tree 1 more.
- Each year a colonized tree colonizes each bare orthogonal neighbour with chance 0.5. Every draw is fixed per year and cell, so the plan never shifts the dice elsewhere.
- In each connected network, every tree books its own carbon. Donors give what they hold above the reserve (2, the starting store), and that pool pays the trees that would die, each just enough to live. The web never half-saves two trees and loses both.
- A tree below zero carbon dies. That can cut the web in two.
- A seedling that lives 5 years becomes mature.
- Bands: mother → OAK, mature → PINE, seedling → SCRUB, gap → MEADOW.
- `planted(settings, seed, "M.S/TtS")` lets quests hand-plant a stand: M is a mother, T a colonized mature tree, t a bare mature tree, S a seedling, and . a gap.

## What the tests pin

- A lone seedling starves in its third year.
- A mother feeds the seedlings her threads reach, and the fungus spreads on its own.
- In drought the web saves who it can and keeps the mother.
- A seedling whose bridge dies is cut off.
- Felling the mothers more than halves the seedlings raised.
- Timber counts mothers heavier.
- The plan never shifts the weather.
- Bands, determinism, budgets and bad input.

## Host seam

- `WoodWideWeb.stand(Settings, seed)` or `planted(...)`, then `log(x, y)` / `inoculate(x, y)`, then `run()` → `Report`.
- `years()` drives the stand timeline: drought, networks, linked trees, seedlings, deaths.
- `band(i)` paints the forest cells.
- Assets: reuse the pcg-ecology trees. Fungal threads are a ground decal or VFX, plus a marking-axe blaze decal and a spore pouch prop (see UNREAL-QUEUE / BLENDER-ASKS).
