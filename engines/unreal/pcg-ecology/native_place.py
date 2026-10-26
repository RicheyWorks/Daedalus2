# SPDX-License-Identifier: MIT
"""Place the native-PCG ecology over the same patch the Python layout uses: stream + disturbance markers
(TargetPoints tagged PYTH_Stream / PYTH_Disturbance, traced to the ground) and a PCGVolume tagged PYTH_EcoNative
running PCG_EcologyNative. Patch geometry is read from the PYTH_Eco volume (live_pcg.py). Run via ue_send.py."""
import sys, math, unreal, importlib
HERE = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
sys.path.insert(0, HERE)
import ecology_rules as eco; importlib.reload(eco)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ew = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ref = [a for a in eas.get_all_level_actors() if a.actor_has_tag("PYTH_Eco")][0]
c = ref.get_actor_location(); D = (ref.get_actor_scale3d().x - 2) * 200; S = D / (eco.DOMAIN * 100)
ox, oy = c.x - D / 2, c.y - D / 2
for a in eas.get_all_level_actors():
    if any(a.actor_has_tag(t) for t in ("PYTH_Stream", "PYTH_Disturbance", "PYTH_EcoNative")): eas.destroy_actor(a)
def gz(x, y):
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(x, y, c.z + 30000), unreal.Vector(x, y, c.z - 60000),
            unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    return h.to_tuple()[4].z if h else None
marks = 0
for yy in range(0, 101, 4):
    x, y = ox + eco.stream_x(yy) * 100 * S, oy + yy * 100 * S
    z = gz(x, y)
    if z is None: continue
    m = eas.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(x, y, z)); m.tags = ["PYTH_Stream"]
    m.set_actor_label("PYTH_Stream_%02d" % yy); m.set_folder_path("Pythagoras/PCGEcology/Markers"); marks += 1
z0 = gz(ox, oy) or c.z
d = eas.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(ox, oy, z0)); d.tags = ["PYTH_Disturbance"]
d.set_actor_label("PYTH_Disturbance"); d.set_folder_path("Pythagoras/PCGEcology/Markers")
exec(open(HERE + r"\native_graph.py", encoding="utf-8-sig").read(), dict(globals(), PYTH_SCALE=S, PYTH_EXTENT_CM=D / 2, PYTH_VOLUME_SCALE=ref.get_actor_scale3d().x))
g = unreal.load_asset("/Game/Pythagoras/PCGEcology/PCG_EcologyNative")
vol = eas.spawn_actor_from_class(unreal.PCGVolume, c)
vol.set_actor_scale3d(ref.get_actor_scale3d()); vol.tags = ["PYTH_EcoNative"]; vol.set_actor_label("PYTH_PCG_EcologyNative")
vol.set_folder_path("Pythagoras/PCGEcology")
pc = vol.get_component_by_class(unreal.PCGComponent); pc.set_graph(g); pc.generate(True)
result = {"S": round(S, 3), "D_cm": round(D), "stream_markers": marks, "disturbance": [round(ox), round(oy), round(z0)]}
