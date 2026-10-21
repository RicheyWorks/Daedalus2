"""Explicitly invoked, bounded read-only Unreal facts for the existing four units.

No Unreal import at module import; no transport, generation, saves, builders,
spawning, editor commands, plugin changes or filesystem writes. Ordinary asset
loads require an explicit finite list of exact configured, source-pinned assets.
The sole operator retains custody and before/after preservation checks.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import finishline_target_policy as policy_module
from finishline_target_policy import (BUILD_FIELDS, FACTS_SCHEMA, MAX_BYTES, MAX_LEVELS, MAX_LODS,
                                     canonical, fingerprint, require, sha, text,
                                     validate_contract, package_expectations, parse_json)


def _file_pin(path, maximum=65536):
    p = Path(path)
    before = p.stat()
    require(before.st_size <= maximum, "Small source file exceeds limit")
    with p.open("rb") as stream:
        raw = stream.read(maximum + 1)
    after = p.stat()
    require(len(raw) <= maximum and before.st_size == after.st_size == len(raw) and
            before.st_mtime_ns == after.st_mtime_ns, "Source changed while read")
    return hashlib.sha256(raw).hexdigest()


def _id(obj):
    require(obj is not None, "Object unavailable")
    return {"object_path": obj.get_path_name(), "class_path": obj.get_class().get_path_name()}


def collect(config, capture_id, expected_reader_sha256, expected_policy_sha256, *,
            observation=None, exact_asset_loads=(), streaming_packages=(),
            unreal_module=None, file_reader=None):
    """Return a serializable facts envelope; actual native invocation is operator-only.

    Injection supports tiny offline tests; it is not a new runtime authority.
    The caller must admit exact source and config pins through the existing lane.
    """
    config = parse_json(canonical(config))
    validate_contract(config)
    if observation is None:
        observation = {"phase": "preflight", "unit_id": None,
                       "operation_id": None, "package_overrides": {}}
    observation = parse_json(canonical(observation))
    packages = package_expectations(config, observation)
    require(type(exact_asset_loads) in (list, tuple) and
            type(streaming_packages) in (list, tuple), "Finite explicit read requests required")
    require(all(type(x) is str for x in exact_asset_loads) and len(exact_asset_loads) <= 10 and
            len(set(exact_asset_loads)) == len(exact_asset_loads),
            "Invalid exact asset load request count")
    loadable = {x["object_path"]: packages[x["id"]] for x in config["meshes"]}
    loadable[config["pcg"]["graph_path"]] = packages["pcg_graph"]
    hc = config["hlod"]
    if hc.get("layer_path") and hc.get("layer_file_sha256"):
        require(sha(hc["layer_file_sha256"]), "Missing admitted layer file pin")
        loadable[hc["layer_path"]] = hc["layer_file_sha256"]
    require(all(type(x) is str and x in loadable for x in exact_asset_loads),
            "Asset loads must name exact configured source-pinned assets")
    require(all(type(x) is str for x in streaming_packages) and len(streaming_packages) <= MAX_LEVELS and
            len(set(streaming_packages)) == len(streaming_packages) and
            all(type(x) is str and policy_module.path(x) and x.startswith("/Game/") and
                "." not in x and ":" not in x for x in streaming_packages),
            "Streaming lookup requires finite exact full package names")
    request = parse_json(canonical({"exact_asset_loads": list(exact_asset_loads),
                                   "streaming_packages": list(streaming_packages)}))
    require(text(capture_id) and sha(expected_reader_sha256) and sha(expected_policy_sha256),
            "Missing admitted capture/source identity")
    actual_reader = _file_pin(__file__, MAX_BYTES)
    actual_policy = _file_pin(policy_module.__file__, MAX_BYTES)
    require(actual_reader == expected_reader_sha256, "Admitted reader source mismatch")
    require(actual_policy == expected_policy_sha256, "Admitted policy source mismatch")
    if unreal_module is None:
        import unreal as unreal_module
    ue = unreal_module
    read_file = file_reader or _file_pin
    errors = []
    load_events = []

    def observed(label, fn):
        try:
            value = fn()
            canonical(value)
            return value
        except Exception as exc:
            # No default values and no exception payloads/private object dumps.
            errors.append({"field": label, "reason": type(exc).__name__})
            return None

    def find(target):
        obj = ue.find_object(None, target["object_path"])
        if obj is None and target["object_path"] in request["exact_asset_loads"]:
            expected_pin = loadable[target["object_path"]]
            asset_source_pin(target["object_path"], expected_pin)
            event = {"object_path": target["object_path"], "source_sha256": expected_pin,
                     "state": "ATTEMPTED"}
            load_events.append(event)
            obj = ue.load_asset(target["object_path"])
            event["state"] = "RETURNED"
            event["identity"] = _id(obj)
        record = _id(obj)
        require(record == {"object_path": target["object_path"], "class_path": target["class_path"]},
                "Exact loaded object/class mismatch")
        return obj

    def asset_source_pin(object_path, expected_sha):
        require(object_path.startswith("/Game/") and ":" not in object_path,
                "Only admitted project assets have source files")
        package = object_path.split(".", 1)[0][len("/Game/"):]
        p = Path(config["release"]["project_file"]).parent / "Content" / (package + ".uasset")
        actual = read_file(str(p), 33554432)
        require(actual == expected_sha, "Current asset file pin changed")
        return actual

    try:
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        world_info = dict(_id(world), state="OBSERVED")
        canonical(world_info)
    except Exception as exc:
        world = None
        world_info = {"state": "UNKNOWN"}
        errors.append({"field": "world.identity", "reason": type(exc).__name__})
    if world is None:
        return {"schema": FACTS_SCHEMA, "contract_sha256": fingerprint(config), "capture_id": capture_id,
                "reader_sha256": actual_reader, "policy_sha256": actual_policy, "world": world_info,
                "observation": observation, "read_request": request,
                "read_request_sha256": fingerprint(request), "asset_load_events": load_events,
                "meshes": [{"id": x["id"], "state": "UNKNOWN"} for x in config["meshes"]],
                "pcg": {"graph": {"state": "UNKNOWN"}, "component": {"state": "UNKNOWN"}},
                "hlod": {"state": "UNKNOWN"}, "release": {"state": "UNKNOWN"}, "errors": errors}

    def owning_world(obj):
        # UObject outer identity is available to Python; do not assume a plain-C++
        # AActor/UWorld GetWorld override is a reflected script method.
        seen = set()
        for _ in range(16):
            require(obj is not None, "World outer unavailable")
            ident = _id(obj)
            require(ident["object_path"] not in seen, "Outer cycle")
            seen.add(ident["object_path"])
            if ident["class_path"] == config["world"]["class_path"]:
                return ident["object_path"]
            obj = obj.get_outer()
        raise RuntimeError("World outer depth exceeds bound")
    if world is not None:
        expected = config["world"]
        require(world_info["object_path"] == expected["object_path"] and
                world_info["class_path"] == expected["class_path"], "Refuse a different current realm/world")
        def partitioned():
            # World.h GetWorldPartition is NOT a UFUNCTION. Use reflected WorldSettings property.
            settings = world.get_world_settings()
            return settings.get_editor_property("world_partition") is not None
        world_info["partitioned"] = observed("world.partitioned", partitioned)
        def loaded_level_names():
            # Reflected EditorLevelUtils.GetLevels returns loaded ULevels, including
            # persistent. It is not UWorld's private configured StreamingLevels array.
            levels = ue.EditorLevelUtils.get_levels(world)
            require(len(levels) <= MAX_LEVELS, "Loaded level count exceeds bound")
            names = [o.get_path_name() for o in levels if o is not None]
            require(len(names) == len(levels) and len(set(names)) == len(names), "Unknown/duplicate loaded level")
            return sorted(names)
        world_info["loaded_level_objects"] = observed("world.loaded_levels", loaded_level_names)
        world_info["loaded_level_scope"] = "Loaded ULevels only, including persistent; not configured streaming inventory"
        world_info["streaming_level_objects"] = None
        world_info["streaming_level_scope"] = "Explicit admitted package subset; never a complete configured count"
        world_info["streaming_level_reason"] = "No exact package names admitted; private StreamingLevels is not read"
        if request["streaming_packages"]:
            def streaming_names():
                names = []
                for package in request["streaming_packages"]:
                    level = ue.GameplayStatics.get_streaming_level(world, package)
                    require(level is not None, "Admitted streaming package unavailable")
                    # GetStreamingLevel uses suffix matching; verify the full returned package.
                    require(str(level.get_world_asset_package_f_name()) == package,
                            "Streaming package identity differs from admitted full name")
                    require(owning_world(level) == config["world"]["object_path"], "Streaming world mismatch")
                    names.append(level.get_path_name())
                require(len(set(names)) == len(names), "Duplicate streaming object projection")
                return sorted(names)
            world_info["streaming_level_objects"] = observed("world.streaming_levels", streaming_names)
            world_info["streaming_level_reason"] = "Source-backed explicit-name lookup; full package/world checked"
    meshes = []
    for target in config["meshes"]:
        def mesh_read(target=target):
            mesh = find(target)
            subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
            count = subsystem.get_lod_count(mesh)
            require(type(count) is int and 1 <= count <= MAX_LODS, "Unbounded/empty LOD count")
            screens = list(subsystem.get_lod_screen_sizes(mesh))
            require(len(screens) == count, "Screen-size count differs from LOD count")
            lods = []
            for index in range(count):
                settings = subsystem.get_lod_build_settings(mesh, index)
                values = {name: settings.get_editor_property(name) for name in BUILD_FIELDS}
                require(all(type(x) is bool for x in values.values()), "Unknown build flag")
                lods.append({"index": index, "triangles": mesh.get_num_triangles(index),
                             "vertices": mesh.get_num_vertices(index), "screen_size": screens[index],
                             "build_settings": values})
            return dict(_id(mesh), id=target["id"], state="OBSERVED", lods=lods,
                        asset_file_sha256=asset_source_pin(target["object_path"], packages[target["id"]]),
                        source_pin_scope="Read-only file hash and loaded-object identity; not authority attestation")
        row = observed("mesh." + target["id"], mesh_read)
        meshes.append(row or {"id": target["id"], "state": "UNKNOWN"})
    pcg_config = config["pcg"]
    def graph_read():
        obj = find({"object_path": pcg_config["graph_path"], "class_path": pcg_config["graph_class"]})
        return dict(_id(obj), state="OBSERVED", asset_file_sha256=asset_source_pin(
                    pcg_config["graph_path"], packages["pcg_graph"]),
                    source_pin_scope="Read-only file hash and loaded identity; not authority attestation")
    graph = observed("pcg.graph", graph_read) or {"state": "UNKNOWN"}
    component = {"state": "UNKNOWN", "reason": "Exact component path not yet bound"}
    if pcg_config["component_path"] is not None:
        def component_read():
            obj = find({"object_path": pcg_config["component_path"], "class_path": pcg_config["component_class"]})
            owner = obj.get_owner()
            return dict(_id(obj), state="OBSERVED", world_path=owning_world(owner),
                        graph_path=obj.get_graph().get_path_name(), seed=obj.get_editor_property("seed"),
                        graph_instance_path=observed("pcg.graph_instance", lambda:
                            obj.get_editor_property("graph_instance").get_path_name()),
                        raw_generated_flag=observed("pcg.generated_flag", lambda:
                            obj.get_editor_property("generated")),
                        generated_flag_limit="False can be normal for partitionable actors; not completion proof")
        component = observed("pcg.component", component_read) or {"state": "UNKNOWN"}
    # Enumeration/build of HLOD clusters is outside this reader. Actor references
    # must already exist in the current world; layer asset loads require an exact pin.
    hlod = {"state": "UNKNOWN", "reason": "Exact finite source set/layer not yet bound"}
    hc = config["hlod"]
    if hc["source_actor_paths"] and hc["layer_path"]:
        def hlod_read():
            for object_path in hc["source_actor_paths"]:
                obj = ue.find_object(None, object_path)
                require(_id(obj) == {"object_path": object_path,
                                    "class_path": hc["source_actor_classes"][object_path]},
                        "HLOD source identity mismatch")
                require(owning_world(obj) == config["world"]["object_path"], "HLOD source world mismatch")
            layer = find({"object_path": hc["layer_path"], "class_path": hc["layer_class"]})
            require(_id(layer) == {"object_path": hc["layer_path"], "class_path": hc["layer_class"]},
                    "HLOD layer identity mismatch")
            layer_pin = (asset_source_pin(hc["layer_path"], hc["layer_file_sha256"])
                         if hc.get("layer_file_sha256") else None)
            return {"state": "OBSERVED", "world_path": config["world"]["object_path"],
                    "source_actor_paths": list(hc["source_actor_paths"]), "layer_path": hc["layer_path"],
                    "source_actor_classes": dict(hc["source_actor_classes"]),
                    "layer_class": layer.get_class().get_path_name(), "layer_file_sha256": layer_pin,
                    "builder_invoked": False}
        hlod = observed("hlod.targets", hlod_read) or {"state": "UNKNOWN"}
    def release_read():
        value = dict(config["release"])
        require(read_file(value["project_file"]) == value["project_file_sha256"], "Current project pin changed")
        value["state"] = "OBSERVED"
        value["packaging_or_launch_invoked"] = False
        return value
    release = observed("release.project", release_read) or {"state": "UNKNOWN"}
    result = {"schema": FACTS_SCHEMA, "contract_sha256": fingerprint(config), "capture_id": capture_id,
              "reader_sha256": actual_reader, "policy_sha256": actual_policy,
              "observation": observation, "read_request": request,
              "read_request_sha256": fingerprint(request), "asset_load_events": load_events,
              "world": world_info, "meshes": meshes,
              "pcg": {"graph": graph, "component": component}, "hlod": hlod,
              "release": release, "errors": errors}
    canonical(result)  # Refuse an oversized/nonfinite result; never truncate success.
    return result
