# The Root Cellar: Youtube Master Island, chapter 7 (youtube-master, contest G73)

Chapters 1-6: melody brewing (G25), mended records and clean springs (G33), the record hunt (G46), choir stones
that hold the bridges (G53), the first week home (G62) and the record exchange with the neighbours (G66).
Chapter 7 gets the homestead through its first cloud season.

## Story

Aunt Brine keeps the salt pan on the sea edge, the way her mother kept the ark's cellar. She warns that the cloud
season brings the Long Dark: five days when the boats stay in and the hens stop laying. What isn't in a jar by
then, you go without. Fresh fish turns in two days and eggs in six, so the homestead learns her ways: boil the sea
for salt (two pans a day), salt or smoke the fish and bacon, dry the island herbs and beans in the sun, pickle the
eggs in salt and spring water. Twelve jars fit on the shelves. Now and then a seal goes bad and a jar keeps only
half as long; a spoiled jar goes on the compost for the beds. Salted food has to be soaked in clean spring water
before it goes into the pot. When the dark comes, you eat from the shelves, oldest jar first, and on the last day
Aunt Brine gives you the old brine crock.

## Beats, mechanics and tests (`RootCellarTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Fresh food spoils in days; salt, smoke, sun and brine keep it for weeks | `Preserve.SHELF_DAYS`, `shelfDays` (island herbs: 3 fresh, 30 dried) | `shelfLivesAndCosts` |
| Salt is boiled from the sea, two a day; salting takes salt, pickling salt and clean water; the smokehouse takes 2 a day, the drying rack 3 | `RootCellar.boilSea`, `Preserve.cost`, `Preserve.perDay`, `preserve` guards | `saltPanAndPreserveGuards` |
| Twelve jars fit on the shelves | `RootCellar.CAPACITY`, `CELLAR_FULL`, `take` frees a shelf | `cellarHoldsTwelveJars` |
| A bad seal halves a jar's life (seeded, about 1 in 10); spoiled jars become compost | `Jar.badSeal`, `nextDay` (spoils into `compost` in the plot store) | `badSealsAreSeededHalveLifeAndSpoiledJarsBecomeCompost` |
| Salted food must be soaked in clean water | `take` needs one `BrewBench.WATER` (G33 spring water) for a SALT jar | `saltedFoodMustBeSoakedInCleanWater` |
| Quest `q_root_cellar`: three ways of keeping (not fresh), eight more jars, eat from the cellar on all five Long Dark days, then Aunt Brine | PORT09-twin `colony.QuestProgress` (new_method x3, jar x8, dark_day x5, talk aunt_brine x1) | `questThreeMethodsEightJarsFiveDarkDaysThenBrine` |
| Eggs bartered from Hen-wife Mora (G66) are pickled, and in the dark make the Omelet from chapter 5's larder (G62) | `RecordExchange.trade` -> `preserve(PICKLE)` -> `take` -> `Larder.cook("Omelet")` | `eggsFromTheExchangeArePickledAndCookedInTheLongDark` |

## Aunt Brine's lines (`BrineLines`)

- Greeting: "Cloud season's coming. When the Long Dark sets in there's no boats and no laying, so whatever's not in
  a jar by then, you go without. Salt it, smoke it, dry it or pickle it."
- Methods: "That's 2 ways of keeping. Learn three; fresh doesn't count, it's gone in a week."
- Jars: "Now fill the shelves. 5 more jars before the dark."
- Waiting: "2 days till the dark. Keep the pan boiling."
- Dark: "Long Dark, day 1. Eat from the shelves, oldest jar first. Soak the salt fish or you'll be drinking all
  night."
- Missed: "The dark's passed and the shelves came up short. Next cloud season, fill them sooner."
- Quest done: "Five dark days and nobody went hungry. My mother kept the ark's cellar like that. Here, take the old
  brine crock."
- After: "The light's back. Compost the bad jars into the beds."

## Editor later (UNREAL-QUEUE)

Cellar shelves (12 jar sockets), salt pan on the sea edge, smokehouse and drying rack call `RootCellar`; Aunt Brine
NPC shows `BrineLines`; a Long Dark weather state for the island. Source-only here.
