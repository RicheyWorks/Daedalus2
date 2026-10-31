# Shoal Lure (shoal_lure)

Prismheart cabinet, owner prism-shard-dev (PLAN.md parked item "Shoal Lure", claimed Oct 31, 2026, link 64594).
Source only: Python rules (`tools/minigames/shoal_lure.py`), header-only C++17 core
(`DaedalusShoalLureCore.h`), parity fixture `engines/unreal/core-test/shoal_lure_parity.txt`
(`tools/minigames/shoal_lure_parity.py`, checked by `shoal_lure_core_test.cpp` in CI). No cabinet, assets or editor
work yet; not in Fair Par, Satchel or the catalog until those owners add it.

## Play

```
python tools/minigames/shoal_lure.py --play --seed 1 --difficulty normal
```

1. The Skiff (S) sits in the middle of the top row. Each cell has a current (^ > v <).
2. `n` `e` `s` `w` move the lure one cell: 1 stamina, 2 if that cell's current flows straight back at you.
3. `net` catches the prism-fish under the lure (hues a, b, c).
4. Swimming onto an umbra eel (X) scatters the whole shoal.
5. `dock` at the Skiff banks the shoal and ends the round. Same-hue fish netted one after another chain: a run of k
   scores 1 + 2 + .. + k. Bank at least the target to win; stamina left adds to a win's score.
6. If a move leaves less stamina than the swim home, the line snaps and the round is lost. `dock` before any move
   is refused.

| difficulty | grid | fish | eels | hues | stamina | target |
|---|---|---|---|---|---|---|
| easy | 5x5 | 5 | 2 | 2 | 24 | 60 % of best |
| normal | 6x6 | 6 | 3 | 3 | 26 | 75 % of best |
| hard | 7x7 | 7 | 5 | 3 | 28 | 85 % of best |

The target comes from the exact best trip (every netting order is searched). The demo and `hint` play the best
score (shoal value + stamina left), not just the biggest shoal. Saves are checked on load: grid, fish, eels,
stamina against moves, netted fish, best and target, and the score is recomputed.
