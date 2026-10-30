# DiskSaver Island: Channel Dash (G561)

A timing crossing game. Courier Isadora rows the census dispatches across lanes of drifting
barges.

`tools/streaming/channel_dash.py` reads a world census (the `tools/world_census` output,
read-only). Each island gets a barge lane (up to five, padded to three with spare lanes) across
a 9-cell channel. A seed fills each lane with barges that drift east or west one or two cells a
tick and wrap round, and picks a start column on the near quay and a dock column on the far
quay. It checks that the crossing can be made. Python dev tooling only; nothing runs inside
Unreal.

Each tick Isadora moves `U`, `D`, `L` or `R`, or waits (`.`), and then the barges drift. If a
barge is on her cell after the tick, she is swamped. The quays are always clear.

Par is the fewest ticks to reach the dock, found by an exact breadth-first search over (row,
column, tick mod 9). The barge pattern repeats every 9 ticks. The tests check par against an
independent search that steps real time.

```
python tools/streaming/channel_dash.py census.json --seed 7                # the channel and par
python tools/streaming/channel_dash.py census.json --seed 7 --moves U.UUR
python tools/streaming/channel_dash.py census.json --seed 7 --auto
```

Map: top row the far quay (`D` dock), `#` barge, `~` water, bottom row the near quay, `@` Isadora.

| verdict | meaning |
|---|---|
| `swift` | on the dock in par ticks |
| `safe` | on the dock in more ticks than par |
| `swamped` | hit by a barge (`hit_tick`), or not on the dock yet |

Exit 2 refuses a letter other than U D L R ., a move off the channel, moves after reaching the
dock, or a census with no islands. CI (`.github/workflows/channel-dash.yml`) runs the tests,
including the real census fixtures, and plays the seed-7 channel. Hook: `data/islands/disk-saver/channel-dash-v1.json`.
