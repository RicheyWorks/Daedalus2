# DiskSaver Island: Belfry Changes (G565)

A change-ringing puzzle. Ringer Agatha calls the census bells back into rounds.

`tools/streaming/belfry_changes.py` reads a world census (the `tools/world_census` output,
read-only). Every island (up to six) gives the belfry one bell, numbered in label order, and
spare bells pad the ring to five. The tenor is the island bell with the largest RAM cost
(G206 model). A seed jumbles the starting row. Python dev tooling only; nothing runs inside
Unreal.

Each change swaps one or more neighbouring pairs at once, and the pairs may not overlap. You
write a change as the 1-based places where each swapped pair starts: `1+3` swaps places 1-2
and 3-4. The tenor must rest for one change after every change in which it moves. The goal is
for every island bell to ring at lead (place 1) at some point, and for the ring to finish in
rounds (`1 2 3 4 5`).

Par is the fewest changes, found by an exact breadth-first search over (row, island bells led,
tenor resting). The tests check it against an independent layered search. `single_swap_par`
shows how many changes it would take if only one pair could swap at a time.

```
python tools/streaming/belfry_changes.py census.json --seed 7                  # the ring and par
python tools/streaming/belfry_changes.py census.json --seed 7 --changes 1+3,2,1
python tools/streaming/belfry_changes.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `rung` | rounds with every island bell led, in par changes |
| `clattered` | the same, in more changes than par |
| `unfinished` | not in rounds, or an island bell never led |

Exit 2 refuses a place off the ring, overlapping pairs, a change that moves a resting tenor, or a
census with no islands. CI (`.github/workflows/belfry-changes.yml`) runs the tests, including
the real census fixtures, and rings the seed-7 row. Hook: `data/islands/disk-saver/belfry-changes-v1.json`.
