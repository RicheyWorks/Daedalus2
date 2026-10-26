# Twin Doors C++ core (LAB07, contest gap G04)

Header-only C++17 port of `daedalus-core` `com.daedalus.world.labyrinth.TwinDoors`. The test
regenerates the 10 fixture riddles in `docs/contracts/twin-doors-v1/riddles.twd` byte for byte,
then proves the embedded question solves every seed at both difficulties.

    python engines/unreal/core-test/twin_doors/run_twin_doors_core.py --sanitize
    python engines/unreal/core-test/twin_doors/run_twin_doors_core.py --compiler cl.exe

Tie-in: the Labyrinth archive opens "through reasoning". The guards answer in the same low bells as
the Echo Bell gate (G01), so the player who learned to listen can learn to reason. Doors actor and
TwinDoors/GateArch art come later (unreal-epic-boss, blender-team).
