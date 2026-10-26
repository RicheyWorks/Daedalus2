# disk-saver capture B: remove ONLY the temporary DS_TempCapture actors spawned by ds_capture_ue.py (never saved).
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tmp = [a for a in eas.get_all_level_actors() if "DS_TempCapture" in [str(t) for t in a.tags]]
result = {"removed": [a.get_actor_label() for a in tmp if a.get_actor_label().startswith("DS_TEMP_")]}
for a in tmp:
    if a.get_actor_label().startswith("DS_TEMP_"): eas.destroy_actor(a)
