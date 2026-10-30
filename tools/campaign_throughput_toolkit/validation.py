# SPDX-License-Identifier: MIT
"""Reconcile R18 source/native receipts and project one bounded validation pass.

Reuses the existing snapshot consumer. A passing report establishes retained
evidence consistency only: it neither calls native validators nor admits assets.
"""
import math
import re

from tools.unreal_mcp.native_validation_snapshot_consumer import consume, SnapshotError
from .evidence import EvidenceError, read_pinned, decode


def _need(condition, message):
    if not condition:
        raise EvidenceError(message)


def _asset(value):
    _need(isinstance(value, str) and re.fullmatch(r"/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+", value),
          "exact /Game object path required: " + repr(value))
    package, name = value.rsplit(".", 1)
    _need(package.rsplit("/", 1)[-1] == name, "object/package identity mismatch: " + value)
    return value


def _triple(value, where):
    _need(isinstance(value, list) and len(value) == 3 and
          all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in value),
          "three finite nonnegative dimensions required: " + where)
    return value


def validate_chunk(source_pin, receipt_pin, *, roots, expected_chunk, expected_range, expected_ids):
    """Validate exactly ten skulls + ten toters using explicit retained identities.

    Pins use existing {path,bytes,sha256}. ``expected_ids`` is the caller's exact
    retained 20-item selection, never synthesized from a filename or index.
    Every referenced blend and FBX is rehashed. No package-byte claim is possible
    from R18 receipts, which contain no package pins or complete dependency graph.
    """
    _need(type(expected_chunk) is int and expected_chunk > 0, "positive chunk required")
    _need(isinstance(expected_range, list) and len(expected_range) == 2 and
          all(type(v) is int and v > 0 for v in expected_range) and
          expected_range[1] - expected_range[0] == 9, "exact ten-index range required")
    _need(isinstance(expected_ids, list) and len(expected_ids) == 20 and
          all(isinstance(v, str) and v for v in expected_ids) and len(set(expected_ids)) == 20,
          "20 unique retained item IDs required")
    manifest = read_pinned(source_pin, roots, json_document=True)
    receipt = read_pinned(receipt_pin, roots, json_document=True)
    _need(isinstance(manifest, dict) and isinstance(receipt, dict), "source/native objects required")
    _need(manifest.get("chunk") == expected_chunk and manifest.get("range") == expected_range,
          "source chunk/range mismatch")
    _need(manifest.get("held") == [] and manifest.get("counts") == {"skull": 10, "toter": 10},
          "source count/held mismatch")
    items = manifest.get("items")
    _need(isinstance(items, list) and len(items) == 20, "source manifest must contain exactly 20 items")
    _need(all(isinstance(row, dict) for row in items), "invalid source item")
    _need([row.get("id") for row in items] == expected_ids, "source identity/order mismatch")
    _need({(row.get("kind"), row.get("index")) for row in items} ==
          {(kind, index) for kind in ("skull", "toter")
           for index in range(expected_range[0], expected_range[1] + 1)},
          "source kind/index coverage mismatch")
    native = receipt.get("native")
    _need(isinstance(native, dict) and native.get("saved") is True and
          native.get("dirty") == {"maps": [], "content": []} and
          native.get("play") is False and native.get("import_active") is False,
          "exact saved/quiescent native receipt required")
    world = _asset(native.get("world"))
    namespace = "/Game/Daedalus/Sandbox/NativeDiscovery/20261024/R18_C%04d" % expected_chunk
    _need(world == namespace + "/L_GrandCollection_C%04d.L_GrandCollection_C%04d" %
          (expected_chunk, expected_chunk), "native chunk/world mismatch")
    records = native.get("item_records")
    _need(isinstance(records, dict) and list(records) == expected_ids, "native identity/order mismatch")
    checked_files, imported, dependencies = {}, [], []
    item_reports = []

    def source_file(pin):
        _need(isinstance(pin, dict) and isinstance(pin.get("path"), str), "missing source file pin")
        existing = checked_files.get(pin["path"])
        _need(existing is None or existing == pin, "conflicting source pins: " + pin["path"])
        if existing is None:
            read_pinned(pin, roots)
            checked_files[pin["path"]] = pin

    for source in items:
        identity = source["id"]
        row = records[identity]
        _need(isinstance(row, dict) and row.get("id") == identity and row.get("catalog_identity") == identity,
              "retained catalog identity mismatch: " + identity)
        _need(row.get("source") == source and row.get("kind") == source["kind"] and
              row.get("index") == source["index"] and row.get("name") == source.get("name"),
              "source/native manifest mismatch: " + identity)
        _need(source.get("source_created") is True and row.get("native_saved") is True,
              "source/save state mismatch: " + identity)
        _need(row.get("native_admission") == "Valid", "retained item admission held: " + identity)
        source_file(source.get("blend"))
        parts, imports = source.get("parts"), row.get("imports")
        _need(isinstance(parts, list) and parts and isinstance(imports, list) and len(imports) == len(parts),
              "part/import count mismatch: " + identity)
        _need(all(isinstance(part, dict) for part in parts), "invalid source part: " + identity)
        groups = [part.get("group") for part in parts]
        _need(all(isinstance(g, str) and g for g in groups) and len(set(groups)) == len(groups),
              "duplicate/unknown part group: " + identity)
        for part, observed in zip(parts, imports):
            _need(isinstance(observed, dict) and observed.get("source") == part and observed.get("saved") is True,
                  "retained part/source order mismatch: " + identity)
            source_file(part.get("fbx"))
            path = _asset(observed.get("asset"))
            expected_directory = namespace + "/Items/" + identity + "/Parts/" + part["group"]
            _need(isinstance(part.get("name"), str) and re.fullmatch(r"[A-Za-z0-9_]+", part["name"]),
                  "retained source part name required: " + identity)
            # Interchange can shorten the retained source part name. Bind the
            # actual object to the exact item/group destination, never rederive it.
            _need(path.rsplit("/", 1)[0] == expected_directory and path not in imported,
                  "duplicate/out-of-chunk imported asset: " + path)
            imported.append(path)
            dimensions = _triple(part.get("dimensions_m"), identity)
            observed_dimensions = _triple(observed.get("dimensions_cm"), identity)
            _need(max(abs(a - b * 100) for a, b in zip(observed_dimensions, dimensions)) <= .5,
                  "source/native bounds mismatch: " + path)
            slots = observed.get("slots")
            _need(type(part.get("material_slots")) is int and isinstance(slots, list) and
                  len(slots) == part["material_slots"], "material slot count mismatch: " + path)
            for slot in slots:
                _need(isinstance(slot, dict), "invalid material slot: " + path)
                dependencies.append(_asset(slot.get("native")))
            materials = part.get("materials")
            _need(isinstance(materials, list) and all(isinstance(m, str) for m in materials) and
                  all(isinstance(slot.get("source_slot"), str) for slot in slots) and
                  sorted(slot["source_slot"] for slot in slots) == sorted(materials),
                  "source material roles mismatch: " + path)
            triangles = part.get("render_triangles")
            _need(type(triangles) is int and triangles > 0 and type(observed.get("triangles")) is int,
                  "invalid triangle counts: " + path)
            if triangles != observed["triangles"]:
                proof = observed.get("source_render_evidence", {})
                _need(proof.get("build_settings_changed") is False and
                      proof.get("source_triangles") == triangles and proof.get("source_retained") == triangles and
                      proof.get("queried_triangle_coverage") == triangles and
                      proof.get("render_triangles") == observed["triangles"] and
                      proof.get("native_copy_outcome") in
                      ("GeometryScriptOutcomePins.SUCCESS", "<GeometryScriptOutcomePins.SUCCESS: 1>") and
                      type(proof.get("zero_area_source_triangles")) is int and
                      0 <= proof["zero_area_source_triangles"] <= triangles and
                      triangles - proof["zero_area_source_triangles"] == observed["triangles"],
                      "unexplained source/render geometry mismatch: " + path)
        item_reports.append({"id": identity, "parts": len(parts), "source_consistent": True,
                             "retained_native_admission": row.get("native_admission", "unrecorded")})
    _need(type(native.get("native_valid_parts")) is int and native["native_valid_parts"] == len(imported),
          "native valid-part count mismatch")
    admissions = native.get("admission")
    _need(isinstance(admissions, list), "retained native admission groups required")
    covered, retained = [], []
    for index, group in enumerate(admissions):
        _need(isinstance(group, dict), "invalid retained group")
        paths, report = group.get("paths"), group.get("report")
        _need(isinstance(paths, list) and 1 <= len(paths) <= 16 and len(set(paths)) == len(paths),
              "retained group identity/count mismatch")
        _need(not set(paths).intersection(covered) and all(p in imported for p in paths),
              "duplicate/extraneous retained validation paths")
        _need(isinstance(report, dict) and report.get("status") == "Valid" and
              report.get("native_invoked") is True and report.get("accepted") is True and
              report.get("native_return") == 0 and report.get("cancellation_observed") is False,
              "retained native validation envelope held: group %d" % index)
        snapshot = report.get("snapshot_json")
        _need(isinstance(snapshot, str), "canonical snapshot string required")
        # Reject duplicate keys before delegating to the established typed consumer.
        decode(snapshot)
        try:
            result = consume(snapshot)
        except (SnapshotError, TypeError) as exc:
            raise EvidenceError("canonical snapshot malformed: " + str(exc)) from exc
        _need(result.accepted and list(result.snapshot.requested_assets) == paths,
              "canonical snapshot identity/result mismatch: group %d" % index)
        _need(result.snapshot.results.counts["NumExternalObjects"] == 0,
              "unexpected expanded validation scope")
        _need(result.snapshot.settings.validation_usecase == "EDataValidationUsecase::Script" and
              all(detail.package_name == detail.object_path.split(".")[0] and
                  detail.asset_name == detail.object_path.split(".")[1]
                  for detail in result.snapshot.results.details),
              "canonical snapshot detail/settings identity mismatch")
        covered.extend(paths)
        retained.append({"group": index, "paths": paths, "consumer": result.to_dict()})
    _need(set(covered) == set(imported), "retained validation coverage mismatch")
    declared = native.get("assets")
    _need(isinstance(declared, list), "native asset dependency references required")
    dependency_refs = list(dict.fromkeys(imported + dependencies + [_asset(p) for p in declared]))
    new_refs = [p for p in dependency_refs if p.startswith(namespace + "/")]
    batches = [new_refs[offset:offset + 16] for offset in range(0, len(new_refs), 16)]
    return {"schema": "daedalus-offline-chunk-validation/1", "status": "retained_evidence_consistent",
            "chunk": expected_chunk, "range": expected_range, "items": item_reports,
            "source_manifest": source_pin, "native_receipt": receipt_pin,
            "files_rehashed": len(checked_files) + 2, "imported_parts": len(imported),
            "retained_validation": retained, "native_invoked": False, "native_admission": False,
            "proposal": {"method": "DaedalusEditorAcceptanceLibrary.validate_named_assets",
                         "allowed_package_root": namespace, "cancel_requested": False,
                         "batches": batches, "one_call_per_named_asset": True,
                         "reused_external_references": [p for p in dependency_refs if p not in new_refs],
                         "unvalidated_new_references": [p for p in new_refs if p not in covered],
                         "dependency_scope": "receipt-reference closure; complete native dependency graph unproven",
                         "boss_review_required": True},
            "limitations": ["Retained pins establish consistency, not authenticity or current custody.",
                            "No native validator execution, package-byte parity or full dependency graph proof.",
                            "Validator implementation/set parity, current build and live adoption remain pending."]}
