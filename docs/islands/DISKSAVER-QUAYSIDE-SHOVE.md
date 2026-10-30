# DiskSaver Island: Quayside Shove (G558)

A crate-pushing puzzle. Yardmaster Hamish must shove the census crates onto their berth marks.

`tools/streaming/quayside_shove.py` reads a world census (the `tools/world_census` output,
read-only). The up to three islands with the largest RAM cost (G206 model,
`census_budget.island_cost`) each ship one crate. A seed lays out a walled 7x7 yard with a few
bollards and one chalk mark per crate. It then scatters the crates by pulling them backwards
off the marks, so every yard can be cleared. Python dev tooling only; nothing runs inside Unreal.

Each step moves Hamish up, down, left or right (`U D L R`). Walking into a crate pushes it one
cell if the cell beyond is free. He can never pull a crate, and he can only push one at a time.
Par is the fewest steps to put every crate on a mark, found by an exact breadth-first search
and checked in the tests against an independent layered search. A `stuck` result also reports
`deadlocked`: whether the yard can no longer be cleared from that position.

```
python tools/streaming/quayside_shove.py census.json --seed 7               # the yard and par
python tools/streaming/quayside_shove.py census.json --seed 7 --moves RRUL
python tools/streaming/quayside_shove.py census.json --seed 7 --auto
```

Map: `#` wall, `.` mark, `$` crate, `*` crate on a mark, `@` Hamish, `+` Hamish on a mark.

| verdict | meaning |
|---|---|
| `tidy` | every crate on a mark in par steps |
| `shuffled` | every crate on a mark in more steps than par |
| `stuck` | crates still off the marks (`deadlocked` says whether the yard is lost) |

Exit 2 refuses a letter other than U D L R, a blocked step, steps after the yard is clear, or a
census with no islands. CI (`.github/workflows/quayside-shove.yml`) runs the tests, including
the real census fixtures, and plays the seed-7 yard. Hook: `data/islands/disk-saver/quayside-shove-v1.json`.
