# SPDX-License-Identifier: MIT
"""READ-ONLY lighting audit (run on our editor turn only): lists every light / sky / fog / post-process / exposure actor in the
loaded world with its level, owner folder, visibility, intensity, rotation and exposure settings. Changes nothing."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
KINDS = (unreal.DirectionalLight, unreal.SkyLight, unreal.ExponentialHeightFog, unreal.PostProcessVolume, unreal.SkyAtmosphere, unreal.VolumetricCloud)
def gp(o, n, d=None):
    try: return o.get_editor_property(n)
    except Exception: return d
out = []
for a in eas.get_all_level_actors():
    if not isinstance(a, KINDS): continue
    e = {"label": a.get_actor_label(), "class": a.get_class().get_name(), "level": a.get_level().get_outer().get_name(),
         "folder": str(a.get_folder_path()), "hidden_editor": a.is_hidden_ed(), "hidden_game": a.hidden}
    if isinstance(a, unreal.DirectionalLight):
        c = a.light_component; r = a.get_actor_rotation()
        e.update(intensity=gp(c, "intensity"), visible=gp(c, "visible"), pitch=round(r.pitch, 1), yaw=round(r.yaw, 1), atmosphere_sun=gp(c, "atmosphere_sun_light"))
    elif isinstance(a, unreal.SkyLight):
        c = a.light_component; e.update(intensity=gp(c, "intensity"), visible=gp(c, "visible"), real_time=gp(c, "real_time_capture"), source=str(gp(c, "source_type")))
    elif isinstance(a, unreal.PostProcessVolume):
        s = gp(a, "settings"); e.update(unbound=gp(a, "unbound"), enabled=gp(a, "enabled"), priority=gp(a, "priority"),
            exp_method=str(gp(s, "auto_exposure_method")) if s else None, exp_bias=gp(s, "auto_exposure_bias") if s else None,
            override_bias=gp(s, "override_auto_exposure_bias") if s else None, min_ev=gp(s, "auto_exposure_min_brightness") if s else None, max_ev=gp(s, "auto_exposure_max_brightness") if s else None)
    out.append(e)
vp = None
try: vp = str(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).get_current_level().get_outer().get_name())
except Exception: pass
result = {"count": len(out), "current_level": vp, "actors": out}
