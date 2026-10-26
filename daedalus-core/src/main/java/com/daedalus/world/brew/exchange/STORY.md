# The Record Exchange: Youtube Master Island, chapter 6 (youtube-master, contest G66)

Chapters 1-5: melody brewing (G25), mended records and clean springs (G33), the record hunt (G46), choir stones
that hold the bridges (G53) and the first week home (G62). Chapter 6 opens the island to its neighbours.

## Story

The other fragments have what the homestead lacks: Pell twists rope, Quarry Ida splits stone, Hen-wife Mora keeps
the only hens on the shelf, Fisher Dov works the cloud pools. None of them has heard music since the sky fell. A
mended record can be pressed into one copy a day, and a copy is worth a lot to someone who hasn't heard a tune in
years: one unit of their goods for every note, one more if the tune comes home, twice that if it's the tune they
were humming for today. But the same tune twice is less of a gift, and by the fourth copy they'll thank you and
decline. Rope goes to the bridges, stone blanks to the choir stones, eggs into the omelets that got you through the
first week.

## Beats, mechanics and tests (`RecordExchangeTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Only a mended record can be pressed, one copy a day | `RecordExchange.press` (uses G33 `SeedSongSpring.isRestored`, `nextDay`) | `onlyMendedRecordsPressAndOnlyOneCopyADay` |
| A copy is worth its notes (+1 if it comes home), double if wanted, halved per repeat; nothing = refused | `price`, `trade` (`REFUSED` keeps the copy) | `priceIsNotesPlusCadenceDoubledWhenWantedHalvedPerRepeat` |
| Each neighbour hums for different tunes each day | `wantsToday` (seeded per seed, day, trader; distinct) | `wantsAreSeededDistinctAndChangeDaily` |
| Trades need a copy, a known trader and a known tune; each trade counts once | `NO_COPY`, `UNKNOWN_TRADER`, `UNKNOWN_TUNE`, `DUPLICATE` | `tradeGuards` |
| Quest `q_record_exchange`: four trades, then two wanted tunes, then tell Pell | PORT09-twin `colony.QuestProgress` (trade x4, trade_wanted x2, talk pell x1) | `questFourTradesThenTwoWantedThenPell` |
| Rope and stones from the exchange keep chapter 4's bridges | goods land in `colony.PlotState` as `rope` / `choir_stone_blank`, used by `stones.ChoirStones` | `ropeAndStonesFromTheExchangeKeepTheBridgesOfChapterFour` |

In-game barter only: goods are store items; nothing touches money, wallets or the colony ledger.

## Neighbours and lines

Pell the rope-maker (rope), Quarry Ida (choir_stone_blank), Hen-wife Mora (Egg), Fisher Dov (fish).

- Greeting: "No one's played us a tune since the sky fell. Bring a pressed copy and we'll pay in rope, stone, eggs
  or fish."
- Progress: "2 trades so far. Ask what we're humming for today; we pay double for that."
- Wanted: "Now bring us the tunes we asked for. 2 more of those."
- Quest done: "Music on every fragment again. Take the good rope; you'll need it for those bridges."
- After: "Come back tomorrow. We'll be humming something new."
- Refused: "We've heard that one plenty, thanks."

Editor later (UNREAL-QUEUE): trader stalls on the fragments can call this rule set through the server; no editor
work was done here.
