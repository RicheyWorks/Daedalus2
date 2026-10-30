# DiskSaver Island: Last Crate (G549)

A push-your-luck game the dockhands play on slow tides, run by Dockhand Ambrose.

`tools/streaming/last_crate.py` reads a world census (the `tools/world_census` output) and the
G206 census-budget config, both read-only. Every island becomes a crate weighing its RAM cost
in the G206 model (`census_budget.island_cost`). A seed shuffles the crates into a face-down
stack. Each turn you `load` the top crate or `sail`. Go over the hold (default: the G206 RAM
budget, or `--hold-kib`) and the whole load goes overboard. Python dev tooling only; nothing
runs inside Unreal.

| outcome | meaning |
|---|---|
| `full` | you sailed with the best load any stopping point of this stack allowed |
| `light` | you sailed safely, but a later stop would have carried more |
| `overboard` | the hold burst; nothing is carried |

Every turn shows the advisor, which knows only what a player could: the load so far and which
crates are still in the stack, not their order. It reports exact fractions: `bust_chance` for
the next crate, `load_value` (expected KiB if you load one more and then sail, bust counting
as 0), `sail_value`, and `advice`. `--auto` plays the advice.

```
python tools/streaming/last_crate.py census.json --seed 7 --moves load,load,sail
python tools/streaming/last_crate.py census.json --seed 7 --auto --hold-kib 70000
```

The stack depends only on the census snapshot date, the island labels and `--seed`, so a seed
is a shareable challenge. Exit 0, or 2 on a refusal (bad census, unknown move, moves that do
not end with `sail`, an empty stack).

CI (`.github/workflows/last-crate.yml`) runs the tests, including the real census fixtures, and
plays one auto game. Hook: `data/islands/disk-saver/last-crate-v1.json`.
