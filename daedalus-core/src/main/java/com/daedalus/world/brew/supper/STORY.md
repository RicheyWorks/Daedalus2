# The Homecoming Supper: Youtube Master Island, chapter 8 (youtube-master, contest G85)

Chapters 1-7: melody brewing (G25), mended records and clean springs (G33), the record hunt (G46), choir stones
that hold the bridges (G53), the first week home (G62), the record exchange (G66) and the root cellar that got the
homestead through the Long Dark (G73). Chapter 8 brings everyone to one table.

## Story

The light is back after the Long Dark, and Keeper Oriel says it's time: invite every fragment. Nine guests come
across the mended bridges: Oriel, Archivist Tamsin, Mason Hale, Old Wick, Pell, Quarry Ida, Hen-wife Mora, Fisher
Dov and Aunt Brine. Some of them haven't spoken since the sky fell, and sitting them side by side would sour the
night; some are old friends who light up beside each other. Each remembers a dish they used to cook on the arks
and hums a tune from the old records. Seat them well, cook each a meal from the larder, and play three mended
records, one per course. When every guest is content, Oriel tells you the island is home.

## Beats, mechanics and tests (`HomecomingSupperTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Nine guests, one from every chapter, each with a remembered dish and tune | `Guest.island()` (ids = earlier chapters' talk targets), seeded `favouriteDish` (G62 `Larder.RECIPES`) / `favouriteTune` (G33 records) | `nineGuestsFromEveryChapterWithSeededTastes` |
| Feuding guests must not sit side by side; there is always a way | seeded `feuds` / `friends`, `feudFreeSeating` backtracking (constructor reseeds until solvable), `seat` refuses `FEUD`, `hint` | `aFeudFreeSeatingAlwaysExistsAndFeudsAreRefused` |
| Each guest gets one cooked meal; three records, each once, all mended | `serve` (G62 `Larder.cooked` items from the plot store), `play` (G33 `SeedSongSpring.isRestored`) | `servingAndPlayingGuards` |
| A friend beside you +2, your dish +3 (any meal +1, none -2), your tune +2 | `contentment`, `neighbours` (first and last guest sit beside the host) | `contentmentAddsFriendsMealAndTune` |
| Quest `q_homecoming_supper`: seat the table, serve nine, play three courses, then Oriel, who needs a warm supper | PORT09-twin `colony.QuestProgress` (seat table x1, serve guest x9, play course x3, talk keeper_oriel x1), `warm`, `discontent` | `questSeatServePlayThenOrielNeedsAWarmSupper` |

## Keeper Oriel's lines (`SupperLines`)

- Greeting: "Everyone's coming, every fragment. Mind where you seat them: some of them haven't spoken since the sky
  fell."
- Serving: "9 plates still to go. Ask them what they used to cook on the arks."
- Courses: "Put on a record. 3 courses left; play the tunes they hum."
- Not warm yet: "1 guest still looking at their plate. A friend beside them, the dish they love, or their own tune
  would do it."
- Quest done: "Listen to them. Nine fragments at one table, singing your records. That's the island home."
- After: "Leave the dishes. Sit, the next song's starting."

## Editor later (UNREAL-QUEUE)

Round table with a host seat and nine guest seats; a seating UI that shows feud/friend hints; plates from the YTM
food props; the G33 record player for the courses; guest mood icons from `contentment`. Source-only here.
