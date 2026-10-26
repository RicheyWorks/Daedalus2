# Combat Odds Engine (DOR 1)

Owner: OddsReaper (`oddsreaper`). Code: `daedalus-core/src/main/java/com/daedalus/world/odds`. JDK-only, pure, offline.
It never runs in a frame path and never touches the network or Unreal.

## What it answers
Given one player and a squad (with the squad's DTO 1 orders), how fair is the fight? A run returns an `OddsReport`:

- P(win) with a 95% Wilson interval (honest near 0 and 1), plus P(loss) and P(draw)
- time-to-kill distribution of wins and time-to-die distribution of losses (mean, sd, p50/p90/p99)
- health lost by the player: mean, sample variance, share of max health
- expected value per encounter with its own 95% interval (`Payoffs`: win / loss / draw value, cost per health point)
- mean foes downed

`report.encode()` is the single-line `DOR 1 ...` form for the team link and golden tests.

## Determinism
`OddsRng` is SplitMix64, fixed by source (not `java.util.Random`). `OddsRng.forTrial(seed, trial)` gives each trial its own
stream, so a report is a pure function of (encounter, seed, trials, payoffs), independent of trial order, and a C++ port
would match. `goldenReportLocksTheModel` pins a full report line.

## Model (assumptions to tune from in-game telemetry, not contract)
- Event-driven, continuous time. Every fighter swings on its own cooldown with a random first-swing phase.
- A hit rolls `accuracy`, then `critChance` for `critMultiplier` x damage. Armor is flat per hit, at least 10% always lands.
- DTO 1 verbs map to an `OrderProfile`: ATTACK fights at once, FLANK joins 3 s late with +15% accuracy, DEFEND takes 0.7x
  damage at 0.9x accuracy, REINFORCE joins 6 s late, HOLD and RETREAT are not threats (retreat leaves the fight).
- The player picks targets by `TargetPolicy` (FIRST_LISTED, LOWEST_HEALTH, HIGHEST_THREAT).
- WIN: no attacking foe left. LOSS: player health reaches 0. DRAW: `maxSeconds` runs out.

## Modules
| Class | Job |
|---|---|
| `OddsRng` | seeded RNG + per-trial streams |
| `Combatant` | one fighter's numbers; `withGrade(ForgeGrades.WeaponGrade)` applies a forged weapon (DFW 1) |
| `OrderProfile` | verb -> behaviour in the model |
| `Encounter` | player + foes + policy + time limit; `fromOrders(TacticalOrders.Spec, ...)` reads the squad-orders contract |
| `RosterStats` | DTR 1 roster -> per-unit stats at current health |
| `CombatOddsSimulator` | the Monte Carlo run |
| `Summary`, `Payoffs`, `OddsReport` | result types |
| `BalanceLimits` | balance band check for adaptive encounters |
| `CombatOddsDemo` | `java ... CombatOddsDemo [seed] [trials]` |

## Balance limits
`BalanceLimits.FAIR` = P(win) 40-85%, median time-to-kill <= 60 s, mean health lost <= 80%. A limit is VIOLATED only when
the whole 95% interval is outside it; a point estimate outside with an interval that still reaches in is a WARNING (run
more trials). Intended consumer: the Adaptive Combat Director's balance limits (team-codex / Astra) and encounter tuning.

## Use
```java
var parsed = TacticalOrders.parse(dto);                       // or the Director's Decision.orders()
var stats  = RosterStats.fromRoster(TacticalOrders.parseRoster(dtr), templatesByKind);
var enc    = Encounter.fromOrders(parsed.spec(), stats, hero, TargetPolicy.LOWEST_HEALTH, 60);
var report = CombatOddsSimulator.run(enc, 42L, 20_000);
var verdict = BalanceLimits.FAIR.check(report);
```