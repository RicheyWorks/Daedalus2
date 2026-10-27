# The Weak Bridges: Youtube Master Island, chapter 75 (youtube-master, contest G415)

Chapters 1-74 run from melody brewing (G25) to the twin braids (G407) and the lamplighter's round (G410). Winter
storms are coming, and there is only so much new rope.

## Story

Small islets off the shore are joined by rope bridges, and some pairs of islets have two ropes side by side. Keeper
Oriel asks for every bridge that, if it snapped, would leave someone cut off; only those get new rope. Marking both
of a pair of side-by-side ropes is a trap, since each backs the other up. A MISSED set, a WRONG set that marks a safe
bridge, or a bad pick earns no credit, and if some islet has no bridge to the rest the islets are SCATTERED.

## Beats, mechanics and tests (`WeakBridgesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The islets | `seeded`: 1-6 islets, 0-8 bridges (repeats allowed) | `seededIsletsAreDeterministic` |
| Weak bridges | `weak()`: Tarjan bridge-finding (discovery time, low link, skip only the bridge we came by); equals brute force cutting each bridge in turn (30 seeds) | `weakMatchesBruteForce` |
| Twin ropes are a trap | the two 3-4 ropes back each other up; only 2-3 is weak | `twinRopesAreATrap` |
| Missed, wrong, scattered | `mark` MISSED, MALFORMED, SCATTERED (islets not all joined), no credit | `missedWrongAndScatteredEarnNoCredit` |
| Rope store rules | `mark`: IGNORED, DUPLICATE | `guards` |
| Quest `q_weak_bridges` | colony `QuestProgress`: cross islets x1, mark bridges x1 (retries allowed), talk keeper_oriel | `questWrongThenExactThenKeeper` |

## Keeper Oriel's lines (`KeeperWeakBridges`)

- Greeting: "5 islets and 6 rope bridges. Mark every bridge that, if it snapped, would leave someone cut off. Only
  those get new rope this winter."
- Missed: "You marked 1, but 2 bridges would cut someone off."
- Wrong: "One you marked has another way round. Save the rope."
- Scattered: "Some islets have no bridge to the rest at all. Build first, mend later."
- Quest done: "Exactly the weak ones. New rope on every one!"
- After: "The weak bridges have fresh rope. No one will be cut off."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Small islets joined by sagging rope bridges, some doubled, with coils of new rope on the shore. Source-only here.
