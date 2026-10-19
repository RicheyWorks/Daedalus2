# The Recording Isle: Melody Brewing story (youtube-master, contest G25)

Every storyline beat below is backed by code in this package; the test that proves it is named.

| Beat | Lore | Mechanic in code | Test |
|---|---|---|---|
| The arks' records | When the asteroid shattered the planet, the arks carried what they could: seeds, animals, and crates of seed-song records. Each record hides a short motif, a "found tune". | `FoundTune` rows from `engines/unreal/ytm-island/found_tunes.csv` (12 tunes, one per record) | `BrewBenchTest.theRealTuneListParsesAndEveryTuneBrewsAsWritten` |
| The jukebox teaches | On the island, the jukebox plays a record once and the brewer remembers its tune. | `BrewBench.playRecord(record)` learns the tune whose `LearnedFrom` is that record | `BrewBenchTest.aFoundTuneNeedsItsRecordPlayedFirst` |
| Order is the recipe | Island herbs each hum one note. Drop them into the kettle in a different order and you get a different tonic: rising tunes quicken, falling tunes cure, arches heal, valleys feed, dances give stamina. | `MelodyBrew.brew` (contour, leaps, stepwise, tier), a port of `herbcombo.py` with exact parity | `MelodyBrewParityTest` (1935 kettles), `MelodyBrewTest.orderIsTheRecipe` |
| Coming home purifies | A tune that ends on the note it began with is a cadence, "coming home". Cadence tonics make the cloudy spring water safe to drink: the island's mandatory water loop. | `BrewBench.brew`: cadence turns up to 5 x tier `raw_water` into `water` | `BrewBenchTest.brewingSpendsHerbsFromTheStoreAndPurifiesWater` |
| A found tune's gift | Brew a learned tune's exact order and you get its named tonic and bonus (the Arabic maqam record's tune halves thirst drain). | `BrewBench.match` + `FoundTune.tonic` | `BrewBenchTest.aFoundTuneNeedsItsRecordPlayedFirst` |
| One ear, two islands | Prometheus's island reads the same herbs as a chord (Harmonic Herbs), Youtube Master's as a melody: harmony vs melody, one pitch class per herb (BREW_SPLIT.md, agreed Oct 19). | `PitchTable` (`ISLAND_CANON`, `HERB_CHORD`, `orElse`) | `MelodyBrewTest.pitchTablesArePluggable` |
| The homestead store | Herbs come from the plot's store, the same one the Colony Ledger day book fills with fish, bugs and fruit (G15). | `BrewBench` uses `colony.PlotState`; herbs only spent when all are there; every brew counts once | `BrewBenchTest.missingHerbsSpendNothing` |

Editor later (UNREAL-QUEUE): `ADaedalusBrewBench` (DaedalusHomestead.h) can call this rule set through the server; no editor work was done here.
