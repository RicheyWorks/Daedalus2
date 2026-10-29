# The Jar Shelves: Youtube Master Island, chapter 101 (youtube-master, contest G484)

Chapters 1-100 run from melody brewing (G25) to the chant words (G481) and the shell necklace (G482). After the
festival, the pantry jars came back to the shelf in a jumble.

## Story

Each pantry jar has a number and a place on the shelf, and the jars are all in the wrong places. Keeper Oriel can swap
any two jars at a time and asks for the fewest swaps to put every jar home. Counting the misplaced jars is the trap,
since one swap can send two jars home at once and a ring of jars needs one swap fewer than its size. A WRONG count earns
no credit, and a shelf already SORTED needs no swaps.

## Beats, mechanics and tests (`JarShelvesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The shelf | `seeded`: 1-6 jars in a random order | `seededIsDeterministic` |
| Fewest swaps | `swaps()`: split the order into cycles; swaps = jars minus cycles; equals brute force by breadth-first search over every swap (30 seeds) | `answerMatchesBruteForce` |
| Counting misplaced is a trap | shelf 1 2 0: 2 swaps, 3 misplaced | `trap` |
| Wrong, sorted | `count` WRONG, MALFORMED, SORTED (shelf in order), no credit | `wrongAndSpecialEarnNoCredit` |
| Pantry rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_jar_shelves` | colony `QuestProgress`: read shelf x1, count swaps x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperJarShelves`)

- Greeting: "The jars sit in the order [1, 2, 0], and jar k belongs in place k. Swapping two jars at a time, what is
  the fewest swaps?"
- Wrong: "Not 3. Follow each ring of jars: it needs one swap fewer than its size."
- Sorted: "Every jar is already home. No swaps needed."
- Quest done: "Fewest swaps! The pantry is tidy again."
- After: "Jar by jar, the shelf remembers its order."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A pantry shelf of numbered clay jars, a few out of place, with chalk numbers on the shelf edge. Source-only here.
