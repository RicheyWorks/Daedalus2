# SPDX-License-Identifier: MIT
"""Frozen whole-ZIP handoffs; no extraction, native import or original-path replay."""

import hashlib
import os
from pathlib import Path
import re
import stat

from .batch_plan import (MAX_ITEMS, MAX_OUTPUT_BYTES, MAX_REQUEST_BYTES, MAX_SOURCE_BYTES,
                         _local_path, _request, build_batch, encode_batch)
from .reader_adapter import MAX_PACKAGE_BYTES, PlanError, strict_json
from .replay_plan import _text

FORMAT = "daedalus-world-frozen-job"
MANIFEST = "job.json"
PENDING = "job.pending.json"
CHUNK_BYTES = 65536
MAX_MANIFEST_BYTES = 65536
CONTROL_LIMITS = {"provenance.json": 2 * MAX_REQUEST_BYTES,
                  "request.json": MAX_REQUEST_BYTES, "plan.json": MAX_OUTPUT_BYTES}


class JobError(PlanError):
    """A job refused; partial files and any uncertain publication are preserved."""


def _json_bytes(value, limit):
    data = encode_batch(value)
    if len(data) > limit:
        raise JobError("job JSON exceeds its byte limit")
    return data


def _json(data):
    return strict_json(data.decode("utf-8"))


def _path(value):
    try:
        raw = os.fspath(value)
    except TypeError as error:
        raise JobError("job paths must be explicit text or PathLike values") from error
    return Path(os.path.abspath(_local_path(raw)))


def _plain(path, directory=False, data_file=False):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400 or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or
            (data_file and info.st_nlink != 1)):
        raise JobError(str(path) + ": expected a plain local " + ("directory" if directory else "file"))
    return info


def _write(path, data):
    with path.open("xb") as stream:
        if stream.write(data) != len(data):
            raise OSError("short write: " + str(path))
        stream.flush()
        os.fsync(stream.fileno())


def _copy(source, target):
    _plain(source)
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode):
            raise JobError(str(source) + ": source is not a regular file")
        while True:
            block = incoming.read(min(CHUNK_BYTES, MAX_PACKAGE_BYTES - size + 1))
            if not block:
                break
            size += len(block)
            if size > MAX_PACKAGE_BYTES:
                raise JobError(str(source) + ": package exceeds frozen input byte limit")
            if outgoing.write(block) != len(block):
                raise OSError("short package copy: " + str(target))
            digest.update(block)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    return {"path": target.parent.name + "/" + target.name, "bytes": size,
            "sha256": digest.hexdigest()}


def _pin(name, data):
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _read(path, limit, expected=None, keep=True):
    _plain(path, data_file=expected is not None)
    digest = hashlib.sha256()
    chunks = []
    size = 0
    with path.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise JobError(str(path) + ": not a regular file")
        while True:
            block = stream.read(min(CHUNK_BYTES, limit - size + 1))
            if not block:
                break
            size += len(block)
            if size > limit:
                raise JobError(str(path) + ": pinned file exceeds byte limit")
            digest.update(block)
            if keep:
                chunks.append(block)
    if expected is not None and (size != expected["bytes"] or digest.hexdigest() != expected["sha256"]):
        raise JobError(str(path) + ": pinned size/hash mismatch")
    return b"".join(chunks)


def _mapping(items):
    return {item["key"]: "packages/" + str(index).zfill(4) + ".zip"
            for index, item in enumerate(items)}


def _batch(root, request, pins):
    items, _ = _request(request)
    mapping = _mapping(items)
    if any(item["package"] != mapping[item["key"]] for item in items):
        raise JobError("staged request has an unexpected package mapping")
    absolute = dict(request, packages=[dict(item, package=str(root / item["package"])) for item in items])
    result = build_batch(absolute)
    if not result["ready"]:
        errors = [item["key"] + ": " + item.get("error", item["status"])
                  for item in result["items"] if item["status"] in ("error", "conflict")]
        raise JobError("frozen batch refused: " + "; ".join(errors))
    inventory = {item["reference"]: item for item in result["inventory"]}
    for item in result["items"]:
        relative = mapping[item["key"]]
        pin = pins[relative]
        record = inventory[item["reference"]]
        if (record["package_sha256"] != pin["sha256"] or
                record["plan"]["source"]["package_bytes"] != pin["bytes"]):
            raise JobError(relative + ": validated snapshot differs from its frozen pin")
        # Rewrite only the planner's input-path field. Identities, receipts and
        # versioned destinations are never rewritten to make relocation match.
        item["package"] = relative
    return result


def _manifest(value):
    if (not isinstance(value, dict) or
            set(value) != {"format", "version", "state", "files", "native_acceptance"} or
            value["format"] != FORMAT or type(value["version"]) is not int or value["version"] != 1 or
            value["state"] != "complete" or value["native_acceptance"] is not False or
            not isinstance(value["files"], list) or not 4 <= len(value["files"]) <= MAX_ITEMS + 3):
        raise JobError("unsupported or incomplete job manifest")
    pins = {}
    total = 0
    for pin in value["files"]:
        if not isinstance(pin, dict) or set(pin) != {"path", "bytes", "sha256"}:
            raise JobError("invalid job file pin")
        name, size, digest = pin["path"], pin["bytes"], pin["sha256"]
        package = isinstance(name, str) and re.fullmatch(r"packages/[0-9]{4}\.zip", name)
        if (not isinstance(name, str) or name in pins or (name not in CONTROL_LIMITS and not package) or
                type(size) is not int or size < 0 or size > (MAX_PACKAGE_BYTES if package else CONTROL_LIMITS[name]) or
                not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise JobError("unsafe, duplicate or invalid job file pin")
        pins[name] = pin
        if package:
            total += size
    if not set(CONTROL_LIMITS) <= set(pins) or total > MAX_SOURCE_BYTES:
        raise JobError("job control inventory or cumulative package budget is invalid")
    return pins


def _inventory(root, pins):
    _plain(root, directory=True)
    _plain(root / "packages", directory=True)
    expected_root = set(CONTROL_LIMITS) | {MANIFEST, PENDING, "packages"}
    expected_packages = {name.split("/")[1] for name in pins if name.startswith("packages/")}
    for directory, expected in ((root, expected_root), (root / "packages", expected_packages)):
        seen = set()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name not in expected:
                    raise JobError("unexpected job entry: " + str(directory / entry.name))
                seen.add(entry.name)
        if seen != expected:
            raise JobError("missing job entry in " + str(directory))


def _selection(provenance, staged):
    if (not isinstance(provenance, dict) or
            set(provenance) != {"format", "version", "base_directory", "request"} or
            provenance["format"] != "daedalus-world-job-provenance" or
            type(provenance["version"]) is not int or provenance["version"] != 1):
        raise JobError("invalid original selection provenance")
    _text(provenance["base_directory"], "original base directory", maximum=4096)
    original = provenance["request"]
    if (not isinstance(original, dict) or not isinstance(original.get("packages"), list) or
            not 1 <= len(original["packages"]) <= MAX_ITEMS):
        raise JobError("invalid original selection request")
    # Original paths are descriptive provenance, not paths to open on this host.
    # Validate the request contract with only those path fields relocated. This
    # also allows a Windows-produced job to be inspected on a POSIX host.
    items = []
    for item in original["packages"]:
        if not isinstance(item, dict) or set(item) != {"key", "package"}:
            raise JobError("invalid original package selection")
        _text(item["key"], "original input key", maximum=128)
        _text(item["package"], "original package path", maximum=4096)
        items.append(dict(item))
    items.sort(key=lambda item: item["key"])
    mapping = _mapping(items)
    normalized = dict(original, packages=[dict(item, package=mapping[item["key"]]) for item in items])
    _request(normalized)
    if normalized != staged:
        raise JobError("staged keys/receipts differ from the original selection")


def create_job(explicit_batch_request, fresh_output, explicit_base_directory):
    """Publish a new self-contained byte-pinned job; never reuse/clean a partial job."""
    _request(explicit_batch_request)
    original = _json(_json_bytes(explicit_batch_request, MAX_REQUEST_BYTES))
    items, _ = _request(original)
    root, base = _path(fresh_output), _path(explicit_base_directory)
    mapping = _mapping(items)
    staged = dict(original, packages=[dict(item, package=mapping[item["key"]]) for item in items])
    provenance = {"format": "daedalus-world-job-provenance", "version": 1,
                  "base_directory": str(base), "request": original}
    created = False
    try:
        root.mkdir()
        created = True
        (root / "packages").mkdir()
        pins = []
        data = _json_bytes(provenance, CONTROL_LIMITS["provenance.json"])
        _write(root / "provenance.json", data)
        pins.append(_pin("provenance.json", data))
        total = 0
        for item in items:
            if total + MAX_PACKAGE_BYTES + 1 > MAX_SOURCE_BYTES:
                raise JobError("frozen source-read budget exhausted before opening " + item["key"])
            raw = Path(item["package"])
            source = _path(raw if raw.is_absolute() else base / raw)
            pin = _copy(source, root / mapping[item["key"]])
            pins.append(pin)
            total += pin["bytes"]
        pin_map = {pin["path"]: pin for pin in pins}
        plan = _batch(root, staged, pin_map)
        for name, value in (("request.json", staged), ("plan.json", plan)):
            data = _json_bytes(value, CONTROL_LIMITS[name])
            _write(root / name, data)
            pins.append(_pin(name, data))
        manifest = {"format": FORMAT, "version": 1, "state": "complete",
                    "files": sorted(pins, key=lambda pin: pin["path"]), "native_acceptance": False}
        _manifest(manifest)
        encoded = _json_bytes(manifest, MAX_MANIFEST_BYTES)
        _write(root / PENDING, encoded)
        # Atomic no-replace publication on supporting local filesystems. Keep the
        # candidate as diagnostic evidence. No rename/overwrite fallback exists.
        os.link(root / PENDING, root / MANIFEST)
        return {"manifest": manifest, "plan": plan, "native_acceptance": False}
    except (OSError, PlanError, UnicodeError) as error:
        state = "output not created"
        if created:
            state = "unpublished"
            try:
                if (root / MANIFEST).exists():
                    state = "publication uncertain; inspect job.json explicitly"
            except OSError:
                state = "publication uncertain; cannot check job.json"
        raise JobError(str(root) + ": " + state + ": " + str(error)) from error


def inspect_job(job_directory):
    """Verify only retained job bytes; original package paths are never reopened."""
    root = _path(job_directory)
    try:
        _plain(root, directory=True)
        manifest_bytes = _read(root / MANIFEST, MAX_MANIFEST_BYTES)
        manifest = _json(manifest_bytes)
        pins = _manifest(manifest)
        _inventory(root, pins)
        if _read(root / PENDING, MAX_MANIFEST_BYTES) != manifest_bytes:
            raise JobError("published and pending job manifests disagree")
        controls = {}
        for name, pin in pins.items():
            package = name.startswith("packages/")
            data = _read(root / name, pin["bytes"], expected=pin, keep=not package)
            if not package:
                controls[name] = data
        staged = _json(controls["request.json"])
        _request(staged)
        _selection(_json(controls["provenance.json"]), staged)
        expected = set(CONTROL_LIMITS) | set(_mapping(_request(staged)[0]).values())
        if set(pins) != expected:
            raise JobError("pinned packages do not match the staged selection")
        plan = _batch(root, staged, pins)
        if encode_batch(plan) != controls["plan.json"]:
            raise JobError("retained plan differs from the frozen package/receipt plan")
        return {"manifest": manifest, "plan": plan, "native_acceptance": False}
    except (OSError, PlanError, UnicodeError) as error:
        raise JobError(str(root) + ": cannot inspect frozen job: " + str(error)) from error
