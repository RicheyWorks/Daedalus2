# DiskSaver: C++17 ports of the minigame cores (G573 batch 1, G574 batch 2)

These are header-only, engine-free C++17 ports of the pure logic of the DiskSaver Python minigames, so a game
build can grade a player's moves without Python. None of them includes Unreal headers or uses UObject,
and none needs exceptions or RTTI: they build with `-fno-exceptions -fno-rtti` and MSVC `/GR-`. Errors come back
as `Error` codes. Any Unreal glue will be a thin separate wrapper later.

| Game | Header (`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/`) | Ported |
|---|---|---|
| G556 Manifest Match | `DaedalusDiskSaverManifestMatchCore.h` | perfect-memory par and plan, turn validation (range/matched/same/over), hits, verdict sharp/matched/unfinished |
| G557 Twin Pilots | `DaedalusDiskSaverTwinPilotsCore.h` | exact two-boat BFS par and routes, one-boat Held-Karp bells, route grading (berth/channel), verdict in_step/late/adrift |
| G558 Quayside Shove | `DaedalusDiskSaverQuaysideShoveCore.h` | push rule, exact BFS par and plan, move validation (letter/clear/blocked), pushes, deadlock check, verdict tidy/shuffled/stuck |
| G559 Sack Chute | `DaedalusDiskSaverSackChuteCore.h` | sowing rule, exact BFS par and plan, nearest-the-hold greedy, move validation (bin/clear/empty), verdict stowed/slow/loose |
| G560 Seal Roll | `DaedalusDiskSaverSealRollCore.h` | tip table, exact BFS par and plan over (cell, seal side, stamped marks), tip validation (letter/wall), verdict true/wobbly/off_mark |
| G561 Channel Dash | `DaedalusDiskSaverChannelDashCore.h` | barge drift (Python modulo, tick reduced mod 9), exact BFS par and plan over (row, col, tick mod 9), move validation (letter/dock/leaves), hit tick, verdict swift/safe/swamped |
| G562 Boom Defence | `DaedalusDiskSaverBoomDefenceCore.h` | tick simulator with fates, exhaustive par over site pairs, most-reach greedy, post parsing (site/twice/many), verdict watertight/leaky/overrun |
| G563 Salvage Sale | `DaedalusDiskSaverSalvageSaleCore.h` | Broker bid rule, exact par search (pass-first tie rule) and bids, win-what-you-can greedy, bid parsing (count/coin, huge bids saturate), verdict shrewd/fair/fleeced |

**Layouts stay in Python.** The seeded layouts use Python's `random`, which the ports do not reimplement. Each core takes the
puzzle as the Python tool laid it out (card pair ids, chart edges, the yard's `draw()` rows, sacks per bin, quay walls/marks/dock/start, barge lanes, channel path/sites/hulls, lot values/coin). Overflow
is guarded by size caps: 64 cards, 12 chart nodes, a 7x7 yard with a 4M-state BFS cap, 8 bins / 24 sacks, 4 seal marks, 8 barge lanes with |velocity| <= 9, 6 skiffs / 12 sites / hull 1000, and 8 lots with value and coin caps.

**Golden files.** `tools/streaming/disksaver_cpp_parity.py` runs each tool's real `play()` path and writes
`engines/unreal/core-test/disksaver_<game>_parity.txt`. The cases are the real `tools/world_census` fixtures under several seeds,
synthetic censuses, and hand-laid edges (an unsolvable corner yard, a disconnected chart, wrap-around chutes, a walled-off dock, a solid barge lane, a chart with no post sites, a sale with no coin), plus
refusals. Each `disksaver_<game>_core_test.cpp` (no framework; shared helpers in `disksaver_parity.h`) asserts every line:
layout, par, plan, and each play's result or refusal. Single-line mutations of the golden files make the tests fail.

    python tools/streaming/disksaver_cpp_parity.py --check
    cd engines/unreal/core-test
    g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -fno-exceptions -fno-rtti -fsanitize=address,undefined \
      -I../DaedalusLink/Source/DaedalusLink/Public disksaver_sack_chute_core_test.cpp -o t && ./t disksaver_sack_chute_parity.txt

CI: three steps in the `engines.yml` mesh-parity job: gcc with ASan/UBSan, clang, and a check that the golden files match the Python tools. The steps loop over every `disksaver_*_core_test.cpp`, so a new batch needs no workflow edit.
Next: G564 Rope Run, G565 Belfry Changes, G566 Tram Shunt, then the earlier games.
