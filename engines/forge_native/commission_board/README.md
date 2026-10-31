# Forgemaster's Commission Board core (Prismheart Crafting + rewards lane)

Each calendar day the Forgemaster on Hephaestus Island posts three commissions for three different ingots.
Delivering one takes the ingots from the Shard Smelter inventory and pays **Forge Marks**; filling all three on one
board pays a board bonus. Everyone sees the same board on the same day.

Rules authority: `commission_board_ref.py` (Python, CPython `random`). `commission_board_golden.txt` pins the header to it.

## Files

| File | What it is |
| --- | --- |
| `DaedalusCommissionBoardCore.h` | Header-only C++17 core: `ValidDate`, `MakeBoard`, `Deliver` |
| `commission_board_ref.py` | Rules reference and golden writer (`--check` verifies the file is current) |
| `commission_board_golden.txt` | 517 dates (498 boards, 19 bad dates), 2,031 scripted deliveries with full state |
| `commission_board_test.cpp` | Replays the golden file, checks 730 days of board shape, edges and refusals |

## Rules

- `MakeBoard(date, &board)`: `date` must be a real `YYYY-MM-DD` (year 0001..9999, Gregorian leap years). Seeds
  `daedalus::pyrandom::PyRandom` (DaedalusPyRandomCore.h) with `"commission|" + date`, draws `sample(range(5), 3)` for
  three different ingots, then per slot a quantity 1..3 (a heartglass ingot is always 1). Pay = quantity x the
  ingot's shard value + 2. Reposting clears progress and keeps the marks balance.
- `Deliver(&inventory, &board, slot)`: checks pointers, slot, already-delivered, valid counts and marks, enough
  ingots, then marks ceiling (999,999,999). Pays the commission plus 5 when it fills the board. Any refusal changes
  nothing.
- Statuses (stable): OK, NULL_POINTER, BAD_DATE, BAD_SLOT, ALREADY_DONE, BAD_INVENTORY, SHORT, OVERFLOW.

Marks are a reward currency, not shard value: nothing turns marks back into shards or ingots, so the Smelter and
Salvage/Reforge conservation property is untouched. Inventory is the Smelter's `ShardInventory`.

## Build and test

```
g++ -std=c++17 -Wall -Wextra -Werror -pedantic commission_board_test.cpp -o t && ./t commission_board_golden.txt
python commission_board_ref.py --check commission_board_golden.txt
```

Mutation-checked: a bigger board bonus and a board-filled check that ignores the current slot both fail the golden replay.

## Lane log

- Item 4 of 5: Commission Board core.
