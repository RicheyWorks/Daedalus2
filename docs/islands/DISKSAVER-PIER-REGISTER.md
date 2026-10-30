# Pier Register (G534, DiskSaver Island, quest q_pier_register)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.
Python dev tooling over JSON data; nothing here runs inside Unreal.

## What it does
Every DiskSaver island ships a Daedalus hook file `data/islands/disk-saver/<slug>-v1.json`
(quest id, NPC, hook values). `tools/streaming/pier_register.py` reads all of them, read-only,
with `docs/islands` and `tools/streaming`, and writes one berth row per hook (quest, NPC, doc, tool).

| kind | level | meaning |
|---|---|---|
| `bad_json` | error | file is not a JSON object |
| `no_quest` | error | no quest id `q_<name>` |
| `duplicate_quest` | error | two hook files share a quest id |
| `lines_mismatch` | error | a `hook.values` entry has no `npc.lines` line (extra lines are fine) |
| `no_doc` | advisory | no `docs/islands/DISKSAVER-<SLUG or QUEST>.md` |
| `no_tool` | advisory | no `tools/streaming/*.py` named after the slug or quest, or naming the file |
| `no_npc` | advisory | no `npc.name` |
| `name_reused` | advisory | the same NPC given name (last word) on more than one island |

Report files without a quest (e.g. the committed G505 baseline) are skipped.
Verdict: `unregistered` (any error), `queried` (advisories only), `registered`.

`--name "Title Given"` checks whether a new NPC's given name is free; it exits 1 when taken, so
future islands can pick an unused keeper before they ship.

## CLI
```
python tools/streaming/pier_register.py [--root DIR] [--name NAME] [--json] [--fail-on queried|unregistered]
```
Exit 0 register printed; 1 with `--fail-on` and a verdict at least that bad, or `--name` taken; 2 refusal.
CI runs it on the repo with `--fail-on unregistered` (the existing reused given names Wren, Bram,
Odile and Ines are advisories, not failures).

## Daedalus hook
`data/islands/disk-saver/pier-register-v1.json`: Pier Registrar Abelard reads the register each
evening (`berths[]`), raises a query for each finding and refuses berths on errors. The verdict
picks his line.
