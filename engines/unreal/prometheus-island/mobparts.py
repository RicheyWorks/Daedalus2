import unreal
EAL=unreal.EditorAssetLibrary; es=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MOB="/Game/Daedalus/Art/Mob/"
def parts(mob):
    base=MOB+"%s/%s/StaticMeshes/"%(mob,mob); ms=[]
    for p in EAL.list_assets(base,True,False):
        a=unreal.load_asset(p.split(".")[0])
        if isinstance(a,unreal.StaticMesh): ms.append(a)
    if not ms:
        for p in (MOB+"%s/%s"%(mob,mob),MOB+mob):
            a=unreal.load_asset(p)
            if isinstance(a,unreal.StaticMesh): ms=[a]; break
    ms.sort(key=lambda m:(0 if m.get_name() in (mob,mob+"_Body") else 1,m.get_name())); return ms
def spawn_mob(mob,loc,yaw,mat,label,tags):
    ms=parts(mob)
    if not ms: return 0
    root=None
    for m in ms:   # parts share one pivot (amf_pets_ue.py convention)
        a=es.spawn_actor_from_class(unreal.StaticMeshActor,loc,unreal.Rotator(0,0,yaw)); a.static_mesh_component.set_static_mesh(m)
        a.set_actor_label(label if root is None else label+"_"+m.get_name().split("_")[-1]); a.tags=[unreal.Name(t) for t in tags]
        if mat:
            for s in range(a.static_mesh_component.get_num_materials()): a.static_mesh_component.set_material(s,mat)
        if root is None: root=a
        else: a.attach_to_actor(root,"",unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    return len(ms)
