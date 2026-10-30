# Stray Cargo (G531, DiskSaver Island, quest q_stray_cargo)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
G206 prices islands from their `asset_definitions` counts, and every later streaming tool
(G253, G505, G517, G519, G522, G525, G529) inherits that view. `tools/streaming/stray_cargo.py`
reads the census asset list itself (`census.json`, read-only) and reports what slips past:

| kind | level | meaning |
|---|---|---|
| `dangling` | error | an asset's `island_slot` names no island in its world |
| `duplicate_name` | error | one asset name defined twice in a world |
| `count_mismatch` | error | `assets_without_island` disagrees with the asset list |
| `stray` | advisory | asset with no island; carries its G206 cost once placed (24 KiB RAM / 96 KiB disk) |
| `empty_hull` | advisory | island with no assets, still paying base 16384 KiB RAM / 4096 KiB disk |
| `shared_file` | advisory | the same file defined in several worlds; extra definitions cost 96 KiB disk each |
| `no_realm` | advisory | world with no `realm_id` |

Verdict: `adrift` (any error), `littered` (advisories only), `tidy` (nothing). Totals:
`hidden_cost_kib`, `empty_hull_ram_kib`, `shared_disk_kib`.

## CLI
```
python tools/streaming/stray_cargo.py census.json [--json] [--fail-on littered|adrift]
```
Exit 0 report; 1 only with `--fail-on` and a verdict at least that bad; 2 refusal. No clock.

## Daedalus hook
`data/islands/disk-saver/stray-cargo-v1.json`: Beachcomber Linnet walks the tideline each morning
and lays out every finding as a crate on the sand; her tally of `hidden_cost_kib` is the weight the
Harbour Pilot's scales never see. The verdict picks her line.