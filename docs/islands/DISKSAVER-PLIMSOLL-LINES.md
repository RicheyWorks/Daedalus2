# Plimsoll Lines (G522, DiskSaver Island, quest q_plimsoll_lines)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
`tools/streaming/plimsoll_lines.py` looks forward where the other streaming tools look back.
It reads a World Census `census.json` (priced with the G206 model) or an already-made G206
`census_budget.py` report, read-only, and marks for every island how many more asset definitions
(24 KiB RAM + 96 KiB disk each) it can take:

- `to_amber`: before its beacon leaves green (0 if already amber or red);
- `to_red`: before its beacon turns red (0 if already red);
- `to_spill`: before its world can no longer hold every island resident (same for every island
  in the world, since each definition costs the same wherever it lands).

The lines are closed form and are tested equal to a brute-force scan over the G206 `beacon`.
Each world also names its `tightest_slot`.

## Cargo what-if
`--add WORLD:SLOT:N` (repeatable) loads N extra definitions onto existing islands and re-prices
with G206: `afloat` (all green, every world fits), `awash` (some amber), `sunk` (some red, or a world spills).

```
python tools/streaming/plimsoll_lines.py census.json [--add alpha:2:40 ...] [--json] [--fail-on-sunk]
```
Exit 0 report; 1 only with `--fail-on-sunk` and a sunk verdict; 2 refusal. No clock, integers only.

## Daedalus hook
`data/islands/disk-saver/plimsoll-lines-v1.json`: Surveyor Odile paints a white line (`to_amber`)
and a red line (`to_red`) on each hull and a blue line along the harbour wall (`to_spill`). Players
bring her a cargo list; the verdict picks her line before anything is loaded.
