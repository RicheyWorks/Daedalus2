# Offline World Package preservation preflight

The existing importer reads World Package v1 and validates its format, version,
world GLB header and chunk count. Its native import path uses replacement,
shared materials and a fixed level. This adapter addresses the missing
preservation/replay planning boundary identified by
[the catalog audit](CODEX-CATALOG-HOOKS-20261026.md). It leaves that importer
unchanged and reuses its actual `read_package` and `glb_summary` functions.

From the repository root, using Python 3.10 or later:

```console
python -m tools.world_package /path/world-zero-r12.daedalus.zip
python -m tools.world_package /path/world-zero-r12.daedalus.zip --prior-receipt /path/accepted-r12.json
```

The CLI reads local files and prints JSON to stdout. Exit 0 means a valid
`plan_new` or `no_op` plan; exit 1 means refusal with an error on stderr. It
does not fetch URLs, extract ZIPs, write receipts, or touch native content.
The Python API is `tools.world_package.build_plan(path, prior_receipt=None)`;
invalid input raises `PlanError`. Runtime has no third-party dependencies.

## Destination and identity contract

Each root is under `/Game/Daedalus/PackageImports/`, followed by a readable
16-character world-name prefix, revision and full SHA-256 of the canonical
JSON array `[raw_world_id, revision, package_sha256]`. Raw IDs remain unchanged
in the plan. Names that collapse to the same sanitized prefix, case variants
and Unicode variants have distinct identity hashes. Hash input uses UTF-8,
JSON ASCII escaping and compact comma/colon separators.

Level, geometry, materials and every declared asset receive destinations below
that root. Asset subdirectories similarly retain a readable prefix and full
hash of the original UTF-8 asset name. Original asset `name`, `file` and `use`
values are retained in the plan; new revision roots preserve predecessor
destinations. All policy flags forbid replacement, deletion, shared materials
and live connection. `native_acceptance` is always false.

Supply a prior receipt explicitly when comparing against an accepted import:

```json
{
  "format": "daedalus-world-import-receipt",
  "version": 1,
  "status": "accepted",
  "world_id": "world-zero",
  "revision": 12,
  "package_sha256": "<64 lowercase hex digits from accepted plan>",
  "destination_root": "<exact root from accepted plan>",
  "acceptance_reference": "<native owner's retained acceptance evidence>"
}
```

This is an illustrative receipt shape; replace the placeholders with actual
owner evidence. The planner never generates acceptance evidence. Supplied
receipts are assertions, not authenticated native state. The native owner must
verify their authenticity, custody and actual saved/reopened content.

An exact raw ID, revision, byte hash and recomputed destination match returns
`no_op`. Different bytes at the same accepted revision, an older revision,
a different raw ID, a forged destination, unknown fields or unsupported
receipt versions refuse. A newer revision produces a fresh plan and includes
`previous_destination_root`. Without a prior receipt, the result is a proposal;
absence of a receipt does not prove that its destination is unoccupied.

[import-plan-v1.schema.json](../../tools/world_package/import-plan-v1.schema.json)
defines both output and accepted-receipt structure using JSON Schema 2020-12.
Runtime additionally checks derived paths and cross-field identity bindings;
structural schema validation alone does not establish those relationships.

## Input limits and reader reuse

The adapter snapshots at most 64 MiB of ZIP input and permits at most 4,096
file entries / 256 MiB expanded content. It refuses unsafe or nonportable
names, directories, symlinks, encrypted entries, duplicate/case-colliding
members, file/directory prefix collisions, ambiguous JSON keys and nonfinite
numbers. JSON integer/float token lengths are bounded before conversion, also
on early Python 3.10 releases. Server packages contain
file entries only. ZIPs and prior receipts are never modified on success or
refusal. Declared asset names/files cannot collide case-insensitively.

The adapter compiles only the existing reader's literal constants, exception
and two pure functions from its source. It does not import the native module,
attempt `import unreal`, evaluate its CLI/top-level statements, or call its
fetch/native functions. Changed reader signatures fail closed and require
review. This is a source adapter to the existing interface, not a second
implementation of the package grammar.

The legacy reader validates `world.glb` envelope/version and node count, plus
declared asset presence. This preflight does not establish secondary GLB CRC
or geometry validity, full glTF/material/texture semantics, external URI
availability, rights, native filesystem path compatibility or import success.
Package hashes bind exact source bytes, including ZIP metadata; a repackaged
archive is different evidence even if its extracted contents match.

## Native owner integration dependency

Boss's existing importer owner must adopt and validate these destinations
through the native pipeline before use. The old importer does not consume
this plan and must not be invoked expecting these preservation policies.
Adoption must check destination absence or exact accepted replay, local
materials, fresh versioned level, no replacement or actor deletion, actual
sole-writer custody, resource limits, clean saved state and native validation.
The planner's paths are proposals and do not claim an exclusive reservation.
Plan/review/test success is separate from native import, source-to-DLL parity,
gameplay or saved/reopened acceptance. This lane performs none of those actions.

## Verification

```console
python -m pip install 'jsonschema==4.25.1'
python -m unittest discover -s tools/world_package/tests -p 'test_*.py' -v
```

Synthetic fixtures exercise actual package-reader refusals, exact replay,
revision conflicts, raw-ID/sanitization collisions, owned asset/material/level
destinations, strict receipts/schema, input immutability, malformed ZIP/GLB/JSON,
resource budgets and blocked native/network/top-level execution. CI runs the
same serial Python 3.10 suite, including when the existing reader changes.
