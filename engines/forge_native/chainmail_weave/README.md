# Chainmail Weave (original Prismheart minigame, hephaestus)

A link puzzle in the Hephaestus Island armory. The Forgemaster hands you a torn mail shirt: a 7x7 grid of rings, some
already rusted through. Place links one at a time to join the **left edge to the right edge** with orthogonally
adjacent links before your link budget runs out. Every link that does not finish the weave lets rust spread to one
more ring, so the cheapest path today may be gone next turn.

Rules authority: `chainmail_weave_ref.py` (Python, CPython `random`). `chainmail_weave_golden.txt` pins the C++ header to it.

## Files

| File | What it is |
| --- | --- |
| `DaedalusChainmailWeaveCore.h` | Header-only C++17 core: `Game(seed)`, `Place`, `Demo`, `Score`, plus constexpr `Crossing` / `DemoCell` / `Joined` |
| `chainmail_weave_ref.py` | Rules reference and golden writer (`--check` verifies the file is current) |
| `chainmail_weave_golden.txt` | 308 seeded rounds, 2,897 placements (demo, random and mixed players, bad moves included) |
| `chainmail_weave_test.cpp` | Replays the golden file (full grid, budget, state, loss reason, score and demo move after every placement), tampered-fixture self-test, invariants, property checks, edges |

## Rules

- `Game(seed)`: PyRandom (DaedalusPyRandomCore.h) seeded `"chainmail|" + seed` draws 9 rust rings (repeats allowed).
  If rust blocks every crossing it redraws, up to 20 times, then falls back to a clean grid. Budget = cheapest
  crossing (empty rings still to link) + slack: easy 4, normal 3 (default), hard 2. Difficulty changes only the
  budget; the grid and the rust stream are the same for one seed.
- `Place(cell)` (row-major 0..48): `BAD_CELL` off the grid, `OCCUPIED` on rust or a link, `GAME_OVER` after the
  round ends; these take no turn and change nothing. `OK` places a link and spends 1 budget. If links now join the two
  edges the round is **WON**. Otherwise rust spreads to one seeded empty ring, and the round is **LOST** when the
  cheapest crossing is gone or costs more than the budget left.
- Score on a win: 10 + 10 x budget left (0 on a loss).
- `Demo()`: the chokepoint ring on a cheapest crossing (the hint and the replay bot; see iteration 4). `PathCells()` gives the whole crossing.

Balance (2,000 seeds, Python reference): the demo wins 90.6 % (86.5 % before iteration 4); a player who follows the hint 60 % of the time and
plays a random ring otherwise wins 47 %. Budgets run 10..12.

Integer only; the grid logic is constexpr and allocation-free; no exceptions, RTTI, I/O or Unreal headers.

## Build and test

```
g++ -std=c++17 -Wall -Wextra -Werror -pedantic chainmail_weave_test.cpp -o t && ./t chainmail_weave_golden.txt
python chainmail_weave_ref.py --check chainmail_weave_golden.txt
```

Mutation-checked: a larger slack and rust drawn from the wrong end of the empty list both fail the golden replay;
two static_asserts pin the empty-grid cost and a full rust wall.

## Iteration log

1. **Loss reason.** `LossReason` (NONE, OUT_OF_LINKS, BLOCKED) and `Game::Reason()`, so the result screen can say
   "rust cut every path" vs "ran out of links". Added to the Python reference and the golden file (column after the
   state); the test checks a reason is set exactly when the round is lost. Golden: 15 blocked, 151 out-of-links losses.
2. **Property checks.** Refusals (off-grid, occupied) interleaved with every demo move leave the grid, budget and
   outcome identical over 200 rounds, so a refusal never draws randomness. Over 12,210 single-ring changes, a link
   lowers the cheapest crossing by at most one, rust never lowers it, and the demo ring always lowers it.
3. **Fixture self-test.** The replay is now a function over a stream; five tampered copies of the golden file (a grid
   cell, a status, a loss reason, a trailing token, an unknown row) must each be rejected.
4. **Chokepoint hint.** `Demo()` now picks, among empty rings on a cheapest crossing, the one whose rusting would
   raise the cheapest crossing most (a ring whose loss blocks every crossing counts highest), earliest row-major on
   ties, instead of simply the earliest. Measured on 2,000 seeds (Python reference): the demo's win rate rises from
   86.5 % to 90.6 % and its average score from 29.4 to 30.4; 923 of the 1,000 invariant rounds (was 878). Python
   reference first, golden regenerated from it.
5. **Hint path.** `PathCells(grid, out)` returns one cheapest crossing in path order for the hint glow
   (deterministic smallest-cost-first search with predecessors; 0 when rust cuts every crossing). The test checks
   2,241 paths: left edge to right edge, adjacent steps, no rust, and exactly `Crossing()` empty rings.
6. **Stricter build and compile-time hint check.** Clean under -Wnull-dereference -Wdouble-promotion -Wformat=2
   -Wcast-align -Wextra-semi -Wduplicated-cond -Wlogical-op on top of the earlier flags (test and header alone).
   A static_assert pins the hint on a one-gap rust wall: it takes a ring whose loss blocks the crossing (cell 23)
   where the old rule took cell 21, and `PathCells` threads the gap.
7. **Difficulty.** `Game(seed, Difficulty)` with easy / normal / hard = slack 4 / 3 / 2 (normal is the old game,
   unchanged), `ParseDifficulty` (strict names) and `SlackFor`. Measured on 1,000 seeds with the chokepoint hint:

   | Difficulty | Slack | Demo wins | 60 % hint-follower | 30 % hint-follower |
   | --- | --- | --- | --- | --- |
   | easy | 4 | 92.0 % | 63.3 % | 15.2 % |
   | normal | 3 | 89.1 % | 49.0 % | 7.7 % |
   | hard | 2 | 83.9 % | 34.3 % | 3.0 % |

   (More rust, 12 draws instead of 9, mostly lowered the demo, so the rust count stays 9.) The golden file now
   cycles easy / normal / hard per round (`S <difficulty> <len> <seed>`); the test checks that difficulty changes
   only the budget and that a tampered difficulty is rejected.
8. **Copies and rules-side self-test.** A round copied mid-play continues exactly like the original (the PyRandom
   stream is copied too; needed for save and rewind), checked over 300 seeds. `chainmail_weave_ref.py --selftest`
   runs the same properties on the Python authority over 200 rounds: refusals change nothing and draw no
   randomness, link / rust / hint cost moves, loss reason iff lost, difficulty changes only the budget.
