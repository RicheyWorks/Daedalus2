# The Lamp Posts: Youtube Master Island, chapter 54 (youtube-master, contest G328)

Chapters 1-53 run from melody brewing (G25) to the stream forks (G319) and the message shells (G323). The news has
gone round: the spring fair is tonight.

## Story

Every family hangs a lamp along a run of fence posts by the green, and each lamp adds its glow to every post in its
run. The fiddler plays by the brightest post. Keeper Oriel asks the player to find it. A post with the most light is
right (ties are fine); a dimmer post earns no credit. The post under the most lamps is not always the brightest.

## Beats, mechanics and tests (`LampPostsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The fence | `seeded`: 1-15 posts, 0-8 lamps of glow 1-6 | `seededFenceIsDeterministic` |
| The light | `light(p)`: difference array and prefix sum; every post and `brightest()` equal brute force (30 seeds) | `lightMatchesBruteForce` |
| Most lamps is a trap | post 1 under three faint lamps has 3; posts 3-4 under two have 6 | `mostLampsIsNotBrightest` |
| Dim | `point` at a dimmer post is DIM, no credit | `dimPostEarnsNoCredit` |
| Fence rules | `point`: NOT_THERE, DUPLICATE, IGNORED; ties are BRIGHT | `guards` |
| Quest `q_lamp_posts` | colony `QuestProgress`: hang lamps x1, point bright x1 (retries allowed), talk keeper_oriel | `questDimThenBrightThenKeeper` |

## Keeper Oriel's lines (`KeeperLampLines`)

- Greeting: "6 fence posts, and every family hangs a lamp along a run of them. The fiddler plays by the brightest
  post. Which post is it?"
- Dim: "Post 1 has 3 light. Another post has 6."
- Quest done: "That's the spot. I'll fetch the fiddler."
- After: "The fair is lit. Listen to the fiddle."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A fence of posts along the green with lamp strings over runs of posts, light that pools at each post, and a fiddler.
Source-only here.
