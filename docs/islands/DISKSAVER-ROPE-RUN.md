# DiskSaver Island: Rope Run (G564)

A path-drawing puzzle. Ropewalker Theodora lays one mooring rope across the quay through the
best cleats.

`tools/streaming/rope_run.py` reads a world census (the `tools/world_census` output,
read-only). A seed lays out a 5x6 quay with a few crates, a start bollard (`S`) and a dock post
(`D`), and checks that a rope can join them. Every island (up to five) has a brass cleat worth
3 + its asset count mod 3. Every other open square has an iron ring worth 1. Python dev tooling
only; nothing runs inside Unreal.

The rope is laid square by square (`N S E W`). It may never cross itself or go over a crate,
and it must end on the dock post. The score is the grip of every square it covers, start and
dock included.

Par is the best grip over every possible rope, found by an exact search over simple paths and
checked in the tests against an independent recursive search. `greedy_grip` shows the trap:
always heading for the best neighbouring square, which scores 0 if it strands the rope.

```
python tools/streaming/rope_run.py census.json --seed 7               # the quay and par
python tools/streaming/rope_run.py census.json --seed 7 --route EESSW
python tools/streaming/rope_run.py census.json --seed 7 --auto
```

Map: `#` crate, `S` start, `D` dock, digits = grip, `*` rope.

| verdict | meaning |
|---|---|
| `taut` | the rope reaches the dock with par grip |
| `slack` | it reaches the dock with less grip |
| `loose` | it ends short of the dock |

Exit 2 refuses a letter other than N S E W, a step off the quay or into a crate, a step that
crosses the rope, steps after the dock, or a census with no islands. CI
(`.github/workflows/rope-run.yml`) runs the tests, including the real census fixtures, and
plays the seed-7 quay. Hook: `data/islands/disk-saver/rope-run-v1.json`.
