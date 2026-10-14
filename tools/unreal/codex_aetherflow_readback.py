# SPDX-License-Identifier: MIT
"""Read the two saved Aetherflow plants against the completed 87-actor baseline.

Only the acknowledged operator runs this after the final world save. Native
operations read state only: 89 actors, 85 saved StaticMesh files, five owned PBR
instances and their base. Glasskelp remains a saved asset with zero world refs.
No import, placement, material mutation, save, screenshot, test or queue probe.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from codex_admitted_asset_assembly import AETHERFLOW_CONFIGS, plan_admitted
from codex_editor_handoff import (
    APP, DEST, MAP, MAP_FILE, Mcp, NATIVE_READ, SCENE, _asset_file, _file,
    _same_transform, _witness, fingerprint, package, wire,
)
from codex_saved_asset_assembly import _read, _write

BASELINE = "codex-aetherflow-before.native.json"
BASELINE_FP = {"sha256": "3eed9e8d3ac04cd4e6b4404a7dc192b0e2a4d328b24d5b2eb952d24732364cf5", "bytes": 5765486}
BASELINE_MAP = {"sha256": "a32fd910fb3a29ce89b09590cdfd8fa18ab4cc91d08a31b06538cd7280f1db18", "bytes": 209300262}
INPUTS_FP = {"sha256": "af2a7a3533c3fa1b6ad425a189b07047c35bbc9e23289d49b45c12f6ab689234", "bytes": 16456}
PREPARED_FP = {"sha256": "493b44d5ca482e454e2312d3c2c7e44d776913d04b40fae5d9a17df69ab332d0", "bytes": 36483}
REVISION = "AetherflowR2"
KINDS = ("ribbon_reeds", "star_lilies", "glasskelp")
NAMES = tuple("CodexAetherflow_" + kind + "_617024" for kind in KINDS)
PLACED = NAMES[:2]
KELP = NAMES[2]
SOURCE_COMMIT = "44f0b1583162aeeebd6f4784b539022c0760c193"
SOURCE_GLB = {
    "ribbon_reeds": {"sha256": "3124f31b2889f9610b79cdd582a03fdc40a13fc919ebcfb70d2065a966fa0695", "bytes": 62472},
    "star_lilies": {"sha256": "0cfa8be1dc9fc71f9efce89601b3d7e6a4286735bea55532f4fec24c23ffa209", "bytes": 62204},
    "glasskelp": {"sha256": "97b6af850c377fb6b76b1499b6ceecd1091cd9244f03f7141242c4699ea6bf86", "bytes": 91780},
}
SOURCE_REVIEW = {
    "Delivery_Receipt.json": {"sha256": "13ca2e81f94a28228ee430146ddd54dd70bae9797c9f584b28024c5ad15ba142", "bytes": 12741},
    "../Aetherflow_Package_Receipt.json": {"sha256": "47da61d38deccaf8ed84e1f077d11b131b6730426372b7e7629cd0a8672390c4", "bytes": 9940},
    "Aetherflow_Aquatic_Life.png": {"sha256": "1400c668cb065316a58ac7c91f9a5249297f3104802483c6f800654b1128551c", "bytes": 1670458},
    "Aetherflow_Nursery_detail.png": {"sha256": "437ad2d53b6932bc4ed6ff42d75ee4bd51bb4e6f33fd7fdb49a1b776fec2c052", "bytes": 1907798},
    "Aetherflow_Reach_day.png": {"sha256": "c29db29874d275b4b717665fe8fc13164cbb3f3d2d8779eff9774e1f266f4d8d", "bytes": 2022426},
    "Aetherflow_Reach_dusk.png": {"sha256": "c93623e93a9eca107bfcfbe75a1b28f6f84e302edc7c012f4ddc5f18d865d1dc", "bytes": 1955744},
    "Aetherflow_Willowdrift_player.png": {"sha256": "b535bf1366c795a5534cf740b019fa213808d0b5cc4e882e3e1ad82f95aba411", "bytes": 1568013},
}
PALETTE_ROOT = DEST + "/Aetherflow/Palette"
BASE_MATERIAL = PALETTE_ROOT + "/M_Aetherflow_Clearcoat_v1.M_Aetherflow_Clearcoat_v1"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _close(actual, expected):
    return type(actual) in (int, float) and math.isfinite(actual) and abs(actual - expected) <= 1e-5


def _pbr_same(actual, expected, alpha=False):
    rgb = actual.get("linear_rgb", [])
    return (len(rgb) == 3 and all(_close(a, b) for a, b in zip(rgb, expected["linear_rgb"])) and
            all(_close(actual.get(key), expected[key]) for key in ("roughness", "metallic", "clearcoat", "clearcoat_roughness")) and
            (not alpha or _close(actual.get("alpha"), 1.0)))


def _local(folder, *, before_first_save=False):
    evidence, protected = {}, {}

    def protect(path, expected=None):
        actual = _file(path)
        if expected is not None and _witness(actual) != _witness(expected):
            raise ValueError("protected witness differs: " + str(path))
        if actual["path"] in protected and _witness(protected[actual["path"]]) != _witness(actual):
            raise ValueError("production input changed while collecting: " + actual["path"])
        protected[actual["path"]] = actual
        return actual

    def retain(relative, expected=None):
        path = (folder / relative).resolve()
        value, witness = _read(path)
        if expected is not None and witness != _witness(expected):
            raise ValueError("receipt witness differs: " + str(path))
        file = protect(path, witness)
        evidence[str(relative)] = {"file": file, "receipt": value}
        return value

    baseline = retain(BASELINE, BASELINE_FP)
    if (baseline.get("schema") != "daedalus.codex-power-unit-production-readback.v1" or
        baseline.get("stage") != "power_unit_production_readback_completed" or baseline.get("issues") != [] or
        baseline.get("measured_actor_rows") != 87 or baseline.get("verified_saved_mesh_files") != 82 or
        _witness(baseline["map_after_readback"]) != BASELINE_MAP):
        raise ValueError("require exact clean completed87-actor/82-mesh baseline")
    prior = baseline["native_readback"]
    old_rows, disk = baseline["local"]["actors"], dict(baseline["local"]["disk_static_meshes"])
    old = {row["label"]: row for row in prior["actors"]}
    if (len(old_rows) != 87 or len(old) != 87 or len(prior["actors"]) != 87 or
        {row["label"] for row in old_rows} != set(old) or len(disk) != 82 or
        set(prior["saved_asset_classes"]) != set(disk)):
        raise ValueError("baseline actor/file sets differ")
    if (prior["dirty_map_packages"] or prior["dirty_content_packages"] or
        prior["hero_r2_actor_labels"] or prior["hero_r2_mesh_references"] or
        len(prior["power_unit_actor_references"]) != 5):
        raise ValueError("baseline dirty/held-asset/PowerUnit state differs")
    for path, witness in baseline["local"]["protected_files"].items():
        protect(path, witness)
    for path, witness in disk.items():
        protect(_asset_file(path), witness)
    inputs = retain(REVISION + "/native-inputs.json", INPUTS_FP)
    prepared = retain(REVISION + "/codex-aetherflow.delivery.json", PREPARED_FP)
    batch = retain(REVISION + "/Aetherflow_Dropin_Receipt.json", inputs["source_batch_fingerprint"])
    saved = retain(REVISION + "/native-saved.json")
    world = retain(REVISION + "/world.json")
    palette = retain(REVISION + "/materials.json")
    if before_first_save:
        actions = world.get("native_mutations", [])
        if (world.get("stage") != "inspection_required" or world.get("created_actors") != 2 or
            world.get("save_return") is not None or world.get("saved_unreal") is not False or
            len(actions) != 5 or any(row.get("state") != "responded" for row in actions) or
            [row.get("tool") for row in actions] != ["add_to_scene_from_asset", "set_actor_folder",
                "add_to_scene_from_asset", "set_actor_folder", "execute_python component overrides"] or
            actions[-1]["result"].get("error") or
            "expected a JSON object" not in world.get("error", "")):
            raise ValueError("require the exact known responded parser failure before any save")
        world["applied_component_overrides"] = actions[-1]["result"].get("result")
    if (inputs.get("schema") != "daedalus.codex-aetherflow-native-inputs.v1" or
        inputs.get("stage") != "three_source_dropins_prepared" or set(inputs["candidates"]) != set(NAMES) or
        Path(inputs["prepared_manifest"]).resolve() != (folder / REVISION / "codex-aetherflow.delivery.json").resolve() or
        inputs["prepared_manifest_fingerprint"] != PREPARED_FP or
        Path(inputs["source_batch"]).resolve() != (folder / REVISION / "Aetherflow_Dropin_Receipt.json").resolve()):
        raise ValueError("exact prepared three-plant inputs differ")
    if (batch.get("stage") != "three_retained_fbx_exported" or batch.get("original_payloads_unchanged") is not True or
        batch.get("seed") != 617024 or batch.get("source_commit") != SOURCE_COMMIT or
        [row["name"] for row in batch["artifacts"]] != list(NAMES)):
        raise ValueError("require completed retained unchanged-source conversion")
    protect(batch["converter_source"]["path"], batch["converter_source"])
    expected_source = dict(SOURCE_REVIEW)
    expected_source.update({"modules/Life_" + kind + ".glb": SOURCE_GLB[kind] for kind in KINDS})
    if set(batch["source_witnesses"]) != set(expected_source):
        raise ValueError("Sol source/review witness set differs")
    for relative, expected in expected_source.items():
        recorded = batch["source_witnesses"][relative]
        if _witness(recorded) != expected:
            raise ValueError("Sol source/review fingerprint differs: " + relative)
        protect(recorded["path"], expected)
    if saved.get("stage") != "three_assets_saved" or _witness(saved["map_after"]) != BASELINE_MAP:
        raise ValueError("three asset saves lack their unchanged pre-placement map")
    saved_rows = {row["name"]: row for row in saved["receipts"]}
    if len(saved["receipts"]) != 3 or set(saved_rows) != set(NAMES):
        raise ValueError("saved admission identity set differs")
    if ((not before_first_save and (world.get("stage") != "placed_and_saved" or world.get("save_return") is not True or
        world.get("saved_unreal") is not True)) or world.get("staging_only") is not True or
        world.get("ownership_tags_added") is not False):
        raise ValueError("require confirmed saved two-plant staging world")
    assembly = world["plan"]
    if (assembly.get("schema") != "daedalus.codex-aetherflow-assembly.v1" or
        set(assembly["placements_cm"]) != set(PLACED) or set(assembly["source_admissions"]) != set(NAMES)):
        raise ValueError("world assembly must admit three but place only reeds and lilies")
    plans, sources, expected_pbr, new_paths = {}, {}, {}, {}
    source_slots = {}
    prepared_by_name = {row["name"]: row for row in prepared["assets"]}
    batch_by_name = {row["name"]: row for row in batch["artifacts"]}
    for name, kind in zip(NAMES, KINDS):
        candidate = inputs["candidates"][name]
        config = candidate["config"]
        if (candidate["config_sha256"] != AETHERFLOW_CONFIGS[name] or _digest(config) != AETHERFLOW_CONFIGS[name] or
            config.get("seed") != 617024 or config.get("plant") != kind or config.get("source_author") != "SolUltra" or
            config.get("source_commit") != SOURCE_COMMIT or config.get("source_glb") != SOURCE_GLB[kind] or
            config.get("waterline_local_z") != 0.0 or config.get("converter") != _witness(batch["converter_source"])):
            raise ValueError("source config identity differs: " + name)
        source_path = folder / REVISION / (name + ".receipt.json")
        if Path(candidate["source_receipt"]).resolve() != source_path.resolve():
            raise ValueError("source receipt leaves exact retained revision")
        source = retain(REVISION + "/" + name + ".receipt.json", candidate["source_receipt_fingerprint"])
        sources[name] = source
        if (source.get("schema") != "daedalus.codex-aetherflow-dropin.v1" or source.get("converter_revision") != 2 or
            source.get("stage") != "retained_fbx_exported" or source.get("name") != name or source.get("seed") != 617024 or
            source.get("source_commit") != SOURCE_COMMIT or source.get("source_witnesses") != batch["source_witnesses"] or
            source["source_gltf_contract"]["materials_linear_gltf"] != config["materials_linear_gltf"] or
            source["source_root_extras"] != source["source_gltf_contract"]["root_extras"] or
            source["source_root_extras"].get("waterline_local_z") != 0.0 or source["source_root_extras"].get("seed") != 617024 or
            source.get("original_payloads_unchanged") is not True):
            raise ValueError("retained conversion provenance differs: " + name)
        preservation = source["preservation"]
        if (preservation.get("geometry_and_materials_preserved") is not True or preservation.get("exact_oriented_faces_aligned") is not True or
            any(preservation.get(field) != 0 for field in ("maximum_position_error_metres", "maximum_corner_normal_component_error", "maximum_corner_normal_angular_error_degrees"))):
            raise ValueError("require actual zero-error R2 conversion witness")
        for field in ("receipt", "fbx"):
            record = batch_by_name[name][field]
            protect(record["path"], record)
        protect(source["artifacts"]["fbx"]["path"], source["artifacts"]["fbx"]["fingerprint"])
        if (candidate["entry"] != prepared_by_name[name] or
            _witness(candidate["entry"]["fbx"]) != _witness(source["artifacts"]["fbx"]["fingerprint"])):
            raise ValueError("prepared entry differs from retained source")
        source_slots[name] = source["after_merge"]["material_slots"]
        if candidate["entry"]["objects"] != [{"name": name, "dims": source["after_merge"]["dimensions_metres"],
                                               "triangles": source["after_merge"]["triangles"], "materials": source_slots[name]}]:
            raise ValueError("prepared mesh dimensions/triangles/material slots differ")
        for material in config["materials_linear_gltf"]:
            pbr, coat = material["pbrMetallicRoughness"], material["extensions"]["KHR_materials_clearcoat"]
            slot = material["name"]
            value = {"linear_rgb": pbr["baseColorFactor"][:3], "metallic": pbr["metallicFactor"], "roughness": pbr["roughnessFactor"],
                     "clearcoat": coat["clearcoatFactor"], "clearcoat_roughness": coat.get("clearcoatRoughnessFactor", 0.0)}
            if slot in expected_pbr and expected_pbr[slot] != value:
                raise ValueError("shared source PBR values disagree")
            expected_pbr[slot] = value
        admitted = saved_rows[name]
        receipt_path = Path(admitted["receipt"]).resolve()
        if receipt_path.parent != (folder / REVISION / "NativeReceipts").resolve():
            raise ValueError("saved receipt leaves exact retained revision")
        admission = retain(receipt_path, admitted["fingerprint"])
        placement = assembly["placements_cm"][name] if name in PLACED else [0, 0, 0]
        plan = plan_admitted(receipt_path, placement, MAP, MAP_FILE)
        plans[name] = plan
        if (len(plan["entries"]) != 1 or plan["entries"][0]["label"] != name or
            plan["source_fingerprint"] != _witness(source["artifacts"]["fbx"]["fingerprint"]) or
            plan["config_sha256"] != candidate["config_sha256"] or admitted["assets"] != admission["assets"]):
            raise ValueError("canonical saved admission differs from retained source")
        record = assembly["source_admissions"][name]
        if (Path(record["receipt"]).resolve() != receipt_path or record["fingerprint"] != admitted["fingerprint"] or
            record["canonical_plan"] != plan):
            raise ValueError("world source-admission plan differs: " + name)
        for path, witness in admission["manifest"]["dependencies"].items():
            protect(path, witness)
        for path, witness in plan["native_output_fingerprints"].items():
            if path in disk:
                raise ValueError("new Aetherflow output overlaps baseline meshes")
            disk[path] = witness
            protect(_asset_file(path), witness)
            new_paths[name] = path
    expected_entries = [plans[name]["entries"][0] for name in PLACED]
    expected_outputs = {path: witness for plan in plans.values() for path, witness in plan["native_output_fingerprints"].items()}
    if (assembly["entries"] != expected_entries or assembly["native_output_fingerprints"] != expected_outputs or
        len(disk) != 85 or len(set(new_paths.values())) != 3):
        raise ValueError("world entry/output sets differ from exact two actors and three assets")
    actors = world["actors"]
    by_label = {row["label"]: row for row in actors}
    if len(actors) != 2 or set(by_label) != set(PLACED):
        raise ValueError("require exactly two saved Aetherflow actors")
    for entry in expected_entries:
        row = by_label[entry["label"]]
        if (row["mesh_path"] != entry["mesh_path"] or row.get("group") != entry["group"] or
            not _same_transform(row["transform"], entry["transform"]) or package(row["actor"]) != MAP):
            raise ValueError("saved actor mapping differs from canonical plan")
    if (palette.get("stage") != "owned_materials_saved" or palette.get("palette_profile") != "aetherflow_linear_pbr_v1" or
        palette.get("map_unchanged") is not True or set(palette["materials"]) != set(expected_pbr) or
        palette["source_settings"] != {slot.removeprefix("SW_Life_"): settings for slot, settings in expected_pbr.items()}):
        raise ValueError("require exact five saved linear-source PBR instances")
    palette_source = Path(__file__).resolve().parents[2] / "engines/unreal/DaedalusLink/Content/Python/daedalus_codex_staging_palette.py"
    palette_source_file = protect(palette_source)
    if palette_source_file["sha256"] != palette["source_sha256"]:
        raise ValueError("owned PBR source differs from its native execution witness")
    material_paths = {slot: row["refPath"] for slot, row in palette["materials"].items()}
    if len(set(material_paths.values())) != 5 or any(not package(path).startswith(PALETTE_ROOT + "/MI_Aetherflow_") for path in material_paths.values()):
        raise ValueError("palette instances leave exact owned material namespace")
    saves = [row for row in palette["palette_mutations"] if row["action"] in ("save_base", "reuse_clean_base", "save_instance", "reuse_clean_instance")]
    if len(saves) != 6 or any(row.get("state") != "responded" or row.get("save_return") is not True for row in saves):
        raise ValueError("palette lacks all six confirmed material saves")
    base = [row for row in saves if package(row["target"]) == package(BASE_MATERIAL)]
    if (len(base) != 1 or base[0].get("two_sided") is not True or base[0].get("use_material_attributes") is not True or
        "MSM_CLEAR_COAT" not in base[0].get("shading_model", "")):
        raise ValueError("owned base clearcoat/two-sided/material-attributes readback differs")
    for row in saves:
        protect(_asset_file(row["target"]), row["disk"])
    for slot, path in material_paths.items():
        rows = [row for row in saves if package(row["target"]) == package(path)]
        if len(rows) != 1 or not _pbr_same(rows[0], expected_pbr[slot]):
            raise ValueError("saved material PBR readback differs: " + slot)
    overrides = assembly["component_overrides"]
    applied = {row["label"]: row for row in world["applied_component_overrides"]}
    if set(overrides) != set(PLACED) or len(world["applied_component_overrides"]) != 2 or set(applied) != set(PLACED):
        raise ValueError("component overrides must cover exactly the two placed plants")
    desired = {}
    for name in PLACED:
        slots = applied[name]["slots"]
        if (len(slots) != len(source_slots[name]) or set(slots) != set(source_slots[name]) or
            overrides[name] != {slot: material_paths[slot] for slot in source_slots[name]}):
            raise ValueError("source/native component slot mapping differs")
        desired[name] = [material_paths[slot] for slot in slots]
        if applied[name]["materials"] != desired[name]:
            raise ValueError("applied native material order differs")
    all_rows = old_rows + actors
    if (len(all_rows) != 89 or len({row["label"] for row in all_rows}) != 89 or
        len({row["actor"]["refPath"] for row in all_rows}) != 89):
        raise ValueError("require87 distinct prior actors plus two new actors")
    for path, witness in protected.items():
        if fingerprint(path) != _witness(witness):
            raise ValueError("protected input changed during local collection: " + path)
    return {"baseline_input": evidence[BASELINE]["file"], "prior_native": prior, "actors": all_rows,
            "new_actors": actors, "new_paths": new_paths, "new_component_materials": desired,
            "new_component_slots": {name: applied[name]["slots"] for name in PLACED},
            "source_slots": source_slots, "power_paths": baseline["local"]["power_paths"],
            "disk_static_meshes": disk, "protected_files": protected, "evidence": evidence,
            "material_paths": material_paths, "expected_pbr": expected_pbr,
            "base_material_readback": {key: base[0][key] for key in ("two_sided", "use_material_attributes", "shading_model")},
            "expected_latest_saved_map": _witness(world["map_before"] if before_first_save else world["map_after"]),
            "folder": world["folder"]}


def _native_code(local):
    code = NATIVE_READ.replace("hero2_labels=[]", "hero2_labels=[]\nhero2_mesh_references=[]\nplant_references=[]\nplant_paths=set(PLANT_PATHS)")
    code = code.replace("observed=[]", "    if mesh and 'CodexIsland_summit_rim_84011_HeroR2' in mesh.get_path_name():\n        hero2_mesh_references.append({'actor':actor.get_path_name(),'label':label,'mesh_path':mesh.get_path_name()})\n    if mesh and mesh.get_path_name() in plant_paths:\n        plant_references.append({'actor':actor.get_path_name(),'label':label,'mesh_path':mesh.get_path_name()})\nobserved=[]")
    code += r'''
result['hero_r2_mesh_references']=hero2_mesh_references
result['aetherflow_actor_references']=plant_references
result['aetherflow_asset_slots']={}
for path in sorted(plant_paths):
    mesh=unreal.EditorAssetLibrary.load_asset(path)
    result['aetherflow_asset_slots'][path]=[str(slot.material_slot_name) for slot in mesh.get_editor_property('static_materials')]
base=unreal.EditorAssetLibrary.load_asset(BASE_MATERIAL_PATH)
result['aetherflow_base']={'path':base.get_path_name(),'class':base.get_class().get_name(),
    'two_sided':bool(base.get_editor_property('two_sided')),
    'use_material_attributes':bool(base.get_editor_property('use_material_attributes')),
    'shading_model':str(base.get_editor_property('shading_model')),
    'blend_mode':str(base.get_editor_property('blend_mode')),
    'expressions':unreal.MaterialEditingLibrary.get_num_material_expressions(base)}
result['aetherflow_materials']={}
for slot,path in MATERIAL_PATHS.items():
    instance=unreal.EditorAssetLibrary.load_asset(path)
    mel=unreal.MaterialEditingLibrary
    tint=mel.get_material_instance_vector_parameter_value(instance,'Tint')
    parent=instance.get_editor_property('parent')
    value={'path':instance.get_path_name(),'class':instance.get_class().get_name(),
        'parent':parent.get_path_name() if parent else None,
        'linear_rgb':[getattr(tint,axis) for axis in ('r','g','b')],'alpha':tint.a}
    for parameter,field in (('Roughness','roughness'),('Metallic','metallic'),('Clearcoat','clearcoat'),('ClearcoatRoughness','clearcoat_roughness')):
        value[field]=mel.get_material_instance_scalar_parameter_value(instance,parameter)
    result['aetherflow_materials'][slot]=value
'''
    return (code.replace("ROWS", repr(local["actors"])).replace("ASSETS", repr(sorted(local["disk_static_meshes"])))
            .replace("POWER_PATHS", repr(local["power_paths"])).replace("PLANT_PATHS", repr(list(local["new_paths"].values())))
            .replace("BASE_MATERIAL_PATH", repr(BASE_MATERIAL)).replace("MATERIAL_PATHS", repr(local["material_paths"])))


def collect(folder, output):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    if output.exists() or not output.parent.is_dir() or output.suffix.lower() != ".json":
        raise ValueError("--out must be a new JSON path in an existing directory")
    local = _local(folder)
    before = _file(MAP_FILE)
    if _witness(before) != local["expected_latest_saved_map"]:
        raise ValueError("current map differs from final Aetherflow world save")
    report = {"schema": "daedalus.codex-aetherflow-production-readback.v1", "stage": "local_evidence_collected",
              "collected_utc": datetime.now(timezone.utc).isoformat(), "local": local, "native_calls": [],
              "map_before_readback": before, "expected_latest_saved_map": local["expected_latest_saved_map"],
              "scope": "87 prior actors preserved; two new plants placed; three new saved meshes; glasskelp held",
              "staging_only": True, "ownership_changes": False,
              "limits": {"bar_acceptance": "not_established", "collision_navigation_swimming_ecology": "unverified",
                         "tests": "deferred_by_user", "background_compilation": "not_queried", "native_queue_state": "not_queried",
                         "actor_scan": "first StaticMeshComponent per loaded level actor",
                         "source_conversion": "original GLBs pinned; R2 evaluated join witnesses inspected locally; no FBX reimport here"}}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    def read_call(label, action):
        item = {"label": label, "state": "pending", "read_only": True}
        report["native_calls"].append(item)
        _write(output, report)
        try:
            result = action()
        except Exception as error:
            item.update(state="read_failed", error=str(error))
            _write(output, report)
            raise
        item.update(state="responded", result=result.server if isinstance(result, Mcp) else result)
        _write(output, report)
        return result

    try:
        mcp = read_call("MCP initialize", lambda: Mcp(timeout=60))
        pie = read_call("IsPIERunning", lambda: mcp.call(APP, "IsPIERunning"))
        current = read_call("get_current_level", lambda: mcp.call(SCENE, "get_current_level"))
        report["editor"] = {"pie_running": pie, "current_map": current}
        if pie is not False or package(current) != MAP:
            raise RuntimeError("require agreed map with PIE stopped")
        native = read_call("execute_python89actors85meshes and owned PBR readback", lambda: wire.obj(
            wire.call(wire.UNREAL, "execute_python", code=_native_code(local), unattended=False, timeout=90, side="Unreal"),
            side="Unreal", what="Aetherflow production readback"))
        issues = []
        observed = {row["label"]: row for row in native["actors"]}
        if len(native["actors"]) != 89 or len(observed) != 89 or set(observed) != {row["label"] for row in local["actors"]}:
            issues.append("native actor set differs from exact89")
        prior_fields = ("actor", "mesh_path", "transform", "materials", "override_materials", "folder", "tags")
        for row in local["prior_native"]["actors"]:
            if any(observed.get(row["label"], {}).get(field) != row[field] for field in prior_fields):
                issues.append("prior actor state changed from completed87 baseline: " + row["label"])
        for row in local["new_actors"]:
            actual = observed.get(row["label"], {})
            if (actual.get("actor") != row["actor"] or actual.get("mesh_path") != row["mesh_path"] or
                not actual.get("transform") or not _same_transform(actual["transform"], row["transform"])):
                issues.append("new plant actor identity/mesh/transform differs: " + row["label"])
            desired = local["new_component_materials"][row["label"]]
            if actual.get("materials") != desired or actual.get("override_materials") != desired or actual.get("folder") != local["folder"]:
                issues.append("new plant component materials/folder differ: " + row["label"])
            if any(tag.lower() in ("land", "deed") or tag.lower().startswith("deed:") for tag in actual.get("tags", [])):
                issues.append("new plant actor has ownership tag: " + row["label"])
        expected_refs = {(row["actor"]["refPath"], row["label"], row["mesh_path"]) for row in local["new_actors"]}
        refs = native["aetherflow_actor_references"]
        if len(refs) != 2 or {(row["actor"], row["label"], row["mesh_path"]) for row in refs} != expected_refs:
            issues.append("Aetherflow world references differ from exact two plants; glasskelp must remain zero")
        def reference_set(rows):
            return {(row["actor"], row["label"], row["mesh_path"]) for row in rows}
        if (len(native["power_unit_actor_references"]) != 5 or
            reference_set(native["power_unit_actor_references"]) != reference_set(local["prior_native"]["power_unit_actor_references"])):
            issues.append("PowerUnit exact five world references changed")
        if native["hero_r2_actor_labels"] or native["hero_r2_mesh_references"]:
            issues.append("held HeroR2 has loaded world references")
        classes = native["saved_asset_classes"]
        if (set(classes) != set(local["disk_static_meshes"]) or len(classes) != 85 or
            any(row.get("class") != "StaticMesh" or row.get("is_static_mesh") is not True for row in classes.values()) or
            any(classes.get(path) != row for path, row in local["prior_native"]["saved_asset_classes"].items())):
            issues.append("saved85 StaticMesh class/path set differs")
        for name, path in local["new_paths"].items():
            slots = native["aetherflow_asset_slots"][path]
            if len(slots) != len(local["source_slots"][name]) or set(slots) != set(local["source_slots"][name]):
                issues.append("native saved plant source slots differ: " + name)
            if name in PLACED and slots != local["new_component_slots"][name]:
                issues.append("native placed plant slot order changed: " + name)
        base = native["aetherflow_base"]
        if (base.get("path") != BASE_MATERIAL or base.get("class") != "Material" or base.get("expressions") != 6 or
            "BLEND_OPAQUE" not in base.get("blend_mode", "") or
            any(base.get(key) != value for key, value in local["base_material_readback"].items())):
            issues.append("owned base material attributes differ")
        if set(native["aetherflow_materials"]) != set(local["expected_pbr"]):
            issues.append("owned PBR instance set differs")
        for slot, expected in local["expected_pbr"].items():
            value = native["aetherflow_materials"].get(slot, {})
            if (value.get("path") != local["material_paths"][slot] or value.get("class") != "MaterialInstanceConstant" or
                value.get("parent") != BASE_MATERIAL or not _pbr_same(value, expected, alpha=True)):
                issues.append("owned PBR instance readback differs: " + slot)
        if native["dirty_map_packages"] or native["dirty_content_packages"]:
            issues.append("map/content dirty-package lists are not empty")
        pie_after = read_call("IsPIERunning after snapshot", lambda: mcp.call(APP, "IsPIERunning"))
        current_after = read_call("get_current_level after snapshot", lambda: mcp.call(SCENE, "get_current_level"))
        if pie_after is not False or package(current_after) != MAP:
            issues.append("PIE/current map changed during readback")
        for path, witness in local["protected_files"].items():
            if fingerprint(path) != _witness(witness):
                issues.append("protected production file changed during readback: " + path)
        after = _file(MAP_FILE)
        if _witness(after) != _witness(before) or _witness(after) != local["expected_latest_saved_map"]:
            issues.append("map changed during readback or differs from final world save")
        report.update(stage="aetherflow_production_readback_completed" if not issues else "aetherflow_production_inspection_required",
                      native_readback=native, map_after_readback=after, issues=issues,
                      measured_actor_rows=len(observed), verified_saved_mesh_files=85,
                      new_actor_rows=2, new_saved_mesh_files=3, held_glasskelp_world_references=0 if len(refs) == 2 and
                      all(row["mesh_path"] != local["new_paths"][KELP] for row in refs) else "inspection_required",
                      prior87_actor_state_unchanged=not any(message.startswith("prior actor") for message in issues),
                      protected_disk_files_unchanged=not any(message.startswith("protected production file") for message in issues),
                      editor_after={"pie_running": pie_after, "current_map": current_after})
        _write(output, report)
        return report
    except Exception as error:
        report.update(stage="aetherflow_production_readback_incomplete", error=str(error))
        _write(output, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="CodexContest source/evidence root")
    parser.add_argument("--out", type=Path, required=True, help="new exclusive production readback JSON path")
    args = parser.parse_args()
    result = collect(args.folder, args.out)
    print(json.dumps({key: result[key] for key in ("stage", "measured_actor_rows", "verified_saved_mesh_files", "map_after_readback", "issues")}, indent=2))
    return 0 if not result["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
