"""Pure JSON qualification of one unsaved worker skeletal-import readback.

This validates supplied evidence only. Namespace freshness, actual UObject reads,
and the absence of engine side effects must be established by the caller.
"""

import math


CLIP_NAMES = frozenset({"Idle", "Walk", "Attack", "Hurt", "Mine", "Trade", "Repair"})
CLIP_LENGTH_TOLERANCE_S = 1.0 / 30.0 + 0.0001
ALLOWED_CLASSES = frozenset(
    {"SkeletalMesh", "Skeleton", "AnimSequence", "MaterialInstanceConstant", "Material", "PhysicsAsset"}
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _dict(value, label):
    _require(isinstance(value, dict), label + " must be an object")
    return value


def _list(value, label):
    _require(isinstance(value, list), label + " must be a list")
    return value


def _name(value, label):
    _require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
             label + " must be a nonempty trimmed string")
    return value


def _positive_number(value, label):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             label + " must be a finite positive number")
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError(label + " must be a finite positive number") from None
    _require(math.isfinite(number) and number > 0, label + " must be a finite positive number")
    return number


def _path(value, label):
    value = _name(value, label)
    _require(value.startswith("/Game/") and "\\" not in value,
             label + " must be a /Game object or package path")
    _require(not any(ord(c) < 32 for c in value), label + " contains a control character")
    _require(all(part and part not in {".", ".."} for part in value.split("/")[1:]),
             label + " must not contain empty or relative path segments")
    return value


def _owned_path(value, root, label):
    value = _path(value, label)
    _require(value.startswith(root + "/"), label + " is outside the expected namespace")
    return value


def _expected_bones(value):
    rows = _list(value, "expected.bones")
    _require(len(rows) == 14, "expected.bones must contain exactly 14 bones")
    by_source = {}
    native_names = set()
    folded_names = set()
    for index, row in enumerate(rows):
        row = _dict(row, "expected.bones[%d]" % index)
        source = _name(row.get("source_name"), "expected bone source_name")
        native = _name(row.get("native_name"), "expected bone native_name")
        _require(source not in by_source, "expected bone source_name is duplicated")
        _require(native.casefold() not in folded_names, "expected bone native_name is duplicated")
        _require("parent" in row, "expected bone parent is missing")
        parent = row["parent"]
        if parent is not None:
            _name(parent, "expected bone parent")
        by_source[source] = {"native_name": native, "parent": parent}
        native_names.add(native)
        folded_names.add(native.casefold())
    roots = [row["native_name"] for row in by_source.values() if row["parent"] is None]
    _require(len(roots) == 1, "expected bones must have exactly one root with parent None")
    parents = {row["native_name"]: row["parent"] for row in by_source.values()}
    for parent in parents.values():
        _require(parent is None or parent in native_names, "expected bone parent is unknown")
    for native in parents:
        visited = set()
        cursor = native
        while cursor is not None:
            _require(cursor not in visited, "expected bone hierarchy contains a cycle")
            visited.add(cursor)
            cursor = parents[cursor]
    return by_source


def qualify(expected, observed):
    """Return a compact qualified mapping, or raise ValueError on any mismatch.

    Inputs contain JSON dictionaries/lists/scalars. The seven required clip names
    and fourteen-bone tree describe the pinned producer packet. No engine module,
    filesystem, network, process, or asset operation is performed here.
    """
    expected = _dict(expected, "expected")
    observed = _dict(observed, "observed")
    asset_id = _name(expected.get("asset_id"), "expected.asset_id")
    root = _path(expected.get("root"), "expected.root")
    _require("." not in root.rsplit("/", 1)[-1], "expected.root must be a package namespace")
    expected_clips = _dict(expected.get("clips"), "expected.clips")
    _require(set(expected_clips) == CLIP_NAMES, "expected.clips must contain exactly the seven worker clips")
    spans = {
        name: _positive_number(_dict(row, "expected clip").get("span_s"), "expected clip span_s")
        for name, row in expected_clips.items()
    }
    bones = _expected_bones(expected.get("bones"))
    saved_files = _list(observed.get("saved_files"), "observed.saved_files")
    _require(not saved_files, "observed.saved_files must be empty")

    objects = _list(observed.get("objects"), "observed.objects")
    paths_by_class = {name: [] for name in ALLOWED_CLASSES}
    paths_seen = set()
    for index, row in enumerate(objects):
        row = _dict(row, "observed.objects[%d]" % index)
        path = _owned_path(row.get("path"), root, "observed object path")
        _require(path.casefold() not in paths_seen, "observed object path is duplicated")
        paths_seen.add(path.casefold())
        class_name = _name(row.get("class"), "observed object class")
        _require(class_name in ALLOWED_CLASSES, "observed object class is not allowed")
        paths_by_class[class_name].append(path)
    _require(len(paths_by_class["SkeletalMesh"]) == 1, "exactly one SkeletalMesh is required")
    _require(len(paths_by_class["Skeleton"]) == 1, "exactly one Skeleton is required")
    _require(len(paths_by_class["AnimSequence"]) == 7, "exactly seven AnimSequences are required")
    _require(len(paths_by_class["PhysicsAsset"]) <= 1, "at most one PhysicsAsset is allowed")
    mesh = _owned_path(observed.get("mesh_path"), root, "observed.mesh_path")
    skeleton = _owned_path(observed.get("skeleton_path"), root, "observed.skeleton_path")
    _require(paths_by_class["SkeletalMesh"] == [mesh], "mesh_path does not identify the SkeletalMesh")
    _require(paths_by_class["Skeleton"] == [skeleton], "skeleton_path does not identify the Skeleton")
    _require(observed.get("mesh_skeleton_path") == skeleton, "mesh references a different Skeleton")

    clip_rows = _list(observed.get("clips"), "observed.clips")
    _require(len(clip_rows) == 7, "observed.clips must contain exactly seven clips")
    clip_paths = {}
    used_clip_paths = set()
    for row in clip_rows:
        row = _dict(row, "observed clip")
        source = _name(row.get("source_name"), "observed clip source_name")
        _require(source in spans, "observed clip source_name is not expected")
        _require(source not in clip_paths, "observed clip source_name is duplicated")
        path = _owned_path(row.get("path"), root, "observed clip path")
        _require(path not in used_clip_paths, "observed clip path is duplicated")
        _require(row.get("skeleton_path") == skeleton, "clip references a different Skeleton")
        length = _positive_number(row.get("length_s"), "observed clip length_s")
        _require(abs(length - spans[source]) <= CLIP_LENGTH_TOLERANCE_S,
                 "observed clip length differs from source span beyond one frame")
        used_clip_paths.add(path)
        clip_paths[source] = path
    _require(used_clip_paths == set(paths_by_class["AnimSequence"]),
             "clip paths do not exactly identify the imported AnimSequences")

    bone_rows = _list(observed.get("bones"), "observed.bones")
    _require(len(bone_rows) == 14, "observed.bones must contain exactly 14 bones")
    bone_map = {}
    for row in bone_rows:
        row = _dict(row, "observed bone")
        source = _name(row.get("source_name"), "observed bone source_name")
        _require(source in bones, "observed bone source_name is not expected")
        _require(source not in bone_map, "observed bone source_name is duplicated")
        native = _name(row.get("native_name"), "observed bone native_name")
        _require(native == bones[source]["native_name"], "observed bone native_name is misbound")
        _require("parent" in row and row["parent"] == bones[source]["parent"],
                 "observed bone parent is misbound")
        _require(row.get("exists_in_all_clips") is True, "bone is not present in every clip")
        bone_map[source] = native
    _require(set(bone_map) == set(bones), "observed bones do not cover the expected source bones")

    return {
        "asset_id": asset_id,
        "root": root,
        "mesh_path": mesh,
        "skeleton_path": skeleton,
        "clips": dict(sorted(clip_paths.items())),
        "bones": dict(sorted(bone_map.items())),
        "physics_asset_path": next(iter(paths_by_class["PhysicsAsset"]), None),
        "material_paths": sorted(paths_by_class["Material"] + paths_by_class["MaterialInstanceConstant"]),
    }
