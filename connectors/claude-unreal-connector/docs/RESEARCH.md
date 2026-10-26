# Research notes and roadmap (2026-10-11)

Two surveys informed this connector:
1. **Outside:** open-source Unreal MCP servers and agent bridges, Epic's documentation and forums, issue
   trackers, and community threads.
2. **Inside:** the automation harnesses already built in [CSRBT](https://github.com/RicheyWorks/CSRBT) and
   [FlowersForever](https://github.com/RicheyWorks/FlowersForever).

## Adopted

- **Unattended execution through Unreal's own Python Remote Execution.** `remote_execution.py`
  (PythonScriptPlugin) sends `unattended: true` with each command. That sets `GIsRunningUnattendedScript`,
  which makes the editor cancel modal dialogs ("suppressing some UI") instead of blocking the game thread.
  - Verified on UE 5.8.3: `run_command(self, command, unattended=True, exec_mode=...)`.
  - The bridge sends `execute_python` this way from a background thread and yields editor ticks while it
    waits. `install.ps1` sets `bRemoteExecution=True`.
  - Sources: [EPythonCommandFlags](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PythonScriptPlugin/EPythonCommandFlags),
    [IAMSamuelRodda/mcp-unreal](https://github.com/IAMSamuelRodda/mcp-unreal),
    [groscy/unreal-mcp](https://github.com/groscy/unreal-mcp).
- **The outside-the-editor window harness** (`win.ps1`) stays as the fallback for dialogs that unattended
  mode doesn't cover. No other project we found answers dialogs from outside the editor.

## Next (ranked)

1. **Job ids and a result journal** for long commands. The client never resends, and polls for the result
   by id, so a slow import can't time out and run twice. ([chisomobanzi/Unreal-MCP](https://github.com/chisomobanzi/Unreal-MCP),
   [BatSasha52/GameplayMCPToolset](https://github.com/BatSasha52/GameplayMCPToolset))
2. **`batch`:** many commands in one call, under one `unreal.ScopedEditorTransaction` (one undo).
3. **A gateway contract with a risk ladder,** from CSRBT's `tools/harness_contract.py` (the Java form is
   FlowersForever's `HarnessGateway`).
   - Every command declares its risk: READ (status, level, log), SENSITIVE_READ (screenshot), MUTATE
     (execute_python, import), DESTRUCTIVE (save, delete).
   - The MCP layer derives `readOnlyHint` and `destructiveHint` from the risk.
   - `request_id` replay.
4. **A walk ledger.** Drive every command in `list_commands` from its schema, and account
   `discovered == driven + refused + failed + excluded`. A new command with no test then shows up as
   UNACCOUNTED. (CSRBT `tools/harness_walk.py`)
5. **A mutant runner for the bridge**, catalogued as (name, file, old, new, why), recorded with
   `mutant_ledger.record()`. Example mutants:
   - drain one job per tick
   - remove the re-entry guard
   - report an error as ok
   - a huge timeout

   (CSRBT `tools/mutate_run_all.py`, `tools/mutant_ledger.py`)
6. **Floors:** a minimum check count per suite, so a suite that silently runs 0 checks is red.
   (FlowersForever `scripts/verify_harness.py`, CSRBT `tools/verify/floors.json`)
7. **Faster, UI-free screenshots:** a `SceneCapture2D` into a `TextureRenderTarget2D`, then
   `RenderingLibrary.export_render_target`. Before capturing, wait on `FinishAllAssetCompilation` and
   shader compilation, which avoids black frames.
8. **Pre-seeded suppressible dialogs.** Write `SuppressableDialogs` keys into
   `Saved/Config/Windows/EditorPerProjectUserSettings.ini` before launch. Unverified section name.
9. **Watch Epic's official "Unreal MCP"** (experimental in UE 5.8: HTTP at 127.0.0.1:8000/mcp, Python
   toolsets via `unreal.ToolsetDefinition`). A bridge command set could also be published as a toolset.
   It says nothing about dialogs, which is where this connector is different.

## Pitfalls to guard against

- **A UE 5.8.3 PythonScriptPlugin GC crash** with closures held in Python reference cycles
  ([forum](https://forums.unrealengine.com/t/ue5-8-pythonscriptplugin-crash-during-gc-fpycfunctionwithclosureobject-layout-omits-weakref-vectorcall-fields/2776052)).
  Register module-level functions for tick callbacks; the bridge's `pump` is one.
- **Silent no-ops in the Python API:**
  - Python names are snake_case.
  - Blueprint class paths need `_C`.
  - Interchange imports are async.
  - Edits need `PostEditChangeProperty` / `set_editor_property`.

  ([ibrews/ue5-mcp](https://github.com/ibrews/ue5-mcp))
- **Saving:** the editor doesn't auto-save, so call `save` after changes.

## Projects surveyed

- [Epic Unreal MCP](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)
- [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)
- [flopperam/unreal-engine-mcp](https://github.com/flopperam/unreal-engine-mcp)
- [remiphilippe/mcp-unreal](https://github.com/remiphilippe/mcp-unreal)
- [unreal-engine-mcp (PyPI)](https://pypi.org/project/unreal-engine-mcp/)
- [groscy/unreal-mcp](https://github.com/groscy/unreal-mcp)
- [IAMSamuelRodda/mcp-unreal](https://github.com/IAMSamuelRodda/mcp-unreal)
- [chisomobanzi/Unreal-MCP](https://github.com/chisomobanzi/Unreal-MCP)
- [BatSasha52/GameplayMCPToolset](https://github.com/BatSasha52/GameplayMCPToolset)
- [ibrews/ue5-mcp](https://github.com/ibrews/ue5-mcp)
- More under the GitHub topic [unreal-mcp](https://github.com/topics/unreal-mcp).

Reddit and X added little beyond these; GitHub, Epic's docs and Epic's forums held the substance.
