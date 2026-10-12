# Automation lessons: driving Unreal, Blender and Windows without a human clicking

What the team has learned by making an AI agent operate Richmond's Windows PC, Unreal Engine 5.8 and Blender.
Every entry was found live, mostly by something breaking. Read this before you automate anything here, and add
to it when something new breaks.

## The tools

| Tool | What it reaches | Where |
|---|---|---|
| Claude Unreal Bridge | the open editor's Python, on its game thread (TCP 127.0.0.1:9877) | `connectors/claude-unreal-connector` |
| Unreal extension (MCP) | the bridge, plus a window harness that sees and answers dialogs from outside the editor | same, `extension/` |
| Shell harness (`powershell`) | PowerShell on the PC, whether or not Unreal is open | Richmond's local copy, not on GitHub |
| Claude Blender Bridge | Blender's Python (TCP 127.0.0.1:9876) | `RicheyWorks/claude-blender-connector` |
| Asset pipeline | Blender, then `.glb`, then Unreal, judged on both sides | `connectors/claude-asset-pipeline` |
| Capability walk | what the editor can really do, proven live | `connectors/claude-unreal-connector/harness/caps` |

## Running things on the PC

1. **Calls through the device link time out at 60 s.** Keep each call short. To wait, sleep 45-55 s in one call,
   then look again in the next. Never sleep longer.
2. **A job started from the extension dies when the call ends.** The Claude app runs extensions inside a Windows
   job object that kills child processes, and `detached` doesn't escape it. For anything long (setup, builds,
   anything that restarts Unreal), launch it through WMI, which runs outside the job object:
   `Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = "powershell.exe -File job.ps1" }`.
   Have the script write a log and an `.exit` file, and read them in later calls.
3. **Setup closes Unreal, so run it as a WMI job.** The bridge goes down while it runs. Read the job's log instead.
4. **Leave `-Connector` off setup while the shell harness is installed.** Its packer used to pack a fixed list of
   files and dropped `shell.js`, which crashed the extension. The packer now packs every file, but a local
   `index.js` with the shell wired in still differs from GitHub, so stash or copy it back after a pull.
5. **Memory.** The PC has 32 GB, and other apps often hold 25 GB or more. A second, headless editor (the
   sandbox) needs 2-4 GB, so it refuses to start below 4 GB free and only one runs at a time.

## Dialogs: the editor stops for them, so the automation must answer them

6. **A modal dialog freezes the editor's game thread, and the bridge with it.** Calls then time out. Look from
   outside with `editor_windows` or a PowerShell window scan; never wait on the bridge.
7. **The method that works: focus the window, then press the real key.** Tap Alt, call `SetForegroundWindow`,
   check it's now the foreground window, then send Enter or Escape with `keybd_event`. Posting `WM_COMMAND`
   (IDYES) to the dialog didn't work, and UI Automation couldn't even see its buttons (UE 5.8.3, Windows 11).
8. **`dialog-watch.ps1` answers the startup dialogs, and setup `-Open` starts it.**

   | Dialog | Answer |
   |---|---|
   | "Missing *Project* Modules ... rebuild?" | Yes |
   | "Restore Packages" | Skip |
   | "Error: could not be compiled" | OK, logged as a build failure (then read the setup log; the box only means the build failed) |

   Add new dialogs as rules in its table. Unknown dialogs are logged, not answered.
9. **The extension's dialog watcher cancels any modal** (Escape) during a bridge call, and says so in the reply.
10. **Run code unattended.** `execute_python` goes through Unreal Remote Execution in unattended mode, so dialogs
    are cancelled instead of waited on. The reply must say `"unattended": true`. If it doesn't, the editor has an
    old bridge.
11. **Close stray tool windows (Plugins, Message Log) by their X**, or with `window_input` action `close`. The
    safety classifier blocked Alt+F4.

## Crashes: sweep in a sandbox, never in the user's editor

12. **Creating assets with unknown factories crashed the live editor twice.**
    - A factory opened a modal picker ("Choose Dataflow Setup").
    - `DataAssetFactory` with no class set made an abstract asset, and saving it asserted.
    - `LightWeightInstanceFactory` (deprecated in 5.8) and `SlateWidgetStyleAssetFactory` crash the engine.
13. **Risky work runs in the sandbox** (`harness/caps/sandbox.py`). That's a headless `UnrealEditor-Cmd
    -nullrhi` started by the open editor, under a supervisor. Before each item it writes the item's name to a
    progress file. After a crash, the supervisor reruns the sweep and skips the last item named, which is the
    culprit. The user's editor never goes down.
14. **Save the level before anything risky.** Use the bridge's `save`.
15. **The editor can pull the harness straight from GitHub** (`urllib` to raw.githubusercontent.com), so nothing
    needs pasting.

## Unreal Python traps (UE 5.8)

16. Names come out snake-cased oddly: `IDs` becomes `i_ds` (`get_num_triangle_i_ds`), and `LODs` sometimes
    becomes `lo_ds`.
17. Making a static mesh from Geometry Scripting is `GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh`,
    not `..._AssetUtils`.
18. Editor subsystems (`StaticMeshEditorSubsystem` and others) are `None` in a commandlet. Probes that need them
    run in the open editor.
19. Factories that need a setting fail or misbehave without it: `BlueprintFactory.parent_class`,
    `DataTableFactory.struct`, a skeleton for animation assets.
20. Interchange glTF import makes **one static mesh per node and bakes the node's scale into it**. A 2x crate
    comes in as 200 cm. Compare sizes per node.
21. `register_slate_post_tick_callback` animates things over editor ticks (a camera orbit, driving the hero) while
    the bridge call returns at once.
22. Python can't read Unreal's own class name with `cls.get_name()` (unbound). Use `cls.__name__`, and pass
    `cls.static_class()` where a UClass is wanted.
23. `TraceTypeQuery.TRACE_TYPE_QUERY1` is deprecated; use `ECC_VISIBILITY`.

## C++ traps (UE 5.8, MSVC 14.44)

24. Include what you use. `GetWorld()->` needs `Engine/World.h` (C2027 otherwise).
25. UE 5.8's JSON object keys are not `FString` (C2665 in `TMap::Find`). Look fields up by name with
    `TryGetArrayField` and similar, instead of walking `Values`.
26. Unreal treats variable shadowing as an error: no local named like a member function (`Swing`, for example).
27. MSVC 14.40-14.43 is banned by UE 5.8, so 14.44 or newer is needed. Setup skips the build when a Visual Studio
    Installer window is open.
28. Load engine assets in a constructor with `ConstructorHelpers::FObjectFinder`, not `LoadObject`.

## Habits that saved us

- **A verifier must be able to say no.** Every check has a canary or a mutant that makes it fail, and a check
  nobody has seen fail proves nothing.
- **Run it live early.** The stand-ins were wrong twice (the scale baked in on import, the editor subsystems), and
  only the live editor showed it.
- **One finding, one fix, one commit**, and the commit message says what broke and how it was found.
- **Scenery folders aren't worlds.** Tools that scan `Daedalus/*` folders must check what's inside them: lamps
  and a light show once got mistaken for a world.
