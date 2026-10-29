# The Village Vote: Youtube Master Island, chapter 67 (youtube-master, contest G387)

Chapters 1-66 run from melody brewing (G25) to the tall palms (G378) and the pebble line (G383). The village must
choose where to build the new well.

## Story

Every villager drops a marked shell in the voting jar. A choice wins only with more than half the shells. Keeper Oriel
asks which choice wins, or whether none does. The choice with the most shells is not always a winner; a WRONG answer
earns no credit.

## Beats, mechanics and tests (`VillageVoteTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The jar | `seeded`: 1-15 shells over 1-3 choices | `seededVoteIsDeterministic` |
| The winner | `majority()`: Boyer-Moore majority vote plus a confirming count; equals brute-force tallies (30 seeds, both kinds) | `majorityMatchesBruteForce` |
| Leading is a trap | 3 of 7 shells for choice 2 leads but is not more than half | `leadingIsNotWinning` |
| Wrong | `name` the wrong choice (or none, when one wins) is WRONG, no credit | `wrongEarnsNoCredit` |
| Jar rules | `name`: DUPLICATE, IGNORED | `guards` |
| Quest `q_village_vote` | colony `QuestProgress`: open jar x1, name winner x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperVoteLines`)

- Greeting: "5 shells in the voting jar, each marked with a choice. A choice wins only with more than half the shells.
  Which choice wins, or does none?"
- Wrong: "Not so. Choice 1 has more than half." / "Not so. No choice has more than half. We vote again."
- Quest done: "That's the count. The village has spoken."
- After: "The vote is settled."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A clay voting jar, marked shells poured onto a mat, and villagers gathered round. Source-only here.
