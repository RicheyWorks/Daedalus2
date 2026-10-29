# The Night Watch: Youtube Master Island, chapter 19 (youtube-master, contest G186)

Chapters 1-18 run from melody brewing (G25) to the signal fires (G174) and the keepsake chests (G181). The chests
are roped down and the boats are out past the jetty.

## Story

The first night at sea, Keeper Oriel chalks a rota board by the mast: dusk to dawn, hour by hour. Somebody has to be
awake for every hour of it. Each sailor offers one stretch they can manage. The player wakes sailors onto the rota
and sends them back to bed, then calls the night. If every hour was watched and nobody was woken who didn't need to
be, the night is warm; if more were woken than needed, the boat is weary in the morning.

## Beats, mechanics and tests (`NightWatchTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The crew offers | `seeded`: an 8-12 hour night, a covering chain of stretches plus 3-5 overlapping extras, shuffled | `seededCrewCoversTheNightAndIsDeterministic` |
| The longest isn't always best | long (2-8) is left out; dusk (0-5) + dawn (5-10) cover the night with two | `theLongestStretchIsNotAlwaysInTheBestRota` |
| The fewest woken | `rota()`: greedy interval cover, from the first unwatched hour take the furthest reach; equals brute force over every subset (20 seeds) | `fewestMatchesBruteForce` |
| Shifts that touch | dusk 0-5 and dawn 5-10 touch at hour 5: covered, no gap | `touchingEndpointsCountAsCovered` |
| Nobody offered an hour | `callNight` returns NO_COVER with no quest credit when the offers can never cover the night | `anUncoverableNightIsNoCoverWithNoCredit` |
| Rota rules | `wake` / `sendToBed` / `callNight`: UNKNOWN, ALREADY_WOKEN, NOT_WOKEN, GAPS, DUPLICATE, IGNORED | `guards` |
| Quest `q_night_watch` | colony `QuestProgress`: wake sailor x3, night warm x1 (WEARY can be fixed), talk keeper_oriel | `questWearyNightThenWarmThenKeeper` |

## Keeper Oriel's lines (`KeeperWatchLines`)

- Greeting: "Somebody stays awake from dusk to dawn, every hour of it. Wake as few as you can; they'll need their
  sleep tomorrow."
- Rota: "1 on the rota. Hour 0 has nobody yet."
- Ready: "Every hour's watched. Call the night."
- Weary: "The night was kept, but you woke 3 where 2 would do. Let someone sleep."
- No cover: "Nobody offered hour 2. We'll take turns at the tiller and say no more about it."
- Quest done: "Watched all night, and most of the boat slept through it. That's seamanship."
- After: "The rota's chalked for every night now."

## Editor later (UNREAL-QUEUE)

A chalk rota board by the mast (hours across, sailors' stretches as chalk bars), deck lanterns that light for each
watched hour, sleeping and waking sailor poses, and a dawn moment. Source-only here.
