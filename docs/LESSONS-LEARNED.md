# Lessons learned

Lessons that held up in practice and should shape the next piece of work. Each one has the evidence
behind it. Newest at the top of each section.

## Design

### Modular, portable design wins over the long run (2026-10-11)

> "Yes, modular design philosophy wins the long run." (RicheyWorks)

**The lesson.** Modularity pays when the boundaries are in the right places, and the right places are
found by reusing a piece for real. Split too early, before the seams are known, and you pay for
interfaces nobody uses.

**Why it worked here.** Daedalus' boundaries were proven by moving things. The maze engine went into a
2D web well, then a 3D realm, then Blender, then Unreal Engine 5. Each move tested whether the seams
held. That is why the game (ADR-036 on) arrives quickly: each new feature mostly composes parts that are
already tested.

**Two habits keep it winning:**
1. **Guard the boundaries with tests, not intentions.** Agents (Claude, Grok, anyone) take shortcuts
   across a boundary that nobody checks. Here:
   - `PortabilityTest`: `daedalus-core` imports only the JDK and itself.
   - The C++ mesh core's parity tests against the Java mesher (`engines/unreal/core-test`).
   - The Unreal import's own verifier, which checks the result against the manifest (`verify_judge_test.py`).
2. **The contract is the product.** These outlive any one engine:
   - the World Package format
   - `/api/v1/...`, including the published rules such as `/api/v1/hero/rules`
   - the shared C++ core

   Keep them stable and versioned, and the presentation layer (three.js, Unreal, Blender, VR) can change
   without touching the game.

**The shape to keep:** Java engine (rules, plain JDK) → stable interface (data and HTTP) → engine adapter
(DaedalusLink, the realm, Blender) → gameplay. Platform code belongs in adapters, never in the core.

## Verification

### Make a tool check its own work, and prove the check can fail (2026-10-11)

The Unreal import used to report only "done". Now it reopens the level and checks it against the
manifest, and each check prints PASS or FAIL. The judging logic is pure Python, so it is tested without
Unreal: each kind of broken project fails exactly the check that names it (13/13). A check that cannot
fail proves nothing.

### Wait on outcomes, not timers (ADR-037)

In the browser harness, software WebGL runs at about 5 frames a second with six pages open. Checks that
waited a fixed time (a 1.3 s jump, a knockback measured after 300 ms, one thrust after 450 ms) failed
when frames came late. Physics only advances when a frame arrives. The harness now waits until something
happens (a landing, a numbered thrust that met a foe, the knockback settling), as a player would.

## Portability across machines

### What runs here may not run on the user's PC (2026-10-11, `setup-unreal.ps1`)

Every one of these passed in the Linux sandbox and failed on Windows:
- **Windows PowerShell 5.1 and wildcards.** A wildcard in the middle of a `-Recurse` path matches
  nothing there, so an old server jar looked current. The server it ran had no World Packages.
- **UE 5.8 and MSVC.** UE 5.8 refuses MSVC 14.40–14.43, and the installed VS 2022 had 14.41.
- **The VS installer and `--passive`.** It refuses `--passive` without elevation (exit 5007).
- **A plugin that never loaded.** It declared `"EngineVersion": "5.4.0"`, so UE 5.8 skipped it silently.
- **Unbuilt plugins.** The editor won't open a project that enables a plugin that isn't compiled yet.

**The lesson.** A setup script must look, report what it found, and recover on the real target. Run it
there early, and read its full output.

## Working through PowerShell

### Drive everything from one PowerShell line (2026-10-11)

> "Save to memory to just get everything going via PowerShell." (RicheyWorks)

Opening Unreal by hand, then importing while it was open, failed again and again. One line now does the
whole job, and it is the line to give whenever something needs to run:

```
cd C:\Users\730ri\projects\Daedalus2 ; git pull --ff-only ; .\engines\unreal\setup-unreal.ps1 -Project C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -Build -Import -Open
```

What made the line reliable:
- **Always start with `git pull --ff-only`.** One handed-over line left it out, so the old script ran,
  and the fix it carried (Shader Model 6) never arrived.
- **The script owns the apps it touches.** `-Open` closes the editor, does the work, and reopens it.
  Asking a person to close and open windows between steps is where the runs went wrong.
- **One writer per file.** On Windows an open file can't be replaced (error 32). Two Unreal editors were
  open, so one held the assets while the other saved. Before importing, close every editor that could hold
  the project.
- **When a window won't close, force it.** It is usually waiting on a save prompt nobody can see.
  `Get-Process UnrealEditor | Stop-Process -Force`, then wait about 3 s for Windows to release the files.
  The import rebuilds the level, so nothing of value is lost.
- **Never interrupt an installer.** Rerunning setup while the Visual Studio Installer was busy left Visual
  Studio half-installed. Even an idle installer window blocks the next run. Let it finish, close it, then
  run again. `vswhere -all` shows a half-installed copy, which plain `vswhere` hides.
- **Elevate on purpose.** The VS installer refuses `--passive` without admin (exit 5007). `Start-Process
  -Verb RunAs` asks Windows once, visibly.
- **Windows PowerShell 5.1 is not PowerShell 7.**
  - A wildcard in the middle of a `-Recurse` path matches nothing in 5.1.
  - A native tool writing to stderr, such as `java -version`, throws under `$ErrorActionPreference =
    "Stop"`. Lower it around such calls.
  - Parse-check every edit (`[Parser]::ParseFile`) before pushing.
- **Use the API instead of clicking.** Raising islands is one `Invoke-RestMethod` per seed against the
  local server, chained into the same line.
- **Ask for the end of the output, after `cls`.** Long pastes held old scrollback, and once a fix was
  read from an earlier run instead of the latest one.

### Use the browser when the shell can't reach (2026-10-11)

> "Use Chrome if you need." "Keep that in lessons learned: use Chrome when needed." (RicheyWorks)

Some steps can't be done from the cloud shell: creating a public GitHub repository, or a site that needs his
sign-in. Don't stop there. Do the step in his browser (Claude in Chrome, or the built-in browser), which has
his own sign-ins, and tell him what was done. The browser is also how to reach a page the shell's network
allowlist blocks.

### Make a tool modular before it is shared (2026-10-11)

> "Make this design modular. I want to share this with Grok bots etc., so we will put it on GitHub and
> update it as we go." (RicheyWorks)

The Unreal connector began inside DaedalusLink, with Daedalus commands inside the bridge. To share it, it
was split:
- **A generic core.** `connectors/claude-unreal-connector` holds the bridge plugin, the MCP extension, an
  installer and tests, and knows nothing of Daedalus.
- **A public extension point.** `register(name, fn, description, params)` adds commands, and
  `list_commands` / `run_command` reach them.
- **A protocol doc and a stdlib client,** so agents without MCP (Grok bots) can use the same bridge.

Daedalus is now just one user of the connector. A test checks that the two sides stay apart.

## Every README has screenshots

A README with no pictures leaves a bot or a person guessing what the thing does. Every module's README shows it
working: a render, a run, a board. The screenshots are made by a script from real runs (for example
`connectors/claude-asset-pipeline/harness/shots.py`), so they get regenerated with the code and never go stale.

## A sweep over everything finds the sharp edges, so it must survive them

The first factory sweep over all 266 asset factories crashed the live editor (UE 5.8.3). One factory opened a
modal picker. Another (DataAssetFactory with no class set) made an abstract asset, and saving it asserted.
What changed:
- factories that prompt or need a class are excluded, with that reason
- the sweep runs in batches, so a crash costs one batch
- the level is saved first
- the extension watches for dialogs during every call and cancels them

A harness that only looks when asked misses the dialog that froze the editor. Watching has to be automatic.

## Pin asynchronous integration work to its exact job (2026-10-13)

The Unreal turn report marked build-1013-073247 successful after 2.8 seconds, while that
job's build log recorded 56.91 seconds. The runner started a job and called `-Wait` without
`-Id`; before the new log appeared, the wait helper could choose an older successful job.
Scenarios then reached the old editor before the ongoing rebuild/restart completed. The
report showed a missing Python module, connection reset, then refused connections and a
failed save. This evidence supports a build-wait race; it does not prove a GPU crash.

The runner now extracts the started job ID, passes it on every wait, verifies the response
belongs to that job, and stops before editor calls for missing/mismatched IDs or failed jobs.
Offline regression covers a still-running job before its log exists and an older success.
Always correlate start, completion and evidence by ID; a successful earlier C++ build is
not proof that the current Java/C++/Python integration is ready. Live scenarios must be rerun
by the editor owner after the actual build and bridge readiness checks finish.

## Measure contention before moving work between Java and C++ (2026-10-13)

The adaptive tactics benchmark initially timed decisions and disk writes separately. That
missed requests waiting behind TacticsHost's shared lock. The concurrent durable-host probe
in PR37 (`tools/benchmarks/TacticalHostProbe.java`, initial commit `8f266d0c`) measured total
p95 of 3.21 / 15.11 / 33.71 ms with 1 / 4 / 8 callers. Brain-to-return p95 remained near
3 ms; pre-brain p95 grew from 0.10 to 31.34 ms. Evidence is recorded in
`docs/benchmarks/adaptive-profile-after/host-contention.csv`.

**Lesson:** measure the complete path under contention before choosing a language rewrite.
The results are consistent with serialized durable work dominating added latency; they do
not demonstrate that porting decision math to C++ would remove that delay. Keep Unreal's
immediate movement/combat and fallback asynchronous from Java persistence. Reuse the existing
host, director and store when measuring, and validate receipts and checkpoints during the run.

Pre-brain timing includes parsing, scheduling and bookkeeping as well as lock wait. This
short closed-loop test on temporary storage is not HTTP/JWT, a production capacity estimate,
an open-loop overload test, or an Unreal frame/FPS measurement. Do not add independently
computed percentiles or describe allocation reductions as proven latency improvements.

Next measurement: use the real request cadence and storage volume, include HTTP/authentication,
and measure queue growth and fallback behavior. Any concurrency change must retain per-session
tick fencing, checkpoint-before-reply and the exclusive writer contract. Coordinate ownership
with the native team before changing either side; a green Java suite is not visible gameplay proof.
## Add server contracts through the existing integration gates (2026-10-13)

The Kennel TONIC 1 endpoint reuses TonicBook/TonicBrewer and packages the canonical recipe
file instead of duplicating recipe math or relying on the server working directory.
The initial focused tests passed, but full verification caught missing endpoint entries in
the production-auth table and the named rate-limit registry. Both were added, along with
the README API row. Next endpoint: check those registries before running the full suite.

Keep native fixtures executable: committed TONIC responses are compared against HTTP output,
and real JWT requests prove 401/403/200. Carry all source semantics across the language
boundary (mode, grants, breeding chance and already-scaled modifiers), not just the fields
needed by the first demo. A deterministic calculator is not an inventory transaction;
state clearly which side validates ownership, consumes ingredients and applies effects once.
## Reuse the touring jukebox when adding audio contracts (2026-10-13)

AUD 1 carries the existing ADR-052 music cue rather than inventing a second music service.
The existing JukeboxClient/JukeboxTransport handles touring content; native daedalus.Jukebox
handles cue changes. Ambience and creature calls reuse BiomeAmbience and PCS 1 unchanged.
Keep design/calculation independent of remote music fetches, retain the prior valid mix on
failure, and do not restart an unchanged track at every refresh. Parameter fixtures prove
cross-language inputs, not audible playback; native playback needs its own live verification.

### Verify checkout before every Git mutation

Always set an explicit working directory on Git mutations, then verify the branch
and HEAD match the intended isolated checkout. A missing working directory created
an unused branch in the shared checkout during Brick art delivery. Recovery checked
that the original branch and commit matched and compared every dirty-file status
before and after restoring the branch. No file resets or stashes were needed.
Verify the pushed commit and PR base too; a successful push alone does not prove
that the intended change was published.

### Initialize Unreal test worlds before testing RPC wrappers

Creating a UWorld is insufficient to dispatch actor RPCs in an automation test.
UE 5.8 AActor::ProcessEvent gates dispatch on AreActorsInitialized unless editor
script execution is explicitly allowed. InitializeActorsForPlay and assert that
state before exercising the real wrapper. A direct implementation call can help
diagnose movement logic but cannot substitute for dispatch verification. Neither
standalone dispatch nor a direct handler proves client/server network delivery.

### C++ prefixes do not make Unreal reflection names unique

ADaedalusOceanDock and FDaedalusOceanDock collided in UHT even though their C++
names differ. Unreal removes type prefixes when deriving reflected names. Name
new actor roles distinctly (OceanDockControl versus OceanDock data) and preserve
established data APIs. A full reflection build caught this before publication.


## team-codex firsthand Unreal and harness handoff — 2026-10-14

Use the new UE 5.8 ModelContextProtocol/ToolsetRegistry/AllToolsets connector. When this task has no named native tool binding, the existing `tools/unreal_mcp/client.py` initializes a Streamable HTTP session at `http://127.0.0.1:8000/mcp` and invokes discovered toolsets through call_tool. Actual read-only calls succeeded: IsPIERunning=false and SceneTools.get_current_level=/Game/Daedalus/DaedalusWorld. Exact small-call receipts include resume-audit/native-connector-check.json (13:03:17.801715 UTC, 0.093 s) and native-during-compile.json (13:31:15.022817 UTC, 0.094 s). These do not prove every tool, image transfer or current readiness after an editor restart. No later named-binding use is claimed here. During Claude's new startup, a fresh initialization refused connection with WinError10061/request_submission; owner must start/verify the endpoint, not another agent or fallback broker.

Read describe_toolset and typed native results before calling. Material connect/save operations can return void/None on success; treating that as false produces an incorrect failure. Conversely, a saved asset is insufficient evidence of a correct graph. Inspect actual pin names/connections: Noise uses World Position, and single-input nodes may expose an unnamed pin. Verify graph readback and saved packages. The additive World Zero material/pilot preserves Claude's existing scene dressing; do not replace an old 100-cm Cube with a 9,200-cm mesh while retaining XY scale 92. NativePool meshes use a top-centre origin, top Z=0 and one verified convex hull.

Editor ownership and saved-state proof are separate from presence and locks. Record the explicit receiver acceptance, source/artifact hashes, map/package save and current owner. An empty lock table or expired heartbeat does not release an app. Last new claim is Claude/unreal-team hub30306/30307, reopening on reported main481e30b; native editor PID41828 was observed starting 08:29:25 PT. Codex isolated compile68196 is terminal exit0 and compute lease released30312. Do not restart an operation because observation timed out. Startup itself runs UBT SDK checks, so coordinate the compute lease too.

CaptureViewport sometimes returned incomplete response bodies near their tails, while other full images succeeded. A fixed 3-MB ceiling or a specific networking cause was not established. Ground-shader capture11:12:55.079768..11:12:55.561264 UTC completed in0.484 s: rock-pilot-ground-shader.png, 4,190,608 bytes, SHA256 8f36c91c4df58040e5dee4071d07502850bc1d31498e34f257b44f406d9e2fb4. This image was visually inspected previously; transport/appearance evidence is distinct from collision, walking and annotated Claude desktop acceptance. Do not retry mutations or alter transport limits based solely on screenshot failure.

Keep current data provenance. Native realm-7.drr has34 lands including Claude's31 additions, 21,988 bytes, SHA256 a48de4b11000485ceecd618c3d4f612e5e5923fff08fe3df4dde73cf795eb0b6. It matches the accepted50b55d15/3ba94ab9 data; an older three-land branch snapshot must not replace it. Eleven staged files comprise five DIC, five DCS and this DRR. UFS declarations alone did not prove staging. Actual DaedalusRealm Shipping compiled66 actions in292.71 s; EXE SHA256 7dac18b7cdaa54352ac2a40910e90e9c2469b3a72eb0b4d413f4872cac6af48d. Generic UnrealGame success was metadata-only and was not counted as compilation. Normal project GameFeatureData AlwaysCook repair preserved custom scan/config arrays; it fixed actual cook errors without disabling validation. Actual cook/stage/PAK+IOStore/archive exited0 in166.76 s,13,259 packages. All11 extracted payloads matched source hashes/lengths. Archive: C:/Unreal/DaedalusRealm/Saved/Packages/WZ-20261014-native/Windows. Local actual-shipping-build-proof.json, native-package-payload-proof.json, asset-manager-cook-fix.json and package-success.log retain the evidence; this is not launch/gameplay/public hosting proof.

Isolated-host lessons: pin both Git names and blob bytes, generate explicit Game/Editor targets, and distinguish source, scaffold and overlays. One streaming cat-file process cut one warm-cache198-file snapshot observation from12.328 s to0.594 s with identical manifests; this is not a general speed claim. full_plugin_host.py --verify HOST now checks descriptor/plugin/scaffold hashes and additional source/content; run before and after builds. It is a manifest check, not a signed attestation or concurrent edit lock. Old hosts require fresh descriptor-bound snapshots. Frozen b1a33bcf explicit Editor and Shipping targets compiled66/67 actions in296.30/280.81 s; source-only receipts do not imply installed DLLs.

Owned Shardstead clock signals committed cycle+1, suppresses pending writes, limits hitch callbacks to once per frame and clears on EndPlay/destruction. It does not grant goods. Latest receipt consumer captures pending bytes/domain revision/SHA256 together and validates actual bytes against caller expectations before confirmation. Domain and outer store revisions remain distinct; unknown writes stay pending. Strict portable receipt tests pass; the already-started isolated binding compile passed six actions in21.35 s, with all198 base inputs and three explicit source overlays rechecked. Canonical inventory, shared Production tab, native record transport and live persistence remain unaccepted. Poot's shared transport proposal30251/30257 still has no scope release per30300; keep arcade owner files untouched.

PR94 merge7afb6c44740738787bc2cb147eeed842ff839b38 is independently verified through GitHub after Poot's approved source-only merge. Resulting main CI is Poot's lane; no overall current-main green claim is made here. PR139 and PR140 remain distinct delivery lanes. Preserve other authors' files and carry source-tested, isolated-compiled, saved-editor, packaged-payload and gameplay stages separately in every handoff.

