# G42: q_forge_temper, the Hephaestus arrival quest

Contest gap G42 (Hephaestus, Oct 19 2026). This is the quest from `data/islands/hephaestus/ISLAND.md` beat 5. Old Keeper Ysolde Anvilward gives it to the smith on arrival: dual-quench a tonic, water the pens through a forge shift, and leave one ark plate stamped with your mark. The quest closes when the Great Forge glows at full strength.

Code: `daedalus-core/src/main/java/com/daedalus/world/forge/ForgeTemperQuest.java`.
Tests: `ForgeTemperQuestTest` (11 tests).

## Steps

| Step | What closes it | Ties in |
|------|----------------|---------|
| ARRIVAL | `drink(source)` at a clean source: HotSpring_Clean, SteamVentCatch, RainCatch_Ash or SaltStill_Basalt. AshWell_Dirty and the QuenchTrough_Forge are refused. | mechanics.json `water.sources` |
| PENS | `waterPen(pen, dl)`: all six troughs (emberhen 5, ashgoat 80, forgeox 120, lavaboar 60, cinderwool 60, vent bees 10 dL) reach their daily need within one forge shift | G24 `ArkDrydock.Life.dlPerDay()` |
| TONIC | `quenchTonic(recipe, DUAL)` with one of the eight dual-cookbook recipes. Magma or spring alone is NOT_DUAL. Tea is UNKNOWN_RECIPE. The first tonic is kept. | mechanics.json herbs, `quench: dual` |
| PLATE | `leavePlate(result)`: a G19 `TemperForge.Result` with `arkPlate` (a dual quench and temper of at least 60) | G19 anvil and quench |
| GLOW | Great Forge Glow at 100 | mechanics.json `balance` |

Steps can be done in any order. Whichever event finishes the last one returns `QUEST_COMPLETE`. `current()` returns the first step not yet done, so the UI can show the keeper's line for it (`keeperLine(step)`). Repeating an event changes nothing and returns `ALREADY_DONE`.

## Great Forge Glow (0 to 100)

The four parts are water running (30), pens producing (30 × pens full / 6), herb beds watered (30 × beds / 3; each bed needs 10 dL) and a dual tonic in the pack (10). The weights are the island's own `balance` block. The test reads mechanics.json and fails if the two drift apart.

## Shift bell

`endShift()` rings the shift bell. If the PENS step isn't finished, every trough empties. If the three beds aren't all watered, the beds dry out. Finished steps stay finished. This is the quest's "through a forge shift" clause.

## Host and engine

The host holds one `Quest` per player and applies events from validated interactions: drink at a water actor, a trough fill, the quench tub, the drydock plate rack. All outcomes are enums, so an Unreal widget can map them to keeper barks without string matching. Editor work isn't needed for the core. A quest-log widget would go on UNREAL-QUEUE.md.

## C++ core (G51)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusForgeTemperQuestCore.h` ports the quest to header-only C++17 with no Unreal types. It contains `ForgeTemperQuest`, `QuestStep`, `QuestOutcome`, `QuestKeeperLine` and `Encode` (the FTQ 1 line), and it uses DaedalusArkDrydockCore.h for the pen needs and TemperForgeCore for plates. `core-test/forge_temper_quest_core_test.cpp` passes 10 checks under MSVC /W4 /WX and g++ -Werror with ASan/UBSan. Its `--write` plays 100 seeded scripts of 60 events each into `forge_temper_quest_parity.txt`. The events are drinks, pens, beds, tonics, plates forged through Judge(IdealRun) and shift bells. `ForgeTemperQuestParityTest` replays the same scripts in Java and compares the two line by line. Java gains `Quest.encode()`.
