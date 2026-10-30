# The Middle Catch: Youtube Master Island, chapter 71 (youtube-master, contest G401)

Chapters 1-70 run from melody brewing (G25) to the mirror chant (G395) and the counting circle (G398). In the
morning the fishers land a fresh catch.

## Story

The fish lie on the table in the order they came out of the net. The cook wants the k-th smallest for the soup.
Keeper Oriel asks how long it is. The k-th fish on the table is a trap; a WRONG length earns no credit.

(The package is `world.brew.catches`, since `catch` is a Java keyword.)

## Beats, mechanics and tests (`MiddleCatchTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The catch | `seeded`: 1-15 fish of length 1-20 and any rank | `seededCatchIsDeterministic` |
| The k-th smallest | `kth()`: quickselect with a Lomuto partition; equals brute-force sorting for every rank (30 seeds) | `kthMatchesBruteForce` |
| Table place is a trap | lengths 7, 2, 9, 4, 4, 1: the 3rd on the table is 9, the 3rd smallest is 4 | `tablePlaceIsATrap` |
| Wrong | `name` a wrong length is WRONG, no credit | `wrongEarnsNoCredit` |
| Table rules | `name`: DUPLICATE, IGNORED | `guards` |
| Quest `q_middle_catch` | colony `QuestProgress`: land catch x1, name fish x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperCatchLines`)

- Greeting: "6 fish on the table. The cook wants the 3rd smallest for the soup. How long is it?"
- Wrong: "You said 9. The 3rd smallest is 4 long."
- Quest done: "That's the fish. Into the pot!"
- After: "The fish soup is simmering."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A fish table on the beach with a row of fish of different lengths, a measuring stick, and the soup pot. Source-only
here.
