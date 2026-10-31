# Salvage and Reforge (Prismheart Crafting + rewards lane), native C++17 core

Break unwanted or duplicate ingots into scrap at a fixed loss, then reforge scrap at full value into the ingot you want. This is the second item of the Crafting + rewards lane (claim 60695). It builds on `../shard_smelter/DaedalusShardSmelterCore.h`.

| File | Role |
| --- | --- |
| `DaedalusSalvageReforgeCore.h` | Header-only, engine-free C++17 core: integer only, `constexpr`, no allocation, exceptions, RTTI, I/O, randomness or Unreal headers |
| `salvage_reforge_ref.py` | Rules authority (Python, reuses `shard_smelter_ref.py`) and golden-vector writer |
| `salvage_reforge_golden.txt` | Golden parity fixture: 407 op scripts, 5,006 ops, every status |
| `salvage_reforge_test.cpp` | Standalone core test |

## Rules

- `ForgeLedger` holds a `ShardInventory` plus a scrap pool (0..999,999,999). Shards are not salvageable or reforgeable; only ingots (slots 5..9) are.
- `Salvage(&l, ingot, count)`: each ingot gives `floor(3 * value / 4)` scrap (glowsteel 3, tidebrass 3, galeiron 2, umbral_alloy 3, heartglass_ingot 11).
- `Reforge(&l, ingot, count)`: each ingot costs its full shard value in scrap (4, 4, 3, 4, 15).
- `Smelt(&l, recipe, batches)` is the Shard Smelter on the ledger's inventory, with its statuses mapped below.
- Status values are stable: `Ok` 0, `NullPointer` 1, `NotAnIngot` 2 (or an unknown recipe), `BadCount` 3, `BadLedger` 4, `Short` 5 and `Overflow` 6. Any refusal leaves the ledger untouched.

## Conservation property

Ledger value is `Value(inventory) + scrap`. Smelt and Reforge keep it equal and Salvage strictly lowers it, so no sequence or loop of operations can gain value. This is checked four ways:

1. A `static_assert` that every ingot salvages for less than its value and reforges for at least its value.
2. Every script in the golden fixture never rises above its starting value.
3. 54,000 single operations over a grid of ledgers: Smelt and Reforge stay equal, and Salvage drops.
4. An exhaustive search of every ledger reachable from four starts by any sequence of operations: 24,116 ledgers, none worth more than its start.

A mutation run (reforge one scrap cheaper) is caught by the static_asserts, by the fixture, and by checks 3 and 4 on their own.

## Build and test

```
python salvage_reforge_ref.py --check salvage_reforge_golden.txt
g++     -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -pedantic -fsanitize=address,undefined salvage_reforge_test.cpp -o t && ./t salvage_reforge_golden.txt
clang++ -std=c++17 -O2 -Wall -Wextra -Wshadow -Werror -pedantic salvage_reforge_test.cpp -o t && ./t salvage_reforge_golden.txt
```

CI: the existing `stable-cores.yml` forge_native step builds and replays this folder. No workflow change is needed.
