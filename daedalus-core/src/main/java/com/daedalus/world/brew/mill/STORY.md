# The Grain Mill: Youtube Master Island, chapter 36 (youtube-master, contest G254)

Chapters 1-35 run from melody brewing (G25) to the island post (G245) and the bakehouse (G248). The bakehouse needs
flour for the next batch, so the children climb to the windmill.

## Story

The millstone grinds two sacks of grain into one sack of flour at a time, and every pound in the pair is work for the
sails. Keeper Oriel asks the player to grind every sack into one with the least work. The least work possible sacks
well; more work is heavy and earns nothing.

## Beats, mechanics and tests (`GrainMillTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The store | `seeded`: 2-7 sacks weighing 1-20 | `seededStoreIsDeterministic` |
| The least work | `least()`: Huffman greedy (grind the two lightest); equals brute force over every merge order (30 seeds) | `leastMatchesBruteForce` |
| Heavy first is a trap | sacks 1, 2, 3, 10: grinding 10 early costs more | `grindingTheHeavySackEarlyCostsMore` |
| Heavy work | a worse order: `sack` is HEAVY, no credit; UNFINISHED while sacks remain | `heavyEarnsNoCredit` |
| Mill rules | `grind`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_grain_mill` | colony `QuestProgress`: grind pair x1, sack well x1 (HEAVY can be retried with `restart`), talk keeper_oriel | `questHeavyThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperMillLines`)

- Greeting: "4 sacks of grain. The stone grinds two at a time into one, and every pound in the pair is work. Grind
  them all into one with the least work."
- Grinding: "3 sacks left, 3 work so far."
- Heavy: "One sack, but 44 work where 25 would do. The sails are tired."
- Quest done: "One sack of flour, and the mill barely broke a sweat."
- After: "The sails are furled. Flour on your nose."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A windmill with turning sails, a millstone, grain sacks that merge on the floor and a flour sack at the end.
Source-only here.
