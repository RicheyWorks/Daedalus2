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

## Find crafting authority before adopting recipe algorithms — Team Codex, 14 October 2026

[Crafting comparison and adoption handoff](production/SHARDSTEAD-CRAFTING-ADOPTION.md):
a catalog reader, opaque snapshot CAS and an authoritative inventory transaction
are different boundaries. Locate the actual mutation owner and stack/tag/container
model before introducing allocation code. Broad-tag greedy consumption is only a
candidate gap until the real recipe model and matching implementation are known.
Current blocker is that authority/model pointer; no parallel implementation added.

Coordinator reports Cuberite root LICENSE Apache-2.0; Luanti source SPDX
LGPL-2.1-or-later and a bipartite helper; noise/mesher/Brigadier repositories MIT.
These are attributed reference findings, not file-level adoption approval. This
lane copied no code, captured no immutable upstream implementation pin and added
no dependency. Preserve source review versus validation/native/E2E distinctions.


<!-- coordinator-metaverse-research-20261015:start -->
## Compare metaverse patterns with actual code before filling gaps — coordinator, 15 October 2026

The parent supplied primary-source research on Second Life, Resonite and The Sandbox; selected official pages were independently opened here. These are design comparisons, not adopted dependencies or proof Daedalus lacks a feature.

- Second Life's checked asynchronous [llUpdateKeyValue](https://wiki.secondlife.com/wiki/LlUpdateKeyValue) illustrates stale-value rejection and result correlation; [Linkset Data](https://wiki.secondlife.com/wiki/LlLinksetDataWrite) is another storage reference. Neither is a Daedalus capture transaction. Original code should reuse actual host identity/revision/idempotency and atomic persistence interfaces.
- [Object permissions](https://community.secondlife.com/knowledgebase/english/object-permissions-r57/) distinguish copy, modify and transfer, motivating explicit provenance/dependency-rights review before publishing a portable package. [Landmarks and safe travel](https://community.secondlife.com/knowledgebase/english/landmarks-teleporting-and-slurls-r54/) and [Shared Media](https://wiki.secondlife.com/wiki/Shared_Media) are candidate discovery/app-panel patterns. Private/shared state and origin boundaries require actual Daedalus interface evidence.
- [Digital Farm System recipes](https://www.digitalfarmsystem.com/dfs-recipes/) and [KittyCats care/lineage](https://kittycats.ws/manual/article.php?id=190) are third-party ecosystem references, not built-in Second Life farming rules. No scripts, assets or proprietary mechanics were copied.
- Official MIT [ResoniteLink](https://github.com/Yellow-Dog-Man/ResoniteLink) and [Unity converter architecture](https://github.com/Yellow-Dog-Man/Resonite.UnitySDK) inform incremental hierarchy/component patches, shared asset providers and explicit material diagnostics. The Link protocol is beta; session identifiers and exported snapshots are unsuitable durable Daedalus identities/storage, and this is not synchronized gameplay transport. Reuse our connector rather than create a competing bridge. Repository licensing does not replace exact-file/module review.
- The Sandbox's [optimization guidance](https://docs.sandbox.game/en/creator/game-maker/docs/gm-guidelines/optimisation), [creator controls](https://docs.sandbox.game/en/creator/game-maker/docs/build-menus/top-bar), [typed events reference](https://docs.sandbox.game/en/creator/game-maker/docs/game-rules/events) and [Game Maker0.12 release](https://docs.sandbox.game/en/creator/game-maker/version-notes-and-changelogs/game-maker-0.12) motivate measured scene budgets, scoped events and immutable releases. Version0.12 documents multiplayer persistence for items, variables, checkpoints and completed quests; old single-player tutorials cannot establish current limits. Engine/SDK reuse permission was not established, and none was copied.

The actual-code audit uses existing45-identity parity evidence plus current source across identity/inventory, portable items, permissions, quest/progression persistence, creator tools, social/discovery, app interfaces and asset publishing. Classify existing/reusable/partial/missing/unknown separately. A current correction already found: MazePlugin.worldCapabilities, PluginRegistry.worldCapabilities and WorldController.capabilities expose the existing CapabilityRegistry; older documentation claiming no world-capability SPI is superseded. Discovery does not grant authority.

The confirmed bounded creature gap is individual capture-to-player-farm custody/capacity/settlement persistence, not aggregate ecology counts or crop-practice saves. Keep the full Flowers integration and obtain its owner's accepted mutation contract rather than invent parallel authority. New handling policy source can progress with explicit null host bindings and receipt/revision guards. Another candidate under source inspection is reconciling production receipt-ledger owner/evidence/stage against preserved catalog receipts; implement only after confirming the exact current gap and existing owner.

Practical production lessons: inspect authoring imports before use; an existing humanoid helper chain executes scene-wide deletion and an original title CLI writes multiple realms/title metadata. Use isolated, pinned, narrowly scoped successors. Preserve original assets and compare complete same-land inputs with identical final cameras/settings; different seeds are references, not an honest same-land improvement pair. Hashes, source completion, compile results, generated images, native integration and player-visible runtime acceptance remain separate. No financial deployment, new persistent access, proprietary/ComputerPets reuse or bypass of the separate blocked BlackJackPro action is part of this work.

### Consolidated lessons: shared facts and honest acceptance — 2026-10-15 22:58 UTC

Reuse the actual ordered quest core and full apps before inventing a second store or simplified replacement. The herder→Tide-Pen proposal translates only verified scoped receipts into ordered progress; historical care competence is not current creature custody, habitat capacity or crafting authority. Imported and local onboarding must both verify the same account/character/realm/compatible season and current freshness/correction policy, share one recognition/completion key, and hold the original unknown operation after reconnect. Source review caught an asymmetric local OR predicate and corrected it before exact-pin closure. PortalQuest ClaimReward is in-memory only; exactly-once durable progress/award remains an existing-host atomic-transaction requirement. No local journal or aggregate ecology count substitutes for that authority.

Source counters, file fingerprints, compile, images, native first saves, world placement, quality BAR and gameplay acceptance are different stages. The final capability auditcb1f006a… records local four-file catalog commit750933675098aeaeac885f6a780f90be34109c3b and eight authored UNRUN tests; earlier mocked tests do not transfer. Coin auditf6293946… inventories27source+10native/cabinet pins, not37 running integrations. DAED actual contract/payment/award identity is unbound; MULE/local Gold/gems/usage credits stay separate. A successful donor balanceOf helper source read is neither current balance evidence nor permission to connect a wallet.

For the exactly23 original Knights, keep private artifact-gated visibility/dialogue, contextual attraction, action reputation and in-world land/vault access as separate contracts. A future consented read-only wallet input requires verified subject/chain/contract/block/finality/freshness/reorg/privacy rules and an accepted owner; none was executed. The paid holdings-weighted chance/MOST/pool overflow/operator+winners/dev-AI-cost idea is qualitative LEGAL HOLD, with all parameters unset. Documentation is not paid-product approval, implementation or an alternate route around a denial.

Preserve the full Dungeon AI app and separate usage credits; parent found the referenced c579 adapter branch absent in both inspected checkouts. Historical TeamCodex/Astra source and Claude native work still require actual wiring/adoption through the sole operator. Parent-reported current production:217packages/143actors/184Cpp after six Winter4 first saves22:45; world/BAR/gameplay held. Ultra two build exit0 results and eight supplementary JPEGs are not combat/controller acceptance. Its47-file primary-main commit was denied and exact command/reason are pending; do not relabel it committed or retry by another owner. Reedwheel eight-render delivery and parent Library verification are distinct from native quality.

Previously recorded Second Life/Resonite/Sandbox links and latest primary comparisons are parent-researched references retained with their attribution; this batch did not independently browse them. Original WoW-inspired adventure appeal does not authorize copied assets, identities or proprietary source. Preserve each realm's chemistry/genre, give useful collectible purposes, equivalent local onboarding and clear recovery/progress without forced attendance. Keep source/design/null bindings visible until the actual owner supplies runtime/persistence evidence. No tests, builds, renders, hub sends, network or financial/native actions ran for this documentation batch.

### Original land-mechanics comparison checklist — parent research, audit pending

Parent-researched references: [Terrariums v1](https://blog.axieinfinity.com/p/terrariums-v1-is-live) (parent reports Homeland sunset17June2026), [Terrariums v1.1](https://blog.axieinfinity.com/p/terrariums-v1-1-is-live) (current passive collection/plot accessories/evolved parts), [Terrariums Estates](https://support.axieinfinity.com/hc/en-us/articles/54666286201115-Terrariums-Estates) (adjacency), and [historical Homeland beta](https://blog.axieinfinity.com/p/homeland-beta-is-live) (active crafting). This batch did not independently open these links. Compare actual present/partial/missing evidence first; an independent audit is assigned, not complete. Reuse full farm, chemistry, creature, crafting and minigame contracts for original realm-appropriate adaptations, keeping cosmetic quality and active adventures primary. No copied assets/code, Axie feature-parity, NFT staking or financial-return claim.

| Existing milestone/backlog reference | Initial evidence-qualified status and next proof |
|---|---|
| Visual identity+biome; functional biome decorations | PARTIAL art/source evidence; native visual BAR/world acceptance remains held |
| Creature homes; persistent residents; evolved traits/accessories | PARTIAL local livestock/source proposals; individual ownership/care/save and destination chemistry bindings unresolved |
| Production→craft→equipment→adventure; upgrades | PARTIAL original farm/craft app/source interfaces; actual cross-module receipts and gameplay loop unverified |
| Meaningful customization; visible land history | PARTIAL authoring/capability/package source; adopted player workflow and persistent land-history contract UNKNOWN |
| Neighbor adjacency/settlement synergies and collaboration | UNKNOWN in this bounded check; audit actual ownership/permissions/settlement interfaces before any proposed wiring |
| Discoverable story and purposeful collectibles | PARTIAL six-step herder→Tide-Pen proposal/eight null-bound references, no installed quest or configured award |
| Saved progress and reliable realm transitions | PARTIAL existing progression/session source; coupled journal/custody/rejoin/atomic receipt acceptance missing |

Track concrete accepted gaps through the existing BACKLOG.md and existing realm production queues/owner sections after the audit, preserving completed content and versions; this checklist is not another subsystem or blanket missing-feature claim.
Final Knights independent static receipt: task/daed-knights-independent-source-review-20261015.json,7345bytes,SHA256e02cb732a351b3e190930544293608028b0e55bf16a9cc563ed1a7be69dec6ad, CLEAR22:56:56UTC/all four pins. Static clearance is not compilation, generated art or runtime acceptance. ### Final qualified production cutoff — parent updates through22:57 UTC

Parent reports Opus semantic ACK32480 and R3 source/manifest delivery32489:19files, immutableR1/R2, layoutSHA95f7e173… and owner-reported commit591bfc761…. Exact-mesh UCX/anchor policy,8m clearance, rope spans and ledger rows are DESIGN/OWNER-REPORTED, not independently validated by this documentation worker or root; R3 has NO renders. Sky→Tide-Pen collaboration was acknowledged after R3, pending canonical/source-plan reading before writes. Native32486 reports PR147 remote head4c2cdfc6510e59366094abd2e2d077ad432384f8, saved intake unchanged217/143/184. New user-authorized placement/view32491 is SOURCE PREPARATION only, not native execution or a compute claim. Willow export32467 and Poot source32466 have no actual ACK/START in this cutoff.

Reedwheel's eight Library creates succeeded per parent receipt reedwheel-r2-parent-attachments-20261015.json; parent reports17R1/R2pins matched, three paired settings equal and all eight original image hashes recovered excluding metadata in memory. Windows metadata-attribute failure is recorded; no source image was altered. This is delivery/file comparison, not native BAR/gameplay acceptance. Parent's final Dungeon artifact is34227bytes SHA256392f5c5ce1aa932d438ad0bad9cbf0b56e3dff1ea6accdcc8425113c05144f21, superseding33318bytes/2bf432…; its scope remains audit/source, not full connected acceptance.

### Broader land references inside the existing plan — 2026-10-15 23:02 UTC

These are **parent-researched official/official-linked references**, not independently opened by this documentation worker. They extend the same living-land milestones and parent-maintained existing backlog JSON receipt; they create no competing feature backlog, adoption/parity claim, token or financial action. Preserve original Daedalus identity, full implemented apps, immutable versions and confirmed-gap-first code reuse.

| Parent reference | Bounded comparison and uncertainty |
|---|---|
| [Decentraland in-world overview](https://docs.decentraland.org/in-world/overview), [LAND manager](https://docs.decentraland.org/marketplace/land-manager) | Programmable LAND/Worlds and delegated editing patterns; inspect our existing publishing/permission interfaces before proposing wiring |
| [Pixels farm-land docs](https://docs.pixels.online/farm-land-nft) | Productive-farm reference; older numeric claims remain UNVERIFIED, no yield/revenue or current-feature inference |
| [Nifty Island creation](https://guide.niftyisland.com/island-token/token-utility/island-creation) | Creator islands, multiplayer and build-budget reference; no copied numeric budget or economic model |
| [Somnium parcels](https://somniumspace.com/en/documentation/parcels-worlds/parcels) | Persistent parcels/custom-world entry reference; no claim our complete saved entry/rejoin flow is accepted |
| [Voxels discovery](https://www.voxels.com/), [official scripting bundle](https://github.com/cryptovoxels/scripting-bundle) | Discovery and scripting-extension patterns; reference availability is not code/module license adoption or runtime acceptance |
| [Soulbound official-linked wiki](https://wiki.soulbound.game/NFT) | Parent's current read says legacy NFT land has NO FUNCTION; this supersedes the historical2024 apartment-utility reference, not proof of Daedalus functionality |
| Otherside | Current full land/resource economy was NOT verified; make neither missing-feature nor fully-shipped claims |

Six highest-value **code-audit candidates**, mapped into existing milestones rather than a new subsystem:

| Candidate | Initial evidence boundary and existing milestone |
|---|---|
| Persistent/versioned land publishing + rollback | PARTIAL manifests/package/source evidence; actual accepted publish/rollback unknown. Maps to meaningful customization, visible history and saved progress |
| ONE complete replayable land activity | PARTIAL ordered quest/activity sources and herder proposal; a complete replay/rejoin/receipt-backed player loop unverified. Maps to resource/craft/adventure and discoverable story |
| Social discovery + friend joins | PARTIAL bounded presence/world source; complete friend admission/safe-arrival/recovery UNKNOWN. Maps to neighboring-land collaboration and reliable transitions |
| Useful stations/resources | PARTIAL full farm/craft app and local station interfaces; cross-authority inventory/craft receipts unbound. Maps to functional habitat and production→craft→equipment→adventure |
| Collaboration + moderation | PARTIAL existing parcel/permission source; accepted delegated editing/moderation workflow UNKNOWN. Maps to meaningful customization and neighboring settlement cooperation |
| Shared inventory + quest continuity | PARTIAL progression saves/ordered quest source; durable atomic cross-realm inventory/quest/rejoin contracts remain missing or unverified. Maps to saved progress and reliable realm transitions |

Independent audit is assigned, not complete. Refine present/partial/missing/unknown only with exact current code and owner evidence; source discovery does not authorize a new shared writer or claim runtime completion. Reuse existing identity, full farm, chemistry, creature, crafting, minigame, quest and publishing contracts before any additive source claim. Cosmetic quality and active adventures remain primary. No staking, financial returns, asset copying or automatic inventory/currency transfer is proposed by this comparison. Stop this documentation batch here; parent owns the single existing backlog receipt and subsequent production assignments.

### Canonical finite build-out reference — 2026-10-15 23:04 UTC

Use the ONE existing [source/action/evidence checkpoint](DAEDALUS_WORLD_ARCHITECTURE.md#coordinator-buildout-20261015) for the living-land milestones, researched comparison inputs, current priority/owner/package and completion gates. No separate feature backlog is introduced; parent maintains its existing backlog receipt. That checkpoint records R3's material clearance gap: a4.74547m actual vertex-pair witness disproves the global8m claim, without establishing the global minimum; preserve R3 and request source-owned R4 correction. Source proposals/null bindings and financial/denied-action holds remain explicit. This link does not claim runtime or native acceptance.

### Scheduled all-team lessons review — 16 October 2026, 01:21 UTC

Coordinator pootscoot-coordination opened the scheduled session at01:21:54UTC in the existing D2-build/docs/production/TEAM-BLENDER-UNREAL-HARNESS.md, Whole workflow harness backlog. This is the current review checkpoint; earlier status paragraphs retain their historical cutoffs. Individual hub invitations32640–32656 are delivery evidence, not attendance or implementation. The existing coordination-member-audit-20261015.json records named current responses, independently read-back owner documentation and pending coverage; historical18/20 preparation is separate.

Ranked lessons now recorded there: preserve producer/validator/reconciliation states; fingerprint the actual receiver; separate immutable source acceptance from adoption/build/runtime and historical tests; constrain transport before dispatch and release input by retained ownership; separate generated output from pixel quality; state exact geometry/units/transform limits; bind comparison captures to actual app state and pinned assets; retain numeric prelaunch rejection evidence. Benefits and effort are ESTIMATED. Existing named owners retain their current scopes; this review assigns documentation consolidation, not fresh implementation or compute.

Current corrections: Willow's retained three-view exit0 is technically reconciled without rerender, with original failure/13pins preserved; visualFAIL/nativeHELD and no-PID resource-blocked reopen remain. Dungeon's corrected8files/71727bytes are receiving-accepted source-only32635, exact decision3190ea8a…/independent review7d64daa2…;191-source candidate/adoption/UHT/module/link/runtime remain pending. Ultra's four-source adapter/provenance is clear, zero accepted browser pairs, build/capture request32631 still held. R4's numerical static3m geometry is qualified; mixed-material receiving profile remains unaccepted. No historical test green transfers to changed code.

Latest saved native baseline218packages/145actors/184sources/mapf77f83a2… is a file receipt, not a fresh world query. Sole native owner codex-play-guard remains even if a lease expires. The human safe-editor-save/pause/close/191-build decision remains pending. Glorp is a separate user-authorized project with its own owner and future preview decision; no Daedalus scope, second editor, compute lease or Dungeon approval follows. Frozen packages/recipes/failed attempts/user data and other authors remain preserved.

Story/reproducibility discipline: link visible prototypes to their actual narrative purpose/player goal and explicit mechanic stage. Willow's pond remains an opaque preview; Residents is asset-only with no placement. Neither proves living ecosystems, fluid simulation or gameplay. No new lore, realm parity, public release or promised utility was invented by the review. Keep finished lands immutable and name any authorized future polished successor/version separately.
<!-- coordinator-metaverse-research-20261015:end -->
## Team Codex — Willow lessons review, 15 October 2026 Pacific

Scheduled review opened16 October01:21UTC. Named participation hub32657.
Existing package: artifacts/biomes/shardstead/WillowWetland/pilot-r1/stage-plan-r1/.
These are evidence-backed findings and proposed improvements, not implementation
or another compute allocation. Preserve all original source, failed attempts and
other authors. Root consolidates the established Whole workflow harness backlog.

1. **Portable receipt paths and failure reconciliation.** Frozen producer0f77409d
   wrote Windows `views\\name.png`; validator38bc9c28 compared forward slashes.
   The one matched-view process exited0 in80.1215451s, then validation failed.
   Root's independent, separately retained comparison-only normalization passed
   against the SAME three PNG hashes; reconciliation receipt
   C:/Users/730ri/Documents/Codex/2026-10-14/task/willow-views-validator-reconciliation-20261015.json
   SHA256 a7f6023888a280354d83d6d73454345a385e902b9bfcf999bfe5281a6b38bcdf
   was read and hash-verified for this review. No rerender, original rewrite or
   quality acceptance followed. Reproduce diagnosis by comparing original
   views.json paths with validator line's expected views/name.png; retain exact
   path allowlist/root containment/hash checks when normalizing separators.
   Proposed owner: Team Codex/ROOT's existing validator reviewer. Next permitted
   step: propose a versioned future validator contract at existing source-review
   gate, not alter frozen bytes. Benefit ESTIMATED: avoid false post-render holds;
   effort ESTIMATED small. No measured speedup or general adoption claim.

2. **Export success is not a finished visual asset.** Three original roles total
   67,832B/1,776tri/4slots passed byte/mesh/material/bounds review. The three
   actual matched1000x1000 AgX/Cycles CPU24sample views were personally inspected:
   skeletal willows, thin reeds, dark pond-edge ring/path seam and empty/clipped
   composition failed the user's visual bar. views-review-r1.json SHA256
   28ae02e55f38bc28fe068345252fe71d33c6e5122009de5a8c37fabcaea4524c
   retains exact PNG pins/settings/findings. The author/export/technical-render
   stages remain complete while visual/native acceptance remain HELD. Proposed
   owner: Team Codex visual kit; codex-play-guard only for later native receiving.
   Next step requires explicit versioned source-polish approval and later render
   allocation; neither granted by this review. Benefit ESTIMATED: spend scarce
   native ingestion time on finished candidates; effort ESTIMATED medium. Actual
   pixels prove this pilot's gap, not a universal quality score or native cause.

3. **Retain prelaunch resource readings even when no PID starts.** Reopen grant
   willow-pilot-reopen-r1-20261015T2355Z stopped at unchanged physical1,700,000/
   virtual2,200,000KiB floors. No process/PID; compute unlock/readback succeeded
   23:55:43.4583826UTC. Attempt failure4c726f7b and releasee6854141 retained under
   attempts/. Numeric readings were not persisted on that branch, so the exact
   failing value/floor is UNKNOWN. Proposed owner: Team Codex local stage-wrapper
   source; Poot is support reviewer, no shared-harness takeover. Next permitted
   step: propose a new-version prelaunch receipt that stores the existing fresh
   readings before the guard, without lowering floors/retrying this attempt.
   Benefit ESTIMATED: actionable blocker diagnosis; effort ESTIMATED small.
   No new source implementation, rerun or changed safety threshold in this review.
