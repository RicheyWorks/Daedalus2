# The Net Rack: Youtube Master Island, chapter 87 (youtube-master, contest G456)

Chapters 1-86 run from melody brewing (G25) to the lantern wishes (G448) and the flag shells (G453). The fishing
season is back, and Keeper Oriel's knees ache from walking to the net shed.

## Story

The jetty rack holds only a few nets. The fishers ask for nets in a known order, and any net not on the rack means a
trip to the shed, carrying one net back if the rack is full. Keeper Oriel asks for the fewest trips. Sending back the
net unused for longest is a trap, since that can be the very net wanted next; the trick is to send back the one not
wanted for longest. A WRONG count or a bad pick earns no credit, and a rack ROOMY enough for every net leaves no
choice to make.

## Beats, mechanics and tests (`NetRackTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The rack | `seeded`: 1-3 slots, 0-10 asks for nets 0-4 | `seededRackIsDeterministic` |
| Fewest trips | `fewest()`: Belady's rule (send back the net needed furthest ahead); equals brute force over every send-back choice (30 seeds); `lruTrips()` never beats it | `fewestMatchesBruteForce` |
| Unused longest is a trap | 2 slots, asks 0 1 2 0 1 2: fewest 4, LRU 6 | `unusedLongestIsATrap` |
| Wrong, roomy | `count` WRONG, MALFORMED, ROOMY (3 slots for 3 nets), no credit | `wrongAndRoomyEarnNoCredit` |
| Jetty rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_net_rack` | colony `QuestProgress`: read asks x1, count trips x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperNetRack`)

- Greeting: "The rack holds 2 nets, and today the fishers ask for [0, 1, 2, 0, 1, 2] in that order. Any net not on
  the rack is a trip to the shed. What is the fewest trips?"
- Wrong: "Not 6. Send back the net that won't be wanted for longest."
- Roomy: "The rack holds every net they want. No choices to make."
- Quest done: "Fewest trips! My old legs thank you."
- After: "The nets come and go and the shed path stays quiet."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A small net rack on the jetty with two hanging nets, a path to a net shed full of coiled nets. Source-only here.
