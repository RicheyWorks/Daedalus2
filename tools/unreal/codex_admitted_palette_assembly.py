# SPDX-License-Identifier: MIT
"""Prepare a retained voxel palette, then place and bind before one map save.

Use only in the sole operator's accepted editor turn, with no other native job.
The existing importer and palette generator retain their own save/receipt rules.
An unfinished palette or assembly journal requires inspection, never replay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time
import uuid

from codex_admitted_asset_assembly import POWER_NAME, RETAINED_ISLANDS, plan_admitted
from codex_contest_island_delivery import DEST, Mcp, SCENE, fingerprint, package
from codex_saved_asset_assembly import _read, _write, execute_plan
from codex_staging_palette import _linear
from codex_workshop_terrain import _islands
from asset_pipeline import wire

ROOT = Path(__file__).resolve().parents[2]
PALETTE = DEST + "/Palette"
SCHEMA = "daedalus.codex-admitted-voxel-palette.v1"
HELPER = ROOT / "engines/unreal/DaedalusLink/Content/Python/daedalus_codex_staging_palette.py"


def _result(reply):
    if isinstance(reply, dict):
        if reply.get("error"):
            raise RuntimeError("inspect retained native error before another operation")
        return reply.get("result")
    return reply


def _source(plan, source_path):
    source, witness = _read(source_path)
    names = set(plan["placements_cm"])
    name = source.get("name")
    config = source.get("config", {})
    schema = "daedalus.codex-salvage-assembly.v1" if name == POWER_NAME else "daedalus.codex-island.v1"
    if names != {name} or name not in set(RETAINED_ISLANDS) | {POWER_NAME} or source.get("stage") != "exported" or source.get("schema") != schema:
        raise ValueError("require one exact retained exported voxel candidate")
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    if source.get("config_sha256") != plan["config_sha256"] or config_hash != plan["config_sha256"] or config.get("seed") != plan["seed"]:
        raise ValueError("source palette recipe differs from its saved admission")
    fbx = source.get("artifacts", {}).get("fbx", {})
    if fbx.get("fingerprint") != plan["source_fingerprint"] or fingerprint(fbx["path"]) != plan["source_fingerprint"]:
        raise ValueError("source palette FBX differs from its saved admission")
    objects = source.get("blender", {}).get("objects", [])
    labels = {row["label"] for row in plan["entries"]}
    if len(objects) != len(labels) or {row.get("name") for row in objects} != labels:
        raise ValueError("source palette object set differs from admitted roles")
    slots = {row["name"]: row.get("materials") for row in objects}
    rgb = source.get("palette_rgb", {})
    surfaces = source.get("palette_surface", _islands().SURFACES)
    used = {slot for values in slots.values() if isinstance(values, list) for slot in values}
    if any(not isinstance(values, list) or not values or len(values) != len(set(values)) for values in slots.values()):
        raise ValueError("require distinct nonempty exported material slots per mesh")
    if not isinstance(rgb, dict) or not 1 <= len(rgb) <= 32 or any(re.fullmatch(r"[a-z][a-z0-9_]{0,31}", key) is None for key in rgb):
        raise ValueError("palette exceeds the bounded voxel key contract")
    if not used.issubset({"CodexVoxel_" + key for key in rgb}):
        raise ValueError("exported slots leave their source palette")
    settings = {}
    for key, values in rgb.items():
        if "CodexVoxel_" + key not in used:
            continue
        surface = surfaces[key]
        if not isinstance(values, (list, tuple)) or len(values) != 3 or set(surface) != {"roughness", "metallic"}:
            raise ValueError("require three sRGB channels and exact surface fields")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in (*values, *surface.values())):
            raise ValueError("palette channels and surfaces must be finite in [0,1]")
        settings[key] = dict(linear_rgb=[_linear(v) for v in values], **surface)
    return witness, settings, slots


def _material_paths(settings):
    return {"CodexVoxel_" + key: PALETTE + "/MI_Codex_" + key + "_" +
            hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]
            for key, value in settings.items()}


def _attach(record, journal):
    plan = dict(record["assembly_plan"])
    paths = _material_paths(record["settings"])
    plan["component_overrides"] = {label: {slot: paths[slot] + "." + paths[slot].rsplit("/", 1)[-1] for slot in slots}
                                   for label, slots in record["slots"].items()}
    plan["component_override_contract"] = {"schema": SCHEMA, "journal": str(journal), "fingerprint": fingerprint(journal)}
    return plan


def _protected_inputs(plan, source_receipt):
    return ({Path(plan[key]).resolve() for key in ("manifest", "saved_receipt", "map_file")} |
            {Path(source_receipt).resolve(), HELPER.resolve(), (ROOT / "tools/blender/codex_contest_island.py").resolve()} |
            {Path(value["path"]).resolve() for value in plan["native_output_fingerprints"].values()})


def validate_palette_plan(plan, assembly_journal=None):
    """Recheck saved palette/input witnesses before the first world mutation."""
    contract = plan["component_override_contract"]
    if contract.get("schema") != SCHEMA:
        raise ValueError("unknown component palette contract")
    record, witness = _read(contract["journal"])
    bare = {key: value for key, value in plan.items() if key not in ("component_overrides", "component_override_contract")}
    if witness != contract["fingerprint"] or record.get("stage") != "palette_saved" or record.get("assembly_plan") != bare:
        raise ValueError("palette journal is unfinished, changed or belongs to another plan")
    if assembly_journal is not None:
        protected = _protected_inputs(bare, record["source_receipt"]) | {Path(contract["journal"]).resolve()}
        protected |= {Path(value["path"]).resolve() for value in record["palette_outputs"].values()}
        if Path(assembly_journal).resolve() in protected:
            raise ValueError("assembly journal must not overwrite a palette/input witness")
    source_fp, settings, slots = _source(bare, record["source_receipt"])
    if source_fp != record["source_fingerprint"] or settings != record["settings"] or slots != record["slots"]:
        raise ValueError("palette source identity changed")
    if fingerprint(HELPER) != record["helper_fingerprint"] or fingerprint(ROOT / "tools/blender/codex_contest_island.py") != record["surface_profile_fingerprint"]:
        raise ValueError("reviewed palette helper/profile changed")
    for key in ("manifest", "saved_receipt"):
        if fingerprint(bare[key]) != bare[key + "_fingerprint"]:
            raise ValueError("saved admission changed before placement")
    for output in bare["native_output_fingerprints"].values():
        if fingerprint(output["path"]) != {key: output[key] for key in ("sha256", "bytes")}:
            raise ValueError("saved admitted mesh bytes changed before placement")
    if _attach(record, Path(contract["journal"])) != plan:
        raise ValueError("component overrides differ from the exact source palette")
    paths = set(_material_paths(settings).values()) | {PALETTE + "/M_CodexPalette_v1"}
    if set(record["palette_outputs"]) != paths:
        raise ValueError("saved palette output set differs")
    for output in record["palette_outputs"].values():
        if fingerprint(output["path"]) != {key: output[key] for key in ("sha256", "bytes")}:
            raise ValueError("saved palette bytes changed before placement")


def _live_preflight(plan, timeout):
    """Read current editor state and exact mesh slots without writing journals."""
    mcp = Mcp(timeout=timeout)
    if mcp.call("EditorToolset.EditorAppToolset", "IsPIERunning") or package(mcp.call(SCENE, "get_current_level")) != plan["map_package"]:
        raise RuntimeError("require stopped PIE and the exact agreed map")
    # Read only the admitted meshes, without a full-world actor snapshot.
    read_label = "Codex admitted palette readback " + uuid.uuid4().hex
    code = '''import unreal,sys
rows=ROWS
b=sys.modules.get('claude_unreal_bridge')
others=[req for gen,req,box in list(b._running)
        if req.get('type')!='execute_python' or (req.get('params') or {}).get('label')!=OWN_LABEL] if b else [None]
if others or b._jobs.qsize() or b._remote_lock.locked():
    raise RuntimeError('conflicting or unobservable bridge job; no palette mutation')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    raise RuntimeError('preserve dirty packages before palette preparation')
result={}
for row in rows:
    mesh=unreal.EditorAssetLibrary.load_asset(row['mesh_path'])
    if not isinstance(mesh,unreal.StaticMesh) or mesh.get_path_name()!=row['mesh_path']:raise RuntimeError('admitted mesh identity changed')
    result[row['label']]=[str(slot.material_slot_name) for slot in mesh.get_editor_property('static_materials')]
'''.replace("ROWS", repr(plan["entries"]), 1).replace("OWN_LABEL", repr(read_label), 1)
    started = time.perf_counter()
    reply = wire.call(wire.UNREAL, "execute_python", code=code, label=read_label, unattended=False, timeout=30, side="Unreal")
    return reply, round(time.perf_counter() - started, 6)


def _require_native_slots(reply, slots):
    actual = _result(reply)
    if not isinstance(actual, dict) or set(actual) != set(slots) or any(len(actual[label]) != len(expected) or set(actual[label]) != set(expected) for label, expected in slots.items()):
        raise RuntimeError("saved native material slots differ from the exported source")


def prepare_palette(plan, source_receipt, journal_path, timeout=180):
    """Prepare assets without actors or map saves; reuse only a completed journal."""
    journal = Path(journal_path).resolve()
    source_receipt = Path(source_receipt).resolve()
    if journal in _protected_inputs(plan, source_receipt):
        raise ValueError("palette journal must not overwrite an input")
    if not journal.parent.is_dir():
        raise ValueError("palette journal directory must already exist")
    source_fp, settings, slots = _source(plan, source_receipt)
    if journal.exists():
        record, _ = _read(journal)
        if record.get("stage") != "palette_saved" or record.get("assembly_plan") != plan or record.get("source_receipt") != str(source_receipt):
            raise RuntimeError("unfinished or different palette journal requires inspection; no replay")
        prepared = _attach(record, journal)
        validate_palette_plan(prepared)
        # Saved disk witnesses cannot establish current PIE/dirty/job state.
        # Recheck live state without changing this completed journal or its key.
        reply, _ = _live_preflight(plan, timeout)
        _require_native_slots(reply, slots)
        validate_palette_plan(prepared)
        return prepared
    record = {"stage": "preflight", "assembly_plan": plan, "source_receipt": str(source_receipt),
              "source_fingerprint": source_fp, "settings": settings, "slots": slots,
              "helper_fingerprint": fingerprint(HELPER),
              "surface_profile_fingerprint": fingerprint(ROOT / "tools/blender/codex_contest_island.py"),
              "native_mutations": [], "timings_s": {}, "map_saves": 0}
    _write(journal, record)
    reply, elapsed = _live_preflight(plan, timeout)
    record["slot_readback_reply"] = reply
    record["timings_s"]["slot_readback"] = elapsed
    _write(journal, record)
    _require_native_slots(reply, slots)
    record["stage"] = "palette_mutation_pending"
    palette_label = "Codex admitted palette before placement " + uuid.uuid4().hex
    record["native_palette_label"] = palette_label
    _write(journal, record)
    code = '''from pathlib import Path
import hashlib,sys,unreal
source=SOURCE
raw=Path(source).read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('reviewed palette helper changed')
scope={'__name__':'_codex_admitted_palette'}
exec(compile(raw,source,'exec'),scope)
def steps():
    b=sys.modules.get('claude_unreal_bridge')
    others=[req for gen,req,box in list(b._running)
            if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=OWN_LABEL] if b else [None]
    if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('conflicting bridge job; preserve palette journal')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('dirty packages changed before palette admission')
    return (yield from scope['palette_steps'](SETTINGS,JOURNAL))
'''.replace("SOURCE", repr(str(HELPER)), 1).replace("EXPECTED", repr(record["helper_fingerprint"]["sha256"]), 1).replace("SETTINGS", repr(settings), 1).replace("JOURNAL", repr(str(journal)), 1).replace("OWN_LABEL", repr(palette_label), 1)
    started = time.perf_counter()
    try:
        reply = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=palette_label, budget_ms=1, timeout=timeout, side="Unreal")
    except Exception as error:
        # The native helper may have journaled a partial action. Retain it.
        record, _ = _read(journal)
        record.update(stage="palette_outcome_uncertain", error=str(error))
        _write(journal, record)
        raise
    record, _ = _read(journal)
    record["palette_reply"] = reply
    record["timings_s"]["palette_assets"] = round(time.perf_counter() - started, 6)
    record["stage"] = "palette_response_received"
    _write(journal, record)
    materials = _result(reply)
    paths = _material_paths(settings)
    if not isinstance(materials, dict) or set(materials) != set(paths) or any(materials[slot] != {"refPath": path + "." + path.rsplit("/", 1)[-1]} for slot, path in paths.items()):
        raise RuntimeError("inspect retained palette response before another operation")
    actions = record.get("palette_mutations", [])
    if not actions or any(action.get("state") != "responded" or action.get("save_return", True) is not True for action in actions):
        raise RuntimeError("palette actions lack completed native save proof")
    map_file = Path(plan["map_file"])
    content = next(parent for parent in map_file.parents if parent.name.lower() == "content")
    record["palette_outputs"] = {path: dict(path=str(content / (path[len('/Game/'):] + '.uasset')),
                                              **fingerprint(content / (path[len('/Game/'):] + '.uasset')))
                                 for path in set(paths.values()) | {PALETTE + "/M_CodexPalette_v1"}}
    record["stage"] = "palette_saved"
    _write(journal, record)
    prepared = _attach(record, journal)
    validate_palette_plan(prepared)
    return prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="exact guarded saved admission")
    parser.add_argument("--source-receipt", type=Path, required=True, help="exact exported voxel palette recipe")
    parser.add_argument("--placement-cm", nargs=3, type=float, required=True)
    parser.add_argument("--map", dest="map_path", required=True)
    parser.add_argument("--map-file", type=Path, required=True)
    parser.add_argument("--palette-journal", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True, help="existing durable assembly journal")
    args = parser.parse_args()
    if args.palette_journal.resolve() == args.journal.resolve():
        raise ValueError("palette and assembly require separate durable journals")
    # Refuse an unfinished world journal before even preparing palette assets.
    if args.journal.exists() and _read(args.journal)[0].get("stage") != "placed_and_saved":
        raise RuntimeError("unfinished assembly requires inspection; no replay")
    plan = plan_admitted(args.receipt, args.placement_cm, args.map_path, args.map_file)
    if args.journal.resolve() in _protected_inputs(plan, args.source_receipt):
        raise ValueError("assembly journal must not overwrite an input")
    plan = prepare_palette(plan, args.source_receipt, args.palette_journal)
    print(json.dumps(execute_plan(plan, args.journal), indent=2))


if __name__ == "__main__":
    main()
