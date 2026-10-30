# The Lantern Wishes: Youtube Master Island, chapter 85 (youtube-master, contest G448)

Chapters 1-84 run from melody brewing (G25) to the lucky doors (G440) and the refrain count (G443). The new canoe is
launched, and tonight is the lantern festival.

## Story

Each villager makes a wish with two parts, such as "lantern 1 lit or lantern 3 dark", and goes home happy if either
part comes true. Keeper Oriel asks for a lighting that makes everyone happy. Lighting every lantern is a trap. An
UNHAPPY lighting or a bad pick earns no credit, and if the wishes pull against each other it is IMPOSSIBLE.

## Beats, mechanics and tests (`LanternWishesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The festival | `seeded`: 1-6 lanterns, 0-9 two-part wishes | `seededFestivalIsDeterministic` |
| Can all be happy? | `possible()`: 2-SAT (two implication arrows per wish, Kosaraju groups, no lantern grouped with its opposite); equals brute force over every lighting (30 seeds) | `possibleMatchesBruteForce` |
| All lit is a trap | lighting every lantern leaves "not 2 or not 3" unhappy | `lightingEverythingIsATrap` |
| Unhappy, impossible | `light` UNHAPPY (2 unhappy), MALFORMED, IMPOSSIBLE (lantern 1 lit and dark both wished), no credit | `unhappyAndImpossibleEarnNoCredit` |
| Rack rules | `light`: IGNORED, DUPLICATE | `guards` |
| Quest `q_lantern_wishes` | colony `QuestProgress`: hear wishes x1, light lanterns x1 (retries allowed), talk keeper_oriel | `questUnhappyThenGrantedThenKeeper` |

## Keeper Oriel's lines (`KeeperLanternWishes`)

- Greeting: "3 lanterns and 4 wishes. Each wish has two parts, like 'lantern 1 lit or lantern 3 dark', and a villager
  is happy if either part comes true. Light them so everyone is happy."
- Unhappy: "Unhappy villagers with that lighting: 1."
- Impossible: "These wishes pull against each other. No lighting makes everyone happy."
- Quest done: "Every wish granted! Light them up."
- After: "The lanterns glow and every villager smiles."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A lantern rack on the shore with paper lanterns, some lit and some dark, and villagers holding wish slips. Source-only.
