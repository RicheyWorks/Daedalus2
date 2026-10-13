# ADR-057: The Orrery Reach (Claude Island) and its game, Starbloom Steeping

Status: accepted (code written; compiled and verified in the Claude editor slot)
Date: 2026-10-12

## Why

Richmond set the bar: "the goal is to build the biggest metaverse ever". He wants it "as immersive as" the greatest
adventure games, with every bot inventing an original realm, mechanic and adventure. Claude's entry is Claude Island,
in a realm of its own, the Orrery Reach (`docs/realms/OrreryReach.md`).

## Decision

**500 original items** come from one generator (`tools/claude_island/orr_build.py`, headless Blender, 34 s).
- Every item passes the art rules: 500/500 in `orr_check.py`.
- They ship through the art queue, first in Claude's slot, using the watcher's new `--first _Orr_` flag.

**The island** is laid out by `tools/claude_island/orr_place.py`.
- It lives in its own sublevel, `/Game/Claude/ClaudeIsland_Sub`, 4 km east of the unreal-team ARK_ORIGIN.
- It is a 240 m terrace disc over a hanging rock, with the observatory on the summit.
- It has districts for herbs, water, pens, the plaza, crops, the dock and the sky.

**The game** lives in `DaedalusOrrery.h/.cpp`, in the DaedalusLink plugin.

**`UDaedalusOrrery`** is a world subsystem. It holds the sky hour, which is the Sky Director's (ADR-056) when there
is one and the island's own clock otherwise. It also holds the satchel, the brews, the charts, the logbook step and
clean water.
- **24 herbs, one per hour.** The 12 constellations each have one day bloom and one night bloom.
- **What a steep makes:**
  - one herb makes its tea;
  - a constellation's pair makes its brew;
  - a day bloom and a night bloom from different constellations make one of 8 eclipse brews.
- **Clean water is required** for any steep.
- **Effects:** a tea heals, a brew restores health and shield, an eclipse brew overcharges.

**`ADaedalusUsable`** is the base of everything the hero uses with Interact. The hero checks for one in reach before
Ghosts and portals.
- **`ADaedalusStarbloom`** is a bud until its hour. It then shows its Bloom art, glows and pulses, and can be
  harvested once per bloom hour.
- **`ADaedalusKettle`**: the steeping kettle.
- **`ADaedalusWaterFilter`**: the storm-clogged sand filter. Fixing it makes the water drinkable.
- **`ADaedalusStarChart`**: the twelve charts. Each slowly turns and glows, and names its constellation's two herbs.
- **`ADaedalusKeeper`**: Keeper Ostra at the dock, with one line per logbook step. She never gives a recipe outright;
  the charts do that.

**The Keeper's Logbook** has nine steps, each unlocked only by the one before:
1. Meet the Keeper.
2. Fix the filter.
3. Find the Lantern chart.
4. Harvest a bloom in its hour.
5. Steep a tea.
6. Steep a constellation brew.
7. Recover all twelve charts.
8. Steep an eclipse brew.
9. The telescope and the new moon (the phase 2 hook).

**On the HUD**, inside 250 m of any usable, top centre: the sky clock and the current objective, the last thing that
happened, the `[E]` prompt for whatever is in reach, and the satchel.

## Proof

The harness scenario `orrery` plays the first six steps with real Interact calls:
- the Keeper;
- the filter;
- the Lantern chart;
- harvesting Duskmallow at 18:00;
- a Duskmallow tea;
- Sunsprig at 8:00 plus a regrown Duskmallow at the next dusk, making the Lantern Brew.

## Held

- **Voiced dialogue and music cues** wait for the jukebox endpoint (ADR-052).
- **The vault and telescope finale (step 9)** waits for the Phase 2 moon.
- **Bees making honey only near a blooming bed** waits for livestock code that every island can share; youtube-master
  is writing `ADaedalusLivestock`.
