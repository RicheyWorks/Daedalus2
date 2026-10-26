import unreal
eas=unreal.EditorAssetLibrary; act=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
out=[]
for n in ["YoungMeadow","BrambleScrub","PineStand","OldGrowthOak","WillowRiverbank","Master"]:
    s=eas.load_asset(f"/Game/YTM/Seq/WB_Flythrough_{n}")
    if not s: out.append(n+":MISSING"); continue
    b=s.get_spawnables(); cut=s.find_tracks_by_type(unreal.MovieSceneCameraCutTrack)
    keys=0
    for sp in b:
        for t in sp.get_tracks():
            for sec in t.get_sections():
                for ch in sec.get_all_channels():
                    try: keys+=len(ch.get_keys())
                    except Exception: pass
    out.append(f"{n}: cams={len(b)} cuts={len(cut[0].get_sections()) if cut else 0} keys={keys} end={s.get_playback_end()}")
labels=[a.get_actor_label() for a in act.get_all_level_actors() if a.get_actor_label().startswith("WB_Label_")]
print("; ".join(out)); print("labels",labels); print("play",les.is_in_play_in_editor())
