"""Offline qualification for four existing Daedalus integration targets.

This validates declared evidence, not caller authority or native adoption. No I/O,
Unreal import, transport, side effects, or automatic policy selection occurs here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

SCHEMA = "daedalus.finishline-targets/v1"
FACTS_SCHEMA = "daedalus.finishline-target-facts/v1"
UNITS = ("mesh.lod_build_policy_operation", "generation.pcg_consumer",
         "streaming.partition_hlod_consumer", "release.cook_package_launch")
MAX_BYTES = 262144
MAX_LODS = 8
MAX_MESHES = 8
MAX_ACTORS = 128
MAX_LEVELS = 512
BUILD_FIELDS = ("recompute_normals", "recompute_tangents", "use_mikk_t_space",
                "generate_lightmap_u_vs", "use_full_precision_u_vs")
HEX = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def integer(value, low=0, high=100000000):
    return type(value) is int and low <= value <= high


def finite(value, low=0.0, high=1.0):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def sha(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def path(value):
    return (isinstance(value, str) and 1 <= len(value) <= 512 and
            value.startswith(("/Game/", "/Script/")) and ".." not in value and
            re.fullmatch(r"[A-Za-z0-9_./:-]+", value) is not None)


def text(value, maximum=128):
    return isinstance(value, str) and 1 <= len(value) <= maximum and all(ord(c) >= 32 for c in value)


def canonical(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise ContractError("Noncanonical JSON value") from exc
    require(len(raw) <= MAX_BYTES, "Payload exceeds byte limit")
    return raw


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_json(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, "Invalid JSON byte payload")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ContractError("Nonfinite JSON constant")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError("Malformed JSON") from exc
    canonical(value)
    return value


def validate_contract(config):
    canonical(config)
    require(isinstance(config, dict) and config.get("schema") == SCHEMA, "Wrong contract schema")
    require(sha(config.get("source_packet_sha256")), "Missing source packet identity")
    require(set(config.get("units", {})) == set(UNITS), "Contract must name exactly four units")
    world = config.get("world", {})
    require(path(world.get("object_path")) and path(world.get("class_path")), "Invalid world identity")
    meshes = config.get("meshes", [])
    require(isinstance(meshes, list) and 1 <= len(meshes) <= MAX_MESHES, "Invalid mesh target count")
    ids = set(); paths = set()
    for target in meshes:
        require(isinstance(target, dict) and text(target.get("id")), "Invalid mesh target")
        require(target["id"] not in ids and target.get("object_path") not in paths, "Duplicate mesh target")
        ids.add(target["id"]); paths.add(target.get("object_path"))
        require(path(target.get("object_path")) and target.get("class_path") == "/Script/Engine.StaticMesh",
                "Invalid StaticMesh identity")
        require(sha(target.get("asset_file_sha256")), "Missing pinned mesh source")
    pcg = config.get("pcg", {})
    require(path(pcg.get("graph_path")) and pcg.get("graph_class") == "/Script/PCG.PCGGraph",
            "Invalid graph identity")
    require(integer(pcg.get("seed"), -2147483648, 2147483647), "Invalid graph consumer seed")
    require(pcg.get("component_path") is None or path(pcg["component_path"]), "Invalid component path")
    require(pcg.get("component_class") == "/Script/PCG.PCGComponent", "Invalid component class")
    require(sha(pcg.get("graph_file_sha256")), "Missing graph file pin")
    descriptors = pcg.get("descriptor_mesh_paths")
    require(isinstance(descriptors, list) and 1 <= len(descriptors) <= MAX_MESHES and
            len(set(descriptors)) == len(descriptors) and set(descriptors).issubset(paths),
            "Descriptors must reference exact admitted Blender meshes")
    require(pcg.get("expected_output_sha256") is None or sha(pcg["expected_output_sha256"]),
            "Invalid expected PCG output pin")
    actors = config.get("hlod", {}).get("source_actor_paths")
    require(isinstance(actors, list) and len(actors) <= MAX_ACTORS and
            len(set(actors)) == len(actors) and all(path(x) for x in actors), "Invalid HLOD source set")
    require(config["hlod"].get("layer_path") is None or path(config["hlod"]["layer_path"]), "Invalid HLOD layer")
    classes = config["hlod"].get("source_actor_classes", {})
    require(isinstance(classes, dict) and set(classes) == set(actors) and all(path(x) for x in classes.values()),
            "Missing exact HLOD source classes")
    require(path(config["hlod"].get("layer_class")), "Missing HLOD layer class")
    release = config.get("release", {})
    require(release.get("target") == "DaedalusRealm" and release.get("platform") == "Win64" and
            release.get("configuration") == "Shipping", "Unexpected release target")
    require(text(release.get("project_file"), 512) and sha(release.get("project_file_sha256")),
            "Missing exact project source pin")
    require(release["project_file"].replace("\\", "/") ==
            "C:/Unreal/DaedalusRealm/DaedalusRealm.uproject", "Unexpected project file root")
    archive = release.get("fresh_archive_path", "").replace("\\", "/")
    require(archive.startswith("C:/Unreal/DaedalusRealm/Saved/Packages/") and ".." not in archive and
            archive != release.get("historic_archive_not_current", "").replace("\\", "/"),
            "Unexpected/nonfresh release archive identity")
    require(release.get("packaged_executable", "").replace("\\", "/") == archive +
            "/DaedalusRealm/Binaries/Win64/DaedalusRealm-Win64-Shipping.exe", "Unexpected packaged executable")
    for unit in config["units"].values():
        require(isinstance(unit, dict) and text(unit.get("target_id")), "Missing unit target identity")
    return config


def identity(actual, expected_path, expected_class):
    require(isinstance(actual, dict), "Missing object facts")
    require(actual.get("object_path") == expected_path, "Object path mismatch")
    require(actual.get("class_path") == expected_class, "Object class mismatch")


def package_expectations(config, observation):
    """Bind mutable post-operation package witnesses without changing original plan pins."""
    require(isinstance(observation, dict), "Missing observation context")
    require(set(observation) == {"phase", "unit_id", "operation_id", "package_overrides"},
            "Unexpected observation context fields")
    expected = {x["id"]: x["asset_file_sha256"] for x in config["meshes"]}
    expected["pcg_graph"] = config["pcg"]["graph_file_sha256"]
    changes = observation["package_overrides"]
    require(isinstance(changes, dict), "Invalid package witness map")
    if observation["phase"] == "preflight":
        require(observation["unit_id"] is None and observation["operation_id"] is None and not changes,
                "Preflight cannot override native package pins")
    else:
        unit = observation["unit_id"]
        require(observation["phase"] in ("post_operation", "reopen") and unit in UNITS and
                text(observation["operation_id"]), "Invalid operation observation")
        allowed = set()
        if unit == UNITS[0]:
            desired = config["units"][unit].get("desired_policy")
            require(isinstance(desired, dict) and desired.get("mesh_id") in
                    {x["id"] for x in config["meshes"]}, "Missing selected LOD target")
            allowed = {desired["mesh_id"]}
        elif unit == UNITS[1]:
            allowed = {"pcg_graph"}
        require(set(changes).issubset(allowed) and all(sha(x) for x in changes.values()),
                "Unadmitted/unrelated native package override")
        expected.update(changes)
    return expected


def _mesh_facts(config, facts, packages):
    rows = facts.get("meshes")
    require(isinstance(rows, list) and len(rows) == len(config["meshes"]), "Mesh facts count mismatch")
    require(len({x.get("id") for x in rows if isinstance(x, dict)}) == len(rows), "Duplicate mesh facts")
    by_id = {x["id"]: x for x in rows}
    ready = True
    for expected in config["meshes"]:
        require(expected["id"] in by_id, "Wrong mesh target identity")
        row = by_id[expected["id"]]
        if row.get("state") != "OBSERVED":
            ready = False
            continue
        identity(row, expected["object_path"], expected["class_path"])
        require(row.get("asset_file_sha256") == packages[expected["id"]], "Mesh package pin mismatch")
        lods = row.get("lods")
        require(isinstance(lods, list) and 1 <= len(lods) <= MAX_LODS, "Invalid LOD facts count")
        for index, lod in enumerate(lods):
            require(lod.get("index") == index and type(lod.get("index")) is int, "LOD index mismatch")
            require(integer(lod.get("triangles"), 1) and integer(lod.get("vertices"), 1),
                    "Missing positive actual render geometry")
            require(finite(lod.get("screen_size")), "Invalid LOD screen size")
            require(isinstance(lod.get("build_settings"), dict) and
                    set(lod["build_settings"]) == set(BUILD_FIELDS), "Unknown or missing actual build fields")
            require(all(type(v) is bool for v in lod["build_settings"].values()), "Invalid build boolean")
    return ready


def inspect(config, facts):
    """Readiness only. Valid measured facts do not authorize a mutation or claim adoption."""
    try:
        validate_contract(config); canonical(facts)
        require(facts.get("schema") == FACTS_SCHEMA, "Wrong facts schema")
        require(facts.get("contract_sha256") == fingerprint(config), "Facts contract pin mismatch")
        require(text(facts.get("capture_id")) and sha(facts.get("reader_sha256")) and
                sha(facts.get("policy_sha256")), "Missing capture/source identity")
        packages = package_expectations(config, facts.get("observation"))
        world = facts.get("world", {})
        require(world.get("state") == "OBSERVED", "Current world unavailable")
        identity(world, config["world"]["object_path"], config["world"]["class_path"])
        mesh_ready = _mesh_facts(config, facts, packages)
        pcg = facts.get("pcg", {})
        graph = pcg.get("graph", {})
        if graph.get("state") == "OBSERVED":
            identity(graph, config["pcg"]["graph_path"], config["pcg"]["graph_class"])
            require(graph.get("asset_file_sha256") == packages["pcg_graph"], "Graph package pin mismatch")
        component = pcg.get("component", {})
        pcg_ready = config["pcg"]["component_path"] is not None and component.get("state") == "OBSERVED"
        if pcg_ready:
            identity(component, config["pcg"]["component_path"], config["pcg"]["component_class"])
            require(component.get("world_path") == config["world"]["object_path"], "PCG consumer world mismatch")
            require(component.get("graph_path") == config["pcg"]["graph_path"], "PCG graph binding mismatch")
            require(type(component.get("seed")) is int and component["seed"] == config["pcg"]["seed"],
                    "PCG consumer seed mismatch")
        pcg_ready = pcg_ready and graph.get("state") == "OBSERVED"
        hlod = facts.get("hlod", {})
        partitioned = world.get("partitioned")
        require(partitioned is None or type(partitioned) is bool, "Invalid partition mode")
        source_set = config["hlod"]["source_actor_paths"]
        hlod_ready = (type(partitioned) is bool and bool(source_set) and
                      config["hlod"]["layer_path"] is not None and hlod.get("state") == "OBSERVED")
        if hlod_ready:
            require(hlod.get("world_path") == config["world"]["object_path"], "HLOD world mismatch")
            require(hlod.get("source_actor_paths") == source_set and
                    hlod.get("source_actor_classes") == config["hlod"]["source_actor_classes"] and
                    hlod.get("layer_path") == config["hlod"]["layer_path"] and
                    hlod.get("layer_class") == config["hlod"]["layer_class"], "HLOD source/layer mismatch")
        release = facts.get("release", {})
        release_ready = release.get("state") == "OBSERVED"
        if release_ready:
            for key in ("project_file", "project_file_sha256", "target", "platform", "configuration"):
                require(release.get(key) == config["release"][key], "Release identity mismatch: " + key)
        result = {UNITS[0]: {"state": "FACTS_READY_POLICY_SELECTION" if mesh_ready else "PENDING", "adopted": False},
                  UNITS[1]: {"state": "TARGET_FACTS_READY" if pcg_ready else "PENDING", "adopted": False},
                  UNITS[2]: {"state": "TARGET_FACTS_READY" if hlod_ready else "PENDING", "adopted": False},
                  UNITS[3]: {"state": "TARGET_FACTS_READY" if release_ready else "PENDING", "adopted": False}}
        return {"state": "VALID_TARGET_FACTS", "units": result, "errors": [],
                "scope": "Readiness/declared provenance only; no authentication, mutation, or adoption"}
    except (ContractError, KeyError, TypeError, AttributeError, ValueError, RecursionError) as exc:
        return {"state": "REJECTED", "units": {}, "errors": [str(exc)[:256]], "adopted": False}


def qualify(config, before, after, evidence):
    """Qualify a finite declared completion packet, never inventing native acceptance.

    Evidence references must still be verified by the existing owner/operator.
    This function cannot authenticate a JSON assertion or publish an adoption flag.
    """
    try:
        first, second = inspect(config, before), inspect(config, after)
        require(first["state"] != "REJECTED" and second["state"] != "REJECTED", "Invalid before/after facts")
        canonical(evidence)
        unit = evidence.get("unit_id")
        require(unit in UNITS, "Unknown integration unit")
        require(evidence.get("contract_sha256") == fingerprint(config), "Completion contract mismatch")
        require(evidence.get("before_sha256") == fingerprint(before) and
                evidence.get("after_sha256") == fingerprint(after), "Completion facts mismatch")
        require(before["capture_id"] != after["capture_id"], "Fresh readback capture required")
        require(before["reader_sha256"] == after["reader_sha256"], "Reader revision changed")
        require(before["policy_sha256"] == after["policy_sha256"], "Policy revision changed")
        target = config["units"][unit]["target_id"]
        require(evidence.get("target_id") == target and text(evidence.get("operation_id")), "Operation identity mismatch")
        require(before["observation"]["phase"] == "preflight", "Expected original preflight witness")
        require(after["observation"]["phase"] == "reopen" and
                after["observation"]["unit_id"] == unit and
                after["observation"]["operation_id"] == evidence["operation_id"],
                "Fresh operation-bound reopened package witnesses required")
        require(evidence.get("changed") is True and integer(evidence.get("observed_output_count"), 1),
                "Empty/no-op result cannot complete an integration")
        require(first["units"][unit]["state"] != "PENDING" and
                second["units"][unit]["state"] != "PENDING", "Target binding remains unknown")
        for stage in ("operation", "save", "reopen", "consumer"):
            receipt = evidence.get(stage, {})
            require(receipt.get("completed") is True, "Incomplete stage: " + stage)
            require(receipt.get("operation_id") == evidence["operation_id"] and
                    receipt.get("unit_id") == unit and receipt.get("target_id") == target,
                    "Stage identity mismatch: " + stage)
            require(sha(receipt.get("receipt_sha256")) and text(receipt.get("record_path")),
                    "Missing exact receipt/record reference: " + stage)
        require(len({(evidence[x]["receipt_sha256"], evidence[x]["record_path"])
                     for x in ("operation", "save", "reopen", "consumer")}) == 4,
                "Stages require distinct correlated evidence records")
        if unit == UNITS[0]:
            desired = config["units"][unit].get("desired_policy")
            require(isinstance(desired, dict) and desired.get("kind") in ("authored_lod_pair", "build_settings"),
                    "Select a justified measured policy first")
            require(evidence.get("applied_policy_sha256") == fingerprint(desired), "LOD policy mismatch")
            selected = desired.get("mesh_id")
            old = {m["id"]: m for m in before["meshes"]}
            new = {m["id"]: m for m in after["meshes"]}
            require(selected in old and selected in new, "Unknown policy mesh")
            require(all(old[k]["lods"] == new[k]["lods"] for k in old if k != selected),
                    "Unrelated mesh changed")
            a, b = old[selected]["lods"], new[selected]["lods"]
            require(a != b, "No actual LOD/build delta")
            require(selected in after["observation"]["package_overrides"] and
                    old[selected]["asset_file_sha256"] != new[selected]["asset_file_sha256"],
                    "Changed saved native package witness required")
            if desired["kind"] == "authored_lod_pair":
                require(sha(desired.get("lod1_source_sha256")) and len(a) == 1 and len(b) == 2,
                        "Missing authored LOD1 pin/two-LOD result")
                require(integer(desired.get("lod1_triangles"), 1), "Invalid desired LOD1 count")
                screens = desired.get("screen_sizes")
                require(isinstance(screens, list) and len(screens) == 2 and
                        all(finite(x) for x in screens) and screens[0] > screens[1], "Invalid desired screens")
                require(b[0]["triangles"] == a[0]["triangles"] and b[0]["vertices"] == a[0]["vertices"],
                        "Authored LOD0 changed")
                require(b[0]["build_settings"] == a[0]["build_settings"], "Unrequested LOD0 build change")
                require(b[1]["triangles"] == desired.get("lod1_triangles") and
                        b[1]["triangles"] < b[0]["triangles"], "Unexpected LOD1 geometry")
                require(integer(desired.get("lod1_vertices"), 1) and
                        b[1]["vertices"] == desired["lod1_vertices"], "Unexpected LOD1 vertices")
                require(isinstance(desired.get("lod1_build_settings"), dict) and
                        set(desired["lod1_build_settings"]) == set(BUILD_FIELDS) and
                        b[1]["build_settings"] == desired["lod1_build_settings"], "Unrequested LOD1 build settings")
                require([x["screen_size"] for x in b] == desired.get("screen_sizes"), "Wrong LOD screens")
            else:
                changes = desired.get("changes")
                require(isinstance(changes, dict) and changes and len(a) == len(b), "Missing build change")
                require(all(type(v) is bool for v in changes.values()), "Invalid desired build values")
                require(set(changes).issubset(a[0]["build_settings"]), "Unknown build-setting name")
                require(any(a[0]["build_settings"].get(k) != v for k, v in changes.items()), "Build no-op")
                require(all(b[0]["build_settings"].get(k) == v for k, v in changes.items()), "Build result mismatch")
                for index, (old_lod, new_lod) in enumerate(zip(a, b)):
                    require(all(old_lod[k] == new_lod[k] for k in ("index", "triangles", "vertices", "screen_size")),
                            "Build policy unexpectedly changed geometry/screens")
                    allowed = set(changes) if index == 0 else set()
                    require(all(old_lod["build_settings"][k] == new_lod["build_settings"].get(k)
                                for k in old_lod["build_settings"] if k not in allowed), "Unrequested build flag changed")
        elif unit == UNITS[1]:
            require(evidence.get("generated_by_pcg") is True and evidence.get("manual_fallback") is False,
                    "Manual placements are not PCG output")
            require(sha(config["pcg"].get("expected_output_sha256")) and
                    config["pcg"]["expected_output_sha256"] == evidence.get("observed_output_sha256"),
                    "PCG output differs from pinned expected result")
            require(evidence.get("descriptor_mesh_paths") == config["pcg"]["descriptor_mesh_paths"],
                    "Wrong Blender mesh descriptors")
            require(evidence.get("repeat_seed_output_sha256") == evidence["observed_output_sha256"],
                    "Same-seed readback evidence missing")
        elif unit == UNITS[2]:
            require(evidence.get("map_migrated") is False, "Map migration is outside this contract")
            require(type(before["world"].get("partitioned")) is bool and
                    before["world"]["partitioned"] == after["world"]["partitioned"],
                    "Observed map partition mode changed")
            expected_route = "partitioned" if after["world"]["partitioned"] else "standalone_nonpartitioned"
            require(evidence.get("supported_builder_route") == expected_route,
                    "Actual supported map/builder route is not qualified")
            require(evidence.get("source_actor_paths") == config["hlod"]["source_actor_paths"], "Wrong HLOD source set")
            require(evidence.get("proxy_state_changed") is True, "HLOD no-op cannot count")
            proxies = evidence.get("proxy_paths")
            require(isinstance(proxies, list) and 1 <= len(proxies) <= MAX_ACTORS and
                    len(set(proxies)) == len(proxies) and all(path(x) for x in proxies) and
                    len(proxies) == evidence["observed_output_count"], "Missing actual finite proxy outputs")
        else:
            require(evidence.get("fresh_archive") is True and evidence.get("launched_packaged_executable") is True,
                    "Historical archive/compile alone cannot count")
            for key in ("executable_sha256", "container_manifest_sha256", "custom_payload_sha256"):
                require(sha(evidence.get(key)), "Missing packaged artifact: " + key)
            require(evidence.get("launched_map") == config["world"]["object_path"], "Wrong packaged realm")
            require(evidence.get("archive_path") == config["release"]["fresh_archive_path"] and
                    evidence.get("executable_path") == config["release"]["packaged_executable"], "Wrong release paths")
            require(integer(evidence.get("process_id"), 1) and evidence.get("process_terminal") is True and
                    type(evidence.get("exit_code")) is int and evidence["exit_code"] == 0,
                    "Packaged process terminal not established")
        return {"state": "QUALIFIED_REFERENCED_EVIDENCE", "unit_id": unit, "adopted": False,
                "requires_owner_receipt_verification": True, "errors": []}
    except (ContractError, KeyError, TypeError, AttributeError, ValueError, RecursionError) as exc:
        return {"state": "HELD", "adopted": False, "errors": [str(exc)[:256]]}
