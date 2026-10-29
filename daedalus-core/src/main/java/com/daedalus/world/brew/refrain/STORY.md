# The Refrain Count: Youtube Master Island, chapter 84 (youtube-master, contest G443)

Chapters 1-83 run from melody brewing (G25) to the hut floor (G437) and the lucky doors (G440). With the doors
painted, the whole village hauls the new canoe to the water, singing as they pull.

## Story

The work song is a long run of drum beats, and whenever the refrain starts everyone shouts and pulls. Keeper Oriel
asks how many times the refrain starts in the song, overlapping ones included, so the drummers know how many pulls
to call. Counting only copies that don't overlap is a trap. A WRONG count or a bad pick earns no credit, and a
refrain that is NEVER_SUNG in the song cannot be counted.

## Beats, mechanics and tests (`RefrainCountTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The song | `seeded`: a song of 0-24 beats, a refrain of 1-3 beats (a, b, sometimes c); `zFunction("aabcaab")` checked by hand | `seededSongIsDeterministic` |
| Refrain count | `times()`: Z-function of refrain + '\|' + song; equals brute force trying every place (30 seeds) | `timesMatchBruteForce` |
| Skipping overlaps is a trap | aba starts 3 times in abababab, not 2 | `skippingOverlapsIsATrap` |
| Wrong, never sung | `count` WRONG, MALFORMED, NEVER_SUNG (bb in ababab), no credit | `wrongAndNeverSungEarnNoCredit` |
| Drummer rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_refrain_count` | colony `QuestProgress`: hear song x1, count refrains x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperRefrain`)

- Greeting: "The work song goes abababab. How many times does the refrain aba start in it? Count the ones that
  overlap too."
- Wrong: "Not 2. Listen again, beat by beat."
- Never sung: "That refrain is never sung in this song."
- Quest done: "That's how often we all shout! The drummers will know."
- After: "Everyone shouts the refrain right on the beat."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Villagers hauling a new canoe down the beach on rollers, two drummers keeping the beat. Source-only here.
