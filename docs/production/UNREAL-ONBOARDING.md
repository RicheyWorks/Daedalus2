# Unreal onboarding (for Unreal Epic Boss, `unreal-epic-boss`)

Created 2026-10-19 by Prometheus on Richey's order (relayed by Buffffff). One section per owner; add yours below.

## Prometheus — Island audio + Turing music engine

Repo is RicheyWorks/Daedalus2 unless noted. Status words: ON MAIN = merged; OPEN = not built.

**Java Island Audio core (ON MAIN).** `daedalus-core/src/main/java/com/daedalus/world/audio/` (15 classes: BiomeAmbience, AmbienceState/Layer, Biome, CallSynth, CallSpec, Genome, Species, Herb, HerbChord, JukeboxClient, JukeboxTransport, HttpJukeboxTransport, Rng, Wav). Landed in 3d964b4b, synced to main at b1716c10. Deterministic from seed, JDK only.

**AUD 1 endpoint (ON MAIN, PR41, team-codex).** `POST /api/v1/audio/design` returns text AUD 1: ambience layers + one PCS 1 creature call + jukebox cue. Contract `docs/contracts/aud-v1/README.md`. Auth: `daedalus.audio.host-subject` must equal the engine JWT subject.
**PR44 (PootScoot, DRAFT, not merged).** Native consumer `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusIslandAudio.cpp` + portable `DaedalusAudioCore.h`: decodes AUD 1, renders calls off the game thread, binds ambience by layer id. Compiled in an isolated host only; no Play proof; needs an actor binding and looping ambience assets.

**HRB 1 herb-chord endpoint (ON MAIN, 62ca681a).** `POST /api/v1/audio/herb-chord`, herbs -> `chord <root> <quality> <effect> <strength>` + `freq` lines. Same auth/rate limit as AUD 1. Contract + fixture `docs/contracts/hrb-v1/`. AUD 1 unchanged.
**HRB 1 C++ decoder (ON MAIN, 584b40e9).** Header-only `engines/unreal/core-test/hrb1/DaedalusHerbChordCore.h` (no UE deps), 33 checks incl. the Java-pinned fixture; `python engines/unreal/core-test/hrb1/run_hrb1_core.py --compiler cl.exe` (or g++ --sanitize).

**Prometheus Island (UE).** Sublevel `/Game/Prometheus/Maps/PrometheusIsland` in DaedalusWorld, origin (2000000, 2000000, 0) cm (`data/islands/prometheus/ue_transforms.json`). 24 AmbientSound emitters: 18 genome livestock calls (`PI_Call_*`, assets `/Game/Prometheus/Audio/Calls/`) + 6 beds (`PI_Snd_Stream_*`, `PI_Snd_IslandSong`). Demo stills (editor-world SceneCapture, no audio): `data/islands/prometheus/PI_audio_demo_{calls,call_close,ambience}.png` at 9d2c58ff. Known issue: terrain mesh vs heightmap mismatch ~6 m mean abs (shape, not placement; rotation r5 and translation r6 fits both failed). Wild Biomes scripts `engines/unreal/prometheus-island/wild-biomes/` are BLOCKED: target sublevel WildBiomes_* does not exist.

**Jukebox.** Asset `/Game/DaedalusAudio/SW_Jukebox_e00015` (placer `engines/unreal/prometheus-island/wild-biomes/daedalus_audio_quickplace.py`). Music engine: RicheyWorks/rd-music-nft `rd-music-nft/packages/rd-studio/` at 10e9b98 (Python; CC0 VSCO-2 CE samples fetched by `tools/fetch_r4.py`). Java `JukeboxClient` calls Art Master Flex's `/api/v1/jukebox` (client only; retries + breaker).
**Ear rules (keep in UE mixing).** No bright or piercing tones (beds low-passed, calls LP ~2.5 kHz), passing notes light, warm vinyl/headphone target; forest-cave and spacey sounds are never removed, only added to.

**Ecology x audio (agreed with Pythagoras, link 47958 / reply 48008; Java side OPEN, not yet on main).** Planned `AmbienceEcologyAdapter.sample(BattlefieldEcology eco, x, y) -> EcologyAmbience{burning, cover, concealment 0..1}`: burning fades in fire crackle and ducks creature calls; cover/concealment apply a gentle low-pass and volume dip. UE mirror uses the existing `UDaedalusEcology::BurningAt/CoverAt/ConcealmentAt` in `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcology.h` (on main, 8ef8c75b).

**Open for the Unreal lead.** (1) Native HRB 1 consumer in UE (include the decoder, map effect -> gameplay/sound). (2) Audible playback proof (PIE capture with audio) for AUD 1 / calls / beds. (3) Runtime bridge: land PR44, bind PrometheusIsland emitters to it. (4) Terrain re-export to fix the 6 m mismatch. All Unreal writes go through codex-play-guard.
## Pythagoras: Battlefield Ecology + PCG island

Owner: pythagoras. Repo: RicheyWorks/Daedalus2. Relevant main commits: `7daf410d` (Java ecology + CoverField),
`dafbbf00` (C++ core + `UDaedalusEcology`; exception-free fix `f377c3bb`), `8ef8c75b` (battlefield-check module +
offline Java->C++->Java round trip + evidence), `436e73b7` (pcg-ecology/tools).

### What it is
Reactive Battlefield Ecology (ADR-061, `docs/adr/ADR-061-battlefield-ecology.md`): a grid of vegetation that gives
cover and concealment, burns and spreads fire with wind, and regrows by succession. It is deterministic from seed +
events. Java is the authority; Unreal reads snapshots and sends combat events back.

### Source map
| Part | Path |
| --- | --- |
| Java package | `daedalus-core/src/main/java/com/daedalus/world/battlefield/` (`BattlefieldEcology.java`, `Vegetation.java`, `Dbe.java`, `BattlefieldDemo.java`, `BattlefieldBench.java`) |
| Director wiring | `daedalus-core/src/main/java/com/daedalus/world/tactics/SquadDirector.java`: `SquadDirector.CoverField` has the same shape as `BattlefieldEcology::bestCover(ux, uy, thx, thy, radiusCm)`, so the ecology passes in as a method reference; the director never sends a squad into a burning cell |
| Java tests | `daedalus-core/src/test/java/com/daedalus/world/battlefield/` (`BattlefieldEcologyTest`, `BattlefieldDemoTest`, `DirectorCoverIntegrationTest`, `EcologyRoundTripTest`); `daedalus-core/src/test/java/com/daedalus/world/tactics/CoverAwareDirectorTest.java` |
| C++ core (plain C++17, no UObject, no exceptions) | `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcologyCore.h` (namespace `daedalus::ecology`: `ReadSnapshot`, `Field::CoverAt/ConcealmentAt/BurningAt`, `WriteEvents`) |
| Unreal wrapper | `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcology.h` and `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusEcology.cpp`: `UDaedalusEcology : UWorldSubsystem`, Blueprint-callable `LoadSnapshot`, `LoadSnapshotText`, `CoverAt`, `ConcealmentAt`, `BurningAt`, `QueueEvent`, `FlushEvents`, `LastError`, `Stats`, `GetEcology`. Default files `Saved/Daedalus/ecology.dbe` (in) and `Saved/Daedalus/ecology_events.dbe` (out) |
| C++ test (no Unreal) | `engines/unreal/core-test/ecology_core_test.cpp` (21/21; CI step in `.github/workflows/engines.yml`, gcc ASan/UBSan). Fixtures: `engines/unreal/core-test/ecology_roundtrip.dbe` (Java `BattlefieldDemo.scene(7)`), `engines/unreal/core-test/ecology_roundtrip_events.txt` (C++-written IGNITE; regenerate with `ecology_core_test --write`) |
| In-editor check | `engines/unreal/battlefield-check/` (`README.md`, `BattlefieldCheck.java` snap/apply, `battlefield_check_ue.py`) |
| PCG island + Wild Biomes | `engines/unreal/pcg-ecology/` (ecology rules, live PCG, island flora, succession sim, quests; pytest 28/28; `ISLAND.md`, `MECHANIC.md`, `ADVENTURE.md`, `README_WildBiomes.md`; bridge client `ue_send.py`; `tools/` probes; `evidence/` screenshots) |

### DBE 1 / DBE-E 1 contract (plain text, all or nothing)
```
DBE 1                                       snapshot, Java -> Unreal
grid <w> <h> <cellCm> <originX> <originY> <seed>
tick <n>
row <j> <w vegetation codes>                exactly h rows, j = 0..h-1 in order
fire <i> <j> <ticksLeft>                    zero or more, after the rows; ticksLeft 1..64; bare/wetland cannot burn

DBE-E 1                                     combat events, Unreal -> Java
event <IGNITE|BLAST|DOUSE> <x> <y> <z> <radiusCm>      at most 256 events (Dbe.MAX_EVENTS / MaxEvents); radius <= 100000
```
Vegetation codes (cover / concealment): `.` bare 0.00/0.00, `m` meadow 0.05/0.35, `s` scrub 0.25/0.65, `p` pine
0.55/0.70, `o` oak 0.80/0.60, `w` wetland 0.10/0.40. World X/Y map to cells by `floor((x - originX) / cellCm)`,
clamped to the grid (same in Java and C++). Errors: one bad line refuses the whole spec with `DBE line <n>: <reason>`
(Java throws; C++ returns `Result{Ok=false, Error}`; `UDaedalusEcology` keeps the old field and exposes `LastError()`).
CRLF is accepted.

### Status and the pending in-editor check
- `BOARD/ARCHITECTURE.md` (bot-team), row "Reactive Battlefield Ecology": **BUILDING**. Everything off-editor is on main and
  tested; the plugin compiled with RunUAT BuildPlugin (UnrealEditor + UnrealGame Win64).
- Not yet in the running editor: the plugin copy the editor loads, `C:\Unreal\DaedalusRealm\Plugins\DaedalusLink` on
  BLACKBEARD, is stale (no `DaedalusEcology*`, and no Streamer/Tactics/Homestead from main). It needs codex-play-guard
  (sole native writer) to sync it from main, rebuild, and restart the editor at a safe point with everyone's work saved.
- Then run ONE read-only check per `engines/unreal/battlefield-check/README.md`: `BattlefieldCheck snap` ->
  `battlefield_check_ue.py` via `engines/unreal/pcg-ecology/ue_send.py` (load, 5 queries, 1 IGNITE flushed) ->
  `BattlefieldCheck apply` (oak at 2000,1500 burning). No import, save, place or bind. When it passes the row moves off BUILDING.

## 2Hot2Trot — Core Unreal operations (launch, harness, pipeline, evaluation, worktrees, crashes, comms)

Written 2026-10-19 by 2Hot2Trot (Studio CEO, `2hot2trot`) on Richey's order, relayed by Buffffff. Each numbered part stands on its own, so any new bot can read just the part it needs. Every path below was checked on BLACKBEARD or GitHub on 2026-10-19. Anything I could not check is marked **UNVERIFIED**. Times are Pacific (PT) unless marked UTC.

Where things live:
- Repo `RicheyWorks/Daedalus2` holds this doc at `docs/production/`. The folders `C:\Users\730ri\projects\D2-build`, `Daedalus2-bb-wt`, `D2-ceo*` and the others are worktrees of that one repo. There is no separate "D2-build" repo.
- `C:\Users\730ri\projects\bot-team` is local to BLACKBEARD and not on GitHub. It holds `BOARD\` (plans, lessons, live view), `art\` (the art handoff board) and `link\` (the team link).
- `C:\Users\730ri\projects\studio-screen-connector` is a clone of `RicheyWorks/studio-screen-connector`, which holds the watcher, capture and build view.
- The Unreal project is `C:\Unreal\DaedalusRealm\DaedalusRealm.uproject`. The engine is `C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe`, version UE 5.8.3 (CL58210709, per `Engine/Build/Build.version` in the lessons file).

### 1. How Unreal is launched, and who may touch it

**Hidden launch.**
- The crash guard in `studio-screen-connector\crashguard.ps1` relaunches the editor hidden. It calls WMI `Win32_Process.Create` with a `Win32_ProcessStartup` whose `ShowWindow = 0` (lines 147-148). No window appears and the user's focus is never taken.
- Build jobs in `engines/unreal/unreal-job.ps1` start through the same WMI call, but with `ShowWindow = 7` (minimized, no focus).
- Standing rule (relayed by Buffffff): jobs never show windows, so always launch hidden.

**Flags.**
- `engines/unreal/setup-unreal.ps1 -Open` always adds `-d3d11 -gpucrashdebugging` to the editor's arguments (commit 45e91309). That script itself starts the editor with `Start-Process`, not WMI.
- The reason is a lesson from hephaestus (2026-10-13 05:58). A no-flag D3D12 launch hit a GPU page fault twice while importing. `-d3d11` avoids that path, and `-gpucrashdebugging` makes DRED record breadcrumbs.
- The crash guard on its own adds `-d3d11` after 2 crashes within 60 minutes (`crashguard.json`: `d3d11_after_crashes`, `crash_window_min`). Its `extra_args` is empty, so add `-gpucrashdebugging` there if you need it on every relaunch.
- Read-only snapshot at 00:3x PT on 2026-10-19: the only running `UnrealEditor.exe` was codex-play-guard's disposable evaluation project (`...\DisposableMCPR7\DisposableMCPR7.uproject`, MCP port 18877), not DaedalusRealm. Check before you assume which project is open.

**Sole editor writer: codex-play-guard.**
- `bot-team\BOARD\LANES-UNREAL-CODEX.md` has a dated roster override (2026-10-15T03:01Z, `poot-haiku-cancel-20261015`). It says Unreal/editor production custody is **SOLE codex-play-guard**, and Claude does not get editor custody back.
- Rules from 48059 (2026-10-19): Grok bots submit packets. They never open the editor, call native code, or adopt anything without the operator.
- Why: one shared editor and one writer prevents the lost turns, crossed replies and unsaved-work collisions recorded in the crash history (part 7).

**Requesting an editor turn.**
- Send a `NEED` on the team link with structured `to=pootscoot-coordination`. Include:
  - the exact ask
  - the files, commits or packets involved
  - what "done" looks like
  - the default you will follow if nobody answers
- PootScoot routes the request to codex-play-guard. Real examples: 47969 (asking team Codex to open and merge a PR) and 48069 (PootScoot asking codex-play-guard for a test window).
- Longer-lived editor needs also go in `bot-team\BOARD\UNREAL-QUEUE.md`, newest at the bottom, with priority, ask, done-when and status.

**Editor rules.** These are standing rules relayed by Buffffff. The lessons each comes from are in part 7.
- **One editor at a time.** Never start a second Unreal editor.
- **Stop Play between tests.** Leftover Play-in-Editor (PIE) blocks imports; see playguard in part 2.
- **Restarts need approval.** Restarting or relaunching the editor needs Richey's OK or a GO from Buffffff. Any turn that builds C++ counts as a relaunch: `unreal-job.ps1 -Start` closes and reopens the editor.
- **Import READY art first, then build.**
- **Check that the editor is alive with a real Python round trip**, not by process or socket checks. A GPU-dead editor still holds port 9877 open.

### 2. The harness watcher (studio-screen-connector)

All of these live in `RicheyWorks/studio-screen-connector` (BLACKBEARD clone at main 7ab51e3). The README in that repo is the full reference.

**Tidy watcher (`tidy.ps1 -Watch`).**
- `tidy-start.ps1` starts it hidden through WMI and holds a single-instance lock in `tidy.lock`. Use `-Status` and `-Stop` to check or stop it.
- Every 3 s it closes floating Unreal tabs listed in `tidy.json`. It never touches the main window or dialogs, and it skips while Unreal is importing or busy (e75c1d8). That skip exists because closing the Content Browser mid-import crashed D3D12.
- It also runs the two guards below.
- **Not running at the 2026-10-19 00:3x snapshot.** No `tidy` process was found, so the crash guard and play guard are not active right now.

**Crash guard (`crashguard.ps1` + `crashguard.json`).**
- **Crash reporter dismiss:**
  - Trigger: no editor is running, `CrashReportClient(Editor)` is alive, and the log tail shows `Critical error`, `Fatal error` or `DXGI_ERROR`.
  - Action: it kills the crash reporter without sending anything, posts `BLOCKED` on the link, restores autosaves and relaunches hidden.
  - It writes `bSendUnattendedBugReports=False` to `C:\Unreal\DaedalusRealm\Config\DefaultEditorSettings.ini`.
  - It never relaunches while UnrealBuildTool or AutomationTool is running, or while an editor is up.
- **Autosave restore:**
  - UE 5.8 has no auto-restore setting, and `-AutoDeclinePackageRecovery` and `-unattended` both throw the restore list away, so never launch with either flag.
  - Before relaunching, the guard copies each `PackageRestoreData.json` entry from `Saved/Autosaves` over `Content`, backing up overwritten files under `bot-team\backups\crashguard-<stamp>`. It then loads and saves the restored packages through the bridge.
  - Manual run: `.\crashguard.ps1 -RestoreOnly` (only with the editor closed).
  - A `Restore Packages` dialog cannot be clicked, because Slate exposes no controls. The guard handles it by kill, restore and hidden relaunch.
- **DX11 fallback:** `-d3d11` is added from the 2nd crash inside `crash_window_min` (60).
- **Known gap** (codex-play-guard audit, 2026-10-15): an assertion crash such as `NumUVs>0` matched none of the guard's log signatures. Assertion classification is still open.

**Play guard (`playguard.ps1` + `playguard.json`).**
- Every 15 s it sends the bridge a `ping` and reads `result.playing`.
- It sends `stop` only when either:
  - PIE has been on for more than 8 min while `bot-team\art\STATUS.md` or `QUEUE.md` has READY rows, or
  - STATUS has said "Waiting on: Unreal to leave Play mode" for more than 3 min.
- Each stop is posted to the link from `2hot2trot`.

**Turn audit (`audit.ps1`).** A read-only check that a turn ended clean: Play stopped, nothing dirty, no floating panels, no dialogs. It never fixes anything.

**Blender splash fix.**
- Blender 4.3 has no `--no-splash` flag; the splash is the user preference `show_splash`.
- `set-blender-prefs.ps1` runs `blender -b --python blender_prefs.py` with user prefs loaded (never `--factory-startup`). That sets `preferences.view.show_splash = False` and saves `userpref.blend`.
- `-Live` sets the same preference in a running Blender through bridge 9876.
- The local-only launcher `%LOCALAPPDATA%\Daedalus\ops\start-blender-bridge.ps1` calls it. That launcher is deliberately kept off GitHub; it is the only file in that ops folder besides its `.bak-presplash` backup.

**Build view (the "view items").**
- `status-loop.ps1` refreshes every 60 s. Each pass runs `status-capture.ps1` (which reuses `capture.ps1`, with the same allowlist and denylist) and then `statuspage.py`.
- Output goes to `C:\Users\730ri\projects\bot-team\BOARD\live\`: `index.html`, `status.json`, `capture-state.json`, `blender.png`, `unreal.png`. The loop's PID is in `loop.lock`.
- The page shows:
  - bridge health for 9876, 9877 and 9890
  - art-queue counts and last events
  - each bot's last post and recent CLAIM/DONE/STATUS lines (secrets redacted, HTML escaped)
  - the screenshots
- Start it with `open-build-view.cmd` (or `.ps1`), which refreshes once, starts the hidden loop and opens the page. Use `status-loop.ps1 -Once` for one refresh and `-Stop` to stop it.
- Running at the snapshot: PID 46772, with `-BlenderBridge` on. `unreal.png` was last written 2026-10-18 23:27, so it is stale.

**Minimized-editor capture (SceneCapture2D).**
- `capture.ps1 -Op capture -Target unreal` falls back to the bridge when the editor is minimized, hidden or blank (commit c42c873, 2026-10-13).
- It spawns a transient SceneCapture2D at the viewport camera, renders one RGBA8 frame, exports it with `RenderingLibrary.export_render_target` to `screens\unreal-bridge-<stamp>.png`, then destroys the actor. Nothing is saved, and `newly_dirty` should come back empty.
- The build view's `-UnrealBridge` switch uses this path. It stays off unless a bot holds an editor turn, because it is still a bridge call into the shared editor.
- Lesson from prometheus: a hidden editor never draws its viewport, so HighResShot writes nothing. Always check pixel stats (max and mean) before trusting a shot.

**Art-queue watcher.** This is the separate importer: `connectors/claude-asset-pipeline/art-queue.ps1` with `asset_pipeline/artqueue.py`. It is off by plan. It must be made turn-aware before anyone restarts it, because it once imported into the live editor without an editor turn (the 05:54 crash in part 7). `art\STATUS.md` was last updated 2026-10-13 06:05.

### 3. The Blender-to-Unreal pipeline

**Bridges.**
- Blender connector: `127.0.0.1:9876`, Blender 4.3.1. Add-on `%APPDATA%\Blender Foundation\Blender\4.3\scripts\addons\claude_blender_bridge\__init__.py` v1.0.2. Repo: `RicheyWorks/claude-blender-connector`; there is no local clone under projects.
- Unreal bridge: `127.0.0.1:9877`, newline-delimited JSON. It is the Python-only plugin `ClaudeUnrealBridge` in `connectors/claude-unreal-connector` (`PROTOCOL.md`, `clients/python/unreal_client.py`) and runs commands on the game thread.
- Official Epic MCP is a different interface: Streamable HTTP, default port 8000, auto-start off. Do not confuse the two.

**Bridge rules (lessons file).**
- Every call gets a request id and a timeout, and you match replies by id (a minimized editor ticks at about 3 fps).
- Call `main()` directly; an `if __name__ == "__main__"` guard runs nothing over the bridge.
- One GLB per bridge call (`tools/unreal_play/import_cast.py`).
- No more than about 150 items per call, and save with `EditorLoadingAndSavingUtils.save_packages` (only dirty packages).
- An interrupted call may still have run, so check the editor's state before reporting anything.

**Pipeline module.**
- `connectors/claude-asset-pipeline` covers Blender export to `.glb`, a file witness, Interchange import and a judge, with the verdict `SHIPPED` or `REJECTED`.
- New reports bind the GLB by SHA256 and byte count before import, and import from a private snapshot under `daedalus-pipeline/import-snapshots`.
- The combat harness is `asset_pipeline/combat_handoff.py`, `combat_report.py` and `combat_fixtures.py`, with spec `specs/combat-slice-1.json`.
- The live slice-1 to-do is `bot-team\BOARD\combat-slice-1\TODO-FOR-BLENDER-TEAM.md`; 0 of 5 assets exist.

**Art handoff board (`bot-team\art\`).**
- `BRIEF.md` is the art brief. `QUEUE.md` holds the rows: TODO, DOING, READY, SHIPPING, SHIPPED, REJECTED, BLOCKED, HOLD, WAITING. `STATUS.md` holds counts and "Waiting on". `feed.jsonl` is the event feed.
- `glb\` is the watched drop folder. `packets\` sits outside the watched folder.
- Names must start with `Tool/Item/Mob/Veh/Bld/Prop/Sky/Wpn_`.

**BIP 1 packets** (`tools/islands/blenderboss/BIP1.md`, `bip_split.py`, `bip_verify.py`; manifest `data/islands/blenderboss/flagship.bip.json`).
- READY at Daedalus2 main a8e9f599. It splits `Prop_Island_Flagship_BlenderBoss.glb` (14.5 MB) into **67 packets**: 28 terrain quadtree chunks plus 39 prop-library packets, covering 1,164 props and 1,730 placements.
- Caps: 12,000 tris, 1.5 MiB and 64 materials per packet.
- `bip_verify` passes 7,461 of 7,461 checks, and source tris equal packet tris (448,046).
- Packets are in `bot-team\art\packets\flagship\`.
- Ingest **one packet at a time, inside a claimed turn, never from the art watcher: terrain first, then the prop library, then placements**. Only the sole Unreal writer does this, on `-d3d11`.
- Not yet imported.
- blender-team works in `C:\Users\730ri\projects\Daedalus2-bb-wt`, and also briefed Unreal Epic Boss directly (link 48073).

**Acceptance means import, save, then a fresh reopen.** These are separate stages; one passing does not prove the next. The reference run is codex-play-guard's static-FBX acceptance r2, 2026-10-19 05:24:52 UTC, in the lessons file:
1. Import exactly one pinned file into a fresh namespace.
2. Check the owned asset's class, bounds against the frozen tolerance, topology and material slots.
3. Save the exact non-empty allowlist and confirm it returns true.
4. Close the editor normally.
5. Reopen in a **different process**.
6. Compare the saved package bytes and facts.
7. Confirm the main project was preserved.

That run also caught a units bug: a stock-wrapper import came out 4 x 1 x 0.5 cm instead of 400 x 100 x 50 cm. Its opt-in unit adapter is on draft PR147. A cached load in the same process is not a reopen.

### 4. Official UE 5.8.3 MCP and the Slate evaluation

**r1 (isolated, run by codex-play-guard).** 2Hot2Trot's independent review is link 47891, 2026-10-18 23:19, verdict `PASS_DISCOVERY_STATUS; SESSION_RECOVERY_UNPROVEN`.

What passed:
- missing session returns 400, unknown session returns 404
- initialize negotiated protocol 2025-06-18
- `tools/list` returned the 3 meta-tools
- `list_toolsets` returned one AutomationTestToolset
- `GetTestStatus` answered

Gaps:
- Recovery was never exercised. The 404 test used a made-up id, and nothing used a deleted session afterwards.
- The DELETE calls are not verified on the server side, because no request headers were recorded.
- `serverInfo` is empty.
- Results are JSON-in-JSON.

Proposed fix: on "Unknown session id", re-initialize **once** and replay only allowlisted read-only calls. Never auto-replay mutations. Record the `Mcp-Session-Id` sent with every request.

**Later results (lessons file, 2026-10-19).**
- Live asset inspection passed.
- One FBX import, save and reopen passed (part 3).
- Paired warm read: bridge median 16.03 ms vs MCP 31.73 ms, n=2 each, so there is no MCP speedup claim.
- Blueprint, Automation and DataValidation are still under test.
- The main-project catalog has **52 unique toolset IDs** (corrected from 67). That is exposure, not 52 tested capabilities.

**SlateInspector contract.**
- The installed experimental toolset is `SlateInspectorToolset.SlateInspectorToolset`, with Windows, Observe, Snapshot, Screenshot, WaitFor and Unobserve.
- UI acceptance is untested.
- Codex's read-only result consumer is on branch `codex/epic-slate-results-20261019` (head acf9ab7a, not merged at the time of writing): `tools/unreal_mcp/slate_inspector_results.py` and `test_slate_inspector_results.py`. Key points:
  - It is pure and has no transport.
  - Snapshot returns plain accessibility text, not JSON, and may come from a cache.
  - `Windows(list)` gives indices and titles only.
  - `NATIVE_RUNTIME_QUALIFIED = False`.
  - Source hashes are pinned.

**2Hot2Trot's Slate packet-adapter turn.**
- When: 07:50-08:20 UTC on 2026-10-19 (00:50-01:20 PT), the Grok half of the 30-minute rotation in 48059. Codex has 07:20-07:50 UTC.
- What: one isolated adapter plus tests that build execution packets from Codex's contract and the 52-ID schema. New files only, no transport, no shared-file edits. Stop at a save/test checkpoint and hand off findings.
- Branch `grok/slate-packet-adapter`, **UNVERIFIED**: it did not exist on GitHub at the time of writing, because the turn had not started.

### 5. D2-build and TEAM-BLENDER-UNREAL-HARNESS.md

**What D2-build is.** `C:\Users\730ri\projects\D2-build` is a git worktree of `RicheyWorks/Daedalus2` (gitdir `Daedalus2\.git\worktrees\D2-build`). At the time of writing it was detached at 550e88fd with local changes, so treat it as someone's working folder, not a clean mirror. The production docs it shows are `docs/production/` on Daedalus2 main.

**What [TEAM-BLENDER-UNREAL-HARNESS.md](TEAM-BLENDER-UNREAL-HARNESS.md) says** (Codex, 2026-10-13). It is the shared Codex, Claude and Grok handoff contract:
- Use the existing teamlink/live_handoff protocol. A queued message is not acceptance.
- The producer sends one artifact-first request, and the consumer ACKs and returns a source hash and a planned integration window.
- Engine mutation needs the shared lease. Never restart just because something timed out.
- Carry exact artifact identity from export to runtime.
- Build complete is not success. A saved scene is not playable acceptance.
- Implemented so far:
  - GLB SHA256 plus byte-count binding before import
  - private import snapshots
  - atomic partial failure receipts
- Next:
  - durable accepted/running/completed receipts
  - replay-safe job ids
  - stage timestamps

Other useful docs on main:
- `docs/AUTOMATION-LESSONS.md`
- `docs/production/INTEGRATION-LESSONS.md`
- `tools/unreal_mcp/DOCTOR.md`
- `tools/unreal_preflight/preflight.py`: run it before any build slot

### 6. Worktrees versus the dirty shared checkout

- `C:\Users\730ri\projects\Daedalus2` is the **shared** checkout. At the time of writing it was on `main` at caf1b103 with about 195 changed files from many bots.
- Never `git pull`, `reset`, `checkout` or `stash` in it, and never commit anyone else's files there. Commit only your own files, and only if you must work there at all.
- Work in your own isolated worktree or clone, made from `origin/main`.
- Existing worktrees belong to their creators:
  - `Daedalus2-bb-wt` is blender-team's
  - `D2-ceo`, `D2-ceo6`, `D2-ceo7` and `D2-watcher` are 2Hot2Trot's
  - `_wt-wake-relay` holds the running wake relay
  - many more exist
- Don't fast-forward or clean another bot's worktree.
- Build from a clean worktree of origin/main, not from a checkout with other bots' local commits (unreal-team preflight lesson).
- Local-only PowerShell ops (`%LOCALAPPDATA%\Daedalus\ops\`, `bot-team\link\*.ps1`) stay off GitHub.
- Don't edit `bot-team\link\grok-relay.ps1`. Buffffff owns it, and it is moving into the wake-relay module.

### 7. Crash and hang history (from bot-team\BOARD\LESSONS-LEARNED-UNREAL.md)

Summarized from each crash or hang entry. Read the full entry before acting on one.

| When (PT) | What happened | Fix |
|---|---|---|
| 2026-10-12 14:03 and 14:37 | D3D12/DXGI crashes during glTF imports: the tidy watcher sent WM_CLOSE to the import's Content Browser | `tidy.ps1` skips while importing (e75c1d8); one tidy pass per job end (45bfbc5c) |
| 2026-10-12 (pythagoras) | Minimized editor at about 3 fps; bridge replies timed out and crossed | Async `ue_send` with request ids and per-call timeouts (30149257, 4a146613) |
| 2026-10-12 16:43 / 22:32 / 23:25 (prometheus) | Viewport screenshot quit the editor; hidden-editor shots came out black or missing | Transient SceneCapture2D; check pixel stats; Blender render fallback |
| 2026-10-12 afternoon to 19:18 | D3D12 `DXGI_ERROR_INVALID_CALL` and page faults; one editor stayed alive but GPU-dead; crash-reporter popups | crashguard: `-d3d11` after 2 crashes, crash reporter killed without sending, hidden WMI relaunch, `bSendUnattendedBugReports=False` (ssc 9fd4821); relaunched on DX11 (pid 56584) |
| 2026-10-12 19:17:55 | Modal "GPU Crashed or D3D Device Removed" (pid 12904); socket alive but no Python ran; turns lost | Prove the editor is alive with a 1+1 `execute_python` round trip ("BBPING"); stand down, never click or kill |
| 2026-10-12 ~23:00 | Editor died with under 1 GB free RAM; two runners drove one turn | Single-runner lock and RAM/bridge preflight (43ab7c1e) |
| 2026-10-12/13 (prometheus, hephaestus, buffffff) | Imports under 1 GB free RAM crash the editor | RAM guard: check every 5 meshes, keep above 1.5 GB; imports last; degrade to place-only (c1b76985, 5b1f80f9) |
| 2026-10-12 (2hot2trot) | Restore Packages dialog blocked unattended recovery | On-disk restore before relaunch (`crashguard.ps1 -RestoreOnly`, ssc 9fd4821) |
| 2026-10-12 (2hot2trot) | Leftover Play stalled imports | playguard (ssc a37cea8); stop Play between tests |
| 2026-10-12 (unreal-team) | Saved component array made ADaedalusVoxelIsle crash on every load | Constructor-filled arrays are `UPROPERTY(Transient)`; preflight rule P4 |
| 2026-10-12 (unreal-team) | Art watcher hung 35 min on shared Remote Execution | `unattended=False` plus `bridge_timeout` (artqueue 63/63) |
| 2026-10-12 (unreal-team) | Build slots lost when C++ failed after the editor closed | `tools/unreal_preflight/preflight.py` runs first in `unreal-job.ps1 -Run` |
| 2026-10-13 05:54:12 | GPU page fault (D3D device removed) while the art watcher imported the 14.5 MB flagship GLB into a no-flag D3D12 editor with no turn held | Imports only in a claimed turn; always `-d3d11 -gpucrashdebugging` (45e91309); split GLBs over about 5 MB (led to BIP 1) |
| 2026-10-13 06:55 | Near miss: a "light" turn would have relaunched without `-d3d11` | `--light` mode (e99155f4); `setup-unreal.ps1 -Open` forces the flags (45e91309) |
| 2026-10-13 07:40 | Stale BUILD OK: post-build steps ran against a closing editor | Wait on the exact job id (b6ae596c); PR38 hardening |
| 2026-10-13 09:40 | An interrupted bridge call had still run (14 levels moved) | Reverted from the undo table; check the editor's state after any interrupted call |
| 2026-10-13 19:14 | Crash during the ADR-055 material reparent: 3.5 min blocked game thread, D3D11 CreateSwapChain `DXGI_ERROR_INVALID_CALL` | Batches capped at 150 per call; `save_packages(only_dirty)`; resumable ledger (314fd845c) |
| 2026-10-13 22:19 | GPU crash: 22 rigged GLBs in one call (pid 14388, `DXGI_ERROR_DRIVER_INTERNAL_ERROR`) | `import_cast.py`, one GLB per call; save the world after each realm; relaunched as pid 48348 |
| 2026-10-14 08:41 (15:41 UTC) | Editor 41828 crashed under memory pressure (about 96.8% physical in use); later a Parcels save crash; Richey restarted it (5792) at 08:52 | Recovery under the owner; no blind repeat of the streaming that triggered it; watcher fix in PootScoot's lane |
| 2026-10-15 09:53 (16:53:53 UTC) | Assert `NumUVs>0` (StaticMesh.cpp:9811) on a Gallery mesh, editor 28232; crash-reporter popup; crashguard signatures missed it | Saved work verified preserved; UV0 source fix prepared; assertion classification is an open watcher gap |

Other hangs in the file:
- An "Add Level" dialog blocked a job (blender-team).
- Background jobs freeze between tool calls, so run anything long-lived detached and hidden (pythagoras).

### 8. Comms in brief, and the sync rule

Full standard: `bot-team\BOARD\COMMS-STANDARD.md` (owner Buffffff, set by Richey 2026-10-19). Worked example and PowerShell template: the 2026-10-19 00:15 entry "How a Grok bot talks to PootScoot" in `LESSONS-LEARNED-UNREAL.md`.

**Sending.**
- There is one broker at `127.0.0.1:9890`. Never start a second broker or relay.
- `POST /send` with `{from, to, type, reply_to, body:{request_id, text}}`. Read with `GET /pending?me=<you>`; the log is `bot-team\link\log.jsonl`.
- Put the recipient in the structured `to` field. An @name in the body does not route.
- One recipient per message. `*` is for FYI only, and it never wakes a Grok bot.

**Each message.**
- The first word is QUESTION, NEED, ACK, DONE, BLOCKED or FYI.
- Every reply sets `reply_to` and copies `body.request_id`.
- Close every ask with ACK and then DONE or BLOCKED.
- Keep it under about 1,000 characters; put long detail in a file and send its path and hash.
- No secrets in messages.

**Conduct.**
- Never bulk-ack.
- Act only on messages addressed to you.
- Never hand-forward other bots' messages.

**Wake relay.**
- Grok bots show `alive:false` in `/bots`, and that is normal. The wake relay (Daedalus2 `connectors/claude-asset-pipeline/wake-relay`, running hidden from `_wt-wake-relay`) wakes the addressed bot.
- Its endpoint configuration lives only in the git-ignored `bot-team\link\relay-webhook.json`. Never print, copy or commit that file.
- New bots (for example `unreal-epic-boss`) must ask Buffffff to be added to the relay.

**Human clicks.** Steps that need a human click, such as a GitHub PR review form, go as a NEED to `pootscoot-coordination` so team Codex does them, not Richey (Richey, 2026-10-19). Message Richey in chat only for decisions or major results, and never by text or SMS.

**Claims.** Claim work in `bot-team\BOARD\ARCHITECTURE.md` (registry row plus `CLAIM` on the link) before you build.

**Sync rule (Richey's standing order, given in chat on 2026-10-13 and 2026-10-18; I found it written in no BOARD file):**
1. The code compiles and passes its tests.
2. It lands on `main`.
3. The BLACKBEARD copy matches GitHub exactly.
4. Then post `SYNCED <repo> <hash>`.

Nothing may live only in a worktree, a temp folder or a bot's box.

**Approvals.**
- Deletes, keys, release tags, payments, signing keys and outgoing sends in Richey's name always need his explicit yes.
- Before every push, scan the diff for secrets (Richey, 2026-10-19). If the scan finds anything, stop.

## Blender (blender-team)

Owner: blender-team (Blender Boss), link name `blender-team`. Every fact below was checked against the files named, on BLACKBEARD, on 2026-10-19. Read 2Hot2Trot's §3 for the Unreal side; this section is the Blender side.

### 1. Blender on BLACKBEARD
- **Version and exe:** Blender 4.3.1 (build 2024-12-10), `C:\Program Files\Blender Foundation\Blender 4.3\blender.exe`. Every job script hard-codes this path (`jobs/lod1run.py`, `jobs/chain.py`, `assets/autowave.py`).
- **Richey's GUI Blender** is that exe launched with no arguments. It runs the add-on **Claude Blender Bridge 1.0.2** (`%APPDATA%\Blender Foundation\Blender\4.3\scripts\addons\claude_blender_bridge\__init__.py`, repo RicheyWorks/claude-blender-connector), which listens on `127.0.0.1:9876` only and autostarts when Blender loads.
- **Leave the GUI window alone.** The art watcher uses it to open `art\<Kind>\<Asset>.blend` and export (`docs/blender-team-log.md`, `assets/headless.py`). Don't close, restart or reload it, don't open files in it, and never discard unsaved work. If 9876 is down, ask Richey; don't relaunch it yourself.
- **All factory work runs headless, in its own process:**
  `"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" -b --factory-startup --python <script.py> -- <script args>`
  - `-b` (background) opens no window, UI or splash.
  - `--factory-startup` ignores Richey's `userpref.blend` and user add-ons, so the headless process never starts a second bridge.
  - Scripts read their own arguments after `--`.
  - Jobs launch hidden: `Start-Process ... -WindowStyle Hidden -RedirectStandardOutput <log>` (`jobs/bbisle_final.ps1`), or `subprocess` with `creationflags=0x08000000` (no console; `jobs/lodworker.py`).
  - Only one heavy headless job runs at a time: `bbisle_final.ps1` waits until no `blender.exe` with ` -b ` remains.
- **Splash:** Richey's user preferences have the splash turned off (Preferences → Interface → *Splash Screen*; `bpy.context.preferences.view.show_splash` reads `False` from `%APPDATA%\Blender Foundation\Blender\4.3\config\userpref.blend`, checked 2026-10-19). Headless jobs never show one, because `-b` has no UI.
- **Heavy Blender steps need a window:** no heavy author/export/render without a coordinated window from `pootscoot-coordination`. Check the hub for an active `compute` lock first (`GET http://127.0.0.1:9890/locks`).

### 2. The GUI bridge (127.0.0.1:9876)
- **Wire format:** one JSON object per line over TCP. Request `{"id": <any>, "type": "<command>", "params": {...}}`. Reply `{"id", "status": "ok", "result"}` or `{"id", "status": "error", "message", "traceback"}`. Commands run on Blender's main thread through an app timer.
- **Commands:**
  - `ping`
  - `get_scene_info` (`limit`, default 200)
  - `get_object_info` (`name`)
  - `execute_code` (`code`; whatever the code assigns to `result` is returned, and stdout is captured)
  - `viewport_screenshot` (`max_size`)
  - `render_image` (`output_path`, `resolution_percentage`, `max_size`)
- **A client timeout does not cancel the work.** Blender finishes the call, and the next call waits (`bharness/client.py`).
- **Read-only check:** `python -m bharness call bridge.ping`. The harness gates every action by risk (READ < SCENE < FILE < DESTRUCTIVE); the CLI default ceiling is SCENE, so FILE work needs `--allow FILE`.

### 3. Where the factory lives
- **RicheyWorks/blender-harness** (BLACKBEARD `C:\Users\730ri\projects\blender-harness`; tests: `python -m harness.run_all`, 7/7):
  - `bharness/`
    - `client.py`: 9876 client.
    - `local.py`: `LocalBridge`, the same interface run in-process inside `blender -b`.
    - `contract.py`, `context.py`: gateway and wiring.
    - `palette.py`: colour names → hex.
    - `glb.py`: reads a glb with no 3D library.
    - `plugins/judge.py`: the brief's checks.
    - `plugins/probe.py`, `plugins/export.py`, `plugins/render.py`, `plugins/queue.py`.
    - `handoff.py`: `art\jobs\<Asset>.json` contracts.
    - `bus.py`: the team link client.
  - `assets/`
    - `catalog.py`: the mechanics-to-assets map.
    - `ecospecs.py`, `toolspecs.py`, `worldspecs.py`, `wave*.py`: shape specs.
    - `runner.py`: `build_one` = build → judge → glb export + self-check → turntable → save.
    - `headless.py`: the batch entry point, `blender -b --factory-startup --python assets/headless.py -- <repo> <module> [groups] --batch=10 --turntable=4 [--no-send]`.
  - `jobs/`: the batch scripts, e.g. `lodglb.py` (LOD1) and `bbisle_final.ps1`.
  - `HANDOFF-SPEC.md`, `BLENDER-LESSONS.md`.
  - `releases/assets-2026-10-18.*`: manifest of the GitHub release that holds the 4.6 GB of .blend/.glb binaries.
- **RicheyWorks/Daedalus2:**
  - `tools/islands/blenderboss/`:
    - `bbkit.py`, `bbisle.py`, `flagship.py`: the island.
    - `bba_manifest.py`: LOD manifest.
    - `bip_glb.py`, `bip_split.py`, `bip_verify.py`, `bip_render_check.py`, `BIP1.md`: packets.
  - `tools/blender/weapons/`: `rifle_recipe.py` (pure-data recipe), `build_rifle.py` (headless builder), `test_rifle_recipe.py` (11/11).
  - Data: `data/assets/catalog.bba`, `data/islands/blenderboss/flagship.bip.json`, `data/combat/slice1/*.recipe.json`.
  - blender-team commits from the worktree `C:\Users\730ri\projects\Daedalus2-bb-wt`, never from the shared `Daedalus2` checkout.

### 4. Units, axes, names (`docs/BLENDER-TEAM-BRIEF.md`, `bharness/plugins/judge.py`)
- **Units:** 1 Blender unit = 1 m = one cube, with scale applied. Unreal sees centimetres: 1 m = 100 cm (`asset_pipeline/ship.py` `CM_PER_M = 100.0`). The judge allows 1% or 0.01 between file sizes ×100 and the Unreal bounds.
- **Origin and facing:** origin at the bottom centre. The judge requires min z within 0.01 m of 0 and the x/y centre within 0.05 m of 0. The front faces −Y in Blender. **In Unreal that front lands on +Y, not +X** (see glTF axes). Decided (buffffff 48769): glbs are **not** rotated at export; face them with actor or component **yaw −90** at placement, the same way UE's mannequin is handled. Exception: if UE code needs mesh +X forward (weapon or character attach; the rifle and fishing rod are the likely cases), unreal-epic-boss raises it and only those assets are revisited.
- **glTF axes:** glTF is exported +Y up (`export_yup=True`), so Blender (x, y, z) becomes glTF (x, z, −y). Stock UE 5.8 glTF Interchange then maps **UE = 100·(gX, gZ, gY) = 100·(x, −y, z) cm** (native evidence from unreal-epic-boss 48725, terrain_33, no node rotation; our glbs carry no node rotations either). So Blender +X = UE +X, Blender −Y (our front) = UE +Y, Blender +Z = UE +Z.
- **Names:** `^(Prop|Item|Tool|Wpn|Mob|Veh|Bld|Sky)_[A-Za-z0-9]+(_[A-Za-z0-9]+)*$`, one collection per asset named like the asset, and no spaces in object names.
- **Triangle budgets** (`judge.BUDGET`):

  | Kind | Max tris |
  |---|---|
  | Prop / Item / Tool / Wpn | 3,000 |
  | Mob | 6,000 |
  | Veh | 12,000 |
  | Bld / Sky | 15,000 |

  A slice spec can override a budget, e.g. combat slice 1 allows the rifle 40,000.

### 5. Materials, UVs, collision, LOD
- **Materials:**
  - 1 to 3 filled slots, flat colour, no image textures.
  - Colours come by name from `bharness/palette.py` (block colours, ores, misc; for example `wood` 9A6B3F, `steel` C9D4E0, `starmetal` 7FE3FF). An unknown name is an error.
  - The sRGB→linear conversion is `(c/255)^2.2`.
  - `crystal`, `starmetal` and `portal` glow (emission).
  - The weapon builder names its slots `<Asset>_M<slot>`.
- **UVs:** we don't unwrap, bake or ship textures, so nothing should depend on our UVs, and we make no lightmap UVs. `bip_split.py` keeps whatever UVs the source has.
- **Collision:** our exports have **no** `UCX_`/`UBX_`/`USP_`/`UCP_` meshes today. `combat_handoff.py` requires them only for the `environment` role (Env_Slice1_Arena: `min_hulls 4`), which would be new blender-team work. Ask for it in the spec.
- **LOD** (ADR-062, `docs/adr/ADR-062-asset-lod-manifest.md`):
  - `jobs/lodglb.py` makes `<Asset>_LOD1.glb`: it keeps the largest loose parts until about 60% of the faces remain, then applies a 0.5 decimate to any mesh still over 2,000 tris.
  - `bba_manifest.py` writes `data/assets/catalog.bba`, one line per asset: `asset <id> lod0 <faces> lod1 <faces|-> radius <cm> switch <cm>`. The file currently has 5,605 assets, all with LOD1.
  - The switch distance is 20 bounding radii, never less than 5 m.
  - Parity: `DaedalusAssetLodCore.h` (C++17, header only) and Java `AssetLodManifest` agree byte for byte.
  - Unreal side: `DaedalusLink/Content/Python/daedalus_lod.py` sets LOD 1's screen size to 1.778·r/d (0.089 at 20 radii).

### 6. Export settings (from the code)
- **bharness / catalog assets** (`bharness/plugins/export.py`): `export_scene.gltf(export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_materials="EXPORT", export_animations=False)`. It selects **only the MESH objects** in the asset's collection, so empties and sockets are not exported. The glb is then re-read and checked against Blender's own numbers (tris, slots, sizes).
- **Weapons / socketed assets** (`tools/blender/weapons/build_rifle.py`): `export_format="GLB", export_yup=True, export_apply=True, export_extras=True`, with no selection filter. Sockets are empties parented to the mesh, named `SOCKET_<Name>`, and become glTF nodes. It also saves the `.blend` and a `build_report.json` (tris read back, dimensions, socket names). It refuses an `--out` path containing an `art` folder unless `--allow-art` is passed.
- **Sockets:** stock UE 5.8 glTF Interchange keeps `SOCKET_` empties as native static-mesh sockets (unreal-epic-boss 48725: fixture B `Top` at (0, 0, 50) cm; the earlier "dropped" result was a reader false negative). Every socketed asset also ships `<Asset>.sockets.json` (`tools/blender/sockets_sidecar.py`: `units` cm, `space` unreal, per socket `name`, `parent`, `location` relative to the parent node, `rotation` [pitch, yaw, roll] from the socket's forward vector). It is a **cross-check** for the native sockets and the carrier of socket rotation (our empties have none); PR203 intake reads it.
- **LOD1 and flagship:** `use_selection=True, export_apply=True`, with the defaults otherwise (GLB, +Y up).
- **FBX:** blender-team does not ship FBX. Other teams' `tools/blender/voxel_*.py` and `hd_island.py` use `export_scene.fbx(apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z")`.

### 7. BIP 1 packets (`tools/islands/blenderboss/BIP1.md`)
- **Split:** `python bip_split.py <island.glb> <packet dir> <manifest.json>`. It is pure numpy, needs no Blender, and is deterministic (byte-identical on rerun).
  - Terrain and underside are cut into a quadtree by triangle centroid (leaf target 6,000 tris; no triangle is cut).
  - Props become a deduplicated mesh library plus placements.
- **Hard caps per packet:** 12,000 tris, 1,572,864 bytes (1.5 MiB), 64 materials. The splitter refuses to write a packet over any cap.
- **Verify:** `python bip_verify.py <manifest> <packet dir> [source.glb] [--rebuild]` recomputes sizes, sha256, tris, bounds, index ranges, caps and placement refs. `bip_render_check.py` compares top-down renders of the source and the reassembled packets.
- **Flagship:** 67 packets (28 terrain + 39 prop), manifest `data/islands/blenderboss/flagship.bip.json`, packets in `bot-team\art\packets\flagship\` (outside the watched `art\glb`).
  - They are **frozen**: no regeneration and no import outside a claimed turn by the sole Unreal writer.
  - Import order: terrain first, then the prop library, then placements.

### 8. Handoff protocol: asking blender-team for an asset
1. **Write a spec** (JSON, one asset):
   ```json
   {"request_id": "<stable id>", "asset": "Kind_Name", "kind": "Prop|Item|Tool|Wpn|Mob|Veh|Bld|Sky",
    "size_m": [x, y, z], "tri_cap": 0, "sockets": ["Name"], "palette": ["wood", "steel"],
    "lod": "LOD0 only | LOD1 via lodglb.py", "collision": "none | UCX_ hulls: N", "seed": 0,
    "front": "-Y", "origin": "bottom centre", "notes": "..."}
   ```
   `size_m` is Blender x, y, z in metres; `tri_cap` is at most the Kind budget unless your spec overrides it.
2. **Send it** on the team link, per `bot-team\BOARD\COMMS-STANDARD.md`:
   - `POST http://127.0.0.1:9890/send` with `{"from": "unreal-epic-boss", "to": "blender-team", "type": "note", "body": {"request_id": "...", "text": "NEED ...", "spec": {...}}}`.
   - One recipient per message (a `*` broadcast never wakes a Grok bot) and a first word of NEED.
   - Put a long spec in a file and send its path + sha256.
3. **What blender-team hands back** (a reply to your message id):
   - the staged `.glb` path (outside watched `art\`), with its sha256 and bytes;
   - the `.blend`;
   - the recipe/manifest (`*.recipe.json`) and `build_report.json`;
   - a render when the asset has one (`art\promo\<Asset>\` turntables come from the catalog runner);
   - the QUEUE row number when the asset goes onto the board.
   - We never mark READY ourselves for spec work.
4. **Receiving gate (your side, before anything enters `art\glb` or Unreal):**
   - Re-hash the glb and compare it to the sha we sent.
   - Run `python -m asset_pipeline.combat_handoff --spec <spec.json> --folder <staging dir> --out <dir>` in `connectors/claude-asset-pipeline`, **without `--import`**, for sockets and triangle caps.
   - Check sizes with `bharness.glb.summarize(bharness.glb.read_json(path))` (per-mesh `dims` in metres, largest first; ×100 = Unreal cm).
   - Import only inside a claimed Unreal turn by the sole writer (2Hot2Trot §3).
   - Close the request with ACK, then DONE or BLOCKED.

### 9. Practice task: Prop_PracticeCrate
1. **UEB sends a spec** to=blender-team, with request_id `ueb-practice-crate-<date>`. The filled example:
   ```json
   {"request_id": "ueb-practice-crate-20261019", "asset": "Prop_PracticeCrate", "kind": "Prop",
    "size_m": [0.52, 0.52, 0.5], "tri_cap": 500, "sockets": ["Top"], "palette": ["wood", "dark"],
    "lod": "LOD0 only", "collision": "none", "seed": 0, "front": "-Y", "origin": "bottom centre",
    "notes": "0.5 m cube body in wood plus two 0.52 m dark bands at z 0.10 and 0.40; SOCKET_Top at (0, 0, 0.5) m"}
   ```
2. **blender-team builds it headless.** The crate becomes a `build_rifle.py`-format recipe: body box 0.5 m centred at z 0.25 (slot 0); bands 0.52 × 0.52 × 0.06 m at z 0.10 and 0.40 (slot 1); a bevelled box is 44 tris, so 132 tris predicted. The build runs `blender -b --factory-startup --python tools/blender/weapons/build_rifle.py -- --manifest <crate.recipe.json> --out <staging dir outside art\>`. It waits for any active `compute` lock and needs no GUI.
3. **UEB checks the export against the spec** and replies DONE (all pass) or BLOCKED (the failed check):

   | Check | Expect |
   |---|---|
   | sha256 / bytes | equal what blender-team posted |
   | triangles | 132 (≤ 500) |
   | socket | node `SOCKET_Top`; glTF location (0, 0.5, 0) = Blender (0, 0, 0.5) m |
   | size | 0.52 × 0.52 × 0.5 m → 52 × 52 × 50 cm in Unreal |
   | materials | 2 slots: `Prop_PracticeCrate_M0` wood 9A6B3F, `_M1` dark 4A4D57 |

   For the socket and triangle checks, use a practice spec with `"schema": "combat-slice/v1"`, `"assets": [{"name": "Prop_PracticeCrate", "role": "weapon", "sockets": ["Top"], "max_triangles": 500}]`. `weapon` is the only role that checks sockets.
