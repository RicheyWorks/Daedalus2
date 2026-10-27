# The Kin Tree: Youtube Master Island, chapter 94 (youtube-master, contest G472)

Chapters 1-93 run from melody brewing (G25) to the marsh path (G470) and the beacon fence (G471). Winter evenings are
for stories, and Keeper Oriel keeps the island's kin tree.

## Story

Every islander but the founder has one parent on the kin tree. Keeper Oriel names two islanders and asks how many
steps apart they are on the tree. Walking both of them all the way up to the founder is the trap: the path only
needs to climb to the nearest shared ancestor. A WRONG count earns no credit, and naming the SAME islander twice
leaves nothing to count.

## Beats, mechanics and tests (`KinTreeTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The tree | `seeded`: 1-8 islanders, each parent earlier on the tree, two names | `seededIsDeterministic` |
| Steps apart | `steps()`: lowest common ancestor by binary lifting (jump tables of 2^k ancestors), then depth(a) + depth(b) - 2 depth(lca); equals brute force by breadth-first search on the tree (30 seeds) | `answerMatchesBruteForce` |
| Via the founder is a trap | parents -1 0 0 1 1 2, islanders 3 and 4: 2 steps (siblings), 4 via the founder | `trap` |
| Wrong, same | `count` WRONG, MALFORMED, SAME (one islander twice), no credit | `wrongAndSpecialEarnNoCredit` |
| Hearth rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_kin_tree` | colony `QuestProgress`: read tree x1, count steps x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperKinTree`)

- Greeting: "The kin tree lists each islander's parent: [-1, 0, 0, 1, 1, 2]. How many steps apart are islanders 3
  and 4?"
- Wrong: "Not 4. Climb only as far as the nearest shared ancestor."
- Same: "That's the same islander twice. No steps at all."
- Quest done: "Right! You read the tree like an elder."
- After: "Branch by branch, the island remembers its own."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A hearth room with a kin tree carved into a wooden wall panel, names on little brass tags. Source-only here.
