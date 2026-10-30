# DiskSaver Island: Tram Shunt (G566)

A railway-shunting (stack sorting) puzzle. Shunter Rosalind marshals the quay tram wagons into
number order.

`tools/streaming/tram_shunt.py` reads a world census (the `tools/world_census` output,
read-only). Every island (up to six) loads one wagon, numbered in label order, and spare
wagons pad the train to six. A seed jumbles the order of the wagons on the inbound line,
reshuffling until the yardman's habit (below) falls short of par. Python
dev tooling only; nothing runs inside Unreal.

There are two dead-end sidings, `A` and `B`. Only the front wagon of the inbound line and the
top wagon of each siding can move. A move is FROM+TO: `inA`, `inB`, `inout`, `AB`, `BA`,
`Aout` or `Bout`. Nothing goes back onto the inbound line, and the outbound line only takes the
next number.

Par is the fewest moves to get the whole train out, found by an exact breadth-first search and
checked in the tests against an independent search, for every train of up to five wagons.
`greedy_moves` shows the yardman's habit: send a wagon out if it can go, otherwise drop the
front wagon onto the siding whose top is the smallest wagon larger than it. It is `None` if the
habit jams the yard.

```
python tools/streaming/tram_shunt.py census.json --seed 7                    # the train and par
python tools/streaming/tram_shunt.py census.json --seed 7 --moves inA,inout,Aout
python tools/streaming/tram_shunt.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `smart` | the train out in par moves |
| `slow` | the train out in more moves than par |
| `jammed` | wagons still in the yard |

Exit 2 refuses a malformed move, an impossible move (empty track, or the wrong number for the
outbound line), moves after the train is out, or a census with no islands. CI
(`.github/workflows/tram-shunt.yml`) runs the tests, including the real census fixtures, and
shunts the seed-7 train. Hook: `data/islands/disk-saver/tram-shunt-v1.json`.
