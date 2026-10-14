# Unreal plugin recovery

The editor owner explicitly checkpoints an approved build while editor/build tools are stopped:

```powershell
engines/unreal/unreal-job.ps1 -SaveGreen -Project C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -GreenBuildId APPROVED_COMMIT_OR_JOB
engines/unreal/unreal-job.ps1 -Rollback -Project C:\Unreal\DaedalusRealm\DaedalusRealm.uproject
```

`GreenBuildId` is the operator's approval reference, not an automatically inferred green build. Capture saves the full Win64 directory, DLL/module identity, every file's hash/size, project path and engine association. Copy validation must agree with both the saved and current files before the latest pointer is published. Use `-Snapshot green-UUID` to select an older checkpoint.

Rollback verifies the checkpoint and prepares a sibling directory before renaming the current binaries aside and publishing the restored directory. Failure during publication restores the previous directory when possible. Previous binaries, partial preparations and all snapshots remain available for diagnosis. There is no recursive cleanup. A process-held lock excludes concurrent recovery operations.

The default 60-second budget applies to preparation before publication; it refuses an overdue preparation. It cannot guarantee filesystem I/O completes in 60 seconds. The native filesystem fixture restored in 0.075 seconds; this is not evidence for a real plugin's recovery time. No installed plugin has been rolled back by this change.

Active editors and Unreal build tools cause refusal. No process is stopped, no build runs and no editor opens. Idle probes are observational, so other launchers must respect the coordinated editor turn. The owner must reconcile source/config compatibility, open the editor and verify runtime health afterward; restored bytes alone do not prove a healthy runtime.
