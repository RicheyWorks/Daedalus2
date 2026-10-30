# The Gift Swap: Youtube Master Island, chapter 105 (youtube-master, contest G490)

Chapters 1-104 run from melody brewing (G25) to the regatta order (G487) and the cairn run (G489). Midwinter comes, and
the islanders swap gifts by lot.

## Story

Every friend puts a gift in the basket and draws one out. The swap only works if nobody draws their own gift. Keeper
Oriel asks how many ways the draw can go with nobody getting their own. Counting every draw except the one where
everyone keeps their own is the trap, since a draw where just one person keeps theirs fails too. A WRONG count earns no
credit, and one friend ALONE can't swap at all.

## Beats, mechanics and tests (`GiftSwapTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The friends | `seeded`: 1-7 friends | `seededIsDeterministic` |
| Good draws | `ways()`: derangement recurrence D(n) = (n - 1)(D(n - 1) + D(n - 2)), D(0) = 1, D(1) = 0; equals brute force over every draw (30 seeds) | `answerMatchesBruteForce` |
| All but one draw is a trap | 3 friends: 2 good draws, not 5 | `trap` |
| Wrong, alone | `count` WRONG, MALFORMED, ALONE (one friend), no credit | `wrongAndSpecialEarnNoCredit` |
| Swap rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_gift_swap` | colony `QuestProgress`: read friends x1, count draws x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperGiftSwap`)

- Greeting: "3 friends put gifts in the basket and each draws one. In how many draws does nobody get their own gift?"
- Wrong: "Not 5. If even one friend draws their own gift, the swap fails."
- Alone: "One friend can't swap with nobody. Nothing to count."
- Quest done: "Every good draw counted! Let the swap begin."
- After: "Wrapped, drawn and opened, and nobody's gift came home."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A midwinter hall with a woven basket of wrapped gifts and a ring of chairs by the fire. Source-only here.
