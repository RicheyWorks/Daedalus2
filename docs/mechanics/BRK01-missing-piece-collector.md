# BRK01 Missing Piece Collector (contest gap G16)

Owner: hephaestus. Core: `daedalus-core/src/main/java/com/daedalus/world/bricks/AssemblyRepair.java`, tests in `AssemblyRepairTest.java`. Source only; the Unreal binding waits in BOARD\UNREAL-QUEUE.md.

## Story tie-in
The Unmaker scattered the Bricks airfield's machines across the baseplate (BRICK-CAST.md story proposal). The Missing Piece Collector gathers the parts, PocketBot points at candidates, and the player chooses which piece seats in which slot. Restoring the **Brick Plane** opens the airfield, so the Bricks world reaches its sky gate by air (BricksOps runway and hangar berth on gate 0's line). The **Hover Cart** gives accessible ground travel but never opens the gate.

Forge tie-in (the Hephaestus lane): every piece carries wear, and a fit is graded like a temper, `quality = 1000 - 10 * wear` per-mille:

| Grade | Quality | Wear |
|---|---|---|
| PERFECT | >= 850 | 0-15 |
| SNUG | >= 600 | 16-40 |
| LOOSE | >= 300 | 41-70 |
| REJECT | below 300, or the wrong stud shape | 71-100 |

The **Kiln** (the kiln baker's workshop) re-bakes a collected, unfitted piece once, removing 30 wear, with 3 charges per session, so a cracked spare can still be saved. A machine's receipt reports its weakest fit, mean quality, pieces used, rejects and Kiln uses.

## Rules (host-authoritative)
- `AssemblyRepair.scatter(seed)` is pure data. It places one genuine piece per slot (wear 0-60, always at least LOOSE), a spare for about half of the slots (wear 40-100), and 6 decoys whose shapes no slot takes. Every piece lies on a free, unprotected cell on the baseplate top, never the obby, spawn or runway, so no player build or deed is touched.
- A `Session` collects a piece once, within 3 cubes horizontally and 2 vertically. A piece is consumed by exactly one slot, a REJECT consumes nothing, and a slot takes one piece.
- PocketBot `hints(slot, from)` lists uncollected pieces of the slot's shape, nearest first. It cannot see wear; choosing a piece is the player's job.
- `receipt(machine)` is the objective gate. `restored` is true only when every slot seats a piece; `skyGateOpen` is true only for the plane.

## Tests
`AssemblyRepairTest`: 11 tests. Every one of 300 seeds is solved for both machines, the scatter is seeded, pieces stay off protected and build cells, decoys never fit, the grade bands hold, and the reach, collect-once, consume-once, slot-filled and reject rules hold, along with Kiln charges and re-bakes, PocketBot ordering, and the gate.

## Unreal later (UNREAL-QUEUE)
Bind the scatter to the brick kit's salvage bin, repair bay and kiln props, show the PocketBot highlight, and swap the plane at the hangar berth from wreck to whole when `skyGateOpen` is true.
