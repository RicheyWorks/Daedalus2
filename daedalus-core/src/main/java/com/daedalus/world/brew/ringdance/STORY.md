# The Ring Dance: Youtube Master Island, chapter 80 (youtube-master, contest G429)

Chapters 1-79 run from melody brewing (G25) to the driftwood cuts (G424) and the gossip circles (G427). The news has
gone round, and everyone is coming to the festival dance.

## Story

Dancers stand in a ring, each wearing a shell crown or a feather crown. Every dancer holds one ribbon with one
partner in the other crown, and no two ribbons may cross. Keeper Oriel asks how many ways the ring can pair up, so
there is a new dance each night. Counting every non-crossing pairing (the plain Catalan number) is a trap, since it
ignores the crowns. A WRONG count or a bad pick earns no credit, and a ring that cannot pair up at all has NO_WAY.

## Beats, mechanics and tests (`RingDanceTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The ring | `seeded`: 2-10 dancers, S or F crowns | `seededRingIsDeterministic` |
| Pairings | `ways()`: Catalan interval recurrence (dancer i pairs with k; inside and outside counted apart); equals brute force over every mixed pairing with a crossing check (30 seeds) | `waysMatchBruteForce` |
| Plain Catalan is a trap | SSFSFF: 5 pairings ignoring crowns, only 2 mixed | `plainCatalanIsATrap` |
| Wrong, no way | `count` WRONG, MALFORMED, NO_WAY (SSSSFF), no credit | `wrongAndNoWayEarnNoCredit` |
| Dance rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_ring_dance` | colony `QuestProgress`: form ring x1, count pairings x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperRingDance`)

- Greeting: "6 dancers in a ring, crowns SSFSFF. Each holds a ribbon with one partner in the other crown, and no
  ribbons may cross. How many ways can they pair up?"
- Wrong: "Not 5. Count the ways again."
- No way: "However they try, some ribbon crosses or joins two of the same crown."
- Quest done: "That many dances! We'll try one each night of the festival."
- After: "The ribbons swirl and never tangle."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A ring of dancers in shell and feather crowns holding coloured ribbons on the dancing ground. Source-only here.
