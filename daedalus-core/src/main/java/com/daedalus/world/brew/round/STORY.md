# The Harbour Round: Youtube Master Island, chapter 13 (youtube-master, contest G139)

Chapters 1-12 run from melody brewing (G25) to the song school (G116) and the graduation concert (G131). After the
concert, the children want to play the harbour.

## Story

An ark is due in from the far islands, carrying the children's families. Fisher Dov says the old ark crews
greeted every landing with a round: one voice starts the song, the next comes in a few beats behind, a third or a
fifth up, then another. When the voices fit, the harbour rings and even the gulls go quiet. When they rub, the
gulls answer back. The children rehearse on the green, choosing for each voice when it comes in and at what
interval. Some songs round beautifully; the duduk lament never does. When the ark comes round the point, they sing
a three-voice round from the jetty, and the far-island children on deck sing it back.

## Beats, mechanics and tests (`HarbourRoundTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Voices fit or rub, beat by beat | `harmony` = consonant pairs (interval class 0/3/4/5/7/8/9) over all pairs across one pass; `grade` sweet at 0.75 or better, fair at 0.5 or better, sour below; `legal` entries (delay 1..length-1, all different; interval unison, 3rd, 4th, 5th or 6th) | `harmonyCountsConsonantPairsBeatByBeat` |
| Dov knows the best round; some songs won't round | `best(song, voices)`: exact search, checked against brute force; 11 of the 12 ark songs round sweetly with three voices, the duduk lament tops out at fair | `solverIsExactAndSomeSongsWontRound` |
| Rules on the green | `rehearse` / `sing` guards: UNKNOWN_SONG, NOT_KNOWN, TOO_FEW_VOICES (2 to rehearse, 3 at the harbour), TOO_MANY_VOICES (4), BAD_ENTRY | `guards` |
| Quest `q_harbour_round` | colony `QuestProgress`: rehearse round x3, a sweet harbour round x1 (fair does not count), talk dov | `questRehearseThenASweetHarbourRoundThenDov` |
| The graduates' songs | `fromSchool`: what the G116 graduates know (record thirteen has no fixed notes); every seed tested has a sweet round | `songSchoolGraduatesKnowASweetRound` |

## Fisher Dov's lines (`DovRoundLines`)

- Greeting: "A round for the ark? One starts, the next comes in a few beats behind, a third or a fifth up. Get it
  wrong and the gulls join in."
- Rehearsing: "2 more goes on the green before the ark's due."
- Fair: "Close. Some of it rubbed. Try another entry."
- Sour: "The gulls are louder than you. Different beat, different interval."
- Ready: "Ark's on the horizon. Three voices at least, and make it sweet."
- Quest done: "The far-island kids on that ark sang it back to you. First time I've heard two islands in one song."
- After: "Every ark gets a round now. The gulls have learned to wait."

## Editor later (UNREAL-QUEUE)

Harbour jetty at the ark dock, a voice-entry staff UI (one row per voice: entry beat, interval, live clash marks),
G116 children singing through the G33 record player, a gull flock that grows louder on clashes, and an arriving ark
whose deck children echo a sweet round. Source-only here.
