# Quench Window core (Prismheart Crafting + rewards lane)

The finishing step at the Hephaestus Island forge. A piece leaves the fire and cools tick by tick; the player
quenches it at one tick. Above the temper band it stays **Soft**, inside it is **Tempered**, within 10 of the band's
middle it is **Perfect**, and below the band it **Cracks**. The curve is seeded, so a daily or shared seed gives every
player the same window.

Rules authority: `quench_window_ref.py` (Python, CPython `random`). `quench_window_golden.txt` pins the C++ header to it.

## Files

| File | What it is |
| --- | --- |
| `DaedalusQuenchWindowCore.h` | Header-only C++17 core: `MakeCurve`, `Grade`, `BestTick` |
| `quench_window_ref.py` | Rules reference and golden writer (`--check` verifies the file is current) |
| `quench_window_golden.txt` | 608 seeded curves, every tick graded (7,904 grades) |
| `quench_window_test.cpp` | Replays the golden file, checks curve invariants and grading edges |

## Rules

- `MakeCurve(seed)` seeds `daedalus::pyrandom::PyRandom` (DaedalusPyRandomCore.h) with `"quench|" + seed` and draws,
  in order: start heat 900..1000, then 12 cooling steps of 40..80 each, then the band low 521..601 (band high = low + 90).
- Every curve starts above the band and ends below it, and the band (90) is wider than any one step (80), so every
  curve has at least one tick inside the band. Three `static_assert`s pin this.
- `Grade(curve, tick, &out)` for tick 0..12: heat > high is Soft, heat < low is Cracked, |heat - middle| <= 10 is
  Perfect, otherwise Tempered. A tick outside 0..12 returns `BadTick` and leaves `out` untouched.
- `BestTick(curve)` is the earliest tick closest to the band middle.

`Grade` and `BestTick` are constexpr and allocation-free; only `MakeCurve` touches PyRandom. No exceptions, RTTI,
I/O or Unreal headers.

## Build and test

```
g++ -std=c++17 -Wall -Wextra -Werror -pedantic quench_window_test.cpp -o t && ./t quench_window_golden.txt
python quench_window_ref.py --check quench_window_golden.txt
```

Mutation-checked: making each cooling step one hotter fails the golden replay, and moving the band base back to 520
trips the "ends below the band" static_assert.

## Lane log

- Item 3 of 5: Quench Window core.
