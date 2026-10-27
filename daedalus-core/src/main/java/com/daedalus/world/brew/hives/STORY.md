# The Lucky Hives: Youtube Master Island, chapter 64 (youtube-master, contest G374)

Chapters 1-63 run from melody brewing (G25) to the festival rites (G363) and the treasure scales (G368). The trader
paid in ribbons, and the beekeepers want them on the lucky hives.

## Story

The hives on the hill are numbered from 1. The beekeepers call a hive lucky if no smaller number but 1 divides it,
and 1 itself is not lucky. Keeper Oriel asks how many lucky hives there are. Counting the odd hives, or counting
hive 1, gives a MISCOUNT and no credit.

## Beats, mechanics and tests (`LuckyHivesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hill | `seeded`: 1-200 hives | `seededHillIsDeterministic` |
| Lucky hives | `isLucky(n)` from a sieve of Eratosthenes; every hive and `lucky()` equal trial division (30 seeds) | `sieveMatchesBruteForce` |
| Odds and 1 are traps | 30 hives: 10 lucky; 1 and 9 are not | `oddsAndOneAreTraps` |
| Miscount | `count` wrong is MISCOUNT, no credit | `miscountEarnsNoCredit` |
| Hill rules | `count`: DUPLICATE, IGNORED; one hive has none lucky | `guards` |
| Quest `q_lucky_hives` | colony `QuestProgress`: visit hives x1, count lucky x1 (retries allowed), talk keeper_oriel | `questMiscountThenCountedThenKeeper` |

## Keeper Oriel's lines (`KeeperHiveLines`)

- Greeting: "Hives numbered 1 to 30. The beekeepers say a hive is lucky if no smaller number but 1 divides it, and 1
  itself is not lucky. How many lucky hives are there?"
- Miscount: "You said 11. There are 10 lucky hives."
- Quest done: "That's the count. A ribbon on every lucky hive!"
- After: "The lucky hives hum with ribbons on."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Numbered wooden hives up a hillside, bees, and ribbons tied on the lucky ones. Source-only here.
