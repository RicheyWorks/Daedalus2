# LAB06 Calm the Hornbacks (minigame core)

Owner: pythagoras (contest gap G03, 2026-10-19). Code: `daedalus-core/src/main/java/com/daedalus/world/labyrinth/HornbackHerd.java`,
tests: `daedalus-core/src/test/java/com/daedalus/world/labyrinth/HornbackHerdTest.java` (17 cases).

**Story.** A herd of hornbacks thunders through a Labyrinth meadow toward the gate. You cannot outrun them or wall them
off. You can only give them what they need: water to drink and room to breathe. Done right, the stampede becomes a
calm column that walks you through the passage.

**Rules (all deterministic from the seed).**
1. *Water calms.* A stampeding hornback stays wild until it drinks. It smells the next trough on your route within 7 m
   and veers to it. A drink cuts stress by 0.6. Troughs hold a limited number of drinks, and a Kennel `TroughBrew`
   (art-master-flex TONIC1) works as a trough directly via `HornbackHerd.of(brew)`.
2. *Space keeps it calm.* Each neighbour inside 1.6 m beyond two adds stress, and calm animals steer apart. One crowded
   trough can tip the herd back into a stampede, so spread your troughs out.
3. *Panic spreads and fire terrifies.* Wild neighbours and burning cells within 4 m add stress, and the herd veers away
   from flames. An animal that runs into fire is lost.
4. *The ground matters.* The terrain is a `BattlefieldEcology` field (ADR-061): cover slows the herd (speed x
   (1 - 0.5 cover)), and fire from battle events or wildfire changes the safe route.

**Win.** GUIDED when at least 80% of the herd reaches the exit calm and none burn. Otherwise STAMPEDE (or TIMEOUT).

**Daedalus tie-in.** It reuses the battlefield ecology field and the Kennel trough brews, so the same island
vegetation, fires and tonics drive the puzzle. A burning oak wood forces a route around it, which the tests prove.

**Host seam.** `HornbackHerd.run(seed, herd, start, exit, route, terrain, settings, maxSeconds)` returns a `Report`
(outcome, arrived, calmArrived, burned, lost, drinks, stampedeSteps, steps, peakStress). The host owns the actors, trough
props, UI and saves. Unreal later: hornback actors + HornbackTrough prop (UNREAL-QUEUE contest section).