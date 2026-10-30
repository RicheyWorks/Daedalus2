# DiskSaver Island: Watchfires (G555)

A graph puzzle between islands. Firekeeper Leofric lights the ferry chart on storm nights.

`tools/streaming/watchfires.py` reads a world census (the `tools/world_census` output,
read-only). Every island is a landing on the ferry chart. Routes: each world's islands are
chained in slot order, the worlds are joined in a seeded order, and a seed adds one extra
crossing per island, so the chart is always connected. Python dev tooling only; nothing runs
inside Unreal.

A watchfire lights its own island and every island one crossing away. Light the whole chart
with as few fires as possible (a minimum dominating set). Par comes from an exact
branch-and-bound search (pick the first dark island; it or one of its neighbours must burn),
checked in the tests against trying every set. The greedy plan (always light the most new
islands) is shown as the trap.

```
python tools/streaming/watchfires.py census.json --seed 7                  # the chart and par
python tools/streaming/watchfires.py census.json --seed 7 --fires alpha:2,beta:4
python tools/streaming/watchfires.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `blazing` | every island lit with par fires |
| `smoky` | every island lit, more fires than par |
| `dark` | at least one island is unlit (listed) |

Charts are capped at 40 islands. CI (`.github/workflows/watchfires.yml`) runs the tests,
including the real census fixtures, and solves the seed-7 chart. Hook:
`data/islands/disk-saver/watchfires-v1.json`.
