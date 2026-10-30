# The Bell Tower: Youtube Master Island, chapter 57 (youtube-master, contest G342)

Chapters 1-56 run from melody brewing (G25) to the loom pattern (G333) and the hill trails (G338). The sick child is
well again, and the island wants to ring the news.

## Story

The tower holds a few bells, and each rings on its own beat. They all rang together just now. Keeper Oriel asks the
player on which beat they next ring together, so the ringers can pull as one. A beat where some bell is silent is
OFFBEAT, and a later shared beat (like the product of the periods) is LATE; neither earns credit.

## Beats, mechanics and tests (`BellTowerTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The tower | `seeded`: 1-4 bells with periods 1-9 | `seededTowerIsDeterministic` |
| Together | `together()`: lcm of the periods via Euclid's gcd; equals brute-force beat counting (30 seeds) | `togetherMatchesBruteForce` |
| The product is a trap | bells 4, 6, 9 meet at 36, not 216 (LATE) | `productIsLate` |
| Offbeat | `name` at beat 12 misses the 9-beat bell: OFFBEAT, no credit | `offbeatEarnsNoCredit` |
| Tower rules | `name`: DUPLICATE, IGNORED (blank id or beat 0) | `guards` |
| Quest `q_bell_tower` | colony `QuestProgress`: listen bells x1, name beat x1 (retries allowed), talk keeper_oriel | `questOffbeatThenTogetherThenKeeper` |

## Keeper Oriel's lines (`KeeperBellLines`)

- Greeting: "3 bells, and each rings on its own beat. They all rang together just now. On which beat do they next ring
  together?"
- Offbeat: "On beat 12 not every bell rings."
- Late: "They do ring together on beat 216, but sooner, on beat 36."
- Quest done: "Right on the beat. Pull the ropes!"
- After: "The bells ring as one. The whole island hears."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A stone bell tower with three or four bells on ropes, swinging on their own beats and ringing together. Source-only
here.
