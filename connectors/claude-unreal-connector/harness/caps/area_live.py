# SPDX-License-Identifier: MIT
# Live probes: need the open editor (a renderer, the viewport, selection, undo). Each restores what it touches.
# Run in the open editor: exec this source with progress/SKIP_EXTRA/ONLY in the namespace (see README).
import json, time, traceback, warnings
import unreal
warnings.simplefilter("ignore")

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
WORLD = UES.get_editor_world()
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
FOLDER = "ClaudeProbe"
D = "/Game/_ClaudeProbe/Live"
FAR = unreal.Vector(0, 0, -60000)
PROBES, MADE = [], []


def probe(fn):
    PROBES.append(fn)
    return fn


def spawn(cls, loc=FAR, rot=None):
    a = EAS.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0, 0, 0))
    a.set_folder_path(FOLDER)
    MADE.append(a)
    return a


@probe
def render_target_capture():
    rt = unreal.RenderingLibrary.create_render_target2d(WORLD, 64, 64, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cap = spawn(unreal.SceneCapture2D, FAR + unreal.Vector(-300, 0, 0))
    lamp = spawn(unreal.PointLight, FAR + unreal.Vector(-150, 0, 50))
    lamp.light_component.set_intensity(50000)
    cube = spawn(unreal.StaticMeshActor, FAR)
    cube.static_mesh_component.set_static_mesh(EAL.load_asset("/Engine/BasicShapes/Cube.Cube"))
    cc = cap.capture_component2d
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.capture_scene()
    px = unreal.RenderingLibrary.read_render_target_pixel(WORLD, rt, 32, 32)
    lit = (px.r + px.g + px.b) > 0
    return {"ok": lit, "center_pixel": [px.r, px.g, px.b, px.a]}


@probe
def text_render_sign():
    t = spawn(unreal.TextRenderActor)
    c = t.text_render
    c.set_text("DAEDALUS")
    c.set_world_size(80)
    c.set_text_render_color(unreal.Color(255, 80, 200, 255))
    back = str(c.get_editor_property("text"))
    return {"ok": back == "DAEDALUS" and abs(c.get_editor_property("world_size") - 80) < 1e-3, "text": back}


@probe
def niagara_actor():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Niagara", "NiagaraSystem")],
                          package_paths=["/Niagara", "/Engine"], recursive_paths=True)
    found = reg.get_assets(flt)
    if not found:
        return {"ok": False, "skipped": "no NiagaraSystem assets under /Niagara or /Engine"}
    sysasset = found[0].get_asset()
    n = spawn(unreal.NiagaraActor)
    comp = n.niagara_component
    comp.set_asset(sysasset)
    back = comp.get_asset()
    return {"ok": back is not None and back.get_path_name() == sysasset.get_path_name(), "systems_found": len(found),
            "used": sysasset.get_path_name()}


@probe
def lights_readback():
    out = {}
    for cls in (unreal.PointLight, unreal.SpotLight, unreal.RectLight):
        a = spawn(cls)
        lc = a.light_component
        lc.set_intensity(1234.0)
        lc.set_light_color(unreal.LinearColor(0.2, 0.4, 0.8, 1))
        out[cls.__name__] = round(lc.get_editor_property("intensity"), 1)
    return {"ok": all(abs(v - 1234.0) < 0.5 for v in out.values()), "intensity": out}


@probe
def cvar_set_restore():
    name = "r.ScreenPercentage"
    before = unreal.SystemLibrary.get_console_variable_float_value(name)
    unreal.SystemLibrary.execute_console_command(WORLD, "%s 73" % name)
    during = unreal.SystemLibrary.get_console_variable_float_value(name)
    unreal.SystemLibrary.execute_console_command(WORLD, "%s %s" % (name, before))
    after = unreal.SystemLibrary.get_console_variable_float_value(name)
    return {"ok": abs(during - 73) < 1e-3 and abs(after - before) < 1e-3, "before": before, "during": during, "after": after}


@probe
def viewport_camera_restore():
    loc, rot = UES.get_level_viewport_camera_info()
    UES.set_level_viewport_camera_info(loc + unreal.Vector(0, 0, 1000), rot)
    moved, _ = UES.get_level_viewport_camera_info()
    UES.set_level_viewport_camera_info(loc, rot)
    back, _ = UES.get_level_viewport_camera_info()
    return {"ok": abs(moved.z - loc.z - 1000) < 1 and abs(back.z - loc.z) < 1, "z": [loc.z, moved.z, back.z]}


@probe
def selection_restore():
    before = EAS.get_selected_level_actors()
    a = spawn(unreal.Note)
    EAS.set_selected_level_actors([a])
    sel = EAS.get_selected_level_actors()
    EAS.set_selected_level_actors(before)
    after = EAS.get_selected_level_actors()
    return {"ok": len(sel) == 1 and sel[0] == a and len(after) == len(before), "restored": len(after)}


@probe
def undo_move():
    a = spawn(unreal.Note)
    start = a.get_actor_location()
    with unreal.ScopedEditorTransaction("Claude probe move"):
        a.modify()
        a.set_actor_location(start + unreal.Vector(500, 0, 0), False, False)
    moved = a.get_actor_location()
    unreal.SystemLibrary.execute_console_command(WORLD, "TRANSACTION UNDO")
    undone = a.get_actor_location()
    return {"ok": abs(moved.x - start.x - 500) < 1 and abs(undone.x - start.x) < 1, "x": [start.x, moved.x, undone.x]}


@probe
def attach_duplicate_tags():
    p = spawn(unreal.Note)
    c = spawn(unreal.Note)
    c.attach_to_actor(p, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                      unreal.AttachmentRule.KEEP_WORLD, False)
    c.tags = ["claude", "probe"]
    d = EAS.duplicate_actor(c)
    if d:
        d.set_folder_path(FOLDER)
        MADE.append(d)
    return {"ok": c.get_attach_parent_actor() == p and "claude" in [str(t) for t in c.tags] and d is not None}


def _cleanup():
    n = 0
    for a in MADE:
        try:
            if a and EAS.destroy_actor(a):
                n += 1
        except Exception:
            pass
    for a in EAS.get_all_level_actors():
        if str(a.get_folder_path()) == FOLDER:
            EAS.destroy_actor(a)
            n += 1
    if EAL.does_directory_exist("/Game/_ClaudeProbe"):
        EAL.delete_directory("/Game/_ClaudeProbe")
    return n


ONLY = globals().get("ONLY")
result = {"probes": {}}
t_all = time.time()
for fn in PROBES:
    if ONLY and fn.__name__ not in ONLY:
        continue
    t0 = time.time()
    try:
        r = fn() or {}
    except Exception as e:
        r = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
    r["ms"] = int((time.time() - t0) * 1000)
    result["probes"][fn.__name__] = json.loads(json.dumps(r, default=repr))
result["cleaned"] = _cleanup()
result["passed"] = sum(1 for r in result["probes"].values() if r.get("ok"))
result["total"] = len(result["probes"])
result["secs"] = round(time.time() - t_all, 1)
