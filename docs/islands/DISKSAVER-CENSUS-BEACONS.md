# DiskSaver Island: Census Budget Beacons (G206, quest q_census_beacons)

Follow-up to the DSB 1 island streaming budget planner (ADR-063). The World Census
(`tools/world_census`, Codex) counts asset definitions per world and island slot. It does
not price them. This tool does only the pricing and flagging, read-only over the census
output: it never re-counts, edits or re-validates census inputs beyond the fields it reads.

## What it does
- Reads `census.json` (`daedalus-world-census` v1): `worlds[].id`, `worlds[].islands[].slot`
  and `asset_definitions`.
- Prices each island with the DSB 1 placement ESTIMATE from `dsb_manifest.py`
  (RAM 16384 + 24 KiB per asset definition, disk 4096 + 96 KiB per asset definition). A test pins
  these constants equal to `dsb_manifest.py`, so the two never drift.
- Budgets come from `data/islands/disk-saver/census-budget-v1.json`
  (`ram_budget_kib` 40000, `disk_budget_kib` 32768, `warn_permille` 900).

## Flags and beacons
| Flag | Rule | Beacon |
|---|---|---|
| `ram_over` | island RAM > RAM budget (can never be resident) | red |
| `disk_over` | island disk > disk budget | red |
| `ram_near` / `disk_near` | not over, but cost x 1000 > budget x warn_permille | amber |
| none | fits with headroom | green |

Per world: total RAM/disk, `fits_all_resident` (both totals within budget) and `max_resident`,
the most islands that can be resident at once under the RAM budget (lightest first, which is
optimal for a count; tests check it against a brute-force subset oracle).

## Daedalus hook
The report (`daedalus-census-budget` v1) is a file the game can read: each island's
`beacon` lights its lighthouse lamp green, amber or red, and Harbour Pilot Wren speaks the
matching line from the config. Red lamps tell designers which islands to lighten before
they ship. No Unreal editor work is in this change; the lamp props are a later editor turn.

## Run
```
python -B -m tools.world_census <manifests...> --snapshot-date 2026-10-26 --output-dir OUT
python tools/streaming/census_budget.py OUT/census.json [-o beacons.json] [--strict]
python -B -m unittest tools/streaming/census_budget_test.py -v
```
Exit 0 = report, 1 = `--strict` and a red beacon, 2 = refusal. `-o` never overwrites.
Integers only, stdlib only, deterministic bytes (sorted keys, worlds and slots).
Costs are estimates until islands pin measured numbers in the DSB manifest.