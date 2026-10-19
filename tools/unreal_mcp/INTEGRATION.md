# Official Unreal tool integration

The CodexContest delivery host can use the qualified class and registry audit
after its explicit save. It can also select the unit-correct FBX wrapper for a
new import. Both options preserve the existing delivery and material workflow.

## Delivery options

Pass `official_audit_endpoint="http://127.0.0.1:8000/mcp"` to
`tools.unreal.codex_contest_island_delivery.deliver`, or use the CLI option
`--official-audit-endpoint`. Each saved producer receipt gets a separate,
exclusively created `.official-audit.json` sidecar. The producer receipt stays
byte-identical. Completion requires the negotiated protocol, exact endpoint,
complete ordered wire responses, matching class/tags/requested metadata, and
confirmed session cleanup. A failed or incomplete audit raises before delivery
returns; inspect its retained sidecar and reconcile before another operation.
This audit qualifies asset identity and metadata. Geometry and disk persistence
require their own readbacks.

Pass `unit_qualified_import=True` or `--unit-qualified-import` to select
`daedalus_unit_tools.unit_qualified_static_toolset.UnitQualifiedStaticMeshTools`.
The caller must already have registered the pinned wrapper and admitted the
native operation. The integration describes its exact schema before one import,
checks the returned owned references, and never falls back or retries. The
wrapper sets scene and source-unit conversion explicitly. Its native acceptance
fixture imported, saved, and reopened a 400 by 100 by 50 cm mesh; other geometry,
palette, collision, and UV requirements remain asset-specific. The existing
client protocol is unchanged, so a client/profile compatibility failure stops
this opt-in route.

## Result contracts

`AutomationResultContract` consumes completed `Mcp.call` results in order:
`accept_discovery`, `accept_catalog`, then `evaluate_run`. Discovery must be ready,
the catalog must be uncapped and match the exact nonempty requested set, and all
returned tests must be terminal with consistent aggregates. Failures, warnings,
skips, missing results, and nonterminal states cannot pass. Native execution of
this contract remains unqualified.

`evaluate_native_validation` checks an explicit native DataValidation snapshot,
including counts, settings, exact asset identities, details, and messages. There
is no verified official MCP callable or serializer for this API in the current
profile; this module does not enable the plugin or invent a wire schema.

The auditor's `McpToolError.data` preserves bounded tool/error text without
request arguments. A complete error response does not establish rollback or
safe replay. Transport failure remains an unknown native outcome.

`BlueprintCDODiagnosticTools` is a separately registered disposable-project
wrapper around the unchanged stock setter. Its read-only context reports the
CDO/default/world and editor subsystems. Its setter uses the public scoped
`tool_raising_exceptions` context to retain stage and observed exception type,
including empty assertions. It keeps the stock permissions, permits only the
exact owned integer zero-to-37 fixture, and requires reconciliation after any
failed write. Its 26 mocked checks pass; native qualification is pending.

## Blueprint fixture

`fixtures/blueprint_compiled_zero_r1` contains the saved diagnostic asset,
portable recipe, sanitized receipt, and original setter error. Strict compile,
exact save, and a fresh-process reopen preserved `AuditValue=0`. The requested
`AuditValue=37` setter returned a complete native error; read-first reconciliation
found zero and no setter retry occurred. Full value-editing acceptance remains
failed. The wrapper's compile return is `null`; its helper enforces strict native
Blueprint status. The underlying C++ compile API separately returns a boolean.

After the diagnostic run, memory admission recovered and the restored main
editor's preservation proof found only a startup viewport-camera reset. The
remaining-only `viewport_preservation.run` callback restored that recorded
camera once, then independently checked the scene and camera. All 252 protected
files, map/config bytes, actor digest, and selection matched; no asset or map
save occurred. `restoration_completion.json` retains the scoped outcome and
receipt hashes. This callback requires external admission and pinned clean
before/target snapshots; it never retries a retained intent.

## Offline verification

From the repository root, use a new report path:

```text
python -B -S -E -m tools.unreal_mcp.offline_gate --report NEW_REPORT.json tools.unreal_mcp.test_asset_receipt_audit tools.unreal_mcp.test_automation_result_contract tools.unreal_mcp.test_validation_result_contract tools.unreal_mcp.test_tool_result_errors tools.unreal_mcp.test_delivery_integration tools.unreal_mcp.test_blueprint_cdo_diagnostics
```

The runner blocks real sockets and Unreal imports. The recorded 2026-10-19 runs
passed 133 tests with zero skips, failures, or errors, including 130 mutations of
delivery wire evidence. Measured times and process memory are in
`fixtures/source_verification_20261019.json`; these are source-test measurements.
