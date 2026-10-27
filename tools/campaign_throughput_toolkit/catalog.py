# SPDX-License-Identifier: MIT
"""Offline, incremental adapter for the retained R18 catalog/CSV contracts.

This module never imports a producer, scans assets, or performs native admission.
The SQLite index is an offline lookup cache; published deltas and chunk CSVs are
immutable. A cumulative JSON snapshot is only produced by explicit ``snapshot``.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
from typing import Any
import uuid


COLUMNS = (
    "name", "kind", "category", "world", "owner", "status", "queue_status",
    "blender_files", "uassets", "path",
)
SCHEMA = "daedalus-offline-incremental-catalog/1"
MAX_RECEIPT_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 1000
MAX_PARTS = 256
R18_ROOT = "/Game/Daedalus/Sandbox/NativeDiscovery/20261024"


class CatalogError(ValueError):
    """An input or retained export is inconsistent; no automatic replay."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise CatalogError(f"Duplicate JSON field/identity: {key}")
        value[key] = child
    return value


def _reject_constant(value: str) -> Any:
    raise CatalogError(f"Non-finite JSON value refused: {value}")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise CatalogError(f"Non-finite JSON value refused: {value}")
    return number


def _decode(raw: bytes | str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant, parse_float=_finite_float)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
        raise CatalogError(f"Malformed retained JSON: {error}") from error


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def immutable(item: dict[str, Any]) -> str:
    """Exactly the immutable field selection used by collection_catalog_r18."""
    return digest({key: item.get(key) for key in (
        "record_key", "stable_item_id", "existing_identity_alias", "assembly",
        "source", "lineage_parent",
    )})


def _regular(path: Path) -> os.stat_result:
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or (
            ancestor.exists()
            and getattr(ancestor.lstat(), "st_file_attributes", 0) & 0x400
        ):
            raise CatalogError(f"Symlink/reparse path refused: {ancestor}")
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        raise CatalogError(f"Regular file required: {path}")
    return value


def _stamp(value: os.stat_result) -> str:
    return ":".join(str(getattr(value, name)) for name in (
        "st_size", "st_mtime_ns", "st_ctime_ns", "st_dev", "st_ino",
    ))


def _read_stable(path: Path, *, limit: int | None = None) -> tuple[bytes, os.stat_result]:
    before = _regular(path)
    if limit is not None and before.st_size > limit:
        raise CatalogError(f"Receipt exceeds {limit}-byte bound: {path}")
    with path.open("rb") as stream:
        raw = stream.read() if limit is None else stream.read(limit + 1)
    if limit is not None and len(raw) > limit:
        raise CatalogError(f"Receipt exceeds {limit}-byte bound during read: {path}")
    after = _regular(path)
    if _stamp(before) != _stamp(after) or len(raw) != after.st_size:
        raise CatalogError(f"File changed during read: {path}")
    return raw, after


def _utc(seconds: float) -> str:
    return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat()


def active_item(identity: str, row: dict[str, Any], world: str,
                evidence: dict[str, Any]) -> dict[str, Any]:
    """Pure R18 active-item adapter apart from its retained blend mtime lookup.

    Field values and ordering follow ``collection_catalog_r18.active_item``.
    Native status is copied from the supplied receipt, never independently proved.
    """
    source = row["source"]
    materials = sorted({slot["native"] for part in row["imports"] for slot in part["slots"]})
    parts = [{
        "role": part["source"]["group"], "asset_path": part["asset"],
        "source_fbx": part["source"]["fbx"],
        "material_indices": [materials.index(slot["native"]) for slot in part["slots"]],
        "separate_saleable_nft": False,
    } for part in row["imports"]]
    return {
        "record_key": identity, "stable_item_id": row["catalog_identity"],
        "identity_origin": "Existing native/source catalog_identity; never derived again from a current filename or PrimaryAssetId",
        "name": row["name"],
        "category": "skull_sculpture" if row["kind"] == "skull" else "living_toter_trash_art",
        "collection_label": "Skulls" if row["kind"] == "skull" else "Toters",
        "stable_collection_id": None, "source_collection": "GrandCollectionR18",
        "catalog_row": {
            "name": identity + " " + row["name"], "kind": "Prop",
            "category": "skull_sculpture" if row["kind"] == "skull" else "living_trash_art",
            "world": "DaedalusDiscovery", "owner": "project",
            "status": "native_saved_sandbox", "queue_status": "REVIEW",
            "blender_files": source["blend"]["path"],
            "uassets": ";".join(part["asset_path"] for part in parts),
            "path": world.split(".")[0],
        },
        "assembly": {"world": world, "parts": parts, "material_assets": materials},
        "source": {key: source.get(key) for key in (
            "blend", "source_units", "lineage", "geometry_identity", "facial_recipe",
            "eye_recipe", "headwear", "interior",
        )},
        "status": {
            "source_created": True, "native_saved": row["native_saved"],
            "native_admitted": row.get("native_admission") == "Valid",
            "individual_visual_approval": False,
            "headwear_motion": row.get("headwear_motion"), "gameplay_mechanics": "Not claimed",
        },
        "nft": {
            "eligibility_tag": "design_candidate", "requested_nft_availability": True,
            "eligibility_verified": False, "chain": None, "contract": None,
            "token_id": None,
            "mint_status": "No verified chain binding; no mint performed by this pipeline",
        },
        "evidence": evidence,
        "source_timestamp_utc": _utc(_regular(Path(source["blend"]["path"])).st_mtime),
        "mapping_gaps": [
            "Canonical collection/chain/contract/token mapping unresolved",
            "Rights/technical/media release review remains pending",
        ],
    }


def csv_bytes(native: dict[str, Any]) -> bytes:
    """The R18 write_catalog byte contract: insertion order, UTF-8, CRLF."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
    writer.writeheader()
    for identity, row in native["item_records"].items():
        writer.writerow(dict(zip(COLUMNS, [
            identity + " " + row["name"], "Prop",
            "living_trash_art" if row["kind"] == "toter" else "skull_sculpture",
            "DaedalusDiscovery", "project", "native_saved_sandbox", "REVIEW",
            row["source"]["blend"]["path"],
            ";".join(part["asset"] for part in row["imports"]),
            native["world"].split(".")[0],
        ])))
    return stream.getvalue().encode("utf-8")


def _native(data: Any, chunk: int) -> dict[str, Any]:
    native = data.get("native", data) if isinstance(data, dict) else None
    if not isinstance(native, dict) or native.get("saved") is not True:
        raise CatalogError("Saved native receipt required (a receipt assertion, not native acceptance)")
    base = f"{R18_ROOT}/R18_C{chunk:04d}"
    name = f"L_GrandCollection_C{chunk:04d}"
    world = base + "/" + name
    if native.get("world") not in (world, world + "." + name):
        raise CatalogError("Native world/chunk identity mismatch")
    if "chunk" in native and (type(native["chunk"]) is not int or native["chunk"] != chunk):
        raise CatalogError("Native chunk identity mismatch")
    records = native.get("item_records")
    if not isinstance(records, dict) or not records or len(records) > MAX_ITEMS:
        raise CatalogError("Nonempty native item_records required")
    assets: set[str] = set()
    for identity, row in records.items():
        if not isinstance(row, dict) or not isinstance(identity, str) or not identity:
            raise CatalogError("Malformed native identity")
        if row.get("id") != identity or row.get("catalog_identity") != identity:
            raise CatalogError(f"Retained identity/catalog identity mismatch: {identity}")
        if row.get("kind") not in ("skull", "toter") or row.get("native_saved") is not True:
            raise CatalogError(f"Invalid kind or unsaved item: {identity}")
        if not isinstance(row.get("name"), str) or type(row.get("index")) is not int or row["index"] <= 0:
            raise CatalogError(f"Malformed retained name/index: {identity}")
        source = row.get("source")
        if not isinstance(source, dict) or source.get("id") != identity:
            raise CatalogError(f"Source identity mismatch: {identity}")
        if source.get("kind") != row["kind"] or source.get("index") != row.get("index"):
            raise CatalogError(f"Source kind/index mismatch: {identity}")
        if "expansion_wave" in source and (
            type(source["expansion_wave"]) is not int or source["expansion_wave"] != chunk
        ):
            raise CatalogError(f"Source expansion_wave/chunk mismatch: {identity}")
        source_parts = source.get("parts")
        if not isinstance(source_parts, list) or not source_parts or len(source_parts) > MAX_PARTS:
            raise CatalogError(f"Missing or oversized source parts: {identity}")
        imports = row.get("imports")
        if not isinstance(imports, list) or len(imports) != len(source_parts):
            raise CatalogError(f"Imported/source parts count mismatch: {identity}")
        groups: set[str] = set()
        fbx_paths: set[str] = set()
        for part, source_part in zip(imports, source_parts):
            if not isinstance(part, dict) or not isinstance(source_part, dict):
                raise CatalogError(f"Malformed imported/source part: {identity}")
            group = source_part.get("group")
            fbx = source_part.get("fbx")
            if not isinstance(group, str) or not group or group in groups:
                raise CatalogError(f"Missing or duplicate source part group: {identity}")
            if not isinstance(fbx, dict) or not isinstance(fbx.get("path"), str) or not fbx["path"]:
                raise CatalogError(f"Missing retained source FBX identity: {identity}")
            if fbx["path"] in fbx_paths:
                raise CatalogError(f"Duplicate source FBX identity: {identity}")
            groups.add(group)
            fbx_paths.add(fbx["path"])
            asset = part.get("asset")
            if not isinstance(asset, str) or not asset.startswith(base + "/") or asset in assets:
                raise CatalogError(f"Missing or duplicate asset identity: {identity}")
            assets.add(asset)
            if part.get("source") != source_part:
                raise CatalogError(f"Imported/source part order or identity differs: {identity}")
            slots = part.get("slots")
            if not isinstance(slots, list) or not slots or len(slots) > MAX_PARTS:
                raise CatalogError(f"Missing retained material slots: {identity}")
            for slot in slots:
                if (not isinstance(slot, dict) or not isinstance(slot.get("native"), str)
                        or not slot["native"].startswith("/Game/")):
                    raise CatalogError(f"Malformed retained material slot: {identity}")
    return native


def _exclusive(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class CatalogExporter:
    """A single-writer, explicit-receipt offline exporter.

    Default reads hash each supplied receipt. ``trust_metadata=True`` allows a
    previously hashed receipt with an unchanged stat tuple to reuse its entries;
    it does not establish continuous content verification. ``full=True`` bypasses
    that reuse. Any interrupted publication leaves pending.json and must be
    reconciled independently, never automatically replayed.
    """

    def __init__(self, output: str | Path, *, trust_metadata: bool = False):
        self.root = Path(output).absolute()
        self.trust_metadata = trust_metadata
        for ancestor in (self.root, *self.root.parents):
            if ancestor.is_symlink() or (ancestor.exists() and getattr(
                ancestor.lstat(), "st_file_attributes", 0
            ) & 0x400):
                raise CatalogError(f"Output symlink/reparse path refused: {ancestor}")
        if not self.root.exists():
            self.root.mkdir(parents=True)
            _exclusive(self.root / "offline-catalog.json", _json_bytes({"schema": SCHEMA}))
        marker = self.root / "offline-catalog.json"
        if not marker.exists() or _decode(_read_stable(marker)[0]) != {"schema": SCHEMA}:
            raise CatalogError("Refuse existing directory without exact offline catalog marker")
        if (self.root / "pending.json").exists():
            raise CatalogError("Uncertain pending publication; preserve and reconcile, no replay")
        if (self.root / "writer.lock").exists():
            raise CatalogError("Existing writer lock; preserve and reconcile, no probe or replay")
        database = self.root / "index.sqlite3"
        if database.exists():
            _regular(database)
        self.db = sqlite3.connect(database, timeout=0)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                identity TEXT PRIMARY KEY, stable_id TEXT UNIQUE NOT NULL,
                fingerprint TEXT NOT NULL, payload TEXT NOT NULL, ordinal INTEGER UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS receipts (
                path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
                stamp TEXT NOT NULL, chunk INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks (
                number INTEGER PRIMARY KEY, csv_sha256 TEXT NOT NULL,
                delta_sha256 TEXT NOT NULL, item_count INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.db.commit()
        self._check_current()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> CatalogExporter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _check_current(self) -> None:
        row = self.db.execute("SELECT value FROM metadata WHERE key='current'").fetchone()
        path = self.root / "current.json"
        if row is None:
            if path.exists() or self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]:
                raise CatalogError("Current pointer/index mismatch; reconcile retained publication")
        elif not path.exists() or _read_stable(path)[0] != row[0].encode("utf-8"):
            raise CatalogError("Current pointer/index mismatch; reconcile retained publication")

    def _verify_chunk(self, number: int) -> None:
        row = self.db.execute(
            "SELECT csv_sha256,delta_sha256 FROM chunks WHERE number=?", (number,)
        ).fetchone()
        if row is None:
            raise CatalogError("Retained receipt references missing chunk index")
        for name, expected in ((f"Chunk{number:04d}.catalog-staging.csv", row[0]),
                               (f"Chunk{number:04d}.items-delta.json", row[1])):
            raw, _ = _read_stable(self.root / name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise CatalogError(f"Published chunk changed: {name}")

    def _audit_index(self) -> list[dict[str, Any]]:
        """Full stop/checkpoint readback of immutable segments and lookup cache."""
        retained: list[dict[str, Any]] = []
        for number, expected_count in self.db.execute(
            "SELECT number,item_count FROM chunks ORDER BY number"
        ):
            self._verify_chunk(number)
            raw, _ = _read_stable(self.root / f"Chunk{number:04d}.items-delta.json")
            delta = _decode(raw)
            rows = delta.get("items")
            if delta.get("chunk") != number or not isinstance(rows, list) or len(rows) != expected_count:
                raise CatalogError("Retained delta identity/count mismatch")
            retained.extend(rows)
        indexed = self.db.execute(
            "SELECT identity,stable_id,fingerprint,payload FROM items ORDER BY ordinal"
        ).fetchall()
        if len(retained) != len(indexed):
            raise CatalogError("Lookup cache/delta item count differs")
        for item, row in zip(retained, indexed):
            expected = (item["record_key"], item["stable_item_id"], immutable(item))
            if row[:3] != expected or _decode(row[3]) != item:
                raise CatalogError("Lookup cache differs from immutable delta; reconcile cache")
        return retained

    def export_chunk(self, receipt_pin: dict[str, Any], chunk: int, *,
                     full: bool = False) -> dict[str, Any]:
        """Serialize every export path, including receipt reuse/cache updates."""
        lock = self.root / "writer.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise CatalogError("Existing writer lock; no probe, deletion or concurrent replay") from error
        os.close(fd)
        try:
            return self._export_chunk_locked(receipt_pin, chunk, full=full)
        finally:
            if not (self.root / "pending.json").exists():
                lock.unlink()

    def _export_chunk_locked(self, receipt_pin: dict[str, Any], chunk: int, *,
                             full: bool) -> dict[str, Any]:
        if type(chunk) is not int or chunk <= 0:
            raise CatalogError("Positive integer chunk required")
        if not isinstance(receipt_pin, dict) or not isinstance(receipt_pin.get("path"), str):
            raise CatalogError("Explicit {path,bytes,sha256} receipt pin required")
        expected_size, expected_hash = receipt_pin.get("bytes"), receipt_pin.get("sha256")
        if type(expected_size) is not int or expected_size < 0 or not isinstance(expected_hash, str):
            raise CatalogError("Malformed receipt pin")
        if expected_size > MAX_RECEIPT_BYTES:
            raise CatalogError(f"Receipt exceeds {MAX_RECEIPT_BYTES}-byte bound")
        if len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
            raise CatalogError("Lowercase SHA256 receipt pin required")
        path = Path(receipt_pin["path"]).absolute()
        before = _regular(path)
        if before.st_size != expected_size:
            raise CatalogError("Receipt bytes differ from explicit pin (size before read)")
        seen = self.db.execute(
            "SELECT sha256,bytes,stamp,chunk FROM receipts WHERE path=?", (str(path),)
        ).fetchone()
        if seen is not None and seen[3] != chunk:
            raise CatalogError("Receipt path already assigned to another retained chunk")
        self._check_current()
        if (self.root / "pending.json").exists():
            raise CatalogError("Uncertain pending publication; no replay")
        if full:
            self._audit_index()
        if (seen and self.trust_metadata and not full and seen == (
                expected_hash, expected_size, _stamp(before), chunk)):
            self._verify_chunk(chunk)
            return self._report(chunk, reused=True, hashed=0, new=0, metadata_reused=True)
        raw, observed = _read_stable(path, limit=MAX_RECEIPT_BYTES)
        if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise CatalogError("Receipt bytes differ from explicit pin")
        try:
            native = _native(_decode(raw), chunk)
            evidence = {
                "path": receipt_pin["path"], "bytes": len(raw), "sha256": expected_hash,
                "modified_utc": _utc(observed.st_mtime),
            }
            candidates = [active_item(key, row, native["world"], evidence)
                          for key, row in native["item_records"].items()]
            csv_raw = csv_bytes(native)
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise CatalogError(f"Malformed retained receipt: {error}") from error
        new: list[dict[str, Any]] = []
        for item in candidates:
            prior = self.db.execute(
                "SELECT fingerprint FROM items WHERE identity=?", (item["record_key"],)
            ).fetchone()
            if prior and prior[0] != immutable(item):
                raise CatalogError(f"Append-only identity/assembly collision: {item['record_key']}")
            alias = self.db.execute(
                "SELECT identity FROM items WHERE stable_id=?", (item["stable_item_id"],)
            ).fetchone()
            if alias and alias[0] != item["record_key"]:
                raise CatalogError(f"Stable item ID already belongs to {alias[0]}")
            if prior is None:
                new.append(item)
        existing = self.db.execute("SELECT number FROM chunks WHERE number=?", (chunk,)).fetchone()
        csv_path = self.root / f"Chunk{chunk:04d}.catalog-staging.csv"
        if existing:
            self._verify_chunk(chunk)
            if _read_stable(csv_path)[0] != csv_raw or new:
                raise CatalogError("Existing chunk identity/order/CSV differs; never replace")
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO receipts VALUES (?,?,?,?,?)", (
                    str(path), expected_hash, len(raw), _stamp(observed), chunk,
                ))
            return self._report(chunk, reused=True, hashed=len(raw), new=0, metadata_reused=False)
        if not new:
            raise CatalogError("New chunk contains no new item identities; refuse duplicate count")
        if len(new) != len(candidates):
            raise CatalogError("New chunk overlaps existing item identities")
        if seen is not None:
            raise CatalogError("Receipt path already assigned to another retained chunk")
        highest = self.db.execute("SELECT MAX(number) FROM chunks").fetchone()[0]
        if highest is not None and chunk <= highest:
            raise CatalogError("Chunk order must be strictly increasing")
        delta_path = self.root / f"Chunk{chunk:04d}.items-delta.json"
        if csv_path.exists() or delta_path.exists():
            raise CatalogError("Unindexed existing chunk output; uncertain publication, no replay")
        delta_raw = _json_bytes({
            "schema": "daedalus-item-catalog-delta/1", "chunk": chunk,
            "items": new, "offline_source_only": True,
        })
        delta_sha = hashlib.sha256(delta_raw).hexdigest()
        csv_sha = hashlib.sha256(csv_raw).hexdigest()
        count = self.db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        prior_pointer = self.db.execute("SELECT value FROM metadata WHERE key='current'").fetchone()
        current = {
            "schema": SCHEMA, "chunk": chunk, "item_records": count + len(new),
            "delta_path": delta_path.name, "delta_sha256": delta_sha,
            "csv_path": csv_path.name, "csv_sha256": csv_sha,
            "previous_current_sha256": hashlib.sha256(prior_pointer[0].encode()).hexdigest()
            if prior_pointer else None,
            "offline_source_only": True, "native_acceptance_performed": False,
        }
        current_raw = _json_bytes(current)
        try:
            self._check_current()
            now_pointer = self.db.execute("SELECT value FROM metadata WHERE key='current'").fetchone()
            if now_pointer != prior_pointer:
                raise CatalogError("Catalog advanced while preparing; re-evaluate supplied input")
            _exclusive(self.root / "pending.json", _json_bytes({
                "chunk": chunk, "receipt_sha256": expected_hash,
                "reason": "Publication in progress; reconcile if retained",
            }))
            _exclusive(csv_path, csv_raw)
            _exclusive(delta_path, delta_raw)
            with self.db:
                for offset, item in enumerate(new):
                    self.db.execute("INSERT INTO items VALUES (?,?,?,?,?)", (
                        item["record_key"], item["stable_item_id"], immutable(item),
                        json.dumps(item), count + offset,
                    ))
                self.db.execute("INSERT INTO chunks VALUES (?,?,?,?)", (
                    chunk, csv_sha, delta_sha, len(new),
                ))
                self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?)", (
                    str(path), expected_hash, len(raw), _stamp(observed), chunk,
                ))
                self.db.execute("INSERT OR REPLACE INTO metadata VALUES ('current',?)", (
                    current_raw.decode("utf-8"),
                ))
            temporary = self.root / (".current-" + uuid.uuid4().hex)
            _exclusive(temporary, current_raw)
            temporary.replace(self.root / "current.json")
            (self.root / "pending.json").unlink()
        except Exception:
            # pending.json and the owned lock intentionally survive uncertainty.
            raise
        return self._report(chunk, reused=False, hashed=len(raw), new=len(new), metadata_reused=False)

    def _report(self, chunk: int, *, reused: bool, hashed: int, new: int,
                metadata_reused: bool) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "chunk": chunk, "reused_unchanged_export": reused,
            "new_item_records": new, "receipt_bytes_hashed": hashed,
            "metadata_cache_reused": metadata_reused,
            "trust_assumption": "Opt-in stat metadata reuse can miss metadata-preserving changes; use full=True to rehash"
            if self.trust_metadata else "Every supplied receipt hashed against its explicit pin",
            "global_snapshot_rewritten": False, "native_acceptance_performed": False,
            "csv_path": str(self.root / f"Chunk{chunk:04d}.catalog-staging.csv"),
            "current_path": str(self.root / "current.json"),
        }

    def snapshot(self, name: str = "catalog-snapshot.json") -> dict[str, Any]:
        """Explicit stop/export checkpoint; creates a cumulative snapshot once."""
        lock = self.root / "writer.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise CatalogError("Existing writer lock; snapshot refused") from error
        os.close(fd)
        try:
            return self._snapshot_locked(name)
        finally:
            if not (self.root / "pending.json").exists():
                lock.unlink()

    def _snapshot_locked(self, name: str) -> dict[str, Any]:
        if Path(name).name != name or not name.endswith(".json") or name in (
            "current.json", "pending.json", "offline-catalog.json",
        ):
            raise CatalogError("Fresh simple .json snapshot filename required")
        if (self.root / "pending.json").exists():
            raise CatalogError("Uncertain or concurrent publication; snapshot refused")
        self._check_current()
        items = self._audit_index()
        raw = _json_bytes({
            "schema": "daedalus-item-catalog-offline-snapshot/1", "items": items,
            "item_records": len(items), "offline_source_only": True,
            "native_acceptance_performed": False,
        })
        target = self.root / name
        if target.exists():
            if _read_stable(target)[0] != raw:
                raise CatalogError("Existing snapshot differs; choose a fresh name")
        else:
            _exclusive(target, raw)
        return {"path": str(target), "sha256": hashlib.sha256(raw).hexdigest(),
                "item_records": len(items), "native_acceptance_performed": False}
