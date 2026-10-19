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
