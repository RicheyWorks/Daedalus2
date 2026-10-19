# FIRE01 Fireline Warden (minigame core)

Owner: pythagoras (contest gap G27, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/FirelineWarden.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/FirelineWardenTest.java` (11 cases).
It reuses the Reactive Battlefield Ecology field and fire spread (ADR-061: `BattlefieldEcology.tick`, `IGNITE`, `DOUSE`).
It pairs with ASH01 Ashfall Regrowth (G20): the growth you brought back is the fuel you now have to defend.

## Story (shattered-planet canon)

The fragments that regrew after the impact (ASH01) have a dry season. Lightning walks the ridge, the wind turns
south, and a wall of fire comes down through the bramble toward the homestead the ark families built. Warden Ilsa,
the seed keeper, gives you three hands, a water cart from the spring and one rule: "You cannot fight it out there.
Fight it here, close to home, and choose what you give up."

## Quest `q_fireline`

| Step | Trigger (what the core reports) | NPC line |
| --- | --- | --- |
| 1 Smoke | `ignite(...)` > 0, `frontDistance()` large | **Warden Ilsa** (`npc_ark_seedkeeper`): "Lightning on the ridge, and the wind is behind it. Three of us, six strides from the yard. Move." |
| 2 Break | first `cut` | **Herder Bram** (`npc_ark_herder`): "A cut line holds for good, but whatever we cut is gone. That bramble took four seasons to grow." |
| 3 Wet line | first `wet` | **Spring tender Oru** (`npc_spring_tender`): "Wet ground will not catch, but it dries in eight breaths, and the cart only brings one load a breath." |
| 4 Close | `frontDistance() <= 2` | Ilsa: "It is at the fence! Douse what is burning, now!" |
| Win HELD | `Outcome.HELD` | Ilsa: "The yard stands and most of the green with it. That is a warden's work." Reward: `warden_badge`, `lore_fireline` |
| Win SAVED | `Outcome.SAVED` | Ilsa: "The yard stands. The hills will need the seed caches again." (Points back to ASH01.) |
| Lose | `Outcome.LOST` | Ilsa: "The yard is burning. Get the families to the ark." (Retry with a new seed.) |

## Rules (deterministic from the field seed and the crew's moves)

1. **The fire** is ADR-061 fire on a `BattlefieldEcology` field. Wind pushes it downwind, scrub and pine carry it,
   and burnt cells go bare. `ignite(x, y, radiusCm)` is the lightning or a stray shell.
2. **The crew** has `crew` actions per tick (default 3), all within `reach` cells of the homestead (default 6).
3. **Cut** clears a cell to bare ground. The break is permanent, but the growth counts as lost. Burning cells
   cannot be cut.
4. **Wet** costs one water and keeps a cell fireproof for `wetTicks` (8). Then it dries and can burn. The growth
   survives.
5. **Douse** costs one water and puts out a burning cell.
6. **Water**: the tank holds 24 and the cart brings back 1 per tick, never above the tank.
7. **End**: LOST the moment any homestead cell burns. Otherwise, once the fire is out, HELD if 60% of the starting
   growth survives (neither burnt nor cut), else SAVED. `frontDistance()` is the nearest flame to the yard, for the
   HUD and NPC lines.

## What the tests prove

An unfought fire downwind takes the homestead in at least 6 of 8 storms. A cut ring 3 cells out always saves it
(22 cells cut). A wet line 1 cell out saves it too, and spends water. Dousing every flame in reach holds every storm
and saves more growth than doing nothing. Also tested: crew actions per tick and reach; water running out and the
cart refilling only up to the tank; a wet cell that will not burn while wet and dries on time; dousing needs
flames; the front closing in downwind; determinism; no ticks after the homestead is lost; bad input refused.

## Host seam (Unreal, later)

Pass the island field the host already streams through `Dbe.write` -> `UDaedalusEcology`. Map crew interactions
to `cut/wet/douse` and run `tick()` on the combat tick. Combat IGNITE events (DBE-E 1) can call `ignite`. Assets:
crew (reuse Mob villagers), water cart, and the pcg-ecology flora bands. The editor binding goes in `BOARD/UNREAL-QUEUE.md`.
