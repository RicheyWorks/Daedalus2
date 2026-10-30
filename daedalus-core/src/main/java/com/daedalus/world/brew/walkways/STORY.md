# The Hut Walkways: Youtube Master Island, chapter 46 (youtube-master, contest G293)

Chapters 1-45 run from melody brewing (G25) to the water channels (G282) and the well pipes (G289). With water piped
through the village, the marsh families on their stilt huts ask to be joined in too.

## Story

Stilt huts stand over the marsh, and a plank walkway between any two huts costs some planks. Keeper Oriel wants
walkways so anyone can walk from any hut to any other, with as few planks as possible. The player surveys the marsh
and lays walkways. The cheapest network is right; a dearer one earns no credit, and one that leaves a hut cut off is
broken and earns none either.

## Beats, mechanics and tests (`HutWalkwaysTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The marsh | `seeded`: 3-6 huts, walkways of 1-9 planks | `seededMarshIsDeterministic` |
| The cheapest walkways | `cheapest()`: minimum spanning tree by Prim; equals brute force over every joining set of n-1 walkways (30 seeds) | `cheapestMatchesBruteForce` |
| Hut to hut is a trap | walking 0-1-2-3 costs 13; a star from hut 0 costs 5 | `hutToHutWalkIsNotCheapest` |
| Broken | a hut cut off: `lay` is BROKEN, no credit | `brokenNetworkEarnsNoCredit` |
| Marsh rules | `lay`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_hut_walkways` | colony `QuestProgress`: survey marsh x1, lay well x1 (DEAR can be relaid), talk keeper_oriel | `questDearThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperWalkwayLines`)

- Greeting: "4 stilt huts over the marsh. Lay plank walkways so anyone can walk from any hut to any other, with as
  few planks as you can."
- Broken: "Somebody's hut is still cut off. They'd have to wade."
- Dear: "That takes 13 planks. Every hut can be joined with 5."
- Quest done: "Every hut joined, and planks to spare. Good work."
- After: "Mind the gaps between the planks."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Stilt huts over a marsh with plank walkways that appear as they are laid, a plank stack that shrinks with each one,
and reeds. Source-only here.
