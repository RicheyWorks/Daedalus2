# SPDX-License-Identifier: MIT
"""Opt-in adoption points for the existing CodexContest delivery host.

The caller owns native admission, a compatible initialized client, source pins,
geometry checks, saving, and editor lifecycle. This module registers no toolset,
starts no server, changes no protocol/settings, and performs no automatic retry.
The original import route remains the default. Read audits qualify class/tags
and metadata; they do not qualify geometry, source units, or disk persistence.
"""
from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
import re

from . import asset_receipt_audit as receipt_audit
from . import transport

STATIC_MESH_TOOLS = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
QUALIFIED_PROTOCOL = "2025-06-18"
# Exact alias observed in the retained unit-qualified import/save/reopen run.
# Loading/registering the pinned wrapper under this alias remains external.
UNIT_QUALIFIED_TOOLS = "daedalus_unit_tools.unit_qualified_static_toolset.UnitQualifiedStaticMeshTools"
_IMPORT_STRINGS = ("folder_path", "asset_name", "source_file")
_IMPORT_FLAGS = ("import_materials", "import_textures", "combine_meshes")


class DeliveryAuditError(RuntimeError):
    """The audit receipt was retained, but delivery completion is not allowed."""

    def __init__(self, report, report_path):
        self.report, self.report_path = report, Path(report_path)
        super().__init__("official post-save audit failed; inspect " + str(self.report_path))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _unit_import_schema(description):
    """Validate the one published wrapper, not arbitrary callable tool schemas."""
    _require(isinstance(description, dict) and description.get("name") == UNIT_QUALIFIED_TOOLS,
             "the admitted unit-qualified toolset is not available")
    rows = description.get("tools")
    _require(isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict)
             and rows[0].get("name") == UNIT_QUALIFIED_TOOLS + ".import_file", "unit tool inventory differs")
    inputs = rows[0].get("inputSchema")
    _require(isinstance(inputs, dict) and inputs.get("type") == "object"
             and isinstance(inputs.get("properties"), dict)
             and set(inputs["properties"]) == set(_IMPORT_STRINGS + _IMPORT_FLAGS)
             and isinstance(inputs.get("required"), list)
             and len(inputs["required"]) == 3 and set(inputs["required"]) == set(_IMPORT_STRINGS),
             "unit import argument fields differ")
    for name in _IMPORT_STRINGS + _IMPORT_FLAGS:
        spec = inputs["properties"][name]
        _require(isinstance(spec, dict) and spec.get("type") == ("string" if name in _IMPORT_STRINGS else "boolean"),
                 "unit import argument type differs: " + name)
    output = rows[0].get("outputSchema")
    _require(isinstance(output, dict) and output.get("type") == "object"
             and isinstance(output.get("properties"), dict) and set(output["properties"]) == {"returnValue"}
             and output.get("required") == ["returnValue"], "unit import result wrapper differs")
    array = output["properties"]["returnValue"]
    _require(isinstance(array, dict) and array.get("type") == "array", "unit import must return object references")
    ref = array.get("items")
    _require(isinstance(ref, dict) and ref.get("type") == "object"
             and ref.get("title") == "/Script/CoreUObject.Object"
             and isinstance(ref.get("properties"), dict) and set(ref["properties"]) == {"refPath"}
             and ref.get("required") == ["refPath"]
             and isinstance(ref["properties"]["refPath"], dict)
             and ref["properties"]["refPath"].get("type") == "string", "unit import reference shape differs")


def import_static_file(client, *, folder_path, asset_name, source_file,
                       import_materials=False, import_textures=False, combine_meshes=True,
                       unit_qualified=False):
    """Call the original route, or explicitly select the qualified FBX wrapper.

    The opt-in path performs live describe before its one effectful call. An
    absent wrapper, incompatible client/protocol, bad schema, or import failure
    stops delivery; the legacy importer is never used as a fallback. The caller
    still checks geometry/materials and explicitly saves the returned assets.
    """
    _require(type(unit_qualified) is bool, "unit_qualified must be an explicit boolean")
    arguments = dict(folder_path=folder_path, asset_name=asset_name, source_file=source_file,
                     import_materials=import_materials, import_textures=import_textures, combine_meshes=combine_meshes)
    if not unit_qualified:
        return client.call(STATIC_MESH_TOOLS, "import_file", **arguments)
    _require(isinstance(folder_path, str)
             and re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)+", folder_path) is not None
             and folder_path.startswith(receipt_audit.OWNED_ROOT + "/"), "unit import leaves CodexContest ownership")
    _require(isinstance(asset_name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", asset_name) is not None,
             "unit import requires one canonical asset name")
    _require(isinstance(source_file, str), "unit import requires a source filename string")
    source = Path(source_file)
    _require(source.suffix.lower() == ".fbx" and source.is_file(), "unit import requires an existing FBX file")
    _require(all(type(arguments[name]) is bool for name in _IMPORT_FLAGS), "unit import flags must be booleans")
    _unit_import_schema(client.describe(UNIT_QUALIFIED_TOOLS))
    result = client.call(UNIT_QUALIFIED_TOOLS, "import_file", **arguments)
    _require(isinstance(result, list) and 0 < len(result) <= receipt_audit.MAX_ASSETS,
             "unit import returned no bounded asset references; reconcile without replay")
    packages = []
    for ref in result:
        _require(isinstance(ref, dict) and set(ref) == {"refPath"} and isinstance(ref["refPath"], str),
                 "unit import returned a malformed reference; reconcile without replay")
        package, dot, leaf = ref["refPath"].partition(".")
        _require(dot and re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)+", package) is not None
                 and package.rsplit("/", 1)[0] == folder_path and leaf == package.rsplit("/", 1)[1],
                 "unit import returned a foreign/noncanonical asset; reconcile without replay")
        packages.append(package)
    _require(len(packages) == len(set(packages)), "unit import returned duplicate assets; reconcile without replay")
    return result


def _receipt_time(value):
    _require(isinstance(value, str), "audit receipt timestamp is missing")
    result = datetime.fromisoformat(value)
    _require(result.tzinfo is not None and result.utcoffset() is not None, "audit timestamp must carry a timezone")
    return result


class _RecordedAudit(receipt_audit._Session):
    """Validate retained bytes through the auditor's existing pure validators.

    There is no opener, socket, native call, retry, or reconstructed success.
    The inherited meta/read_asset and _discover checks run against the recorded
    operations. Shapes/order come from _Session/audit and the qualified R1
    eight-operation receipt; no alternate polling or call sequence is accepted.
    """

    def __init__(self, operations, begin, end):
        _require(isinstance(operations, list) and 0 < len(operations) <= 6 + 3 * receipt_audit.MAX_ASSETS,
                 "audit operations are absent or exceed the finite profile")
        self.operations, self.index, self.counter = operations, 0, 0
        self.previous_end, self.end, self.received_bytes = begin, end, 0

    def exchange(self, label, method=None, params=None, http_method="POST", notification=False):
        self.counter += 1
        body = None
        if http_method == "POST":
            body = {"jsonrpc": "2.0", "method": method}
            if not notification:
                body["id"] = self.counter
            if params is not None:
                body["params"] = params
        _require(self.index < len(self.operations), "audit operation sequence is incomplete")
        operation = self.operations[self.index]
        self.index += 1
        _require(isinstance(operation, dict) and "error" not in operation
                 and {"label", "started_utc", "ended_utc", "http_method", "request", "status", "response",
                      "raw_text", "headers", "session_header_received", "response_bytes", "response_sha256"} <= set(operation)
                 and operation.get("label") == label and operation.get("http_method") == http_method
                 and operation.get("request") == body, "audit operation order/request/error differs")
        if body is not None and "id" in body:
            _require(type(operation["request"].get("id")) is int, "audit request id must be an integer")
        begin, end = _receipt_time(operation.get("started_utc")), _receipt_time(operation.get("ended_utc"))
        _require(self.previous_end <= begin <= end <= self.end, "audit operation timestamps are inconsistent")
        self.previous_end = end
        status = 202 if notification or http_method == "DELETE" else 200
        _require(type(operation.get("status")) is int and operation["status"] == status,
                 "audit HTTP completion status differs")
        _require(type(operation.get("session_header_received")) is bool
                 and (label != "initialize" or operation["session_header_received"] is True),
                 "audit session negotiation evidence is absent")
        headers = operation.get("headers")
        _require(isinstance(headers, dict)
                 and all(isinstance(key, str) and isinstance(value, str) for key, value in headers.items()),
                 "audit response headers are malformed")
        lower_headers = {key.lower(): value for key, value in headers.items()}
        _require(len(lower_headers) == len(headers), "audit response header names are duplicated")
        length = lower_headers.get("content-length")
        _require(isinstance(length, str) and re.fullmatch(r"0|[1-9][0-9]*", length) is not None,
                 "qualified audit response lacks canonical Content-Length")
        text = operation.get("raw_text")
        _require(isinstance(text, str), "audit raw response evidence is missing")
        raw = text.encode("utf-8")
        _require(len(raw) == int(length) <= receipt_audit.MAX_RESPONSE_BYTES
                 and type(operation.get("response_bytes")) is int and operation["response_bytes"] == len(raw)
                 and operation.get("response_sha256") == hashlib.sha256(raw).hexdigest(),
                 "audit response byte/length/hash evidence differs")
        self.received_bytes += len(raw)
        _require(self.received_bytes <= receipt_audit.MAX_TOTAL_RESPONSE_BYTES, "audit response budget differs")
        if status == 202:
            _require(not raw and operation.get("response") is None, "audit notification/DELETE is not a complete empty response")
            return None
        receipt_audit._strict_wire(raw)
        reply = transport._decode_reply(raw, self.counter, len(raw), int(length))
        _require(isinstance(reply, dict) and set(reply) == {"jsonrpc", "id", "result"}
                 and operation.get("response") == reply, "audit JSON-RPC response is erroneous or differs from wire bytes")
        return reply["result"]


def _completed_audit(report, contract, endpoint):
    _require(isinstance(report, dict) and report.get("schema") == receipt_audit.RESULT_SCHEMA
             and report.get("outcome") == "PASS" and report.get("contract") == contract and "error" not in report
             and receipt_audit.PROTOCOL == QUALIFIED_PROTOCOL and report.get("protocol") == QUALIFIED_PROTOCOL
             and report.get("endpoint") == endpoint
             and type(report.get("asset_writes")) is int and report["asset_writes"] == 0,
             "audit success/protocol/endpoint/contract evidence differs")
    cleanup = report.get("cleanup")
    _require(isinstance(cleanup, dict) and "error" not in cleanup
             and cleanup.get("attempted") is True and cleanup.get("confirmed") is True,
             "audit cleanup is incomplete")
    begin, end = _receipt_time(report.get("started_utc")), _receipt_time(report.get("ended_utc"))
    _require(begin <= end, "audit report timestamps are inconsistent")
    recorded = _RecordedAudit(report.get("operations"), begin, end)
    initialized = recorded.exchange("initialize", "initialize", {"protocolVersion": QUALIFIED_PROTOCOL,
        "capabilities": {}, "clientInfo": {"name": "daedalus-asset-receipt-audit", "version": "1"}})
    _require(isinstance(initialized, dict) and initialized.get("protocolVersion") == QUALIFIED_PROTOCOL,
             "audit negotiated protocol differs")
    recorded.exchange("initialized", "notifications/initialized", {}, notification=True)
    receipt_audit._discover(recorded, any(row["required_metadata"] for row in contract["assets"]))
    observed = report.get("assets")
    _require(isinstance(observed, list) and len(observed) == len(contract["assets"]), "audited asset inventory differs")
    for row, wanted in zip(observed, contract["assets"]):
        path, expected_class = wanted["asset_path"], wanted["expected_class"]
        _require(isinstance(row, dict) and row.get("verified") is True and row.get("asset_path") == path
                 and row.get("expected_class") == expected_class, "audited asset identity/completion differs")
        actual_class = recorded.read_asset("get_asset_class", path)
        tags = receipt_audit._string_map(recorded.read_asset("get_asset_tags", path), "recorded registry tags")
        metadata = (receipt_audit._string_map(recorded.read_asset("get_metadata_tags", path), "recorded metadata")
                    if wanted["required_metadata"] else {})
        _require(actual_class == expected_class and row.get("actual_class") == actual_class
                 and row.get("registry_tags") == tags and row.get("metadata") == metadata
                 and all(metadata.get(key) == value for key, value in wanted["required_metadata"].items()),
                 "claimed asset readback differs from complete recorded responses")
    recorded.exchange("delete-session", http_method="DELETE")
    _require(recorded.index == len(recorded.operations), "audit contains extra/duplicate/poll operations")


def audit_saved_receipt(saved_path, output_path, *, endpoint, namespace,
                        required_metadata=None, timeout=15, opener=None):
    """Gate host completion on the proven audit of its exact saved receipt.

    Only the existing delivery/prepared save profiles are accepted. The new
    sidecar is reserved exclusively before connection; neither prior audit
    evidence nor the fingerprinted producer receipt is overwritten. FAIL,
    malformed completion evidence, or cleanup failure raises with the retained
    report. Admission/lease checks remain the invoking operator's responsibility.
    """
    contract = receipt_audit.template_from_saved(saved_path, namespace)
    if required_metadata is not None:
        for row in contract["assets"]:
            row["required_metadata"] = dict(required_metadata)
    contract = receipt_audit.validate_contract(contract)
    output = Path(output_path).resolve()
    _require(output != Path(contract["source_receipt"]["path"]), "audit cannot overwrite its source receipt")
    with output.open("x", encoding="utf-8") as stream:
        try:
            report = receipt_audit.audit(contract, endpoint=endpoint, timeout=timeout, opener=opener)
        except Exception as error:
            report = {"schema": receipt_audit.RESULT_SCHEMA, "outcome": "FAIL", "contract": contract,
                      "error": type(error).__name__ + ": " + str(error), "assets": [], "operations": [],
                      "asset_writes": 0, "cleanup": {"attempted": False, "confirmed": False}}
        if not isinstance(report, dict):
            report = {"schema": receipt_audit.RESULT_SCHEMA, "outcome": "FAIL", "contract": contract,
                      "error": "auditor returned a malformed report", "returned_report": report}
        try:
            _completed_audit(report, contract, endpoint)
            accepted = True
        except Exception as error:
            accepted = False
            report["outcome"] = "FAIL"
            report.setdefault("error", "audit completion evidence rejected: " + type(error).__name__ + ": " + str(error))
        json.dump(report, stream, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if not accepted:
        raise DeliveryAuditError(report, output)
    return report
