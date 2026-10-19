# LAB08 Folding Maze boss (minigame core)

Owner: pythagoras (contest gap G05, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/labyrinth/FoldingMaze.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/labyrinth/FoldingMazeTest.java` (16 cases).

**Story.** At the Labyrinth's heart the maze itself is the boss. Its mimic walls breathe open and shut, and the corridor
you trusted is gone. The maze is alive but bound by one old law: it may confuse you, never bury you. The exit always
stays reachable, and when a fold would seal you in, the maze restores the way out instead.

**Rules.**
1. The maze is carved by any Daedalus maze-engine generator (`MazeGenerator`: Kruskal's, Growing Tree and the other 23).
   `create(gen, rows, cols, seed, mimics)` picks the mimic walls: half current passages, half solid walls (seeded).
2. `fold(player)`: the background schedule. Each mimic flips with probability 1/2. Opening is always safe. Before any
   close, a breadth-first search proves the player can still reach the exit, and a close that would trap the player is
   **vetoed** (the wall stays open, listed in `Fold.vetoed`).
3. `bossFold(player)`: the boss phase. It closes the open mimic that lengthens your shortest route most, and opens the
   closed mimic that shortens it least, under the same proof. Ties go to the lowest index, so it stays deterministic.
4. Every `Fold` reports what opened, closed and was vetoed, plus your route length afterwards, which the host can show
   as "steps to the exit".

**Proofs in the tests.** Over 300 background folds and 150 boss folds on five seeds, with a wandering player, the
exit is reachable after every fold. Vetoes really happen. The boss lengthens routes more than background folds. Runs
are deterministic, and the maze works with more than one engine generator.

**Daedalus tie-in.** Daedalus began as a maze engine. This turns that engine into a living Labyrinth boss without
copying it, and the veto rule is the realm's "restore an exit without destroying it". Unreal later: WallMimic / Wall4m
actors that rise and sink on `Fold.opened/closed` (UNREAL-QUEUE contest section).