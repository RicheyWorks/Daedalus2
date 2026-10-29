# SPDX-License-Identifier: MIT
"""Explicit retained files -> existing source request; no capture or live facts."""

from . import contracts as c
from . import packet, source_snapshot


SELECTION_SCHEMA = "daedalus.source-request-selection.v1"
_METADATA = ("profile", "campaign", "max_source_age_seconds", "identity", "session_ref", "runtime", "source_state")


def build_request(explicit_selection, source_root, captured_utc):
    """Pin exactly the named exports without changing declarations or originals.

Pins describe bytes read, not a stable generation or authenticated/living owner.
The existing capture consumer rechecks those pins and all cross-receipt facts.
Catalog remains opaque, matching that consumer; other roles require JSON objects.
"""
    c._object(explicit_selection, ("schema", "inputs") + _METADATA, "source selection")
    if explicit_selection["schema"] != SELECTION_SCHEMA:
        packet.fail("UNSUPPORTED_SOURCE_SELECTION", "Explicit source request selection v1 required")
    c._object(explicit_selection["inputs"], source_snapshot.ROLES, "selection.inputs")
    inputs = {}
    for role in source_snapshot.ROLES:
        row = explicit_selection["inputs"][role]
        if not isinstance(row, dict):
            packet.fail("INVALID_FIELD", "selection.inputs." + role + " must be an object")
        c._enum(row.get("status"), ("present", "unknown"), "selection.inputs." + role + ".status")
        if row["status"] == "present":
            c._object(row, ("status", "path", "logical_path"), "selection.inputs." + role)
            inputs[role] = dict(status="present", path=row["path"], logical_path=row["logical_path"],
                                sha256="0" * 64, bytes=0, reason=None)
        else:
            c._object(row, ("status", "reason"), "selection.inputs." + role)
            inputs[role] = dict(status="unknown", path=None, logical_path=None, sha256=None,
                                bytes=None, reason=row["reason"])
    request = {key: explicit_selection[key] for key in _METADATA}
    request.update(schema=source_snapshot.SCHEMA, captured_utc=captured_utc, inputs=inputs)
    # Transient pins admit only metadata/path validation; they are never returned.
    # Validate every declaration and case collision before accessing any export.
    source_snapshot.validate_request(request)
    request = packet.decode(packet.canonical(request), "source request declarations")
    source = packet._root(source_root)
    total = 0
    for role in source_snapshot.ROLES:
        row = request["inputs"][role]
        if row["status"] == "unknown":
            continue
        raw = packet._read(packet._path(source, row["path"]), packet.MAX_EVIDENCE_BYTES)
        total += len(raw)
        if total > packet.MAX_TOTAL_BYTES:
            packet.fail("evidence_size", "Selected source receipts exceed the existing 64 MiB limit")
        if role != "catalog":
            document = packet.decode(raw, "selected receipt " + role)
            if not isinstance(document, dict):
                packet.fail("SOURCE_FORMAT", "Selected receipt " + role + " must be a JSON object")
        row.update(sha256=packet.digest(raw), bytes=len(raw))
    source_snapshot.validate_request(request)
    return request
