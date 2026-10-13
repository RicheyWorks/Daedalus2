# disk-saver batched canopy re-import: ONE batch (<=8 meshes) per bridge call, resumable via progress file.
# Driver: run_canopy.py. Our sublevel/folder only (/Game/DiskSaver/Art), overwrite-reimport, no deletes.
import unreal, os, json, time
D = r"C:\Users\730ri\projects\bot-team\art\NOTES\disksaver"; GLB = D + r"\glb"
TODO = D + r"\canopy_todo.json"; PROG = D + r"\canopy_progress.json"; TAG = "DS_Island"; BATCH = 8
eal = unreal.EditorAssetLibrary; eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {"imported": [], "swapped": 0, "notes": []}
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor(): raise SystemExit("PIE running")
ROOTS = ("/Game/DiskSaver/Art/", "/Game/Daedalus/Art/")
def asset_of(a):
    try: c = a.static_mesh_component; p = c.static_mesh.get_path_name()
    except Exception: return None
    for r in ROOTS:
        if p.startswith(r):
            s = p.split("/"); return s[5] if len(s) > 5 else None
    return None
mine = [a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
byname = {}
for a in mine:
    n = asset_of(a)
    if n and "_DS_" in n: byname.setdefault(n, []).append(a)
if not os.path.exists(TODO):
    json.dump(sorted(byname), open(TODO, "w"))
todo = json.load(open(TODO)); done = json.load(open(PROG)) if os.path.exists(PROG) else []
batch = [n for n in todo if n not in done][:BATCH]
def own_mesh(n):
    d = "/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n); p = d + "/" + n
    if eal.does_asset_exist(p): return unreal.load_asset(p)
    for q in (eal.list_assets(d, True, False) if eal.does_directory_exist(d) else []):
        if q.split("/")[-1].split(".")[0] == n:
            x = unreal.load_asset(q)
            if isinstance(x, unreal.StaticMesh): return x
    return None
tasks = []
for n in batch:
    f = os.path.join(GLB, n + ".glb")
    if not os.path.exists(f): out["notes"].append("no glb " + n); continue
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = "/Game/DiskSaver/Art/%s/%s" % (n.split("_")[0], n)
    t.destination_name = n; t.automated = True; t.save = True; t.replace_existing = True; tasks.append(t)
if tasks: unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
leaf = unreal.load_asset("/Game/DiskSaver/Materials/MI_DS_Leaf") if eal.does_asset_exist("/Game/DiskSaver/Materials/MI_DS_Leaf") else None
for n in batch:
    m = own_mesh(n)
    if m is None: out["notes"].append("no single mesh " + n); done.append(n); continue
    for a in byname.get(n, []):
        c = a.static_mesh_component
        if c.static_mesh != m: c.set_static_mesh(m); out["swapped"] += 1
        if a.get_actor_label().startswith("Cube"): a.set_actor_label(n)
        if leaf and "_DS_Tree_" in n:
            for i, mt in enumerate(c.get_materials()):
                if mt and "leaf" in mt.get_name().lower(): c.set_material(i, leaf)
    done.append(n); out["imported"].append(n)
json.dump(done, open(PROG, "w"))
out["remaining"] = len([n for n in todo if n not in done]); out["total"] = len(todo)
result = out
