# Hallmark Tiers core (Prismheart Crafting + rewards lane)

The stamp a finished piece earns at the Hephaestus Island forge. **Cosmetic only**: a hallmark picks a stamp tier
and a finish for display; it never changes counts, shard value, Forge Marks or any other gameplay number.

Rules authority: `hallmark_tiers_ref.py`. `hallmark_tiers_golden.txt` pins the header to it.

## Inputs (landed systems, no placeholder needed)

Prism Satchel's progression and Fair Par are both on main, so the hallmark reads them directly:

| Input | Source on main | Values |
| --- | --- | --- |
| `seal` | `DaedalusPrismSatchelCore.h`: `Satchel::SealsByGame[game]` (best Warden seal) | `SealIndex` 0 none .. 6 heartglass |
| `par` | `DaedalusPrismFairParCore.h`: `prismpar::TierOf(row, won, score)` | `Tier` 0 none, 1 bronze, 2 silver, 3 gold |
| `quench` | `../quench_window/DaedalusQuenchWindowCore.h`: `Grade(...)` | `Outcome` 0 soft, 1 tempered, 2 perfect, 3 cracked |

The header takes plain ints, so it does not compile those cores in. `hallmark_tiers_test.cpp` includes all three
real headers, static_asserts that the numbering matches, and stamps a hallmark from a real `Satchel::Record` and a
real Fair Par row.

## Rules

`Stamp(seal, par, quench, &out)`:

- A cracked quench takes no stamp (`NONE`).
- Otherwise the par tier gives `PLAIN`, `BRONZE`, `SILVER` or `GOLD`, capped at `BRONZE` for a soft quench and
  `SILVER` for a tempered one.
- `GOLD` with a perfect quench and a heartglass seal becomes `PRISM`.
- The finish is the seal hue (`none`, `ember`, `tide`, `verdant`, `gale`, `umbra`, `heartglass`).
- Out-of-range inputs return `BAD_SEAL`, `BAD_PAR` or `BAD_QUENCH` and leave `out` unchanged.

A `static_assert` proves the stamp is monotone: better par, seal or quench never gives a worse stamp.

## Build and test

```
g++ -std=c++17 -Wall -Wextra -Werror -pedantic hallmark_tiers_test.cpp -o t && ./t hallmark_tiers_golden.txt
python hallmark_tiers_ref.py --check hallmark_tiers_golden.txt
```

The golden file covers every input, valid and not (324 rows, 112 stamped). Mutation-checked: loosening the soft cap
fails the golden replay, and reversing the par order trips the monotone static_assert.

## Lane log

- Item 5 of 5: Hallmark tiers. Lane complete: Smelter, Salvage/Reforge, Quench Window, Commission Board, Hallmarks.
