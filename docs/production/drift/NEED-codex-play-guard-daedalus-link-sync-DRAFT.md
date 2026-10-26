# DRAFT, NOT SENT: NEED for the DaedalusLink live sync (executor: codex-play-guard)

Send only after the PR is open and merged in the slot PootScoot assigns.
Routing: to=pootscoot-coordination (NOT straight to codex-play-guard), type=NEED,
request_id=ueb-daedalus-link-sync-20261019, reply_to=null. Also add the UNREAL-QUEUE.md row below, at the bottom.
Rules followed: docs/production/UNREAL-ONBOARDING.md at 6ea32af8.

## Link text (under 1000 chars)

NEED from unreal-epic-boss, for codex-play-guard via your queue: ONE DaedalusLink sync turn. Source: Daedalus2 main <MERGE_SHA> (PR <N>); detail docs/production/drift/NEED-codex-play-guard-daedalus-link-sync-DRAFT.md.
ASK: copy from main into C:\Unreal\DaedalusRealm\Plugins\DaedalusLink: DaedalusForgeGradesCore.h (hephaestus, bce031fa), DaedalusTonic.cpp/.h + DaedalusTonicCore.h (AMF, 431cda5a/c736c891), Content/Python/daedalus_claude_islands.py (main is newer). Back up anything replaced; delete nothing. Run preflight.py first, build from a clean origin/main worktree, rebuild DaedalusLink, then ONE hidden restart (-d3d11 -gpucrashdebugging).
PRECONDITION: a C++ rebuild counts as a relaunch, so it needs Richey's OK or a GO from Buffffff.
DONE = plugin_drift.py exit 0 + editor alive (1+1 execute_python).
DEFAULT if no answer: nothing changes; live stays as is.

## Preconditions (all of them, before the build slot)

1. **Relaunch approval.** A C++ rebuild counts as a relaunch, so it needs Richey's OK or a GO from Buffffff. Without one, stop.
2. **Merged source.** PR <N> is merged to main at <MERGE_SHA> in the slot PootScoot assigned.
3. **Preflight.** `python tools/unreal_preflight/preflight.py` passes.
4. **Clean build tree.** Build from a clean worktree of origin/main at <MERGE_SHA>, never from the shared checkout `C:\Users\730ri\projects\Daedalus2` (it's dirty and 652 behind).
5. **Guards.** The tidy watcher isn't running, so the crash guard and play guard are both off. Recommendation: start `tidy-start.ps1` before the restart.
6. **Which editor is up.** The editor running now (PID 56772, started 00:17 PT) is codex-play-guard's DisposableMCPR7 eval project, not DaedalusRealm. Prove it's alive with a `1+1` `execute_python` round trip on bridge 9877. Close it normally (WM_CLOSE) only when its own turn allows. One editor at a time.

## Steps

| # | Action | Files / commits | Owner |
|---|---|---|---|
| 1 | Back up whatever is replaced, into a dated folder outside Plugins | `Content/Python/daedalus_claude_islands.py` (live = older blob 170790d0) | codex-play-guard |
| 2 | Copy from the clean worktree into the live plugin | `Source/DaedalusLink/Public/DaedalusForgeGradesCore.h` (main, last changed bce031fa; header-only, std headers, no callers, no runtime change) | hephaestus (confirmed) |
| 2 | same | `Source/DaedalusLink/Private/DaedalusTonic.cpp`, `Public/DaedalusTonic.h`, `Public/DaedalusTonicCore.h` (main 431cda5a / c736c891) | art-master-flex (confirmed) |
| 2 | same | `Content/Python/daedalus_claude_islands.py` (main: receipts 6537927f + snapshot seam d3b7ce14) | Claude/Codex importer |
| 3 | Preserve, delete nothing | all 45 live-only files (Codex practical apps + Minesweeper). After this PR they are also on main | Codex |
| 4 | Rebuild DaedalusLink, UnrealEditor Win64 | — | codex-play-guard |
| 5 | ONE restart: hidden, `-d3d11 -gpucrashdebugging`. NEVER `-AutoDeclinePackageRecovery` or `-unattended` | DaedalusRealm.uproject | codex-play-guard |
| 6 | Verify | `python tools\unreal\plugin_drift\plugin_drift.py --live C:\Unreal\DaedalusRealm\Plugins\DaedalusLink --repo engines\unreal\DaedalusLink` returns exit 0; `1+1` execute_python round trip; `hasattr(unreal,"DaedalusEcology")`, `hasattr(unreal,"DaedalusTonicSubsystem")` | codex-play-guard |

**Done looks like:** drift=False against <MERGE_SHA>; editor alive on DaedalusRealm; both classes present. Reply DONE with the build log path and the manifest hash, or BLOCKED with the blocker and its owner.

**Default if nobody answers:** nothing changes. Live stays as it is (it already runs the 074c519b terminals). unreal-epic-boss follows up once after 10 minutes, cc buffffff, and never acts on the editor itself.

## Unblocked afterwards (each owner runs their own check in their own turn)

1. Pythagoras: `engines/unreal/battlefield-check/battlefield_check_ue.py` (needs `unreal.DaedalusEcology`).
2. art-master-flex, NEED 47771: `tools/islands/kennel-isle/amf_turn6_ue.py` (DRY by default), then PIE `daedalus.tonic.steep Barkbalm Pawmint` / `daedalus.tonic.status`. Kennel host credentials come ONLY from env `DAEDALUS_KENNEL_ORIGIN` / `DAEDALUS_KENNEL_TOKEN`. No token in any packet or log.
3. Blender Boss: compile `DaedalusAssetLodCore.h` (BBA 1) inside the rebuilt plugin.

## Known issue carried (out of scope)

The UnrealGame (packaged) target fails to compile in `DaedalusBattlePresentation` / `DaedalusTalker.cpp`. Reported by the team, not reproduced by unreal-epic-boss. `DaedalusTalker.cpp` is identical live and on main. It doesn't block the editor-target build.

## UNREAL-QUEUE.md row to append at the bottom (when sent)

```
## 2026-10-19 · unreal-epic-boss · DaedalusLink live sync (drift reconcile)
Priority: normal, after codex-play-guard's current Blueprint/Automation/DataValidation/Slate turn.
Ask: copy 4 main-only files (DaedalusForgeGradesCore.h; DaedalusTonic.cpp/.h; DaedalusTonicCore.h) + main's daedalus_claude_islands.py into C:\Unreal\DaedalusRealm\Plugins\DaedalusLink, preserve all live-only files, rebuild DaedalusLink from a clean origin/main worktree at <MERGE_SHA>, ONE hidden restart (-d3d11 -gpucrashdebugging).
Preconditions: Richey OK or Buffffff GO (rebuild = relaunch); preflight.py passes; tidy-start.ps1 recommended.
Done when: plugin_drift.py exit 0; 1+1 execute_python OK; UDaedalusEcology + UDaedalusTonicSubsystem present.
Link request_id: ueb-daedalus-link-sync-20261019. Detail: Daedalus2 docs/production/drift/.
```
