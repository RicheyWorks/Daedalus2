# The Song School: Youtube Master Island, chapter 11 (youtube-master, contest G116)

Chapters 1-10: melody brewing (G25), mended records and springs (G33), the record hunt (G46), choir stones (G53),
the first week home (G62), the record exchange (G66), the root cellar (G73), the homecoming supper (G85), the
thirteenth song (G94) and letters by ark (G97). Chapter 11 is what the far islands write back for.

## Story

The replies from the far islands all ask the same thing: send us the songs. Instead the islands send their
children, one from each, and Old Wick opens a schoolroom in the homestead loft. Each child is set four of the
thirteen songs (the twelve ark records and the island's own). A song taught once slips away, so Wick keeps a
shelf of cards in five boxes: a card comes back for review after a day, then two, four, eight, sixteen. Remember
it and the card moves up; forget it and it starts again from the first box. Review late and the child is more
likely to have lost it. Wick only has six lessons in him a day, so the player plans who to see. A song that makes
the top box is learned for good. When three children can sing all their songs without a record, Wick says the arks
are back in them.

## Beats, mechanics and tests (`SongSchoolTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Thirteen songs; one child from each far island (G97), seeded aptitude; four songs each | `thirteenSongs` (found tunes + G94 `ThirteenthSong.RECORD`), `fromFarIslands`, seeded `songsFor` | `thirteenSongsAndAChildFromEachFarIsland` |
| Leitner shelf: boxes 1-5, reviews after 1/2/4/8/16 days; remembered moves up, forgotten goes to box 1; the top box is learned | `introduce`, `review`, `Card.due`, `TOP_BOX` retires the card | `leitnerBoxesClimbOnTimeAndAMissGoesBackToBoxOne` |
| Late reviews are less likely to stick | `recallChance` = aptitude - 0.10 per overdue day; `dueToday` most overdue first | `lateReviewsAreLessLikelyToStick` |
| Six lessons a day | `LESSONS_PER_DAY`, `NO_LESSONS_LEFT`, guards | `sixLessonsADayAndGuards` |
| Quest `q_song_school`: start four songs, graduate three children, then Old Wick | PORT09-twin `colony.QuestProgress` (introduce card x4, graduate pupil x3, talk old_wick); a simple lesson plan graduates three in every tested seed | `questIntroduceGraduateThreeThenWick` |

## Old Wick's lines (`WickSchoolLines`)

- Greeting: "Children from every far island, and not one of them knows a seed-song. Teach them a tune, then come
  back to it before it slips. I've six lessons in me a day."
- Starting: "2 more songs to start them on."
- Shelf: "3 pupils still to see through. Review what's due; the late ones forget."
- Quest done: "Three of them sing all their songs without a record. That's how it was on the arks. They'll teach the
  next ones."
- After: "School's in every morning. Bring the little ones."

## Editor later (UNREAL-QUEUE)

Schoolroom in the homestead loft, a five-box card shelf UI (cards by pupil, due day, recall chance), the G33 record
player for teaching, four child NPCs. Source-only here.
