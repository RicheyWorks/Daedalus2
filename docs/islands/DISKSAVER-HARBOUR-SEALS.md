# Harbour Seals (G525, DiskSaver Island, quest q_harbour_seals)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
Committed G206 `census_budget.py` reports (the G505 Beacon Watch baseline, examples, hand-offs
between bots) silently go stale when the World Census or the budget config changes.
`tools/streaming/harbour_seals.py` reads a `census.json`, a G206 report and the current G206
config (all read-only) and seals the report:

| verdict | meaning |
|---|---|
| `unsealed` | the report names no `census_sources`, so it cannot be traced |
| `stale` | `census_sources` or `snapshot_date` differ from the census, or the budget differs from the current config |
| `tampered` | same census and budget, but a fresh G206 re-price does not reproduce the report |
| `sealed` | the fresh re-price reproduces the report exactly |

Differences are listed by path, with worlds keyed by id and islands by slot, so reordering is
not a difference but a changed number, a type change (int vs float), a missing or extra field is.

## CLI
```
python tools/streaming/harbour_seals.py census.json report.json [--config CFG] [--json] [--fail-on-broken]
```
Exit 0 seal printed; 1 only with `--fail-on-broken` and a verdict other than `sealed`; 2 refusal.
CI seals the committed G505 baseline against the real World Census fixtures on every change.

## Daedalus hook
`data/islands/disk-saver/harbour-seals-v1.json`: Customs Officer Perpetua recounts every crate of
figures against tonight's census before pressing her wax stamp (`census_sources`). The verdict
picks her line; each `diffs[].path` is a mark she chalks on the crate.