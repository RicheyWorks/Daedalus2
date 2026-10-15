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

### Capture new-game configuration before asynchronous authentication

2026-10-15, pootscoot-desktop-games; java_gap_scan source review.
Sudoku4d5577dc binds existing Java chaos/mirror/timeAttack flags instead of
hardcoding false. Capture accepted options after request gates and before async
bootstrap; build the eventual request from that snapshot. Keep next-game choices
separate from Java-confirmed current modes, and preserve the old ordinary entry
point. Open/resume must not recreate a game or extend its authoritative clock.
Source review and77 static checks (61 unchanged methods) pass; compiler/tests,
services and native operations remain deferred. No measured gameplay benefit.
Harness idea, benefit ESTIMATED: extend the existing Java cabinet harness with
eight option combinations, UI changes during bootstrap, failed/replaced requests
and timed save/resume. Proposed owner desktop-games at its next validation slot;
no new framework/job. Reviewer has no new firsthand native/Blender/queue evidence.

### Bind source shortcuts through the existing guarded action interface

2026-10-15, pootscoot-desktop-games; java_package_gap_review source review.
PR152 package source c7b3f3e2 adds original Blackjack TableKeys through the same
IsBlackjackActionLegal/SubmitBlackjackAction path as buttons, with the separate
insurance affordability flag. Consume recognized disabled keys, require direct
board/table and opening-user focus, and exclude repeats/modifiers/controllers so
typing and button activation do not dispatch twice. Sudoku H only asks: consume
the confirmation target and recheck current game/canAct before the existing hint
request. Preserve the explicit labeled Hint button's source behavior. Clear old
prompts on create/open/resume/configure. Keep authoritative status visible beside
local form errors; a validation message must not conceal later service failure.
Source review and 110 static checks (56 unchanged baseline methods) pass; compiler,
behavioral tests/services/native remain deferred. No measured native benefit.
Harness proposal, benefit ESTIMATED: extend the existing Java cabinet acceptance
cases with focused forms/buttons, repeats/other user/controller edges, illegal
actions, H/Cancel/Buy and replaced IDs, plus invalid Configure followed by service
failure. Proposed owner desktop-games at its later validation slot; no new job
framework or runtime queue claim. No fresh Blender/native evidence from reviewer.

### Explicit local note overrides must represent an empty result

2026-10-15, pootscoot-desktop-games; sudoku_editing_source_trace source review.
Sudoku source da2b4a84 keeps local notes outside the Java answer snapshot. Preserve
untouched snapshot masks, but let each local toggle/erase establish an override,
including zero; falling back when the mask is empty would restore erased notes
on the next resync. Hide notes behind answers without deleting them, and clear
them before the unchanged-value early return on erase. Bind context to an accepted
board identity/shape, keep same-ID updates, and describe exact UI entry/configure/
close resets without promising durable saves. Route typed characters and pad
through one guarded entry helper; remove overlapping physical-digit dispatch.
Cosmetic counts/duplicates must never become local legality or completion rules.
Source review/57 static checks pass;14 existing Slate methods and entire actor,
public API/protocol/build files unchanged. Compiler/behavioral tests/native remain
deferred; no measured visual or performance benefit. Existing-harness proposal,
benefit ESTIMATED: exercise zero-mask resync, hidden notes/undo/refusal, refused vs
accepted same-ID entry, Shift/numpad/form focus and counted one-command dispatch.
Proposed owner desktop-games at a later authorized slot; no new framework/queue.



### Separate requested input, local acceptance and received identity

2026-10-15, pootscoot-desktop-games; existing java_package_gap_review worker.
Source6e287066 extends PR152 from c0cacb26 in only the private Java Slate pair.
An existing received-ID row needs clearer provenance, not a duplicate state store.
Editable/requested IDs, actor bool acceptance and received snapshots are distinct.
State-derived enabled recovery is only a candidate: private pending/unknown-create
branches remain actor authority. Preserve fresh Start after definite Blackjack
refusal; NeedsSync alone cannot distinguish that case from unknown creation.
Local Use current ID fills/focuses only. Show received answers separately from
local/received pencil masks, including explicit zero and hidden notes. Never
display Sudoku's unpopulated Revision as a server version. Independent manual
branch/source review passes; no counted suite/tests/builds/services/native ran.
Existing-harness proposal: use the documented identity/recovery/focus/cell matrix
at a later authorized slot. Benefit ESTIMATED, owner desktop-games; no new service,
framework, worker or runtime queue reservation. No firsthand native/Blender proof.

### Reopen through the existing read contract without bypassing uncertainty

2026-10-15, pootscoot-desktop-games, existing independent Java reviewer.
Blackjack already had a query route but no cabinet entry after close forgot the
received ID and bearer. Explicit Open now captures a private query target and
shares its CanOpen predicate with Slate. Refuse pending work, unknown creation,
uncertain mutations and live-table replacement before any reset. Bind all reads/
retries and atomic acceptance to that target; never seed accepted state from text.
Reuse existing generation, read budget, strict visible DTO and closed error path.
Local ID fill is not a request. New endpoints, controllers, durable storage and
per-player authority are unnecessary and not supplied by shared-bearer GET.
Source product impact: a recorded still-active table becomes reachable again;
no measured gameplay/performance benefit or runtime acceptance. Existing-harness
idea is the reopen branch matrix at a later authorized slot, benefit ESTIMATED;
no new framework/worker/job or editor/compute slot. No tests/build/services ran.

### Establish authenticated ownership before designing durable resume

2026-10-15, pootscoot-desktop-games; existing Java source/packet reviewer.
Backend code `a75241bd01e149df3b34c7dfdac1b9be93811939` scopes the existing bearer/routes, session ownership
and typed create-replay key to trusted immutable local profile credentials.
Check owner before caches/activity/engine; do not let legacy overloads or caller
body identity bypass it. Preserve nullable constructors using a named factory.
Legacy mode stays shared; opt-in local profiles are not Daedalus account mapping.
Actual storage trace matters: live-round bytes contain dealer/future shoe/rules;
SaveManager books live losses; RoundSeal needs a protected key supplied by Android,
not desktop. Single-file rename is not an atomic durable state/ledger transaction.
No bearer-derived encryption, plaintext export or invented resume adapter.
Product impact is a source authorization prerequisite;9 tests authored/unrun,
manual review only, no measured native/performance/security certification. Next
existing-harness cases are profile/refusal/replay/idle/capacity and legacy mode,
then actual provider/key/storage crash/restart work; benefit ESTIMATED, no new
framework/worker/editor or compute slot. Native7c4 source and saves unchanged.


### Capture decisions from the actual ledger before designing a store

2026-10-15, pootscoot-desktop-games; backend source `8b5a5c217889fcdf11392b359a6569dba651b112`.
Use one immutable grammar for live command equality and owner-gated inspection.
Capture actual historical creation bytes and FIFO cached replies with revision at
decision insertion, not expected/capture-time revision. Do not observe expiry or
renew activity during inspection. A future-revision refusal is valid; equal stamps
cannot prove order; evicted IDs can be reevaluated. Original create and command
namespaces differ. Strict HTTP inputs fit bounds but oversized trusted direct maps
can refuse capture. A frame without hidden state, clocks, global create refusals/
occupancy, authenticated codec and atomic protected storage cannot restore service
semantics. Structural validation is not authenticated import. Source impact is an
inspectable reusable decision boundary; no measured runtime/performance gain.
Six tests/four synthetic fixtures authored/unrun,13manualsourcecases,15protected
source pins. Existing reviewer only; no new framework/worker/service/build/compute.
Full app parity remains required. Native7c4 and original saves/keys unchanged;
actual account/key/storage/crash-restart and sole-operator native acceptance remain.
