r"""youtube-master: diagnose + fix darkness on YTM_Island (next editor turn). Step 1 DIAG (read-only): every light /
sky / fog / post-process actor in the world with its level, plus the island ground + spawn. Step 2 FIX, scoped to
the YTM_Island sublevel only (tag YTM_Light, idempotent):
 - no DirectionalLight anywhere in the loaded world -> add sun (atmosphere sun, movable) + SkyLight (real-time capture)
   + SkyAtmosphere + ExponentialHeightFog to YTM_Island.
 - global sun already exists (persistent or another sublevel) -> do NOT add a 2nd sun/sky (they fight); add a
   bounded PostProcessVolume around the island (+2 EV) and a SkyLight only if none exists anywhere.
Never touches other levels. Saves YTM_Island only. Print-based so ue_send stdout shows it."""
import unreal
SUB = "/Game/YTM/Maps/YTM_Island"; TAG = "YTM_Light"; O = unreal.Vector(0, -2600000, 0)
act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
KINDS = ("DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud", "PostProcessVolume")
def lvl(a):
    try: return a.get_level().get_outer().get_name()
    except Exception: return "?"
found = {k: [] for k in KINDS}
for a in act.get_all_level_actors():
    c = a.get_class().get_name()
    for k in KINDS:
        if k in c and not a.actor_has_tag(TAG): found[k].append((a.get_actor_label(), lvl(a), a))
for k, v in found.items(): print("DIAG", k, len(v), [(n, l) for n, l, _ in v][:6])
for a in act.get_all_level_actors():
    if a.actor_has_tag("YTM_Spawn") or a.get_actor_label().startswith("YTM_Island_Base"):
        print("DIAG island", a.get_actor_label(), a.get_actor_location(), "hidden", a.is_hidden_ed(), lvl(a))
for n, l, a in found["DirectionalLight"]:
    lc = a.get_component_by_class(unreal.DirectionalLightComponent)
    print("DIAG sun", n, l, "intensity", lc.get_editor_property("intensity"), "rot", a.get_actor_rotation(), "atmos", lc.get_editor_property("atmosphere_sun_light"))
ls = unreal.GameplayStatics.get_streaming_level(world, "YTM_Island"); unreal.EditorLevelUtils.make_level_current(ls)
for a in act.get_all_level_actors():
    if a.actor_has_tag(TAG): act.destroy_actor(a)
def spawn(cls, loc, rot=unreal.Rotator(0, 0, 0), label=""):
    a = act.spawn_actor_from_class(cls, loc, rot); a.set_actor_label(label); a.tags = ["YTM_Island", TAG]; return a
added = []
# pythagoras #26445: darkness is world-wide since the 22:59 editor restart -> persistent-level owner should fix it.
# Default is DIAG ONLY when no sun exists; set ADD_SUN = True only if the team agrees the island may carry its own.
ADD_SUN = False
if not found["DirectionalLight"] and not ADD_SUN:
    print("YTM_LIGHT no DirectionalLight in loaded world -> world-level issue, NOT adding an island sun (see #26445)")
if not found["DirectionalLight"] and ADD_SUN:
    sun = spawn(unreal.DirectionalLight, O + unreal.Vector(0, 0, 3000), unreal.Rotator(roll=0, pitch=-40, yaw=135), "YTM_Sun")
    c = sun.get_component_by_class(unreal.DirectionalLightComponent); c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity", 8.0); c.set_editor_property("atmosphere_sun_light", True); added.append("sun")
    if not found["SkyAtmosphere"]: spawn(unreal.SkyAtmosphere, O, label="YTM_SkyAtmosphere"); added.append("atmosphere")
    if not found["ExponentialHeightFog"]:
        f = spawn(unreal.ExponentialHeightFog, O + unreal.Vector(0, 0, 200), label="YTM_HeightFog")
        f.get_component_by_class(unreal.ExponentialHeightFogComponent).set_editor_property("fog_density", 0.01); added.append("fog")
if not found["SkyLight"] and (found["DirectionalLight"] or ADD_SUN):
    s = spawn(unreal.SkyLight, O + unreal.Vector(0, 0, 2000), label="YTM_SkyLight")
    sc = s.get_component_by_class(unreal.SkyLightComponent); sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property("real_time_capture", True); added.append("skylight")
# global sun already present but island dark -> bounded post-process around the island, auto exposure +2 EV only
# oddsreaper #26482: world dark was the saved Sky Director storm state (sun 0 lux), now restored -> only add the
# PPV if the world sun is still near-zero at run time.
def _lux(a):
    try: return a.get_component_by_class(unreal.DirectionalLightComponent).get_editor_property("intensity")
    except Exception: return 0
if found["DirectionalLight"] and max(_lux(a) for _, _, a in found["DirectionalLight"]) < 0.5:
    pp = spawn(unreal.PostProcessVolume, O + unreal.Vector(0, 0, 2000), label="YTM_Exposure")
    pp.set_editor_property("unbound", False); pp.set_actor_scale3d(unreal.Vector(160, 160, 60))  # ~320x320x120 m
    st = pp.get_editor_property("settings")
    st.set_editor_property("override_auto_exposure_bias", True); st.set_editor_property("auto_exposure_bias", 2.0)
    pp.set_editor_property("settings", st); added.append("exposure_ppv")
print("YTM_LIGHT added", added)
unreal.EditorLoadingAndSavingUtils.save_current_level()
