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
