# Offline World Package census

Count exported World Package **asset definitions** per world, explicitly bound
realm, and explicitly bound island. The adapter consumes the existing
`WorldManifest.java` / `WorldPackageService.java` format
`daedalus-world-package`, version 1. It reads only JSON files supplied as
arguments. Geometry files, asset files, URLs, live services and engine state
are never opened or queried. There is no default catalog discovery.

Run from the repository root with Python 3.10 or newer (runtime uses stdlib only):

```sh
python -B -m tools.world_census \
  tools/world_census/fixtures/alpha.json \
  tools/world_census/fixtures/beta.json \
  --snapshot-date 2026-10-26 \
  --bindings tools/world_census/fixtures/bindings.json \
  --output-dir /tmp/census-2026-10-26
```

The output directory must be new, with an existing parent. Each invocation
creates `census.json` and `daily.csv`; choose a fresh directory for another
snapshot. No input or existing output is overwritten. Exit 0 means both files
were written; exit 2 gives a refusal or I/O error on stderr. Validation finishes
before reserving the output directory. Directory reservation is exclusive;
files use exclusive creation too. Two-file crash atomicity is not promised:
on a disk/write failure a partial new bundle is preserved and identified in
the error. Inspect it and choose another fresh directory after fixing the cause.

## Counts and identities

- A world is identified by raw `world.id`. Supply one revision per world per
  snapshot. Structurally identical JSON duplicates (including different object
  key order/whitespace) count once; every distinct raw source SHA-256 is retained.
  Different manifests for the same world, even at the same revision, refuse.
  No implicit newest-revision selection occurs.
- An island is a unique nonnegative `islands[].slot` within its world. An asset
  definition is the unique `(name, file)` pair within its world, including `use`.
  Referencing the same filename in two worlds counts two world-specific
  definitions. Repeated asset identities or island slots in a manifest refuse.
- `WorldManifest` does not supply a realm ID or an asset-to-island association.
  Realm and placement remain JSON `null` without explicit bindings. Descriptive
  `use`, live arks/berths, titles, paths and styles never imply placement. A
  definition assigned to one island is counted once, regardless of how many
  runtime instances could use it. Native instances, loaded assets, ownership,
  completeness and saved/live world acceptance are outside these counts.
- Separate unknown totals identify worlds/assets without a realm and definitions
  without an island. Every world includes all island slots, including zero counts.
  `realms` counts known realm IDs only; a `null` realm summary contains unassigned
  worlds. No fake realm or island identity is created.

The CLI requires explicit `--snapshot-date YYYY-MM-DD`; it does not infer a
capture date from clocks or input timestamps. Sources record SHA-256 and world
revision; output paths and local absolute input paths are omitted. Array ordering,
JSON and CSV bytes are deterministic for the same input bytes/date/bindings,
regardless of argument order or repeated input paths.

## Explicit bindings

Use the strict [bindings schema](../../schemas/world-census-bindings-v1.schema.json):

```json
{
  "format": "daedalus-world-census-bindings",
  "version": 1,
  "worlds": [{
    "world_id": "alpha",
    "revision": 12,
    "realm_id": "synthetic-realm",
    "assets": [{"name": "ark", "file": "assets/ark.glb", "island_slot": 2}]
  }]
}
```

`realm_id` and `assets` are independently optional; omitted values stay unknown.
Each world binding must match a supplied world's exact revision. Asset bindings
must match both name and file, and an existing island slot in that same world.
Unknown identities, stale revisions, duplicate bindings, additional binding
fields, unsupported formats/versions, duplicate JSON keys, nonfinite numbers and
booleans in integer fields refuse before outputs. Missing manifest asset/island
arrays mean empty lists, matching the Java DTO's null-list normalization; explicit
JSON `null` arrays are refused. Manifest fields the census does not consume are
allowed and are covered by the input hash; this is not full package/geometry
validation. Inputs are limited to 128 files and 4 MiB per file. Asset `file` values
must be relative package paths, but those paths are never accessed.

## Daily sheet export

`daily.csv` is UTF-8 CSV with a stable header and a required snapshot date on
every row. Import it into a spreadsheet as a daily sheet. It contains `total`,
`realm`, `world`, `island`, and `unassigned_island` scopes. Filter by one scope;
the hierarchy intentionally repeats counts, so summing all rows double-counts.
Blank realm/island cells mean unknown or not applicable; JSON distinguishes them
with explicit nulls. Source hashes are semicolon-separated per row; the optional
bindings hash is included on every row. Numeric counts remain numeric. Formula
prefixes (`=`, `+`, `-`, `@`, including after whitespace) in text cells receive a
leading apostrophe for spreadsheet safety; JSON retains raw identities.

The [report schema](../../schemas/world-census-v1.schema.json) describes the JSON
contract. Schema validation checks shape; CLI validation also enforces reference,
identity, revision, count and duplicate semantics. There is no scheduled job or
external sheet write; invoking the exporter remains explicit.

## Offline verification

```sh
python -m pip install jsonschema==4.26.0
python -B -m unittest tools.world_census.test_census -v
```

`jsonschema` is a test dependency only. Synthetic fixtures exercise multi-world
counts, explicit/unknown dimensions, duplicate provenance, deterministic bytes,
refusals, fresh outputs, partial-write reporting, CSV safety, both schemas, and
the CLI under the interpreter running the tests. CI runs Python 3.10 on Linux
and Windows serially. No test requires Unreal, private assets or network calls.
