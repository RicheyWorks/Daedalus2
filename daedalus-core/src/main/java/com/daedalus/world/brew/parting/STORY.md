# The Parting Jars: Youtube Master Island, chapter 16 (youtube-master, contest G167)

Chapters 1-15 run from melody brewing (G25) to the guest lofts (G149) and the apprentices (G155). The families are
going home, and the children are staying.

## Story

Every visiting family wants to sail with a jar of home: salt fish for Kelp Harbour, salt bacon for Cinder Reach,
pickled eggs for Glass Shoals, dried moonbeans for Far Orchard. Aunt Brine's new apprentice does the work, one order
at a time, starting the day the first family comes ashore. Salting takes a day a jar, pickling or smoking two,
drying three. A jar finished after its family has sailed is no use to anyone. The player sets the work order. The
trick Brine teaches: work to whoever leaves first, and if that makes someone late, drop the longest job you've
taken on. That sends the most families home with a jar.

## Beats, mechanics and tests (`PartingJarsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| A jar of home, kept the longest way | `methodFor` (G73 `Preserve.shelfDays`, best non-fresh method), `forFamilies` (G149 families, G97 favourites, seeded 1-2 jars, due = leave day, start = first arrival) | `eachFamilyGetsTheirIslandsFavouriteKeptTheLongestWay` |
| Drop the longest when someone would be late | `onTime`, Moore-Hodgson `best()` | `mooreHodgsonDropsTheLongestWhenLate` |
| No plan does better | best equals brute force over every subset (30 seeds); working everything in due order is not always best | `bestMatchesBruteForceAndThePuzzleBites` |
| Quest `q_parting_jars` | colony `QuestProgress`: plan jars x1, fill shelf x1 (FULL_SHELF), talk aunt_brine; guards EMPTY, REPEATED, UNKNOWN_FAMILY | `questShortThenFullShelfThenBrine` |

## Lines (`ApprenticeJarLines`)

- Brine: "Every family wants a jar of home to sail with, and the apprentice has two hands. Salt's a day, pickle or
  smoke two, drying three, per jar. Finish it after they've sailed and it just sits on my shelf."
- Short: "5 families sail with a jar. 6 could. Look at who's leaving first."
- Quest done: "As many jars as the days allowed, and not one left behind on the shelf. That apprentice will do."
- After: "The shelf's for parting jars now. Every ark that leaves takes a taste of here."

## Editor later (UNREAL-QUEUE)

Cellar work bench with the G155 apprentice, an order-rail UI (cards per family with food, method, days and leave
day; drag to order; a late card turns grey), jars handed over at the G139 jetty as each family boards. Source-only
here.
