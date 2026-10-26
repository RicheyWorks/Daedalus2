# The Graduation Concert: Youtube Master Island, chapter 12 (youtube-master, contest G131)

Chapters 1-11 run from melody brewing (G25) through the letters by ark (G97) to the song school (G116). Chapter 12
is the night the children sing for everyone.

## Story

Three of Old Wick's pupils can sing all their songs without a record, so the island puts up a stage on the
homestead green. Wick hands the player the chalkboard: five solos, then everybody on the island song. Every song
lives in a key, the note it starts and comes home to. Moving between songs in near keys (a fifth apart) keeps the
crowd with you; jumping across the circle loses them. Every child must get a solo, nobody sings twice running, and
no song is sung twice. Get close to the smoothest possible order and the green stands and sings record thirteen
back at the stage. Get it badly wrong and the crowd drifts off; you can try again tomorrow evening.

## Beats, mechanics and tests (`GraduationConcertTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Every song has a key; key changes cost warmth by circle-of-fifths distance | `keysOf` (found tune first note, record thirteen = island key), `fifths` (0-6), `cost`, `warmth` = 12 - cost | `keysSitOnTheCircleOfFifths` |
| Wick knows the smoothest set | `best()` / `bestSet()`: exact search over legal orders (checked against brute force) | `solverFindsTheSmoothestLegalSet` |
| The rules of the chalkboard | `perform`: NOT_GRADUATE, NOT_THEIRS, SAME_SINGER, ALREADY_SUNG, LEAVES_SOMEONE_OUT, SET_FULL; `close` needs 5 solos | `setListRules` |
| A rough night, then a good one | `close`: CHEERED within `SLACK` 2 of best, else ROUGH; `rerun` next evening | `roughConcertRerunsThenTheBestSetIsCheered` |
| The Song School's graduates take the stage | `fromSchool` (G116 graduates and their set songs, choir closes on G94 `ThirteenthSong.RECORD`) | `songSchoolGraduatesGiveTheConcert` |
| Quest `q_graduation_concert` | colony `QuestProgress`: perform solo x5, cheer concert x1, talk old_wick | `roughConcertRerunsThenTheBestSetIsCheered` |

## Lines (`ConcertLines`)

- Wick, before: "Five songs from the children, then all of us on the island song. Mind the keys: every jump between
  them loses the crowd a little."
- During: "The green is at 2. 1 more solo before the choir."
- Ready: "That's the solos. Bring in the choir."
- Cheer: "They're on their feet! The whole green is singing it back."
- Rough: "Too many jumps; they lost the thread. Same time tomorrow, smoother this time."
- Wick, quest done: "When I was their age the arks were still flying. Tonight it felt like they never left."
- After: "The children want to play the harbour next. Can't stop them now."

## Editor later (UNREAL-QUEUE)

A stage on the homestead green, a chalk set-list board UI with keys drawn on a circle of fifths and a warmth meter,
G116 child NPCs singing through the G33 record player, the G53 choir stones lit for the closer. Source-only here.
