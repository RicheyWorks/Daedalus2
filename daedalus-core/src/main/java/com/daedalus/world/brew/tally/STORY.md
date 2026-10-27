# The Pebble Line: Youtube Master Island, chapter 66 (youtube-master, contest G383)

Chapters 1-65 run from melody brewing (G25) to the lucky hives (G374) and the tall palms (G378). Under the palms the
children play the pebble game.

## Story

Pebbles of different sizes lie in a line. You may only swap two neighbours at a time. Keeper Oriel asks how few swaps
line them up from smallest to largest, and tallies the answer on a stick. A guess like 4 is a trap (the big pebble passes the three others once each),
and equal pebbles never need a swap; a MISCOUNT earns no credit.

## Beats, mechanics and tests (`PebbleLineTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The line | `seeded`: 1-12 pebbles of size 1-9 | `seededLineIsDeterministic` |
| Fewest swaps | `swaps()`: inversions counted with a Fenwick tree; equals bubble-sort swaps and brute-force pair counts (30 seeds) | `swapsMatchBruteForce` |
| Guessing is a trap | sizes 3, 1, 2, 2: 3 swaps, not 4; ties need none | `misplacedIsATrap` |
| Miscount | `count` wrong is MISCOUNT, no credit | `miscountEarnsNoCredit` |
| Game rules | `count`: DUPLICATE, IGNORED (blank id or negative) | `guards` |
| Quest `q_pebble_line` | colony `QuestProgress`: line pebbles x1, count swaps x1 (retries allowed), talk keeper_oriel | `questMiscountThenCountedThenKeeper` |

## Keeper Oriel's lines (`KeeperPebbleLines`)

- Greeting: "4 pebbles in a line. You may only swap two neighbours at a time. How few swaps line them up smallest to
  largest?"
- Miscount: "You said 4 swaps. It takes 3."
- Quest done: "Exactly that many. Tally it on the stick!"
- After: "The pebbles stand in order, smallest first."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A line of pebbles of different sizes on flat sand, children's hands, and a notched tally stick. Source-only here.
