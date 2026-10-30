# The Ark Record Hunt: Youtube Master Island, chapter 3 (youtube-master, contest G46)

Chapter 1 (G25, `../STORY.md`) taught the island to brew by melody. Chapter 2 (G33, `../story/STORY.md`) mends
the arks' scratched seed-song records and clears the springs. Chapter 3 is about getting the records back first.

## Story

When the asteroid hit, the arks were still loading. The crates of seed-song records broke open in the blast, and
the records were flung across the shelf of broken land around the homestead: fragments of hillside, keel and
choir stone, now held together only by rope bridges the survivors strung.

Archivist Tamsin kept the ark's record ledger. Her legs won't take the bridges any more, but she can still hear a
record hum through the stone, and she tells you how far off the nearest one is and which bridge to cross first.
Each bridge costs you stamina, and so does searching a fragment; when you're spent, you sleep and go again
tomorrow. Every record you carry home goes into the homestead store, ready for Keeper Oriel's bench (chapter 2).

## Beats, mechanics and tests (`RecordHuntTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The shelf is broken land joined by rope bridges, and every fragment can be reached | `FragmentMap.seeded` (seeded spanning tree + loops), `FragmentMap.of` (hand-built, must be connected) | `seededMapsAreConnectedStableAndLoopy` |
| The records were flung across the shelf, never left at home | `RecordHunt` scatters records over distinct non-home fragments (seeded) | `recordsScatterOverDistinctFragmentsNeverTheHomestead` |
| Tamsin's bridge always brings you closer | `FragmentMap.nextStep` (neighbour on a shortest route), `RecordHunt.hint` | `theArchivistsBridgeAlwaysShortensTheWay`, `followingTheHintsFindsEveryRecordInExactlyItsDistance` |
| Bridges and searches cost stamina; sleep refills it once per new day | `walk`, `search`, `rest` (`TIRED`, `NO_BRIDGE`, `DUPLICATE`) | `bridgesStaminaAndDaysGateTheWalk` |
| Her hum gets louder as you get closer | `ArchivistLines.line` (underfoot / one bridge / warmer / faint / tired / empty) | `archivistHumsByDistance` |
| Quest `q_ark_record_hunt`: find 3 records, carry them home, tell the Archivist | PORT09-twin `colony.QuestProgress` steps find_record x3, return homestead x1, talk archivist_tamsin x1; reward claimable once | `questFindThreeCarryThemHomeAndTellTheArchivistThenMendThem` |
| The records you find are the ones chapter 2 mends | found records go into `colony.PlotState`; `story.SeedSongSpring.restore` mends them and clears springs | same test (Daedalus tie-in) |

## Archivist Tamsin's lines

- Underfoot: "It's right here. The needle-hum is under your feet. Search."
- One bridge: "One bridge away. Cross to Lantern Isle."
- Warmer: "Warmer. 3 bridges off; start across to Bell Ledge."
- Faint: "Faint, far out on the shelf: 6 bridges. Head for Reed Shelf and listen again."
- Tired: "You're spent. Sleep, and the bridges will still be there tomorrow."
- Quest done: "Three records home already. Take them to Keeper Oriel's bench and mend them. I'll keep listening for
  the rest."
- All found: "The crates are empty. Every record is home."

Fragments: Homestead, Reed Shelf, Goat Rock, Keel Drift, Bell Ledge, Mist Step, Lantern Isle, Choir Stone,
Cloudfoot, Needle Spur, Summit Shard, Ferry Knoll, Willow Crumb, Ash Tooth, Kite Perch, Hollow Bell (then "Reed
Shelf 2" and so on for bigger maps).

Editor later (UNREAL-QUEUE): record pickups, the Archivist NPC and rope-bridge links can call this rule set through
the server; no editor work was done here.
