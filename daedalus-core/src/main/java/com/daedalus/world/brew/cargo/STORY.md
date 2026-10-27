# The Cargo Weights: Youtube Master Island, chapter 102 (youtube-master, contest G486)

Chapters 1-101 run from melody brewing (G25) to the shell necklace (G482) and the jar shelves (G484). The trading boat
takes on cargo, and the harbour scale only reads whole loads.

## Story

Crates of different weights wait on the quay. The boat can take any non-empty selection of them. Keeper Oriel asks
how many different total loads are possible. Counting the selections is the trap, since different selections can
weigh the same. A WRONG count earns no credit, and an EMPTY quay has no load to weigh.

## Beats, mechanics and tests (`CargoWeightsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The quay | `seeded`: 0-7 crates weighing 1-6 | `seededIsDeterministic` |
| Different loads | `loads()`: bitset subset-sum DP (reach = reach OR reach shifted by each weight), counting set bits above 0; equals brute force over every selection with a set of totals (30 seeds) | `answerMatchesBruteForce` |
| Counting selections is a trap | crates 1 2 3: 6 loads (1-6), 7 selections | `trap` |
| Wrong, empty | `count` WRONG, MALFORMED, EMPTY (no crates), no credit | `wrongAndSpecialEarnNoCredit` |
| Quay rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_cargo_weights` | colony `QuestProgress`: read crates x1, count loads x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperCargoWeights`)

- Greeting: "The crates on the quay weigh [1, 2, 3]. The boat takes any of them, at least one. How many different
  loads could the scale read?"
- Wrong: "Not 7. Different crates can add up to the same load."
- Empty: "The quay is empty. No load to weigh."
- Quest done: "Every load counted! The trader can't fool us now."
- After: "The scale creaks, and the boat sails heavy."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A stone quay with wooden crates of different sizes, a hanging harbour scale and a small trading boat. Source-only here.
