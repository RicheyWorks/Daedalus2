# The Two Buckets: Youtube Master Island, chapter 48 (youtube-master, contest G301)

Chapters 1-47 run from melody brewing (G25) to the hut walkways (G293) and the name stones (G297). The smokehouse
fish (G272) need a pickle, and the pickle needs an exact measure of brine.

## Story

There are only two unmarked buckets by the brine trough. Keeper Oriel wants exactly the right amount for the pickle
crock. The player can fill a bucket, empty it, or pour one into the other until it is empty or the other is full.
Ending with the exact amount in either bucket in the fewest moves is right; more moves earn no credit, and a move
list that misses the amount earns none. Some targets cannot be measured at all.

## Beats, mechanics and tests (`TwoBucketsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The buckets | `seeded`: buckets of 1-7, a target that fits; 2 and 4 never make 3 | `seededBucketsAreDeterministic` |
| The fewest moves | `fewest()`: breadth-first search over bucket states; equals brute-force relaxation over every state (30 seeds) | `fewestMatchesBruteForce` |
| The small bucket is a trap | 3 and 5 for 4: starting with the 3 takes 8 moves, the 5 takes 6 | `startingWithTheSmallBucketIsLonger` |
| Missed | neither bucket on the target: `measure` is MISSED, no credit | `missedMeasureEarnsNoCredit` |
| Trough rules | `measure`: NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_two_buckets` | colony `QuestProgress`: fetch buckets x1, measure well x1 (LONG can be redone), talk keeper_oriel | `questLongThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperBucketLines`)

- Greeting: "Two unmarked buckets, 3 and 5, and the pickle wants exactly 4 of brine. Fill, empty and pour between
  them, in as few moves as you can."
- Missed: "Neither bucket holds 4. The pickle will be too salty or too weak."
- Long: "Right amount, but 8 moves. It can be done in 6."
- Quest done: "Exactly right, and quick about it. Into the crock it goes."
- After: "The pickle crock is sealed."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A brine trough with two buckets whose water levels follow each move, and a pickle crock. Source-only here.
