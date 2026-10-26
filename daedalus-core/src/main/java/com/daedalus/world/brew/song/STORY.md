# The Thirteenth Song: Youtube Master Island, chapter 9 (youtube-master, contest G94)

Chapters 1-8: melody brewing (G25), mended records and clean springs (G33), the record hunt (G46), choir stones
(G53), the first week home (G62), the record exchange (G66), the root cellar (G73) and the homecoming supper (G85).
Chapter 9 gives the island a song of its own.

## Story

When the supper plates are cleared, Archivist Tamsin points at the gap on her shelf: twelve records came off the
arks, and the island has never had one of its own. Every guest hums a phrase from the tune they love; ask each for
a verse, one step of melody from their favourite record. The island's song is four or five herbs long, each step
borrowed from a different guest, and like every good ark tune it comes home on the note it started on. Tamsin
knows every ark record by heart and will not accept one of them back in a new key. Brew it once to prove it holds,
and she presses record thirteen.

## Beats, mechanics and tests (`ThirteenthSongTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The island herbs are the twelve notes | `ThirteenthSong.HERBS` = `PitchTable.ISLAND_CANON` order, `herbsFor`, `steps` (G25 `MelodyBrew.step`) | `herbsFollowTheIslandCanon` |
| Each guest's verse is a step from their favourite record (G85) | `offers` (seeded pick from that `FoundTune`'s steps), `ask` | `eachGuestOffersAStepFromTheirFavouriteRecord` |
| With every verse gathered, a song always exists | constructor re-draws until `solve` finds one; `hint` | `withEveryVerseASongAlwaysExists` |
| 4-5 herbs, comes home, never an ark tune even transposed, each step a different verse | `check` (`WRONG_LENGTH`, `UNKNOWN_HERB`, `NO_HOME`, `NOT_NEW` by step pattern, `NOT_OFFERED` by matching) | `theRulesOfTheSong` |
| Quest `q_thirteenth_song`: five verses, compose, brew once, then Tamsin presses record thirteen | PORT09-twin `colony.QuestProgress` (gather verse x5, compose song, brew song, talk archivist_tamsin); `brew` at a G25 `BrewBench` that knows the song; record into `colony.PlotState` | `questGatherComposeBrewThenTamsinPressesRecordThirteen` |
| Record thirteen plays at any bench like an ark record | `song()` is a `FoundTune` learned from `Item_YTM_Record_IslandHome` | `recordThirteenPlaysAtAnyBenchThatHasItLikeAnArkRecord` |

## Archivist Tamsin's lines (`TamsinLines`)

- Greeting: "Twelve records came off the arks. The island has never had one of its own. Ask each of them for a
  verse, a step from the tune they love."
- Gathering: "4 more verses. One step from each guest; no one gives two."
- Compose: "Now put them together: four or five herbs, each step a different verse, and it has to come home. And
  don't hand me a copy of an ark tune in a new key, I'll know."
- Brew: "Brew it once, so we know it holds. Then I'll press it."
- Quest done: "Record thirteen. I've left room on the shelf for it since the hunt. Here's the first pressing."
- After: "Play it at the spring. It's the island's now."

Five verses are enough to try; if those five make no song, ask the others (all nine always do).

## Editor later (UNREAL-QUEUE)

A composing UI on the G33 record player (herb slots, step readout, verse chips per guest), Tamsin's catalogue
shelf with a thirteenth slot, and a Prop_YTM_Record_IslandHome label. Source-only here.
