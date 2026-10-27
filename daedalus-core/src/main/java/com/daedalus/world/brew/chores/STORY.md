# The Chore Days: Youtube Master Island, chapter 91 (youtube-master, contest G468)

Chapters 1-90 run from melody brewing (G25) to the twin baskets (G463) and the tide marks (G466). The festival is a
week away, and the village has a list of chores.

## Story

Some chores must wait for others: the hall is swept before the tables go up, and the tables go up before the
lanterns are hung. The whole village works at once, so any chore whose earlier chores are done can start that day.
Keeper Oriel asks for the fewest days to finish everything. One chore a day is the trap, since chores with nothing
between them share a day. A WRONG count earns no credit, and a TANGLED list, where chores wait on each other in a
loop, can never be finished.

## Beats, mechanics and tests (`ChoreDaysTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The list | `seeded`: 1-5 chores, 0-5 "before" rules (loops possible) | `seededIsDeterministic` |
| Fewest days | `days()`: Kahn's algorithm in layers (every chore with no unfinished earlier chore is done the same day); equals brute force over every day plan (30 seeds), and both agree on loops | `answerMatchesBruteForce` |
| One a day is a trap | 4 chores, 0 before 1 and 2, both before 3: 3 days, not 4 | `trap` |
| Wrong, tangled | `count` WRONG, MALFORMED, TANGLED (0 before 1 before 0), no credit | `wrongAndSpecialEarnNoCredit` |
| Village rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_chore_days` | colony `QuestProgress`: read chores x1, count days x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperChoreDays`)

- Greeting: "4 chores before the festival, and some must wait: [[0, 1], [0, 2], [1, 3], [2, 3]]. Everyone works at
  once. What is the fewest days?"
- Wrong: "Not 4. Chores with nothing between them can share a day."
- Tangled: "These chores wait on each other in a loop. They can never be done."
- Quest done: "Fewest days! The festival can start early."
- After: "Swept, set and lit, one layer at a time."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A village hall with brooms, stacked tables and unlit festival lanterns, and a chore board by the door. Source-only here.
