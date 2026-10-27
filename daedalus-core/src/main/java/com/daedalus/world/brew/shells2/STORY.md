# The Message Shells: Youtube Master Island, chapter 53 (youtube-master, contest G323)

Chapters 1-52 run from melody brewing (G25) to the hauling days (G316) and the stream forks (G319). Spring news must
reach every islander, and the island passes news by message shell.

## Story

Each islander always passes the message shell to the same neighbour. Started from the player, the shell is passed
along until it comes round to someone who held it before, and from then on it goes round the same loop for ever.
Keeper Oriel asks how many passes it takes to reach the loop and how long the loop is, to know who will never hear
the message. Naming both right earns credit; a wrong reading, even half right, earns none.

## Beats, mechanics and tests (`MessageShellsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The island | `seeded`: 1-12 islanders passing at random; one islander keeps the shell (loop 1) | `seededIslandIsDeterministic` |
| Tail and loop | `tail()`, `loop()`: Floyd's tortoise and hare; equal a brute-force simulation with a first-held table (30 seeds) | `tailAndLoopMatchBruteForce` |
| The loop is not everyone | 1, 2, 3, 4, 2: 2 passes in, a loop of 3 among 5 | `loopIsNotEveryone` |
| Wrong reading | `read` is WRONG, no credit | `wrongReadingEarnsNoCredit` |
| Shell rules | `read`: half right is WRONG; DUPLICATE, IGNORED | `guards` |
| Quest `q_message_shells` | colony `QuestProgress`: pass shell x1, read right x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperShellLines`)

- Greeting: "5 islanders, and each always passes the message shell to the same neighbour. Start it with yourself:
  how many passes before it starts going round in a loop, and how long is the loop?"
- Wrong: "0 passes in and a loop of 5? Watch the shell again."
- Quest done: "Right. Now we know who will never hear the message."
- After: "The shell is still going round."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Islanders standing about the village green, a conch shell that arcs from hand to hand, and a glowing ring once it
loops. Source-only here.
