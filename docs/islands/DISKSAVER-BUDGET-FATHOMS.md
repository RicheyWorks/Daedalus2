# Budget Fathoms (G529, DiskSaver Island, quest q_budget_fathoms)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.

## What it does
G206 colours islands at a fixed budget and G522 counts asset headroom at a fixed budget.
`tools/streaming/budget_fathoms.py` solves for the budget instead. It reads a World Census
`census.json` (priced with the G206 model) or an already-made G206 report, read-only, and
computes in KiB, separately for RAM and disk:

- per island: `*_green_kib` (smallest budget that keeps it green at `warn_permille`) and
  `*_clear_kib` (smallest budget that keeps it out of red);
- per world: `*_fit_kib` (smallest budget holding every island resident at once);
- fleet `need_kib`: `all_green`, `no_red`, `all_fit` and `deep` (= max of all_green and all_fit),
  with `slack_kib` = current budget minus each (negative = short);
- optional `sweep`: G206 beacon counts and spilling worlds re-priced at each `--sweep-ram` / `--sweep-disk` value.

Breakpoints are closed form and tested tight against a brute-force scan over the G206 `beacon`
(one KiB less always flips the state).

Verdict at the current budget: `deep` (all green, all fit), `shoal` (no red, all fit, some amber),
`aground` (a red island or a spilling world).

## CLI
```
python tools/streaming/budget_fathoms.py census.json [--sweep-ram 32000,40000] [--sweep-disk 24000] [--json] [--fail-on-aground]
```
Exit 0 report; 1 only with `--fail-on-aground` and an aground verdict; 2 refusal. No clock, integers only.

## Daedalus hook
`data/islands/disk-saver/budget-fathoms-v1.json`: Gauge-keeper Corwin's gauge post at the harbour
mouth carries the four `need_kib` marks; tonight's tide is the current budget, the water under the
keel is `slack_kib.ram.deep`, and `sweep` is his printed tide table. The verdict picks his call.