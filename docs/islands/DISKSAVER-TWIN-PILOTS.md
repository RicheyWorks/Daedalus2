# DiskSaver Island: Twin Pilots (G557)

A cooperative planning puzzle for two pilot boats. Pilotmaster Cuthbert has to call at every
berth before the fog closes the harbour.

`tools/streaming/twin_pilots.py` reads a world census (the `tools/world_census` output,
read-only). Every island becomes a berth, and seeded channel buoys fill the chart up to 8 calls.
Channels join the islands of each world in slot order, link each world to the harbour, and add
seeded crossings. Python dev tooling only; nothing runs inside Unreal.

Both boats start in the harbour. On every bell, each boat runs one channel or holds. Between
them they must call at every berth and buoy, and both must end in the harbour. You give one
route per boat, separated by `;`, with berths joined by `>` and the start left out.

Par is the fewest bells for the pair, found by an exact breadth-first search over (boat A,
boat B, calls made). The tests check it against an independent oracle that tries every split of
the calls and tours each half by brute force. `solo_bells` shows the trap: one boat doing the
whole round alone.

```
python tools/streaming/twin_pilots.py census.json --seed 7            # the chart and par
python tools/streaming/twin_pilots.py census.json --seed 7 --plan "alpha:2>harbour;beta:4>harbour"
python tools/streaming/twin_pilots.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `in_step` | every call made, both boats home, in par bells |
| `late` | every call made and both home, in more bells than par |
| `adrift` | a call missed or a boat not home |

Exit 2 refuses an unknown berth, a step with no channel, more than two boats, or a census with
no islands or more than 8. CI (`.github/workflows/twin-pilots.yml`) runs the tests, including
the real census fixtures, and plays the seed-7 chart. Hook: `data/islands/disk-saver/twin-pilots-v1.json`.
