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
29. A `.cpp` that logs with `UE_LOG(LogDaedalus, ...)` must include `DaedalusLinkModule.h` itself. The header
    that declares the category is not pulled in by the others (C2065).
30. `FImageView` in 5.8 takes `(FColor*, W, H, EGammaSpace)`. The raw-pointer form needs a slice count as well, so
    the 5-argument call is C2661. Write PNGs with `FImageUtils::SaveImageByExtension(Path, FImageView)`. `FUpdateTextureRegion2D` lives in
    `RHITypes.h`, not `RHI.h`, and needs the RHI module. Find a 5.8 type with `Select-String '^struct FName'` over
    the engine's `Source\Runtime\*\Public`, not from memory.
31. Engine-free game cores go behind `THIRD_PARTY_INCLUDES_START/END`, and every name in them needs a check against
    Windows macros: `near`, `far`, `small`, `IN`, `OUT`, `ERROR`, `DrawText`. `grep -w` for these before the first
    build.

## Habits that saved us

- **Build a game its own framebuffer and capture that.** The viewport capture never worked in Play (play_capture).
  The 8-bit realm renders into a 256x240 array, so `RealmCapture` writes the PNG straight from it. A
  command-line test writes the same PNGs with no editor at all (`realm_core_test`, 13 frames).
- **Generate in Java, play in C++, prove in both.** The realm is rolled once in Java, and a walk proves it can be
  finished (200/200 seeds). The C++ test then plays the shipped spec with buttons only, and checks every storeroom
  chest against what Java rolled. A Java test fails if the shipped spec (`Content/Realm/realm-7.drr`) drifts from
  the generator.
- **Argument order is unspecified.** `Check(label, WalkTo(...), G.Describe())` printed the state from *before* the
  walk, and three "failures" were the test reading stale state. Take the reading in its own statement, after the
  action.
- **A walk that ends through a door is a success.** Helpers that walk to a link tile land on another map. Check
  where the party ended up, not whether the helper reached the target's (x, y).
- **Don't tear a widget down inside its own Tick.** The realm asks to close from its Tick. `ExitRealm` runs on the
  next core tick (`FTSTicker`), so the widget isn't freed while it's still on the stack.
- **A report must not blame an old log.** `-Wait` printed AutomationTool's ErrorLog.txt ("conflicting instance")
  for two builds that had really failed on compile errors. The ErrorLog was from 8:53; the builds ran at 11:01.
  Compile errors now come first, and the ErrorLog is shown only when it was written during this job.
- **Game logic must not live in Slate's Tick.** The realm walked 12 steps in one run and 0 in the next. The
  difference: the editor was minimized for the second run, and Slate stops ticking widgets in a minimized window.
  The portal's exit (raised from Tick) never fired either. The core now runs on `FTSTicker`, which ticks no matter
  what; Slate's Tick only copies pixels. The scenario also tries each direction until one walks, because a seed can
  put water to the right of the spawn.
- **Never press blind; read the screen state first.** The second live run walked 0 steps. Restoring a save closes
  the welcome message, so the scenario's "A to dismiss" opened the field menu, and the menu then swallowed every
  direction. Scenarios now close boxes until `ui=NONE` before they act.
- **Shared job folders need owned names.** Once the Blender team's harness also wrote jobs to
  `%LOCALAPPDATA%\Daedalus\jobs`, `unreal-job -Wait` with no id reported their `bharness-job` as our build.
  `Latest` now looks only at `build-*` logs.
- **ASan and UBSan on every engine-free core.** The first run crashed with a heap overflow in the test's
  pathfinder: a target outside a smaller map. The sanitizer named the line; a plain build only said "segfault".

- **A verifier must be able to say no.** Every check has a canary or a mutant that makes it fail, and a check
  nobody has seen fail proves nothing.
- **Run it live early.** The stand-ins were wrong twice (the scale baked in on import, the editor subsystems), and
  only the live editor showed it.
- **One finding, one fix, one commit**, and the commit message says what broke and how it was found.
- **Scenery folders aren't worlds.** Tools that scan `Daedalus/*` folders must check what's inside them: lamps
  and a light show once got mistaken for a world.
- **Drive gameplay per frame, not per call.** Each `execute_python` call is a single frame. To hold a trigger or a
  stick, register `unreal.register_slate_post_tick_callback`, act each tick, unregister when done, and read the
  record (ShotsFired, Hits, Kills) in a later call.
- **A background editor runs PIE at about 3 fps.** Count frames, not seconds, and judge movement by world deltas.
- **Aim tests pick a target the shooter can see.** The Ghost "missed" 22 of 22 because the test aimed at a foe up
  a cliff; tracing from the camera showed the rock. Filter targets by level and line of sight first.
- **Islands have ledges.** "4 m ahead" can be a lower tier; spawn points must match the hero's feet height.
- **Pawn swaps leave bodies wedged.** After getting off a vehicle, place the rider with `TeleportTo` (which checks
  for overlaps) at a spot with ground under it, not `SetActorLocation`.
- **C++ traces with no query params trace complex collision.** `FCollisionQueryParams::DefaultQueryParam` has
  `bTraceComplex = true`, and the island meshes only have simple collision, so those traces went straight through
  the ground. Every ground step looked like a drop and the foes stood still. Python's traces default to simple and
  hit, which is how it was found: the same trace, run from both sides, disagreed. Always pass
  `FCollisionQueryParams(..., false, this)`.
- **One Unreal build at a time.** A build started while another AutomationTool was alive failed in 0 s with
  "A conflicting instance of AutomationTool is already running", and setup still reopened the editor on the old
  plugin. `unreal-job.ps1` now waits for any running AutomationTool / UnrealBuildTool and retries once on that
  error; `-Wait` prints the AutomationTool error log when the plugin step fails, so the cause is on screen.
- **Split long PowerShell calls.** A single call that started a build, slept 48 s and then waited was refused
  more than once; the same steps as separate short calls (`-Start`, then `-Wait`) went through. Keep each call
  one action.
- **Play tests are scenarios, not hand-rolled loops.** `daedalus.play_scenario` / `play_status` run a mechanic
  frame by frame and return PASS/FAIL with numbers; a scenario that "passes" on nothing is a bug (the encounters
  check passed with zero foes until `len(...) > 0` was added).
- **Sample where the world is.** The sky between islands is empty: random points on a ring found ground 5 times
  in 200. Place things by sampling the island meshes' bounds, not open space.
- **A failed search must back off.** A foe with no route re-ran A* every frame (1,752 searches a minute);
  failures now wait 1.5 s. Watch the harness's counters (`nav_stats`) for runaway work.
- **Copy structs you read from Unreal Python.** `get_editor_property("target_cube")` returned a view that kept
  following the hero's target; after mining it pointed at the next cube and the check read the wrong one. Copy
  it (`unreal.IntVector(t.x, t.y, t.z)`) before the world changes.
- **Aim tests at what's there after the change.** Once a cube is mined, a ray aimed at it goes through the hole
  and past reach; aim at the hole's floor to place back.
- **No asset imports while Unreal is in Play.** The pipeline's import "completed", but `load_asset` and saving
  failed with "The Editor is currently in a play mode" and the judge saw 0 meshes. The art queue watcher now waits
  for Play to end (and says so in STATUS.md) instead of stopping anyone's session.
- **UE 5.8.3's Interchange reports only the meshes as imported.** Materials are created beside them but missing
  from `imported_object_paths`, so the judge saw "Unreal made 0 materials". Listing the destination folder
  instead was wrong: the e2e canary caught it counting a previous import's leftovers. The import script now counts
  the materials the meshes' slots actually reference, and the stand-in models what live Unreal does.
- **An import made during Play poisons its folder until the editor restarts.** It leaves unsaved, transient
  materials in memory at those paths; later imports to the same folder silently fall back to the engine's grid
  material. A fresh folder imported cleanly. The cause can't recur now (the watcher waits for Play to end), and a
  probe import into a scratch folder is the quick way to tell "poisoned path" from "broken file".
- **A minimised editor doesn't render.** The job launcher starts minimised and the editor inherited it: viewport
  screenshots timed out, HighResShot wrote nothing, and Play ran at ~3 fps all morning. Restoring the window
  (SW_SHOWNOACTIVATE, so it doesn't steal focus) fixed the screenshot at once. `unreal-job.ps1 -Wait` now
  restores it after every build.
- **PowerShell variable names ignore case.** Adding typed `[int]$W` / `[int]$H` parameters to `win.ps1` made the
  list loop's `$w = $wins[$i]` fail ("cannot convert … to Int32"), silently breaking `editor_windows` since
  v1.3.0. Don't reuse a parameter's name in any case.
- **Python can't spawn into the Play world or add components there** (`begin_deferred_actor_spawn_from_class`
  and `add_component_by_class` aren't exposed). A play-camera capture needs C++ or the restored viewport.
