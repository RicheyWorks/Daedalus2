# The Beach Mats: Youtube Master Island, chapter 58 (youtube-master, contest G348)

Chapters 1-57 run from melody brewing (G25) to the hill trails (G338) and the bell tower (G342). The bells rang for a
big catch, and the fish must dry.

## Story

The fishers lay drying mats along the beach, and some lie over each other. Keeper Oriel asks how many paces of sand
the mats cover, so the salt can be measured out. Adding up the mat lengths counts the overlaps twice; any MISCOUNT
earns no credit.

## Beats, mechanics and tests (`BeachMatsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The beach | `seeded`: 0-8 mats within 0-20 paces, 1-6 long | `seededBeachIsDeterministic` |
| The cover | `merged()` by sort and sweep; spans disjoint and covering exactly the brute-force paces (30 seeds) | `mergedMatchesBruteForce` |
| Adding is a trap | mats 0-4, 2-6, 6-8, 10-12 add to 12 but cover 10; touching mats join | `addingLengthsOvercounts` |
| Miscount | `measure` with a wrong count is MISCOUNT, no credit | `miscountEarnsNoCredit` |
| Beach rules | `measure`: DUPLICATE, IGNORED (blank id or negative); no mats covers 0 | `guards` |
| Quest `q_beach_mats` | colony `QuestProgress`: lay mats x1, measure cover x1 (retries allowed), talk keeper_oriel | `questMiscountThenCoveredThenKeeper` |

## Keeper Oriel's lines (`KeeperMatLines`)

- Greeting: "4 drying mats laid along the beach, some over each other. How many paces of sand do they cover?"
- Miscount: "You said 12. The mats cover 10 paces."
- Quest done: "That's the cover. Spread the fish to dry."
- After: "The fish are drying in the sun."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Woven drying mats overlapping on the sand, split fish laid out, and a pacing stick. Source-only here.
