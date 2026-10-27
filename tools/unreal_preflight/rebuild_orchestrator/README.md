# rebuild_orchestrator

Runs the batched-rebuild runbook (BOARD `GUARDS-AND-REBUILD-RUNBOOK.md`, section 2) in order. **Dry-run is the default and runs nothing.**

| step | what |
|---|---|
| 1 | `rebuild_delta` from `--base` to `--target` (report only) |
| 2 | `preflight.py` (all rules, incl. P12) in the `--repo` worktree |
| 3 | gates: `unreal` lease held by `--owner` (GET `/locks`), editor 0 dirty and not in Play (read-only bridge probe, no global `b`), producer stopped at a saved chunk (`producer_status`), free RAM > 3 GB |
| 4 | copy-backup of the live plugin `Binaries/` + `.uplugin` to `--backup-root/<stamp>` with `backup-manifest.json` (never deletes, refuses an existing dir) |
| 5 | UBT: the exact command from `--ubt-command-file` (JSON list). The runbook does not spell the command out, so it is never guessed: copy it from the latest recorded rebuild. |
| 6 | `build_receipt.py write` then `verify` |
| 7 | `rebuild-orchestration-<phase>.json` + `.md` in `--run-dir` |

```
# plan only
python tools/unreal_preflight/rebuild_orchestrator/rebuild_orchestrator.py --repo <clean main worktree> --base <built sha> \
  --plugin <live Plugins/DaedalusLink> --dll <live DLL> --backup-root <dir> --run-dir <dir> --owner unreal-epic-boss \
  --producer-launch-dir <boss-launch dir> --producer-run-root <producer root> --ubt-command-file ubt.json --stamp 20261027T1200
# phase A: steps 1-4, then prints the manual close steps and stops
...same... --execute
# close the editor normally yourself, then phase B: bridge must be gone, lease/producer/RAM rechecked, steps 5-7
...same... --execute --editor-closed --resume <run-dir>/rebuild-orchestration-A.json
```

It never kills, closes or launches a process, never touches locks or pins, and the relaunch stays manual (with the
small map arg; never `-AutoDeclinePackageRecovery` / `-unattended`). On UBT failure the report carries the
runbook's restore hint. Exit 0 ok/planned/awaiting close, 1 refused or failed, 2 bad input.
