# Static subset admission

`asset_pipeline.subset` plans and checks a small static GLB subset using files
only. It does not generate a subset, launch Blender, contact a connector, import
into Unreal, or mark an asset ready for native use.

Run commands from `connectors/claude-asset-pipeline`. The module uses the Python
standard library. Both commands emit JSON on stdout.

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
entry point is `admit(plan, candidate_path, expected_candidate)`, using the same
`sha256`/`bytes` pin shape. Admission establishes source-file preservation only;
native readiness remains false.

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

## Produce the subset separately

Use an existing explicit-object exporter in a later allocated Blender job.
Open the retained scene in an isolated process, verify its source pin, select
exactly the planned existing meshes, and write a fresh output. Preserve geometry,
materials and authored transforms. Do not join, recenter, apply object
transforms, rename nodes or rewrite materials while claiming preservation.

The current pipeline CLI performs export followed by native import; it is not
this offline producer. No importer node-filter capability is established here.
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
selection handoff, no actual three-mesh subset had been generated or admitted,
and no native acceptance was established. The existing hero shows the whole
269-mesh assembly. Frozen AFTER source was not a generated Blender scene,
export or render.

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
- Keep build, export, image review, admission and native receipts separate, with
  captions tied to the revision and stage actually shown.

Run the offline contract suite with `python harness/subset_test.py`.
These tests do not establish Blender exporter execution or native acceptance.
