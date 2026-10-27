# The Water Channels: Youtube Master Island, chapter 44 (youtube-master, contest G282)

Chapters 1-43 run from melody brewing (G25) to the boatyard (G275) and the low tide walk (G278). Back from the far
shore with pitch, the player finds the village cistern low.

## Story

The spring sits at the top of the hill. Stone channels of different widths run one way between basins down to the
village cistern. Keeper Oriel wants the sluice opened to the most water the channels can carry to the cistern and not
a bucket more. The player traces the channels and sets the sluice. The exact flow is right; more overflows onto the
fields and less leaves the village thirsty. Neither earns credit.

## Beats, mechanics and tests (`WaterChannelsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The hillside | `seeded`: 3-7 basins, one-way channels 1-9 wide | `seededHillIsDeterministic` |
| The most water | `most()`: maximum flow by Edmonds-Karp; equals the brute-force smallest cut over every split (30 seeds) | `mostMatchesBruteForceCut` |
| The spring is a trap | 5 buckets leave the spring, but only 4 reach the cistern | `springOutputIsNotTheAnswer` |
| Overflow | more than the maximum flow: `open` is OVERFLOW, no credit | `overflowEarnsNoCredit` |
| Sluice rules | `open`: SHORT, DUPLICATE, IGNORED | `guards` |
| Quest `q_water_channels` | colony `QuestProgress`: trace channels x1, open right x1 (retries allowed), talk keeper_oriel | `questShortThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperChannelLines`)

- Greeting: "4 basins down the hill, joined by stone channels of different widths. Open the sluice to the most water
  the channels can carry to the cistern, and not a bucket more."
- Overflow: "5 buckets an hour? The channels will spill over the fields."
- Short: "3 buckets an hour is safe, but the channels can carry 4. The village is thirsty."
- Quest done: "Full channels, and not a drop spilled. The cistern will fill by evening."
- After: "Listen to the water running down the hill."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter. The
spring echoes the purified water of chapter 2 (G33).

## Editor later (UNREAL-QUEUE)

A hillside of stone basins and channels with water planes that fill to each channel's flow, a spring sluice wheel and
the village cistern. Source-only here.
