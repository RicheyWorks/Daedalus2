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
| `KeepersToteAdapter` | G88 The Keeper's Tote, `world.odds.tote.ToteQuest` (oddsreaper) | `odds.keepers-tote` | `Heat.of(quest, abandoned)` (BOARD_OPEN/BACKED refused) | won, overlay, pool | animal, bird / observation, counting |

What completes: a DOUBLED ledger, a wise launch (within the Keeper's 98% tolerance of the best expected life,
whatever sky the dice brought), every soft rival line EXPOSED, a SOLVENT season and a WON heat. The Keeper's Mark,
the overlay and the bust risk are kept as measures so an owner-approved policy can reward discipline over luck.

Tie-in: the Keeper teaches the survivors to stake what the odds justify; the companions that kept the tally, read
the glass and sniffed out the soft lines each earn their G12 credit once per quest, replayable from the G49 journal.
