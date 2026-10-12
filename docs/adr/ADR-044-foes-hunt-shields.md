# ADR-044: Foes that hunt, routes from the maze solver, and Halo shields

Status: accepted, 2026-10-12

## Why

With a blaster and a Ghost (ADR-042, ADR-043), the foes had to fight back. Richmond: "we have all those maze
algorithms to find fastest route, no way outrunning certain creatures", and "I love the shield mechanic of Halo...
better armor, better shields".

## Decision

**Routes: the maze engine's A* in the game.** `UDaedalusNav` (a world subsystem) is a port of daedalus-core's
`AStarSolver`. Like the solver it is a best-first search on f = g + h over arrays indexed by cell ID (`GridIndex`), with
per-cell weights (`WeightedMazeGrid`) and a search budget (`SolverBudgetExceededException`'s idea). The maze is the
island:

- 100 cm cells, each cell's floor read by a trace the first time a search touches it, then cached by cell and
  height band (islands have tiers).
- A step is walkable up 70 cm and down 220 cm. Higher is a wall or cliff; no floor is a ledge.
- 8-connected moves, no corner cutting, octile heuristic (admissible: every weight is at least 1).
- Cells beside a drop weigh 2.5, so foes keep off the lips.
- `engines/unreal/core-test/nav_astar_check.py` checks the same rules on a synthetic island with two tiers, a ramp,
  a wall and a drop (5/5).

**Foes** (`ADaedalusTarget`), each attack telegraphed by an orange glow:

| Kind | Hunts by | Attack |
|---|---|---|
| Blight Slime | hops along the A* route | bite up close, 0.3 s windup |
| Shardback | closes in | 0.55 s windup, then a straight charge at 1500 cm/s; stops at ledges; 1.8 s winded after |
| Dust Wisp | flies, keeps 7 to 13 m away above your head | slow glowing bolts (1500 cm/s), led a little: sidestep them |
| Stone Knight | plods along the A* route | 0.65 s windup, then a slam around it; step out to dodge |

Damage is ADR-037 power x 10. A foe hunts when it can see you within 26 m (or you are within 9 m, or it was
shot). With no route on foot (another tier, another island) it waits (LOST). `daedalus.FoesHunt 0` stops all
hunting.

**Shields (Halo).** The hero has 100 shield and 100 health. Hits take the shield first, then health. After 4 s
with no damage the shield recharges (50/s), then health (25/s). At zero health he falls: off any Ghost, back to
the player start, full shield and health, Deaths +1. Holding the sword's shield toward a blow takes 80% off it. On a
Ghost, 60% of a hit reaches the rider. HUD: Halo's shield bar at the top centre (orange when low), health under
it (red when low), and a red flush at the screen edge when hit.

**Armor tiers** (held, with avatars and wardrobe): better armor raises `MaxShield` (and later the recharge
delay and rate). The numbers are hero properties already.

## Proven live

Pending the route fix below.

## Held

Armor tiers and pickups, foe packs and spawners per island, sound, foe health bars.
