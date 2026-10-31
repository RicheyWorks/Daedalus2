# Shard Smelter (Prismheart Crafting + rewards lane), native C++17 core

The forge bench on Hephaestus Island where Prism Shards won in the Prismheart cabinets are smelted into ingots by fixed recipes. This is the first deliverable of the Crafting + rewards lane (`bot-team\PRISMHEART\PLAN.md`, owner hephaestus, claim 60695). Later items are Salvage/Reforge, Quench Window, Commission Board and hallmark tiers.

| File | Role |
| --- | --- |
| `DaedalusShardSmelterCore.h` | Header-only, engine-free C++17 core: integer only, `constexpr`, no allocation, exceptions, RTTI, I/O, randomness or Unreal headers |
| `shard_smelter_ref.py` | Rules authority (Python) and golden-vector writer |
| `shard_smelter_golden.txt` | Golden parity fixture written by the reference (never hand-edited) |
| `shard_smelter_test.cpp` | Standalone core test: replays the fixture row for row, plus properties and edges |

## Shard input

The header defines its own minimal `ShardInventory` (10 `int64_t` counts). It does not include Prism Satchel. Slots 0..4 are the five Prism Shard hues in Prism Satchel order: ember, tide, verdant, gale, umbra. A caller copies the Satchel wallet's counts in and writes the spent counts back out. Slots 5..9 hold ingots. A count must be within 0..999,999,999, the same 9-digit ceiling as a Satchel count.

## Recipes (one ingot per batch)

| Id | Ingot | Inputs per batch | Shard value |
| --- | --- | --- | --- |
| 0 | glowsteel | 3 ember + 1 tide | 4 |
| 1 | tidebrass | 2 tide + 2 verdant | 4 |
| 2 | galeiron | 2 gale + 1 umbra | 3 |
| 3 | umbral_alloy | 1 ember + 3 umbra | 4 |
| 4 | heartglass_ingot | 1 glowsteel + 1 tidebrass + 1 galeiron + 1 umbral_alloy | 15 |

A shard is worth 1, and an ingot is worth exactly its inputs, so a smelt always conserves total value. A `static_assert` checks every recipe against this. Salvage/Reforge will build on this rule and may only lose value.

## API

- `Smelt(&inv, recipe, batches)` smelts in place.
- `MaxBatches(inv, recipe)` returns the largest accepted batch count (0 if none, -1 for a bad recipe or inventory).
- `Value(inv)`, `ValidInventory(inv)` and `StatusName(s)`.
- The tables are `kRecipeTable`, `kValue` and `kMaterialNames`.

Status codes, with stable values, are checked in this order:

| Value | Status | When |
| --- | --- | --- |
| 1 | `NullPointer` | Null inventory pointer |
| 2 | `UnknownRecipe` | Recipe id outside 0..4 |
| 3 | `BadBatch` | Batches outside 1..1,000,000 |
| 4 | `BadInventory` | A count below 0 or above 999,999,999 |
| 5 | `Short` | Not enough of some input for every batch |
| 6 | `Overflow` | An output would pass the count ceiling |

`Ok` is 0. Any refusal leaves the inventory exactly as it was.

## Build and test

```
python shard_smelter_ref.py --check shard_smelter_golden.txt
g++     -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -pedantic -fsanitize=address,undefined shard_smelter_test.cpp -o t && ./t shard_smelter_golden.txt
clang++ -std=c++17 -O2 -Wall -Wextra -Wshadow -Werror -pedantic shard_smelter_test.cpp -o t && ./t shard_smelter_golden.txt
cl /std:c++17 /W4 /WX /EHsc shard_smelter_test.cpp && shard_smelter_test.exe shard_smelter_golden.txt
```

CI: the existing `stable-cores.yml` forge_native step (#1131) builds and replays every `engines/forge_native/<name>/` under g++ and clang++ with ASan/UBSan. No workflow change is needed. The header alone also builds with `-fno-exceptions -fno-rtti` and strict conversion warnings.

## Lane log

1. **Smelter core.** Five recipes, refusals that never change the inventory, exact `MaxBatches`, and value conservation. The fixture holds 2,559 smelt rows (746 ok, 1,813 refused across every status). Properties cover 12,000 grid smelts. A mutation run (an off-by-one in the overflow or short check) is caught by the fixture.
