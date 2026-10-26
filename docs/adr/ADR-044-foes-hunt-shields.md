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

## Proven live (UE 5.8.3, `daedalus.play_scenario`, ADR-045)

- **foes_hunt 6/6** over 901 frames:
  - Routes: the Slime found 11 A* routes and the Knight 10.
  - Closing in: the Slime came 304 cm closer and the Knight 214 cm.
  - Attacks by kind (landed/attacked): Slime 30/30, Shardback 21/22, Wisp 23/26, Knight 18/18.
- **shield 4/4:**
  - 30 damage took only the shield (70/100).
  - 90 more emptied it, and 20 reached health (0/80).
  - It recharged to 100/100 after the delay.
  - A 500 hit made him fall and come back whole.

Found on the way, each one fixed and re-proven:
- **Foes over the void.** SpawnFoes put foes 9 m ahead, which was past the island's edge. It now looks for ground
  at the hero's level.
- **Shardback re-charging.** It charged again every frame after a miss: 34 charges, 0 hits. A miss now leaves it
  winded for 1.8 s.
- **Traces through the ground.** C++ traces with no params ran on complex collision, which the islands don't have,
  so every floor read as a void. The A* never left its start and no foe took a step. Found by running the same
  trace from Python (hit) and from C++ (miss). All world traces now use simple collision.
- **A* every frame.** A foe with no route re-searched every frame: 1,752 searches in a minute. Failed routes now
  wait 1.5 s.

## Held

Armor tiers and pickups, foe packs and spawners per island, sound, foe health bars.
