# Bell Buoys (G538, DiskSaver Island, quest q_bell_buoys)

Post-contest disk/memory tooling (buffffff lane, 2026-10-29). Source only, no editor, no assets.
Python dev tooling; nothing here runs inside Unreal and no workflow is executed.

## What it does
A workflow with an `on: pull_request: paths:` filter only runs when a changed file matches one of
its patterns. If a run step uses a file the filter misses, a change to that file merges without
the check ringing. `tools/streaming/bell_buoys.py` reads `.github/workflows/*.yml` and the repo
tree (read-only, plain-text parse) and checks each filtered workflow:

| kind | level | meaning |
|---|---|---|
| `unguarded` | error | a repo file, module (`python -m tools.x`) or directory a step uses that no paths pattern matches |
| `missing_file` | error | a step names a repo path that does not exist |
| `stale_pattern` | advisory | a paths pattern that matches no file in the repo |

Step `name:` lines and `$VAR/...` paths are ignored. Workflows with no `pull_request` paths filter
(or with `paths-ignore`) run on every change and are listed as `unfiltered`. Patterns follow GitHub
glob rules (`*` within a segment, `**` across segments; tested against a reference matcher).
`--under PREFIX` keeps workflows whose steps use files under PREFIX.

Verdict: `silent` (any error), `muffled` (stale patterns only), `ringing`.

## CLI
```
python tools/streaming/bell_buoys.py [--root DIR] [--under tools/streaming] [--json] [--fail-on muffled|silent]
```
Exit 0 report; 1 with `--fail-on` and a verdict at least that bad; 2 refusal. CI fails only on the
streaming lane (`--under tools/streaming --fail-on silent`) and prints the whole-repo report for
information (other lanes' workflows are not ours to gate).

## Daedalus hook
`data/islands/disk-saver/bell-buoys-v1.json`: Buoy-tender Ottoline rows out each dawn to check the
bell buoys (`workflows[]`): channels boats use with no bell (`unguarded`) and bells over open water
(`stale_pattern`). The verdict picks her line.