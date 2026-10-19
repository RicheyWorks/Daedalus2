# BEAVER01 Beaver Waters (minigame core)

Owner: pythagoras (contest gap G34, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/BeaverWaters.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/BeaverWatersTest.java` (10 cases).
It writes into the Reactive Battlefield Ecology field (ADR-061): water cells become WETLAND, the "beaver ground" state
that never burns and grows willow carr. So a beaver pond is a firebreak for FIRE01 Fireline Warden (G27) and a
willow nursery for ASH01 Ashfall Regrowth (G20). The beaver is already in the ecology species canon
(`daedalus-core/src/main/resources/com/daedalus/world/ecology/species.tsv`).

## Story (shattered-planet canon)

The arks carried more than seed. In one hold rode a beaver colony, and the families of the regrown fragment have
finally let them out by the spring. Water on a floating island does not stay: the spring runs down the valley and
pours off the edge into the sky in a long white thread. Spring tender Oru wants the valley meadow under water,
because a pond stops fire and willow grows beside it. Herder Bram wants the homestead left dry. The beavers only
want trees.

## Quest `q_beaver_waters`

| Step | Trigger (what the core reports) | NPC line |
| --- | --- | --- |
| 1 The thread | `spring(...)`, `pondCells() == 0` | **Spring tender Oru** (`npc_spring_tender`): "See it fall off the edge? Every drop we lose to the sky is a drop the fire would have hated." |
| 2 First dam | a `dam` returns true | Oru: "They took a pine for that. Every layer costs a tree, so build where the timber is close." |
| 3 Around the ends | the pond stops growing and water runs past a dam end | **Herder Bram** (`npc_ark_herder`): "It is running around the end of your dam. Higher will not help; wider will." |
| 4 Meadow under water | `Outcome.WET` | Oru: "The meadow is a pond. Nothing burns in there, and the willow will come." Reward: `lore_beaver_waters`, `beaver_kit` |
| Too far | `Outcome.FLOODED` | Bram: "Water in the yard! Break a layer, quick." (A `breach` drains it back to wet meadow.) |

## Rules (deterministic, no randomness)

1. **The fragment** is a heightmap in cm (one value per cell of the `BattlefieldEcology` field) with a spring at one cell.
   Its edge drops into the sky, so all water ends up leaving over it.
2. **Water** is steady state and the spring never runs dry. A priority flood from the edge gives every cell its spill
   level, the lowest level at which water there could reach the edge. The spring's water fills the basin it rises
   in up to that level, pours over the lowest rim, runs downhill, fills every basin on its way, and falls off the edge.
   Standing water is a pond (`depthCm > 0`); running water is a stream.
3. **Dams** add `damHeightCm` (60) per layer to a cell, and layers stack (8 per run by default). Each layer fells
   `woodPerDam` pine or oak within `woodReach` (4) cells, nearest first, and the stumps turn to meadow. A stream cell can
   be dammed. Pond cells, the spring and the homestead cannot. A dam that is too short is useless, because the water
   runs around its ends.
4. **Breach** removes one layer. The pond drains to the new level, and drained cells are left as wet meadow.
5. **End**: FLOODED if any water reaches the homestead plot. WET if at least 75% of the target plot is under a pond.
   Otherwise DRY.

## What the tests prove

With no dam, the stream runs down the valley and off the edge. A dam backs up a pond behind it and never below it.
A short dam stops helping, because the water runs around its ends. A wide enough dam floods the target meadow and
leaves the homestead dry. Over-damming drowns the homestead, and a breach drains it back to meadow. Dams cost the
nearest timber, and no timber means no dam. The spring, ponds, the homestead and the layer budget are all refused. The
pond is fireproof WETLAND, so IGNITE does nothing there. The same moves give the same water. Bad input is refused.

## Host seam (Unreal, later)

The heightmap comes from the island landscape, sampled per ecology cell. Show the field via `Dbe.write` and
`UDaedalusEcology` (WETLAND cells drive the water plane and the willow flora). Player or colony orders call `dam/breach`.
`depthCm(i, j)` sets the water plane height and `water(i, j)` places the stream spline. Assets: beaver, dam
segment, pond water plane, and the edge waterfall VFX. The editor binding goes in `BOARD/UNREAL-QUEUE.md`.
