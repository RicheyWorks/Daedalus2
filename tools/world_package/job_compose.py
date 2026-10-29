# SPDX-License-Identifier: MIT
"""Compose verified frozen jobs without trusting mutable original selections."""

import hashlib
import os
import re

from .batch_plan import MAX_ITEMS, MAX_REQUEST_BYTES, MAX_SOURCE_BYTES, REQUEST_FORMAT, _request, build_batch, encode_batch
from .job_store import (CONTROL_LIMITS, MAX_MANIFEST_BYTES, JobError, _json, _json_bytes,
                        _manifest, _mapping, _path, _pin, _plain, _read, _selection,
                        _write, create_job, inspect_job)
from .reader_adapter import PlanError
from .replay_plan import _text

FORMAT = "daedalus-world-composite-job"
MANIFEST = "composite.json"
PENDING = "composite.pending.json"
CHILD_FILES = ("job.json", "provenance.json", "request.json", "plan.json")
MAX_LINEAGE_BYTES = 16 * 1024 * 1024


class CompositionError(JobError):
    """Selected jobs cannot publish a complete aggregate; partial evidence stays."""


def _selectors(values):
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_ITEMS:
        raise CompositionError("select an explicit array of 1 to 16 child jobs")
    result = []
    keys = set()
    for item in values:
        if not isinstance(item, dict) or set(item) != {"key", "job"}:
            raise CompositionError("each child selector requires exactly key and job")
        key = _text(item["key"], "child key", maximum=128)
        if key in keys:
            raise CompositionError("duplicate child key: " + key)
        keys.add(key)
        result.append({"key": key, "root": _path(item["job"])})
    return sorted(result, key=lambda item: item["key"])


def _frame(key, source, raw):
    pins = _manifest(_json(raw["job.json"]))
    for name in CONTROL_LIMITS:
        if _pin(name, raw[name]) != pins[name]:
            raise CompositionError(key + ": copied child control differs from its manifest: " + name)
    staged = _json(raw["request.json"])
    items, _ = _request(staged)
    mapping = _mapping(items)
    if (any(item["package"] != mapping[item["key"]] for item in items) or
            set(pins) != set(CONTROL_LIMITS) | set(mapping.values())):
        raise CompositionError(key + ": child package inventory/mapping mismatch")
    _selection(_json(raw["provenance.json"]), staged)
    return {"key": key, "source_job": source, "raw": raw, "pins": pins, "staged": staged}


def _recipe(frames):
    children, packages, receipts = [], [], {}
    for child_index, frame in enumerate(frames):
        items, _ = _request(frame["staged"])
        mappings = []
        for item_index, item in enumerate(items):
            if len(packages) >= MAX_ITEMS:
                raise CompositionError("composed package selection exceeds 16 inputs")
            key = "child-" + str(child_index).zfill(4) + "-item-" + str(item_index).zfill(4)
            path = "packages/" + str(len(packages)).zfill(4) + ".zip"
            packages.append({"key": key, "package": path})
            mappings.append({"key": item["key"], "child_package": item["package"],
                             "aggregate_key": key, "aggregate_package": path})
        for receipt in frame["staged"]["prior_receipts"]:
            world_id = receipt["world_id"]
            if world_id in receipts and receipts[world_id] != receipt:
                raise CompositionError("conflicting accepted receipts for raw world ID: " + world_id)
            receipts[world_id] = receipt
        children.append({"key": frame["key"], "source_job": frame["source_job"],
                         "control_directory": "children/" + str(child_index).zfill(4),
                         "manifest_sha256": hashlib.sha256(frame["raw"]["job.json"]).hexdigest(),
                         "items": mappings})
    lineage = {"format": "daedalus-world-composite-lineage", "version": 1, "children": children}
    request = {"format": REQUEST_FORMAT, "version": 1, "packages": packages,
               "prior_receipts": [receipts[key] for key in sorted(receipts)]}
    _request(request)
    return lineage, request


def _verify_copies(root, frames, lineage, aggregate):
    aggregate_pins = _manifest(aggregate["manifest"])
    for frame, child in zip(frames, lineage["children"]):
        for item in child["items"]:
            expected = frame["pins"][item["child_package"]]
            actual = aggregate_pins[item["aggregate_package"]]
            if any(expected[field] != actual[field] for field in ("bytes", "sha256")):
                raise CompositionError(child["key"] + ": aggregate copy differs from inspected child pin")
            _read(root / "aggregate" / item["aggregate_package"], expected["bytes"], expected=expected, keep=False)
    return aggregate_pins


def _replay_children(root, frames, lineage):
    for frame, child in zip(frames, lineage["children"]):
        mapping = {item["key"]: item for item in child["items"]}
        request = dict(frame["staged"], packages=[
            {"key": item["key"], "package": str(root / "aggregate" / item["aggregate_package"])}
            for item in child["items"]])
        plan = build_batch(request)
        if not plan["ready"]:
            errors = [item["key"] + ": " + item.get("error", item["status"])
                      for item in plan["items"] if item["status"] in ("error", "conflict")]
            raise CompositionError(child["key"] + ": retained child plan refused: " + "; ".join(errors))
        inventory = {item["reference"]: item for item in plan["inventory"]}
        for item in plan["items"]:
            relative = mapping[item["key"]]["child_package"]
            pin = frame["pins"][relative]
            record = inventory[item["reference"]]
            if record["package_sha256"] != pin["sha256"] or record["plan"]["source"]["package_bytes"] != pin["bytes"]:
                raise CompositionError(child["key"] + ": replay snapshot differs from retained child pin")
            item["package"] = relative
        if encode_batch(plan) != frame["raw"]["plan.json"]:
            raise CompositionError(child["key"] + ": retained child plan does not bind its packages/receipts")


def _limit(name):
    if name == "lineage.json":
        return MAX_REQUEST_BYTES
    if name == "aggregate/job.json":
        return MAX_MANIFEST_BYTES
    match = re.fullmatch(r"children/[0-9]{4}/(job\.json|provenance\.json|request\.json|plan\.json)", name)
    if not match:
        raise CompositionError("invalid composite pin path")
    return MAX_MANIFEST_BYTES if match[1] == "job.json" else CONTROL_LIMITS[match[1]]


def _outer_pins(manifest):
    if (not isinstance(manifest, dict) or set(manifest) != {"format", "version", "state", "files", "native_acceptance"} or
            manifest["format"] != FORMAT or type(manifest["version"]) is not int or manifest["version"] != 1 or
            manifest["state"] != "complete" or manifest["native_acceptance"] is not False or
            not isinstance(manifest["files"], list) or not 6 <= len(manifest["files"]) <= 4 * MAX_ITEMS + 2):
        raise CompositionError("unsupported or incomplete composite manifest")
    pins, directories, retained = {}, set(), 0
    for pin in manifest["files"]:
        if not isinstance(pin, dict) or set(pin) != {"path", "bytes", "sha256"}:
            raise CompositionError("invalid composite pin")
        name, size, digest = pin["path"], pin["bytes"], pin["sha256"]
        if (not isinstance(name, str) or name in pins or type(size) is not int or size < 0 or size > _limit(name) or
                not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise CompositionError("invalid/duplicate composite pin value")
        pins[name] = pin
        if name.startswith("children/"):
            retained += size
            directories.add(name.split("/")[1])
    expected_dirs = {str(index).zfill(4) for index in range(len(directories))}
    expected = {"lineage.json", "aggregate/job.json"} | {
        "children/" + directory + "/" + name for directory in expected_dirs for name in CHILD_FILES}
    if not directories or directories != expected_dirs or set(pins) != expected or retained > MAX_LINEAGE_BYTES:
        raise CompositionError("invalid composite control inventory or lineage byte budget")
    return pins, expected_dirs


def _directory(path, expected):
    _plain(path, directory=True)
    seen = set()
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.name not in expected:
                raise CompositionError("unexpected composite entry: " + str(path / entry.name))
            seen.add(entry.name)
    if seen != expected:
        raise CompositionError("missing composite entry in " + str(path))


def _failure(root, created, error):
    state = "output not created"
    if created:
        state = "unpublished composite"
        try:
            if (root / MANIFEST).exists():
                state = "publication uncertain; inspect composite.json explicitly"
            elif (root / "aggregate" / "job.json").exists():
                state += "; nested aggregate marker exists; inspect it separately"
        except OSError:
            state = "publication uncertain; cannot check composite.json"
    return CompositionError(str(root) + ": " + state + ": " + str(error))


def compose_jobs(explicit_child_jobs, fresh_output):
    """Copy verified child lineage and aggregate frozen ZIPs into a fresh container."""
    selectors, root = _selectors(explicit_child_jobs), _path(fresh_output)
    if any(root == item["root"] or item["root"] in root.parents for item in selectors):
        raise CompositionError("composite output must not be inside a selected child job")
    created = False
    try:
        root.mkdir()
        created = True
        (root / "children").mkdir()
        frames, pins, sources = [], [], []
        packages = package_bytes = retained = 0
        for item in selectors:
            source = item["root"]
            _plain(source, directory=True)
            marker = _read(source / "job.json", MAX_MANIFEST_BYTES)
            child_pins = _manifest(_json(marker))
            payloads = [pin for name, pin in child_pins.items() if name.startswith("packages/")]
            packages += len(payloads)
            package_bytes += sum(pin["bytes"] for pin in payloads)
            retained += len(marker) + sum(child_pins[name]["bytes"] for name in CONTROL_LIMITS)
            if packages > MAX_ITEMS or package_bytes > MAX_SOURCE_BYTES or retained > MAX_LINEAGE_BYTES:
                raise CompositionError("selected children exceed aggregate input/byte/lineage budgets")
            sources.append((item, marker, child_pins))
        # Reject over-budget selections from bounded manifests before opening
        # any child ZIP for deep inspection or copying child controls.
        for index, (item, marker, child_pins) in enumerate(sources):
            source = item["root"]
            inspected = inspect_job(source)
            if inspected["manifest"] != _json(marker) or _read(source / "job.json", MAX_MANIFEST_BYTES) != marker:
                raise CompositionError(item["key"] + ": child manifest changed during inspection")
            raw = {"job.json": marker}
            for name in CONTROL_LIMITS:
                raw[name] = _read(source / name, child_pins[name]["bytes"], expected=child_pins[name])
            frame = _frame(item["key"], str(source), raw)
            if encode_batch(inspected["plan"]) != raw["plan.json"]:
                raise CompositionError(item["key"] + ": child plan changed during inspection")
            directory = root / "children" / str(index).zfill(4)
            directory.mkdir()
            for name in CHILD_FILES:
                _write(directory / name, raw[name])
                pins.append(_pin("children/" + directory.name + "/" + name, raw[name]))
            frames.append(frame)
        lineage, staged = _recipe(frames)
        actual = dict(staged, packages=[
            {"key": item["aggregate_key"], "package": str(selectors[index]["root"] / item["child_package"])}
            for index, child in enumerate(lineage["children"]) for item in child["items"]])
        aggregate = create_job(actual, root / "aggregate", str(selectors[0]["root"]))
        _verify_copies(root, frames, lineage, aggregate)
        aggregate_bytes = _read(root / "aggregate" / "job.json", MAX_MANIFEST_BYTES)
        if _json(aggregate_bytes) != aggregate["manifest"]:
            raise CompositionError("aggregate manifest changed after publication")
        pins.append(_pin("aggregate/job.json", aggregate_bytes))
        data = _json_bytes(lineage, MAX_REQUEST_BYTES)
        _write(root / "lineage.json", data)
        pins.append(_pin("lineage.json", data))
        manifest = {"format": FORMAT, "version": 1, "state": "complete",
                    "files": sorted(pins, key=lambda pin: pin["path"]), "native_acceptance": False}
        _outer_pins(manifest)
        _write(root / PENDING, _json_bytes(manifest, MAX_MANIFEST_BYTES))
        os.link(root / PENDING, root / MANIFEST)
        return {"manifest": manifest, "aggregate": aggregate, "lineage": lineage, "native_acceptance": False}
    except (OSError, PlanError, UnicodeError) as error:
        raise _failure(root, created, error) from error


def inspect_composite_job(job_directory):
    """Rebuild aggregate/child contracts using copied controls and aggregate ZIPs only."""
    root = _path(job_directory)
    try:
        _plain(root, directory=True)
        marker = _read(root / MANIFEST, MAX_MANIFEST_BYTES)
        manifest = _json(marker)
        pins, directories = _outer_pins(manifest)
        _directory(root, {MANIFEST, PENDING, "lineage.json", "children", "aggregate"})
        _directory(root / "children", directories)
        _plain(root / "aggregate", directory=True)
        for directory in directories:
            _directory(root / "children" / directory, set(CHILD_FILES))
        if _read(root / PENDING, MAX_MANIFEST_BYTES) != marker:
            raise CompositionError("published/pending composite manifests disagree")
        controls = {}
        for name, pin in pins.items():
            if name == "aggregate/job.json":
                data = _read(root / name, MAX_MANIFEST_BYTES)
                if _pin(name, data) != pin:
                    raise CompositionError("aggregate manifest pin mismatch")
            else:
                data = _read(root / name, pin["bytes"], expected=pin)
            controls[name] = data
        lineage = _json(controls["lineage.json"])
        if (not isinstance(lineage, dict) or set(lineage) != {"format", "version", "children"} or
                lineage["format"] != "daedalus-world-composite-lineage" or
                type(lineage["version"]) is not int or lineage["version"] != 1 or
                not isinstance(lineage["children"], list) or len(lineage["children"]) != len(directories)):
            raise CompositionError("invalid copied child lineage")
        frames, keys = [], []
        for index, child in enumerate(lineage["children"]):
            if (not isinstance(child, dict) or
                    set(child) != {"key", "source_job", "control_directory", "manifest_sha256", "items"}):
                raise CompositionError("invalid child lineage record")
            key = _text(child["key"], "retained child key", maximum=128)
            source = _text(child["source_job"], "retained source job", maximum=4096)
            directory = "children/" + str(index).zfill(4)
            if child["control_directory"] != directory:
                raise CompositionError("child control directory mapping mismatch")
            frames.append(_frame(key, source, {name: controls[directory + "/" + name] for name in CHILD_FILES}))
            keys.append(key)
        if keys != sorted(set(keys)):
            raise CompositionError("child keys must be unique and deterministically ordered")
        expected_lineage, expected_request = _recipe(frames)
        if lineage != expected_lineage:
            raise CompositionError("retained child manifest/key lineage mismatch")
        aggregate = inspect_job(root / "aggregate")
        if aggregate["manifest"] != _json(controls["aggregate/job.json"]):
            raise CompositionError("aggregate inspection differs from pinned manifest")
        aggregate_pins = _verify_copies(root, frames, lineage, aggregate)
        request_bytes = _read(root / "aggregate" / "request.json", aggregate_pins["request.json"]["bytes"],
                              expected=aggregate_pins["request.json"])
        if _json(request_bytes) != expected_request:
            raise CompositionError("aggregate request does not bind the retained keys/receipt union")
        _replay_children(root, frames, lineage)
        return {"manifest": manifest, "aggregate": aggregate, "lineage": lineage, "native_acceptance": False}
    except (OSError, PlanError, UnicodeError) as error:
        raise CompositionError(str(root) + ": cannot inspect composite: " + str(error)) from error
