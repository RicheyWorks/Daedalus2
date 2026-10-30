# DiskSaver: C++17 ports of the minigame cores (G573 batch 1)

These are header-only, engine-free C++17 ports of the pure logic of four DiskSaver Python minigames, so a game
build can grade a player's moves without Python. None of them includes Unreal headers or uses UObject,
and none needs exceptions or RTTI: they build with `-fno-exceptions -fno-rtti` and MSVC `/GR-`. Errors come back
as `Error` codes. Any Unreal glue will be a thin separate wrapper later.

| Game | Header (`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/`) | Ported |
|---|---|---|
| G556 Manifest Match | `DaedalusDiskSaverManifestMatchCore.h` | perfect-memory par and plan, turn validation (range/matched/same/over), hits, verdict sharp/matched/unfinished |
| G557 Twin Pilots | `DaedalusDiskSaverTwinPilotsCore.h` | exact two-boat BFS par and routes, one-boat Held-Karp bells, route grading (berth/channel), verdict in_step/late/adrift |
| G558 Quayside Shove | `DaedalusDiskSaverQuaysideShoveCore.h` | push rule, exact BFS par and plan, move validation (letter/clear/blocked), pushes, deadlock check, verdict tidy/shuffled/stuck |
| G559 Sack Chute | `DaedalusDiskSaverSackChuteCore.h` | sowing rule, exact BFS par and plan, nearest-the-hold greedy, move validation (bin/clear/empty), verdict stowed/slow/loose |

**Layouts stay in Python.** The seeded layouts use Python's `random`, which the ports do not reimplement. Each core takes the
puzzle as the Python tool laid it out (card pair ids, chart edges, the yard's `draw()` rows, sacks per bin). Overflow
is guarded by size caps: 64 cards, 12 chart nodes, a 7x7 yard with a 4M-state BFS cap, and 8 bins / 24 sacks.

**Golden files.** `tools/streaming/disksaver_cpp_parity.py` runs each tool's real `play()` path and writes
`engines/unreal/core-test/disksaver_<game>_parity.txt`. The cases are the real `tools/world_census` fixtures under several seeds,
synthetic censuses, and hand-laid edges (an unsolvable corner yard, a disconnected chart, wrap-around chutes), plus
refusals. Each `disksaver_<game>_core_test.cpp` (no framework; shared helpers in `disksaver_parity.h`) asserts every line:
layout, par, plan, and each play's result or refusal. Single-line mutations of the golden files make the tests fail.

    python tools/streaming/disksaver_cpp_parity.py --check
    cd engines/unreal/core-test
    g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -fno-exceptions -fno-rtti -fsanitize=address,undefined \
      -I../DaedalusLink/Source/DaedalusLink/Public disksaver_sack_chute_core_test.cpp -o t && ./t disksaver_sack_chute_parity.txt

CI: three steps in the `engines.yml` mesh-parity job: gcc with ASan/UBSan, clang, and a check that the golden files match the Python tools.
Next batches cover G560 to G566, then the earlier games.
