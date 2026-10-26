# Native Blueprint behavior authoring: proven recipe

Use Unreal's installed tools first. This recipe adds no graph-authoring wrapper,
toolset, endpoint or plugin. It was exercised on UE 5.8.4-58902052+++UE5+Release-5.8 using
the existing guarded bridge and `unreal.ToolsetRegistry.execute_tool`.

## Scope and prerequisites

Use sole editor custody, normal RAM/disk guards, no pending/uncertain operation,
a clean protected scene and a **new owned** `/Game/CodexToolEvaluation/...` target.
Refuse a foreign or occupied target before creation. Never pass an empty list to
`AssetTools.save_assets` (that saves all dirty packages). Do not enable access or
another transport for this recipe. Preserve the registered tools' typed `refPath`
results exactly; read current input and output schemas rather than copying stale ones.

Read registered `BlueprintBasicsSkill` using `AgentSkillToolset.GetSkills` and
the installed `BlueprintTools.get_graph_dsl_docs`. Discover the exact node types
and pins before graph writing. The exercised operators are in the adjacent proof.

## Native operation sequence

All Blueprint operations below belong to
`editor_toolset.toolsets.blueprint.BlueprintTools`; asset operations belong to
`editor_toolset.toolsets.asset.AssetTools`. A native dispatcher result must be
complete with no error before using its JSON `returnValue`; retain a pending result
and reconcile it instead of resending mutations. Void methods return an empty JSON object.

1. `AssetTools.exists({"path":"<new package path>"})` must return false.
   **The argument is `path`, not `asset_path`.** The latter was actually rejected
   by the schema before invocation; its complete evidence is retained.
2. `create(folder_path, asset_name, asset_type={"refPath":"/Script/Engine.Actor"})`.
   Keep the returned Blueprint ref. `asset_type` here is the parent class.
3. `add_function_graph(blueprint, graph_name="EvaluateProbe")`; keep its graph ref.
4. `add_function_param(graph, param_name="Value", param_type="int", input_param=true)`
   and the output `param_name="Result", param_type="int", input_param=false`.
5. For each needed operator, `find_node_types(graph, type_id_filter, context_pins=[])`,
   then `get_node_type_pins(graph, type_id=<actual discovered ID>)`.
6. `write_graph_dsl(graph, code=<below>)`. This installed implementation transpiles
   through Epic's graph APIs and **compiles automatically** after the logical unit;
   do not compile after every node. Require `BlueprintStatus.BS_UP_TO_DATE`.
7. `read_graph_dsl`, `find_nodes(graph,title="")` and `get_node_infos(nodes)` must
   show the intended typed links/defaults, not just an existing asset.
8. `get_default_object(blueprint)` resolves the generated CDO. Execute the real
   compiled function with existing Unreal reflection:
   `cdo.call_method("EvaluateProbe", args=(input_value,))`. No PIE/helper is needed
   for this side-effect-free function. Assert the independent expected results.
9. `AssetTools.save_assets({"asset_paths":["<exact new asset>"]})` must return true.
10. From a verified clean state, reload **only** that asset's top-level package:
    `EditorLoadingAndSavingUtils.reload_packages([package], interaction_mode=ReloadPackagesInteractionMode.ASSUME_NEGATIVE)`.
    Require tuple `(True, empty error)`. Load the asset again via `AssetTools.load_asset`,
    reacquire the graph/CDO and repeat structural and behavioral assertions.
    Compare all node/pin links, types, defaults and positions; compare saved file hashes.

## Authored function

```lisp
(fn EvaluateProbe (Value)
  (if (< Value 0)
    (return 0)
    (elif (> Value 100)
      (return 201)
      (else
        (return (+ (* Value 2) 1))))))
```

`Value` and `Result` are int32. Clamping avoids overflow at the tested int32 extremes.

| Input | Expected result, before and after disk reload |
|---:|---:|
| -2147483648 | 0 |
| -5 | 0 |
| -1 | 0 |
| 0 | 1 |
| 1 | 3 |
| 7 | 15 |
| 37 | 75 |
| 100 | 201 |
| 101 | 201 |
| 2147483647 | 201 |

The actual non-integer argument `"not_an_int"` was refused by Unreal's native
Python/reflection conversion as `TypeError`; it was not coerced to an accepted value.

## Verified result and limits

20 actual evaluations passed; 14 graph nodes, all links/defaults/types/positions
persisted exactly; one clean package reload succeeded and saved bytes stayed equal.
Protected original files, world, camera, selection and clean state matched the
before snapshot. Compute was normally released and the original editor retained.

This adopts a reusable **isolated behavior-function authoring slice**. It does not
qualify all53Blueprint tools, PIE/gameplay, arbitrary graph safety, production UI,
latent/component behavior or a fresh-editor reopen. No new C++/Python authoring
implementation or dependency was added. Inspect exact native errors and full logs
on failure; graph writes may leave partial private state, so never assume rollback.

Actual paths, engine/source identities, native receipts and hash pins:
`native-blueprint-behavior-pilot-20261022.json`.
