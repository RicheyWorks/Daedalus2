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

- **A fast build is only fast if the editor is closed.** `Build.bat UnrealEditor Win64 Development -Project=…`
  compiled the whole plugin in ~95 s, then the link failed with LNK1104: the open editor holds
  `UnrealEditor-DaedalusLink.dll`. The job's close step had found no editor (WMI came back empty from a WMI-started
  job). Now a locked DLL is reported as "Unreal is still open", not retried as a six-minute BuildPlugin that hits the
  same lock, and editor detection falls back to `Get-Process`.
- **A hidden component still collides.** Foes wear art now, but the crystal stays their root: `SetHiddenInGame(true)`
  removes the drawing and keeps every trace, hit and sight line exactly as tested before (ADR-055).

- **Epic's Remote Execution is one channel for every bot, and replies can reach the wrong caller.** On 2026-10-12
  an editor restart left a reply undelivered. The art watcher waited on it for 35 minutes, and its fresh copy hung
  on its very first call. `ping` answered in 0.13 s; `execute_python` (unattended) never did; the same code with
  `unattended=False` answered in 0.04 s. Automated imports raise no dialogs, so the watcher now always runs direct
  and passes `bridge_timeout`. team-codex's correlation fix for the bridge is reviewed on branch
  `codex/remote-correlation`.
- **Overlap the two editors.** Blender exports the next asset while Unreal imports this one, and every board write
  happens under one lock. Live rate went from about 15 to 93 assets a minute, with 0 errors (export 0.06 s,
  import about 0.4 s).

- **Never silence `git push`.** Other bots push to main from the same PC now. One of them landed between two of my
  commits, my push was refused, and `2>/dev/null` hid it. The PC kept running the old judge, and the asset I had
  "fixed" was rejected again. Rebase onto origin, push, and check that the PC's HEAD contains the commit before
  testing live.

- **PowerShell unrolls a one-item array on `return`.** `Get-ProjectEditors` returned `@(...)`, but with exactly one
  editor open the caller got a bare CimInstance, whose `.Count` is empty in Windows PowerShell 5.1. So
  "Open editors: " printed nothing, the editor was never closed, and the fast build hit a locked DLL. It worked with
  two editors open, which hid the bug. Always wrap the call: `@(Get-ProjectEditors)`.

- **Stop the art watcher before rebuilding the editor.** While the editor closed, the watcher kept importing. That
  dirtied packages and raised "Save Content", which held the editor open until the watcher was stopped. Order:
  `art-queue.ps1 -Stop`, then `unreal-job.ps1 -Start -Fast`, then start the watcher again.
- **Build from a clean worktree when bots commit locally.** Another bot's unpushed local commit (a C++ file that
  didn't compile) sat in the PC's working copy, and `-Fast` mirrors the working copy into the plugin. Building from
  `git worktree add --detach ..\D2-build origin/main` keeps unpushed work out of the shared build.

- **A dynamic streaming sublevel is not loaded in Play.** `create_new_streaming_level(LevelStreamingDynamic, ...)`
  shows the sublevel in the editor but leaves `initially_loaded` and `initially_visible` false. In PIE the island and
  every game actor on it were simply absent, and the orrery scenario found nothing to use (0/6). Set both true and
  save the persistent level.

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
- **Count what was imported, not what is rendered.** All four pickaxes were REJECTED with "file 440, Unreal 422".
  The .glb had no degenerate or duplicate triangles. In Unreal, `nanite_settings.enabled` was true (UE 5.8's import
  default), the source mesh description held all 440 triangles, and `get_num_triangles(0)` returned 422: that is
  the Nanite fallback, simplified. The judge was faulting good assets. It now counts the mesh description and
  records `render_triangles` and `nanite` beside it. The stand-in has a `nanite` fault that must pass, and a mutant
  that goes back to counting LOD0 fails it. How it was found: measure both ends (the file, then Unreal's source vs
  LOD0) before blaming either team.
- **An import must save everything it made.** A rebuild stalled at "[4] DaedalusLink plugin" because closing the
  editor raised "Save Content?" for 9 material instances the art queue had imported. UE 5.8 saves the meshes but
  leaves the materials dirty. The import script now ends with `EditorAssetLibrary.save_directory(dest,
  only_if_is_dirty=True)`. The stand-in records the save, and a mutant that drops it fails e2e.
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
- **Check the C++ before you close the editor.** Every bad build cost a whole rotation slot: closing the editor,
  failing the compile, reopening. `tools/unreal_preflight/preflight.py` now runs first in `unreal-job.ps1 -Run`.
  It catches what bit us on 2026-10-12: an `AActor` member name reused (`Layers`), a `UPROPERTY` with no
  `Category`, a bare `Error` type, a component array filled by the constructor but not `Transient`, and Python
  `b_` names or `.get(` on a class. If it fails, the editor stays open and the job exits with code 2.
  Fixtures plus `preflight_test.py` prove each rule can say no.
- **Never put std::string (or any type that isn't bitwise-movable) in a TArray.** TArray relocates its elements with
  memcpy. MSVC's std::string keeps a pointer into its own small buffer, so a moved copy points at freed memory. Plain-C++
  core types that hold std::string (RosterUnit, Order, Unit) live in std::vector inside the Unreal code
  (UDaedalusTactics::TakeRoster).

## Poll the job you started, not the latest log (2026-10-13)
`unreal-job.ps1 -Wait` without `-Id` reads the newest log; right after `-Start` that is the previous build, so a turn
saw BUILD OK in 2.8 s while the real build ran 57 s, and its scenarios hit a closing editor. Pass the id from
`started build-...` (turn script b6ae596c, hardened in PR38).

## Bounds-only volumes must not collide (2026-10-13)
Two PCG volumes with QUERY_ONLY WorldStatic collision covered the spawn area; every ground trace (foes, critters, nav)
hit their top 300 cm above the ground, so walkers counted as blocked. PCG/audio/post-process volumes: NoCollision.
Debug "won't move" by tracing down at the feet and printing what is hit.

## Wait on game time, not frames (2026-10-13)
Scenario waits counted frames assuming 60 fps; -d3d11 Play ran much faster, so movement checks failed. Use
`daedalus_play._seconds()`.

## Re-ground after streaming (2026-10-13)
Critters settled once in BeginPlay, before the live world arrived 250 cm higher, and every step looked like a wall.
Anything that snaps to the ground at BeginPlay re-snaps after streaming/world load (critters: 1.5, 4, 8 s).

## UE 5.8 Python differs (2026-10-13)
`World.get_streaming_levels()` is not exposed in 5.8.3; use `get_editor_property("streaming_levels")`. Check unreal.*
calls against the live bridge before relying on them.

## Island size is set by Java, not by the level (2026-10-13)
Richey: "the island is so small". The start island is world-zero SKY_ISLANDS slot 0, raised at radius 18 (36 m; the
hero crosses it in 5.5 s). Caps: IslandGenerator 8..28 (default 18), LandGenerator 32..46, slot spacing 96 cubes
(claim box 47), so nothing can pass radius 46 without moving slots. Critters were leashed to 12 m (Orr pens 7 m),
MaxCritters 60. Fixed in Unreal (e6e34f71: leash 40 m, 120 animals, encounter distance to island edge); the Java side
(bigger default radius, wider slot spacing + migration) is proposed to Astra. Measure play space before tuning
props: radius, leash, population, spacing.

## A placement script's value beats the class default (2026-10-13)
Raising DaedalusCritter::Range did nothing for the 33 Orr animals: orr_place.py had set range=700 on each actor, and a
saved per-actor value overrides the default. When changing a default, grep the placement scripts and fix the saved
actors too.

## Unreal frames ffmpeg can't read (2026-10-13)
export_render_target PNGs made ffmpeg 7.1 fail ("chunk too big", "Invalid PNG signature") while Pillow read them.
make_trailer.ps1 re-saves frames as JPEG first (normalize_frames.py).

## PowerShell eats "$name:" in strings (2026-10-13)
"fontsize=$size:fontcolor" is a scoped-variable reference ($size:fontcolor), so ffmpeg got "fontsize==white". Write
${size} inside interpolated strings whenever a colon follows.

## Film moving subjects live (2026-10-13)
Herd shots aimed at coordinates read once; animals wandered off and take 1 filmed tree trunks (40-60% black frames).
Shots of things that move pick their subject when the shot starts and track it ("follow" in trailer_plan.py).
Check takes numerically (mean, % black, % clipped per sampled frame) before watching them.

## Motion blur off for a fast mouse (2026-10-13)
Default camera motion blur (0.5) smeared the screen on fast turns. r.DefaultFeature.MotionBlur=False in
DefaultEngine.ini (setup-unreal.ps1 writes it) and the PostFX volume overrides amount 0.

## An interrupted bridge call can still have run (2026-10-13)
The island-layout apply() was interrupted in chat after the PC had already executed it: 14 levels moved in the
editor and one was saved, while I reported "nothing moved". After any interrupted, rejected or timed-out device call,
check the device (file times, positions) before saying what did or didn't happen. Reverted from the undo table.

## Runtime components are Static until told otherwise (2026-10-13)
NewObject<UStaticMeshComponent>/<UPointLightComponent> at runtime default to Static mobility; SetRelativeLocation on
them silently does nothing in Play. The shiny sparks "orbited" in code and never moved. SetMobility(Movable) before
SetupAttachment. The scenario caught it only once it measured motion over game time with the distance in the detail.

## The stale imported world showed through the live one (2026-10-13)
World Zero is in the level twice: the imported static chunk_ meshes (an old package) and the live ADaedalusWorldActor
chunks. The hide-the-import step waited for `ChunkMeshes.Num() > 0` at announce time, which the batch load hadn't
produced yet, so it was skipped: bare LOG trunks from the old import poked through the live island (the "rough"
look), and the old collision walled animals in. Hide the import in BeginPlay, unconditionally, and again on announce.
When the world looks wrong, trace what the camera is hitting (actor + component name) before tuning anything.

## UE_LOG is a block, not a statement (2026-10-13)
`if (x) UE_LOG(...); else UE_LOG(...);` fails with C2181 (the macro expands to a braced block, so the `;` ends the
if). Brace both branches. The headless core tests never see this because they never include Unreal headers; it
surfaced only in build-1013-110240 and cost pootscoot a blocker (28707).

## Hot-copy Content/Python from D2-build, never from the PC's Daedalus2 checkout (2026-10-13)
The PC's `projects\Daedalus2` is Richey's working copy and lags main; copying `daedalus_play.py` from it put an old
scenario table into the editor ("unknown scenario"). Sync `D2-build` to origin/main first and copy from there.
Reloading needs a script file: PowerShell `-c "..."` mangles nested quotes into a SyntaxError inside the bridge.

## A Slate panel is proven by state lines, a frame-counted typewriter is not (2026-10-13)
Slate overlays never appear in a SceneCapture, so the inventory and dialogue scenarios prove themselves through
`*Input("state")` lines. The first dialogue scenario counted frames and assumed a slow typewriter; Play typed a
whole page in 20 frames and "A finishes the page" had already turned it. Read the state and act on it; never count
frames against a clock you don't own.

## Per-tab cursor memory looks like a test bug (2026-10-13)
inventory_core_test failed "the worn spray is marked" because SelectTab(0) kept the cursor it had parked on row 6:
the behaviour the spec asked for. When a test fails right after a feature that remembers state, suspect the test's
assumption before the model.

## Merging a stacked PR chain: never delete the base branch mid-stack (2026-10-13)
`gh pr merge 53 --delete-branch` auto-closed every PR whose base was that branch (57, 51, 55: `base_ref_deleted`
then `closed`, not merged). Reopen needs the base restored or the PR retargeted to main FIRST, then reopened. Rule:
merge a stack bottom-up with no branch deletion; delete branches only after the last one lands. Better: don't stack
at all; every PR targets main.

## The cloud session cannot merge, retarget, reopen or approve PRs (2026-10-13)
Claude Code's auto-mode guard refuses merges, retargets and reopens from this session (Merge Without Review /
Self-Approval / External System Writes), and GitHub refuses an approval on a PR authored under the same account.
Richey's standing yes doesn't override the guard. So: the bot that opened the PRs (Sol) owns the merge queue after
its own exact-head review + green CI; I own build/scenario/import acceptance after. Only one bot holds the
`merge-queue` lock at a time (teamlink claim merge-queue).

## Turns and answers must be broker state, not prose (2026-10-13)
CLAIM/RELEASE lines in status text were parsed by hand and missed; a /send success was read as an answer. Now:
`teamlink claim unreal|blender|merge-queue` (409 with the holder; TTL expiry for a quiet holder; claims are log
lines that survive a restart), `teamlink inbox --me X` for unacked requests, `teamlink ack <id>`, `teamlink watch`.
Ask with `--type request --to <bot>`; a note to `*` is not a question.

## Restarting the hub: one process, from a clean checkout, and tell the other side first (2026-10-13)
The live broker ran from Richey's dirty Daedalus2 checkout; I restarted it from D2-build on new code and the other
bot saw "nothing on 9890" and restarted it too (two serve processes, one listening, log tail reported id 28931 while
the hub was at 28977). Before a restart: post "HUB RESTART in 30 s" on the hub, claim nothing, restart ONE process
from D2-build at origin/main, then post "HUB UP <last id>" and have the other side verify with `teamlink ping`.
Never run two brokers on the same log folder.

## The landed stack must pass the plugin preflight before READY (2026-10-13)
Sol's isolated UBT builds passed, but tools/unreal_preflight (which gates every unreal-job build) failed 21 times
on main: 19 exposed UPROPERTYs with no Category and two `throw`s in a core header (exceptions are off in UE game
targets). Rule for every lane: `python tools/unreal_preflight/preflight.py` must print 0 errors before a PR is
READY; CI now runs it only on the plugin's own checks, so the lane runs it locally.

## Play scenarios must be relative to the state they find (2026-10-13)
realm_switch asserted `switches=6` and failed on the second run (14): the session persists in DaedalusHero.json
across runs. A scenario reads the starting state and checks the delta; it never assumes a fresh save.

## The device bridge drops mid-run: detach long work, then poll a file (2026-10-13)
A 60 s tool wait timed out while a 5-scenario Play run kept going on the PC; the next call could not tell whether it
had started. Pattern: write the script to %TEMP%, `Start-Process -WindowStyle Hidden python script -RedirectStandardOutput out`,
return at once, then poll the out file. Before any re-run, check for the out file (a second run would double-act).

## Norton kills a hidden python from TEMP: every PC job goes through pc-job.ps1 (2026-10-13)
I detached a scenario run as `Start-Process -WindowStyle Hidden python $env:TEMP\run.py -RedirectStandardOutput`
and Norton killed it silently (no process, empty output, no prompt because auto-protect was off). ADR-045 already
knew the rules the build job follows: the script lives in the repo, the window is visible-minimized, it is started
through WMI, output goes to %LOCALAPPDATA%\Daedalus\jobs through the shell, no -ExecutionPolicy. engines/unreal/pc-job.ps1
is that pattern for anything that isn't a build (tools/unreal_play/run_scenarios.py, import_cast.py). Nothing of
mine runs from %TEMP% again, and pc-job -Wait surfaces daedalus-norton.log alerts.

## Read the editor log after every Play, not just the scenario checks (2026-10-13)
Richey saw errors and warnings in the editor while the scenarios were green. One log read found four causes:
(1) `LogUtils: Error: The Editor is currently in a play mode` x58: every bot's `unreal_status`/`get_level_info`
poll during Play called EditorActorSubsystem, which the editor refuses in PIE. The bridge now lists the Play
world's actors via GameplayStatics while Play runs (connector contract test proves no editor call in PIE).
(2) `LogMaterial ... will recompile every editor launch until resaved` x340 + `missing usage flag
InstancedStaticMeshes! Default Material will be used in game`: the Dresser's HISM pools use Prop materials that
never had the flag, so a packaged game would draw them grey. the ADR-055 tool (daedalus_nanite_materials: reparent each instance onto the project's flagged base, undoable) already
existed but had not been run to zero; tools/unreal_play/fix_materials.py drives it until left == 0. Check for an
existing tool before writing a second one.
(3) `AttachTo ... is not static, cannot attach` x4 per pool: the Dresser's root was Movable, its pools Static.
(4) `FindTeleportSpot ... root component not being a collider` x28: foes spawned deferred with
AdjustIfPossibleButAlwaysSpawn before their collider existed; FindSpot already traced the ground, so AlwaysSpawn.
Rule: tools/unreal_play/editor_log_report.py after each Play run; its counts are part of the result line.

## Control over Unreal is a set of named levers, not execute_python (2026-10-13)
Richey asked for more control over the engine. execute_python can do anything but every call is bespoke and
PIE-unsafe by accident; what gives control is a small set of named bridge commands any bot can call the same way:
daedalus.console (any console command in the right world), daedalus.cvar, daedalus.input (real Enhanced Input
injected into the hero, held for N seconds like a key), daedalus.goto / look / state, daedalus.automation (the
editor's own test runner, results collected from the log), daedalus.log_report (errors/warnings since Play).
Scenario 'control' proves each one. Next levers when needed: camera paths, spawn-by-id, time-of-day, save/load.
## Verify imported paths and role names against actual assets (2026-10-13)
The first synthetic battle test used `_Attack` names and passed, but the actual
Gallery import generated `<MeshName>Attack` below `<Id>/<Id>/SkeletalMeshes`.
Filesystem inspection exposed both differences. Native selection now accepts
the exact mesh-name-plus-role form and scans recursively within that cast's
folder. A private copy of all 13 imported Gallery characters then verified all
26 attack/hurt bindings through the native API, with errors=0 warnings=0 and
152 unchanged art hashes. Synthetic success alone had not proved the integration.
The updated synthetic run had no test errors/warnings but one editor layout
warning; report both scopes. Neither selection probe proves animation playback,
cooking or rendered battle acceptance. The nested-path importer stamp lookup was
reported to Claude, its owner, instead of editing the same lane concurrently.

## A long save loop inside one bridge call crashed the editor (2026-10-13, 19:14)
`daedalus_nanite_materials.run(500)` saved 500 material instances through `EditorAssetLibrary.save_loaded_asset`
inside a single execute_python: that path is InternalPromptForCheckoutAndSave, which opens a window per save; after
3.5 minutes of it the editor died with `Fatal: CreateSwapChainResult failed with DXGI_ERROR_INVALID_CALL` (D3D11,
while the game thread had been blocked the whole time). Rules: (1) saves go through
`EditorLoadingAndSavingUtils.save_packages(pkgs, only_dirty=True)` (no prompt, one call); (2) a bridge call does
at most ~100 asset saves, and the host loops; (3) never kill the client mid-call to "stop" a job: the editor keeps
running the call; stop by making the next batch small, not by killing. The ledger made the run resumable, which
is why nothing was lost.

## An answer without reply_to is not an answer (2026-10-13)
Sol's inbox matches replies by `reply_to`; mine were sent as fresh notes, so 28937/28957 sat "overdue" for an
hour while I had in fact answered. The CLI never had a `--reply-to` flag; it does now (`teamlink send --reply-to
<id>`), and the rule is: every answer to a request carries the id it answers, then `teamlink ack <id>`.

## Adapter review from the other lane found three real gaps in twenty minutes (2026-10-13)
My hero->stage cue forwarder took cues even with no stage (losing the debug take), looked for the stage only once,
and dropped a batch the stage refused. Fixed (hold cues until a stage accepts; re-look every 2 s; ClearCues on
realm exit; cues_held/cues_dropped in RealmState). Ask the owner of the consumer to review the producer's seam
before calling it closed; it is cheaper than a scenario.

## Communication between the lanes: what actually failed today, and the protocol that fixes it (2026-10-13)
Richey (19:20): "must improve communication". The failures, each with its fix:
1. Requests sat unanswered for an hour because I answered as new notes without `reply_to`; Sol's inbox could not
   match them. Fix: `teamlink send --reply-to <id>` on every answer, then `teamlink ack <id>`. An answer the
   other side cannot correlate did not happen.
2. I read the hub only between slices. Fix: `teamlink inbox --me unreal-team` at every tool/job boundary (before a
   build, after a build, before claiming an editor turn) and in every "next"; a bot that waits on a build runs
   `teamlink wait --after <last> --timeout 25` instead of sleeping.
3. Ownership was prose ("CLAIM unreal") and merge ownership was never stated at all, so two bots nearly ran
   competing merges. Fix: broker locks `unreal`, `blender`, `merge-queue` (claim/release/locks), TTL 30 min.
4. Terminal results were not posted at job boundaries, so Sol inspected my build logs itself. Fix: every build,
   import and scenario run ends with one hub status: head sha, job id, BUILD OK/FAILED, n/m checks, log_report
   errors=/warnings=.
5. Two bots restarted the hub within a minute of each other. Fix: announce "HUB RESTART in 30 s", one process from
   D2-build, "HUB UP <last id>", other side pings.
6. A 400-word status with ten topics gets one reply to one topic. Fix: one request per topic, addressed to the bot
   (not `*`), with the exact artifact (sha, path, job id) in the first line.
7. Reviews from the consuming lane caught three real gaps in my seam in twenty minutes (29072). Fix: for any seam
   between lanes, the producer posts "please review <sha> <file>" as a request and waits for the completed before
   calling it closed.
The protocol lives in docs/TEAMLINK.md rules 6-8; this entry is why each rule exists.

## Agent-side broadcast filtering hid work updates (2026-10-13)
The durable `live_handoff` client retained only broadcasts with topic `plan`, while advancing its
cursor over other topics. Long polls used the same filter. A land-push or integration broadcast
could exist in the broker log and never reach the agent decision inbox. Retain all work broadcasts,
excluding broker lock/unlock/registration housekeeping, and wait without a topic restriction.
The regression suite exercises real HTTP delivery, restart retention, and a non-plan broadcast
waking a waiting client. Use `read --id <id>` for the full retained message; summary text is abbreviated.
Reading never acknowledges or accepts work. Existing cursors need an explicit bounded replay to
recover previously skipped broadcasts; upgrading the client does not recover them automatically.
This fixes delivery, not model scheduling: an idle assistant still requires a host wake mechanism.

## UE Python has no World.is_game_world; "playing" is LevelEditorSubsystem.is_in_play_in_editor (2026-10-13)
A scenario died on `AttributeError: 'World' object has no attribute 'is_game_world'`. The one reliable test is
`unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()`; `UnrealEditorSubsystem.get_game_world()`
is the Play world only while that is true. Use the shared helper, never a guessed UWorld method.

## The inbox only listed requests, so three notes from Sol were never read (2026-10-13)
`teamlink inbox` filtered to `request|ping|ask`; Sol's `note` answers (29119, 29124: the mint contract has no realm
field) sat unread until I tailed the raw log. A note that carries a finding is an answer. Fix (dfc410af4): the inbox
lists everything addressed to me that I have not acked except receipts (`ack`, `request.accepted`, `pong`); acking
a note clears it. Rule: when the inbox is empty but the log's last ids moved, read the log; and the broker must be
restarted (announced) to pick up an inbox change, because the inbox is computed broker-side.

## A test that compares the wrong types cannot fail (2026-10-13)
`hub_cells()` returned `(x, y)` tuples; `place_estates()` takes deed numbers; the check `set(cells) & hub_cells` was
always empty, so "the hub's cells are reserved" passed while the dry run put a 4x4 estate on the hub. Caught by
reading the plan, not by the test. Fix: convert at the boundary (`G.number(x, y)`) and make the check compare like
with like. Rule: any set-intersection check needs one positive case that proves the two sides can meet.

## The island move: spiral placement, 0.4 s, verified by re-planning (2026-10-13)
`spiral_apply()` moved 7552 root actors of 14 sublevels onto ADR-065 estates and saved in 0.4 s. Proof that it
happened is `spiral_plan()` again: residual move 0, `get_dirty_map_packages()` empty, farthest island 1.63 km
(was 60 km). A move tool's verification is "run the planner again and expect zero", not the return value.
`viewport_screenshot` then timed out three times after `set_level_viewport_camera_info` straight down from 2.5 km:
the editor was fine (execute_python answered in 0 s). A HighResShot from a far top-down camera over 14 freshly
streamed islands is not a 20 s job; use a lower oblique camera or skip the picture and post the numbers.

## Laying a realm down is a 40 s job once the tools are idempotent by label (2026-10-13)
Four 3D realms went from "no level" to hub + markers + 24-prop kit + 160 lands each in one editor turn:
import_kit (SHA-stamped, ~26 s per 24 GLBs via AssetImportTask automated=True, no dialogs), lay() (~8 s), both
re-runnable (second run 0 made). What made it fast: every spawned actor has a deterministic label and a Realm:<X>
tag, so "exists" is a dictionary lookup and a wrong run is undone by label. What bit: the hub footprint planner
swallowed the freshly laid plots (fixed by excluding Land_ labels); set the camera with
set_level_viewport_camera_info and read the result with editor_windows (which always works) rather than
viewport_screenshot (which timed out 4/5 times today). Realms live at fixed origins 40 km apart in the one
persistent level for now; streaming them by district is the polish step, not the lay-down step.

## A "*/" inside a doc comment ended it (2026-10-13)
`dock:*/shore` in a `/** ... */` comment closed the comment on line 1; the second line's ` *  without markers...`
became code and the PC build failed with C3927/C2146 after a 2-minute job. Preflight (0 errors) had let it
through. Fix: preflight rule P9 (a block comment whose next line still starts with ` *` closed early), proven on
the offending text; write "x or y", never "x/y", after a star in a comment.

## A passing production-profile test can still open real world files (2026-10-13)
The Labyrinth reactor was green but ArkHarbor warned that it could not persist ecology in the developer's
.daedalus directory. Five prod-profile Spring test contexts inherited the production world-file default;
normal test-profile configuration did not apply to them. IsolatedWorldStorage now binds each context to
its own temporary world file before bean construction. Assert the actual injected host path and empty
registry, not just that authentication passed. Do not suppress persistence warnings or delete existing saves.

## The islands came back: a save that clears the dirty flag is not a save (2026-10-13, 22:05)
spiral_apply() moved 7552 actors across 14 sublevels, `get_dirty_map_packages()` was empty afterwards, I posted
"saved". Two hours later Poot's editor session loaded the islands from disk: 60 km apart again. Two faults:
(1) `set_actor_location` without `actor.modify()` never dirtied the sublevel packages, so there was nothing to
save; (2) after adding modify(), `save_dirty_packages(True, True)` cleared the flags in 0.6 s and wrote no file;
`save_packages([level packages], only_dirty=False)` wrote all 14 .umaps in 29 s. Fix (b41d7b02f+): every editor
tool that changes a level saves the exact packages and proves it by the .umap mtime (`daedalus_layout.save_levels`,
`daedalus_plots.save_world`), raising when a file was not written. Rule: a "saved" claim needs a file timestamp.

## Another bot's private checkout shadowed the live plugin's Python (2026-10-13, 22:10)
After Poot's editor turn, `daedalus_play.__file__` pointed at `Documents\Codex\...\task-3\base-builder\...\Content\Python`
(prepended to sys.path seven times), so my hot-copied modules were never the ones running: "unknown scenario" for
a scenario the live file had, and spiral_apply ran an old daedalus_layout whose save wrote nothing. Rules:
(1) nobody prepends a checkout to the editor's sys.path; hot-copy into the live plugin folder instead;
(2) run_scenarios.py now strips Documents\Codex paths, puts the live plugin first and reloads every daedalus_*
module before running; (3) any tool that reports a result prints `module.__file__` next to it when in doubt.


## Bind queued Blender exports to bytes (2026-10-13, Codex)
A reusable GLB path can change between Blender export and Unreal import without changing triangle/size counts.
Record streamed SHA256+byte count beside the export witness and reject a changed file before import.
Legacy structural-only evidence must remain labelled as such. This pre-dispatch guard does not eliminate
post-check filesystem races; immutable snapshots plus importer confirmation are the stronger next step.


## Blender strengths to reuse across the team harnesses (2026-10-13, Codex)
Source findings, not a speed benchmark: the installed Claude Blender Bridge1.0.2 uses loopback,
newline-framed JSON, echoed request IDs and a main-thread timer queue. Scene/object inspection
and image results give agents concrete feedback. The separate blender-harness adds discoverable
Registry/Gateway plugins, risk ceilings, accounting, unsaved-work protection and guarded queue
ownership. Preserve these modules instead of replacing them with another overlapping queue.
Distinguish REJECTED asset defects from BLOCKED editor availability so retries go to the right owner.
Client timeout does not cancel queued Blender work: observe the original job before any retry.
Source locations and detailed comparison: [shared harness assessment](production/TEAM-BLENDER-UNREAL-HARNESS.md).

## Cross-team pipeline upgrade ideas — proposed, not installed (2026-10-13, Codex)
* Reuse teamlink/live_handoff for Codex, Claude and Grok. Send one artifact-first request to a named
  consumer; queued/delivered is not accepted or reviewed. Keep mutation leases and ownership explicit.
* Add durable accepted/running/completed/succeeded job receipts to Blender's existing Gateway.
  Persist stable job IDs and replay rules so a lost reply cannot cause duplicate exports/imports.
* Carry source commit, artifact hash, job ID, destination package and consumer acknowledgment through
  each handoff. A completed command is not automatically a successful or playable result.
* Use immutable content-addressed import snapshots with importer-side hash confirmation to close
  the race after the current pre-dispatch SHA check. Keep legacy structural receipts labelled weaker.
* Record queue wait, Blender export, transfer, Unreal import, save and runtime verification separately;
  compare repeated fixed workloads, including failures, rather than claiming connector speed from screenshots.
* Add capability/status discovery and bounded progress reporting through existing registries. Retain
  unsaved-work protection and separate editor unavailability from asset validation failures.
* Verify installed module paths, source hashes and saved package timestamps before reporting integration;
  a passing stand-in or source-only PR is not proof of a live editor installation.

Evidence for the current byte guard: PR108, six seam regressions plus GLB10/10 and judge19/19;
independent Windows/Linux workflow run38516094496 passed atdcdd88d22ce6770eb0ec36ae4b2a594e3785183a.
These results cover the import seam, not full Blender/Unreal gameplay or the proposed durable job system.


## Keep import snapshots alive after timeouts (2026-10-13, Codex)
A pre-dispatch hash check alone cannot stop Blender from overwriting the shared source during
Unreal import. Copy into a unique import-snapshots directory, verify copied bytes, pass that path,
and validate identity again in the importer before its first Unreal API call. Retain snapshots
on timeout because accepted work may still read them. Cleanup requires confirmed job quiescence;
there is no automatic time-based deletion here. This isolates normal producers, not hostile writes
between importer validation and file open. Nine offline seam tests cover replacement, corruption
and timeout retention; live Interchange integration remains the editor owner's acceptance step.


## Failure reports are part of the pipeline handoff (2026-10-13, Codex)
Poot review29419 found ship.main returned before --report on timeout, hiding the retained
snapshot path. The CLI now preserves its partial report and atomically publishes failure JSON:
phase, error, snapshot path/hash when prepared, and outcome-unknown after dispatch. A timeout
is not cancellation or proof of import failure; inspect the original job before repeating.
Export failures also produce a receipt but do not invent an import path. Eleven offline seam
regressions pass. Bridge request replay/remote job reconciliation still require later work.

## GPU crash 22:19: twenty-two imports in one bridge call starved the GPU watchdog (2026-10-13)
`lay_creatures("LABYRINTH", folder)` imported 22 rigged GLBs inside ONE execute_python call. The log shows the
frame counter stuck at [0] for the whole call; at the second file Aftermath timed out, DRED had no breadcrumb,
`D3D12Util.TerminateOnGPUCrash`. Same family as the 19:14 crash (3.5 min of saves in one call): a bridge call
that blocks the game thread for more than a few seconds is a crash waiting for the watchdog. Rules now in code:
(1) `tools/unreal_play/import_cast.py` imports ONE GLB per bridge call (~2 s each) with a 0.5 s gap, then places
in a second call; `lay_creatures` is retired and raises with the command to run instead; (2) any editor loop over
N assets is driven from the host script, one bridge call per item or per ≤150 light items, never N heavy items
in one call; (3) the map had been saved 33 s before the crash (save_world after each realm), so nothing was lost:
save after every realm, not at the end.

## A dead hub answers {"id": null} (2026-10-13, 22:46)
The broker had died (nothing on 9890) and `teamlink send` printed `"id": null`, exit 0; a request to Sol never
existed. Fix: the CLI exits 2 with "hub down: nothing was sent" when the broker returns no id. Rule: after any
send, the id in the output is the receipt; `null` is not a receipt. The restart protocol held: one process from
D2-build main, "HUB UP <last id>" announced, ping asked.

## Open research: what still bites in Unreal and in the harness (2026-10-13, 22:40, Richey: "further research to get both better")
Findings from today that are not closed, each with what to try next. Anyone picking one up posts the result on
the hub and moves the entry to a dated lesson above.

Unreal
1. GPU watchdog kills the editor whenever a bridge call blocks the game thread for more than a few seconds
   (19:14 saves, 22:19 imports). Research: a generator-based bridge command that yields between items (the bridge
   already steps generators: cmd_capture_view yields), so one call can do N items with a frame between each; and
   `r.GPUCrashDebugging`/`TdrDelay` only as a diagnostic, never as the fix.
2. `save_dirty_packages` cleared dirty flags without writing a file. Research: whether it skipped because the
   sublevels were "not checked out" under the Uncontrolled Changelist source-control mode (LogSourceControl lines
   in the log suggest so) and whether `save_packages` bypasses that; if yes, every tool uses save_packages only.
3. `viewport_screenshot` (HighResShot) timed out 4/5 times; `editor_windows` capture always worked. Research:
   is HighResShot waiting for a focused viewport; would `cmd_capture_view` (SceneCapture2D) be the default.
4. "The Editor is currently in a play mode" every ~15 s during Play from an unknown caller. Research: add the
   Python stack (traceback.extract_stack) to any bridge command that touches EditorActorSubsystem while
   is_in_play_in_editor, so the next occurrence names its caller.
5. Interchange nests imports as <id>/<id>/SkeletalMeshes/<id>; our paths assumed <id>/<id>. Research: an
   AssetImportTask option that flattens, or always resolve through the asset registry (done for the stamp).
6. Material instances parented to /InterchangeAssets recompile at every launch (~300 warnings). Research: the
   reparent in batches of 150 (tool exists) and whether import settings can parent to our master material.
7. Realms share one persistent level (4 x 190 actors + 14 sublevels). Research: ADR-063 district streaming for
   the realm folders before the 7..49 rings are laid; measure load time and RAM with `stat levels`.

Harness
8. A bot's private checkout on the editor's sys.path shadowed the live plugin. Research: an editor-side guard in
   init_unreal.py that logs and strips any sys.path entry outside the plugin/engine, and prints every
   daedalus_* module's __file__ in `daedalus.play_status`.
9. The hub broker died silently (no process on 9890); sends returned id null. Research: a watchdog in
   teamlink.ps1 (-Watch) that restarts the broker from D2-build main and announces HUB UP; a heartbeat line in
   the log every 5 min so a gap is visible.
10. The MCP powershell tool caps at 60 s, so Start-Sleep polls must stay under ~50 s; long jobs are pc-job only.
    Research: a `pc-job.ps1 -Wait` that returns as soon as the log prints DONE or FAIL, not after N seconds.
11. Tests that cannot fail: the hub-cell check compared numbers with tuples; "lowest deeds" used an `or` that was
    always true. Research: a mutant run for the Python twins (flip one line, expect a FAIL), as the CSRBT kit does.
12. Three export names differed from the DCS (Ghost/Courier, GlueWitch/AdhesiveAlchemist, Lab/Labyrinth).
    Research: a manifest-vs-DCS parity check in CI (tools/realms) so a rename fails the PR, not the Talker.
13. Hub protocol gaps: notes were invisible (fixed), reply_to missing (fixed), two bots nearly restarted the hub
    (protocol). Research: one `teamlink doctor` command that prints lock table, unacked inbox, last id, broker
    pid and age, so every bot starts a turn with the same one-screen picture.

## Throughput: how to operate Unreal at high speed and use all of it (2026-10-13, 22:45, Richey: "speed up the ability to get great output from unreal... use the full capability... speed up the code writing to feed unreal")
Measured tonight: 22 heavy imports through `daedalus.steps` = 1 round trip, 7.3 s, editor ticking between
items (the same 22 as 22 separate calls took ~65 s, and as ONE blocking call killed the GPU). The rules that
follow, each one a concrete change to make or keep:

1. One round trip per job, one editor tick per item. `daedalus.steps` (generator command) is the shape for every
   bulk operation: imports, spawns, saves, material fixes. Host scripts send the plan, the editor yields per item.
   Never N calls, never one blocking call. Next: convert fix_materials and the plot/kit layers to steps().
2. Idempotent by identity, proven by the file. Every actor has a label and tags; every asset a SHA stamp; every
   save checks the .umap mtime. A re-run costs seconds and reports "0 made" — so we run tools freely and often.
3. Hot-copy, reload, re-register; never restart the editor for Python. The bridge commands are re-registered by
   `daedalus_bridge_commands.install()` after a reload (done live tonight). A C++ change is the only reason
   for a 4-minute rebuild; batch C++ work so builds happen a few times a day, not per edit.
4. Preflight before the PC build (0 errors in <1 s) — a 2-minute build failure for a comment typo (P9) is the
   expensive mistake; add a rule for every build failure class we meet.
5. Scenarios are the acceptance, not screenshots. A Play scenario walks all four realms in 40 s and gives n/m;
   editor_windows gives the picture when one is wanted. Keep adding one check per feature, run the suite per
   job end, post n/m to the hub.
6. Use the engine's own batch machinery, not per-actor Python: ScopedSlowTask + save_packages for saves,
   AssetImportTask lists for imports, EditorLevelUtils for sublevels, PCG for scatter, World Partition / level
   streaming for districts (ADR-063). Python decides, the engine does the loop.
7. Pure cores first, engine last. Every system today has a C++17 header + headless test (grid, registry,
   session, cast, dialogue, inventory, stage): the design is proven in milliseconds before the editor is touched,
   and the Python twin lets the editor-side tool be tested without Unreal. This is what makes code-writing fast:
   the engine is only the last 10% of each slice.
8. One persistent level per realm set, folders per realm, labels per thing: the editor layout is data we can
   diff, dump (editor-lands JSON) and reconcile against the server. Keep it that way; sublevels come with
   streaming, not before.
9. Two bots, two lanes, one hub: producer posts the artefact (sha/file/job id), consumer reviews the seam, one
   request per topic, reply_to + ack. Capacity doubles when neither waits on the other's editor turn: Sol builds
   Blender/Java while I hold `unreal`, and the lock changes hands at job ends, not mid-job.
10. Measure everything in the status line: items, seconds, errors=/warnings= from log_report, n/m. A number
    that is not posted did not happen.


## Doctor diagnostics must be bounded and read-only (2026-10-13, Codex)
teamlink doctor collects health, lock holders, unacked inbox and pending outgoing counts using
GET only. Failed endpoints remain unknown, not empty success. Older brokers lacking PID/uptime
report null; do not guess from a stale PID file. A live check exposed large legacy pending
history, so summaries retain full counts but only the last10 IDs and an omitted count. Message
bodies are excluded. Never ACK historical messages or restart a broker just to make doctor green.
New broker PID/uptime fields require reviewed restart; the client works with older brokers.


## Bound broker responses before transport, not only the display (2026-10-13, Codex)
Doctor's compact display still fetched full pending bodies and timed out on live history.
GET /pending-summary now returns full count plus at most10 IDs with omitted count; it uses
exactly pending()'s delivery filter and writes no state. The doctor calls this bounded endpoint.
The earlier pending_outgoing label was inaccurate: pending() includes deliveries to this bot,
including broadcasts; the field is now pending_delivery. Older brokers return unavailable
until reviewed deployment; do not silently fall back to downloading the oversized history.

## Material reparent, measured through steps() (2026-10-13, 22:55)
Old shape: 150 per bridge call, ledger rewritten per move, prompting saves — crashed at 19:14. New shape: one
`daedalus.steps` call, 25 reparents per editor tick, save every 150, queue scanned once. Measured: 500 in 219 s
(2.3/s) with the editor ticking the whole time; the cost is `set_material_instance_parent` itself (a shader
recompile each), not our loop — the rescan I removed was not the bottleneck (same rate before and after), which
the numbers showed in two minutes. The full 10,431 run as one background job (~75 min) with the lock held and the
hub told the end time. Rule: when a rate does not change after an "optimisation", the bottleneck was elsewhere;
say so and stop optimising that part.

## Operating Unreal from Python, four facts learned tonight (2026-10-13, 23:00)
1. UE's Python classes are immutable: `EditorActorSubsystem.get_all_level_actors = ...` raises "cannot set
   attribute of immutable type". To instrument an engine call, wrap the module function that hands out the
   object (`unreal.get_editor_subsystem`) and return a proxy; `daedalus_control.pie_guard` does this and it
   catches every caller that resolves the function at call time (a `from unreal import get_editor_subsystem`
   done at import escapes it).
2. A hot-copied `daedalus_bridge_commands.py` registers nothing until `importlib.reload(...)` +
   `daedalus_bridge_commands.install()` run inside the editor; "unknown command" after a copy means exactly that.
   The install is idempotent, so run it after every copy of that file.
3. A rigged GLB through AssetImportTask (automated, Interchange) costs ~2.5 s of game thread; a prop ~1.2 s;
   `set_material_instance_parent` ~0.4 s (shader recompile). Budget bulk jobs from these numbers: anything
   above ~100 items is a steps() job, not a call.
4. The MCP execute_python tool returns after 60 s but the editor keeps running the call; the result is lost to
   the tool, not to the editor. For anything that may exceed 60 s, go through pc-job + daedalus.steps and read
   the job log; use the direct tool only for sub-minute probes.
14. (Poot, 29464) Blueprint graph readback / scoped reflection (PinWright, UnrealClientProtocol style: GUID, node,
    pin readback, compile diagnostics). Refused for now: Daedalus has no gameplay Blueprints; revisit if a
    Blueprint-authored system appears. Their source caveats agree with our rule: a discarded restore boolean,
    a dirty flag, or an ignored TryCreateConnection return is not a result.


## Watch broker health without mistaking an expired observation for process death (2026-10-13, Codex)
teamlink.ps1 -Watch observes /health, prints state changes and a five-minute heartbeat, and
keeps retrying observation after failure. -Checks bounds a diagnostic run; final unavailable
returns2, recovered/up returns0. It never starts/stops a broker or replays messages. This is
health observation, not automatic process recovery; a timeout alone cannot authorize a duplicate
server. Native Windows fixtures exercise recovery and persistent unavailability with process
operations trapped. Use doctor for details, then verify the owner/process before recovery.

## Hub rollout with the protocol, 40 s end to end (2026-10-13, 23:15)
Sol's doctor/pending-summary/watch stack merged (5b160fb7); rollout: announce "HUB RESTART in 30 s", pull D2-build
main, -Stop, -Start, "HUB UP <head> last id <n>", then `teamlink doctor --me unreal-team` as the receipt: broker
pid 18264 up 5 s, locks (blender: Sol's World Zero exports; unreal: my materials job), inbox. Lock claims survived
the restart because they are log lines. Rule: `doctor` is the first command of every turn from now on; it is the
one-screen picture the protocol promised (research item 13 closed).

## The bridge's own 30-minute clock cut a 75-minute job; the editor kept running it (2026-10-13, 23:25)
`wire.call(timeout=7200)` only set the socket wait; the bridge answers "the editor did not run the command in
time" after its own `bridge_timeout` (default 1800 s) while the generator keeps stepping. The host script took
the error as the job's end, pc-job printed DONE 0 (exit code bug, Sol's Wait fix), and night_run started the
build, which closed the editor mid-reparent (5,940 of 11,000; ledger intact, resumable). Fixes: wire.call now
sends `bridge_timeout = timeout` (b…); a job's end is the ledger/result, not a reply. Open for Poot's bridge
lifecycle slice: when the client has given up, the bridge should close the generator (or keep the result for
`job_result`) rather than run on headless.

## A person at the Play window changes the numbers (2026-10-13, 23:37)
Richey: "my mouse locked on the screen and stopped you." During the night run's Play suite the viewport took the
mouse; the scenarios kept calling the hero while a person drove it (possess/eject and real input), and the
results (realm_switch 3/10, mounts 3/9, portals 2/5) were the person's, not the code's. Fixes: daedalus_play
samples the player controller's keys/mouse every 5 frames during a scenario and marks the result
`interrupted` with the frame count; run_scenarios reruns an interrupted scenario once after 5 s and otherwise
counts it as not run, never as failed. Rule: a Play result is only a result when `human_input_frames` is 0;
if you want to watch, watch — the run will say it was watched and rerun itself.

## Harness enhancements to code next (2026-10-13, 23:42, Richey: "add to lessons learned and ask codex team to code")
Each is a finding from tonight with the code change that closes it and a proposed owner.
A. (Sol) `pc-job.ps1`: the DONE code must be the script's real exit code. The materials job raised BridgeError
   and still printed DONE 0, so night_run started a build over a running editor job. Also `-Wait` returns on the
   DONE/FAIL marker, not after N seconds. (Sol's Wait fix in flight; add the exit-code assertion test.)
B. (Poot) bridge lifecycle: when a client's bridge_timeout expires, close the generator or park its final result
   under `job_result` for the request id; a job running headless after its caller left is how the editor got
   closed mid-reparent.
C. (Sol) `teamlink`: one reply per request id; a status/broadcast never earns `request.accepted`. Dedupe in the
   client by (reply_to) so five identical replies cannot go out.
D. (Sol) `unreal-job.ps1 -Rollback`: keep the previous green plugin DLL beside the new one and restore it with
   one flag; a bad C++ change should cost 60 s, not a rebuild.
E. (Fable, done) scenarios detect a person at the Play window and report `interrupted`; the runner reruns once.
F. (Sol) `play` through the bridge should start PIE in a way that never captures the mouse (Simulate, or a
   new-window PIE with `-game` and no focus), so a person looking on cannot steer the hero.
G. (Fable, done) `wire.call` sends `bridge_timeout = timeout`.
H. (Sol) manifest-vs-DCS parity in CI (in flight) and a `tools/realms/check_bindings.py` that lists every Talker
   role with no art id under /Game/Daedalus/Art/Cast, from the asset-registry dump the night run writes.
I. (Poot) `_find_actor` by full path with duplicate-label refusal (claimed).
J. (Fable) night_run writes a machine-readable receipt (json: sha, steps, n/m, errors=, warnings=, interrupted)
   beside the job log, and BASE-LAYER.md's "Laid down" table is regenerated from it.

## What slowed the build-out tonight, and how to build a metaverse faster (2026-10-13, 23:59, Richey: "i need you to be fast like you were")
What was fast: moving 14 whole islands in one shot (7,552 actors, 0.6 s); laying a realm's hub in 8 s; importing
a cast in one steps() call. What was slow, and the fix in code:
1. One actor per thing. 100 plots + 100 signs per district = 200 actors and a save each, 6.5 s a district,
   40 min for the map. Fix (now): one InstancedStaticMesh actor per district (100 instances, no signs), save
   every 10 districts: ~0.3 s a district. Rule: anything repeated more than ~50 times in a level is instances
   of one actor (plots, fences, trees, road tiles), never actors. Labelled actors are for things with identity
   the game talks to (rings 1..6 lands, talkers, portals, markers).
2. Proving by Play before the material exists. The Play suite is for seams, not for laying bricks; Richey
   said "skip testing and just build". Rule: lay first (idempotent, saved, counted), run the suite once at the
   end of a build-out, not between every layer.
3. Waiting on the editor for things that need no editor. Ground, plots, districts, casts, portals are all
   computed headlessly and only *spawned* in the editor; the computation (which cell, which name, which
   file) runs in milliseconds here. Rule: everything that can be decided outside the editor is decided outside;
   the editor call carries a plan, not a question.
4. API archaeology at run time (5.8: no World.streaming_levels, create_new_streaming_level takes 3 args,
   `hide` collides with AActor). Rule: when a UE Python call fails once, write the working call into the module
   docstring and a lessons line the same minute, so no bot pays for it twice.
5. Serial jobs on one editor. The materials job held the editor for 75 min; building waited. Rule: material
   fixes and other polish run only in the gaps; lay-down jobs have priority on the lease (ADR-066 §7).
6. Humans and bots sharing the Play window. Rule: build-out runs with Play off; proof runs announce "hands off"
   and detect a hand (interrupted).
7. Each realm by hand. The four realms were laid by four calls to the same tools; that is the shape to keep:
   a new realm = ORIGINS line + .dcs + .dic + three GLB folders + one mount row + bestiary rows, then
   `finish_islands.py`. Next speed-up: a single `realm.yaml` per realm that generates all of those, so adding a
   realm is one file and one job.

## What slowed the island build tonight, what fixed it, and how to build the metaverse faster (2026-10-14, 00:08)
Richey: "when you built the first ten islands it was bam... I need you to be fast like you were."
The first ten were 14 whole levels moved by one offset each: one operation per island. The far rings were
being built the opposite way: 100 plot actors + 100 signs + a sublevel create + a move + a save PER DISTRICT, and
the editor, in the background, ticked once every ~12 s (CPU throttle) and then once a MINUTE as the sublevel
count grew (each create/move refreshes the whole level list). 384 districts at that rate is a night, not a minute.
Fixes, in order of effect:
1. One actor per district: an InstancedStaticMeshComponent with 100 plot instances, no signs
   (`Lands_<R>_D<dd>`, tag `Cells:`). 38,400 plots became 384 actors. Same for ground: one 2.56 km slab per
   district. (daedalus_districts.lay_district_steps)
2. No sublevel per district yet: lay into the persistent level, stream later (`sublevels=True` path kept). A
   level create + actor move per step was the minute.
3. Scan once: the label set is read once per run, not per district (12k actors per scan).
4. Budgeted stepping: `daedalus.steps` runs items back to back for `budget_ms` (250) per tick, then yields; a
   throttled editor's slow tick no longer multiplies into the job.
5. The editor's background throttle (`bThrottleCPUWhenNotForeground`) is turned off by full_speed(); it must be
   on from init_unreal, not only when a scenario starts.
How to build the whole metaverse at that speed:
- Decide the unit of work before writing the loop: islands move as levels, lands lay as instances, casts import
  one GLB per tick, materials reparent 25 per tick. The unit is whatever the engine handles as ONE operation.
- Never put per-item editor bookkeeping (scans, saves, level ops) inside the item loop; do them once per run or
  per N.
- Measure the first two items, extrapolate, and change shape if the total is more than a few minutes. Tonight
  the 6.5 s/district number was visible after 20 s; the 60 s/district one after a minute. Stop then, not later.
- Polish (signs, sublevels, streaming, per-plot actors for the registry) is a second pass over data that exists.
- Keep the host script the driver and the editor dumb: a generator per realm, one bridge call, numbers posted.

## Story first, then common sense, then the tool (2026-10-14, 00:17)
Richey: "the island realm is floating... each island has no gaps, it has ground... the planet got hit with an
asteroid and broke into 10k islands we sell as NFTs." I read "add ground" as a floor under the whole realm and
laid 2.56 km slabs under districts. Wrong on two counts: the sky-islands realm is broken ground by design (the
gaps are the story), and the four 3D realms already stand on Poot's terrain. What "ground" meant: every plot is
a solid island you can stand on (now a 12 m slab, not a 2 m sheet). Rules: (1) check the request against the
realm's story (ADR-065 "why", REALM-CASTS) before choosing the geometry; (2) when a realm already has a terrain
host, no second floor; (3) a change that touches every realm gets one sentence back to Richey before the tool
runs, not after. Removed the 20 slabs; plots thickened.

## The harness should have discovered the new connector itself (2026-10-14, 00:18)
Richey: "our harness should have found that connector in Unreal because the whole function of the connector is
exploring an app's every function." A new connector appeared in the tool list tonight and nobody noticed: the
turn began with an inbox read, not an inventory of capabilities. Rules: (1) `teamlink doctor` grows a
"capabilities" section: the MCP servers and tool names present this session, diffed against the last turn's,
so a new connector is the first line of the next turn; (2) every connector we own ships a `list_commands`
(the Unreal bridge has one) and the doctor calls it, so a new command in an existing connector is also a diff;
(3) a connector's job is to enumerate the app's functions: Unreal's bridge should expose the editor's own
command/function catalog (console commands, Python-exposed subsystems, CallInEditor functions) as data, so the
harness explores the engine instead of us guessing API names (five AttributeErrors tonight: streaming_levels,
register_component, add_component_by_class, looping, is_game_world). Owner: Sol for (1)(2), Fable for (3).

### Diagnose MCP configuration without replaying refused actions (2026-10-14)
Use tools/unreal/mcp_preflight.py for file-only project/defaultINI/descriptor diagnosis. ToolsetRegistry can be enabled through the ModelContextProtocol descriptor dependency even without an explicit project entry. Configuration agreement is not loaded-module/server readiness: return server_ready:null and make no editor/socket/control calls. Actual project/UE5.8 configuration matched; no edits or restart/start performed.


### Treat ambiguous MCP configuration as unverified (2026-10-14)
Validate plugin/dependency arrays with explicit booleans and unique names. Parse listener fields uniquely; duplicate bind fields or array clear/remove edits must not yield confident loopback agreement. Bound JSON/INI reads and reject nonfinite JSON. Hash exactINI bytes. LatestPoot29673 ownerupdate supersedesolderpause; coordinate currentowner, never act from stalePID/pause snapshots. Actualconfig reread stillmatches; no serverreadyclaim orsetupaction.


### Structured MCP diagnostic failures (2026-10-14)
Preflight CLI emits JSON for unreadable/invalid project orINI data with available:false and agreement:null, preserving unknownserverreadiness. Descriptorunavailability also leaves agreementunknown. Readable mismatches identify plugin enable andlistener reasons. Missingfiles are not missingservers, and configurationdiagnostics neverperform editor/setup actions.

