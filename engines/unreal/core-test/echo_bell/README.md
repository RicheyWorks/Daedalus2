# Echo Bell C++ core (LAB03, contest gap G01)

Header-only C++17 port of `daedalus-core` `com.daedalus.world.labyrinth.EchoBellGate`.
The Java test writes/pins `docs/contracts/echo-bell-v1/peals.ebg`; this test regenerates the
same 20 peals (5 seeds x difficulty 0-3) and requires byte-identical EBG 1 text, then checks
ear rules (146.832-360 Hz, passing notes at gain 0.3) and the timing judge.

    python engines/unreal/core-test/echo_bell/run_echo_bell_core.py --sanitize
    python engines/unreal/core-test/echo_bell/run_echo_bell_core.py --compiler cl.exe

Tie-in: "Listen to the maze before trusting a map". Each bell's echo returns
200 + 70 ms per corridor cell, so a player who listens learns how deep the maze runs.
Echo Crickets (assist) widen the window by half. A bell actor in the editor comes later.
