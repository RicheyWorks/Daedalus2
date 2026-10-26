# The First Week Home: Youtube Master Island, chapter 5 (youtube-master, contest G62)

Chapters 1-4 built the island's tools: melody brewing (G25), mended records and clean springs (G33), the record
hunt over the rope bridges (G46) and the choir stones that hold them (G53). Chapter 5 is the week you have to live
through with them.

## Story

The last ark ferry drops you at the homestead with a canteen and a sack of groats. Old Wick, who ran that ferry
between the fragments for years, says the first week is the hard one: the springs are cloudy until the songs are
mended, the sea looks like water and isn't, and the stove only cooks what the plot gives you. Drink clean when you
can, raw when you must (one cup in four will make you sick), never the sea. Put a note-herb in the pot and the meal
goes further. If you've mended the desert record, its tonic halves a day's thirst. Seven days, and you're not a
survivor any more, you're a neighbour.

## Beats, mechanics and tests (`FirstWeekTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The island's numbers are the ones the Unreal side already uses | constants and recipes checked against `engines/unreal/ytm-island/food_water.json` | `numbersMatchFoodWaterJson` |
| The stove cooks only what the plot holds; clean water only; note-herbs go further | `Larder.cook` (all or nothing), `Larder.restore` (25 + 10 per extra ingredient + 10 note-herb, max 45) | `theStoveTakesEverythingOrNothing` |
| Seven days kept well are survived; Wick welcomes you | `FirstWeek` drink/eat/endDay; quest `q_first_week` (survive day x7, talk old_wick) on PORT09-twin `QuestProgress` | `aWellKeptWeekIsSurvivedAndOldWickWelcomesYou` |
| Going dry or hungry costs health, then the week | thirst/hunger at 0 at day end: -40 health each; 0 health = lost | `goingWithoutWaterCostsHealthUntilTheWeekIsLost` |
| One cup of raw water in four makes you sick for the day | seeded 25% sickness, +20 thirst drain | `rawWaterSicknessIsSeededAtAboutOneInFour` |
| The sea makes it worse; the desert tune helps | salt -10; `Item_YTM_Tonic_Found_desert_thirst` halves the day's drain (once a day) | `theSeaMakesItWorseAndTheDesertTuneHalvesTheDrain` |
| The springs of chapter 2 keep you alive | draw clean water from a G33 purified spring every day | `theSpringsOfChapterTwoKeepYouAlive` |

Day scale: 60 thirst and 45 hunger a day (two clean cups and one good meal hold you steady).

## Old Wick's lines

- Greeting: "First week's the hard one. Drink clean when you can, cook what the plot gives you, and never drink
  the sea, whatever it looks like."
- Thirsty: "Your lips are cracking. Get to a clean spring before the sun goes down."
- Hungry: "You're running on nothing. Cook something, even porridge."
- Sick: "That cloudy water got you. Boil it, filter it, or brew a cadence over it next time."
- Steady: "Day 3. You're holding up."
- Lost: "Lie still. Someone will carry you home. The shelf will wait for you."
- Quest done: "Seven days. You're not a survivor any more, you're a neighbour. The ferry's yours when you want it."

Editor later (UNREAL-QUEUE): vitals HUD and the stove can call this rule set through the server; no editor work
was done here.
