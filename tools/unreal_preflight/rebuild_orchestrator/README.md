# rebuild_orchestrator

Runs the batched-rebuild runbook (BOARD `GUARDS-AND-REBUILD-RUNBOOK.md`, section 2) in order. **Dry-run is the default and runs nothing.**

| step | what |
|---|---|
| 1 | `rebuild_delta` from `--base` to `--target` (report only) |
| 2 | `preflight.py` (all rules, incl. P12) in the `--repo` worktree |
| 3 | gates: `unreal` lease held by `--owner` (GET `/locks`), editor 0 dirty and not in Play (read-only bridge probe, no global `b`), producer stopped at a saved chunk (`producer_status`), free RAM > 3 GB |
| 4 | copy-backup of the whole live plugin (as rebuild 4's script did) to `--backup-root/<stamp>` with `backup-manifest.json` (never deletes, refuses an existing dir) |
| 4b | phase B, before UBT: source sync. Mirrors rebuild 4's script (`Copy-Item <worktree>\engines\unreal\DaedalusLink\* <live plugin> -Recurse -Force`): every file under the worktree's `engines/unreal/DaedalusLink` is copied over the live plugin, no exclusions (the script had none; a clean worktree holds no Binaries/Intermediate). Refuses unless the worktree is clean and `HEAD` equals `--target` (pass the sha). Never deletes: live-only files are listed in `live_only_not_deleted`. `source-sync-manifest.json` has per file path, action (add/overwrite/unchanged), source sha256, live sha256 before and after; any after != source stops before UBT. |
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
small map arg; never the package-recovery auto-decline or unattended flags, see preflight P11). On UBT failure the report carries the
runbook's restore hint. Exit 0 ok/planned/awaiting close, 1 refused or failed, 2 bad input.

## UBT command

`ubt-command.json` is the exact command rebuild 4 ran (Oct 26 2026; verified from its UBT logs and rebuild script): `Build.bat DaedalusRealmEditor Win64 Development -Project=C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -WaitMutex` under `C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles`. Pass it with `--ubt-command-file tools/unreal_preflight/rebuild_orchestrator/ubt-command.json`. The runbook keeps the canonical copy.
