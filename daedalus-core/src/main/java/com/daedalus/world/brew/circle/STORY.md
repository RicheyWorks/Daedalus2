# The Counting Circle: Youtube Master Island, chapter 70 (youtube-master, contest G398)

Chapters 1-69 run from melody brewing (G25) to the tide gauge (G390) and the mirror chant (G395). After the well
blessing, the children sit round the fire.

## Story

The children play counting-out: starting from child 0, every k-th child in the count steps out and the count goes
on round the circle. The last child left lights the night lantern. Keeper Oriel asks who that will be. Naming any
child who steps out (OUT) earns no credit.

## Beats, mechanics and tests (`CountingCircleTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The circle | `seeded`: 1-15 children, a count of 1-6 | `seededCircleIsDeterministic` |
| Last one left | `survivor()`: the Josephus recurrence; equals a brute-force play-out (30 seeds) | `survivorMatchesBruteForce` |
| Out is not last | 5 children, every 2nd: 1, 3, 0, 4 out, child 2 left; a count of 1 leaves child 4 | `firstOutIsNotLast` |
| Out | `name` a child who steps out is OUT, no credit | `outEarnsNoCredit` |
| Circle rules | `name`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_counting_circle` | colony `QuestProgress`: gather circle x1, name last x1 (retries allowed), talk keeper_oriel | `questOutThenLastThenKeeper` |

## Keeper Oriel's lines (`KeeperCircleLines`)

- Greeting: "5 children round the fire, counting from child 0. Every 2nd count steps out, and the count goes on. Who
  is left last to light the lantern?"
- Out: "Child 4 steps out. Child 2 is left last."
- Quest done: "Child 2 it is. Light the lantern!"
- After: "The lantern is lit. Off to bed."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A ring of children on logs round a fire pit, and a night lantern on a pole. Source-only here.
