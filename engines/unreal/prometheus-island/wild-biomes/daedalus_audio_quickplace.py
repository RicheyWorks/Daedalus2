# SPDX-License-Identifier: MIT
"""First playable: import an rd-studio render + a CC0 rain bed and place a jukebox cabinet with an HRTF emitter and a
rain ambience zone in front of the viewport camera. Editor only (not during Play-In-Editor). Re-running replaces DA_* actors.
WAVs: C:/Users/730ri/projects/bot-team/art/audio/{DA_Jukebox_e00015.wav, DA_Bed_Rain.wav}."""
import unreal
D = "C:/Users/730ri/projects/bot-team/art/audio/"
ue = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_game_world(): raise RuntimeError("Play-In-Editor is running; stop it first (assets can't import during PIE)")
tasks = []
for f, n in (("DA_Jukebox_e00015.wav", "SW_Jukebox_e00015"), ("DA_Bed_Rain.wav", "SW_Bed_Rain")):
    t = unreal.AssetImportTask(); t.filename = D + f; t.destination_path = "/Game/DaedalusAudio"; t.destination_name = n
    t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
jw = unreal.load_asset("/Game/DaedalusAudio/SW_Jukebox_e00015"); rw = unreal.load_asset("/Game/DaedalusAudio/SW_Bed_Rain")
for w in (jw, rw): w.set_editor_property("looping", True); unreal.EditorAssetLibrary.save_loaded_asset(w)
es = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in es.get_all_level_actors():
    if a.get_actor_label().startswith("DA_"): es.destroy_actor(a)
cam, rot = ue.get_level_viewport_camera_info()
at = cam + rot.get_forward_vector() * 600
box = es.spawn_actor_from_class(unreal.StaticMeshActor, at); box.set_actor_label("DA_JukeboxCabinet")
box.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube")); box.set_actor_scale3d(unreal.Vector(1, 0.6, 1.8))
j = es.spawn_actor_from_class(unreal.AmbientSound, at + unreal.Vector(0, 0, 120)); j.set_actor_label("DA_JukeboxEmitter_e00015")
ac = j.get_component_by_class(unreal.AudioComponent); ac.set_sound(jw); ac.set_editor_property("override_attenuation", True)
s = ac.get_editor_property("attenuation_overrides")
s.set_editor_property("spatialize", True); s.set_editor_property("spatialization_algorithm", unreal.SoundSpatializationAlgorithm.SPATIALIZATION_HRTF)
s.set_editor_property("falloff_distance", 3000.0); s.set_editor_property("attenuate_with_lpf", True); s.set_editor_property("enable_reverb_send", True)
ac.set_editor_property("attenuation_overrides", s)
r = es.spawn_actor_from_class(unreal.AmbientSound, at); r.set_actor_label("DA_BiomeAmbience_Rain")
rc = r.get_component_by_class(unreal.AudioComponent); rc.set_sound(rw)
rc.set_editor_property("allow_spatialization", False); rc.set_editor_property("volume_multiplier", 0.35)
ac.play(); rc.play()
print("DA placed at", at)
unreal.EditorAssetLibrary.save_directory("/Game/DaedalusAudio", only_if_is_dirty=False, recursive=True)
unreal.EditorLevelLibrary.save_current_level()
print("saved", [unreal.EditorAssetLibrary.does_asset_exist(p) for p in ("/Game/DaedalusAudio/SW_Jukebox_e00015","/Game/DaedalusAudio/SW_Bed_Rain")])
