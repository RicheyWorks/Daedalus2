# SPDX-License-Identifier: MIT
"""Rolling, descriptive selection of complete immutable source snapshots.

The outer sequence links independent captures; inner checkpoints and original
receipts are never rewritten. A single atomic index rotates both advertised
digests. Private cooperative serialization grants no producer or native custody.
"""

import os
from pathlib import Path
import re
import uuid

from . import contracts as c
from . import packet, source_snapshot


INDEX_SCHEMA = "daedalus.composite-checkpoint-index.v1"
ENTRY_SCHEMA = "daedalus.composite-checkpoint-entry.v1"
RESULT_SCHEMA = "daedalus.composite-checkpoint-selection.v1"
MAX_SEQUENCE = 2**63 - 1


def _require(condition, code, message):
    if not condition:
        packet.fail(code, message)


def _index(root, allow_absent=False):
    try:
        raw = packet._read(packet._path(root, "current.json"))
    except FileNotFoundError:
        if allow_absent:
            return None
        packet.fail("checkpoint_missing", "No advertised composite checkpoint index exists")
    value = packet.decode(raw, "composite checkpoint index")
    c._object(value, ("schema", "sequence", "current_sha256", "previous_sha256"), "checkpoint index")
    _require(value["schema"] == INDEX_SCHEMA and packet.canonical(value) == raw,
             "checkpoint_index", "Unsupported or noncanonical composite checkpoint index")
    c._integer(value["sequence"], "checkpoint index sequence", 1, MAX_SEQUENCE)
    c._hash(value["current_sha256"], "checkpoint index current")
    c._hash(value["previous_sha256"], "checkpoint index previous", nullable=True)
    _require((value["sequence"] == 1) == (value["previous_sha256"] is None)
             and value["current_sha256"] != value["previous_sha256"],
             "checkpoint_index", "Composite checkpoint index lineage is inconsistent")
    return value


def _entry(root, sha256):
    c._hash(sha256, "composite checkpoint digest")
    try:
        raw = packet._read(packet._path(root, "entries/" + sha256 + ".json"))
    except FileNotFoundError:
        packet.fail("checkpoint_entry_missing", "Advertised immutable entry is absent: " + sha256)
    _require(packet.digest(raw) == sha256, "checkpoint_entry_hash", "Immutable checkpoint entry bytes differ")
    value = packet.decode(raw, "composite checkpoint entry")
    c._object(value, ("schema", "sequence", "prior_sha256", "capture", "receipt_sha256", "packet_sha256"),
              "checkpoint entry")
    _require(value["schema"] == ENTRY_SCHEMA and packet.canonical(value) == raw,
             "checkpoint_entry", "Unsupported or noncanonical composite checkpoint entry")
    c._integer(value["sequence"], "checkpoint entry sequence", 1, MAX_SEQUENCE)
    for field in ("receipt_sha256", "packet_sha256"):
        c._hash(value[field], "checkpoint entry " + field)
    c._hash(value["prior_sha256"], "checkpoint entry prior", nullable=True)
    _require((value["sequence"] == 1) == (value["prior_sha256"] is None)
             and value["prior_sha256"] != sha256,
             "checkpoint_entry", "Immutable checkpoint entry lineage is inconsistent")
    _require(isinstance(value["capture"], str)
             and re.fullmatch(r"captures/[0-9a-f]{32}", value["capture"]) is not None,
             "checkpoint_capture_path", "Expected an exclusive composite capture directory")
    return value


def _complete(root, entry):
    capture = packet._path(root, entry["capture"])
    result = source_snapshot.read_snapshot(capture, entry["receipt_sha256"])
    _require(result["status"] == "sealed" and result["source_boundary_verified"] is True
             and result["may_execute"] is False and result["packet_sha256"] == entry["packet_sha256"],
             "checkpoint_incomplete", "Advertised entry is not a complete saved composite")
    sealed = packet.read_packet(capture / "packet")
    _require(sealed["sha256"] == entry["packet_sha256"], "checkpoint_packet_hash", "Sealed packet pin differs")
    return result, sealed["checkpoint"]


def read(store, selection="current", expected_sha256=None):
    """Read only the advertised selection; corruption never chooses an orphan.

Explicit previous selection is independent of the current entry/capture bytes.
An unreadable index itself fails closed; this API never repairs or rolls it back.
"""
    _require(selection in ("current", "previous"), "checkpoint_selection", "Selection must be current or previous")
    if expected_sha256 is not None:
        c._hash(expected_sha256, "expected composite digest")
    root = packet._root(store)
    index = _index(root)
    sha256 = index[selection + "_sha256"]
    _require(sha256 is not None, "checkpoint_missing", "No advertised previous composite checkpoint exists")
    _require(expected_sha256 is None or sha256 == expected_sha256,
             "checkpoint_digest", "Selected composite differs from the trusted advertised digest")
    entry = _entry(root, sha256)
    sequence = index["sequence"] - (selection == "previous")
    _require(entry["sequence"] == sequence
             and (selection == "previous" or entry["prior_sha256"] == index["previous_sha256"]),
             "checkpoint_chain", "Selected immutable entry differs from the advertised index lineage")
    snapshot, checkpoint = _complete(root, entry)
    return dict(schema=RESULT_SCHEMA, status="complete", published=True, admission_status="held",
                may_execute=False, live_integration_required=True, selection=selection,
                sha256=sha256, sequence=entry["sequence"], prior_sha256=entry["prior_sha256"],
                current_sha256=index["current_sha256"], previous_sha256=index["previous_sha256"],
                capture=entry["capture"], snapshot=snapshot, checkpoint=checkpoint,
                reasons=snapshot["reasons"])


def _journal(capture, snapshot):
    audit = capture / "source-snapshot"
    manifest_raw = packet._read(audit / "capture.json")
    _require(packet.digest(manifest_raw) == snapshot["capture_sha256"],
             "snapshot_evidence_hash", "Capture manifest changed before continuity validation")
    manifest = packet.decode(manifest_raw)
    raw = packet._read(audit / "copies/journal.json", packet.MAX_EVIDENCE_BYTES)
    pin = dict(sha256=packet.digest(raw), bytes=len(raw))
    _require(pin == manifest["copies"]["journal"]["copy"],
             "snapshot_copy_hash", "Retained journal changed before continuity validation")
    return packet.decode(raw, "retained source journal")


def _continuity(previous, checkpoint, old_snapshot, snapshot, old_journal, journal):
    issues = []
    for field in ("campaign", "runtime", "source", "build"):
        if checkpoint[field] != previous[field]:
            issues.append(dict(code="checkpoint_continuity", message=field + " changed; an explicit transition is required"))
    if (any(checkpoint["owner"][key] != previous["owner"][key] for key in ("owner", "session", "host", "pid"))
            or c.timestamp_key(checkpoint["owner"]["start_utc"]) != c.timestamp_key(previous["owner"]["start_utc"])):
        issues.append(dict(code="checkpoint_continuity", message="Owner generation changed; an explicit transition is required"))
    if any(c.timestamp_key(checkpoint["window"][key]) != c.timestamp_key(previous["window"][key])
           for key in ("start_utc", "deadline_utc")):
        issues.append(dict(code="window_chain", message="Continuation cannot reset or rewrite the original window"))
    if (previous["source"]["status"] != "recorded" or checkpoint["source"]["status"] != "recorded"
            or previous["build"]["status"] != "bound" or checkpoint["build"]["status"] != "bound"):
        issues.append(dict(code="checkpoint_provenance_unknown", message="Unknown source/build continuity cannot advance an existing stream"))
    if (c.timestamp_key(checkpoint["saved_utc"]) < c.timestamp_key(previous["saved_utc"])
            or c.timestamp_key(snapshot["captured_utc"]) < c.timestamp_key(old_snapshot["captured_utc"])):
        issues.append(dict(code="checkpoint_time_regression", message="Original saved/capture times cannot move backwards"))
    counts, old_counts = checkpoint["progress"]["counts"], previous["progress"]["counts"]
    if set(counts) != set(old_counts):
        issues.append(dict(code="checkpoint_continuity", message="Saved-count categories changed; an explicit transition is required"))
    elif any(counts[kind] < count for kind, count in old_counts.items()):
        issues.append(dict(code="progress_regression", message="Saved counts cannot move backwards"))
    if checkpoint["progress"]["next_index"] < previous["progress"]["next_index"]:
        issues.append(dict(code="progress_regression", message="Next index cannot move backwards"))
    operations = {operation["id"]: operation for operation in journal["operations"]}
    if (any(operations.get(operation["id"]) != operation for operation in old_journal["operations"])
            or c.timestamp_key(journal["through_utc"]) < c.timestamp_key(old_journal["through_utc"])):
        issues.append(dict(code="checkpoint_journal_continuity",
                           message="Prior operation evidence and inventory cutoff must remain retained without rewriting"))
    return issues


def _held(capture, snapshot, index, issues):
    return dict(schema=RESULT_SCHEMA, status="held", published=False, admission_status="held",
                may_execute=False, live_integration_required=True, sha256=None, sequence=None,
                prior_sha256=None, current_sha256=index["current_sha256"] if index else None,
                previous_sha256=index["previous_sha256"] if index else None,
                capture=capture, snapshot=snapshot, reasons=snapshot["reasons"] + issues)


def publish(store, request, source_root, expected_current=None, fault=None):
    """Capture explicit exports and advertise a COMPLETE composite by CAS.

None initializes only an unadvertised store. Updates require its actual outer
digest, not the inner packet or capture-receipt digest. All failed/partial and
unadvertised captures remain untouched; retry creates a fresh directory.
"""
    c._hash(expected_current, "expected current composite digest", nullable=True)
    request = packet.decode(packet.canonical(request), "source snapshot request")
    source_snapshot.validate_request(request)
    source = packet._root(source_root)
    target = Path(os.path.abspath(store))
    _require(not (source == target or source in target.parents or target in source.parents),
             "overlapping_store", "Source exports and checkpoint index store must be disjoint")
    root = packet._root(target, create=True)

    def inject(phase):
        if fault:
            fault(phase)

    with packet._writer(root):
        index = _index(root, allow_absent=True)
        current = index["current_sha256"] if index else None
        _require(expected_current == current, "current_changed", "Expected current composite differs; inspect before publishing")
        old = read(root, expected_sha256=current) if index else None
        sequence = index["sequence"] + 1 if index else 1
        _require(sequence <= MAX_SEQUENCE, "checkpoint_sequence", "Composite checkpoint sequence limit reached")
        captures = packet._path(root, "captures")
        captures.mkdir(exist_ok=True)
        entries = packet._path(root, "entries")
        entries.mkdir(exist_ok=True)
        name = "captures/" + uuid.uuid4().hex
        capture = packet._path(root, name)
        snapshot = source_snapshot.capture(request, source, capture,
                                           fault=lambda phase: inject("capture:" + phase))
        inject("after_capture")
        if snapshot["status"] != "sealed":
            return _held(name, snapshot, index, [])
        # Re-read the completed composite, including supplements and lineage.
        snapshot = source_snapshot.read_snapshot(capture, snapshot["receipt_sha256"])
        sealed = packet.read_packet(capture / "packet")
        if old:
            issues = _continuity(old["checkpoint"], sealed["checkpoint"], old["snapshot"], snapshot,
                                 _journal(packet._path(root, old["capture"]), old["snapshot"]),
                                 _journal(capture, snapshot))
            if issues:
                return _held(name, snapshot, index, issues)
        entry = dict(schema=ENTRY_SCHEMA, sequence=sequence, prior_sha256=current, capture=name,
                     receipt_sha256=snapshot["receipt_sha256"], packet_sha256=snapshot["packet_sha256"])
        raw = packet.canonical(entry)
        sha256 = packet.digest(raw)
        packet._write_new(packet._path(root, "entries/" + sha256 + ".json"), raw)
        for directory in (capture / "source-snapshot/copies", capture / "source-snapshot", capture, captures, entries):
            packet._sync_dir(directory)
        inject("after_entry")
        next_index = dict(schema=INDEX_SCHEMA, sequence=sequence,
                          current_sha256=sha256, previous_sha256=current)
        # Both selections commit in one replacement; no half-rotated previous.
        try:
            packet._replace_json(packet._path(root, "current.json"), next_index,
                                 lambda: inject("before_pointer_replace"))
            inject("after_pointer_replace")
            return read(root, expected_sha256=sha256)
        except Exception as exc:
            try:
                advertised = _index(root, allow_absent=True)
            except (OSError, ValueError):
                advertised = None
                uncertain = True
            else:
                uncertain = advertised is not None and advertised["current_sha256"] == sha256
            if uncertain:
                raise c.ContractError("checkpoint_publication_uncertain",
                                      "Composite may be advertised as " + sha256
                                      + "; inspect current/previous without replaying or overwriting captures") from exc
            raise
