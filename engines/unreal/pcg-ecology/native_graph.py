# SPDX-License-Identifier: MIT
"""Build /Game/Pythagoras/PCGEcology/PCG_EcologyNative: the ecology as NATIVE PCG nodes, no precomputed points.

Per species (windows from ecology_rules.native_windows(sp, years)):
  Surface Sampler (landscape/ground under the volume, density ~ species cover)
    -> Normal To Density                      slope: density = up . normal
    -> Density Filter [min_up .. 1]           max slope (root anchoring)
    -> Distance to actors tagged 'PYTH_Stream'  -> Density Filter on distance band (moisture niche)
    -> Distance to actors tagged 'PYTH_Disturbance' -> Density Filter on band (seral stage at YEARS)
    -> Self Pruning (crown radius)            intraspecific competition
    -> Static Mesh Spawner (stand-in shape)
Years since disturbance is baked into the windows at build time (re-run with --years N to shift bands).
Runs inside the editor (bridge or -run=pythonscript). Each node is wrapped so one missing property is reported,
not fatal; the result lists what was set.
"""
import sys, json, unreal, importlib
HERE = r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology"
sys.path.insert(0, HERE)
import ecology_rules as eco; importlib.reload(eco)
YEARS = float(globals().get("PYTH_YEARS", eco.YEARS))
S = float(globals().get("PYTH_SCALE", 1.0))   # patch scale (0.35 on the DaedalusWorld island): distances and sizes shrink with it
ROOT, NAME = "/Game/Pythagoras/PCGEcology", "PCG_EcologyNative"
SH = {"Sphere": "/Engine/BasicShapes/Sphere.Sphere", "Cone": "/Engine/BasicShapes/Cone.Cone", "Cylinder": "/Engine/BasicShapes/Cylinder.Cylinder"}
log = []
def setp(obj, prop, val):
    try: obj.set_editor_property(prop, val); return True
    except Exception as e: log.append("%s.%s: %s" % (obj.get_class().get_name(), prop, str(e).split("\n")[0][:120])); return False

g = unreal.load_asset(ROOT + "/" + NAME)
if g:
    for n in list(g.get_editor_property("nodes")): g.remove_node(n)
else:
    g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, ROOT, unreal.PCGGraph, unreal.PCGGraphFactory())
out = g.get_output_node(); inp = g.get_input_node()
def node(cls):
    n, s = g.add_node_of_type(cls); return n, s
def pins(n, out):
    try: return [str(p.get_editor_property("properties").get_editor_property("label")) for p in n.get_editor_property("output_pins" if out else "input_pins")]
    except Exception: return []
def chain(*ns):
    for a, b in zip(ns, ns[1:]):
        o = next((p for p in pins(a, True) if str(p) in ("Out", "Source")), "Out")
        i = next((p for p in pins(b, False) if str(p) in ("In", "Source")), "In")
        if not g.add_edge(a, o, b, i): log.append("edge %s->%s failed (%s/%s) pins %s %s" % (a.get_name(), b.get_name(), o, i, pins(a, True), pins(b, False)))
def dfilter(lo, hi):
    n, s = node(unreal.PCGDensityFilterSettings)
    setp(s, "lower_bound", float(lo)); setp(s, "upper_bound", float(hi)); return n
def distance_to(tag, max_m):
    n, s = node(unreal.PCGDistanceSettings)
    setp(s, "set_density", True); setp(s, "maximum_distance", float(max_m * 100 * S))
    # target: actors with the tag, fed via Get Actor Data
    an, a = node(unreal.PCGDataFromActorSettings)
    sel = a.get_editor_property("actor_selector")
    setp(sel, "actor_selection", unreal.PCGActorSelection.BY_TAG); setp(sel, "actor_selection_tag", tag)
    setp(sel, "actor_filter", unreal.PCGActorFilter.ALL_WORLD_ACTORS)
    # markers are TargetPoints (no geometry): read each as one point, and take ALL tagged actors, not just the first
    setp(sel, "select_multiple", True)
    a.set_editor_property("actor_selector", sel)
    try: setp(a, "mode", unreal.PCGGetDataFromActorMode.GET_SINGLE_POINT)
    except Exception as e: log.append("mode: %s" % e)
    if not g.add_edge(an, "Out", n, "Target"): log.append("actor->distance failed: %s %s" % (pins(an, True), pins(n, False)))
    return n
made = {}
for sp in eco.SPECIES:
    w = eco.native_windows(sp, YEARS)
    # No landscape in DaedalusWorld (voxel islands): grid over the volume, then project onto a World Ray Hit
    # surface (rays cast straight down hit the chunk meshes' collision), which also gives real normals for slope.
    gn, gs = node(unreal.PCGCreatePointsGridSettings)
    sp_cm = max(25.0, sp["r"] * 100 * 1.2 * S)
    setp(gs, "cell_size", unreal.Vector(sp_cm, sp_cm, 100.0))
    setp(gs, "grid_extents", unreal.Vector(float(globals().get("PYTH_EXTENT_CM", 2000)), float(globals().get("PYTH_EXTENT_CM", 2000)), 50.0))
    try: setp(gs, "coordinate_space", unreal.PCGCoordinateSpace.LOCAL_COMPONENT)
    except Exception: pass
    rn, rs = node(unreal.PCGWorldRayHitSettings)
    sn, ss = node(unreal.PCGProjectionSettings)
    g.add_edge(gn, "Out", sn, "In")
    if not g.add_edge(rn, "Out", sn, "Projection Target"): log.append("rayhit->projection failed: %s" % pins(sn, False))
    nn, ns = node(unreal.PCGNormalToDensitySettings)
    slope = dfilter(w["min_up"], 1.0)
    smax = max(w["stream_m"][1], 1.0)
    d1 = distance_to("PYTH_Stream", min(smax * 1.01, 200))     # density = dist / max (0..1)
    m_f = dfilter(w["stream_m"][0] / (smax * 1.01) if smax < 200 else w["stream_m"][0] / 200, (w["stream_m"][1] / (smax * 1.01)) if smax < 200 else 1.0)
    dmax = 150.0
    d2 = distance_to("PYTH_Disturbance", dmax)
    s_f = dfilter(min(1, w["disturbance_m"][0] / dmax), min(1, w["disturbance_m"][1] / dmax))
    tn, ts = node(unreal.PCGTransformPointsSettings)   # size the 1 m stand-in shapes: crown diameter x height, sat on the ground
    d_, h_ = 2 * sp["r"] * S, sp["h"] * S
    setp(ts, "scale_min", unreal.Vector(d_ * 0.75, d_ * 0.75, h_ * 0.75)); setp(ts, "scale_max", unreal.Vector(d_ * 1.25, d_ * 1.25, h_ * 1.25))
    setp(ts, "uniform_scale", False); setp(ts, "rotation_max", unreal.Rotator(roll=0, pitch=0, yaw=360))
    setp(ts, "offset_min", unreal.Vector(0, 0, h_ * 50)); setp(ts, "offset_max", unreal.Vector(0, 0, h_ * 50))
    setp(ts, "absolute_rotation", True)
    pn, ps = node(unreal.PCGSelfPruningSettings)
    mn, ms = node(unreal.PCGStaticMeshSpawnerSettings)
    sel = ms.get_editor_property("mesh_selector_parameters")
    e = unreal.PCGMeshSelectorWeightedEntry(); d = e.get_editor_property("descriptor")
    d.set_editor_property("static_mesh", unreal.load_asset(SH[sp["shape"]])); e.set_editor_property("descriptor", d)
    sel.set_editor_property("mesh_entries", [e])
    chain(sn, nn, slope, d1, m_f, d2, s_f, tn, pn, mn)
    g.add_edge(mn, "Out", out, "Out")  # output node input pin is "Out"
    made[sp["name"]] = w
unreal.EditorAssetLibrary.save_loaded_asset(g)
result = {"graph": ROOT + "/" + NAME, "years": YEARS, "nodes": len(g.get_editor_property("nodes")), "windows": made, "warnings": log[:40]}
