# Channel Chart (G536, DiskSaver Island, quest q_channel_chart)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.
Python dev tooling; nothing here runs inside Unreal, and the charted code is never executed
(sources are parsed with `ast`).

## What it does
`tools/streaming/channel_chart.py` reads `tools/streaming/*.py`, `.github/workflows` and
`data/islands/disk-saver` (read-only) and charts each tool (non-test module): local imports
(plain `import x` or `tools.streaming.x`) and who imports it, external imports, the disk-saver
data files it or its test names, its test file (`<tool>_test.py` or `test_<tool>.py`) and the
workflows that name it, plus a run order with every tool after the tools it imports.

| kind | level | meaning |
|---|---|---|
| `syntax_error` | error | the source does not parse |
| `import_cycle` | error | local tools import each other in a loop (or a tool imports itself) |
| `missing_module` | error | `tools.streaming.X` that does not exist |
| `no_test` | advisory | no test file |
| `no_workflow` | advisory | no CI workflow names the tool or its test |
| `external_import` | advisory | import that is neither stdlib nor local |
| `unnamed_data` | advisory | a disk-saver data file no tool, test or workflow names |

Verdict: `uncharted` (any error), `shoals` (advisories), `charted`.

## CLI
```
python tools/streaming/channel_chart.py [--root DIR] [--json] [--fail-on shoals|uncharted]
```
Exit 0 chart printed; 1 with `--fail-on` and a verdict at least that bad; 2 refusal. CI runs it on
the repo with `--fail-on uncharted`.

## Daedalus hook
`data/islands/disk-saver/channel-chart-v1.json`: Chartmaker Isaura inks each channel (`tools[].imports`),
marks whirlpools (import cycles) in red and shoals where no inspector walks; `run_order` is her
sailing order. The verdict picks her line.