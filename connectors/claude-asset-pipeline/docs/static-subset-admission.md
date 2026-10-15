# Static subset export and admission

`asset_pipeline.subset` plans, produces and checks a small static GLB subset
using pinned files. Its producer is `pinned-glb-byte-extraction`: a source-derived
GLB subset with zero Blender calls. It does not contact a connector, render,
import into Unreal, or mark an asset ready for native use.

Run commands from `connectors/claude-asset-pipeline`. The module uses the Python
standard library. All commands emit JSON on stdout. `plan` and `admit` read
existing files without writing artifacts; shell redirection saves their JSON
when requested. `export` intentionally creates the specified fresh GLB file.

## Plan from a pinned baseline

Provide the baseline GLB's expected SHA-256 and byte length from its retained
receipt, plus one to three explicit, unique mesh-node names:

```text
python -m asset_pipeline.subset plan --source full.glb --sha256 SOURCE_SHA256 --bytes SOURCE_BYTES --nodes A B C > plan.json
```

Replace the uppercase pin placeholders with the recorded values. Every selected
node must be a scene-root mesh. An empty name list must fail; it must never fall
back to visible meshes, a collection, or the whole assembly. The plan records
the selected baseline evidence; it is not a subset GLB or an export command.
Pins require 64 lowercase hexadecimal SHA-256 characters and a positive integer
byte length of at most 64 MiB per GLB.

Each selected source or candidate inspection has these work caps:

- Exactly one JSON chunk, capped at 4 MiB, followed by one embedded BIN chunk;
  extra chunks or trailing data are rejected during parsing.
- 100,000 rows per accessor, including index accessors.
- 1,000,000 decoded scalar components across the selected meshes.
- 100,000 selected triangles across the selected meshes.
- 16 attributes per primitive, with attribute names limited to 64 characters.
- 16 MiB of cumulative canonical witness work, charged for material/metadata,
  corners, faces and node witnesses, including repeated representations.

Accessor row/component caps are checked before decoding; the triangle cap is
checked before corner and face construction. Repeated decoding of a shared
accessor consumes the component budget again. An indexed triangle primitive
therefore fits at most 33,333 triangles in one index accessor. These are admission
limits, independent of the full assembly's authored budget.

The Python entry point is
`make_plan(source_path, names, expected_source)`, where `expected_source` is
`{"sha256": "<recorded SHA-256>", "bytes": <recorded integer byte length>}`.

## Admit an independently produced candidate

After a separately authorized exporter has created an actual subset file and
recorded its pin, check that file against the saved plan:

```text
python -m asset_pipeline.subset admit --plan plan.json --candidate subset.glb --sha256 CANDIDATE_SHA256 --bytes CANDIDATE_BYTES
```

Replace the candidate placeholders with the export receipt's values. The Python
entry point is
`admit(plan, candidate_path, expected_candidate, include_geometry=False)`, using
the same `sha256`/`bytes` pin shape. Admission establishes source-file
preservation only; native readiness remains false.

The supported scope is static, embedded GLB geometry. Skins, morph targets,
images, textures, external data and extensions are outside this contract.
The candidate must contain exactly the selected mesh nodes and their used mesh
and material definitions, without extra nodes, meshes or unused material
definitions. Checks preserve triangle corners and winding, UVs, normals, raw
PBR values, node transforms and extras. Matching counts alone is insufficient.
Geometry equality covers referenced triangle corners; unused accessor vertices
and unreferenced BIN bytes are outside that comparison. Admission checks the
used definition sets without certifying compact BIN packing or general glTF
conformance.

### Optional geometry handoff

Append `--geometry` to the `admit` command, or pass `include_geometry=True`, to
include a `geometry` object in its JSON receipt. This option reads the existing
candidate and leaves it unchanged. It is not an `export` flag.

The manifest includes each node's actual referenced POSITION bounds, local
bounds before its root transform, source-scene world bounds after that
transform, aggregate world bounds, triangles, observed attributes, primitive
material indices and raw material definitions. Matrices use glTF column-major
storage; TRS is applied as translation times rotation times scale.

With this option, root matrices must be affine and root quaternions must be unit
length; non-finite transformed positions or bounds are rejected. The reported
basis is glTF metres, +Y up and right-handed. These source-scene world bounds
are file evidence; native conversion, actor scale, pivots, collision and runtime
placement remain unverified.

`source_material_slots` counts distinct GLB material definitions referenced by
the mesh's primitives. A primitive without a material has a `null` entry in
`primitive_material_indices`. Unused Blender authoring slots and native slot
assignments require separate evidence. This optional report retains
`native_ready: false` and does not establish native acceptance.

## Produce a source-derived subset

```text
python -m asset_pipeline.subset export --plan plan.json --output FRESH.glb
```

The Python entry point is `export_subset(plan, output_path)`. It verifies the
pinned source and plan, copies whole used bufferViews, and remaps the selected
node/mesh/material/accessor/view references. It preserves copied BIN bytes,
accessor-relative offsets, interleaving, raw material values, metadata and
authored transforms within the selected definitions. Scene metadata and
top-level extras are rebuilt for the subset, and the original source asset
record is retained in the receipt. Identical inputs and selection produce
deterministic GLB bytes. No Blender scene is opened and no geometry is rebuilt.

The producer stages and admits the actual candidate before publishing it with
`os.link` to the requested fresh path. Filesystem hard-link support is required;
an existing destination or a failed hard link prevents publication. There is no
overwrite or copy fallback. A successful receipt reports `exported: true`,
successful admission and `native_ready: false`.
If verification fails after publication, the output remains unadmitted for
reconciliation; its presence must not be interpreted as success or retried by
overwriting it.

Each used view is copied once per source index to an aligned output span.
Distinct overlapping views can duplicate source bytes, so output capacity is
checked before allocation. Whole-view copying can retain unused bytes inside a
referenced span; this is not binary redaction or compact BIN packing. Originals
remain untouched and their pins are rechecked.

The existing `python -m asset_pipeline` CLI performs export followed by native
import; it is a separate workflow. No importer node-filter capability is
established here. A future Blender re-export is also a separate producer and
must carry its own execution receipt.
Do not publish a queue READY state or dispatch a native import from an admission
result. Native units, pivots, material transfer, collision, placement and saves
require their own operator acceptance and receipts.

## Copperfall example and evidence boundaries

The retained Copperfall Ark Rest baseline GLB is 812,404 bytes with SHA-256
`87ac937eb27a422cc04fb5c1b0f785091df3f5b62d1e8e5df1e30987829a0117`.
Its proposed selection is:

| Exact baseline node | Triangles | Material |
|---|---:|---|
| `CAR_Overlook_Stone_Plinth` | 156 | `CAR_rock_light` |
| `CAR_Heartstone_Copper_Base` | 116 | `CAR_copper` |
| `CAR_Heartstone` | 20 | `CAR_heartstone` |

These three meshes total 292 triangles and three materials across two module
roles. They were identified in the completed full-assembly export. At the
2026-10-15 selection handoff, before the source-derived producer step, no actual
three-mesh subset had been generated or admitted and no native acceptance was
established. The retained hero showed the whole 269-mesh assembly. At that
handoff, frozen AFTER source was not a generated Blender scene, export or render.

### Actual Copperfall artifact evidence

The source-derived export completed at **2026-10-15 18:43:03.938417 UTC**, as
recorded in `export-run.json`:

- File: `Copperfall_Ark_Rest_842401_plinth_heartstone_subset_r1.glb`.
- Size: **18,732 bytes**.
- SHA-256: `3a0a9b8a36b8dbf9199f78b9110a8e70742759b61f89b13b49354f43afdfd142`.
- Producer: `pinned-glb-byte-extraction`; exported and source-admitted, with
  `native_ready: false`.

`export-receipt.json` records production; `admission-manifest.json` contains the
geometry handoff. A second direct GLB/source read in `provenance-review.json`
passed 72/72 checks, including copied view bytes, raw materials, transforms,
bounds and all 28 protected file pins. It did not invoke the producer or
admission implementation.

Source node/mesh indices 54, 55 and 56 became subset indices 0, 1 and 2. The
logical node names above remain distinct from the mesh-definition names
`Cylinder`, `Cylinder.001` and `Icosphere.020`. The actual payload has three mesh
nodes, 292 triangles and one used material definition per mesh.

This is an actual source-derived GLB subset, with no Blender re-export, new
render or native acceptance. The retained hero still shows the full assembly;
native material binding, units, pivots, collision and placement remain pending.

Keep these stages and their receipt timestamps explicit. A later candidate
admission must not relabel an earlier whole-assembly image as a standalone subset
view, or source admission as native approval.

## Reusable lessons and offline checks

- Require explicit nonempty names and byte pins; never infer scope from visible
  objects or certify preservation from triangle/material counts alone.
- Preserve raw linear PBR values, including metallic, roughness and emission.
  Do not apply a second colour conversion or substitute a generic material.
- Preserve authored pivots and transforms. Metre source units or FBX unit
  metadata do not establish a native actor scale.
- Remap distant or nonconsecutive indices, including index zero; preserve
  definitions shared by selected nodes or primitives. Do not merge distinct
  definitions merely because their values look alike.
- Budget duplicated view spans and alignment before constructing output. Keep
  original files unchanged, and publish only to a fresh no-overwrite path.
- Keep build, export, image review, admission and native receipts separate, with
  captions tied to the revision and stage actually shown.

Run the offline contract suite with `python harness/subset_test.py`.
These tests do not establish Blender exporter execution or native acceptance.
