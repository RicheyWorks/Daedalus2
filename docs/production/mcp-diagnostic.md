# Epic Unreal MCP diagnostic — 2026-10-14T02:53:15

67 toolsets, 830 tools, inventory in 2.2 s. Probes: 16 ok, 2 failed, 4 skipped.

| toolset | tools | read-like | write-like | describe s |
|---|---|---|---|---|
| AutomationTestToolset.AutomationTestToolset | 7 | 4 | 3 | 0.015 |
| ConfigSettingsToolset.ConfigSettingsToolset | 8 | 5 | 3 | 0.015 |
| Data access for reading and writing properties | - | - | - | 0.013 |
| DataRegistryToolset.DataRegistryTools | 7 | 7 | 0 | 0.017 |
| DataflowAgent.DataflowAgentToolset | 22 | 7 | 15 | 0.017 |
| Dependency rollups via GetSystemDependencies | - | - | - | 0.015 |
| Dynamic-input chain traversal via GetDynamicInputChain | - | - | - | 0.014 |
| EditorToolset.EditorAppToolset | 21 | 8 | 13 | 0.02 |
| EditorToolset.LogsToolset | 4 | 3 | 1 | 0.013 |
| Enum value lookups | - | - | - | 0.018 |
| FX-related operations in levels or blueprints | - | - | - | 0.017 |
| FindNiagaraScripts | - | - | - | 0.015 |
| GASToolsets.AbilitySystemInspectorToolset | 4 | 4 | 0 | 0.019 |
| GASToolsets.AttributeSetToolset | 2 | 2 | 0 | 0.014 |
| GASToolsets.GameplayCueToolset | 8 | 4 | 4 | 0.016 |
| GameFeaturesToolset.GameFeaturesToolset | 7 | 5 | 2 | 0.014 |
| GameplayTagsToolset.GameplayTagsToolset | 6 | 3 | 3 | 0.015 |
| General usage information | - | - | - | 0.015 |
| GetAssetDiscoveryInfo | - | - | - | 0.013 |
| GetNiagaraScriptDigest | - | - | - | 0.014 |
| Niagara Components on actors | - | - | - | 0.014 |
| NiagaraToolsets.NiagaraToolset_Assets | 3 | 3 | 0 | 0.015 |
| NiagaraToolsets.NiagaraToolset_Blueprint | 2 | 0 | 2 | 0.016 |
| NiagaraToolsets.NiagaraToolset_Component | 4 | 2 | 2 | 0.02 |
| NiagaraToolsets.NiagaraToolset_Info | 1 | 0 | 1 | 0.017 |
| NiagaraToolsets.NiagaraToolset_System | 46 | 28 | 18 | 0.055 |
| PCGToolset.PCGSpatialToolset | 1 | 0 | 1 | 0.012 |
| PCGToolset.PCGToolset | 30 | 10 | 20 | 0.021 |
| PhysicsToolsets.PhysicsAssetToolset | 17 | 5 | 12 | 0.014 |
| PluginToolset.PluginToolset | 17 | 11 | 6 | 0.019 |
| Runtime Niagara system manipulation | - | - | - | 0.017 |
| Schema discovery for understanding structure | - | - | - | 0.012 |
| SemanticSearchToolset.SemanticSearchToolset | 2 | 2 | 0 | 0.017 |
| SlateInspectorToolset.SlateInspectorToolset | 14 | 2 | 12 | 0.023 |
| System, emitter, and module creation and modification | - | - | - | 0.009 |
| ToolsetRegistry.AgentSkillToolset | 4 | 2 | 2 | 0.016 |
| Topology and Summary inspection for viewing current configuration | - | - | - | 0.012 |
| UMGToolSet.UMGToolSet | 23 | 7 | 16 | 0.025 |
| User variable overrides on component instances | - | - | - | 0.015 |
| WorldConditionsToolset.WorldConditionTools | 2 | 2 | 0 | 0.017 |
| aimodule_toolset.toolsets.behavior_tree.BehaviorTreeTools | 7 | 7 | 0 | 0.016 |
| animation_toolset.toolsets.conditions.SequencerConditionTools | 9 | 3 | 6 | 0.013 |
| animation_toolset.toolsets.controlrig.ControlRigTools | 44 | 21 | 23 | 0.026 |
| animation_toolset.toolsets.controlrig_sequencer.SequencerControlRigTools | 72 | 26 | 46 | 0.017 |
| animation_toolset.toolsets.custom_bindings.SequencerCustomBindingTools | 8 | 3 | 5 | 0.018 |
| animation_toolset.toolsets.import_export.SequencerImportExportTools | 6 | 2 | 4 | 0.016 |
| animation_toolset.toolsets.keyframing.SequencerKeyframingTools | 22 | 9 | 13 | 0.011 |
| animation_toolset.toolsets.outliner.SequencerOutlinerTools | 18 | 11 | 7 | 0.012 |
| animation_toolset.toolsets.sequencer.SequencerTools | 140 | 53 | 87 | 0.022 |
| conversation_toolset.toolsets.conversation.ConversationTools | 7 | 7 | 0 | 0.018 |
| editor_toolset.toolsets.actor.ActorTools | 17 | 8 | 9 | 0.018 |
| editor_toolset.toolsets.asset.AssetTools | 21 | 11 | 10 | 0.02 |
| editor_toolset.toolsets.blueprint.BlueprintTools | 53 | 22 | 31 | 0.028 |
| editor_toolset.toolsets.curve_table.CurveTableTools | 9 | 2 | 7 | 0.012 |
| editor_toolset.toolsets.data_asset.DataAssetTools | 1 | 0 | 1 | 0.013 |
| editor_toolset.toolsets.data_table.DataTableTools | 10 | 4 | 6 | 0.016 |
| editor_toolset.toolsets.material.MaterialTools | 22 | 8 | 14 | 0.017 |
| editor_toolset.toolsets.material_instance.MaterialInstanceTools | 13 | 5 | 8 | 0.014 |
| editor_toolset.toolsets.object.ObjectTools | 6 | 4 | 2 | 0.014 |
| editor_toolset.toolsets.primitive.PrimitiveTools | 4 | 0 | 4 | 0.014 |
| editor_toolset.toolsets.programmatic.ProgrammaticToolset | 2 | 1 | 1 | 0.013 |
| editor_toolset.toolsets.scene.SceneTools | 20 | 7 | 13 | 0.016 |
| editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools | 22 | 15 | 7 | 0.016 |
| editor_toolset.toolsets.static_mesh.StaticMeshTools | 16 | 8 | 8 | 0.015 |
| editor_toolset.toolsets.string_table.StringTableTools | 8 | 4 | 4 | 0.015 |
| editor_toolset.toolsets.texture.TextureTools | 2 | 1 | 1 | 0.017 |
| state_tree_toolset.toolsets.state_tree.StateTreeTools | 9 | 9 | 0 | 0.015 |

| probe | tool | ok | s | bytes | note |
|---|---|---|---|---|---|
| PIE state | IsPIERunning | True | 0.017 | 5 | false |
| viewport camera | GetCameraTransform | True | 0.014 | 210 | {"location": {"x": -2405.201087465768, "y": -26755.201087465 |
| frustum query | GetVisibleActors | True | 0.044 | 604200 | count=5887 |
| cvar search | SearchCVars | True | 0.023 | 235 | {"r.Shadow.DistanceScale":{"help":"Scalability option to tra |
| selection | GetSelectedActors | True | 0.01 | 2 | count=0 |
| open asset editors | GetOpenAssets | True | 0.014 | 2 | count=0 |
| log reading (tool picked from describe) | GetVerbosity | False | 0.021 | - | Log category 'LogsToolset' not found. |
| level path | get_current_level | True | 0.019 | 28 | /Game/Daedalus/DaedalusWorld |
| outliner folders | get_folders | True | 0.08 | 8333 | count=288 |
| tag query | find_actors | True | 0.066 | 10000 | count=100 |
| line trace at the hub | trace_world | True | 0.018 | 4 | null |
| asset listing (tool picked from describe) | get_plugin_content_paths | True | 0.028 | 42 | count=2 |
| class discovery (tool picked from describe) | None | - | - | - | no argument-free read-only tool |
| settings containers | ListContainers | True | 0.021 | 37 | count=3 |
| settings read-back | GetSectionPropertyValues | True | 0.027 | 39 | {"bThrottleCPUWhenNotForeground":false} |
| gameplay tags (tool picked from describe) | None | - | - | - | no argument-free read-only tool |
| automation test discovery | DiscoverTests | True | 0.389 | 19 | {"status": "ready"} |
| automation test list | ListTests | False | 0.014 | - | Function "ListTests", input params are required by the function input schema Json, but incoming function input params Json is empty.
Function schema Json -
{"type":"object","properties":{"nameFilter":{"type":"string","description":"Optional substring filter applied to the test's full path."},"tagFil |
| plugin listing (tool picked from describe) | ListEnabledPlugins | True | 0.021 | 5495 | count=279 |
| editor UI snapshot (tool picked from describe) | ListObservers | True | 0.017 | 100 | [{"identifier": "observer_1", "root": true, "rootRef": "", " |
| asset semantic search (tool picked from describe) | None | - | - | - | no argument-free read-only tool |
| static mesh inspection (tool picked from describe) | None | - | - | - | no argument-free read-only tool |
