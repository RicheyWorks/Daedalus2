# SPDX-License-Identifier: MIT
"""Offline receipt-audit tests; every HTTP response comes from a scripted opener."""
import copy
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from tools.unreal_mcp import asset_receipt_audit as audit


ASSET_PATH = audit.OWNED_ROOT + "/SM_Receipt"
SECOND_PATH = audit.OWNED_ROOT + "/SM_Second"
ENDPOINT = "http://127.0.0.1:8000/mcp"
GOLDEN_RECEIPTS = Path(__file__).resolve().parents[2] / (
    "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/NativeReceipts")


def text_result(value):
    return {"content": [{"type": "text", "text": value}]}


def tool_result(value):
    return text_result(json.dumps({"returnValue": value}))


def input_schema(properties, required=()):
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = list(required)
    return schema


def meta_tools():
    return {"tools": [
        {"name": "list_toolsets", "inputSchema": input_schema({})},
        {"name": "describe_toolset", "inputSchema": input_schema(
            {"toolset_name": {"type": "string"}}, ["toolset_name"])},
        {"name": "call_tool", "inputSchema": input_schema({
            "toolset_name": {"type": "string"},
            "tool_name": {"type": "string"},
            "arguments": {"type": "object"},
        }, ["tool_name"])},
    ]}


def described_tools():
    return {"tools": [
        {"name": audit.ASSET_TOOLSET + "." + name,
         "inputSchema": input_schema(
             {"asset_path": {"type": "string"}}, ["asset_path"])}
        for name in ("get_asset_class", "get_asset_tags", "get_metadata_tags")
    ]}


class Response(io.BytesIO):
    def __init__(self, data=b"", status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def getcode(self):
        return self.status


class ScriptedOpener:
    """Implements only the audit's permitted discovery and read calls."""

    def __init__(self, paths=(ASSET_PATH,)):
        self.requests = []
        self.results = {}
        self.rpc_errors = {}
        self.raw_replies = {}
        self.raw_headers = {}
        self.failures = {}
        self.classes = {path: "StaticMesh" for path in paths}
        self.registry_tags = {path: {"Triangles": "12"} for path in paths}
        self.metadata = {path: {"AuditToken": "reviewed"} for path in paths}
        self.tools = meta_tools()
        self.description = described_tools()
        self.session_id = "offline-audit-session"

    def open(self, request, timeout):
        method = request.get_method()
        payload = json.loads(request.data) if request.data is not None else None
        headers = {key.lower(): value for key, value in request.header_items()}
        self.requests.append({"method": method, "payload": payload,
                              "headers": headers, "timeout": timeout,
                              "url": request.full_url})
        if method == "DELETE":
            operation = "DELETE"
        elif payload["method"] == "tools/call":
            params = payload["params"]
            operation = params["name"]
            if operation == "call_tool":
                operation = params["arguments"]["tool_name"]
        else:
            operation = payload["method"]

        if operation in self.failures:
            raise self.failures[operation]
        if operation == "DELETE":
            return Response(status=202)
        if operation == "notifications/initialized":
            return Response(status=202)
        if operation in self.raw_replies:
            raw = self.raw_replies[operation]
            raw = raw(payload) if callable(raw) else raw
            return Response(raw, headers=self.raw_headers.get(operation))

        response_headers = {}
        if operation == "initialize":
            result = {"protocolVersion": audit.PROTOCOL,
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "offline-official-fixture", "version": "1"}}
            response_headers["Mcp-Session-Id"] = self.session_id
        elif operation == "tools/list":
            result = self.tools
        elif operation == "list_toolsets":
            result = text_result("- " + audit.ASSET_TOOLSET + ": Asset inspection tools\n")
        elif operation == "describe_toolset":
            if payload["params"]["arguments"] != {"toolset_name": audit.ASSET_TOOLSET}:
                raise AssertionError("Unexpected toolset description request")
            result = text_result(json.dumps(self.description))
        elif operation in ("get_asset_class", "get_asset_tags", "get_metadata_tags"):
            arguments = payload["params"]["arguments"]
            if arguments["toolset_name"] != audit.ASSET_TOOLSET:
                raise AssertionError("Unexpected toolset invocation")
            inner = arguments["arguments"]
            if set(inner) != {"asset_path"}:
                raise AssertionError("Inner tool arguments must preserve the described schema")
            path = inner["asset_path"]
            values = {"get_asset_class": self.classes,
                      "get_asset_tags": self.registry_tags,
                      "get_metadata_tags": self.metadata}[operation]
            result = tool_result(values[path])
        else:
            raise AssertionError("Unpermitted audit operation: " + operation)

        reply = {"jsonrpc": "2.0", "id": payload["id"]}
        if operation in self.rpc_errors:
            reply["error"] = self.rpc_errors[operation]
        else:
            reply["result"] = self.results.get(operation, result)
        return Response(json.dumps(reply).encode("utf-8"), headers=response_headers)

    def inner_calls(self):
        return [row["payload"]["params"]["arguments"] for row in self.requests
                if row["payload"] and row["payload"]["method"] == "tools/call"
                and row["payload"]["params"]["name"] == "call_tool"]

    def delete_calls(self):
        return [row for row in self.requests if row["method"] == "DELETE"]


class AssetReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.saved_path = Path(self.temporary.name) / "codex-saved.delivery.json"
        self.write_saved()

    def write_saved(self, paths=(ASSET_PATH,), stage="assets_saved", saved_unreal=True,
                    meshes=None, save_packages=None):
        mesh_mapping = meshes if meshes is not None else {
            "layer_%03d" % index: path for index, path in enumerate(paths)}
        packages = sorted({path.split(".")[0] for path in mesh_mapping.values()})
        receipt = {"stage": stage, "saved_unreal": saved_unreal,
                   "destination": audit.OWNED_ROOT, "meshes": mesh_mapping,
                   "save_packages": save_packages if save_packages is not None else packages + [
                       audit.OWNED_ROOT + "/Batch/SM_OtherBatch",
                       audit.OWNED_ROOT + "/Materials/M_Palette", "/Game/Maps/ContestReview"]}
        self.saved_path.write_text(json.dumps(receipt), encoding="utf-8")
        return receipt

    def contract(self):
        return audit.template_from_saved(self.saved_path)

    def run_audit(self, contract=None, opener=None, **kwargs):
        opener = opener if opener is not None else ScriptedOpener()
        report = audit.audit(self.contract() if contract is None else contract,
                             endpoint=ENDPOINT, opener=opener, **kwargs)
        return report, opener

    def assert_failed(self, report):
        self.assertEqual(report["outcome"], "FAIL", report)
        self.assertTrue(report.get("error"), report)
        self.assertIsInstance(report["assets"], list)
        self.assertIsInstance(report["operations"], list)

    def assert_cleaned(self, report, opener):
        self.assertTrue(report["cleanup"]["attempted"], report)
        self.assertTrue(report["cleanup"]["confirmed"], report)
        self.assertEqual(len(opener.delete_calls()), 1)

    def test_template_fingerprints_delivery_receipt_and_preserves_exact_mesh_path(self):
        contract = self.contract()
        data = self.saved_path.read_bytes()
        self.assertEqual(contract["schema"], audit.CONTRACT_SCHEMA)
        self.assertEqual(contract["namespace"], audit.OWNED_ROOT)
        self.assertEqual(contract["source_receipt"], {
            "path": str(self.saved_path.resolve()),
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        self.assertEqual(contract["assets"], [{"asset_path": ASSET_PATH,
            "expected_class": "StaticMesh", "required_metadata": {}}])
        self.assertEqual(audit.validate_contract(contract), contract)

    def test_template_selects_only_the_requested_owned_namespace(self):
        selected = audit.OWNED_ROOT + "/RoundA"
        path = selected + "/Mesh.Mesh"
        self.write_saved(paths=(path, audit.OWNED_ROOT + "/RoundB/Other.Other"))
        contract = audit.template_from_saved(self.saved_path, namespace=selected)
        self.assertEqual([row["asset_path"] for row in contract["assets"]], [path])
        audit.validate_contract(contract)

    def test_delivery_receipt_accepts_both_saved_stages_and_exact_object_paths(self):
        path = ASSET_PATH + ".SM_Receipt"
        for stage in ("assets_saved", "placed_and_saved"):
            with self.subTest(stage=stage):
                self.write_saved(paths=(path,), stage=stage)
                contract = self.contract()
                self.assertEqual(contract["assets"][0]["asset_path"], path)
                audit.validate_contract(contract)
                report, opener = self.run_audit(contract, ScriptedOpener((path,)))
                self.assertEqual(report["outcome"], "PASS", report)
                self.assertTrue(all(call["arguments"]["asset_path"] == path
                                    for call in opener.inner_calls()))

    def test_actual_retained_prepared_receipts_generate_valid_exact_contracts(self):
        cases = (("CodexModule_CopperPatina_BridgeCoupler_85000.unreal.json", 1),
                 ("CodexIsland_summit_rim_84011.unreal.json", 8))
        for filename, count in cases:
            with self.subTest(filename=filename):
                path = GOLDEN_RECEIPTS / filename
                source = json.loads(path.read_text(encoding="utf-8"))
                expected = sorted(mesh["path"] for group in source["results"]
                                  for mesh in group["meshes"])
                contract = audit.template_from_saved(path)
                self.assertEqual(len(contract["assets"]), count)
                self.assertEqual([row["asset_path"] for row in contract["assets"]], expected)
                self.assertEqual(audit.validate_contract(contract), contract)

    def test_prepared_receipt_requires_consistent_counts_names_and_saved_group_state(self):
        baseline = json.loads((GOLDEN_RECEIPTS /
            "CodexModule_CopperPatina_BridgeCoupler_85000.unreal.json").read_text(encoding="utf-8"))
        changes = (("saved_groups", 2), ("selected_groups", 2), ("saved_meshes", 2),
                   ("selected_names", ["different"]), ("world_placed", 1),
                   ("manifest_sha256", "invalid"), ("saved_groups", True),
                   ("stage", "batch_save_pending"))
        for key, value in changes:
            with self.subTest(key=key, value=value):
                receipt = copy.deepcopy(baseline)
                receipt[key] = value
                self.saved_path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.contract()
        for field, value in (("stage", "assets_prepared"), ("kind", "unknown")):
            with self.subTest(group_field=field):
                receipt = copy.deepcopy(baseline)
                receipt["results"][0][field] = value
                self.saved_path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.contract()
        receipt = copy.deepcopy(baseline)
        receipt["results"][0]["meshes"][0]["save_return"] = False
        self.saved_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.contract()

    def test_prepared_receipt_rejects_duplicate_meshes_and_group_names(self):
        baseline = json.loads((GOLDEN_RECEIPTS /
            "CodexModule_CopperPatina_BridgeCoupler_85000.unreal.json").read_text(encoding="utf-8"))
        duplicate_mesh = copy.deepcopy(baseline)
        duplicate_mesh["results"][0]["meshes"] *= 2
        duplicate_mesh["saved_meshes"] = 2
        duplicate_group = copy.deepcopy(baseline)
        duplicate_group["results"] *= 2
        duplicate_group["selected_names"] *= 2
        duplicate_group.update(saved_groups=2, selected_groups=2, saved_meshes=2)
        for receipt in (duplicate_mesh, duplicate_group):
            with self.subTest(groups=len(receipt["results"])):
                self.saved_path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.contract()

    def test_success_uses_official_discovery_read_tools_and_deletes_session(self):
        report, opener = self.run_audit()
        self.assertEqual(report["outcome"], "PASS", report)
        self.assertEqual(report["assets"][0]["actual_class"], "StaticMesh")
        self.assertEqual(report["assets"][0]["registry_tags"], {"Triangles": "12"})
        self.assertEqual(report["assets"][0]["metadata"], {})
        self.assertEqual(report["asset_writes"], 0)
        self.assertTrue(report["operations"])
        self.assertEqual([row["tool_name"] for row in opener.inner_calls()],
                         ["get_asset_class", "get_asset_tags"])
        self.assertTrue(all(row["arguments"] == {"asset_path": ASSET_PATH}
                            for row in opener.inner_calls()))
        self.assert_cleaned(report, opener)
        for row in opener.requests[1:]:
            self.assertEqual(row["headers"].get("mcp-session-id"), opener.session_id)
        self.assertTrue(all(row["url"] == ENDPOINT for row in opener.requests))

    def test_multiple_assets_are_audited_without_expanding_the_selected_paths(self):
        self.write_saved(paths=(ASSET_PATH, SECOND_PATH))
        report, opener = self.run_audit(opener=ScriptedOpener((ASSET_PATH, SECOND_PATH)))
        self.assertEqual(report["outcome"], "PASS", report)
        self.assertEqual(len(report["assets"]), 2)
        paths = [row["arguments"]["asset_path"] for row in opener.inner_calls()]
        self.assertEqual(set(paths), {ASSET_PATH, SECOND_PATH})
        self.assertEqual(paths.count(ASSET_PATH), 2)
        self.assertEqual(paths.count(SECOND_PATH), 2)
        self.assert_cleaned(report, opener)

    def test_required_metadata_is_read_and_verified_only_when_requested(self):
        contract = self.contract()
        contract["assets"][0]["required_metadata"] = {"AuditToken": "reviewed"}
        report, opener = self.run_audit(contract)
        self.assertEqual(report["outcome"], "PASS", report)
        self.assertIn("get_metadata_tags", [row["tool_name"] for row in opener.inner_calls()])
        self.assertEqual(report["assets"][0]["metadata"], {"AuditToken": "reviewed"})
        self.assert_cleaned(report, opener)

    def test_metadata_tool_is_required_only_for_nonempty_metadata_requirements(self):
        for needs_metadata in (False, True):
            with self.subTest(needs_metadata=needs_metadata):
                contract = self.contract()
                if needs_metadata:
                    contract["assets"][0]["required_metadata"] = {"AuditToken": "reviewed"}
                opener = ScriptedOpener()
                opener.description["tools"] = [tool for tool in opener.description["tools"]
                    if not tool["name"].endswith(".get_metadata_tags")]
                report, opener = self.run_audit(contract, opener)
                self.assertEqual(report["outcome"], "FAIL" if needs_metadata else "PASS", report)
                if needs_metadata:
                    self.assertEqual(opener.inner_calls(), [])
                self.assert_cleaned(report, opener)

    def test_class_mismatch_fails_and_still_cleans_up(self):
        opener = ScriptedOpener()
        opener.classes[ASSET_PATH] = "SkeletalMesh"
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assert_cleaned(report, opener)

    def test_metadata_mismatch_fails_and_still_cleans_up(self):
        contract = self.contract()
        contract["assets"][0]["required_metadata"] = {"AuditToken": "different"}
        report, opener = self.run_audit(contract)
        self.assert_failed(report)
        self.assert_cleaned(report, opener)

    def test_missing_meta_tool_or_inner_schema_fails_before_asset_calls(self):
        for missing in ("call_tool", "get_asset_class", "get_asset_tags"):
            with self.subTest(missing=missing):
                opener = ScriptedOpener()
                container = opener.tools if missing == "call_tool" else opener.description
                container["tools"] = [tool for tool in container["tools"]
                    if tool["name"].rsplit(".", 1)[-1] != missing]
                report, opener = self.run_audit(opener=opener)
                self.assert_failed(report)
                self.assertEqual(opener.inner_calls(), [])
                self.assert_cleaned(report, opener)

    def test_inner_argument_schema_must_describe_the_expected_path_parameter(self):
        opener = ScriptedOpener()
        opener.description["tools"][0]["inputSchema"] = input_schema(
            {"wrong_path": {"type": "string"}}, ["wrong_path"])
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertEqual(opener.inner_calls(), [])
        self.assert_cleaned(report, opener)

    def test_missing_toolset_in_catalog_fails_without_asset_calls(self):
        opener = ScriptedOpener()
        opener.results["list_toolsets"] = text_result("- Other.Toolset: unrelated\n")
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertEqual(opener.inner_calls(), [])
        self.assert_cleaned(report, opener)

    def test_json_rpc_error_cannot_be_reported_as_pass(self):
        opener = ScriptedOpener()
        opener.rpc_errors["get_asset_class"] = {"code": -32602, "message": "fixture RPC error"}
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assert_cleaned(report, opener)
        self.assertEqual(len(opener.inner_calls()), 1)

    def test_mcp_tool_error_cannot_be_reported_as_pass(self):
        opener = ScriptedOpener()
        opener.results["get_asset_class"] = {**text_result("fixture tool error"), "isError": True}
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assert_cleaned(report, opener)

    def test_malformed_inner_result_wrappers_fail_closed(self):
        for result in ({}, {"content": []}, text_result("not JSON"),
                       text_result('{"wrongValue":"StaticMesh"}'),
                       tool_result(["StaticMesh"]),
                       {"content": [{"type": "image", "data": ""}]}):
            with self.subTest(result=result):
                opener = ScriptedOpener()
                opener.results["get_asset_class"] = result
                report, opener = self.run_audit(opener=opener)
                self.assert_failed(report)
                self.assert_cleaned(report, opener)

    def test_registry_tags_must_be_a_string_mapping(self):
        for value in (None, [], {"Triangles": 12}):
            with self.subTest(value=value):
                opener = ScriptedOpener()
                opener.results["get_asset_tags"] = tool_result(value)
                report, opener = self.run_audit(opener=opener)
                self.assert_failed(report)
                self.assert_cleaned(report, opener)

    def test_malformed_rpc_response_and_wrong_id_fail_without_replay(self):
        for body in (b"not JSON", b"{}", lambda payload: json.dumps({
                "jsonrpc": "2.0", "id": payload["id"] + 100,
                "result": tool_result("StaticMesh")}).encode("utf-8")):
            with self.subTest(body=body):
                opener = ScriptedOpener()
                opener.raw_replies["get_asset_class"] = body
                report, opener = self.run_audit(opener=opener)
                self.assert_failed(report)
                self.assertEqual(len(opener.inner_calls()), 1)
                self.assert_cleaned(report, opener)

    def test_duplicate_and_nonfinite_raw_rpc_json_fail_closed(self):
        def ambiguous_reply(payload, kind):
            identifier = json.dumps(payload["id"])
            result = json.dumps(tool_result("StaticMesh"))
            prefix = '{"jsonrpc":"2.0","id":' + identifier + ',"result":' + result
            suffix = (',"result":' + result if kind == "duplicate" else ',"extra":NaN')
            return (prefix + suffix + '}').encode("utf-8")

        for kind in ("duplicate", "nonfinite"):
            for sse in (False, True):
                with self.subTest(kind=kind, sse=sse):
                    opener = ScriptedOpener()

                    def raw(payload):
                        body = ambiguous_reply(payload, kind)
                        return b"event: message\ndata: " + body + b"\n\n" if sse else body

                    opener.raw_replies["get_asset_class"] = raw
                    if sse:
                        opener.raw_headers["get_asset_class"] = {"Content-Type": "text/event-stream"}
                    report, opener = self.run_audit(opener=opener)
                    self.assert_failed(report)
                    self.assertEqual(len(opener.inner_calls()), 1)
                    self.assert_cleaned(report, opener)

    def test_invalid_utf8_retains_exact_response_bytes_and_fingerprint(self):
        raw = b'\xff{"fixture":"invalid UTF-8"}'
        opener = ScriptedOpener()
        opener.raw_replies["get_asset_class"] = raw
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        failed = next(row for row in report["operations"] if row.get("error"))
        self.assertEqual(failed["response_bytes"], len(raw))
        self.assertEqual(failed["response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(base64.b64decode(failed["raw_body_base64"]), raw)
        self.assertEqual(failed["raw_text"], "")
        self.assert_cleaned(report, opener)

    def test_overflowed_json_numbers_fail_and_the_failure_report_still_serializes(self):
        for inner in (False, True):
            with self.subTest(inner=inner):
                opener = ScriptedOpener()

                def raw(payload):
                    result = text_result('{"returnValue":1e309}') if inner else tool_result("StaticMesh")
                    body = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result})
                    if not inner:
                        body = body[:-1] + ',"overflow":1e309}'
                    return body.encode("utf-8")

                opener.raw_replies["get_asset_class"] = raw
                report, opener = self.run_audit(opener=opener)
                self.assert_failed(report)
                self.assert_cleaned(report, opener)
                output = Path(self.temporary.name) / ("overflow-%s.json" % inner)
                audit._write_new(output, report)
                retained = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(retained["outcome"], "FAIL")
                self.assertTrue(any("1e309" in operation.get("raw_text", "")
                                    for operation in retained["operations"]))

    def test_cli_retains_a_failure_receipt_for_an_overflowed_contract(self):
        contract_path = Path(self.temporary.name) / "overflow-contract.json"
        output_path = Path(self.temporary.name) / "overflow-failure.json"
        contract_path.write_text('{"invalid":1e309}', encoding="utf-8")
        with patch.object(audit.urllib.request, "build_opener") as building, \
                patch("sys.stdout", io.StringIO()):
            result = audit.main(["audit", "--contract", str(contract_path), "--out", str(output_path)])
        self.assertEqual(result, 1)
        building.assert_not_called()
        report = json.loads(output_path.read_text(encoding="utf-8"))
        self.assert_failed(report)
        self.assertFalse(report["cleanup"]["attempted"])

    def test_default_opener_installs_a_handler_that_refuses_all_redirects(self):
        opener = ScriptedOpener()
        with patch.object(audit.urllib.request, "build_opener", return_value=opener) as building:
            report = audit.audit(self.contract(), endpoint=ENDPOINT)
        self.assertEqual(report["outcome"], "PASS", report)
        handlers = building.call_args.args
        blocker = next(handler for handler in handlers if isinstance(handler, audit._NoRedirect))
        for new_url in ("http://example.invalid/mcp", "http://127.0.0.1:8000/other"):
            with self.subTest(new_url=new_url):
                self.assertIsNone(blocker.redirect_request(
                    audit.urllib.request.Request(ENDPOINT), None, 302, "Found", {}, new_url))
        self.assert_cleaned(report, opener)

    def test_total_response_budget_stops_readback_but_keeps_cleanup_allowance(self):
        baseline, _ = self.run_audit()
        consumed = 0
        for operation in baseline["operations"]:
            consumed += operation.get("response_bytes", 0)
            request = operation.get("request") or {}
            inner = request.get("params", {}).get("arguments", {})
            if inner.get("tool_name") == "get_asset_class":
                break
        self.assertGreater(consumed, 0)
        with patch.object(audit, "MAX_TOTAL_RESPONSE_BYTES", consumed):
            report, opener = self.run_audit()
        self.assert_failed(report)
        self.assertIn("budget", report["error"])
        self.assertEqual([call["tool_name"] for call in opener.inner_calls()], ["get_asset_class"])
        self.assert_cleaned(report, opener)

    def test_unsupported_protocol_fails_and_cleans_up_the_created_session(self):
        opener = ScriptedOpener()
        opener.results["initialize"] = {"protocolVersion": "1900-01-01",
            "capabilities": {"tools": {}}, "serverInfo": {"name": "fixture", "version": "1"}}
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertEqual(opener.inner_calls(), [])
        self.assert_cleaned(report, opener)

    def test_session_header_survives_malformed_initialize_reply_for_cleanup(self):
        opener = ScriptedOpener()
        opener.raw_replies["initialize"] = b"not JSON"
        opener.raw_headers["initialize"] = {"Mcp-Session-Id": opener.session_id}
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertEqual(opener.inner_calls(), [])
        self.assert_cleaned(report, opener)

    def test_connection_failure_is_not_retried_and_has_no_session_to_delete(self):
        opener = ScriptedOpener()
        opener.failures["initialize"] = ConnectionRefusedError("offline fixture refusal")
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertEqual(len(opener.requests), 1)
        self.assertFalse(report["cleanup"]["attempted"])
        self.assertFalse(report["cleanup"]["confirmed"])

    def test_cleanup_failure_prevents_pass_and_is_reported(self):
        opener = ScriptedOpener()
        opener.failures["DELETE"] = urllib.error.HTTPError(
            ENDPOINT, 503, "fixture cleanup failure", {}, io.BytesIO(b""))
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertTrue(report["cleanup"]["attempted"])
        self.assertFalse(report["cleanup"]["confirmed"])
        self.assertTrue(report["cleanup"].get("error"))
        self.assertEqual(len(opener.delete_calls()), 1)

    def test_cleanup_failure_preserves_the_original_asset_failure(self):
        opener = ScriptedOpener()
        opener.classes[ASSET_PATH] = "SkeletalMesh"
        opener.failures["DELETE"] = OSError("fixture cleanup failure")
        report, opener = self.run_audit(opener=opener)
        self.assert_failed(report)
        self.assertIn("class differs", report["error"])
        self.assertIn("fixture cleanup failure", report["cleanup"]["error"])
        self.assertEqual(len(opener.delete_calls()), 1)

    def test_duplicate_foreign_and_malformed_object_paths_are_rejected_locally(self):
        baseline = self.contract()
        for path in ("/Game/Foreign/SM_Receipt.SM_Receipt",
                     audit.OWNED_ROOT + "Sibling/SM_Receipt.SM_Receipt",
                     audit.OWNED_ROOT + "/SM_Receipt.Other",
                     audit.OWNED_ROOT + "/SM_Receipt.SM_Receipt:Subobject",
                     audit.OWNED_ROOT + "/../Other/SM_Receipt.SM_Receipt"):
            with self.subTest(path=path):
                contract = copy.deepcopy(baseline)
                contract["assets"][0]["asset_path"] = path
                with self.assertRaises(ValueError):
                    audit.validate_contract(contract)
                report, opener = self.run_audit(contract)
                self.assert_failed(report)
                self.assertEqual(opener.requests, [])
        duplicate = copy.deepcopy(baseline)
        duplicate["assets"].append(copy.deepcopy(duplicate["assets"][0]))
        with self.assertRaises(ValueError):
            audit.validate_contract(duplicate)
        report, opener = self.run_audit(duplicate)
        self.assert_failed(report)
        self.assertEqual(opener.requests, [])

    def test_contract_cannot_add_or_omit_saved_selected_paths(self):
        self.write_saved(paths=(ASSET_PATH, SECOND_PATH))
        baseline = self.contract()
        for rows in (baseline["assets"][:1], baseline["assets"] + [{
                "asset_path": audit.OWNED_ROOT + "/SM_New.SM_New",
                "expected_class": "StaticMesh", "required_metadata": {}}]):
            with self.subTest(rows=rows):
                contract = copy.deepcopy(baseline)
                contract["assets"] = rows
                with self.assertRaises(ValueError):
                    audit.validate_contract(contract)
                report, opener = self.run_audit(contract)
                self.assert_failed(report)
                self.assertEqual(opener.requests, [])

    def test_changed_source_receipt_is_rejected_before_any_request(self):
        contract = self.contract()
        self.saved_path.write_text(self.saved_path.read_text(encoding="utf-8") + "\n",
                                   encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.validate_contract(contract)
        report, opener = self.run_audit(contract)
        self.assert_failed(report)
        self.assertEqual(opener.requests, [])
        self.assertFalse(report["cleanup"]["attempted"])

    def test_delivery_receipt_requires_saved_stage_and_confirmed_batch_save(self):
        for stage, saved in (("assets_prepared", True), ("batch_save_pending", True),
                             ("placed_unsaved", True), ("assets_saved", False),
                             ("assets_saved", "true"), ("assets_saved", 1)):
            with self.subTest(stage=stage, saved=saved):
                self.write_saved(stage=stage, saved_unreal=saved)
                with self.assertRaises(ValueError):
                    self.contract()

    def test_delivery_receipt_requires_all_mesh_packages_in_the_confirmed_save_set(self):
        self.write_saved(save_packages=[SECOND_PATH])
        with self.assertRaises(ValueError):
            self.contract()

    def test_delivery_receipt_rejects_duplicate_save_packages_and_mesh_aliases(self):
        fixtures = (
            {"save_packages": [ASSET_PATH, ASSET_PATH]},
            {"meshes": {"ground": ASSET_PATH, "copy": ASSET_PATH}},
            {"meshes": {"ground": ASSET_PATH, "alias": ASSET_PATH + ".SM_Receipt"}},
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.write_saved(**fixture)
                with self.assertRaises(ValueError):
                    self.contract()

    def test_delivery_receipt_rejects_foreign_meshes_and_duplicate_layer_keys(self):
        self.write_saved(paths=("/Game/Foreign/Mesh",))
        with self.assertRaises(ValueError):
            self.contract()
        receipt = self.write_saved()
        duplicate = json.dumps(receipt).replace(
            '"layer_000": "' + ASSET_PATH + '"',
            '"layer_000": "' + ASSET_PATH + '", "layer_000": "' + SECOND_PATH + '"')
        self.saved_path.write_text(duplicate, encoding="utf-8")
        with self.assertRaises(ValueError):
            self.contract()

    def test_contract_must_preserve_the_receipt_path_without_inventing_an_object_suffix(self):
        contract = self.contract()
        contract["assets"][0]["asset_path"] = ASSET_PATH + ".SM_Receipt"
        with self.assertRaises(ValueError):
            audit.validate_contract(contract)

    def test_asset_limit_and_owned_namespace_are_enforced_locally(self):
        paths = [audit.OWNED_ROOT + "/SM_%03d.SM_%03d" % (i, i) for i in range(129)]
        self.write_saved(paths=paths)
        with self.assertRaises(ValueError):
            self.contract()
        self.write_saved()
        for namespace in ("/Game", "/Game/Foreign", audit.OWNED_ROOT + "Sibling"):
            with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                audit.template_from_saved(self.saved_path, namespace=namespace)

    def test_endpoint_and_timeout_rejections_never_open_a_connection(self):
        for endpoint in ("http://localhost:8000/mcp", "http://0.0.0.0:8000/mcp",
                         "https://127.0.0.1:8000/mcp", "http://127.0.0.1:8000/other"):
            with self.subTest(endpoint=endpoint):
                opener = ScriptedOpener()
                report = audit.audit(self.contract(), endpoint=endpoint, opener=opener)
                self.assert_failed(report)
                self.assertEqual(opener.requests, [])
        for timeout in (0, -1, 31, True, float("inf"), float("nan")):
            with self.subTest(timeout=timeout):
                report, opener = self.run_audit(timeout=timeout)
                self.assert_failed(report)
                self.assertEqual(opener.requests, [])


if __name__ == "__main__":
    unittest.main()
