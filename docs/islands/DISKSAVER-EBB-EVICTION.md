# DiskSaver Island: Ebb Tide Eviction (G253, quest q_ebb_eviction)

Follow-up to G206 Census Budget Beacons. G206 says whether a world's islands all fit
resident in the RAM budget. This tool answers the next question: when they do not,
which resident islands should be unloaded first?

## What it does
- Reads a `daedalus-census-budget` v1 report (`census_budget.py` output), read-only:
  `budget.ram_budget_kib`, `worlds[].id`, `worlds[].islands[].slot` and `ram_kib`.
- Config `data/islands/disk-saver/ebb-eviction-v1.json`: `pinned_slots` (home slot 0 is
  never unloaded), `default_weight` (1) and optional per-world `weights` by slot
  (the reload burden of bringing an island back, 1..1000).
- Per world: `need_kib = total_ram - budget`. If `need <= 0` the tide is `slack`. Otherwise it
  finds the set of unpinned islands freeing at least `need` with the least total weight,
  then the fewest islands (`ebb`). If no set is enough, the world is `stranded`.

## Science
- Exact solver: 0/1 knapsack DP over (total weight, count) keeping the most freed RAM.
  Tests check it equals a brute-force oracle over every subset (n <= 16) on 400 seeded cases.
- Greedy baselines are reported beside the optimum: heaviest RAM first, and lowest weight
  first. Pinned counterexamples show each one paying more than optimal.
- Exact edges: freeing exactly `need` is enough; one KiB short is not.
- Seeded replay gives identical bytes; world/island order in the input does not matter.
- Golden fixture: real `tools/world_census` fixtures -> `census_budget.py` -> this plan.

## Daedalus hook
`worlds[].tide` (`slack` / `ebb` / `stranded`) drives Ebb Warden Marlo's lines, and
`worlds[].optimal.unload_slots` is the order the streaming layer casts islands off.

## Rules
Source only, stdlib only, integers only. Read-only over the census, the G206 report and
G206 config; never edits the G39 Byte Spring quota. `-o` never overwrites a file.
