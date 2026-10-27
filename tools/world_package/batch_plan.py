# SPDX-License-Identifier: MIT
"""Deterministic offline inventories composed from the existing package planner."""

import hashlib
import json
import os
from pathlib import PureWindowsPath

from .reader_adapter import MAX_PACKAGE_BYTES, PlanError
from .replay_plan import _apply_receipt, _text, build_plan, validate_receipt

MAX_ITEMS = 16
MAX_REQUEST_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
REQUEST_FORMAT = "daedalus-world-batch-request"
PLAN_FORMAT = "daedalus-world-batch-plan"


def _local_path(value):
    path = _text(value, "local path", maximum=4096)
    windows = PureWindowsPath(path)
    if ("://" in path or windows.drive.startswith("\\\\") or path.startswith("\\") or
            (windows.drive and not windows.root) or
            (os.name == "nt" and windows.root and not windows.drive)):
        raise PlanError("batch paths must be local absolute or ordinary relative paths; URLs, UNC/device and drive-relative paths are refused")
    return path


def _request(request):
    if (not isinstance(request, dict) or
            set(request) != {"format", "version", "packages", "prior_receipts"} or
            request["format"] != REQUEST_FORMAT or type(request["version"]) is not int or
            request["version"] != 1):
        raise PlanError("batch request has an unsupported format, version or fields")
    packages = request["packages"]
    receipts = request["prior_receipts"]
    if not isinstance(packages, list) or not 1 <= len(packages) <= MAX_ITEMS:
        raise PlanError("batch packages must be an explicit array of 1 to 16 items")
    if not isinstance(receipts, list) or len(receipts) > MAX_ITEMS:
        raise PlanError("batch prior_receipts must be an array of at most 16 accepted receipts")
    items = []
    keys = set()
    for item in packages:
        if not isinstance(item, dict) or set(item) != {"key", "package"}:
            raise PlanError("each batch input requires exactly key and package")
        key = _text(item["key"], "input key", maximum=128)
        path = _local_path(item["package"])
        if key in keys:
            raise PlanError("duplicate input key: " + key)
        keys.add(key)
        items.append({"key": key, "package": path})
    prior = {}
    for value in receipts:
        receipt = validate_receipt(value)
        world_id = receipt["world_id"]
        if world_id in prior:
            raise PlanError("multiple accepted receipts for raw world ID: " + world_id)
        prior[world_id] = receipt
    return sorted(items, key=lambda item: item["key"]), prior


def _identity(plan):
    return (plan["world"]["id"], plan["world"]["revision"], plan["source"]["package_sha256"])


def _reference(identity):
    value = json.dumps(identity, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _error(error):
    # Diagnostics are data, never commands. Bound backend exception messages too.
    return str(error)[:2048]


def build_batch(request):
    """Validate explicit inputs serially; return an inventory, including refusals.

    No input is inferred from a directory or earlier proposal. Every path is
    validated, even byte-identical aliases. Request-envelope errors raise;
    package/receipt-replay errors remain per-item and make the whole batch unready.
    """
    items, receipts = _request(request)
    groups = {}
    revisions = {}
    charged = 0
    validated = 0
    attempts = 0
    retained = 0
    for item in items:
        # Reserve the reader's complete bounded snapshot, including its oversize
        # probe, BEFORE opening another file. Successful reads refund unused
        # reservation. Failed reads conservatively retain it; no stat/TOCTOU trust.
        reserve = MAX_PACKAGE_BYTES + 1
        if charged + reserve > MAX_SOURCE_BYTES:
            item.update(status="error", error="batch source-read budget exhausted before opening input")
            continue
        charged += reserve
        attempts += 1
        try:
            plan = build_plan(item["package"])
        except (PlanError, OSError, UnicodeError) as error:
            item.update(status="error", error=_error(error))
            continue
        size = plan["source"]["package_bytes"]
        charged -= reserve - size
        validated += size
        identity = _identity(plan)
        item["reference"] = _reference(identity)
        if identity not in groups:
            try:
                weight = len(encode_batch(plan))
                if retained + weight > MAX_OUTPUT_BYTES:
                    raise PlanError("batch candidate plans exceed retained output budget")
            except PlanError as error:
                groups[identity] = {"items": [], "error": _error(error)}
            else:
                retained += weight
                groups[identity] = {"plan": plan, "items": []}
        group = groups[identity]
        group["items"].append(item)
        revisions.setdefault(identity[:2], set()).add(identity[2])

    inventory = []
    for identity, group in sorted(groups.items()):
        world_id, revision, digest = identity
        aliases = group["items"]
        record = {"reference": _reference(identity), "world": {"id": world_id, "revision": revision},
                  "package_sha256": digest, "keys": [item["key"] for item in aliases]}
        if len(revisions[identity[:2]]) != 1:
            record["status"] = "conflict"
            for item in aliases:
                item.update(status="conflict", error="raw world ID/revision has conflicting package bytes")
        elif "error" in group:
            record["status"] = "error"
            for item in aliases:
                item.update(status="error", error=group["error"])
        else:
            try:
                plan = _apply_receipt(group["plan"], receipts.get(world_id))
            except PlanError as error:
                record["status"] = "error"
                for item in aliases:
                    item.update(status="error", error=_error(error))
            else:
                record.update(status=plan["action"], plan=plan)
                aliases[0]["status"] = plan["action"]
                for item in aliases[1:]:
                    item.update(status="duplicate", duplicate_of=aliases[0]["key"])
        inventory.append(record)
    counts = {status: sum(item["status"] == status for item in items)
              for status in ("plan_new", "no_op", "duplicate", "error", "conflict")}
    result = {"format": PLAN_FORMAT, "version": 1,
              "ready": not (counts["error"] or counts["conflict"]),
              "items": items, "inventory": inventory, "counts": counts,
              "budget": {"source_bytes_charged": charged, "source_bytes_validated": validated,
                         "source_bytes_limit": MAX_SOURCE_BYTES, "package_attempts": attempts,
                         "input_limit": MAX_ITEMS},
              "native_acceptance": False}
    # The API and CLI share this limit; a caller cannot accidentally export an
    # oversized inventory. Never serialize NaN or a partly constructed result.
    encode_batch(result)
    return result


def encode_batch(result):
    """Produce a bounded deterministic UTF-8 document (including final newline)."""
    encoder = json.JSONEncoder(ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
    chunks = []
    size = 1
    for chunk in encoder.iterencode(result):
        data = chunk.encode("utf-8")
        size += len(data)
        if size > MAX_OUTPUT_BYTES:
            raise PlanError("batch inventory exceeds 8 MiB output budget")
        chunks.append(data)
    return b"".join(chunks) + b"\n"
