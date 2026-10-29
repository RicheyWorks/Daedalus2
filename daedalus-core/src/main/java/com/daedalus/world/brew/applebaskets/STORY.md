# The Apple Baskets: Youtube Master Island, chapter 106 (youtube-master, contest G492)

Chapters 1-105 run from melody brewing (G25) to the cairn run (G489) and the gift swap (G490). The orchard's last
apples are picked, and baskets wait at the gate.

## Story

The apples are all alike, and each basket can take any number of them, even none. Keeper Oriel asks how many different
ways the apples can be shared among the baskets, where only how many go in each basket matters. Treating every apple as
different and choosing a basket for each is the trap. A WRONG count earns no credit, and with NO_APPLES left there is
nothing to share.

## Beats, mechanics and tests (`AppleBasketsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The harvest | `seeded`: 0-8 apples, 1-4 baskets | `seededIsDeterministic` |
| Ways to share | `ways()`: stars and bars, C(apples + baskets - 1, baskets - 1), from a Pascal triangle; equals brute force over every count for each basket (30 seeds) | `answerMatchesBruteForce` |
| Labelled apples is a trap | 2 apples, 2 baskets: 3 shares (2-0, 1-1, 0-2), 4 labelled picks | `trap` |
| Wrong, no apples | `count` WRONG, MALFORMED, NO_APPLES (0 apples), no credit | `wrongAndSpecialEarnNoCredit` |
| Orchard rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_apple_baskets` | colony `QuestProgress`: read harvest x1, count shares x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperAppleBaskets`)

- Greeting: "2 apples, all alike, and 2 baskets that can take any number, even none. How many different ways can the
  apples be shared?"
- Wrong: "Not 4. The apples are alike: only how many go in each basket matters."
- No apples: "The trees are bare. No apples to share."
- Quest done: "Every share counted! The orchard is grateful."
- After: "Basket by basket, the harvest goes home."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

An orchard gate with a few wicker baskets and a heap of red apples on the grass. Source-only here.
