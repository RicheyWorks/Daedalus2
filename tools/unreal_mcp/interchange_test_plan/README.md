# Interchange import test plans (Epic P1 candidate 1, source only)

From docs/production/epic/ueb-findings-20261019.md, candidate 1: turn Blender hand-off specs into
deterministic per-asset import assertions using the installed `InterchangeTests` plugin
(`UInterchangeImportTestPlan`, StaticMeshImportTestFunctions).

| File | Role |
|---|---|
| `plan_core.py` | Engine-free: spec or receiver profile -> ordered checks; deterministic FAIL variant; verdict on observed results |
| `test_plan_core.py` | Engine-free tests (`python -m unittest test_plan_core`) |

Rules: no empty plans, a missing observation is a FAIL, the source sha256 is part of every plan,
and plans are refused for DaedalusRealm (disposable evaluation project only).

**Not done here (editor work, queued for the custodian, codex-play-guard):** creating the
`UInterchangeImportTestPlan` asset from a plan and running it through the automation path,
first for `Prop_PracticeCrate` (PASS) and its `CheckTriangleCount` FAIL variant.
