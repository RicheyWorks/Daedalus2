# The Shell Purse: Youtube Master Island, chapter 88 (youtube-master, contest G460)

Chapters 1-87 run from melody brewing (G25) to the lantern wishes (G448) and the net rack (G456). Market day comes
to the island, and Keeper Oriel wants bread.

## Story

The stall takes shell coins of a few values, as many of each as you like. Keeper Oriel asks how many different
handfuls pay the price exactly. Counting every order the shells could go down is the trap: two shells then one is
the same handful as one then two. A WRONG count earns no credit, and a price that is UNPAYABLE with these shells
leaves nothing to count.

## Beats, mechanics and tests (`ShellPurseTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The purse | `seeded`: 1-3 distinct values 1-5, price 0-10 | `seededIsDeterministic` |
| Handfuls | `ways()`: coin-change counting DP, coins in the outer loop; equals brute force over every count of each shell (30 seeds); `orders()` matches its own brute force and is never smaller | `answerMatchesBruteForce` |
| Orders are a trap | shells 1 and 2, price 4: 3 handfuls, 5 orders | `trap` |
| Wrong, unpayable | `count` WRONG, MALFORMED, UNPAYABLE (shell 2, price 3), no credit | `wrongAndSpecialEarnNoCredit` |
| Stall rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_shell_purse` | colony `QuestProgress`: read coins x1, count ways x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperShellPurse`)

- Greeting: "The stall takes shells worth [1, 2], and the bread costs 4. How many different handfuls pay it exactly?
  Order does not matter."
- Wrong: "Not 5. Two shells and one shell is the same handful whichever goes down first."
- Unpayable: "No handful of these shells pays that price. Nothing to count."
- Quest done: "Every handful counted! The baker is impressed."
- After: "The shells clink and the bread is paid for."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A market stall with a bread basket and a wooden tray of shell coins in two sizes. Source-only here.
