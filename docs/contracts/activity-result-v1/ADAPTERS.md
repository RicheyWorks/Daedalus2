# Contest receipts hub (G23)

Contest gap **G23** (minigame contest 2026-10-19, owner 2hot2trot), added after G01-G22 were filled. It wires the
G12 activity-result envelope (`com.daedalus.world.activity`) into three games that landed in the contest, without
changing their code, and adds one router hosts can call for any finished game.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `FishingCastAdapter` | G07 sky-island fishing, `world.fishing.CastSession` (oddsreaper) | `fishing.cast-outing` | `Outing.of(casts, newKinds, abandoned)` | casts, caught, rare_caught, new_kinds, missed | animal, bird, fish / scouting, observation, current_travel |
| `HornbackPassageAdapter` | G03 Calm the Hornbacks, `world.labyrinth.HornbackHerd` (pythagoras) | `labyrinth.hornback-passage` | `Passage.of(report, abandoned)` | herd, arrived, calm_arrived, burned, lost, drinks, guided | animal / herding, carrying, guarding |
| `EchoBellAdapter` | G01 Echo Bell gate, `world.labyrinth.EchoBellGate` (prometheus) | `labyrinth.echo-bell` | `Listening.of(gate, lastVerdict, attempts, abandoned)` | bells, hits, attempts, gate_open | animal, bird, social_insect / observation, scouting, signaling |

`ActivityRouter.contest(mode)` registers all three with `AwardPolicy.inactive` (contributions recorded, 0 points)
until the owner approves numbers; `setPolicy` installs an approved revision. `settle(activityId, session, result)`
type-checks the result, issues the receipt and credits each participant once. Any other game joins with
`register(adapter, ResultType.class, policy)` (the tests register the G12 Chalk Trail adapter this way).

## Daedalus tie-in

*What Life Learns*: the Kite Ray that spots ripples, the Kennel dog that walks the trough route and the Echo
Crickets that widen the bell window all grow from the same games the player plays, and each is credited exactly once
per session. Stampedes, empty outings and missed peals still count as settleable effort (FAILED); leaving
(ABANDONED) pays nothing. Snapshots hold only primitives, so a receipt never keeps a live simulation.

## Hub II (contest G36)

`ActivityRouter.contestAll(mode)` adds four more landed contest games to the three above, all with inactive
policies until the owner approves numbers:

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `EggCareAdapter` | G06 egg hatching, `world.eggs.EggHatchery` (art-master-flex) | `eggs.hatch-care` | `Care.of(eggState, abandoned)` | ticks, turns, chills, hatched, perfect_care | animal, bird / nursery, guarding |
| `CatchRallyAdapter` | G11 throwable sports, `world.sports.ThrowableSports` (art-master-flex) | `sports.catch-rally` | `Rally.of(catchResult, abandoned)` | throws, caught, best_streak, score | animal, bird / fetching, play |
| `MailRouteAdapter` | G14 mail route, `world.parcels.MailRoute` (hephaestus) | `parcels.mail-route` | `Round.of(receipt, abandoned)` | delivered, late, undelivered, ghost_returned, stamps, medal | animal, bird / carrying, scouting |
| `AssemblyRepairAdapter` | G16 Missing Piece Collector, `world.bricks.AssemblyRepair` (hephaestus) | `bricks.assembly-repair` | `Repair.of(receipt, abandoned)` | restored, mean_quality, pieces_used, rejects, kiln_uses, sky_gate_open | animal, bird / scouting, carrying |

Tie-in: the nest hen that warmed the egg, the Inkpup that fetched, the carrier pigeon on the mail round and the
magpie that spotted the genuine brick each grow from the game they helped with, credited once.

## Hub III (contest G44)

`ActivityRouter.contestAll(mode)` now also registers four more landed games, again with inactive policies:

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `KennelWaterAdapter` | G17 kennel water loop, `world.companion.KennelWaterLoop` (art-master-flex) | `kennel.quiet-spring` | `Watch.of(questResult, abandoned)` | passed, days, thirsty_days, drunk_l, spilled_l | animal / guarding, carrying |
| `TemperForgeAdapter` | G19 Anvil and Quench, `world.forge.TemperForge` (hephaestus) | `forge.anvil-quench` | `Temper.of(result, abandoned)` | heat_pm, hammer_pm, quench_pm, perfect_strikes, cracked, temper, ark_plate | animal / smithing, carrying |
| `AshfallRegrowthAdapter` | G20 Ashfall Regrowth, `world.battlefield.AshfallRegrowth` (pythagoras) | `battlefield.ashfall-regrowth` | `Regrowth.of(report, abandoned)` | restored, seasons, old_growth_pm, strikes, burnt, caches_used, herds_placed | animal, bird / grazing, seeding |
| `FirelineWardenAdapter` | G27 Fireline Warden, `world.battlefield.FirelineWarden` (pythagoras) | `battlefield.fireline-warden` | `Defence.of(report, abandoned)` (a fire still BURNING is refused) | result (2 saved, 1 held, 0 lost), ticks, saved_pm, burnt, cut, wetted, doused | animal / firefighting, carrying |

Fractions (old growth, saved share) are stored as whole per mille so receipts stay canonical integers.

## Hub IV (contest G55)

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `KennelPantryAdapter` | G26 kennel food loop, `world.companion.KennelPantry` (art-master-flex) | `kennel.pack-order` | `Feeding.of(questResult, abandoned)` | passed, days, hungry_days, crafted, served, spoiled_milk_l | animal / guarding, foraging |
| `HerbGardenAdapter` | G40 Herb Chord Garden, `world.audio.HerbChordGarden` (prometheus) | `audio.herb-chord-garden` | `Planting.of(verdict, abandoned)` | lines, target, perfect | social_insect, bird / pollinating, observation |

Both are registered in `ActivityRouter.contestAll` with inactive policies, and every settled receipt lands in the
G49 journal (`ActivityRouter.journal()`).

## Hub V (contest G74)

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `FogBellAdapter` | G52 Fog Bell Call Signs, `world.audio.FogBellCallSigns` (prometheus) | `audio.fog-bell-call-signs` | `Call.of(verdict, abandoned)` | correct, blurred | bird, animal / observation, scouting |
| `WindChimeAdapter` | G60 Wind Chime Tuning, `world.audio.WindChimeTuning` (prometheus) | `audio.wind-chime-tuning` | `Tuning.of(verdict, abandoned)` | tuned, tubes_ok, worst_cents, trim_tenths_mm | bird, animal / observation, crafting |
| `DripCaveAdapter` | G64 Drip Cave Chorus, `world.audio.DripCaveChorus` (prometheus) | `audio.drip-cave-chorus` | `Chorus.of(verdict, abandoned)` | correct, off_ms | animal, bird / observation, scouting |
| `SquallCupAdapter` | G35 Squall Cup, `world.odds.tournament.SquallCupQuest` (oddsreaper) | `odds.squall-cup` | `Cup.of(quest, abandoned)` (a cup still ENTERED/ODDS_POSTED is refused) | champion, rounds_won | animal, bird / fishing, scouting |

G34 Beaver Waters is wrapped in Hub VI below.

## Hub VI (contest G83)

The five landed Pythagoras ecology games, registered in `ActivityRouter.contestAll` with inactive policies:

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `BeaverWatersAdapter` | G34 Beaver Waters, `world.battlefield.BeaverWaters` (pythagoras) | `battlefield.beaver-waters` | `Ponds.of(spring, abandoned)` copies the final facts out of the live grid | wet, home_flooded, target_wet_pm, pond_cells, wet_cells, felled, layers_left | animal / building, foraging |
| `SeedVaultAdapter` | G43 Ark Seed Vault, `world.battlefield.SeedVault` (pythagoras) | `battlefield.ark-seed-vault` | `Voyage.of(vault, abandoned)` (a vault still at sea is refused) | all_bands, years, surviving_species, caches | bird, animal / seeding, caching |
| `BeeBloomAdapter` | G48 Bee Bloom, `world.battlefield.BeeBloom` (pythagoras) | `battlefield.bee-bloom` | `Season.of(report, abandoned)` | thriving, seed_set_pm, hives_alive, frost_day (first frost day + 1, 0 = none), days | social_insect, bird / pollinating, foraging |
| `TrophicCascadeAdapter` | G58 Trophic Cascade, `world.battlefield.TrophicCascade` (pythagoras) | `battlefield.trophic-cascade` | `Valley.of(report, abandoned)` | cascade, willow_pm, colonies, elk, wolves, years | animal / hunting, guarding |
| `SalmonRunAdapter` | G71 Salmon Run, `world.battlefield.SalmonRun` (pythagoras) | `battlefield.salmon-run` | `Run.of(report, abandoned)` | restored, fished_out, mean_escapement, total_catch, forest_nitrogen, years | animal, bird / fishing, carrying |

Only the outcome that heals the valley completes: a WET meadow with a dry homestead, every seed band home at
landfall, a THRIVING bloom, a wolf-driven CASCADE (culling to the same elk count earns no wolf credit) and a
RESTORED run. Everything else is FAILED, or ABANDONED when the host quits. Counts and fractions are whole numbers
(per mille, rounded heads and fish) so receipts stay canonical.

Tie-in: the ark creatures that rebuilt the shattered valley (the beaver colony, the seed-caching jays, the hives,
the wolf pack and the river bears) each earn their G12 credit once per run, and the G49 journal replays it after a
restart.

## Hub VII (contest G95)

The five landed OddsReaper quests, registered in `ActivityRouter.contestAll` with inactive policies. Each snapshot
is taken from the quest object; a quest still in progress is refused unless the host abandoned it.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `KeepersLedgerAdapter` | G56 The Keeper's Ledger, `world.odds.ledger.KeepersLedgerQuest` (oddsreaper) | `odds.keepers-ledger` | `Ledger.of(quest, abandoned)` (OPEN refused) | doubled, keepers_mark, balance, wagers, disciplined | animal, bird / counting, observation |
| `LaunchWindowAdapter` | G68 The Launch Window, `world.odds.launch.LaunchWindowQuest` (oddsreaper) | `odds.launch-window` | `Launch.of(quest, abandoned)` (not SAILED refused) | wise, route, day, expected_souls, best_souls, souls_home | bird, animal / observation, scouting |
| `RivalBookAdapter` | G77 The Rival Book, `world.odds.rival.RivalBookQuest` (oddsreaper) | `odds.rival-book` | `Scan.of(quest, abandoned)` (SCANNING refused) | exposed, value_lines, found, miscalls, reward | animal, bird / scouting, observation |
| `ArkUnderwriterAdapter` | G80 The Ark Underwriter, `world.odds.insurance.UnderwriterQuest` (oddsreaper) | `odds.ark-underwriter` | `Season.of(quest, abandoned)` (QUOTING/REJECTED/APPROVED refused) | solvent, close_herbs, shortfall_herbs, bust_risk_pm | animal, bird / counting, guarding |
| `KeepersToteAdapter` | G88 The Keeper's Tote, `world.odds.tote.ToteQuest` (oddsreaper) | `odds.keepers-tote` | `Heat.of(quest, abandoned)` (BOARD_OPEN/BACKED refused) | won, overlay, pool | animal, bird / observation, counting, scouting |

What completes: a DOUBLED ledger, a wise launch (within the Keeper's 98% tolerance of the best expected life,
whatever sky the dice brought), every soft rival line EXPOSED, a SOLVENT season and a WON heat. The Keeper's Mark,
the overlay and the bust risk are kept as measures so an owner-approved policy can reward discipline over luck.

Tie-in: the Keeper teaches the survivors to stake what the odds justify; the companions that kept the tally, read
the glass and sniffed out the soft lines each earn their G12 credit once per quest, replayable from the G49 journal.

## Receipts hub VIII (contest G115, 2hot2trot): Youtube Master Island story chapters

Registered in `ActivityRouter.contestAll` under inactive `mastery.island-story` policies (points stay an owner
decision). Read-only on `world.brew.*`; each snapshot's `of(chapter, abandoned)` refuses a chapter still in play.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `RecordHuntAdapter` | G46 Ark Record Hunt, `world.brew.hunt.RecordHunt` (youtube-master) | `brew.ark-record-hunt` | `Hunt.of(hunt, abandoned)` (quest open refused) | found, remaining, days | animal, bird / scouting, foraging, listening |
| `ChoirStonesAdapter` | G53 Choir Stones, `world.brew.stones.ChoirStones` (youtube-master) | `brew.choir-stones` | `Watch.of(stones, abandoned)` (open with no cut-off night refused) | stones, held_nights, cut_off | animal, bird / listening, hauling, observation |
| `FirstWeekAdapter` | G62 The First Week Home, `world.brew.week.FirstWeek` (youtube-master) | `brew.first-week-home` | `Week.of(week, abandoned)` (week running refused) | days, health, sick | animal, bird / foraging, carrying, scouting |
| `RootCellarAdapter` | G73 The Root Cellar, `world.brew.cellar.RootCellar` (youtube-master) | `brew.root-cellar` | `Cellar.of(cellar, abandoned)` (before the Long Dark ends refused) | jars, bad_seals, day | animal, bird / carrying, foraging, guarding |
| `HomecomingSupperAdapter` | G85 The Homecoming Supper, `world.brew.supper.HomecomingSupper` (youtube-master) | `brew.homecoming-supper` | `Supper.of(supper, abandoned)` (fewer than 3 courses refused) | seated, courses, discontent | animal, bird / companionship, listening, guarding |
| `ThirteenthSongAdapter` | G94 The Thirteenth Song, `world.brew.song.ThirteenthSong` (youtube-master) | `brew.thirteenth-song` | `Composing.of(song, abandoned)` (not brewed refused) | verses, composed, brewed | animal, bird / listening, singing, companionship |

What completes: three ark records home, every fragment linked through the tremor nights, seven days survived, the
cellar quest done, a warm supper and the island's thirteenth song brewed. A night that cut a fragment off, a week
lost to thirst or hunger, a Long Dark ended without the quest, or a supper that left a guest discontent fails.

Tie-in: the goat that nosed herbs into the kettle and the wren that hummed the verses back walked every chapter of
the shattered-planet homecoming with you; each earns its G12 credit once per chapter run, replayable from the G49
journal.

## Receipts hub IX (contest G127, 2hot2trot): island-audio games

Registered in `ActivityRouter.contestAll` under inactive `mastery.listening` policies. Read-only on `world.audio.*`;
each snapshot is built from the game's own judged `Verdict`.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `ThunderTowersAdapter` | G89 Thunder Towers, `world.audio.ThunderTowers` (prometheus) | `audio.thunder-towers` | `Storm.of(verdict, abandoned)` | correct, towers, worst_error_tenths | bird, animal / listening, counting, observation |
| `DopplerFlybyAdapter` | G96 Doppler Flyby, `world.audio.DopplerFlyby` (prometheus) | `audio.doppler-flyby` | `Flyby.of(verdict, abandoned)` | right_ark, right_speed, speed | bird, animal / listening, observation, scouting |
| `HullKnockAdapter` | G101 Hull Knock Survey, `world.audio.HullKnockSurvey` (prometheus) | `audio.hull-knock-survey` | `Survey.of(verdict, abandoned)` | hits, misses, false_alarms | bird, animal / listening, guarding, observation |
| `WaveOrganAdapter` | G109 Wave Organ, `world.audio.WaveOrgan` (prometheus) | `audio.wave-organ` | `Tide.of(verdict, abandoned)` | triad, worst_cents (0-1200) | bird, animal / listening, singing, observation |

What completes: the right strike cell, the right ark at the right speed, a perfect hull survey and a true triad.

Tie-in: before the arks sail, the island listens: the owl that counted thunder, the hound that heard a cracked
plate ring dull. Each earns its G12 credit once per run, replayable from the G49 journal.

## Receipts hub X (contest G137, 2hot2trot): regrowth island-audio games

Registered in `ActivityRouter.contestAll` under inactive `mastery.listening` policies. Read-only on `world.audio.*`;
each snapshot is built from the game's own judged result.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `KeepersCallAdapter` | G121 Keeper's Call, `world.audio.KeepersCall` (prometheus) | `audio.keepers-call` | `Echo.of(run, abandoned)` (refused while the run is in play unless abandoned) | score (0-16), stars (0-3) | bird, animal / listening, singing, memory |
| `DawnChorusAdapter` | G124 Dawn Chorus Census, `world.audio.DawnChorusCensus` (prometheus) | `audio.dawn-chorus-census` | `Census.of(verdict, abandoned)` | right_loudest, right_missing | bird, animal / listening, counting, observation |
| `FrogPondAdapter` | G130 Frog Pond Niches, `world.audio.FrogPondNiches` (prometheus) | `audio.frog-pond-niches` | `Wetland.of(wetland, verdict, abandoned)` | clear, species (0-10) | bird, animal / listening, observation, habitat |

What completes: an echo run that earns at least one star (a phrase of 6 or more), a census naming both the most
abundant and the missing species, and a pond assignment with no masking pair.

Tie-in: regrowth on the shattered planet is heard before it is seen. The wren that echoed the Keeper's bells, the
hound that sat out the dawn chorus and listened as the frogs sorted themselves into ponds each earn their G12 credit
once per run, replayable from the G49 journal.

## Receipts hub XI (contest G146, 2hot2trot): sky-island odds quests and regrowth audio

Registered in `ActivityRouter.contestAll` under inactive policies (`mastery.reckoning` for the odds quests,
`mastery.listening` for the audio games). Read-only on `world.odds.*` and `world.audio.*`; each snapshot is built from
the game's own quest stage or judged result, and a quest still in play is refused unless the host abandoned it.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `CaptainChoiceAdapter` | G122 Choosing the Last Captain, `world.odds.stopping.CaptainChoiceQuest` (oddsreaper) | `odds.captain-choice` | `Hiring.of(quest, abandoned)` | best, rank (0 = not hired), seen | animal, bird / scouting, observation, judgement |
| `StarChartAdapter` | G125 The Torn Star Chart, `world.odds.collect.ChartCollectorQuest` (oddsreaper) | `odds.star-chart` | `Haul.of(quest, abandoned)` | charted, traded (0-8) | animal, bird / scouting, hauling, observation |
| `LifeboatDriftAdapter` | G133 The Lifeboat Drift, `world.odds.walk.LifeboatQuest` (oddsreaper) | `odds.lifeboat-drift` | `Voyage.of(quest, abandoned)` | harbour, watches (cap 1000), rations_left | animal, bird / rowing, companionship, endurance |
| `BroodCyclesAdapter` | G135 Brood Cycles, `world.audio.BroodCycles` (prometheus) | `audio.brood-cycles` | `Brood.of(verdict, abandoned)` | best, meetings, best_meetings (cap 10000) | bird, animal / listening, counting, observation |
| `DrumRollAdapter` | G138 Drum Roll ID, `world.audio.DrumRollId` (prometheus) | `audio.drum-roll-id` | `Roll.of(roll, guess, abandoned)` | correct, beats | bird, animal / listening, observation, counting |

What completes: hiring the single best sailor, a full star chart, reaching the harbour lights, a brood cycle with the
fewest predator meetings, and naming the right woodpecker.

Tie-in: the last ark needs a captain, a chart and a crew that survives the wreck, while the regrown forest below
counts its cicada years and woodpecker rolls. The gull that watched the interviews and the pup that rowed beside you
each earn their G12 credit once per run, replayable from the G49 journal.

## Receipts hub XII (contest G153, 2hot2trot): Youtube Master Island story chapters 10-13

Registered in `ActivityRouter.contestAll` under inactive `mastery.island-story` policies. Read-only on `world.brew.*`;
each snapshot is built from the chapter's own quest progress and result, and a chapter still in play is refused
unless the host abandoned it.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `LettersByArkAdapter` | G97 Letters by Ark, `world.brew.letters.LettersByArk` (youtube-master) | `brew.letters-by-ark` | `Post.of(post, abandoned)` | steps (0-4), landed_good, replies | animal, bird / hauling, companionship, scouting |
| `SongSchoolAdapter` | G116 The Song School, `world.brew.school.SongSchool` (youtube-master) | `brew.song-school` | `Term.of(school, abandoned)` | graduates, days | animal, bird / listening, singing, companionship |
| `GraduationConcertAdapter` | G131 The Graduation Concert, `world.brew.concert.GraduationConcert` (youtube-master) | `brew.graduation-concert` | `Evening.of(concert, abandoned)` | cheered, key_changes, best, evenings | animal, bird / listening, singing, companionship |
| `HarbourRoundAdapter` | G139 The Harbour Round, `world.brew.round.HarbourRound` (youtube-master) | `brew.harbour-round` | `Harbour.of(round, abandoned)` | sweet, harmony_pct (0-100) | animal, bird / listening, singing, companionship |

What completes: the letters quest finished with Dov, three graduates from Old Wick's school, a cheered concert (a
rough one fails) and a sweet round sung at the harbour.

Tie-in: after the homecoming the island writes to the far islands, teaches their children the thirteen songs, gives
them a concert and sings them a round as the next ark comes in. The goat that carried the jars and the wren that
held a voice in the round each earn their G12 credit once per chapter run, replayable from the G49 journal.

## Receipts hub XIII (contest G160, 2hot2trot): salvage lockers, buzz garden, owl fix, squirrel's winter

Registered in `ActivityRouter.contestAll` under inactive policies (`mastery.reckoning`, `mastery.listening`,
`mastery.observation`). Read-only on the game cores; each snapshot is built from the game's own quest stage, judged
`Verdict` or forager `Report`, and a salvage still dealing is refused unless the host abandoned it.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `SalvageLockersAdapter` | G141 The Salvage Lockers, `world.odds.lockers.LockerQuest` (oddsreaper) | `odds.salvage-lockers` | `Salvage.of(quest, abandoned)` | enough, found, voids, rounds (0-5) | animal, bird / scouting, observation, judgement |
| `BuzzGardenAdapter` | G145 Buzz Garden, `world.audio.BuzzGarden` (prometheus) | `audio.buzz-garden` | `Garden.of(verdict, abandoned)` | best, pollen, best_pollen | bird, animal / listening, pollination, observation |
| `OwlFixAdapter` | G150 Owl Fix, `world.audio.OwlFix` (prometheus) | `audio.owl-fix` | `Fix.of(verdict, abandoned)` | exact, score (0-100) | bird, animal / listening, scouting, observation |
| `SquirrelsWinterAdapter` | G129 Squirrel's Winter, `world.battlefield.PatchForager` (pythagoras) | `ecology.squirrels-winter` | `Hoard.of(report, abandoned)` | hoarded, share_pct (0-200), visits | animal, bird / foraging, observation, companionship |

What completes: finding the compass in three of five salvage rounds, the best bee-to-flower match, the owl's exact
cell, and a HOARDED day in the squirrel's meadow.

Tie-in: the wreck gives up its compass, the regrown meadow buzzes and hoots, and the red squirrel stocks its hoard for
the long dark. The gull at the lockers, the owl at the microphones and the vole in the brambles each earn their G12
credit once per run, replayable from the G49 journal.

## Receipts hub XIV (contest G168, 2hot2trot): guest lofts, scar dig, void crossing, apprentices

Registered in `ActivityRouter.contestAll` under inactive policies (`mastery.companionship`, `mastery.hauling`,
`mastery.crewing`). Read-only on the game cores; each snapshot is built from the game's own settle/announce outcome,
dig `Result` or `Crossing`. A visit not yet settled, a board not yet announced, or a crossing still SAILING is refused
unless the host abandoned it. A dig result is final once run.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `GuestLoftsAdapter` | G149 The Guest Lofts, `world.brew.lofts.GuestLofts` (youtube-master) | `brew.guest-lofts` | `Stay.of(lofts, abandoned)` | aired, fewest, families | animal, bird / companionship, planning, housekeeping |
| `ScarDigAdapter` | G132 Meteor Scar Dig, `world.forge.ScarDig` (hephaestus) | `forge.scar-dig` | `Dig.of(result, abandoned)` | ingots, starmetal, emberite, water | animal / hauling, endurance, prospecting |
| `VoidCrossingAdapter` | G152 Void Crossing, `world.forge.VoidCrossing` (hephaestus) | `forge.void-crossing` | `Passage.of(crossing, abandoned)` | days, min_seam, patches, lost | animal, bird / crewing, endurance, hauling, companionship |
| `ApprenticesAdapter` | G155 The Apprentices, `world.brew.apprentice.Apprenticeships` (youtube-master) | `brew.apprentices` | `Lantern.of(board, abandoned)` | paired, blocking | animal, bird / companionship, matchmaking, observation |

What completes: a snug loft plan (aired = fewest), leaving the scar with an ingot and without fainting, any arrival
at the shard (losses kept as a measure), and a stable lantern-night announcement (no blocking pair).

Tie-in: the far-island families are housed, the scar gives up its starmetal, the ark crosses the void, and the
children find their masters. The loft hound, the scar goat and the crew companions each earn their G12 credit once
per run, replayable from the G49 journal.

## Receipts hub XV (contest G187): Tag and Count, Birth Night Lanterns, Cricket Thermometer, Parting Jars

Registered in `ActivityRouter.contestAll` with inactive `mastery.observation`, `mastery.reckoning`,
`mastery.listening` and `mastery.island-story` policies respectively. These adapters only snapshot existing core
results. They do not run a census, lodge guesses, judge a temperature, schedule jars, harvest, or advance quests.
The host supplies terminal evidence and session authority through the existing G12 contract.

| Adapter | Game (owner) | Activity id | Result snapshot | Measures | Who learns (profiles / roles) |
| --- | --- | --- | --- | --- | --- |
| `TagAndCountAdapter` | G156 Tag and Count, `world.battlefield.MarkRecapture` (pythagoras) | `ecology.tag-and-count` | `Census.of(census, abandoned)` | marked, caught, recaptured (each capped at 1,000,000), accurate (0-1) | animal, bird / counting, observation, scouting |
| `BirthNightLanternsAdapter` | G157 Birth Night Lanterns, `world.odds.match.BirthNightQuest` (oddsreaper) | `odds.birth-night-lanterns` | `Muster.of(quest, abandoned)` | nods (0-2), closest_gap (0-365), shared (0-1) | animal, bird / counting, observation, companionship |
| `CricketThermometerAdapter` | G159 Cricket Thermometer, `world.audio.CricketThermometer` (prometheus) | `audio.cricket-thermometer` | `Listening.of(verdict, abandoned)` | correct (0-1), score (0-100) | animal, bird / listening, observation, counting |
| `PartingJarsAdapter` | G167 The Parting Jars, `world.brew.parting.PartingJars` (youtube-master) | `brew.parting-jars` | `Shelf.of(jars, abandoned)` | orders, on_time, best (each capped at 64) | animal, bird / hauling, planning, companionship |

Completion mappings are adapter choices using the cores' existing judgements: an `ACCURATE` census (not a new
quota rule), both Keeper nods regardless of random birthday matches, a correct cricket verdict including the
silent-night answer, and a full-shelf accepted jar plan (`lastOnTime == best.size()`). Other judged results fail.
A missing census or cricket verdict, a quest still `GUESSING`, or jars with no accepted plan are refused unless
abandoned. Invalid/duplicate jar requests do not replace the last accepted plan. An abandonment always takes
precedence, including after a successful result. Census truth and non-finite cricket error values are not exported.

The census keeper's companion, the muster observer, the cricket listener and Aunt Brine's jar carrier use the
unchanged settlement and G49 journal: identical retries settle once, conflicting payloads are rejected, and replay
restores the same awards. Registering these adapters activates no reward amounts. `HubFifteenAdaptersTest` exercises
real finished/failed cores, unfinished refusal, abandonment, bounded measures, inactive defaults and journal replay.
