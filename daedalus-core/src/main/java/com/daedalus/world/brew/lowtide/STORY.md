# The Low Tide Walk: Youtube Master Island, chapter 43 (youtube-master, contest G278)

Chapters 1-42 run from melody brewing (G25) to the smokehouse racks (G272) and the boatyard (G275). The new boat needs
pitch from the far shore, and at low tide the flats can be crossed on foot.

## Story

The tide almanac lists the water level for every hour, and crossing the flats takes a few hours in a row. The danger
of a crossing is the deepest water met on the way. Keeper Oriel asks for the hour to set out so that the deepest water
is as low as it gets. The player reads the almanac and sets out. A start at the safest danger is right; any deeper
crossing earns no credit, even if it passes through the single lowest hour.

## Beats, mechanics and tests (`LowTideWalkTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The almanac | `seeded`: 4-16 hours, levels 0-9, a 2-4 hour walk | `seededAlmanacIsDeterministic` |
| The safest start | `danger(h)`: sliding-window maximum by a monotonic deque; every window and `safest()` equal brute force (30 seeds) | `windowsMatchBruteForce` |
| The lowest hour is a trap | 5,1,7,2,2,3,8,0,6 with 3 hours: through the 0 the walk meets 8; hours 3-5 peak at 3 | `lowestHourIsNotSafest` |
| Deep water | a start above the safest danger: `walk` is DEEP, no credit | `deepWalkEarnsNoCredit` |
| Flats rules | `walk`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_low_tide_walk` | colony `QuestProgress`: read almanac x1, walk safe x1 (DEEP can be retried), talk keeper_oriel | `questDeepThenSafeThenKeeper` |

## Keeper Oriel's lines (`KeeperTideLines`)

- Greeting: "9 hours in the almanac, and the flats take 3 hours to cross. Pick the hour to set out so the deepest
  water on the way is as low as it gets."
- Deep: "Setting out at hour 5, the water reaches 8. It never needs to pass 3. Wait for a better tide."
- Quest done: "Dry boots, or near enough. That was the safest tide."
- After: "You're across. The tide is coming back in behind you."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Tidal flats with a water plane that follows the almanac hour by hour, a tide-almanac board, and footprints across
the sand. Source-only here.
