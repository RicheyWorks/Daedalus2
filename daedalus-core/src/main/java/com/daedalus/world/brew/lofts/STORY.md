# The Guest Lofts: Youtube Master Island, chapter 14 (youtube-master, contest G149)

Chapters 1-13 run from melody brewing (G25) to the song school (G116), the graduation concert (G131) and the
harbour round (G139). The ark that heard the round has come in, full of families.

## Story

Two families from each far island have crossed to see their children sing. They come off the ark on different
days, depending on how far their island is and how long they waited for a berth, and each stays a few days. Aunt
Brine has the homestead lofts, but every loft she airs is a whole set of linen to wash and dry in the salt wind.
One family to a loft at a time; a family leaving in the morning frees the loft for one arriving that afternoon.
The player plans who sleeps where. Brine knows the trick: you never need more lofts than the most families ever
here on one night, and if you house them in the order they arrive, each in any loft already free, you get exactly
that.

## Beats, mechanics and tests (`GuestLoftsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Two families per far island, arriving after the voyage | `fromFarIslands`: arrive = 1 + legs x `LettersByArk.DAYS_PER_LEG` + wait 0-3, stay 2-6 days (seeded) | `familiesComeOffTheArkAfterTheVoyage` |
| Leaving in the morning frees the loft | `Family.overlaps` on half-open stays; `maxOverlap`; `greedyPlan` | `leavingInTheMorningFreesTheLoft` |
| The fewest lofts | `fewest()` = max overlap; the greedy plan always reaches it, and exhaustive search shows one fewer never fits (40 seeds) | `greedyPlanUsesTheFewestLofts` |
| Brine's rules | `assign`: CLASH, ALREADY_HOUSED, NO_SUCH_LOFT, UNKNOWN_FAMILY; `moveOut`: NOT_HOUSED; `settle`: NOT_EVERYONE | `guards` |
| Quest `q_guest_lofts` | colony `QuestProgress`: house family x8 (counted once each), settle lofts x1 (SNUG; SPRAWL can be fixed by moving), talk aunt_brine | `questSprawlThenSnugThenAuntBrine` |

## Aunt Brine's lines (`BrineLoftLines`)

- Greeting: "Families off the ark, and every loft I air is a set of linen to wash. One family to a loft, mind.
  Someone leaving in the morning frees it for someone coming that day."
- Housing: "3 families still on the jetty with their bags."
- Sprawl: "8 lofts aired? I could've done it with 3. Shuffle them round."
- Quest done: "Everyone under a roof and not a sheet wasted. Their children have been showing them the record
  player all morning."
- After: "The lofts are aired whenever the ark's in."

## Editor later (UNREAL-QUEUE)

Loft rooms above the homestead, a stay-calendar UI (one bar per family across the days, drag onto a loft row, red
on a clash, linen counter), Aunt Brine at the linen cupboard, far-island family NPCs meeting the G116 children.
Source-only here.
