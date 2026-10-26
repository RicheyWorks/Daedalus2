# Commons pond ingestion profile — sole writer handoff

Code/preparation deliverable only. **Prepared 3; imported 0; admitted 0; held 3;
native validation NotValidated; this new profile has never run in Unreal.**
No editor connection, import/save, GUI launch/close, project edit, shared lesson
edit or PR410 branch edit was performed by the code worker.

**OperatorR1 follow-up:** the sole writer reviewed the existing source image,
then stopped before queue/import because the actual Islands corpus is 2,119
meshes, above the old 512 fixture cap. That refusal was reconciled and compute
released; no source-inventory meshes were loaded. The updated v2 adapter uses
complete registry traversal and bounded native source pages. Read
[COMMONS_POND_CORPUS_DELTA.md](COMMONS_POND_CORPUS_DELTA.md) for the exact next
writer operations, evidence, supported bounds and remaining native checks.

The previous receiver deliberately admitted only the original Coupler. These
sources must not be disguised as that fixture. The separate
`unattended_static_adapter.py` wraps the retained qualified-small-static
Interchange helper and the existing retained-call transport. The Coupler,
queue/checkpoint/STOP logic, receipt primitives and canonical Valid consumer are
unchanged. This is not general backlog/overnight qualification.

## Exact selection and destination plan

All sources are in
`C:/Users/730ri/projects/D2-build/engines/unreal/art/claude-aquatic/`.
Each FBX has the same-basename `.json` sidecar. Full source/sidecar/manifest/helper
witnesses and independently measured source facts are in
`fixtures/commons-pond-20261023.json`. Original manifest SHA256:
`cbee25058a48b2173cbba6adb66cc557a0f00779b76d09df1429f9551685ba87`.

| Source basename | FBX bytes | SHA256 | Triangles |
|---|---:|---|---:|
| Prop_Aquatic_Pond_Frogbit_4 | 16668 | 6bd59792c5edff9ab824f111bc13f7c1a082edc9b3a0f1162f9400bd5780adae | 220 |
| Prop_Aquatic_Pond_PinkLily_4 | 19068 | 8b5fcea2ae0a44926210bf9ccfcd42da3333d77f1187e36287797d0c15ba2eec | 544 |
| Prop_Aquatic_Pond_WaterLily_4 | 18780 | 5499801cc09c511b9183f3e66b41e9a27540aeea9b57cf2238fbe454e8f1af2d | 492 |

Use the supported existing import namespace, rather than the preparation's
incompatible `/Game/CodexToolEvaluation/.../20261023/...` proposal:

```text
/Game/Daedalus/Art/Islands/CodexContest/Ingestion/CommonsPond20261023/Prop_Aquatic_Pond_Frogbit_4_6bd59792c5edff9a
/Game/Daedalus/Art/Islands/CodexContest/Ingestion/CommonsPond20261023/Prop_Aquatic_Pond_PinkLily_4_8b5fcea2ae0a4492
/Game/Daedalus/Art/Islands/CodexContest/Ingestion/CommonsPond20261023/Prop_Aquatic_Pond_WaterLily_4_5499801cc09c511b
```

Each destination owns exactly one `/<source basename>.<source basename>` mesh.
Destinations remain plans; no native directories/packages were created.

The file-only FBX parse found v7400, one mesh/model/material, UnitScaleFactor100,
no animations/curves/deformers/textures/videos, exact palettes and bounds. These
are source measurements, not operator source-view acceptance or native evidence.
The existing profile requires one slot using the existing vertex-colour material,
explicit Interchange pipeline, build scale1, Nanite off, lightmap UV generation
off, collision off, and strict palette/geometry/material/metadata readback.
`claude_raw_unit100_build1_actor001_v1` remains exact: future actor scale is .01;
the adapter places no actors. Frogbit is at waterline0..15cm; the two lilies span
-25..15cm. Sidecar ecology/flowering labels do not establish runtime behavior.

## Apply and prepare safely

Only thread `01a139d3-4615-7398-b0fa-aaacca512030` may operate the editor.
Finish its current bounded operation first. Apply the code commit in that
writer's integration checkout only when it is ready; the isolated worker never
changes that checkout/index. Do not run the old Coupler witness, historical
Lotus host, old world/PID baseline or either competing watcher. Do not edit or
resume an existing state with new runner/profile bytes.

The preparation CLI is entirely offline and deliberately refuses the checked-in
measured/HELD fixture. These are inputs the sole writer supplies while doing the
already-authorized import; no further human approval is requested or required.

The exact existing source-review rule is
`contest-island-production/tools/unreal/codex_qualified_static_delivery.py:151-157`:
it requires stage `qualified_static_candidates_source_only` and
`source_views_personally_inspected_by_operator is True`, otherwise raises
`Operator must inspect exact retained source views before preparation`; it then
validates the source items and pins. This means the operator agent's source-view
and provenance review, not user reauthorization. The prior retained example is
`native-ingestion/PondLotusFloweringR1/operator-qualified-packet.json`, which
records the operator's family-image review and limits. Its acceptance is specific
to Lotus and does not automatically qualify these three new sources. The adapter
preserves that existing source check without requiring a new reviewer role,
observation format, human signature, licensing ceremony or questionnaire.
The actual original `sheet-pond.png` can be viewed directly as a file; Blender
and Unreal need not be opened for that source review.

The three required data inputs are:

1. **Qualification JSON:** schema `daedalus.source-qualified-small-static.v1`,
   stage `qualified_static_candidates_source_only`, helper-compatible `items`,
   all retained `source_pins`, and a real operator source-view inspection.
   The sole writer reviews the existing source/family image and the measured
   FBX/sidecar/recipe identities, retains their pins, and records the existing
   `source_views_personally_inspected_by_operator=true` declaration. It may keep
   the prior example's `operator_visual_review` image witness/observations for
   traceability; no new review-body format is required. Any supplied image
   witness is checked. Preserve unverified historical author and source
   provenance. Do not turn the fixture's false flag true without the review.
2. **Fresh baseline JSON:** exact keys `schema`, `editor`, `context`, `files`;
   schema `daedalus.static-owner-baseline.v1`. The writer captures `context()`
   from `unattended_static_native.inc` through its existing guarded read route:
   exact current world, all actor identities/classes/transforms/mesh bindings
   and viewport camera. `editor` is the current PID/full UTC start/project/world,
   not the old Coupler generation. `files` lists path/SHA256/bytes for every
   current protected original/owned file, including installed source/contracts,
   configuration, progress/user saves as applicable, active saved Commons map,
   installed DLL and original palette. Save/resolve current dirty work normally
   before this capture; no blanket save or discard is authorized by this patch.
3. **Paged source inventory JSON:** schema `daedalus.static-source-inventory.v2`,
   root `/Game/Daedalus/Art/Islands`, one pinned complete registry path capture,
   exact editor/native-reader witnesses, path count/digest and ordered page
   descriptors. Each actual native page covers at most 32 exact mesh identities
   and binds observed `codex_sha256` to its saved `.uasset` file fingerprint.
   Partial/unsupported pages, gaps, duplicates, unknown provenance, stale saved
   files and differing reader/editor/corpus identities refuse preparation or
   dispatch. All 2,119 current meshes need 67 pages (66 x 32 + 7), not a 512-row
   prefix. The same complete corpus plus verified DONE outputs must match current
   registry coverage before and after streaming all package hashes. No original
   corpus asset is loaded again during deduplication. Global names are checked
   separately; renamed untagged external imports outside this corpus are not
   certified. See the delta handoff for collection/build commands.

Create an environment JSON with exact keys `owner`, `editor`, `engine_version`,
`start_by_utc`, `host`, `wire`, `importer`, `shared`, `dependencies`. The four
module fields are exact path/SHA256/bytes witnesses, not module names:

- `host`: existing task-2 `official_tools_paired_benchmark_r3.py` (only its
  ordinary hub custody and OS generation readers are used).
- `wire`: existing `contest-island-production/connectors/claude-asset-pipeline/asset_pipeline/wire.py`.
- `importer`: existing `contest-island-production/engines/unreal/DaedalusLink/Content/Python/daedalus_codex_qualified_static.py`,
  SHA256 `ff67f266fa45b276d287d69d5fa750b445353960d7213234dede15bc1f135df0`.
- `shared`: same directory `daedalus_codex_catalogue.py`, SHA256
  `00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03`.

`dependencies` pins the full reviewed local imported host/transport chain,
including that host, `codex_skyfarm_greenhouse_delivery.py`,
`codex_qualified_static_delivery.py`, their helper imports, wire, installed
DLL/header/build version and policy/native wrapper/consumer dependencies.
Preserve the existing 1..32 explicit-dependency cap. Use the actual exact engine
version, actual owner and a finite current start-by UTC. The old184/world host
orchestration is not invoked: its native helper's private dictionary receives
the explicitly frozen current world while the original guard still executes.
No installed helper or shared module global is changed.
Preparation automatically pins the small `static_source_inventory.py` reader
and its transitive page witnesses; it does not add one dependency per page.

```powershell
python tools/unreal_mcp/prepare_static_profile.py --qualification C:/owned/pond-qualified.json --baseline C:/owned/commons-current-baseline.json --dedup C:/owned/source-inventory.json --environment C:/owned/current-environment.json --folder C:/owned/pond-profile-r1
```

Preparation creates new per-item policies, selected manifest and state; it
imports no adapter/host module and makes zero native requests. Review all hashes
and scope before the sole writer uses that state. After current custody/resource
admission, first run exactly one item through the existing queue interface:

```powershell
python tools/unreal_mcp/unattended_ingestion.py run --state C:/owned/pond-profile-r1/state --max-items 1
python tools/unreal_mcp/unattended_ingestion.py status --state C:/owned/pond-profile-r1/state
python tools/unreal_mcp/unattended_ingestion.py stop --state C:/owned/pond-profile-r1/state
```

Native acceptance/readback remains untested for this profile. Inspect exact
saved output, native Valid envelope, protected state, normal exact-lease release
and same-editor resume before proceeding one item at a time. Future placement,
visual/runtime/ecology/collision acceptance and fresh-editor reload are separate.
No bulk/overnight launch is authorized by these instructions.

Checks already completed offline: exact source/sidecar/manifest hashes, FBX
geometry/units/palettes/bounds/static-only metadata, acceptance by the retained
pure `_items` source validator, new adapter refusals, synthetic preparation and
existing queue interruption/STOP/resume logic. Checks the sole writer supplies
in its authorized editor window: actual current PID/world/engine/custody and
clean-state baseline; current native source-hash inventory/destination absence;
one real importer save and strict palette/geometry/metadata readback; exact native
Valid capture and protected-state comparison; then saved resume without a second
effect. Source-image/provenance review is file-only and can precede that window.

STOP persists and never kills native work. After known terminal, the owner may
clear only this state's STOP and use `resume --max-items 1`. DONE verifies saved
hashes and native helper readback, without import/save/revalidation. An uncertain
dispatch retains the exact compute lease/journal. Missing complete native receipt
blocks even reconciliation admission. The owner must establish actual terminal
and release its exact retained turn; TTL or another own lease is not evidence.
`reconcile()` itself only reads the unchanged operation-bound completion receipt;
it never imports, saves, starts validation, rebuilds receipts or retimestamps.
Incomplete, stale, NotValidated, Skipped, malformed or mismatched evidence stays
held/quarantined. Preserve every failed state; use a new reviewed state only
after explicit reconciliation, never reset or edit one to replay work.

## Offline verification and lesson to append later

```powershell
python -m unittest tools/unreal_mcp/test_static_source_inventory.py tools/unreal_mcp/test_static_registry_pages.py tools/unreal_mcp/test_unattended_static_adapter.py tools/unreal_mcp/test_unattended_ingestion.py tools/unreal_mcp/test_unattended_codex_adapter.py -v
```

Tests are synthetic or file-only, never new native evidence. The Windows
restricted temp sandbox denies the existing atomic `os.replace` in queue tests;
The original **59 focused tests passed** in the normal reviewed offline execution
environment (31 new profile/preparation checks plus 28 unchanged queue/Coupler
checks; latest run 1.655s). This includes real measured-HELD refusal before output creation,
synthetic successful preparation without host/native imports, source-hash and
destination refusal, immutable snapshots, pending reconciliation with no native
dispatch, STOP/resume and process interruption without a second effect.
Do not replace atomic writes to make tests pass.
The v2 corpus delta adds large-corpus/page/registry checks and replaces the old
single-dictionary mocks. Its exact final counts are recorded in the delta handoff.

**Lesson for the writer to append to the shared lessons file later:** A receiver
proved on one immutable asset is a fixture, not backlog capacity. Bind each new
source and sidecar hash to the existing import profile, current world/custody,
protected baseline and destination before declaring it ingestible. Deduplicate
by source hash independently of policy/path plus native destination coverage.
Reconciliation must consume the same durable result without import/save or
validation replay. Report prepared, imported, admitted and native-tested counts
separately; retain NotValidated/Skipped and unknown provenance exactly.
