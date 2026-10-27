# The Boatyard: Youtube Master Island, chapter 42 (youtube-master, contest G275)

Chapters 1-41 run from melody brewing (G25) to the fishing crews (G269) and the smokehouse racks (G272). The catch is
good, and the island needs one more boat before spring.

## Story

The yard board lists the jobs for a new boat: keel, ribs, planks, caulking, mast. Each takes some days, and some must
wait for others to finish; jobs with nothing to wait on run side by side. Keeper Oriel asks for the soonest launch day.
The exact day is right. A day too early would leave the hull on the trestles, and a day too late keeps the boat
ashore. Neither earns credit. A board whose jobs wait on each other in a loop can never be built and is refused.

## Beats, mechanics and tests (`BoatyardTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The yard board | `seeded`: 3-9 jobs, 1-5 days, waits from earlier to later jobs; a loop is refused | `seededYardIsDeterministicAndLoopsRefused` |
| The launch day | `launchDay()`: critical path over a Kahn topological order; equals brute-force relaxation (30 seeds) | `launchDayMatchesBruteForce` |
| Side by side | keel 3, ribs 2 and planks 4, caulk 1, mast 5: day 8, not the 15-day sum | `sideBySideIsNotTheSum` |
| Too early | a day before the critical path: `launch` is EARLY, no credit | `earlyDayEarnsNoCredit` |
| Yard rules | `launch`: LATE, DUPLICATE, IGNORED | `guards` |
| Quest `q_boatyard` | colony `QuestProgress`: plan yard x1, launch right x1 (retries allowed), talk keeper_oriel | `questLateThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperYardLines`)

- Greeting: "5 jobs on the yard board, and some must wait for others. Jobs with nothing to wait on can run side by
  side. What is the soonest day the new boat can launch?"
- Early: "Day 6? The hull would still be on the trestles. It can't be done that soon."
- Late: "Day 15 is safe, but the boat could launch on day 8. Don't keep it ashore."
- Quest done: "Right to the day. I'll tell the crews to ready the slipway."
- After: "The new boat is launched. Hear the cheer from the quay."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A boatyard with a job board, a hull on trestles that gains keel, ribs, planks and mast as days pass, and a slipway
launch. Source-only here.
