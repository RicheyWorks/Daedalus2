# DiskSaver Island: Tide Lock (G554)

A lock-scheduling puzzle. Lockkeeper Wilhelmina lifts the census fleet through one canal lock.

`tools/streaming/tide_lock.py` reads a world census (the `tools/world_census` output) and the
G206 census-budget config, both read-only. Every island sends one boat whose length is its RAM
cost in the G206 model (`census_budget.island_cost`); a seed gives the queue order and arrival
minutes. The chamber holds boats up to the G206 RAM budget (or `--chamber-kib`), and every
cycle takes `--cycle-min` minutes (default 30). Python dev tooling only; nothing runs inside
Unreal.

Boats go through in arrival order. A plan such as `2,1,3` groups them: the first two together,
then one, then three. A group leaves when its last boat has arrived and the lock is free; each
boat waits from its arrival until its group leaves. Least total waiting wins.

The optimum comes from an exact memoised search over (next boat, minute the lock is free),
checked in the tests against trying every grouping. The greedy "fill the chamber" plan is shown
too, because waiting for a full chamber is often the trap.

```
python tools/streaming/tide_lock.py census.json --seed 7                 # the queue, par and greedy
python tools/streaming/tide_lock.py census.json --seed 7 --plan 1,2,1
python tools/streaming/tide_lock.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `smooth` | the plan's total wait equals the optimum |
| `slow` | a legal plan, but with more waiting than needed |
| `jammed` | sizes do not add up to the queue, or a group overfills the chamber |

CI (`.github/workflows/tide-lock.yml`) runs the tests, including the real census fixtures, and
solves the seed-7 queue. Hook: `data/islands/disk-saver/tide-lock-v1.json`.
