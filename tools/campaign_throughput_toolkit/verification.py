"""Read-only pin checks for an explicitly supplied offline file inventory.

The pin format is the existing ``{path, bytes, sha256}`` contract.  Returned
cache state is an optimization witness, never authority to add or alter pins.
Callers own retaining that state and binding input pins to approved evidence.
No producer, native module, timer, or filesystem writer is imported here.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterable, Mapping


STATE_SCHEMA = "daedalus-offline-verification-cache/1"
REPORT_SCHEMA = "daedalus-offline-verification-report/1"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_METADATA_FIELDS = {"size", "mtime_ns", "ctime_ns", "device", "inode"}


class VerificationError(ValueError):
    """An input or observed file cannot be verified; no next state is issued."""


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise VerificationError(f"{label} must be an integer >= {minimum}")
    return value


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _path(value: Any, *, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise VerificationError("A nonempty absolute filesystem path is required")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise VerificationError(f"Absolute path without parent traversal required: {value}")
    try:
        for component in [*reversed(path.parents), path]:
            if _is_link(component.lstat()):
                raise VerificationError(f"Symlink or reparse path refused: {component}")
        info = path.lstat()
        expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if not expected:
            raise VerificationError(f"Expected {'directory' if directory else 'file'}: {path}")
        return path.resolve(strict=True)
    except OSError as error:
        raise VerificationError(f"Cannot inspect {value}: {error}") from error


def _key(path: Path) -> str:
    return os.path.normcase(str(path))


def _under(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _pins(values: Iterable[Mapping[str, Any]], roots: list[Path]) -> dict[str, dict[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise VerificationError("Pins must be a sequence of pin objects")
    result: dict[str, dict[str, Any]] = {}
    try:
        for value in values:
            if not isinstance(value, Mapping):
                raise VerificationError("Each pin must be an object")
            path = _path(value.get("path"))
            size = _integer(value.get("bytes"), "Pin bytes")
            digest = value.get("sha256")
            if not isinstance(digest, str) or not _HASH.fullmatch(digest):
                raise VerificationError(f"Pin needs lowercase SHA-256: {path}")
            if not _under(path, roots):
                raise VerificationError(f"Pin outside supplied coverage roots: {path}")
            key = _key(path)
            if key in result:
                raise VerificationError(f"Duplicate pin: {path}")
            result[key] = {"path": str(path), "bytes": size, "sha256": digest}
    except TypeError as error:
        raise VerificationError("Pins must be a sequence of pin objects") from error
    return result


def _metadata(info: os.stat_result) -> dict[str, int]:
    return {
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def _stamp(path: Path) -> dict[str, int]:
    _path(str(path))
    try:
        return _metadata(path.stat())
    except OSError as error:
        raise VerificationError(f"Cannot stat {path}: {error}") from error


def _inventory(roots: list[Path]) -> set[str]:
    found: set[str] = set()
    for root in roots:
        _path(str(root), directory=True)
        pending = [root]
        while pending:
            directory = pending.pop()
            _path(str(directory), directory=True)
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        info = entry.stat(follow_symlinks=False)
                        if _is_link(info):
                            raise VerificationError(f"Symlink or reparse entry refused: {entry.path}")
                        if stat.S_ISDIR(info.st_mode):
                            pending.append(Path(entry.path))
                        elif stat.S_ISREG(info.st_mode):
                            found.add(_key(Path(entry.path)))
                        else:
                            raise VerificationError(f"Unsupported inventory entry: {entry.path}")
            except OSError as error:
                raise VerificationError(f"Cannot enumerate {directory}: {error}") from error
    return found


def _hash_file(path: Path, expected: Mapping[str, Any]) -> tuple[dict[str, int], int]:
    before = _stamp(path)
    digest = hashlib.sha256()
    count = 0
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened_stat = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened_stat.st_mode) or _is_link(opened_stat):
                raise VerificationError(f"Opened entry is not a regular file without reparse attributes: {path}")
            opened = _metadata(opened_stat)
            if opened != before:
                raise VerificationError(f"File changed while opening: {path}")
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                count += len(block)
            after_open = _metadata(os.fstat(stream.fileno()))
        after_path = _stamp(path)
    except OSError as error:
        raise VerificationError(f"Cannot hash {path}: {error}") from error
    if before != after_open or before != after_path:
        raise VerificationError(f"File changed during hashing: {path}")
    if count != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        raise VerificationError(f"Pinned bytes/hash mismatch: {path}")
    return after_path, count


def _cache(
    state: Mapping[str, Any] | None,
    pins: dict[str, dict[str, Any]],
    roots: list[Path],
    chunk: int,
    full_every: int,
) -> tuple[dict[str, Any] | None, list[str]]:
    if state is None:
        return None, ["initial_check"]
    if not isinstance(state, Mapping) or state.get("schema") != STATE_SCHEMA:
        raise VerificationError("Unsupported or malformed retained cache")
    if state.get("roots") != [str(root) for root in roots]:
        raise VerificationError("Coverage roots differ from retained cache")
    if state.get("full_every") != full_every:
        raise VerificationError("Full-check cadence differs from retained cache")
    last_chunk = _integer(state.get("chunk"), "Cache chunk", 1)
    last_full = _integer(state.get("last_full_chunk"), "Cache last full chunk", 1)
    if last_full > last_chunk or chunk < last_chunk:
        raise VerificationError("Retained cache has invalid or regressing chunk history")
    old = state.get("pins")
    records = state.get("records")
    if not isinstance(old, dict) or not old or not isinstance(records, dict):
        raise VerificationError("Retained cache has malformed pin/metadata records")
    if set(old) != set(records):
        raise VerificationError("Retained cache pin/metadata coverage differs")
    for key, pin in old.items():
        if key not in pins:
            raise VerificationError(f"Protected pin removed from supplied manifest: {key}")
        if pin != pins[key]:
            raise VerificationError(f"Protected pin changed from retained manifest: {key}")
        metadata = records[key]
        if not isinstance(metadata, dict) or set(metadata) != _METADATA_FIELDS:
            raise VerificationError(f"Malformed retained metadata: {key}")
        for label, value in metadata.items():
            _integer(value, f"Retained metadata {label}")
        if metadata["size"] != pin["bytes"]:
            raise VerificationError(f"Retained metadata size differs from pin: {key}")
    reasons = []
    if chunk > last_chunk + 1:
        reasons.append("checkpoint_gap")
    if chunk - last_full >= full_every:
        reasons.append("full_check_interval_elapsed")
    return dict(state), reasons


def verify(
    pins: Iterable[Mapping[str, Any]],
    *,
    roots: Iterable[str | Path],
    chunk: int,
    phase: str = "chunk",
    state: Mapping[str, Any] | None = None,
    previous_chunk: int | None = None,
    previous_receipt: Mapping[str, Any] | None = None,
    previous_files: Iterable[Mapping[str, Any]] = (),
    full: bool = False,
    full_every: int = 25,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify an explicit file set and return ``(report, next_cache)``.

    Every file beneath ``roots`` must be pinned, except the explicitly supplied
    current previous-receipt pin. Keep output/cache files outside these roots.
    After chunk 1, callers must supply the exact previous chunk number, a pin
    for its retained receipt, and at least one of its file pins. File pins must
    be present unchanged in ``pins``; their provenance must be established by
    the caller from retained approved evidence, not inferred from this cache.

    Initial/start/stop/explicit-full/every-Nth calls hash the entire inventory.
    Intermediate calls hash new or metadata-changed files and always hash the
    previous receipt/files. Other entries reuse metadata witnesses under the
    trust assumptions stated in the report. This is not continuous hashing.
    The function neither updates input objects nor writes any files.
    """
    chunk = _integer(chunk, "Chunk", 1)
    full_every = _integer(full_every, "Full-check interval", 1)
    if phase not in {"start", "chunk", "stop"} or type(full) is not bool:
        raise VerificationError("Use phase start/chunk/stop and boolean full")
    if isinstance(roots, (str, bytes, Path)):
        raise VerificationError("Coverage roots must be a sequence")
    try:
        root_paths = [_path(str(root), directory=True) for root in roots]
    except TypeError as error:
        raise VerificationError("Coverage roots must be a sequence") from error
    if not root_paths or len({_key(root) for root in root_paths}) != len(root_paths):
        raise VerificationError("Nonempty, distinct coverage roots required")
    root_paths.sort(key=_key)
    if any(a in b.parents or b in a.parents for i, a in enumerate(root_paths) for b in root_paths[i + 1 :]):
        raise VerificationError("Overlapping coverage roots refused")
    supplied = _pins(pins, root_paths)
    if not supplied:
        raise VerificationError("Nonempty explicit protected pin manifest required")
    prior_files = _pins(previous_files, root_paths)
    receipts = _pins([previous_receipt], root_paths) if previous_receipt is not None else {}
    has_previous = previous_chunk is not None or bool(receipts) or bool(prior_files)
    if chunk > 1 or has_previous:
        _integer(previous_chunk, "Previous chunk", 1)
        if previous_chunk != chunk - 1 or len(receipts) != 1 or not prior_files:
            raise VerificationError("Exact previous chunk, receipt pin and nonempty file pins required")
    for key, pin in prior_files.items():
        if supplied.get(key) != pin:
            raise VerificationError(f"Previous file lacks exact manifest pin: {key}")
    for key, pin in receipts.items():
        if key in supplied and supplied[key] != pin:
            raise VerificationError(f"Previous receipt conflicts with manifest pin: {key}")
    retained, reasons = _cache(state, supplied, root_paths, chunk, full_every)
    if phase in {"start", "stop"}:
        reasons.append(phase)
    if full:
        reasons.append("explicit_full")
    if chunk % full_every == 0:
        reasons.append("scheduled_checkpoint")
    full_check = bool(reasons)
    all_pins = {**supplied, **receipts}
    inventory = _inventory(root_paths)
    expected = set(all_pins)
    if inventory != expected:
        raise VerificationError(
            f"Inventory mismatch; unknown={sorted(inventory - expected)}; missing={sorted(expected - inventory)}"
        )
    metadata = {key: _stamp(Path(pin["path"])) for key, pin in all_pins.items()}
    old_records = retained["records"] if retained else {}
    old_pins = retained["pins"] if retained else {}
    new = set(supplied) - set(old_pins)
    changed = {key for key in supplied if key in old_records and metadata[key] != old_records[key]}
    must_hash = expected if full_check else new | changed | set(prior_files) | set(receipts)
    hashed_bytes = 0
    for key in sorted(must_hash):
        stamp, size = _hash_file(Path(all_pins[key]["path"]), all_pins[key])
        metadata[key] = stamp
        hashed_bytes += size
    for key in expected - must_hash:
        if metadata[key]["size"] != all_pins[key]["bytes"]:
            raise VerificationError(f"Pinned byte count differs: {key}")
    # Detect ordinary concurrent additions/removals/metadata changes during this
    # read pass. This remains a read pass, not an atomic filesystem snapshot.
    if _inventory(root_paths) != inventory:
        raise VerificationError("Inventory changed during verification")
    if any(_stamp(Path(pin["path"])) != metadata[key] for key, pin in all_pins.items()):
        raise VerificationError("File metadata changed during verification")
    report = {
        "schema": REPORT_SCHEMA,
        "status": "verified_under_declared_assumptions",
        "source_only": True,
        "chunk": chunk,
        "phase": phase,
        "mode": "full" if full_check else "incremental_metadata_reuse",
        "full_reasons": list(dict.fromkeys(reasons)),
        "full_every": full_every,
        "last_full_chunk": chunk if full_check else retained["last_full_chunk"],
        "protected_files": len(supplied),
        "inventory_files": len(inventory),
        "hashed_files": len(must_hash),
        "hashed_bytes": hashed_bytes,
        "metadata_reused_files": len(expected - must_hash),
        "new_files_hashed": sorted(new),
        "changed_metadata_files_hashed": sorted(changed),
        "previous_chunk": previous_chunk,
        "previous_receipt_hashed": bool(receipts),
        "previous_files_hashed": len(prior_files),
        "previous_pin_provenance": "Caller-supplied retained approved evidence; not inferred from cache or receipt filename",
        "continuous_content_verification": False,
        "trust_assumptions": [
            "Input pins and previous-chunk binding are supplied by a trusted evidence owner; this tool does not authorize them",
            "Retained cache is caller-controlled trusted local state, not an authenticated or tamper-proof ledger",
            "Intermediate reuse trusts size, mtime_ns, ctime_ns, device and inode observations; concealed metadata changes may remain undetected until a full check",
            "Caller invokes start, stop and each checkpoint; no scheduler, daemon or production cadence is activated",
            "Reads detect ordinary concurrent changes but are not an atomic filesystem snapshot",
        ],
    }
    next_state = {
        "schema": STATE_SCHEMA,
        "roots": [str(root) for root in root_paths],
        "chunk": chunk,
        "last_full_chunk": report["last_full_chunk"],
        "full_every": full_every,
        "pins": {key: dict(value) for key, value in supplied.items()},
        "records": {key: dict(metadata[key]) for key in supplied},
    }
    return report, next_state
