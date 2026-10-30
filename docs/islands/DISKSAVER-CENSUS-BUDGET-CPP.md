# DiskSaver: G206 Census Budget cost model in C++17 (G571)

A header-only, engine-free C++17 port of the G206 Census Budget Beacons cost model
(`tools/streaming/census_budget.py`), so a game build can light island beacons without Python.

- Header: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusCensusBudgetCore.h`
  (namespace `DaedalusCensusBudget`). No Unreal includes, no UObject, no exceptions or RTTI
  (it builds with `-fno-exceptions -fno-rtti` and MSVC `/GR-`). Errors come back as `false`.
  Any Unreal glue goes in a separate thin wrapper later; none is needed now.
- Cost (ESTIMATE, same as `dsb_manifest.py`): RAM 16384 KiB + 24 KiB and disk 4096 KiB + 96 KiB
  per asset definition.
- Budget: the shipped config is 40000 KiB RAM, 32768 KiB disk, warn at 900 permille.
  `ValidBudget` applies the same range checks as `load_budget`.
- `Judge` returns the same flags as `beacon()`: `ram_over`/`disk_over`, and only when nothing is over,
  `ram_near`/`disk_near`. Over means red, near means amber, otherwise green.
  `MaxResident` loads the lightest islands first, and `PlanWorld` returns the world totals,
  `fits_all_resident`, and the beacon counts.
- Edges on the shipped budget: 984 assets is exactly 40000 KiB RAM (not over), 985 is over;
  disk 298 is 32704 KiB (fits), 299 is 32800 KiB (over); the disk warn line is between 264 and 265, the RAM warn line between 815 and 816.
- The port refuses counts above 10^12 (Python ints have no limit) so every product fits in 64 bits.

## Golden outputs

`tools/streaming/census_budget_parity.py` runs the Python tool and writes
`engines/unreal/core-test/census_budget_parity.txt`. It covers the real `tools/world_census` fixtures
(alpha + beta + bindings), seeded synthetic censuses for seeds 1/7/42/206, the edge counts above, and
RAM-only and disk-only spill worlds plus an empty world. Each runs under the shipped, a tight and a
lopsided budget: 27 cases, 108 islands. The seeds are drawn in Python only, so the C++ side needs no RNG.
`census_budget_core_test.cpp` (no framework) replays every line and adds direct edge asserts.

    python tools/streaming/census_budget_parity.py --check   # golden file is fresh
    cd engines/unreal/core-test
    g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -fno-exceptions -fno-rtti \
      -I../DaedalusLink/Source/DaedalusLink/Public census_budget_core_test.cpp -o t && ./t census_budget_parity.txt

CI: three steps in the `engines.yml` mesh-parity job (gcc with ASan/UBSan, clang, parity freshness).
