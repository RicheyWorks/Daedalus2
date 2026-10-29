# Structured observation: pinned reference review

Reviewed by Codex on 2026-10-13 against the exact source revisions supplied by Poot29465.
This is source inspection, not an engine test, framework installation or endorsement of every path.

## PinWright: test the restored graph, not just a rollback response
[Rollback graph-pin test](https://github.com/PinWright/pinwright-ue/blob/47eb9718857f185cdd2e445f54d3b1329ada8701/Source/PinWright/Private/Tests/Bpir/TestBpirCompileRollbackGraphPins.cpp)
The fixture creates linked nodes, records their GUIDs, submits invalid replacement code and checks a
structured COMPILE_FAILED response. It then resolves original nodes by GUID and checks restored pins,
exact link counts and links in both directions. Adopt this preservation witness in our tests: explicit
identity and observed relationships after failure. This file alone does not establish save-to-disk
success, every rollback caller's behavior or compatibility with our editor build.

## UCP: attempted graph edits need readback
[BlueprintGraphDiffer.cpp](https://github.com/Italink/UnrealClientProtocol/blob/7f0a56e27875b40259b46a7f2de33e7de7d2045f/Source/UnrealClientProtocolEditor/Private/Blueprint/BlueprintGraphDiffer.cpp)
The differ matches GUIDs first and scopes removal to selected graph nodes. These are useful identity
and boundary patterns. In the LinksToCreate loop it calls Schema->TryCreateConnection without using
its return value, then appends a LinksAdded description. That description is an attempted edit,
not proof of a live connection. Our consumer must use observed graph/scene state plus explicit
compile diagnostics where applicable; a requested link or success-looking summary is insufficient.

## Agreed team boundary
Poot owns structured scene_snapshot/scene_verify producer work and bridge lifecycle cleanup.
Codex accepts schema-aware host result validation against that producer's actual schema/fixtures.
Claude owns editor runtime and has deferred reflected graph mutation tools. No competing queue,
write retry policy, framework install or invented schema is introduced by this review.

## Host validation requirements for the upcoming contract
* Preserve full object paths, world/session identity and observed values without normalization that
  loses precision or disambiguation. Reject duplicate identities rather than selecting the first label.
* Separate transport failure, malformed result, unavailable observation, failed predicate and verified
  predicate. Require explicit booleans; truthy strings and an empty/missing result cannot prove success.
* Keep expected and observed values plus diagnostics for each mismatch, including units/tolerances.
* A changed world/session invalidates earlier actor observations; never reconcile across scopes silently.
* Build fixtures for duplicate labels, PIE/editor scope mismatch, missing values, partial results,
  ambiguous mutation outcome, and readback contradicting a requested operation.
* Read-only consumers must never repair, retry a mutation, discard source state or convert unknown into pass.

Implementation awaits producer schema and fixtures requested in the correlated29465 reply. This review
adds requirements and evidence; it does not claim a schema validator is implemented or deployed.
