# The Crab Pens: Youtube Master Island, chapter 81 (youtube-master, contest G434)

Chapters 1-80 run from melody brewing (G25) to the gossip circles (G427) and the ring dance (G429). After the dance,
someone notices the crab pens are overflowing.

## Story

One crab was set loose in the lagoon, and every moon each crab becomes a whole brood. After many moons the crabs are
shared into pens of equal size. Keeper Oriel asks how many are left over, without counting a single crab: square the
brood and halve the moons. Multiplying the brood by the moons is a trap, since crabs multiply. A WRONG count or a bad
pick earns no credit, and if a brood exactly fills the pens it is WASHED_OUT and there is nothing to count.

## Beats, mechanics and tests (`CrabPensTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The pens | `seeded`: brood 0-9, moons 1-40, pens of 2-13 | `seededPensAreDeterministic` |
| Left over | `leftOver()`: binary exponentiation mod pen (at most 12 steps for 40 moons, under 60 for a billion); equals brute force moon by moon (30 seeds) | `leftOverMatchesBruteForce` |
| Brood times moons is a trap | 3 x 13 = 39 leaves 4; 3^13 leaves 3 | `broodTimesMoonsIsATrap` |
| Wrong, washed out | `count` WRONG, MALFORMED, WASHED_OUT (brood 14, pens of 7), no credit | `wrongAndWashedOutEarnNoCredit` |
| Pen rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_crab_pens` | colony `QuestProgress`: watch pens x1, count leftover x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperCrabPens`)

- Greeting: "One crab, and every moon each crab becomes 3. After 13 moons we share them into pens of 7. How many are
  left over?"
- Wrong: "Not 4. Square and halve, square and halve."
- Washed out: "Each brood fills the pens exactly. None left over, nothing to count."
- Quest done: "Exactly right! The left-over crabs go to the soup pot."
- After: "The pens are full and the soup is on."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Woven crab pens in the lagoon shallows, scuttling crabs, and a soup pot on the shore. Source-only here.
