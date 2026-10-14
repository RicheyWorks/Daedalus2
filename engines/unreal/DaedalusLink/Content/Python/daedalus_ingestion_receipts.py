# SPDX-License-Identifier: MIT
"""Portable receipt primitives for the existing editor importers.

Uses the existing artifact fingerprint shape (sha256/bytes). No Unreal imports,
backend selection, retries, process control or asset mutations happen here.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from types import CodeType
import uuid


SCHEMA = "daedalus.ingestion-receipt.v1"
SAFE_RETRY_STATES = {"input_verified", "input_failed"}
STATES = SAFE_RETRY_STATES | {"import_started", "imported", "postprocessed", "save_started", "saved", "uncertain"}


def loaded_code_fingerprint(function):
    """Canonical semantics, independent of marshal's reference-count encoding.

    Public co_code excludes CPython's adaptive execution caches. Source files
    remain separate manifest dependencies; this also covers loaded defaults.
    """
    def encode(value):
        kind = type(value)
        if value is None:
            return ["none"]
        if value is Ellipsis:
            return ["ellipsis"]
        if kind is bool:
            return ["bool", value]
        if kind is int:
            return ["int", str(value)]
        if kind is float:
            return ["float", value.hex()]
        if kind is complex:
            return ["complex", value.real.hex(), value.imag.hex()]
        if kind is str:
            return ["str", value]
        if kind is bytes:
            return ["bytes", value.hex()]
        if kind in (tuple, frozenset):
            items = [encode(item) for item in value]
            if kind is frozenset:
                items.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
            return [kind.__name__, items]
        if kind is dict and all(type(key) is str for key in value):
            return ["dict", [[key, encode(value[key])] for key in sorted(value)]]
        if kind is CodeType:
            fields = ("co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals",
                      "co_stacksize", "co_flags", "co_code", "co_consts", "co_names", "co_varnames",
                      "co_freevars", "co_cellvars", "co_name", "co_filename", "co_firstlineno")
            code = {field: encode(getattr(value, field)) for field in fields}
            for field in ("co_qualname", "co_linetable", "co_lnotab", "co_exceptiontable"):
                if hasattr(value, field):
                    code[field] = encode(getattr(value, field))
            return ["code", code]
        raise TypeError("unsupported loaded-code constant/default type: " + kind.__name__)
    if function.__closure__:
        raise ValueError("loaded closure state requires an explicit supported identity contract")
    identity = {"algorithm": "daedalus.loaded-code.v1", "implementation": sys.implementation.name,
                "cache_tag": sys.implementation.cache_tag, "python": list(sys.version_info[:3]),
                "code": encode(function.__code__), "defaults": encode(function.__defaults__),
                "kwdefaults": encode(function.__kwdefaults__)}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def manifest(source, destination, settings, engine, backend, dependencies):
    files = sorted({str(Path(path).resolve()) for path in dependencies})
    if len(files) > 32:
        raise ValueError("at most 32 explicit file dependencies per import")
    return {
        "schema": SCHEMA,
        "source": {"path": str(Path(source).resolve()), **fingerprint(source)},
        "destination": destination,
        "settings": settings,
        "engine": engine,
        "backend": backend,
        "dependencies": {path: fingerprint(path) for path in files},
    }


def manifest_key(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_receipt(path):
    if not Path(path).exists():
        return None
    if Path(path).stat().st_size > 131072:
        raise ValueError("oversized ingestion receipt; inspect before delivery")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_receipt(value)


def _valid_witness(value):
    return (isinstance(value, dict) and isinstance(value.get("sha256"), str)
            and re.fullmatch("[0-9a-f]{64}", value["sha256"]) is not None
            and type(value.get("bytes")) is int and value["bytes"] >= 0)


def validate_receipt(value):
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA
            or value.get("state") not in STATES or not isinstance(value.get("manifest"), dict)
            or value.get("manifest", {}).get("schema") != SCHEMA
            or not isinstance(value.get("key"), str)
            or value.get("key") != manifest_key(value["manifest"])):
        raise ValueError("unknown/corrupt ingestion receipt; inspect before delivery")
    if value["state"] == "saved":
        assets, outputs = value.get("assets"), value.get("outputs")
        destination = value["manifest"].get("destination")
        if (value.get("save_confirmed") is not True or not isinstance(destination, str)
                or not isinstance(assets, dict) or not assets or not isinstance(outputs, dict) or not outputs
                or any(not isinstance(path, str) or not path.startswith(destination + "/") for path in assets.values())
                or not set(assets.values()).issubset(outputs)
                or any(not isinstance(path, str) or not _valid_witness(witness) for path, witness in outputs.items())):
            raise ValueError("corrupt saved receipt; asset/save proof is inconsistent")
    elif value.get("save_confirmed") is not False:
        raise ValueError("unfinished receipt cannot claim a confirmed save")
    return value


def write_receipt(path, value):
    """Replace one receipt atomically; a partial file is never a saved proof."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def verified_snapshot(source, expected, folder):
    """Keep an immutable input alive across an uncertain editor operation."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(source).name
    if target.exists():
        if fingerprint(target) != expected:
            raise ValueError("existing import snapshot differs; inspect before retry")
        return str(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
        shutil.copyfile(source, temporary)
        if fingerprint(temporary) != expected:
            raise ValueError("source changed while preparing the immutable import snapshot")
        os.replace(temporary, target)
        return str(target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def may_skip(receipt, key, destination_exists):
    if receipt:
        validate_receipt(receipt)
    return bool(receipt and receipt.get("state") == "saved"
                and receipt.get("key") == key and receipt.get("save_confirmed") is True
                and receipt.get("outputs")
                and all(destination_exists(path, witness)
                        for path, witness in receipt["outputs"].items()))


def require_retry_permission(receipt, retry_uncertain):
    if type(retry_uncertain) is not bool:
        raise ValueError("retry_uncertain must be an explicit boolean")
    if receipt:
        validate_receipt(receipt)
    if receipt and receipt.get("state") not in SAFE_RETRY_STATES | {"saved"} and not retry_uncertain:
        raise RuntimeError("unfinished import receipt requires owner inspection; "
                           "retry_uncertain=True only after its native outcome is reconciled")


@contextmanager
def exclusive_batch(folder):
    """Only upgraded callers share this lock; it does not serialize legacy jobs."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / "batch.lock"
    token = uuid.uuid4().hex
    with lock.open("x", encoding="utf-8") as output:
        json.dump({"token": token, "pid": os.getpid(), "started_utc": utc_now()}, output)
    try:
        yield
    finally:
        if json.loads(lock.read_text(encoding="utf-8")).get("token") != token:
            raise RuntimeError("batch lock ownership changed; preserving it for inspection")
        lock.unlink()
