# The Festival Rites: Youtube Master Island, chapter 62 (youtube-master, contest G363)

Chapters 1-61 run from melody brewing (G25) to the rope splicing (G357) and the berry patch (G360). The berries are
jam, and the harvest festival is ready to begin.

## Story

The festival has numbered rites, and some must come after others (the jam blessing after the fire lighting, and so
on). Of all the orders that keep every need, the elders want the one that reads first on the list. Keeper Oriel asks
the player for it. An order that breaks a need is OUT_OF_ORDER, a valid but later order is NOT_FIRST, and a circle of
needs is TANGLED; none earns credit.

## Beats, mechanics and tests (`FestivalRitesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The list | `seeded`: 1-6 rites, 0-7 needs drawn forward over a shuffled list | `seededFestivalIsDeterministic` |
| The first order | `order()`: Kahn's algorithm with a min-heap; equals the first valid permutation by brute force (30 seeds) | `orderMatchesBruteForce` |
| Needs-first is a trap | needs 3>0, 2>1: first order 2,1,3,0; 3,0,2,1 is NOT_FIRST | `greedyByNeedsIsNotFirst` |
| Wrong orders | OUT_OF_ORDER, MALFORMED and TANGLED (cycle), no credit | `wrongOrdersEarnNoCredit` |
| List rules | `give`: MALFORMED repeats, DUPLICATE, IGNORED | `guards` |
| Quest `q_festival_rites` | colony `QuestProgress`: read list x1, order first x1 (retries allowed), talk keeper_oriel | `questWrongThenFirstThenKeeper` |

## Keeper Oriel's lines (`KeeperRiteLines`)

- Greeting: "4 festival rites, and some must come after others. Of all the orders that work, the elders want the one
  that reads first in the list. What is it?"
- Out of order: "Rite 0 can't come before rite 3."
- Not first: "That order works, but [2, 1, 3, 0] reads first."
- Tangled: "These rites wait on each other in a circle. No order can work."
- Quest done: "That's the order. Ring the start!"
- After: "The rites run in order. The festival begins."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A festival board with numbered rite cards strung in order, a start bell, and the fire pit. Source-only here.
