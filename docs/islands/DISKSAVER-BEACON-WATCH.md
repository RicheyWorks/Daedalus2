# DiskSaver Island: Beacon Watch (G505, quest q_beacon_watch)

Streaming-budget regression gate over G206 Census Budget Beacons. G206 lights a beacon
on each island; G253 plans what to unload. This gate keeps the beacons from quietly
getting worse: CI rebuilds the census from the World Census fixtures, prices it with
`census_budget.py`, and compares the result with a committed baseline report.

## What it does
- Reads two `daedalus-census-budget` v1 reports (baseline and current), read-only:
  `worlds[].id`, `fits_all_resident`, `max_resident`, `islands[].slot` and `beacon`.
- Per island (world, slot) and per world it records a finding. These fail the gate:
  `worse` (green < amber < red), `new_hot` (new island arrives amber or red),
  `spill` (world stops fitting resident), `max_resident_drop`.
- These are reported but pass: `better`, `new` (green), `gone`, `unspill`, `world_new`,
  `world_gone`. `budget_changed` / `cost_model_changed` flag a baseline that no longer
  matches the current budget, so a reviewer can tell a re-priced report from a real change.
- Verdict `calm` or `storm`; `--strict` exits 1 on storm.

## Science
- The gate equals an independent brute-force scan over the raw lists on 500 seeded pairs.
- Each worsening step fails; improvements and removals never fail.
- World and island order in the input do not matter; seeded replay gives identical bytes.
- The baseline must equal the real pipeline output (World Census fixtures -> `census_budget.py`),
  so a change to the census format or the cost model shows up in CI.
- Golden fixture: the baseline against the same pipeline at a 17000 KiB RAM budget (storm).

## Daedalus hook
`verdict` (`calm` / `storm`) drives Watchkeeper Isolde's lines, and `findings[]` names
the islands whose lamps dimmed. Config: `data/islands/disk-saver/beacon-watch-v1.json`.

## Updating the baseline
When an island legitimately grows, regenerate the baseline with `census_budget.py` in the
same PR so the change is reviewed. The gate never rewrites it, and `-o` never overwrites.

## Rules
Source only, stdlib only, integers only. Read-only over the census, the G206 report and
config; never edits the G39 Byte Spring quota.
