# Epic primary-source findings: missing capability candidates (unreal-epic-boss, 2026-10-19)

Answers link 48155 (`epic-primary-source-findings-20261019-r1`), refined by 48161 (`epic-metaverse-acceptance-20261019-r1`).
This was read-only. Nothing was installed, enabled or run in the editor, and Slate was left alone (2hot2trot owns the 07:50 UTC block).

## Inputs checked
- Checklist: `C:/Users/730ri/Documents/Codex/2026-10-14/task/official-tools-capability-acceptance-r1.json` (56049 B).
- Handoff: `C:/Users/730ri/Documents/Codex/2026-10-14/task/epic-slate-delivery-r1/epic-research-owner-handoff.json`. SHA-256 is `539ed4a1d726db85c5f983ab9eac4f8793f7c5ba5f69edb13006a47a755885a6`, verified equal (22392 B).
- Engine: `C:\Program Files\Epic Games\UE_5.8`. `Engine/Build/Build.version` gives 5.8.3, CL 58210709 (compatible CL 55116800), `++UE5+Release-5.8`. There are 893 `.uplugin` files under `Engine/Plugins`.
- Project: `C:\Unreal\DaedalusRealm\DaedalusRealm.uproject` enables DaedalusLink, ProceduralMeshComponent, PythonScriptPlugin, EditorScriptingUtilities, ClaudeUnrealBridge, PCG, ModelContextProtocol and AllToolsets. It does NOT list FunctionalTestingEditor, InterchangeTests or CQTest.

Already covered by the two documents, so excluded here: asset inspection, static import/save/reopen, Blueprint, AutomationTestToolset, DataValidation, reimport, materials/collision/LOD (StaticMeshTools), skeleton/animation, BuildCookRun, Sequencer, MRQ, PCG, World Partition HLOD, Insights and SlateInspector.
Neither file mentions InterchangeTests / UInterchangeImportTestPlan, FunctionalTesting / AFunctionalTest or the PythonScriptCommandlet (keyword grep: 0 hits each). The handoff lists "Interchange and reimport" only as a bounded topic, with no capability ID or acceptance.

## Candidate 1 (highest value): Interchange import test plans, a deterministic ingestion gate for Blender-factory assets
- **Source (installed):** plugin `InterchangeTests` v1.0, `EnabledByDefault: true`, at `Engine/Plugins/Tests/InterchangeTests`.
  - `Source/InterchangeTests/Public/InterchangeImportTestPlan.h` (sha256 `90f3312570705449988e6a5c1a0d699bccc6b9497498817faa0c3bc808529caa`) defines `UInterchangeImportTestPlan` with import/reimport sections and `RunThisTest()`.
  - `Public/ImportTestFunctions/StaticMeshImportTestFunctions.h` (sha256 `9e3ba7a95e61ae2cd484b614024298a4ad8f641e74897eebb13c404571f9179e`) has functions including `CheckTriangleCount`, `CheckMaterialSlotCount`, `CheckImportedMaterialSlotName`, `CheckLodCount`, `CheckUVChannelCount` and `CheckSimpleCollisionPrimitiveCount`.
  - Also present: `ImportTestFunctionsBase.h` (sha256 `d64ce259a3336061c6da040c9500548ee393204fd2e016450918dfbb450ba6f9`) and Actor/Animation/Asset import test functions.
- **Metaverse purpose:** Blender-first content arrives with production naming, material slots, triangle budgets and collision exactly as specified. A failure is a deterministic named FAIL, not a visual guess. It turns the existing `combat_handoff` and BBA 1 specs into an in-engine import assertion. It augments the qualified 9877 import path and doesn't replace it.
- **Benefit / effort:** high benefit (repeatable per-asset acceptance across the 10k-island pipeline) for low effort. One test-plan asset per role, generated from the existing spec JSON.
- **Smallest acceptance test:** in the disposable eval project only (never DaedalusRealm), create ONE `UInterchangeImportTestPlan` for an isolated copy of `Prop_PracticeCrate.glb`. That file is staged at `bot-team/staging/practice-crate-20261019`, sha256 `b1453d459a26a767b6140bf2a0e17496325c3f1d932a916e98ce0516394538c3`, and blender-team (48158) plus my receiving gate verified 132 tris and 2 slots. The plan asserts:
  - `CheckTriangleCount`=132
  - `CheckMaterialSlotCount`=2
  - `CheckImportedMaterialSlotName` = Prop_PracticeCrate_M0 / _M1
  - `CheckSimpleCollisionPrimitiveCount`=0
  - `CheckLodCount`=1

  PASS is all five. Then a deterministic FAIL fixture: the same plan against the `combat_fixtures` defect GLB (wrong tri count) must report FAIL on `CheckTriangleCount`. The production world stays unchanged.
- **Unverified:** whether the plan runs through the qualified AutomationTestToolset path. Plans register as automation tests under an Interchange prefix in Epic's design, but this was not executed here. Socket checks are not in the static-mesh function list I read, so sockets stay with `combat_handoff`. The glTF translator path under Interchange for .glb was not exercised.
- **Existing owner:** native execution is codex-play-guard. The spec source is blender-team / Blender Boss (BBA 1) and 2hot2trot (`combat_handoff`). Test-plan authoring source is unowned, and unreal-epic-boss can prepare it as a packet.

## Candidate 2: FunctionalTesting traversal fixtures plus NavigationSystem reachability
- **Source (installed):**
  - Plugin `FunctionalTestingEditor` v1.0 (`EnabledByDefault: false`, not enabled in DaedalusRealm) at `Engine/Plugins/Tests/FunctionalTestingEditor`.
  - Runtime class `AFunctionalTest` in `Engine/Source/Developer/FunctionalTesting/Classes/FunctionalTest.h` (sha256 `f6250860a5e27a5354223af15048ce4fcbd94d65063cc0f303a18010a6234ad9`). It has `AssertTrue`, `AssertEqual_Vector(..., Tolerance)` and `FinishTest`.
  - Path queries come from `Engine/Source/Runtime/NavigationSystem/Public/NavigationSystem.h` (present).
- **Metaverse purpose:** the Sky Islands traversal acceptance named in ARCHITECTURE.md: horizontal gaps plus above/below layouts, finite jetpack fuel and grapple supplies. A placed functional-test actor gives a deterministic pass/fail per gap, such as "reachable with N fuel", "unreachable without grapple" or "respawn returns to the safe point". It runs through the Automation path already under qualification.
- **Benefit / effort:** high benefit (gameplay acceptance instead of screenshots). Effort is medium: one small C++ or Blueprint fixture plus an isolated test map, and the plugin must be enabled in the disposable project only.
- **Smallest acceptance test:** in an isolated test map inside the disposable project, place ONE functional test with two platforms 600 cm apart:
  1. A pawn launched with a fixed jetpack-fuel value reaches the far platform (`AssertTrue` on overlap within 5 s, `AssertEqual_Vector` landing within 50 cm).
  2. The same launch with fuel=0 must FAIL to reach it (the expected-negative fixture).
  3. The NavigationSystem path query between the two platforms returns no path, so the gap is traversal-only.
  - Run it via AutomationTestToolset RunTestsByFilter on that one test name and record the terminal result.
- **Unverified:** jetpack/grapple components don't exist yet as production code; the fixture uses a stand-in launch impulse. Enabling a plugin needs the operator's custody window. AutomationTestToolset fixture execution is itself still UNTESTED per the checklist, so this is blocked behind that stage.
- **Existing owner:** traversal mechanics have no owner since Team Claude went down (the squad-tactics nav backlog was unreal-team's). Native execution is codex-play-guard. unreal-epic-boss can own the fixture source.

## Candidate 3: PythonScriptCommandlet, headless production-convention audit on an isolated asset copy
- **Source (installed):** `PythonScriptPlugin` v1.0 (enabled in DaedalusRealm), commandlet `Engine/Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PythonScriptCommandlet.cpp` (sha256 `068f6468b9fc37652b00c393d3e113ebb7a3a02f6b95240089006e61c58f17d0`). Epic's documented use is `UnrealEditor-Cmd.exe <project> -run=pythonscript -script=<file.py>`; I didn't read the argument parse lines, so the exact flag is unverified.
- **Metaverse purpose:** check naming (`Prop_*`, `SM_*`/`MI_*`), material-slot names, simple-collision presence and world-scale bounds over isolated copies of real island packages, with no GUI and no live session. This is the "production naming/material/collision/scale checks" need in 48161, and it uses the existing `unreal` Python API the team already scripts against.
- **Benefit / effort:** medium-high benefit (a batch audit of hundreds of packages without tying up the bridge). Low effort, because it reuses existing Python checks.
- **Smallest acceptance test:**
  - Setup: copy ONE real island content folder into the disposable project, for example `/Game/Pythagoras` assets via file copy outside the live project.
  - Run the commandlet with a script that writes `audit.json`: count, names failing the convention regex, meshes with 0 simple collision, bounds outside 1 cm to 100 m.
  - PASS: the script exits 0, `audit.json` lists the known-good assets clean, and one deliberately misnamed copy is flagged.
  - Before and after hashes of the source folder prove nothing was written.
- **Unverified / conflict:** a commandlet IS a second editor process. It must run only inside codex-play-guard's custody window, never alongside the live editor, and never against DaedalusRealm. The team launch rule bans `-unattended` for editor launches; whether a commandlet needs it was not checked. The "one editor at a time" rule takes precedence.
- **Existing owner:** codex-play-guard executes. Each island's owner reviews findings for their own folder.

## Ranking and coordination
Order: 1, then 2, then 3. Candidate 1 fits the current priority (installed official tools, import/readback) and reuses an already-verified asset. Candidate 2 waits on the AutomationTestToolset fixture-execution stage. Candidate 3 waits on an editor custody window. None touches Slate, the frozen Codex result contract or the 9877 bridge. All three augment existing tested work after a tiny acceptance and replace nothing.
