import unreal
act=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
B={}
for x in act.get_all_level_actors():
    if not isinstance(x,unreal.StaticMeshActor): continue
    lv=x.get_level().get_outermost().get_name()
    o,e=x.get_actor_bounds(False)
    if e.x>200000 or e.y>200000: continue
    b=B.setdefault(lv,[1e12,1e12,-1e12,-1e12,0])
    b[0]=min(b[0],o.x-e.x);b[1]=min(b[1],o.y-e.y);b[2]=max(b[2],o.x+e.x);b[3]=max(b[3],o.y+e.y);b[4]+=1
for k,v in sorted(B.items()): print("BND",k,[round(z) for z in v])
