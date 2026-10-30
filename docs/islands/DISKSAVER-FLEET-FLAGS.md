# Fleet Flags (G533, DiskSaver Island, quest q_fleet_flags)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
Every earlier streaming tool (G206 through G531) works per world or per island.
`tools/streaming/fleet_flags.py` reads a World Census `census.json` (read-only), prices it with
G206 `census_budget.py`, and rolls the budget up by realm (worlds with no `realm_id` form the
unrealmed group, id `null`, listed first):

- worlds, islands, asset definitions, RAM/disk totals;
- beacon counts and spilling worlds;
- the heaviest world (most RAM, then disk, then id);
- a realm `flag`: red (any red island or spilling world), amber (any amber island), else green.

It checks the census `realms[]` tallies (`worlds`, `islands`, `asset_definitions`) against the
worlds list: each disagreement, each realm missing a row and each row naming a realm with no
worlds is a `tally_mismatch`.

Verdict: `fair` (all green), `signal` (some amber), `distress` (some red flag).

## CLI
```
python tools/streaming/fleet_flags.py census.json [--config CFG] [--json] [--fail-on-distress]
```
Exit 0 report; 1 only with `--fail-on-distress` and a distress verdict or any tally mismatch; 2 refusal.

## Daedalus hook
`data/islands/disk-saver/fleet-flags-v1.json`: Signal Yeoman Marisol hoists one flag per realm on
the signal tower (`realms[].flag`), marks each squadron's flagship (`heaviest_world`) and runs up a
query pennant for each tally mismatch. The verdict picks her line.
