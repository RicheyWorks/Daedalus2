# SPDX-License-Identifier: MIT
"""Hero framing (our turn only): point the level viewport at Island_Pythagoras from the south-east at ~35 deg down,
and report the light check so the screenshot is taken only if the world is lit. Changes only the editor camera."""
import unreal, math
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
C = unreal.Vector(-60000, 60000, 2500); D = 15000.0; pitch = -35.0; yaw = 135.0
cam = C + unreal.Vector(-D * math.cos(math.radians(pitch)) * math.cos(math.radians(yaw)),
                        -D * math.cos(math.radians(pitch)) * math.sin(math.radians(yaw)), -D * math.sin(math.radians(pitch)))
ues.set_level_viewport_camera_info(cam, unreal.Rotator(roll=0, pitch=pitch, yaw=yaw))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
suns = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.DirectionalLight) and a.light_component.get_editor_property("visible")]
skies = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyLight)]
result = {"camera": [round(cam.x), round(cam.y), round(cam.z)], "suns": [(s.get_actor_label(), round(s.get_actor_rotation().pitch, 1), s.light_component.get_editor_property("intensity")) for s in suns],
          "skylights": len(skies), "lit": bool(suns) and any(s.get_actor_rotation().pitch < -5 for s in suns)}
