"""Pinned import-time provenance for NEW constant-factor glTF M0 materials.

This additive mode never reconstructs historical imports or replaces the closed
persisted-node consumer. A trusted operator must pin the producer's exact receipt
SHA256 outside the receipt. A self-reported hash is not a signature or authority.
Only source-factor binding is admitted; shader output/PBR quality is not proved.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import uuid

SCHEMA = "daedalus.material-import-receipt.v1"
POLICY = "daedalus.material-import-receipt-policy.v1"
NATIVE = "daedalus.fresh-material-current.v1"
PREFIX = "/Game/CodexToolEvaluation/MaterialProvenanceRecovery/"
NAME = "Prop_PracticeCrate_M0"
FUNCTION = "/InterchangeAssets/gltf/MaterialBodies/MF_Default_Body.MF_Default_Body"
PROJECT = "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject"
WORLD = "/Game/Daedalus/DaedalusWorld.DaedalusWorld"
SOURCE_SHA = "4e83515ecb6c49139db195354651fd6e23cebdf6150b2011778755ec8c41581f"
ROOT_UID = "Factory_\\Shaders\\Prop_PracticeCrate_material_0"
LANES = {"base_color": ("BaseColor", "BaseColorFactor_RGB", 0, 2),
         "metallic": ("Metallic", "MetallicFactor", 1, 0),
         "roughness": ("Roughness", "RoughnessFactor", 3, 0)}
TYPES = ("Scalar", "Vector2", "Vector3", "Vector4", "Texture2D", "TextureCube",
         "Texture2DArray", "VolumeTexture", "StaticBool", "MaterialAttributes",
         "TextureExternal", "Bool", "Substrate")
EFFECTS = ("explicit_asset_load_requests", "authored_material_write_requests",
           "material_cache_refreshes", "evaluations", "compilations")
ZERO = (0, 0, 0, 0, 0)
RGB = (1, 1, 1, 1, 0)
RED = (1, 1, 0, 0, 0)
LIMIT = 512 * 1024


class Held(ValueError):
    pass


def need(value, message):
    if not value:
        raise Held(message)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(rows):
    out = {}
    for key, value in rows:
        need(key not in out, "Duplicate JSON member")
        out[key] = value
    return out


def _shape(value, depth=0):
    need(depth <= 32, "JSON depth exceeded")
    if type(value) is dict:
        need(len(value) <= 128, "JSON object exceeded")
        for key, child in value.items():
            need(type(key) is str and 0 < len(key) <= 256, "JSON key invalid")
            _shape(child, depth + 1)
    elif type(value) is list:
        need(len(value) <= 128, "JSON array exceeded")
        for child in value:
            _shape(child, depth + 1)
    elif type(value) is str:
        need(len(value) <= 2048 and not any(ord(c) < 32 for c in value), "JSON text invalid")
    elif type(value) is float:
        need(math.isfinite(value), "Nonfinite JSON value")
    else:
        need(value is None or type(value) in (int, bool), "Unknown JSON type")


def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= LIMIT, "Bounded original UTF8 bytes required")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    _shape(value)
    return value


def _hex(value, count=64):
    need(type(value) is str and re.fullmatch("[0-9a-f]{" + str(count) + "}", value)
         and value != "0" * count, "Nonzero exact digest/GUID required")
    return value


def _utc(value):
    need(type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?(?:Z|\+00:00)", value),
         "Explicit original UTC required")
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d", r"\1", value).replace("Z", "+00:00"))


def _identity(row, path=None, cls=None, owner=None):
    need(type(row) is dict and set(row) == {"path", "class", "owner"}, "Complete typed object identity required")
    need(all(type(x) is str and 0 < len(x) <= 1024 for x in row.values()), "Invalid object identity")
    need(path is None or row["path"] == path, "Object path mismatch")
    need(cls is None or row["class"] == cls, "Object class mismatch")
    need(owner is None or row["owner"] == owner, "Object owner mismatch")
    return row


def _integer(value, low=0, high=128):
    need(type(value) is int and low <= value <= high, "Strict bounded integer required")
    return value


def _number(value):
    need(type(value) in (int, float) and math.isfinite(value) and abs(value) <= 3.4028234663852886e38,
         "Finite float32 number required")
    return value


def _value(value, vector=False):
    if vector:
        need(type(value) is list and len(value) == 4, "Complete RGBA vector required")
        return [_number(x) for x in value]
    return _number(value)


def _masks(row):
    keys = ("mask", "r", "g", "b", "a")
    need(type(row) is dict and set(row) == set(keys), "Complete native masks required")
    return tuple(_integer(row[key], 0, 1) for key in keys)


def _connection(row, allowed):
    need(type(row) is dict and row.get("selected_output_valid") is True, "Cached selected output required")
    raw, selected = _masks(row.get("raw_masks")), _masks(row.get("selected_output_masks"))
    effective = raw if raw[0] else selected
    need(_masks(row.get("effective_masks")) == effective and effective in allowed,
         "Wrong/nonidentity effective projection")


def file_pin(path, maximum=64 * 1024 * 1024):
    path = Path(path).resolve()
    need(path.is_file() and not path.is_symlink() and not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400),
         "Regular non-reparse evidence file required")
    before = path.stat()
    need(0 < before.st_size <= maximum, "Evidence file outside size bound")
    raw = path.read_bytes()
    after = path.stat()
    need(len(raw) == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
         "Evidence changed during read")
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def _same_file(expected):
    need(type(expected) is dict and set(expected) == {"path", "bytes", "sha256"}, "Exact file pin required")
    _hex(expected["sha256"])
    need(file_pin(expected["path"]) == expected, "Current evidence file differs")


def build_policy(source_path, allowed_root, versions, function_package):
    """Called by the owning host BEFORE import, from its independently pinned files."""
    need(type(allowed_root) is str and allowed_root.startswith(PREFIX)
         and re.fullmatch(r"[A-Za-z0-9_-]{1,48}", allowed_root[len(PREFIX):]), "Owned fresh run root required")
    source = file_pin(source_path)
    need(source["bytes"] == 18576 and source["sha256"] == SOURCE_SHA, "Closed source profile mismatch")
    raw = Path(source["path"]).read_bytes()
    magic, version, size, length, kind = struct.unpack_from("<4sIII4s", raw)
    need((magic, version, size, kind) == (b"glTF", 2, len(raw), b"JSON") and 20 + length <= len(raw), "GLB layout mismatch")
    doc = json.loads(raw[20:20+length], object_pairs_hook=_pairs)
    need(not any(doc.get(key) for key in ("textures", "images", "extensionsUsed", "extensionsRequired")), "Only closed constant source supported")
    row = doc["materials"][0]; pbr = row["pbrMetallicRoughness"]
    need(row["name"] == NAME and row["doubleSided"] is True and pbr["baseColorFactor"][3] == 1, "Source material profile mismatch")
    profile = {"base_color": pbr["baseColorFactor"], "metallic": pbr["metallicFactor"], "roughness": pbr["roughnessFactor"]}
    need(type(versions) is dict and set(versions) == {"engine", "producer_sha256", "reader_sha256", "importer_files"}, "Explicit version bindings required")
    _hex(versions["producer_sha256"]); _hex(versions["reader_sha256"])
    need(type(versions["engine"]) is str and versions["engine"].startswith("5.8.4-")
         and type(versions["importer_files"]) is list and 1 <= len(versions["importer_files"]) <= 8, "Bounded installed importer version required")
    for pin in versions["importer_files"]:
        _same_file(pin)
    _same_file(function_package)
    policy = {"schema": POLICY, "root": allowed_root, "asset": allowed_root+"/"+NAME+"."+NAME,
              "source": source, "source_md5": hashlib.md5(raw).hexdigest(), "profile": profile,
              "function_package": function_package, "versions": versions}
    policy["policy_id"] = sha(encode(policy))
    return policy


def _policy(policy):
    need(type(policy) is dict and policy.get("schema") == POLICY, "Versioned caller policy required")
    need(policy.get("policy_id") == sha(encode({k: v for k, v in policy.items() if k != "policy_id"})), "Policy digest mismatch")
    root = policy.get("root")
    need(type(root) is str and root.startswith(PREFIX) and re.fullmatch(r"[A-Za-z0-9_-]{1,48}", root[len(PREFIX):]), "Fresh scope mismatch")
    need(policy.get("asset") == root+"/"+NAME+"."+NAME and policy["source"]["sha256"] == SOURCE_SHA
         and policy["source"]["bytes"] == 18576, "Closed asset/source mismatch")
    need(build_policy(policy["source"]["path"], root, policy["versions"], policy["function_package"]) == policy,
         "Policy does not derive from exact current pinned source")


def _native(policy, payload, clean):
    need(type(payload) is dict and payload.get("schema") == NATIVE and payload.get("state") == "complete"
         and payload.get("native_invoked") is True and payload.get("errors") == [], "Complete native witness required")
    need(payload.get("engine_version") == policy["versions"]["engine"], "Current engine version differs")
    need(payload.get("project_path") == PROJECT and payload.get("world_path") == WORLD, "Current project/world mismatch")
    need(str(uuid.UUID(payload.get("capture_id"))) == payload["capture_id"], "Actual native capture UUID required")
    for key in EFFECTS:
        need(type(payload.get(key)) is int and payload[key] == 0, "Native reader effect refused: " + key)
    before, after = payload.get("dirty_before"), payload.get("dirty_after")
    allowed = [policy["asset"].split(".")[0]]
    need(before == after and (before == [] or (not clean and before == allowed)), "Unexpected dirty state")
    _integer(payload.get("editor_pid"), 1, 2147483647); _utc(payload.get("observed_at_utc"))
    row = payload.get("current"); need(type(row) is dict, "Current material graph missing")
    path = policy["asset"]
    _identity(row.get("material"), path, "/Script/Engine.Material", path.split(".")[0])
    need(row.get("source_material_name") == NAME and row.get("two_sided") is True
         and row.get("blend_mode") == "BLEND_Opaque" and row.get("material_domain") == "MD_Surface"
         and row.get("interface_context") == {"interface_path":path,"exact_class":"/Script/Engine.Material","is_instance":False,"parent_chain":[]}, "Exact fresh surface context required")
    call = row.get("current_call"); need(type(call) is dict, "Current call missing")
    caller = _identity(call.get("caller"), cls="/Script/Engine.MaterialExpressionMaterialFunctionCall", owner=path)
    need(caller["path"].startswith(path+":"), "Caller outside material")
    _identity(call.get("function"), FUNCTION, "/Script/Engine.MaterialFunction", FUNCTION.split(".")[0])
    count = _integer(call.get("input_count"), 1)
    roster = call.get("input_roster")
    need(call.get("input_roster_complete") is True and type(roster) is list and len(roster) == count, "Full paired roster required")
    names, ids, paths = set(), set(), set()
    by_name = {}
    for index, entry in enumerate(roster):
        need(type(entry) is dict and type(entry.get("index")) is int and entry["index"] == index, "Roster order mismatch")
        name = entry.get("input_name"); node_id = _hex(entry.get("node_guid"), 32)
        node = _identity(entry.get("node"), cls="/Script/Engine.MaterialExpressionFunctionInput", owner=FUNCTION)
        kind = _integer(entry.get("input_type_value"), 0, 12)
        need(type(name) is str and name and name not in names and node_id not in ids and node["path"] not in paths
             and node["path"].startswith(FUNCTION+":") and entry.get("caller_input_guid") == node_id
             and entry.get("cached_pointer_equal") is True and entry.get("input_type") == "FunctionInput_"+TYPES[kind], "Unpaired/ambiguous roster")
        names.add(name); ids.add(node_id); paths.add(node["path"]); by_name[name] = entry
    bindings, factors = call.get("property_bindings"), row.get("factors")
    need(type(bindings) is dict and set(bindings) == set(LANES) and type(factors) is dict and set(factors) == set(LANES), "All three roles required")
    for lane, (output, role, output_index, kind) in LANES.items():
        b = bindings[lane]
        need(b.get("current_input_present") is True and b.get("uses_input_constant") is False and b.get("current_pointer_equal") is True
             and b.get("expression_path") == caller["path"] and type(b.get("output_index")) is int and b["output_index"] == output_index
             and b.get("selected_output_name") == output, "Root property output mismatch")
        _connection(b, (ZERO,))
        entry = by_name.get(role); factor = factors[lane]
        need(entry is not None and entry["input_type_value"] == kind and type(factor) is dict
             and factor.get("roster_index") == entry["index"] and type(factor.get("roster_index")) is int
             and factor.get("input_node_guid") == entry["node_guid"] and factor.get("caller_input_guid") == entry["node_guid"]
             and factor.get("current_pointer_equal") is True, "Factor GUID/type binding mismatch")
        c, leaf = factor.get("connection"), factor.get("leaf")
        need(type(c) is dict and c.get("expression_present") is True and type(c.get("output_index")) is int and c["output_index"] == 0
             and type(leaf) is dict, "Direct connected leaf required")
        _connection(c, (ZERO, RGB) if lane == "base_color" else (ZERO, RED))
        cls = "/Script/Engine.MaterialExpression" + ("Constant3Vector" if lane == "base_color" else "Constant")
        expr = _identity(c.get("expression"), leaf.get("expression_path"), cls, path)
        need(expr["path"].startswith(path+":") and leaf.get("value_kind") == ("FLinearColor" if lane == "base_color" else "float32"), "Only exact direct constant leaves supported")
        value = _value(leaf.get("value"), lane == "base_color")
        expected = policy["profile"][lane]
        need(value == expected, "Current constant factor no longer equals pinned source")
    metadata = payload.get("metadata"); need(type(metadata) is dict, "Retained root/source metadata required")
    data = _identity(metadata.get("asset_import_data"), cls="/Script/InterchangeEngine.InterchangeAssetImportData", owner=path)
    need(data["path"].startswith(path+":") and Path(metadata.get("source_filename", "")).resolve() == Path(policy["source"]["path"]).resolve()
         and metadata.get("source") == {k:policy["source"][k] for k in ("bytes","sha256")}
         and metadata.get("source_md5") == policy["source_md5"] and metadata.get("root_uid") == ROOT_UID
         and metadata.get("factory_uid") == ROOT_UID and metadata.get("factory_class") == "/Script/InterchangeFactoryNodes.InterchangeMaterialFactoryNode", "Stored source/root binding mismatch")
    return row


def _live(policy, live, native):
    need(type(live) is dict and live.get("source_sha256") == policy["source"]["sha256"] and live.get("root_uid") == ROOT_UID,
         "Import-time source/root mismatch")
    need(type(live.get("container_path")) is str and live["container_path"].startswith("/Engine/Transient.")
         and len(live["container_path"]) <= 1024, "Actual bounded job container identity required")
    boundaries = live.get("boundaries")
    need(type(boundaries) is list and [x.get("phase") for x in boundaries] == ["post_factory", "post_import"], "Actual callback boundaries required")
    need(all(x.get("container_path") == live.get("container_path") and x.get("asset_path") == policy["asset"]
             and x.get("is_reimport") is False for x in boundaries), "Same-job fresh identity mismatch")
    graph, fn = live.get("shader_graph"), live.get("function_shader")
    factory_fn, factors = live.get("factory_function"), live.get("factor_factories")
    need(type(graph) is dict and graph.get("class") == "/Script/InterchangeNodes.InterchangeShaderGraphNode" and graph.get("label") == NAME
         and type(fn) is dict and fn.get("class") == "/Script/InterchangeNodes.InterchangeFunctionCallShaderNode" and fn.get("function_path") == FUNCTION
         and type(factory_fn) is dict and factory_fn.get("class") == "/Script/InterchangeFactoryNodes.InterchangeMaterialFunctionCallExpressionFactoryNode"
         and type(factors) is dict and set(factors) == set(LANES), "Exact typed graph/function/factors required")
    ids = [ROOT_UID, graph.get("uid"), fn.get("uid"), factory_fn.get("uid")] + [x.get("uid") for x in factors.values()]
    need(all(type(x) is str and 0 < len(x) <= 1024 for x in ids) and len(set(ids)) == len(ids), "Unique exact node identities required")
    need(live.get("root_targets") == [graph["uid"]] == native["metadata"].get("factory_target_uids"), "Factory target/graph mismatch")
    need(factory_fn.get("expression_class") == "MaterialExpressionMaterialFunctionCall"
         and factory_fn.get("expression_path") == native["current"]["current_call"]["caller"]["path"], "Factory UID does not bind actual created caller")
    for lane, (output, role, _, _) in LANES.items():
        need(graph.get("connections", {}).get(lane) == {"uid":fn["uid"],"output":output}
             and live.get("root_connections", {}).get(lane) == {"uid":factory_fn["uid"],"output":output}
             and native["metadata"].get("factory_connections", {}).get(lane) == live["root_connections"][lane], "Import-time property chain mismatch")
        attribute = fn.get("attributes", {}).get(lane)
        need(type(attribute) is dict and attribute.get("role") == role and attribute.get("kind") == ("LinearColor" if lane == "base_color" else "Float")
             and _value(attribute.get("value"), lane == "base_color") == policy["profile"][lane], "Typed source function attribute differs")
        leaf = factors[lane]
        need(factory_fn.get("inputs", {}).get(lane) == {"uid":leaf["uid"],"output":""}
             and leaf.get("class") == "/Script/InterchangeFactoryNodes.InterchangeMaterialExpressionFactoryNode"
             and leaf.get("expression_class") == ("MaterialExpressionConstant3Vector" if lane == "base_color" else "MaterialExpressionConstant")
             and leaf.get("expression_path") == native["current"]["factors"][lane]["connection"]["expression"]["path"], "Factory factor UID does not bind actual created constant")


def _receipt(policy, body):
    _policy(policy)
    need(type(body) is dict and set(body) == {"schema","policy_id","job_id","import_started_utc","created_utc","versions","live","import_native","reload_native","package","preservation","outputs","fresh_import","replace_existing"}, "Exact versioned receipt shape required")
    need(body["schema"] == SCHEMA and body["policy_id"] == policy["policy_id"] and body["versions"] == policy["versions"]
         and body["fresh_import"] is True and body["replace_existing"] is False and body["outputs"] == [policy["asset"]], "Receipt schema/version/output mismatch")
    need(str(uuid.UUID(body["job_id"])) == body["job_id"], "Unique job UUID required")
    first, reload = body["import_native"], body["reload_native"]
    _native(policy, first, False); _native(policy, reload, True); _live(policy, body["live"], first)
    need(first["editor_pid"] == reload["editor_pid"] and first["capture_id"] != reload["capture_id"],
         "Distinct import/reload calls in the same process required")
    need(first["current"] == reload["current"] and first["metadata"] == reload["metadata"], "Saved/reloaded current binding differs")
    need(_utc(body["import_started_utc"]) <= _utc(first["observed_at_utc"]) <= _utc(reload["observed_at_utc"]) <= _utc(body["created_utc"]), "Import/save/reload chronology differs")
    elapsed = (_utc(body["created_utc"]) - _utc(body["import_started_utc"])).total_seconds()
    need(0 <= elapsed <= 900 and (_utc(body["created_utc"]) - datetime.now(timezone.utc)).total_seconds() <= 2,
         "Import interval/future timestamp refused")
    proof = body["preservation"]
    need(type(proof) is dict and set(proof) == {"before_sha256","after_sha256","normal_terminal","dirty_after"}
         and _hex(proof["before_sha256"]) == _hex(proof["after_sha256"])
         and proof["normal_terminal"] is True and proof["dirty_after"] == [], "Protected known terminal required")
    _hex(body["package"].get("sha256")); _integer(body["package"].get("bytes"), 1, 8*1024*1024)


def seal(policy, evidence, package_path):
    """Finalize only after actual completion, new-only save and real reload."""
    body = {**evidence, "schema":SCHEMA, "policy_id":policy["policy_id"],
            "versions":policy["versions"], "package":file_pin(package_path),
            "created_utc":datetime.now(timezone.utc).isoformat()}
    _receipt(policy, body)
    _same_file(policy["source"]); _same_file(policy["function_package"])
    raw = encode(body); need(len(raw) <= LIMIT, "Receipt UTF8 cap exceeded")
    return raw


def consume(policy, raw, *, expected_receipt_sha256, current_native_raw,
            expected_editor_pid, package_path):
    """Recheck exact files + a fresh independently dispatched current reader.

    expected_receipt_sha256 and expected_editor_pid are caller-owned expectations,
    never values copied from the untrusted receipt. Current reader freshness is
    checked against the real clock; there is no public clock override.
    """
    result = {"state":"HELD", "receipt_accepted":False, "historical_admission":False,
              "admission_scope":"FRESH_SOURCE_BASE_COLOR_RGB_BINDING_ONLY",
              "root_output_equivalence_proven":False, "all_pbr_factors_qualified":False,
              "native_runtime_qualified":False, "reasons":[]}
    try:
        _hex(expected_receipt_sha256)
        need(type(raw) is bytes and sha(raw) == expected_receipt_sha256, "Caller-pinned receipt bytes differ")
        body = decode(raw); _receipt(policy, body)
        _same_file(policy["source"]); _same_file(policy["function_package"])
        for pin in policy["versions"]["importer_files"]:
            _same_file(pin)
        need(file_pin(package_path) == body["package"], "Current saved package differs/renamed")
        current = decode(current_native_raw); _native(policy, current, True)
        need(type(expected_editor_pid) is int and current["editor_pid"] == expected_editor_pid, "Independent process identity mismatch")
        need(current["capture_id"] not in (body["import_native"]["capture_id"], body["reload_native"]["capture_id"])
             and _utc(current["observed_at_utc"]) >= _utc(body["created_utc"]), "Distinct current witness after sealed receipt required")
        age = (datetime.now(timezone.utc) - _utc(current["observed_at_utc"])).total_seconds()
        need(-2 <= age <= 300, "Current native witness stale/future")
        need(current["current"] == body["reload_native"]["current"] and current["metadata"] == body["reload_native"]["metadata"], "Current graph/import binding changed")
        result.update(state="PASS_FRESH_IMPORT_RECEIPT", receipt_accepted=True,
                      asset=policy["asset"], receipt_sha256=sha(raw), source_sha256=SOURCE_SHA,
                      observed_factors={lane:current["current"]["factors"][lane]["leaf"]["value"] for lane in LANES})
    except (Held, ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError, OSError, AttributeError) as error:
        result["reasons"].append(str(error))
    return result
