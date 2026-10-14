# SPDX-License-Identifier: MIT
"""Prepare a bounded retained candidate manifest without invoking an importer.

Keep the full original 24-entry batch and its importer source/options/material.
Replace only the original summit/HeroR3 or CopperPatina coupler/PowerUnit entry,
preserve every other entry's JSON
bytes, and bind the replacement to the retained FBX's actual bytes. This grants
no editor ownership, import/admission approval, or world-placement authority.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ORIGINAL = "CodexIsland_summit_rim_84011"
REVISION = ORIGINAL + "_HeroR3"
SALVAGE_ORIGINAL = "CodexModule_CopperPatina_BridgeCoupler_85000"
SALVAGE_REVISION = "CodexSalvage_PowerUnit_86100"
DEST = "/Game/Daedalus/Art/Islands/CodexContest/Prepared/"
DECODER = json.JSONDecoder()


def fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _space(text, position):
    while position < len(text) and text[position] in " \t\r\n":
        position += 1
    return position


def _members(text):
    """Locate top-level JSON value spans without rewriting unrelated bytes."""
    position = _space(text, 0)
    if text[position] != "{":
        raise ValueError("manifest must be a JSON object")
    position, members = _space(text, position + 1), {}
    while text[position] != "}":
        key, position = DECODER.raw_decode(text, position)
        position = _space(text, position)
        if not isinstance(key, str) or key in members or text[position] != ":":
            raise ValueError("duplicate/invalid top-level manifest member")
        start = _space(text, position + 1)
        value, end = DECODER.raw_decode(text, start)
        members[key] = (start, end, value)
        position = _space(text, end)
        if text[position] == "}":
            break
        if text[position] != ",":
            raise ValueError("invalid manifest member separator")
        position = _space(text, position + 1)
    if _space(text, position + 1) != len(text):
        raise ValueError("unexpected data after manifest")
    return members


def _entries(text, start):
    if text[start] != "[":
        raise ValueError("assets must be a JSON array")
    position, spans = _space(text, start + 1), []
    while text[position] != "]":
        value, end = DECODER.raw_decode(text, position)
        spans.append((position, end, value))
        position = _space(text, end)
        if text[position] == "]":
            break
        if text[position] != ",":
            raise ValueError("invalid asset separator")
        position = _space(text, position + 1)
    return spans


def prepare(original_manifest_path, revision_receipt_path, output_path, replace_name=ORIGINAL):
    """Write a new 24-entry candidate; never change inputs or existing output."""
    original_path, receipt_path, output_path = (Path(path).resolve() for path in
                                               (original_manifest_path, revision_receipt_path, output_path))
    raw = original_path.read_bytes()
    text = raw.decode("utf-8")
    original = json.loads(text)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    members = _members(text)
    entries = _entries(text, members["assets"][0])
    if original.get("schema") != "daedalus.codex-prepared-delivery.v1" or len(entries) != 24:
        raise ValueError("require the full original prepared 24-entry manifest")
    if original.get("prepared_groups") != 24 or original.get("islands") != 3 or original.get("modules") != 21:
        raise ValueError("original batch summary differs; no count guard is changed")
    if len({entry["name"] for _, _, entry in entries}) != 24:
        raise ValueError("original asset identities are duplicated")
    if replace_name == ORIGINAL:
        kind, schema, revision, object_count = "island", "daedalus.codex-island.v1", REVISION, 10
    elif replace_name == SALVAGE_ORIGINAL:
        kind, schema, revision, object_count = "module", "daedalus.codex-salvage-assembly.v1", SALVAGE_REVISION, 5
    else:
        raise ValueError("only the exact original summit or CopperPatina BridgeCoupler may be replaced")
    targets = [(index, span) for index, span in enumerate(entries) if span[2]["name"] == replace_name]
    if len(targets) != 1 or targets[0][1][2].get("kind") != kind:
        raise ValueError("exact original replacement entry is absent, ambiguous or a different kind")
    index, (start, end, old_entry) = targets[0]
    config = receipt.get("config", {})
    if receipt.get("schema") != schema or receipt.get("stage") != "exported" or receipt.get("name") != revision:
        raise ValueError("require the exact exported retained candidate receipt")
    if kind == "island":
        if config.get("preset") != "summit-rim" or config.get("revision") != "HeroR3" or config.get("seed") != 84011:
            raise ValueError("receipt is not the retained summit seed84011 HeroR3 revision")
    elif config.get("assembly") != "PowerUnit" or config.get("preset") != "CopperPatina" or config.get("seed") != 86100:
        raise ValueError("receipt is not the retained CopperPatina PowerUnit seed86100 assembly")
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    if receipt.get("config_sha256") != config_sha:
        raise ValueError("receipt config hash differs")
    objects = receipt.get("blender", {}).get("objects", [])
    if len(objects) != object_count or len({row["name"] for row in objects}) != object_count:
        raise ValueError("retained candidate has a differing source-object count or duplicate identity")
    if kind == "module" and {row["name"] for row in objects} != {
            SALVAGE_REVISION + "_" + role for role in ("gearbox", "shaft", "rotor", "battery", "support")}:
        raise ValueError("PowerUnit source object roles differ from the exact retained assembly")
    for row in objects:
        dims = row.get("dims", [])
        if not row["name"].startswith(revision + "_") or len(dims) != 3 or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
                for value in dims):
            raise ValueError("revision source object has invalid identity or dimensions")
    fbx = receipt["artifacts"]["fbx"]
    fbx_path = Path(fbx["path"]).resolve()
    actual = fingerprint(fbx_path)
    if actual != fbx["fingerprint"]:
        raise ValueError("retained candidate FBX bytes differ from the export receipt")
    if output_path in (original_path, receipt_path, fbx_path) or output_path == Path(receipt["artifacts"]["glb"]["path"]).resolve():
        raise ValueError("new manifest must not overwrite an input or exported payload")
    replacement = copy.deepcopy(old_entry)
    replacement.update(name=receipt["name"], config_sha256=config_sha, seed=config["seed"],
                       objects=copy.deepcopy(objects), fbx=dict(path=fbx["path"], **actual),
                       destination=DEST + kind + "/" + actual["sha256"][:16])
    mesh_count = sum(len(entry["objects"]) for _, _, entry in entries)
    if mesh_count != original.get("expected_meshes"):
        raise ValueError("original expected mesh metadata differs from its object records")
    expected_meshes = mesh_count - len(old_entry["objects"]) + len(objects)
    # Only the replacement object and its derived mesh-count metadata change.
    # Entry indentation and the original line-ending style are retained.
    line_start = text.rfind("\n", 0, start) + 1
    indent = text[line_start:start]
    indent = indent if indent.strip() == "" else ""
    newline = "\r\n" if "\r\n" in text else "\n"
    encoded_entry = json.dumps(replacement, indent=2, sort_keys=True).replace("\n", newline + indent)
    count_start, count_end, _ = members["expected_meshes"]
    updated = text
    for low, high, value in sorted(((start, end, encoded_entry), (count_start, count_end, str(expected_meshes))), reverse=True):
        updated = updated[:low] + value + updated[high:]
    clone = json.loads(updated)
    clone_members = _members(updated)
    clone_entries = _entries(updated, clone_members["assets"][0])
    for position, ((old_start, old_end, old), (new_start, new_end, new)) in enumerate(zip(entries, clone_entries)):
        if position != index and (old != new or text[old_start:old_end] != updated[new_start:new_end]):
            raise RuntimeError("unchanged asset entry JSON bytes differ")
    if len(clone_entries) != 24 or any(clone[key] != value for key, value in original.items() if key not in ("assets", "expected_meshes")):
        raise RuntimeError("clone changed importer source, options, material or batch metadata")
    payload = updated.encode("utf-8")
    # Recheck input and FBX bytes immediately before writing the new manifest.
    if original_path.read_bytes() != raw or fingerprint(fbx_path) != actual:
        raise RuntimeError("original manifest or retained FBX changed during preparation")
    if output_path.exists():
        if output_path.read_bytes() != payload:
            raise ValueError("output already exists with differing bytes; choose a new immutable path")
        created = False
    else:
        with output_path.open("xb") as output:
            output.write(payload)
        created = True
    return {"original_manifest": str(original_path), "original_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "revision_receipt": str(receipt_path), "replacement": receipt["name"], "fbx": dict(path=str(fbx_path), **actual),
            "destination": replacement["destination"], "output_manifest": str(output_path),
            "output_sha256": hashlib.sha256(payload).hexdigest(), "created": created,
            "entries": 24, "unchanged_entry_json_spans": 23, "expected_meshes": expected_meshes,
            "importer_source": clone["source"], "importer_source_sha256": clone["source_sha256"],
            "stage": "candidate_manifest_prepared; owner approval and guarded import remain pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_manifest", type=Path)
    parser.add_argument("revision_receipt", type=Path)
    parser.add_argument("output_manifest", type=Path)
    parser.add_argument("--replace", dest="replace_name", choices=(ORIGINAL, SALVAGE_ORIGINAL), default=ORIGINAL,
                        help="exact original entry to replace; default retains the HeroR3 summit contract")
    args = parser.parse_args()
    print(json.dumps(prepare(args.original_manifest, args.revision_receipt, args.output_manifest, args.replace_name), indent=2))


if __name__ == "__main__":
    main()
