# SPDX-License-Identifier: MIT
"""Read-only official MCP audit of exact assets in a retained save receipt.

Offline contract creation (no editor connection)::

    python -m tools.unreal_mcp.asset_receipt_audit template --saved-receipt saved.json --out audit.json

During a separately admitted editor turn::

    python -m tools.unreal_mcp.asset_receipt_audit audit --contract audit.json --out result.json

Two existing producer profiles are accepted: delivery receipts with
``saved_unreal=true``, ``meshes`` and covering ``save_packages`` after batch save;
and prepared ingestion receipts with saved group/mesh counts and confirmed
``results[].meshes[].save_return``. A narrower --namespace selects exact receipt
paths, preserving package or object form without guessing object names. Contracts
can require explicit metadata values; registry tag keys are never assumed.
This does not import, save, execute scripts, start servers, or qualify disk bytes.
An external sole operator must admit the live run; this module does not acquire
an editor lease or prove map/PIE/dirty-package/other-writer guards.
Only automation discovery/status has been live-proven by the prerequisite probe;
AssetTools must pass this auditor's own discovery and readback on a future run.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

if __package__:
    from .transport import read_response
else:
    from transport import read_response

PROTOCOL = "2025-06-18"
ASSET_TOOLSET = "editor_toolset.toolsets.asset.AssetTools"
OWNED_ROOT = "/Game/Daedalus/Art/Islands/CodexContest"
CONTRACT_SCHEMA = "daedalus.official-asset-audit.v1"
RESULT_SCHEMA = "daedalus.official-asset-audit-result.v1"
MAX_ASSETS = 128
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_RESPONSE_BYTES = 16 * 1024 * 1024
READ_TOOLS = frozenset({"get_asset_class", "get_asset_tags", "get_metadata_tags"})


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def _json(text):
    def invalid(value):
        raise ValueError("nonfinite JSON number: " + value)
    def finite_float(value):
        number = float(value)
        _require(math.isfinite(number), "nonfinite JSON number: " + value)
        return number
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=finite_float)


def _read_json(path):
    path = Path(path).resolve()
    with path.open("rb") as source:
        raw = source.read(MAX_JSON_BYTES + 1)
    _require(len(raw) <= MAX_JSON_BYTES, "JSON file exceeds byte limit")
    value = _json(raw.decode("utf-8"))
    _require(isinstance(value, dict), "JSON file must contain an object")
    return value, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _package(value):
    _require(isinstance(value, str) and re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)+", value),
             "expected an exact /Game package or namespace path")
    return value


def _namespace(value):
    value = _package(value)
    _require(value == OWNED_ROOT or value.startswith(OWNED_ROOT + "/"),
             "namespace is outside the source-owned CodexContest root")
    return value


def _object_path(value):
    _require(isinstance(value, str) and value.count(".") <= 1, "expected an exact asset package or object path")
    package, separator, name = value.partition(".")
    _package(package)
    _require(not separator or name == package.rsplit("/", 1)[1], "object name must match its package leaf")
    _require(package.startswith(OWNED_ROOT + "/"), "foreign asset path")
    return value


def _string_map(value, label):
    _require(isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str)
             for k, v in value.items()), label + " must be a string map")
    return value


def _delivery_paths(saved):
    """codex_contest_island_delivery.py: confirmed shared batch-save receipt."""
    _require(saved.get("stage") in {"assets_saved", "placed_and_saved"}
             and saved.get("saved_unreal") is True, "delivery receipt has no confirmed batch save")
    destination = _namespace(saved.get("destination"))
    meshes, packages = saved.get("meshes"), saved.get("save_packages")
    _require(isinstance(meshes, dict) and 0 < len(meshes) <= MAX_ASSETS
             and all(isinstance(key, str) and key for key in meshes), "invalid delivery meshes mapping")
    _require(isinstance(packages, list) and 0 < len(packages) <= MAX_ASSETS * 4,
             "invalid delivery save_packages")
    packages = [_package(path) for path in packages]
    _require(len(set(packages)) == len(packages), "duplicate saved package")
    paths = [_object_path(path) for path in meshes.values()]
    for path in paths:
        package = path.split(".")[0]
        _require(package.startswith(destination + "/"), "mesh leaves its receipt destination")
        _require(package in packages, "mesh is absent from confirmed save_packages")
    return paths


def _prepared_paths(saved):
    """Native prepared ingestion receipts: confirmed per-mesh saves, held from world."""
    _require(saved.get("stage") == "assets_saved" and type(saved.get("world_placed")) is int
             and saved["world_placed"] == 0, "prepared receipt is not saved and held from world")
    _require(isinstance(saved.get("manifest_sha256"), str)
             and re.fullmatch(r"[0-9a-f]{64}", saved["manifest_sha256"]), "invalid prepared manifest fingerprint")
    groups = saved.get("results")
    _require(isinstance(groups, list) and 0 < len(groups) <= MAX_ASSETS, "invalid prepared results")
    for field in ("saved_groups", "selected_groups"):
        _require(type(saved.get(field)) is int and saved[field] == len(groups), "prepared group count differs")
    paths, names = [], []
    for group in groups:
        _require(isinstance(group, dict) and group.get("stage") == "assets_saved_held_from_world"
                 and group.get("kind") in {"module", "island"}, "unconfirmed prepared group")
        name = group.get("name")
        _require(isinstance(name, str) and name and name not in names, "duplicate or invalid prepared group name")
        names.append(name)
        destination = _namespace(group.get("destination"))
        _require(destination.startswith(OWNED_ROOT + "/Prepared/" + group["kind"] + "/"),
                 "prepared destination differs from its kind")
        rows = group.get("meshes")
        _require(isinstance(rows, list) and rows, "prepared group has no meshes")
        for row in rows:
            _require(isinstance(row, dict) and row.get("save_return") is True, "prepared mesh save is unconfirmed")
            path = _object_path(row.get("path"))
            _require(path.split(".")[0].startswith(destination + "/"), "prepared mesh leaves its destination")
            paths.append(path)
    _require(type(saved.get("saved_meshes")) is int and saved["saved_meshes"] == len(paths),
             "prepared mesh count differs")
    selected = saved.get("selected_names")
    _require(isinstance(selected, list) and len(selected) == len(names)
             and all(isinstance(name, str) for name in selected) and sorted(selected) == sorted(names),
             "prepared selected names differ")
    return paths


def _saved_paths(saved, namespace):
    _require("assets" not in saved and ("meshes" in saved) != ("results" in saved),
             "unsupported or ambiguous source receipt profile")
    paths = _delivery_paths(saved) if "meshes" in saved else _prepared_paths(saved)
    _require(0 < len(paths) <= MAX_ASSETS, "source receipt requires 1..128 meshes")
    packages = [path.split(".")[0] for path in paths]
    _require(len(set(packages)) == len(packages), "duplicate source asset package")
    selected = [path for path in paths if path.split(".")[0].startswith(namespace + "/")]
    _require(selected, "namespace selects no saved assets")
    return sorted(selected)


def template_from_saved(saved_path, namespace=OWNED_ROOT, expected_class="StaticMesh"):
    """Build an offline contract from exact retained paths and fingerprint bytes."""
    namespace = _namespace(namespace)
    _require(isinstance(expected_class, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expected_class),
             "expected_class must be an exact native/generated class name")
    saved, source = _read_json(saved_path)
    return {"schema": CONTRACT_SCHEMA, "namespace": namespace, "source_receipt": source,
            "assets": [{"asset_path": path, "expected_class": expected_class, "required_metadata": {}}
                       for path in _saved_paths(saved, namespace)]}


def validate_contract(contract):
    """Fail before connecting if receipt bytes, ownership, or exact path mapping differ."""
    _require(isinstance(contract, dict) and set(contract) ==
             {"schema", "namespace", "source_receipt", "assets"}, "unexpected contract fields")
    _require(contract["schema"] == CONTRACT_SCHEMA, "unrecognized audit contract schema")
    namespace = _namespace(contract["namespace"])
    source = contract["source_receipt"]
    _require(isinstance(source, dict) and set(source) == {"path", "sha256", "bytes"},
             "source_receipt requires path, sha256, and bytes")
    _require(isinstance(source["path"], str) and Path(source["path"]).is_absolute(),
             "source receipt path must be absolute")
    _require(isinstance(source["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
             and type(source["bytes"]) is int and 0 < source["bytes"] <= MAX_JSON_BYTES,
             "invalid source receipt fingerprint")
    saved, actual = _read_json(source["path"])
    _require(actual == source, "source receipt bytes/path differ from the pinned fingerprint")
    expected_paths = _saved_paths(saved, namespace)
    rows = contract["assets"]
    _require(isinstance(rows, list) and 0 < len(rows) <= MAX_ASSETS, "contract requires 1..128 assets")
    seen, normalized = set(), []
    for row in rows:
        _require(isinstance(row, dict) and {"asset_path", "expected_class"} <= set(row)
                 and set(row) <= {"asset_path", "expected_class", "required_metadata"},
                 "unexpected asset contract fields")
        path = _object_path(row["asset_path"])
        _require(path.split(".")[0].startswith(namespace + "/"), "asset leaves the contract namespace")
        _require(path not in seen, "duplicate contract asset path")
        seen.add(path)
        cls = row["expected_class"]
        _require(isinstance(cls, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cls),
                 "expected_class must be an exact native/generated class name")
        metadata = _string_map(row.get("required_metadata", {}), "required_metadata")
        normalized.append({"asset_path": path, "expected_class": cls, "required_metadata": dict(metadata)})
    _require(sorted(seen) == expected_paths, "contract paths differ from the selected saved receipt paths")
    return {"schema": CONTRACT_SCHEMA, "namespace": namespace, "source_receipt": dict(source),
            "assets": sorted(normalized, key=lambda row: row["asset_path"])}


class _CapturedResponse:
    def __init__(self, response):
        self.response, self.chunks = response, []
        self.headers = response.headers

    def read1(self, size):
        chunk = (getattr(self.response, "read1", None) or self.response.read)(size)
        self.chunks.append(chunk)
        return chunk


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _strict_wire(raw):
    """Reject ambiguous/nonfinite JSON before retaining parsed successful replies."""
    text = raw.decode("utf-8")
    if text.lstrip().startswith(("event:", "data:", ":")):
        for event in text.replace("\r\n", "\n").split("\n\n"):
            data = [line[5:].lstrip(" ") for line in event.splitlines() if line.startswith("data:")]
            if data:
                _json("\n".join(data))
    elif text.strip():
        _json(text)


class McpToolError(ValueError):
    """A complete MCP reply failed; operation effects are not established.

    Retain only a bounded tool label and returned error text. Request arguments
    are never copied here. This exception does not authorize an automatic retry
    or imply that a tool rolled back changes before it reported an error.
    """

    def __init__(self, tool_name, content_text, *, kind="mcp_tool_error", content_valid=True):
        tool_name = tool_name if isinstance(tool_name, str) else "unknown_tool"
        content_text = content_text if isinstance(content_text, str) else "malformed MCP error content"
        self.tool_name = re.sub(r"[^A-Za-z0-9_.:-]", "_", tool_name[:160])
        self.content_text = "".join(char if char in "\n\t" or ord(char) >= 32 else "?"
                                    for char in content_text[:1024])
        self.response_complete = True
        self.operation_effects_proven = False
        self.retryable = False
        self.replayed = False
        self.data = {"kind": kind, "tool_name": self.tool_name,
                     "content_text": self.content_text, "content_valid": content_valid,
                     "diagnostic_truncated": len(tool_name) > 160 or len(content_text) > 1024,
                     "response_complete": True, "operation_effects_proven": False,
                     "effect_state": "unknown", "retryable": False, "replayed": False}
        super().__init__("MCP %s from %s: %s" % (kind, self.tool_name, self.content_text))


def _mcp_text_result(tool_name, result):
    # Keep the existing strict one-text-result success shape. This function sees
    # only the completed result, never the original request or its arguments.
    if not isinstance(result, dict):
        raise McpToolError(tool_name, "expected complete MCP result object",
                           kind="malformed_mcp_result", content_valid=False)
    content = result.get("content")
    valid = (isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict)
             and content[0].get("type") == "text" and isinstance(content[0].get("text"), str))
    error_flag = result.get("isError", False)
    if error_flag is True:
        raise McpToolError(tool_name, content[0]["text"] if valid else "malformed MCP error content",
                           content_valid=valid)
    if error_flag is not False or not valid:
        raise McpToolError(tool_name, "expected one complete MCP text result and boolean isError",
                           kind="malformed_mcp_result", content_valid=False)
    return content[0]["text"]


class _Session:
    def __init__(self, endpoint, timeout, operations, opener):
        parts = urllib.parse.urlsplit(endpoint)
        _require(parts.scheme == "http" and parts.hostname == "127.0.0.1" and parts.port
                 and parts.path == "/mcp" and not parts.username and not parts.password
                 and not parts.query and not parts.fragment, "endpoint must be http://127.0.0.1:<port>/mcp")
        _require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 30,
                 "timeout must be finite and within (0, 30] seconds")
        self.endpoint, self.timeout, self.operations = endpoint, timeout, operations
        self.opener = opener if opener is not None else urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect())
        self.sid, self.counter, self.received_bytes = None, 0, 0

    def exchange(self, label, method=None, params=None, http_method="POST", notification=False):
        self.counter += 1
        body = None
        if http_method == "POST":
            body = {"jsonrpc": "2.0", "method": method}
            if not notification:
                body["id"] = self.counter
            if params is not None:
                body["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.sid:
            headers.update({"Mcp-Session-Id": self.sid, "Mcp-Protocol-Version": PROTOCOL})
        receipt = {"label": label, "started_utc": _utc(), "http_method": http_method,
                   "request": body, "status": None, "response": None, "raw_text": ""}
        self.operations.append(receipt)
        captured = None
        try:
            # Reserve a separate bounded cleanup response even after an audit
            # exhausts its data budget; DELETE must still be submitted once.
            remaining = MAX_RESPONSE_BYTES if http_method == "DELETE" else MAX_TOTAL_RESPONSE_BYTES - self.received_bytes
            _require(remaining > 0, "total response byte budget exhausted")
            request = urllib.request.Request(self.endpoint, data=json.dumps(body).encode() if body else None,
                                             headers=headers, method=http_method)
            try:
                response = self.opener.open(request, timeout=self.timeout)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                captured = _CapturedResponse(response)
                receipt["status"] = response.status
                receipt["headers"] = {key: value for key, value in response.headers.items()
                                      if key.lower() != "mcp-session-id"}
                sid = response.headers.get("Mcp-Session-Id")
                receipt["session_header_received"] = bool(sid)
                if sid:
                    _require(isinstance(sid, str) and 0 < len(sid) <= 256
                             and all(33 <= ord(c) <= 126 for c in sid), "invalid session header")
                    _require(self.sid is None or self.sid == sid, "server changed the active session")
                    self.sid = sid
                kwargs = {"max_response_bytes": min(MAX_RESPONSE_BYTES, remaining)}
                if body is not None and "id" in body:
                    kwargs["request_id"] = body["id"]
                reply = read_response(captured, **kwargs)
                _strict_wire(b"".join(captured.chunks))
                receipt["response"] = reply
            expected = 202 if notification or http_method == "DELETE" else 200
            _require(receipt["status"] == expected, "unexpected HTTP status: " + str(receipt["status"]))
            if expected == 202:
                _require(reply is None, "expected an empty HTTP 202 response")
                return None
            _require(isinstance(reply, dict) and "error" not in reply, "JSON-RPC error: " + str(reply))
            return reply["result"]
        except Exception as exc:
            receipt["error"] = type(exc).__name__ + ": " + str(exc)
            raise
        finally:
            if captured is not None:
                raw = b"".join(captured.chunks)
                self.received_bytes += len(raw)
                receipt["response_bytes"] = len(raw)
                receipt["response_sha256"] = hashlib.sha256(raw).hexdigest()
                try:
                    receipt["raw_text"] = raw.decode("utf-8")
                except UnicodeDecodeError:
                    receipt["raw_body_base64"] = base64.b64encode(raw).decode("ascii")
            receipt["ended_utc"] = _utc()

    def meta(self, name, arguments):
        result = self.exchange(name, "tools/call", {"name": name, "arguments": arguments})
        tool_label = name
        if name == "call_tool" and isinstance(arguments, dict) and isinstance(arguments.get("tool_name"), str):
            tool_label = arguments["tool_name"]
        return _mcp_text_result(tool_label, result)

    def read_asset(self, name, path):
        _require(name in READ_TOOLS, "asset tool is not read-only allowlisted")
        value = _json(self.meta("call_tool", {"toolset_name": ASSET_TOOLSET, "tool_name": name,
                                              "arguments": {"asset_path": path}}))
        _require(isinstance(value, dict) and set(value) == {"returnValue"}, "malformed Python tool result")
        return value["returnValue"]


def _schema(tool, fields, required):
    schema = tool.get("inputSchema")
    _require(isinstance(schema, dict) and schema.get("type") == "object", "missing object inputSchema")
    properties = schema.get("properties")
    _require(isinstance(properties, dict) and set(properties) == set(fields), "tool schema properties differ")
    for name, kind in fields.items():
        _require(isinstance(properties[name], dict) and properties[name].get("type") == kind,
                 "tool schema property type differs: " + name)
    actual = schema.get("required", [])
    _require(isinstance(actual, list) and len(actual) == len(set(actual))
             and set(required) <= set(actual) <= set(fields), "tool required parameters differ")


def _discover(session, needs_metadata):
    listing = session.exchange("tools-list", "tools/list", {})
    _require(isinstance(listing, dict) and isinstance(listing.get("tools"), list), "malformed tools/list")
    tools = listing["tools"]
    _require(all(isinstance(t, dict) and isinstance(t.get("name"), str) for t in tools), "malformed tool entry")
    by_name = {tool["name"]: tool for tool in tools}
    _require(len(by_name) == len(tools), "duplicate MCP tool name")
    for name, fields, required in (
        ("list_toolsets", {}, []),
        ("describe_toolset", {"toolset_name": "string"}, ["toolset_name"]),
        ("call_tool", {"toolset_name": "string", "tool_name": "string", "arguments": "object"}, ["tool_name"]),
    ):
        _require(name in by_name, "required MCP meta-tool absent: " + name)
        _schema(by_name[name], fields, required)
    catalog = session.meta("list_toolsets", {})
    names = [name.strip() for name in re.findall(r"(?m)^- ([^:\r\n]+)", catalog)]
    _require(names.count(ASSET_TOOLSET) == 1, "required asset toolset absent or duplicated")
    description = _json(session.meta("describe_toolset", {"toolset_name": ASSET_TOOLSET}))
    _require(isinstance(description, dict) and isinstance(description.get("tools"), list), "malformed toolset description")
    tools = description["tools"]
    _require(all(isinstance(t, dict) and isinstance(t.get("name"), str) for t in tools), "malformed asset schema")
    by_name = {tool["name"]: tool for tool in tools}
    _require(len(by_name) == len(tools), "duplicate asset tool name")
    required = {"get_asset_class", "get_asset_tags"} | ({"get_metadata_tags"} if needs_metadata else set())
    for name in sorted(required):
        full_name = ASSET_TOOLSET + "." + name
        _require(full_name in by_name, "required asset tool absent: " + name)
        _schema(by_name[full_name], {"asset_path": "string"}, ["asset_path"])


def audit(contract, endpoint="http://127.0.0.1:8000/mcp", timeout=15, opener=None):
    """Connect only on explicit invocation; retain all replies and always attempt DELETE."""
    report = {"schema": RESULT_SCHEMA, "started_utc": _utc(), "protocol": PROTOCOL, "endpoint": endpoint,
              "outcome": "FAIL", "assets": [], "operations": [], "asset_writes": 0,
              "cleanup": {"attempted": False, "confirmed": False}}
    session = None
    try:
        contract = validate_contract(contract)
        report["contract"] = contract
        session = _Session(endpoint, timeout, report["operations"], opener)
        initialized = session.exchange("initialize", "initialize", {"protocolVersion": PROTOCOL,
            "capabilities": {}, "clientInfo": {"name": "daedalus-asset-receipt-audit", "version": "1"}})
        _require(session.sid is not None and isinstance(initialized, dict)
                 and initialized.get("protocolVersion") == PROTOCOL, "session/protocol negotiation failed")
        session.exchange("initialized", "notifications/initialized", {}, notification=True)
        _discover(session, any(row["required_metadata"] for row in contract["assets"]))
        for expected in contract["assets"]:
            path = expected["asset_path"]
            observed = {"asset_path": path, "expected_class": expected["expected_class"], "metadata": {}}
            report["assets"].append(observed)
            cls = session.read_asset("get_asset_class", path)
            observed["actual_class"] = cls
            _require(isinstance(cls, str) and cls == expected["expected_class"], "asset class differs: " + path)
            observed["registry_tags"] = _string_map(session.read_asset("get_asset_tags", path), "registry tags")
            if expected["required_metadata"]:
                observed["metadata"] = _string_map(session.read_asset("get_metadata_tags", path), "metadata")
                _require(all(observed["metadata"].get(k) == v for k, v in expected["required_metadata"].items()),
                         "required asset metadata differs: " + path)
            observed["verified"] = True
        report["outcome"] = "PASS"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if session is not None and session.sid is not None:
            report["cleanup"]["attempted"] = True
            try:
                session.exchange("delete-session", http_method="DELETE")
                report["cleanup"]["confirmed"] = True
            except Exception as exc:
                report["cleanup"]["error"] = type(exc).__name__ + ": " + str(exc)
                report.setdefault("error", "session cleanup failed: " + report["cleanup"]["error"])
                report["outcome"] = "FAIL"
        report["ended_utc"] = _utc()
    return report


def _write_new(path, value):
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("template", help="create an offline contract from an existing save receipt")
    template.add_argument("--saved-receipt", required=True, type=Path)
    template.add_argument("--namespace", default=OWNED_ROOT)
    template.add_argument("--expected-class", default="StaticMesh")
    run = sub.add_parser("audit", help="read exact receipt assets through an already admitted official MCP endpoint")
    run.add_argument("--contract", required=True, type=Path)
    run.add_argument("--endpoint", default="http://127.0.0.1:8000/mcp")
    run.add_argument("--timeout", type=float, default=15)
    for command in (template, run):
        command.add_argument("--out", required=True, type=Path, help="fresh output file; never overwritten")
    args = parser.parse_args(argv)
    _require(not args.out.exists(), "output already exists; preserve and inspect the retained receipt")
    if args.command == "template":
        result = template_from_saved(args.saved_receipt, args.namespace, args.expected_class)
    else:
        try:
            contract, fingerprint = _read_json(args.contract)
            result = audit(contract, args.endpoint, args.timeout)
            result["contract_file"] = fingerprint
        except Exception as exc:
            result = {"schema": RESULT_SCHEMA, "started_utc": _utc(), "ended_utc": _utc(),
                      "protocol": PROTOCOL, "endpoint": args.endpoint, "outcome": "FAIL", "asset_writes": 0,
                      "error": type(exc).__name__ + ": " + str(exc), "operations": [], "assets": [],
                      "cleanup": {"attempted": False, "confirmed": False}}
    _write_new(args.out, result)
    print(json.dumps({"outcome": result.get("outcome", "TEMPLATE_CREATED"), "output": str(args.out.resolve()),
                      "assets": len(result.get("assets", [])), "error": result.get("error")}))
    return 1 if result.get("outcome") == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
