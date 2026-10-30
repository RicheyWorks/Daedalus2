# DiskSaver Island: Fleet Soundings (G551)

A daily solitaire-battleship puzzle. The fleet moored in fog; Tugmaster Ignatius has only his
soundings.

`tools/streaming/fleet_soundings.py` reads a world census (the `tools/world_census` output,
read-only). Every island sends one ship whose length comes from its cargo: 0 asset definitions
-> 1, 1-9 -> 2, 10-99 -> 3, 100+ -> 4. A seed picks the fleet (at most 12 hull cells) and moors
it in a 6x6 or 7x7 anchorage. Python dev tooling only; nothing runs inside Unreal.

Rules: ships are straight, horizontal or vertical; no two ships touch, not even diagonally; each
row and column holds exactly its sounding of hull cells; revealed cells must match.

Fair by construction: an exact backtracking solver (checked against brute force in the tests)
counts solutions, and the generator reveals a cell where two solutions disagree until exactly
one remains.

```
python tools/streaming/fleet_soundings.py census.json --seed 7              # the puzzle
python tools/streaming/fleet_soundings.py census.json --seed 7 --solution   # the chart
python tools/streaming/fleet_soundings.py census.json --seed 7 --check mine.txt
```

In the puzzle view `?` is unknown, `#` a sure hull cell, `~` sure water. A grid file has one
line per row with `#` for hull and `.` for water.

| verdict | meaning |
|---|---|
| `charted` | every rule and clue holds (the unique solution) |
| `short` | the fleet is moored legally, but a sounding or hint disagrees |
| `reefed` | a rule is broken: wrong size or symbols, bent or touching ships, or not the fleet |

CI (`.github/workflows/fleet-soundings.yml`) runs the tests, including the real census fixtures,
and prints the seed-7 puzzle. Hook: `data/islands/disk-saver/fleet-soundings-v1.json`.
