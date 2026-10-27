# The Twin Baskets: Youtube Master Island, chapter 89 (youtube-master, contest G463)

Chapters 1-88 run from melody brewing (G25) to the net rack (G456) and the shell purse (G460). The ferry is loading,
and every trip carries exactly two baskets.

## Story

The ferry must carry exactly its load each trip, two baskets at a time. Keeper Oriel asks how many pairs of baskets
on the dock weigh exactly the load together. Counting basket A with B and again B with A is the trap. A WRONG count
earns no credit, and a dock with FEW baskets (fewer than two) has no pair to make.

## Beats, mechanics and tests (`TwinBasketsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The dock | `seeded`: 0-9 baskets weighing 1-6, load 2-12 | `seededIsDeterministic` |
| Pairs | `pairs()`: one pass with a hash map of weights seen so far (two-sum counting); equals brute force over every i < j (30 seeds); `ordered()` is exactly twice it | `answerMatchesBruteForce` |
| Both ways is a trap | baskets 1 2 3 4 3, load 6: 2 pairs, 4 ordered | `trap` |
| Wrong, few | `count` WRONG, MALFORMED, FEW (one basket), no credit | `wrongAndSpecialEarnNoCredit` |
| Dock rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_twin_baskets` | colony `QuestProgress`: read baskets x1, count pairs x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperTwinBaskets`)

- Greeting: "The baskets on the dock weigh [1, 2, 3, 4, 3], and each ferry trip carries two that weigh 6 together.
  How many pairs could go?"
- Wrong: "Not 4. A with B is the same pair as B with A."
- Few: "One basket can't make a pair. Nothing to count."
- Quest done: "Every pair found! The ferry runs full."
- After: "Two by two, the baskets cross the water."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A ferry dock with woven baskets of different sizes and a small two-basket ferry. Source-only here.
