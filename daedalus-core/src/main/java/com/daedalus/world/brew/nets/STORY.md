# The Net Mending: Youtube Master Island, chapter 31 (youtube-master, contest G235)

Chapters 1-30 run from melody brewing (G25) to the fair winds (G229) and the echo cave (G232). A storm has torn the
island's fishing nets the night before the boats go out.

## Story

In the net loft each mender knows only some of the knots, and each torn net needs its own knot. A mender can work one
net and a net takes one mender. Keeper Oriel asks the player to set menders to nets so as many as possible are mended
by the tide. Mending the most possible mends well; fewer is too few and earns nothing. A mender cannot be put on a net
whose knot they do not know.

## Beats, mechanics and tests (`NetMendingTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The loft | `seeded`: 2-5 menders, 2-5 nets, each knot known with probability 0.4 | `seededLoftIsDeterministic` |
| The most nets | `most()`: maximum bipartite matching by augmenting paths (Kuhn); equals brute force over every assignment (30 seeds) | `mostMatchesBruteForce` |
| The greedy trap | mender 0 knows nets 0 and 1, mender 1 only net 0: giving mender 0 net 0 mends one, the swap mends two | `firstChoiceIsNotAlwaysBest` |
| Wrong knot / too few | `assign` refuses CANT_KNOT; `mend` with fewer than the most is FEW, no credit | `fewEarnsNoCredit` |
| Loft rules | `assign`: TAKEN, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_net_mending` | colony `QuestProgress`: assign net x1, mend well x1, talk keeper_oriel | `questFewThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperNetLines`)

- Greeting: "2 menders, 2 torn nets, and each mender knows only some knots. One net each, and mend as many as we can
  before the tide."
- Wrong knot: "Mender 1 does not know net 1's knot. Pick another."
- Few: "1 nets mended where 2 could be. Shuffle the menders."
- Quest done: "Every net that could be mended is mended. The boats go out at dawn."
- After: "The nets are drying. Off to the fire."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A net loft with torn nets on frames, menders' stools, and a knot board showing who knows which knot. Source-only here.
