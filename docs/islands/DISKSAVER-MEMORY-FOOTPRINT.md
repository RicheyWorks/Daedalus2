# Memory Footprint Report (G519, DiskSaver Island, quest q_memory_footprint)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
`tools/streaming/memory_footprint.py` reads a World Census `census.json` (priced with the G206
model: 16384 KiB RAM + 24 per asset definition, 4096 KiB disk + 96 per definition) or an
already-made G206 `census_budget.py` report, read-only, and reports:

- per world: RAM and disk totals and permille of the 40000 KiB RAM / 32768 KiB disk budgets
  (worlds sorted by peak permille), with its top islands and each one's share of the world;
- overall top consumers (islands by RAM, then disk);
- per streaming tool: source bytes of `tools/streaming/*.py` (tests excluded; `--tools-dir ''` skips);
- ranked biggest wins: `unload` an island or `trim` its asset definitions, with KiB freed,
  worlds over budget first, then wins that bring the world back under (`clears`), then most RAM.

A world is over when total RAM or disk is above its budget. Verdict: `light` (peak under
`warn_permille`), `laden` (at or above warn, none over), `overladen` (a world is over).

## CLI
```
python tools/streaming/memory_footprint.py census.json [--top 3] [--wins 10] [--tools-dir DIR] [--json] [--fail-on-over]
```
Exit 0 report; 1 only with `--fail-on-over` and an overladen verdict; 2 refusal. No clock, integers only.

## Daedalus hook
`data/islands/disk-saver/memory-footprint-v1.json`: Quartermaster Bram weighs each island on the
harbour scales and chalks its load (`worlds[].ram_permille`) as a waterline on the hull; the top
three wins are nailed to the gangway as a crate list. The verdict picks his line.
G206 colours lamps, G253 plans unloads, G505 gates changes, G517 tracks drift; Bram ranks the cargo.