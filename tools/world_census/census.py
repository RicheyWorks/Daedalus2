# SPDX-License-Identifier: MIT
"""Count exported definitions without reading geometry, assets, or live services."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_MANIFESTS = 128


class CensusError(ValueError):
    """An input, binding, or fresh-output contract was refused."""


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise CensusError(f"{label}: expected an object")
    return value


def _list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise CensusError(f"{label}: expected an array")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise CensusError(f"{label}: expected a nonempty string without NUL")
    return value


def _integer(value: Any, label: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise CensusError(f"{label}: expected an integer" + (f" >= {minimum}" if minimum is not None else ""))
    return value


def _keys(value: dict, required: set[str], optional: set[str], label: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing or extra:
        raise CensusError(f"{label}: missing keys {sorted(missing)}; unknown keys {sorted(extra)}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise CensusError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise CensusError(f"nonfinite JSON number: {value}")


def _read(path: Path) -> tuple[dict, str, str]:
    try:
        if not path.is_file():
            raise CensusError(f"{path}: expected an explicitly supplied regular JSON file")
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise CensusError(f"{path}: exceeds {MAX_INPUT_BYTES} byte input limit")
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=_constant)
        data = _object(data, str(path))
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        return data, hashlib.sha256(raw).hexdigest(), hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise CensusError(f"{path}: {exc}") from exc


def _contract(data: dict, expected: str, label: str) -> None:
    if data.get("format") != expected:
        raise CensusError(f"{label}.format: expected {expected}")
    if _integer(data.get("version"), f"{label}.version") != 1:
        raise CensusError(f"{label}.version: only version 1 is supported")


def _manifest(data: dict) -> dict:
    _contract(data, "daedalus-world-package", "manifest")
    world = _object(data.get("world"), "manifest.world")
    result = {key: _text(world.get(key), f"world.{key}") for key in ("id", "style", "title")}
    result.update(seed=_integer(world.get("seed"), "world.seed"),
                  revision=_integer(world.get("revision"), "world.revision", 0), realm_id=None)
    slots = set()
    for island in _list(data.get("islands", []), "manifest.islands"):
        slot = _integer(_object(island, "island").get("slot"), "island.slot", 0)
        if slot in slots:
            raise CensusError(f"world {result['id']}: duplicate island slot {slot}")
        slots.add(slot)
    result["islands"] = [{"slot": slot, "asset_definitions": 0} for slot in sorted(slots)]
    assets = {}
    for item in _list(data.get("assets", []), "manifest.assets"):
        asset = _object(item, "asset")
        record = {key: _text(asset.get(key), f"asset.{key}") for key in ("name", "file", "use")}
        file = record["file"]
        parts = PurePosixPath(file).parts
        if file.startswith("/") or "\\" in file or ":" in file or any(p in (".", "..") for p in file.split("/")) or "" in file.split("/") or not parts:
            raise CensusError(f"asset.file: expected a relative package path: {file}")
        key = (record["name"], file)
        if key in assets:
            raise CensusError(f"world {result['id']}: duplicate asset identity {key}")
        assets[key] = dict(record, island_slot=None)
    result["assets"] = [assets[key] for key in sorted(assets)]
    result["asset_definitions"] = len(assets)
    result["assets_without_island"] = len(assets)
    return result


def _bind(worlds: dict[str, dict], data: dict) -> None:
    _contract(data, "daedalus-world-census-bindings", "bindings")
    _keys(data, {"format", "version", "worlds"}, set(), "bindings")
    seen = set()
    for row in _list(data["worlds"], "bindings.worlds"):
        row = _object(row, "world binding")
        _keys(row, {"world_id", "revision"}, {"realm_id", "assets"}, "world binding")
        identity = _text(row["world_id"], "binding.world_id")
        if identity in seen:
            raise CensusError(f"duplicate world binding: {identity}")
        seen.add(identity)
        if identity not in worlds:
            raise CensusError(f"binding references unknown world: {identity}")
        world = worlds[identity]
        if _integer(row["revision"], "binding.revision", 0) != world["revision"]:
            raise CensusError(f"world {identity}: binding revision does not match manifest")
        if "realm_id" in row:
            world["realm_id"] = _text(row["realm_id"], "binding.realm_id")
        assets = {(a["name"], a["file"]): a for a in world["assets"]}
        islands = {i["slot"]: i for i in world["islands"]}
        placed = set()
        for item in _list(row.get("assets", []), "binding.assets"):
            item = _object(item, "asset binding")
            _keys(item, {"name", "file", "island_slot"}, set(), "asset binding")
            key = (_text(item["name"], "binding.name"), _text(item["file"], "binding.file"))
            if key not in assets:
                raise CensusError(f"world {identity}: binding references unknown asset {key}")
            if key in placed:
                raise CensusError(f"world {identity}: duplicate asset binding {key}")
            placed.add(key)
            slot = _integer(item["island_slot"], "binding.island_slot", 0)
            if slot not in islands:
                raise CensusError(f"world {identity}: binding references unknown island slot {slot}")
            assets[key]["island_slot"] = slot
            islands[slot]["asset_definitions"] += 1
            world["assets_without_island"] -= 1


def build_census(manifests: Sequence[Path], snapshot_date: str, bindings: Path | None = None) -> dict:
    """Validate all supplied inputs and return a deterministic census; never write inputs."""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snapshot_date):
            raise ValueError("expected YYYY-MM-DD")
        date.fromisoformat(snapshot_date)
    except (TypeError, ValueError) as exc:
        raise CensusError(f"snapshot date: expected a valid YYYY-MM-DD date: {snapshot_date}") from exc
    if not 1 <= len(manifests) <= MAX_MANIFESTS:
        raise CensusError(f"supply between 1 and {MAX_MANIFESTS} manifests")
    worlds: dict[str, dict] = {}
    canonical_hashes = {}
    sources = {}
    for path in manifests:
        data, raw_hash, canonical_hash = _read(Path(path))
        world = _manifest(data)
        identity = world["id"]
        if identity in worlds and canonical_hash != canonical_hashes[identity]:
            raise CensusError(f"world {identity}: conflicting manifest or multiple revisions in one snapshot")
        worlds[identity] = world
        canonical_hashes[identity] = canonical_hash
        sources[raw_hash] = {"sha256": raw_hash, "world_id": identity, "revision": world["revision"]}
    bindings_hash = None
    if bindings is not None:
        data, bindings_hash, _ = _read(Path(bindings))
        _bind(worlds, data)
    realm_groups: dict[str | None, dict] = {}
    for world in worlds.values():
        world["source_sha256s"] = sorted(s["sha256"] for s in sources.values() if s["world_id"] == world["id"])
        realm = realm_groups.setdefault(world["realm_id"], {"id": world["realm_id"], "worlds": 0, "islands": 0, "asset_definitions": 0})
        realm["worlds"] += 1
        realm["islands"] += len(world["islands"])
        realm["asset_definitions"] += world["asset_definitions"]
    rows = [worlds[key] for key in sorted(worlds)]
    return {
        "format": "daedalus-world-census", "version": 1, "snapshot_date": snapshot_date,
        "count_semantics": "asset-definitions", "bindings_sha256": bindings_hash,
        "sources": [sources[key] for key in sorted(sources)],
        "totals": {
            "worlds": len(rows), "realms": sum(r is not None for r in realm_groups),
            "islands": sum(len(w["islands"]) for w in rows),
            "asset_definitions": sum(w["asset_definitions"] for w in rows),
            "worlds_without_realm": sum(w["realm_id"] is None for w in rows),
            "assets_without_realm": sum(w["asset_definitions"] for w in rows if w["realm_id"] is None),
            "assets_without_island": sum(w["assets_without_island"] for w in rows),
        },
        "realms": [realm_groups[key] for key in sorted(realm_groups, key=lambda k: (k is not None, k or ""))],
        "worlds": rows,
    }


def render_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


CSV_COLUMNS = ("snapshot_date", "scope", "realm_id", "world_id", "island_slot", "worlds", "realms", "islands",
               "asset_definitions", "assets_without_island", "worlds_without_realm", "assets_without_realm",
               "source_sha256s", "bindings_sha256")


def _cell(value: Any) -> Any:
    if isinstance(value, str) and re.match(r"^[\s\x00-\x1f\ufeff]*[=+\-@]", value):
        return "'" + value
    return value


def render_csv(report: dict) -> str:
    """Spreadsheet-safe daily totals and realm/world/island/unassigned rows; not additive across scopes."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()

    def emit(scope: str, values: dict) -> None:
        row = dict(snapshot_date=report["snapshot_date"], scope=scope, bindings_sha256=report["bindings_sha256"] or "")
        row.update(values)
        writer.writerow({key: _cell(value) for key, value in row.items()})

    hashes = ";".join(s["sha256"] for s in report["sources"])
    emit("total", report["totals"] | {"source_sha256s": hashes})
    for realm in report["realms"]:
        realm_hashes = sorted({h for w in report["worlds"] if w["realm_id"] == realm["id"] for h in w["source_sha256s"]})
        emit("realm", {"realm_id": realm["id"], **{k: v for k, v in realm.items() if k != "id"}, "source_sha256s": ";".join(realm_hashes)})
    for world in report["worlds"]:
        context = {"realm_id": world["realm_id"], "world_id": world["id"], "source_sha256s": ";".join(world["source_sha256s"])}
        emit("world", dict(context, worlds=1, islands=len(world["islands"]), asset_definitions=world["asset_definitions"], assets_without_island=world["assets_without_island"]))
        for island in world["islands"]:
            emit("island", dict(context, island_slot=island["slot"], islands=1, asset_definitions=island["asset_definitions"]))
        emit("unassigned_island", dict(context, asset_definitions=world["assets_without_island"]))
    return stream.getvalue()


def write_reports(report: dict, output_dir: Path) -> tuple[Path, Path]:
    """Reserve a fresh directory; existing outputs and aliases are never replaced."""
    json_text, csv_text = render_json(report), render_csv(report)
    output_dir = Path(output_dir)
    try:
        output_dir.mkdir()  # Exclusive reservation also refuses existing directories and symlinks.
    except OSError as exc:
        raise CensusError(f"fresh output directory required: {output_dir}: {exc}") from exc
    outputs = (output_dir / "census.json", output_dir / "daily.csv")
    try:
        for path, content in zip(outputs, (json_text, csv_text)):
            with path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
    except OSError as exc:
        raise CensusError(f"report write failed; partial new bundle preserved at {output_dir}: {exc}") from exc
    return outputs
