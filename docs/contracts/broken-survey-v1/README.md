# Broken Survey v1 — LAB04

The Labyrinth archive has two water-damaged surveys of the same corridors. An
archive keeper asks the player to compare the sketches, check the actual passages,
and carry a corrected route to the exit. Both scribes missed a different passage;
preserving their work and reconciling it restores the archive instead of erasing it.

`BrokenSurvey.generate(rows, cols, seed)` reuses RecursiveBacktrackerGenerator and
BfsSolver. Each dimension is 2–64. Start is (0,0), goal is (rows-1,cols-1). Identical
version/dimensions/seed produces identical maze, route and surveys. Version 1 uses
generator id `recursive-backtracker` and its existing seed mapping.

Each immutable survey lists every interior east/south edge exactly once, in row
order (east then south), with an `open` flag. Exterior edges are always walls.
Exactly one true route edge is falsely closed in each survey, at distinct positions.
Both maps are individually unsolvable; their union recovers the actual passages.
Comparing maps therefore reveals disputed corridors without inventing a passage.
This first difficulty tier has omissions only, not false openings or moving walls.

`solution()` and `truthSnapshot()` are **host-only answer/proof accessors**. Never
include these in a player map payload. The snapshot is a defensive copy; survey
and route lists are immutable. Independently reconstruct a grid or inspect both
directions of each route edge to check the proof. No alternative maze engine exists.

`verify(route)` checks a bounded, simple start-to-goal path against actual truth:
missing/oversized routes, null/outside cells, repeated cells, wrong endpoints,
nonadjacent steps and wall crossings are rejected in that order. It is pure and
replay-safe: repeated accepted routes return VALID without rewards or side effects.
It does not accept a map's claimed opening as authority. Host integrations must
bind the seed/version/dimensions to their puzzle instance; a path is not a signed
receipt, ownership check or shared activity reward.

The class has no networking, persistence, economy, UI or native actors. Unreal map
props, comparison UI, field inspection and quest/result bindings are later work for
their owners. Suggested art: two worn survey sheets and an archive survey table.
Focused tests cover seed extremes, smallest/largest bounds, reconstruction with
existing BFS, each map's corruption, exterior walls, defensive copies, invalid
routes, and replay. Test execution results are reported separately from this contract.
