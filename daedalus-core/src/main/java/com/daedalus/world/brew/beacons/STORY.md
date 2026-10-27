# The Beacon Fence: Youtube Master Island, chapter 93 (youtube-master, contest G471)

Chapters 1-92 run from melody brewing (G25) to the chore days (G468) and the marsh path (G470). A storm is coming,
and the beacon posts on the headland need a fence around them.

## Story

Beacon posts stand on the headland. The storm fence is one tight loop of rope that must enclose every post, and it
only bends where it touches a post. Keeper Oriel asks how many posts the rope bends at. Counting every post is the
trap, since posts inside the loop, or along a straight stretch, never bend it. A WRONG count earns no credit, and posts
standing in a single straight line are too FLAT to fence.

## Beats, mechanics and tests (`BeaconFenceTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The headland | `seeded`: 3-7 distinct posts on a 5x5 grid | `seededIsDeterministic` |
| Corner posts | `corners()`: Andrew's monotone chain convex hull, dropping posts on a straight stretch; equals brute force (a post is a corner unless it lies in a triangle or on a segment of other posts, 30 seeds) | `answerMatchesBruteForce` |
| Every post is a trap | square corners plus a centre post and an edge post: 4 corners, 6 posts | `trap` |
| Wrong, flat | `count` WRONG, MALFORMED, FLAT (three posts in a line), no credit | `wrongAndSpecialEarnNoCredit` |
| Headland rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_beacon_fence` | colony `QuestProgress`: read posts x1, count corners x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperBeaconFence`)

- Greeting: "The beacon posts stand at [[0, 0], [4, 0], [4, 4], [0, 4], [2, 2], [2, 0]]. One tight rope goes around
  them all. How many posts does it bend at?"
- Wrong: "Not 6. Posts inside, or on a straight stretch, don't bend the rope."
- Flat: "The posts stand in one straight line. There's nothing to fence around."
- Quest done: "Every corner found! The fence will hold."
- After: "The rope hums in the wind and the beacons stay lit."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A windy headland with wooden beacon posts and a taut rope fence looping around them. Source-only here.
