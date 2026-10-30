# Kennel Isle: The Ark Glass Cellar (contest gap G45)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/TonicBottler.java`, test `TonicBottlerTest` (6 tests). Composes `TonicBrewer` (tonic engine) and the water grade from the G17 water loop.

## Mechanic
- Quality score = brew strength factor (0-2) x 50, plus the water grade (raw -15, filtered 0, spring +10), plus 15 if the Labyrinth second roll landed.
- Tiers: **T1** under 40, **T2** 40-69, **T3** 70-99, **T4** 100+ and spring water only.

| Tier | Duration | Shelf life | Materials |
|------|----------|-----------|-----------|
| T1 | x1.0 | 3 days | bottle |
| T2 | x1.25 | 7 days | bottle, cork |
| T3 | x1.5 | 14 days | bottle, cork, wax |
| T4 | x2.0 | 30 days | ark glass, cork, wax |

- If the shelf can't pay for the tier the brew deserves, it's bottled at the best tier the materials allow. With no bottle at all, nothing is bottled.
- Each time a bottle outlives its tier's shelf life, it drops one tier (and the next tier's shelf life starts). Below T1 it has spoiled, and it's worth nothing.

## Lore
Glass doesn't keep on a broken planet. Salt air etches it and the quakes crack it. The only glass that lasts came down with the arks: hull ports thick as a fist, made to survive the fall through the sky. The keepers pry the ports out of the wrecks on the north shore and melt them into bottles. A tonic sealed in ark glass keeps for a month. Everything else, drink it this week.

## Quest: The Ark Glass Cellar
Marrow wants the cellar stocked before storm season, when nobody can reach the spring.
1. Salvage ark glass from a wreck (one bottle's worth).
2. Brew a full-strength tonic with spring water and seal it in ark glass (T4).
3. Bottle three more at T3 or better.
4. On day 10, the cellar must hold one T4 and at least four bottles at T3 or better. Old bottles age, so time it.

## NPC lines
- **Marrow** (start): "Storms come, the spring's cut off. What's in the cellar is what the dogs get."
- **Pip** (salvage): "This window was on an ark! It's heavy. Is it supposed to hum?"
- **Marrow** (T1 bottle): "That'll keep three days. Drink it or lose it."
- **Marrow** (T4 bottle): "Ark glass and spring water. That one'll outlast the storm."
- **Marrow** (spoiled): "Smell that? That's a week ago. Pour it out."

## Later (editor)
Bottling interaction at the brew bench; bottle mesh per tier (ark glass is blue-green); a cellar shelf shows tier and days left. Bottle meshes go to blender-team as a NEED; editor work is queued in BOARD\UNREAL-QUEUE.md.
