# Import-time material receipts

`import_time_receipt.inc` is an additive observer for the existing Interchange
pipeline. `material_import_receipt.py` seals and validates its evidence. Neither
changes the engine's factory-dependency retention rules or the original-pair
persisted-node admission route.

Version 1 deliberately supports only the pinned constant-factor
`Prop_PracticeCrate.glb` source and a **new** standalone M0 material under one run
of `/Game/CodexToolEvaluation/MaterialProvenanceRecovery/<run>`. It refuses
instances, parameters, arbitrary graph evaluation, production paths, existing
asset replacement and full-material reimport. Original assets remain HELD.

## Producer

Use the existing single-writer/resource guard and Interchange async import path.
Create a fresh native generic-assets pipeline with static/skeletal mesh and
animation import disabled, material import enabled, existing-material reuse
disabled, and local material search. Append one retained instance of
`DaedalusImportReceiptObserverV1` after that pipeline. The observer disables the
other material root and refuses unexpected asset factory types.

Execute the observer source in a unique retained Python module with a `config`
dictionary containing `output`, `source`, `source_sha256`, `destination`, and
`copy_path`. The last key names the exact **new output** object path; it does not
enable a copy or reimport operation. Retain the module, parameters and pipeline
objects until the real completion delegate returns.

The post-factory and post-import hooks bind the translated source graph and its
typed attributes to the factory function/factor chain. The engine's public
`MaterialExpressionPath` attribute binds each factory UID to its actual created
expression. The native `ReadFreshImportedFactorCurrent` entry reuses the complete
current caller, roster, GUID, owner, direct-constant and mask checks. It also
checks the retained root and actual current source SHA256/MD5. It performs no
explicit load, authored edit, cache refresh, evaluation or compilation.

After exact one-asset completion, capture current evidence, remove only the
diagnostic Python pipeline from the new asset's pipeline list, verify the graph
payload did not change, save only the new asset, reload its clean package, and
obtain a distinct reloaded native witness. Never manufacture a post-save witness
by calling `load_asset` on an object already loaded.

Build the caller-owned policy before import with `build_policy`. Bind the actual
engine version, producer/reader hashes, installed importer/source/binary pins and
function package. `seal(policy, evidence, package_path)` accepts only the complete
fresh job, exact created bindings, source factors, completion, preservation and
real save/reload evidence. Store the resulting bytes in the existing receipt
artifact flow and retain their SHA256 in a separate trusted host manifest.

## Consumer

After sealing, dispatch a **separate** current native read under the normal guard:

```python
decision = consume(
    policy, receipt_bytes,
    expected_receipt_sha256=trusted_host_manifest["receipt"]["sha256"],
    current_native_raw=actual_new_native_bytes,
    expected_editor_pid=independently_verified_current_pid,
    package_path=independently_selected_saved_package,
)
```

The current capture must have a different ID from the import/reload captures, be
observed after sealing, match the independently supplied PID and be at most 300
seconds old. There is no clock override. Every admission rechecks exact source,
function/importer files, saved package bytes and the complete current graph and
source-root binding. Missing, changed, malformed, stale or mismatched evidence
remains HELD. A receipt's own hash or reload witness cannot supply its trust anchor
or substitute for the new current read.

A positive result admits only `FRESH_SOURCE_BASE_COLOR_RGB_BINDING_ONLY` for that
specific new asset. Scalars remain observed source-factor facts, and
`historical_admission`, `all_pbr_factors_qualified`, `root_output_equivalence_proven`
and the generic `native_runtime_qualified` flag remain false. This is no shader
evaluation, rendered-quality judgment, historical reconstruction, or standalone
cryptographic signature. The caller must trust and independently pin its actual
collector output. Any source, implementation, function, package or graph change
requires a new authoritative receipt.

## Verification

Run `python -m unittest tools.unreal_mcp.test_material_import_receipt` for the
focused synthetic and real-file protocol checks. The native test
`Daedalus.Editor.Material.FreshImportScopeRefusal` refuses original, traversal and
mismatched paths without import getters. Native adoption and remaining holds are
recorded separately in `engines/unreal/DaedalusLink/Docs/native-readers-20261021.json`.
