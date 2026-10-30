# DiskSaver Island: Boom Defence (G562)

A small tower-defence game. Boom-master Leopold places two boom posts to stop smuggler skiffs.

`tools/streaming/boom_defence.py` reads a world census (the `tools/world_census` output,
read-only). Every island sends one skiff (up to six, sorted by label, two ticks apart). A
skiff's hull is 4 + its asset count mod 3, plus a seeded 0 or 1. A seed winds a channel across a
7x9 chart from the open sea (west) to the harbour (east) and letters up to twelve post sites
(A-L) beside it. Python dev tooling only; nothing runs inside Unreal.

Each tick, every skiff moves one cell along the channel and the next skiff enters. Then each
post snags the skiff in reach that is furthest along, taking one off its hull. Reach is the
eight cells round the post. A skiff with no hull left sinks, and one that runs off the harbour
end gets through.

Par is the fewest skiffs through over every pair of sites (exhaustive). The tests check it
against an independent simulator. `greedy_through` shows the trap: posts on the sites that
reach the most channel cells.

```
python tools/streaming/boom_defence.py census.json --seed 7              # the chart and par
python tools/streaming/boom_defence.py census.json --seed 7 --posts A,D
python tools/streaming/boom_defence.py census.json --seed 7 --auto
```

Map: `~` sea, `=` channel, `a`-`l` free sites, `A`-`L` posts placed.

| verdict | meaning |
|---|---|
| `watertight` | as few skiffs through as par |
| `leaky` | more through than par, but not all |
| `overrun` | every skiff through |

Exit 2 refuses an unknown site, a site named twice, more than two posts, or a census with no
islands. CI (`.github/workflows/boom-defence.yml`) runs the tests, including the real census
fixtures, and plays the seed-7 chart. Hook: `data/islands/disk-saver/boom-defence-v1.json`.
