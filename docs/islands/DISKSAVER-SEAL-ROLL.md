# DiskSaver Island: Seal Roll (G560)

A rolling-cube puzzle. Sealwright Cornelius tips a cube with the harbour seal on one face across
the quay.

`tools/streaming/seal_roll.py` reads a world census (the `tools/world_census` output,
read-only). Up to four islands (sorted by label) each get a chalk mark. A seed lays out a walled
7x7 quay with a few bollards, the marks, a dock square and a start square, and checks that the
quay can be solved. Python dev tooling only; nothing runs inside Unreal.

Each tip rolls the cube one square north, south, east or west (`N S E W`), and the seal face
turns with it: four tips the same way bring it back to the top. A mark is stamped when the cube
comes to rest on it with the seal facing up. Stamp every mark, then finish on the dock.

Par is the fewest tips, found by an exact breadth-first search over (square, seal side, marks
stamped). The tests check it against an independent solver that turns the seal as a 3-D vector.

```
python tools/streaming/seal_roll.py census.json --seed 7                # the quay and par
python tools/streaming/seal_roll.py census.json --seed 7 --tips EENNWS
python tools/streaming/seal_roll.py census.json --seed 7 --auto
```

Map: `#` wall, `a`-`d` marks (capital once stamped), `D` dock, `@` the cube.

| verdict | meaning |
|---|---|
| `true` | every mark stamped and the cube on the dock, in par tips |
| `wobbly` | the same, in more tips than par |
| `off_mark` | a mark unstamped or the cube not on the dock |

Exit 2 refuses a letter other than N S E W, a tip into a wall or bollard, or a census with no
islands. CI (`.github/workflows/seal-roll.yml`) runs the tests, including the real census
fixtures, and plays the seed-7 quay. Hook: `data/islands/disk-saver/seal-roll-v1.json`.
