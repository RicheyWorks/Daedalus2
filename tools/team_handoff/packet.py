# SPDX-License-Identifier: MIT
"""Immutable evidence copies and pointer-last publication; no live integrations.

Uses the existing live_handoff/R22 durable-write protocol: exclusive temporary
files, flush/fsync, OS-backed cooperative writer serialization, replace last.
The private store lock never represents producer ownership or scheduler custody.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from .contracts import ContractError, timestamp_key, validate_checkpoint

PACKET_SCHEMA = "daedalus.takeover-packet.v1"
POINTER_SCHEMA = "daedalus.takeover-pointer.v1"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}\Z")


def fail(code, message):
    raise ContractError(code, message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            fail("duplicate_json_key", "Duplicate JSON key: " + key)
        out[key] = value
    return out


def decode(raw, label="JSON"):
    if len(raw) > MAX_JSON_BYTES:
        fail("json_size", label + " exceeds the 2 MiB limit")
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: fail("invalid_json", "Nonfinite JSON: " + value))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        fail("invalid_json", label + ": " + str(exc))


def _plain(path):
    """Reject reparse points, including junctions on Python 3.10 Windows."""
    try:
        value = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(value.st_mode) or getattr(value, "st_file_attributes", 0) & 0x400:
        fail("linked_path", "Symlink/junction/reparse point refused: " + str(path))


def _root(path, create=False):
    value = Path(os.path.abspath(path))
    for parent in reversed((value,) + tuple(value.parents)):
        _plain(parent)
    if create:
        value.mkdir(parents=True, exist_ok=True)
    if not value.is_dir():
        fail("missing_directory", "Directory is absent: " + str(value))
    return value


def relative(value):
    if not isinstance(value, str) or len(value) > 220 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", value):
        fail("unsafe_path", "Expected a portable relative evidence path: " + repr(value))
    reserved = {"con", "prn", "aux", "nul"} | {prefix + str(i) for prefix in ("com", "lpt") for i in range(1, 10)}
    if any(part in ("", ".", "..") or part.endswith(".") or part.split(".")[0].lower() in reserved
           for part in value.split("/")):
        fail("unsafe_path", "Unsafe evidence path: " + value)
    return value


def _path(root, name):
    result = root
    for part in relative(name).split("/"):
        result = result / part
        _plain(result)
    return result


def _read(path, limit=MAX_JSON_BYTES):
    _plain(path)
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        fail("file_size", "File exceeds supported limit: " + str(path))
    return raw


def read_json(path):
    return decode(_read(Path(path)), str(path))


def _write_new(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_dir(path):
    # Windows does not expose directory fsync here. Atomic rename is supported;
    # whole-machine power-loss durability is explicitly outside this contract.
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _replace_json(path, value, before_replace=None):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    _write_new(temporary, canonical(value))
    if before_replace:
        before_replace()
    os.replace(temporary, path)
    _sync_dir(path.parent)


@contextmanager
def _writer(root):
    """Existing handoff OS-lock pattern, scoped solely to this offline store."""
    path = root / ".publish.lock"
    _plain(path)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fail("publisher_busy", "Another cooperative publisher holds this offline store")
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _pointer(root, selection):
    if selection not in ("current", "previous"):
        fail("selection", "Selection must be current or previous")
    value = read_json(root / (selection + ".json"))
    if not isinstance(value, dict) or set(value) != {"schema", "sha256"} or value["schema"] != POINTER_SCHEMA:
        fail("pointer_version", "Unsupported or malformed " + selection + " pointer")
    if not isinstance(value["sha256"], str) or not HASH.fullmatch(value["sha256"]):
        fail("pointer_hash", "Invalid packet hash in " + selection + " pointer")
    return value


def _evidence_names(checkpoint):
    names = [row["path"] for row in checkpoint["evidence"].values() if row["status"] == "present"]
    for name in names:
        relative(name)
    if len({name.casefold() for name in names}) != len(names):
        fail("duplicate_path", "Evidence roles require distinct portable paths")
    return sorted(names)


def _provenance(checkpoint, files, base):
    """Validate retained build-time claims, never infer them from current pins."""
    source, build = checkpoint["source"], checkpoint["build"]
    if source["status"] == "recorded":
        role = checkpoint["evidence"]["source"]
        if role["status"] != "present" or files[role["path"]]["sha256"] != source["manifest_sha256"]:
            fail("source_binding", "Recorded source requires its exact retained manifest")
        value = read_json(_path(base, role["path"]))
        if not isinstance(value, dict) or set(value) != {"schema", "commit", "files"} or value["schema"] != "daedalus.build-inputs.v1" or value["commit"] != source["commit"]:
            fail("source_binding", "Source manifest version/commit differs")
        rows = value["files"]
        if not isinstance(rows, list) or not rows or len(rows) > 100000:
            fail("source_binding", "A nonempty complete build-input inventory is required")
        paths = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"path", "category", "sha256", "bytes"}:
                fail("source_binding", "Malformed build input entry")
            paths.append(relative(row["path"]).casefold())
            if row["category"] not in ("source", "header", "descriptor", "config", "generated") or not isinstance(row["sha256"], str) or not HASH.fullmatch(row["sha256"]) or type(row["bytes"]) is not int or row["bytes"] < 0:
                fail("source_binding", "Invalid build-input category/hash/size")
        if len(set(paths)) != len(paths):
            fail("source_binding", "Duplicate build-input identity")
    if build["status"] == "bound":
        role = checkpoint["evidence"]["build"]
        if role["status"] != "present" or files[role["path"]]["sha256"] != build["receipt_sha256"]:
            fail("build_binding", "Bound build requires its exact retained receipt")
        value = read_json(_path(base, role["path"]))
        keys = {"schema", "recorded_at_build_time", "source_commit", "inputs_before_sha256", "inputs_after_sha256", "artifact_sha256", "toolchain", "command", "exit_code"}
        if not isinstance(value, dict) or set(value) != keys or value["schema"] != "daedalus.build-provenance.v1":
            fail("build_binding", "Malformed build-time provenance receipt")
        if (value["recorded_at_build_time"] is not True or type(value["exit_code"]) is not int or value["exit_code"] != 0
                or source["status"] != "recorded" or value["source_commit"] != source["commit"]
                or value["inputs_before_sha256"] != source["manifest_sha256"]
                or value["inputs_after_sha256"] != source["manifest_sha256"]
                or build["source_manifest_sha256"] != source["manifest_sha256"]
                or value["artifact_sha256"] != build["artifact_sha256"]
                or build["artifact_sha256"] != checkpoint["runtime"]["artifact_sha256"]):
            fail("build_binding", "Build/source/artifact binding differs or inputs changed during build")
        if (not isinstance(value["toolchain"], dict) or set(value["toolchain"]) != {"engine", "compiler"}
                or any(not isinstance(item, str) or not item.strip() for item in value["toolchain"].values())
                or not isinstance(value["command"], list) or not value["command"]
                or any(not isinstance(item, str) or not item for item in value["command"])):
            fail("build_binding", "Build command and exact engine/compiler are required")


def _boundary(checkpoint, files, base):
    """Read the existing R18/R20 saved-boundary fields, without another ledger.

    Additional original receipt fields stay intact. These are deliberately small
    supported adapters, not a claim to reconcile native assets or PID liveness.
    """
    def document(role):
        row = checkpoint["evidence"][role]
        if row["status"] == "unknown":
            return None
        value = read_json(_path(base, row["path"]))
        if not isinstance(value, dict):
            fail("boundary_evidence", role + " receipt must be a JSON object")
        return value
    for role in ("ledger", "checkpoint"):
        value = document(role)
        if value is None:
            continue
        if (value.get("saved_counts") != checkpoint["progress"]["counts"]
                or value.get("next_index") != checkpoint["progress"]["next_index"]):
            fail("boundary_evidence", role + " saved counts/next index differ from the checkpoint")
        if role == "checkpoint" and value.get("owner_pid") != checkpoint["owner"]["pid"]:
            fail("boundary_evidence", "Monitor snapshot owner PID differs")
        if role == "checkpoint" and checkpoint["phase"] in ("saved", "stopped"):
            active = value.get("active")
            if (not isinstance(active, dict) or active.get("stage") not in ("chunk_saved", "paused_saved_boundary")
                    or active.get("pending") is not None):
                fail("boundary_evidence", "Monitor must retain a supported saved stage without pending effects; a heartbeat cannot relabel in-flight work")
    owner = document("owner")
    if owner is not None and owner.get("pid") != checkpoint["owner"]["pid"]:
        fail("boundary_evidence", "Retained owner PID differs")
    if owner is not None:
        for key in ("owner", "session", "host", "start_utc"):
            if key not in owner:
                continue
            same = (timestamp_key(owner[key]) == timestamp_key(checkpoint["owner"][key])
                    if key == "start_utc" else owner[key] == checkpoint["owner"][key])
            if not same:
                fail("boundary_evidence", "Retained owner " + key + " differs")
    native = document("native")
    if native is not None and checkpoint["phase"] in ("saved", "stopped"):
        native = native.get("native", native)
        if (not isinstance(native, dict) or native.get("saved") is not True
                or native.get("dirty") != {"maps": [], "content": []}
                or native.get("play") is not False or native.get("import_active") is not False):
            fail("boundary_evidence", "Saved boundary requires retained saved/clean/no-Play/no-import native facts")
    hashes = {row["sha256"] for row in files.values()}
    for operation in checkpoint["operations"]:
        for key in ("intent_sha256", "result_sha256"):
            if operation[key] is not None and operation[key] not in hashes:
                fail("operation_evidence", "Operation " + operation["id"] + " lacks retained " + key + " bytes")


def _load(root, packet_hash, selection):
    base = _path(root, "packets/" + packet_hash)
    raw = _read(base / "manifest.json")
    if digest(raw) != packet_hash:
        fail("manifest_hash", "Packet manifest hash differs: " + packet_hash)
    value = decode(raw, "manifest")
    if not isinstance(value, dict) or set(value) != {"schema", "checkpoint", "files"} or value["schema"] != PACKET_SCHEMA:
        fail("packet_version", "Unsupported or malformed packet manifest")
    validate_checkpoint(value["checkpoint"])
    names = _evidence_names(value["checkpoint"])
    files = value["files"]
    if not isinstance(files, dict) or sorted(files) != names:
        fail("evidence_inventory", "Manifest files must exactly match present checkpoint evidence")
    expected = {"manifest.json"} | {"evidence/" + name for name in names}
    actual = set()
    total = 0
    for path in base.rglob("*"):
        _plain(path)
        if path.is_file():
            actual.add(path.relative_to(base).as_posix())
    if actual != expected:
        fail("packet_inventory", "Packet has missing or unexpected files")
    for name, row in files.items():
        if (not isinstance(row, dict) or set(row) != {"bytes", "sha256"}
                or type(row["bytes"]) is not int or not 0 <= row["bytes"] <= MAX_EVIDENCE_BYTES
                or not isinstance(row["sha256"], str) or not HASH.fullmatch(row["sha256"])):
            fail("evidence_pin", "Invalid evidence hash/size: " + name)
        raw = _read(_path(base / "evidence", name), MAX_EVIDENCE_BYTES)
        total += len(raw)
        if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
            fail("evidence_hash", "Evidence bytes/hash differ: " + name)
    if total > MAX_TOTAL_BYTES:
        fail("evidence_size", "Packet evidence exceeds 64 MiB")
    _provenance(value["checkpoint"], files, base / "evidence")
    _boundary(value["checkpoint"], files, base / "evidence")
    return dict(value, sha256=packet_hash, selection=selection)


def read_packet(store, selection="current"):
    """Read only the requested sealed packet. Never fall back silently."""
    root = _root(store)
    pointer = _pointer(root, selection)
    return _load(root, pointer["sha256"], selection)


def seal(store, checkpoint, evidence_root, expected_current=None, fault=None):
    """Publish copies of existing receipts under a cooperative single-writer rule.

    expected_current=None admits initialization only. For updates, callers must
    pin the current packet digest. An injected exception preserves all receipts;
    unadvertised staging/orphan directories may remain for inspection.
    """
    validate_checkpoint(checkpoint)
    names = _evidence_names(checkpoint)
    source = _root(evidence_root)
    root = _root(store, create=True)
    if root == source or source in root.parents or root in source.parents:
        fail("overlapping_store", "Evidence inputs and publication store must be disjoint")
    def inject(phase):
        if fault:
            fault(phase)
    with _writer(root):
        old = None
        if (root / "current.json").exists():
            old = read_packet(root)
        if expected_current != (old["sha256"] if old else None):
            fail("current_changed", "Expected current packet differs; inspect and reconcile before publication")
        if old:
            previous = old["checkpoint"]
            if (checkpoint["prior_sha256"] != old["sha256"] or checkpoint["sequence"] != previous["sequence"] + 1
                    or checkpoint["campaign"] != previous["campaign"]
                    or timestamp_key(checkpoint["saved_utc"]) < timestamp_key(previous["saved_utc"])):
                fail("checkpoint_chain", "Campaign, sequence, prior digest or checkpoint time differs")
            if any(timestamp_key(checkpoint["window"][key]) != timestamp_key(previous["window"][key])
                   for key in ("start_utc", "deadline_utc")):
                fail("window_chain", "Continuation cannot reset the original campaign window")
            if any(checkpoint["progress"]["counts"].get(kind, -1) < count for kind, count in previous["progress"]["counts"].items()):
                fail("progress_regression", "Saved counts cannot move backwards")
            if checkpoint["progress"]["next_index"] < previous["progress"]["next_index"]:
                fail("progress_regression", "Next index cannot move backwards")
        elif checkpoint["sequence"] != 1 or checkpoint["prior_sha256"] is not None:
            fail("checkpoint_chain", "A new store requires sequence 1 and null prior digest")
        packets = root / "packets"
        _plain(packets)
        packets.mkdir(exist_ok=True)
        staging = packets / (".staging-" + uuid.uuid4().hex)
        staging.mkdir()
        evidence = staging / "evidence"
        evidence.mkdir()
        files, total = {}, 0
        for name in names:
            raw = _read(_path(source, name), MAX_EVIDENCE_BYTES)
            total += len(raw)
            if total > MAX_TOTAL_BYTES:
                fail("evidence_size", "Packet evidence exceeds 64 MiB")
            target = _path(evidence, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_new(target, raw)
            files[name] = {"sha256": digest(raw), "bytes": len(raw)}
        inject("after_evidence")
        _provenance(checkpoint, files, evidence)
        _boundary(checkpoint, files, evidence)
        manifest = {"schema": PACKET_SCHEMA, "checkpoint": checkpoint, "files": files}
        raw = canonical(manifest)
        if len(raw) > MAX_JSON_BYTES:
            fail("json_size", "Packet manifest exceeds 2 MiB")
        packet_hash = digest(raw)
        _write_new(staging / "manifest.json", raw)
        _sync_dir(staging)
        inject("after_manifest")
        target = packets / packet_hash
        if target.exists():
            _load(root, packet_hash, "current")
        else:
            os.rename(staging, target)
            _sync_dir(packets)
        _load(root, packet_hash, "current")
        inject("after_packet")
        if old:
            _replace_json(root / "previous.json", {"schema": POINTER_SCHEMA, "sha256": old["sha256"]})
        _replace_json(root / "current.json", {"schema": POINTER_SCHEMA, "sha256": packet_hash},
                      lambda: inject("before_pointer_replace"))
        inject("after_pointer")
        return read_packet(root)
