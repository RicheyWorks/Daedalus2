# The Seed-Song Spring: Youtube Master Island, chapter 2 (youtube-master, contest G33)

Chapter 1 (G25, `../STORY.md`) taught the island brewing: herbs hum notes, ORDER is the recipe, and a tune that
comes home makes cloudy water drinkable. Chapter 2 is about what the arks lost.

## Story

When the asteroid broke the planet, the arks lifted off with seeds, animals and crates of seed-song records: one
short tune per record, sung into the seed vaults so the growing islands would remember them. The shattering
scratched every record. Each one still plays its opening, then the needle falls into a gouge where the ending (the
cadence) used to be. Since then the island's springs have run cloudy, because the springs only ever sang along.

Keeper Oriel tends the Homestead Well. She can't brew, but she can still hear. Bring her a record and she tells you
what is left of it. Brew the whole tune on your bench, the opening she heard plus the cadence you guessed, and the
record sings whole again. The jukebox learns it, and the mended tune runs downhill into the next cloudy spring,
which clears. Twelve records, twelve springs, from the Homestead Well up to the Summit Basin.

Your companions brew with you: a goat noses herbs into the kettle, a wren hums the opening back. The island
remembers that they helped (activity receipt, credited once).

## Beats, mechanics and tests

| Beat | Mechanic in code | Test (`SeedSongSpringTest` unless noted) |
|---|---|---|
| Every record is scratched; the scratch eats the cadence (1 or 2 closing notes) and always leaves 2+ to hear | `ScratchedRecord.of(tune, seed)`, `heard()`, `heardNotes()` | `theScratchAlwaysEatsTheCadenceAndLeavesTwoNotesToHear` |
| Brew the whole tune (opening plus missing cadence) to mend the record; the jukebox learns it | `SeedSongSpring.restore` uses the G25 `BrewBench.brew`, then `BrewBench.playRecord` | `brewingTheWholeTuneRestoresTheRecordAndPurifiesTheNextSpring` |
| Each mended tune clears the next cloudy spring; cloudy springs give `raw_water`, clean ones `water` | `SpringChain` (12 island springs, `purifyNext`, `draw`) | same, plus `springChainValidatesAndDrawsOncePerEvent`, `everyRecordMendedMakesTheWholeChainRunClean` |
| A wrong order still costs the herbs, and the needle skips | `Outcome.NEEDLE_SKIPS` | `theOpeningAloneOrAWrongOrderMakesTheNeedleSkip` |
| You must hold the record, have the herbs, and each kettle counts once | `NO_RECORD`, `MISSING_HERBS`, `DUPLICATE`, `UNKNOWN_RECORD`, `ALREADY_RESTORED` | `guardsSpendNothing` |
| Quest `q_seed_song_spring`: mend 3 records, drink from a clean spring, tell Keeper Oriel | PORT09-twin `colony.QuestProgress` steps restore x3, draw_clean x1, talk keeper_oriel x1; reward claimable once | `questRestoreThreeDrinkCleanThenTellTheKeeper` |
| Oriel's lines follow the chapter state; her hints say what she hears and whether the tune comes home | `KeeperLines.line`, `KeeperLines.hint` | `keeperHintsNameWhatSheHears`, quest test |
| Companions who brew with you are credited once | `activity/adapters/SeedSongBrewAdapter` (G12) registered on a G23 `ActivityRouter`, inactive policy by default | `SeedSongBrewAdapterTest` |

## Keeper Oriel's lines

- Greeting: "The arks sang these records into the seed vaults. The shattering scratched every one. Bring me a record
  and brew what it can't sing."
- Hint: "This is alpine. I hear Doleaf, Mimint, Solthorn, Mimint, then the scratch eats 1 note. It wants to come
  home: it ends on the note it began with."
- Progress: "The water at Homestead Well runs clear again. 1 of 12 records sing whole."
- After three: "Three songs mended. Go and drink from a clean spring, then come tell me."
- Quest done: "You hear that? The springs are humming the old tunes back. The arks would be proud. Keep the choir:
  every record you mend wakes another spring."
- All twelve: "Every spring on the island runs clean. The choir is whole."

## Springs (uphill order)

Homestead Well, Reed Seep, Ferry Steps, Goat Ledge, Old Ark Keel, Bell Hollow, Mist Stair, Lantern Pool, Broken
Choir, Cloudfoot, Needle Falls, Summit Basin (yield 4, rising by 1 every three springs).

Editor later (UNREAL-QUEUE): spring actors and a record-player prop can call this rule set through the server; no
editor work was done here. Award numbers for `mastery.brewing` remain an owner decision (inactive policy).
