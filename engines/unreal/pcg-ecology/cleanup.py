import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
r={}
for v in [a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_Eco") or a.actor_has_tag("PYTH_EcoNative")]:
    pc=v.get_component_by_class(unreal.PCGComponent)
    try: pc.cleanup(True, False)
    except Exception as e:
        try: pc.cleanup(True)
        except Exception as e2: r["err"]=str(e2)[:200]
    # belt and braces: remove the generated instanced components directly
    k=0
    for c in v.get_components_by_class(unreal.InstancedStaticMeshComponent):
        c.clear_instances(); k+=1
    r[v.get_actor_label()]=k
result=r
