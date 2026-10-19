# SPDX-License-Identifier: MIT
"""Offline adoption tests: fake ingress client and auditor, real receipt validation."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.unreal_mcp import delivery_integration as integration
from tools.unreal_mcp.test_asset_receipt_audit import (
    described_tools, meta_tools, text_result, tool_result)


ROOT = integration.receipt_audit.OWNED_ROOT
FOLDER = ROOT + "/IntegrationFixture"
ASSET = "SM_IntegrationFixture"
OBJECT_PATH = FOLDER + "/" + ASSET + "." + ASSET
ENDPOINT = "http://127.0.0.1:8000/mcp"
UNIT_ALIAS = "daedalus_unit_tools.unit_qualified_static_toolset.UnitQualifiedStaticMeshTools"
GOLDEN_RECEIPT = Path(__file__).resolve().parents[2] / (
    "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/NativeReceipts/"
    "CodexModule_CopperPatina_BridgeCoupler_85000.unreal.json")


def seal_wire(operation, raw_text=None):
    """Keep synthetic wire bytes, parsed response, length, and digest consistent."""
    if raw_text is None:
        raw_text = ("" if operation["response"] is None else
                    json.dumps(operation["response"], ensure_ascii=False, separators=(",", ":")))
    raw = raw_text.encode("utf-8")
    operation["raw_text"] = raw_text
    operation["headers"] = {"content-length": str(len(raw))}
    if raw:
        operation["headers"]["content-type"] = "application/json;charset=utf-8"
    operation["response_bytes"] = len(raw)
    operation["response_sha256"] = hashlib.sha256(raw).hexdigest()
    return operation


def replace_result(report, index, result):
    """Change semantic evidence while preserving valid byte/hash evidence."""
    operation = report["operations"][index]
    operation["response"]["result"] = result
    seal_wire(operation)


def qualified_description():
    properties = {name: {"type": "string"}
                  for name in ("folder_path", "asset_name", "source_file")}
    properties.update({name: {"type": "boolean", "default": default}
                       for name, default in (("import_materials", False),
                                             ("import_textures", False),
                                             ("combine_meshes", True))})
    return {"name": UNIT_ALIAS, "tools": [{
        "name": UNIT_ALIAS + ".import_file",
        "inputSchema": {"type": "object", "properties": properties,
                        "required": ["folder_path", "asset_name", "source_file"]},
        "outputSchema": {"type": "object", "required": ["returnValue"],
            "properties": {"returnValue": {"type": "array", "items": {
                "type": "object", "title": "/Script/CoreUObject.Object",
                "properties": {"refPath": {"type": "string"}}, "required": ["refPath"]}}}},
    }]}


class DeliveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "fixture.fbx"
        # Header/body qualification belongs to the in-editor native helper.
        # This ingress seam should not duplicate its FBX parser/identification.
        self.source.write_bytes(b"header identification deliberately delegated to native helper")
        self.saved = self.directory / "prepared.unreal.json"
        self.saved.write_bytes(GOLDEN_RECEIPT.read_bytes())
        self.output = self.directory / "official-audit.json"

    def client(self, result=None):
        client = MagicMock()
        client.describe.return_value = qualified_description()
        client.call.return_value = ([{"refPath": OBJECT_PATH}] if result is None else result)
        return client

    def import_arguments(self, **updates):
        arguments = dict(folder_path=FOLDER, asset_name=ASSET, source_file=str(self.source),
                         import_materials=False, import_textures=False, combine_meshes=True)
        arguments.update(updates)
        return arguments

    def import_qualified(self, client, **updates):
        return integration.import_static_file(client, unit_qualified=True,
                                               **self.import_arguments(**updates))

    def successful_report(self, contract, **kwargs):
        # Shape/order are pinned to the qualified R1 receipt (SHA256
        # ab26b04d06cf6b140a7aa20b61d12a4147da96cb7b273ecc8662d46f26751fe0).
        # Its out-of-repo file is not a test dependency. Minimal advertised
        # schemas come from the existing offline auditor fixtures.
        base = datetime(2026, 10, 19, tzinfo=timezone.utc)
        report = {
            "schema": integration.receipt_audit.RESULT_SCHEMA,
            "protocol": integration.receipt_audit.PROTOCOL,
            "endpoint": kwargs.get("endpoint", ENDPOINT),
            "started_utc": base.isoformat(),
            "ended_utc": (base + timedelta(minutes=1)).isoformat(),
            "outcome": "PASS", "contract": copy.deepcopy(contract), "asset_writes": 0,
            "cleanup": {"attempted": True, "confirmed": True}, "operations": [],
            "assets": [{"asset_path": row["asset_path"],
                        "expected_class": row["expected_class"],
                        "actual_class": row["expected_class"],
                        "verified": True, "registry_tags": {"Triangles": "12", "Label": "caf\u00e9"},
                        "metadata": dict(row["required_metadata"])} for row in contract["assets"]],
        }

        def add(label, method=None, params=None, result=None, *,
                http_method="POST", notification=False):
            counter = len(report["operations"]) + 1
            request = None
            if http_method == "POST":
                request = {"jsonrpc": "2.0", "method": method}
                if not notification:
                    request["id"] = counter
                if params is not None:
                    request["params"] = params
            response = (None if notification or http_method == "DELETE" else
                        {"jsonrpc": "2.0", "id": counter, "result": result})
            operation = {
                "label": label, "http_method": http_method, "request": request,
                "response": response, "status": 202 if response is None else 200,
                "started_utc": (base + timedelta(milliseconds=counter * 2)).isoformat(),
                "ended_utc": (base + timedelta(milliseconds=counter * 2 + 1)).isoformat(),
                "session_header_received": label in ("initialize", "call_tool"),
            }
            report["operations"].append(seal_wire(operation))

        add("initialize", "initialize", {
            "protocolVersion": integration.receipt_audit.PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "daedalus-asset-receipt-audit", "version": "1"}},
            {"protocolVersion": integration.receipt_audit.PROTOCOL,
             "capabilities": {"resources": {}, "tools": {"listChanged": True}},
             "serverInfo": {"name": "", "title": "", "version": ""}})
        # The notification consumes counter 2 but carries no JSON-RPC id.
        add("initialized", "notifications/initialized", {}, notification=True)
        add("tools-list", "tools/list", {}, meta_tools())
        add("list_toolsets", "tools/call", {"name": "list_toolsets", "arguments": {}},
            text_result("- " + integration.receipt_audit.ASSET_TOOLSET + ": offline fixture\n"))
        add("describe_toolset", "tools/call", {"name": "describe_toolset", "arguments": {
            "toolset_name": integration.receipt_audit.ASSET_TOOLSET}},
            text_result(json.dumps(described_tools())))
        for row in report["assets"]:
            reads = [("get_asset_class", row["actual_class"]),
                     ("get_asset_tags", row["registry_tags"])]
            if row["metadata"]:
                reads.append(("get_metadata_tags", row["metadata"]))
            for name, value in reads:
                add("call_tool", "tools/call", {"name": "call_tool", "arguments": {
                    "toolset_name": integration.receipt_audit.ASSET_TOOLSET, "tool_name": name,
                    "arguments": {"asset_path": row["asset_path"]}}},
                    text_result(json.dumps({"returnValue": value}, ensure_ascii=False)))
        add("delete-session", http_method="DELETE")
        return report

    def audit_arguments(self, **updates):
        arguments = dict(endpoint=ENDPOINT, namespace=ROOT)
        arguments.update(updates)
        return arguments

    def run_fake_audit(self, response=None, saved=None, output=None, **updates):
        saved = self.saved if saved is None else saved
        output = self.output if output is None else output
        response = self.successful_report if response is None else response
        with patch.object(integration.receipt_audit, "audit", side_effect=response) as auditor:
            report = integration.audit_saved_receipt(saved, output, **self.audit_arguments(**updates))
        return report, auditor

    def assert_retained_failure(self, response, **updates):
        before = self.saved.read_bytes()
        with patch.object(integration.receipt_audit, "audit", side_effect=response) as auditor:
            with self.assertRaises(integration.DeliveryAuditError) as raised:
                integration.audit_saved_receipt(self.saved, self.output, **self.audit_arguments(**updates))
        auditor.assert_called_once()
        self.assertEqual(raised.exception.report_path, self.output.resolve())
        self.assertEqual(raised.exception.report["outcome"], "FAIL")
        retained = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(retained, raised.exception.report)
        self.assertTrue(retained.get("error"))
        self.assertEqual(self.saved.read_bytes(), before)
        return retained

    def assert_rejected_mutations(self, cases, **updates):
        for index, (name, mutate) in enumerate(cases):
            with self.subTest(case=name):
                self.output = self.directory / ("rejected-wire-%s.json" % index)

                def response(contract, **kwargs):
                    report = self.successful_report(contract, **kwargs)
                    mutate(report)
                    return report

                retained = self.assert_retained_failure(response, **updates)
                self.assertIn("completion evidence rejected", retained["error"])

    def test_default_import_route_is_unchanged_and_does_not_describe(self):
        result = object()
        client = self.client(result)
        arguments = self.import_arguments(folder_path="/Game/LegacyIngress",
            source_file="legacy-source.glb", import_materials=True, combine_meshes=False)
        returned = integration.import_static_file(client, **arguments)
        self.assertIs(returned, result)
        client.describe.assert_not_called()
        client.call.assert_called_once_with(
            integration.STATIC_MESH_TOOLS, "import_file", **arguments)

    def test_default_import_error_propagates_without_describe_or_replay(self):
        client = self.client()
        failure = RuntimeError("original ingress import failed")
        client.call.side_effect = failure
        with self.assertRaises(RuntimeError) as raised:
            integration.import_static_file(client, **self.import_arguments())
        self.assertIs(raised.exception, failure)
        client.describe.assert_not_called()
        client.call.assert_called_once()

    def test_unit_opt_in_describes_exact_live_alias_before_one_import(self):
        client = self.client()
        before = self.source.read_bytes()
        returned = self.import_qualified(client, import_materials=True,
                                         import_textures=True, combine_meshes=False)
        self.assertIs(returned, client.call.return_value)
        self.assertEqual(integration.UNIT_QUALIFIED_TOOLS, UNIT_ALIAS)
        client.describe.assert_called_once_with(UNIT_ALIAS)
        client.call.assert_called_once_with(UNIT_ALIAS, "import_file", **self.import_arguments(
            import_materials=True, import_textures=True, combine_meshes=False))
        self.assertEqual([call[0] for call in client.mock_calls], ["describe", "call"])
        self.assertEqual(self.source.read_bytes(), before)

    def test_unit_opt_in_does_not_duplicate_the_native_header_validator(self):
        client = self.client()
        self.assertFalse(self.source.read_bytes().startswith(b"; FBX"))
        self.import_qualified(client)
        client.describe.assert_called_once()
        client.call.assert_called_once()

    def test_invalid_local_unit_inputs_fail_before_describe_or_import(self):
        wrong_extension = self.source.with_suffix(".obj")
        wrong_extension.write_bytes(b"fixture")
        cases = (
            {"source_file": str(self.directory / "missing.fbx")},
            {"source_file": str(wrong_extension)},
            {"folder_path": "/Game/Foreign/Ingress"},
            {"folder_path": ROOT + "Sibling/Ingress"},
            {"asset_name": "Nested/Asset"},
            {"import_materials": 1},
        )
        for updates in cases:
            with self.subTest(updates=updates):
                client = self.client()
                with self.assertRaises(ValueError):
                    self.import_qualified(client, **updates)
                client.describe.assert_not_called()
                client.call.assert_not_called()

    def test_unit_route_requires_an_explicit_boolean_selection(self):
        client = self.client()
        with self.assertRaises(ValueError):
            integration.import_static_file(client, unit_qualified="true", **self.import_arguments())
        client.describe.assert_not_called()
        client.call.assert_not_called()

    def test_incompatible_live_schema_stops_before_the_effectful_call(self):
        baseline = qualified_description()
        variants = []
        wrong_alias = copy.deepcopy(baseline)
        wrong_alias["name"] = "Unreviewed.Toolset"
        variants.append(wrong_alias)
        extra_tool = copy.deepcopy(baseline)
        extra_tool["tools"].append(copy.deepcopy(extra_tool["tools"][0]))
        variants.append(extra_tool)
        wrong_argument = copy.deepcopy(baseline)
        wrong_argument["tools"][0]["inputSchema"]["properties"]["source_file"]["type"] = "object"
        variants.append(wrong_argument)
        missing_required = copy.deepcopy(baseline)
        missing_required["tools"][0]["inputSchema"]["required"] = ["folder_path", "asset_name"]
        variants.append(missing_required)
        string_result = copy.deepcopy(baseline)
        string_result["tools"][0]["outputSchema"]["properties"]["returnValue"]["items"] = {"type": "string"}
        variants.append(string_result)
        for description in variants:
            with self.subTest(description=description):
                client = self.client()
                client.describe.return_value = description
                with self.assertRaises(ValueError):
                    self.import_qualified(client)
                client.describe.assert_called_once_with(UNIT_ALIAS)
                client.call.assert_not_called()

    def test_describe_failure_propagates_without_import_or_legacy_fallback(self):
        client = self.client()
        failure = RuntimeError("wrapper missing from actual profile")
        client.describe.side_effect = failure
        with self.assertRaises(RuntimeError) as raised:
            self.import_qualified(client)
        self.assertIs(raised.exception, failure)
        client.describe.assert_called_once()
        client.call.assert_not_called()

    def test_unit_import_failure_is_preserved_without_legacy_fallback_or_replay(self):
        client = self.client()
        failure = RuntimeError("unit-qualified import outcome requires reconciliation")
        client.call.side_effect = failure
        with self.assertRaises(RuntimeError) as raised:
            self.import_qualified(client)
        self.assertIs(raised.exception, failure)
        client.call.assert_called_once_with(UNIT_ALIAS, "import_file", **self.import_arguments())

    def test_invalid_import_results_fail_after_exactly_one_call_without_replay(self):
        cases = (
            [], ["/Game/Unexpected/String"], [{"refPath": "/Game/Foreign/Mesh.Mesh"}],
            [{"refPath": FOLDER + "/Nested/Mesh.Mesh"}],
            [{"refPath": FOLDER + "/Mesh.Other"}], [{"refPath": FOLDER + "/Mesh"}],
            [{"refPath": OBJECT_PATH}, {"refPath": OBJECT_PATH}],
            [{"refPath": OBJECT_PATH, "extra": "not a reference"}],
            [{"refPath": OBJECT_PATH}] * (integration.receipt_audit.MAX_ASSETS + 1),
        )
        for result in cases:
            with self.subTest(result=result):
                client = self.client(result)
                with self.assertRaises(ValueError):
                    self.import_qualified(client)
                client.describe.assert_called_once_with(UNIT_ALIAS)
                client.call.assert_called_once_with(UNIT_ALIAS, "import_file", **self.import_arguments())

    def test_actual_golden_receipt_uses_public_template_validate_and_audit_boundaries(self):
        metadata = {"ReceiptAudit": "reviewed"}
        opener = object()
        template = integration.receipt_audit.template_from_saved
        validate = integration.receipt_audit.validate_contract
        with patch.object(integration.receipt_audit, "template_from_saved", wraps=template) as templating, \
                patch.object(integration.receipt_audit, "validate_contract", wraps=validate) as validating:
            report, auditor = self.run_fake_audit(saved=GOLDEN_RECEIPT,
                required_metadata=metadata, timeout=7, opener=opener)
        templating.assert_called_once_with(GOLDEN_RECEIPT, ROOT)
        validating.assert_called_once()
        contract = auditor.call_args.args[0]
        self.assertEqual(contract["source_receipt"]["path"], str(GOLDEN_RECEIPT.resolve()))
        self.assertEqual(len(contract["assets"]), 1)
        self.assertEqual(contract["assets"][0]["required_metadata"], metadata)
        auditor.assert_called_once_with(contract, endpoint=ENDPOINT, timeout=7, opener=opener)
        self.assertEqual(report["outcome"], "PASS")
        self.assertEqual(len(report["operations"]), 9)
        self.assertEqual(report["operations"][-2]["request"]["params"]["arguments"]["tool_name"],
                         "get_metadata_tags")
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), report)

    def test_complete_wire_fixture_uses_the_qualified_eight_operation_sequence(self):
        report, auditor = self.run_fake_audit()
        auditor.assert_called_once()
        self.assertEqual([operation["label"] for operation in report["operations"]],
            ["initialize", "initialized", "tools-list", "list_toolsets", "describe_toolset",
             "call_tool", "call_tool", "delete-session"])
        self.assertEqual([operation["request"].get("id") if operation["request"] else None
                          for operation in report["operations"]], [1, None, 3, 4, 5, 6, 7, None])
        self.assertEqual(report["protocol"], "2025-06-18")
        self.assertEqual(report["endpoint"], ENDPOINT)
        self.assertIs(report["operations"][0]["session_header_received"], True)
        for operation in report["operations"]:
            raw = operation["raw_text"].encode("utf-8")
            self.assertEqual(int(operation["headers"]["content-length"]), len(raw))
            self.assertEqual(operation["response_bytes"], len(raw))
            self.assertEqual(operation["response_sha256"], hashlib.sha256(raw).hexdigest())
        tags = report["operations"][6]
        self.assertGreater(tags["response_bytes"], len(tags["raw_text"]))
        self.assertEqual(report["operations"][-1]["http_method"], "DELETE")
        self.assertIsNone(report["operations"][-1]["request"])
        self.assertIsNone(report["operations"][-1]["response"])
        self.assertEqual(report["operations"][-1]["status"], 202)
        self.assertEqual(report["operations"][-1]["raw_text"], "")

    def test_missing_reordered_duplicate_or_extra_operations_block_completion(self):
        def swap_reads(report):
            operations = report["operations"]
            operations[5], operations[6] = operations[6], operations[5]

        def insert_poll(report):
            poll = copy.deepcopy(report["operations"][6])
            poll["label"] = "poll-status"
            poll["request"]["method"] = "notifications/progress"
            report["operations"].insert(7, poll)

        self.assert_rejected_mutations((
            ("empty operations", lambda report: report.update(operations=[])),
            ("missing operations", lambda report: report.pop("operations")),
            ("missing discovery", lambda report: report["operations"].pop(2)),
            ("swapped class and tags", swap_reads),
            ("duplicate class read", lambda report: report["operations"].insert(
                6, copy.deepcopy(report["operations"][5]))),
            ("unrequested poll", insert_poll),
            ("trailing duplicate DELETE", lambda report: report["operations"].append(
                copy.deepcopy(report["operations"][-1]))),
        ))

    def test_recorded_requests_must_match_the_exact_read_only_path_and_ids(self):
        self.assert_rejected_mutations((
            ("foreign read path", lambda report: report["operations"][5]["request"]["params"]
                ["arguments"]["arguments"].update(asset_path="/Game/Foreign/Mesh.Mesh")),
            ("package alias changes exact object path", lambda report: report["operations"][5]
                ["request"]["params"]["arguments"]["arguments"].update(
                    asset_path=report["assets"][0]["asset_path"].split(".")[0])),
            ("wrong toolset", lambda report: report["operations"][5]["request"]["params"]
                ["arguments"].update(toolset_name="editor_toolset.toolsets.object.ObjectTools")),
            ("unreviewed write tool", lambda report: report["operations"][5]["request"]["params"]
                ["arguments"].update(tool_name="save_assets")),
            ("wrong meta tool", lambda report: report["operations"][5]["request"]["params"].update(
                name="describe_toolset")),
            ("extra read argument", lambda report: report["operations"][5]["request"]["params"]
                ["arguments"]["arguments"].update(include_dependencies=True)),
            ("wrong request id", lambda report: report["operations"][5]["request"].update(id=7)),
            ("string request id", lambda report: report["operations"][5]["request"].update(id="6")),
            ("boolean request id", lambda report: report["operations"][0]["request"].update(id=True)),
            ("notification has an id", lambda report: report["operations"][1]["request"].update(id=2)),
            ("wrong initialization method", lambda report: report["operations"][0]["request"].update(
                method="tools/list")),
            ("wrong initialized method", lambda report: report["operations"][1]["request"].update(
                method="notifications/cancelled")),
            ("wrong HTTP method", lambda report: report["operations"][5].update(http_method="GET")),
        ))

    def test_protocol_endpoint_and_negotiation_must_match_the_invocation(self):
        def wrong_negotiated_protocol(report):
            result = copy.deepcopy(report["operations"][0]["response"]["result"])
            result["protocolVersion"] = "2024-11-05"
            replace_result(report, 0, result)

        def missing_negotiated_protocol(report):
            result = copy.deepcopy(report["operations"][0]["response"]["result"])
            result.pop("protocolVersion")
            replace_result(report, 0, result)

        self.assert_rejected_mutations((
            ("wrong top protocol", lambda report: report.update(protocol="2024-11-05")),
            ("missing top protocol", lambda report: report.pop("protocol")),
            ("wrong top endpoint", lambda report: report.update(endpoint="http://127.0.0.1:8001/mcp")),
            ("missing top endpoint", lambda report: report.pop("endpoint")),
            ("wrong requested protocol", lambda report: report["operations"][0]["request"]["params"].update(
                protocolVersion="2024-11-05")),
            ("wrong client identity", lambda report: report["operations"][0]["request"]["params"]
                ["clientInfo"].update(name="another-client")),
            ("wrong negotiated protocol", wrong_negotiated_protocol),
            ("missing negotiated protocol", missing_negotiated_protocol),
            ("initialize did not learn session", lambda report: report["operations"][0].update(
                session_header_received=False)),
            ("session flag is not boolean", lambda report: report["operations"][5].update(
                session_header_received=1)),
        ))

    def test_raw_response_completeness_hash_and_byte_counts_are_required(self):
        def partial_but_resealed(report):
            operation = report["operations"][5]
            seal_wire(operation, operation["raw_text"][:-1])

        def character_count_is_not_utf8_byte_count(report):
            operation = report["operations"][6]
            operation["response_bytes"] = len(operation["raw_text"])
            operation["headers"]["content-length"] = str(len(operation["raw_text"]))

        self.assert_rejected_mutations((
            ("partial response retains original count", lambda report: report["operations"][5].update(
                raw_text=report["operations"][5]["raw_text"][:-1])),
            ("partial response with refreshed digest", partial_but_resealed),
            ("wrong digest", lambda report: report["operations"][5].update(response_sha256="0" * 64)),
            ("wrong byte count", lambda report: report["operations"][5].update(response_bytes=1)),
            ("string byte count", lambda report: report["operations"][5].update(
                response_bytes=str(report["operations"][5]["response_bytes"]))),
            ("boolean byte count", lambda report: report["operations"][1].update(response_bytes=False)),
            ("UTF8 count mistaken for character count", character_count_is_not_utf8_byte_count),
            ("missing raw evidence", lambda report: report["operations"][5].pop("raw_text")),
            ("missing digest", lambda report: report["operations"][5].pop("response_sha256")),
        ))

    def test_response_headers_and_http_completion_status_are_required(self):
        self.assert_rejected_mutations((
            ("missing Content-Length", lambda report: report["operations"][5]["headers"].pop("content-length")),
            ("wrong Content-Length", lambda report: report["operations"][5]["headers"].update({
                "content-length": "1"})),
            ("numeric Content-Length", lambda report: report["operations"][5]["headers"].update({
                "content-length": report["operations"][5]["response_bytes"]})),
            ("noncanonical Content-Length", lambda report: report["operations"][5]["headers"].update({
                "content-length": "0" + str(report["operations"][5]["response_bytes"])})),
            ("duplicated case-insensitive header", lambda report: report["operations"][5]["headers"].update({
                "Content-Length": report["operations"][5]["headers"]["content-length"]})),
            ("response HTTP failure", lambda report: report["operations"][5].update(status=500)),
            ("string HTTP status", lambda report: report["operations"][5].update(status="200")),
            ("notification HTTP status", lambda report: report["operations"][1].update(status=200)),
        ))

    def test_rpc_or_mcp_errors_and_malformed_result_wrappers_block_completion(self):
        def rpc_error(report):
            operation = report["operations"][5]
            operation["response"] = {"jsonrpc": "2.0", "id": 6,
                                     "error": {"code": -32603, "message": "fixture RPC failure"}}
            seal_wire(operation)

        def change_envelope(report, **changes):
            operation = report["operations"][5]
            operation["response"].update(changes)
            seal_wire(operation)

        def wrong_claimed_response(report):
            # Leave valid successful raw bytes intact; only the parsed claim differs.
            report["operations"][5]["response"]["result"] = tool_result("SkeletalMesh")

        self.assert_rejected_mutations((
            ("recorded transport error", lambda report: report["operations"][5].update(error="reset")),
            ("JSON-RPC error", rpc_error),
            ("result and error", lambda report: change_envelope(report,
                error={"code": -32603, "message": "fixture failure"})),
            ("wrong JSON-RPC version", lambda report: change_envelope(report, jsonrpc="1.0")),
            ("wrong response id", lambda report: change_envelope(report, id=7)),
            ("string response id", lambda report: change_envelope(report, id="6")),
            ("MCP error", lambda report: replace_result(report, 5,
                {"isError": True, **tool_result("StaticMesh")})),
            ("MCP error flag wrong type", lambda report: replace_result(report, 5,
                {"isError": 0, **tool_result("StaticMesh")})),
            ("missing MCP content", lambda report: replace_result(report, 5, {})),
            ("empty MCP content", lambda report: replace_result(report, 5, {"content": []})),
            ("two MCP text blocks", lambda report: replace_result(report, 5,
                {"content": tool_result("StaticMesh")["content"] * 2})),
            ("nontext MCP content", lambda report: replace_result(report, 5,
                {"content": [{"type": "image", "text": "StaticMesh"}]})),
            ("malformed Python JSON", lambda report: replace_result(report, 5, text_result("{"))),
            ("missing returnValue", lambda report: replace_result(report, 5, text_result("{}"))),
            ("extra Python result key", lambda report: replace_result(report, 5,
                text_result(json.dumps({"returnValue": "StaticMesh", "unreviewed": True})))),
            ("parsed claim differs from valid bytes", wrong_claimed_response),
        ))

    def test_duplicate_or_nonfinite_raw_json_is_rejected_even_with_matching_wire_hash(self):
        def raw_duplicate_key(report):
            operation = report["operations"][5]
            seal_wire(operation, operation["raw_text"].replace('"id":6', '"id":6,"id":6', 1))

        def nonfinite_python_result(report, value):
            replace_result(report, 5, text_result('{"returnValue":' + value + '}'))

        def raw_nonfinite_envelope(report):
            operation = report["operations"][5]
            raw = operation["raw_text"].replace('"id":6', '"id":6,"unreviewed":NaN', 1)
            seal_wire(operation, raw)

        self.assert_rejected_mutations((
            ("duplicate raw envelope key", raw_duplicate_key),
            ("raw envelope NaN", raw_nonfinite_envelope),
            ("inner NaN", lambda report: nonfinite_python_result(report, "NaN")),
            ("inner numeric overflow", lambda report: nonfinite_python_result(report, "1e309")),
        ))

    def test_discovery_requires_the_advertised_meta_and_asset_schemas(self):
        def bad_meta(report, mode):
            listing = meta_tools()
            if mode == "missing":
                listing["tools"].pop()
            elif mode == "duplicate":
                listing["tools"].append(copy.deepcopy(listing["tools"][0]))
            else:
                listing["tools"][2]["inputSchema"]["properties"]["arguments"]["type"] = "string"
            replace_result(report, 2, listing)

        def bad_description(report, mode):
            description = described_tools()
            if mode == "missing":
                description["tools"].pop(1)
            elif mode == "duplicate":
                description["tools"].append(copy.deepcopy(description["tools"][0]))
            elif mode == "wrong namespace":
                description["tools"][0]["name"] = "Foreign.AssetTools.get_asset_class"
            elif mode == "wrong schema":
                description["tools"][0]["inputSchema"]["properties"]["asset_path"]["type"] = "object"
            else:
                description["tools"][0]["inputSchema"].pop("required")
            replace_result(report, 4, text_result(json.dumps(description)))

        catalog = "- " + integration.receipt_audit.ASSET_TOOLSET + ": offline fixture\n"
        self.assert_rejected_mutations((
            ("missing meta tool", lambda report: bad_meta(report, "missing")),
            ("duplicate meta tool", lambda report: bad_meta(report, "duplicate")),
            ("wrong meta schema", lambda report: bad_meta(report, "wrong schema")),
            ("asset toolset absent", lambda report: replace_result(report, 3, text_result("- Foreign: fixture\n"))),
            ("asset toolset duplicated", lambda report: replace_result(report, 3, text_result(catalog * 2))),
            ("malformed toolset description", lambda report: replace_result(report, 4, text_result("{"))),
            ("missing asset tool", lambda report: bad_description(report, "missing")),
            ("duplicate asset tool", lambda report: bad_description(report, "duplicate")),
            ("wrong asset tool namespace", lambda report: bad_description(report, "wrong namespace")),
            ("wrong asset path schema", lambda report: bad_description(report, "wrong schema")),
            ("missing required asset path", lambda report: bad_description(report, "not required")),
        ))

    def test_complete_recorded_readbacks_must_equal_the_claimed_asset_fields(self):
        self.assert_rejected_mutations((
            ("recorded class differs", lambda report: replace_result(report, 5, tool_result("SkeletalMesh"))),
            ("recorded class malformed", lambda report: replace_result(report, 5, tool_result({"name": "StaticMesh"}))),
            ("recorded tags differ from claimed", lambda report: replace_result(report, 6, tool_result({"Triangles": "13"}))),
            ("claimed tags differ from recorded", lambda report: report["assets"][0].update(registry_tags={})),
            ("recorded tags not a string map", lambda report: replace_result(report, 6, tool_result({"Triangles": 12}))),
            ("recorded tags not an object", lambda report: replace_result(report, 6, tool_result([]))),
        ))

    def test_required_metadata_needs_its_own_discovered_recorded_read(self):
        def missing_metadata_schema(report):
            description = described_tools()
            description["tools"].pop()
            replace_result(report, 4, text_result(json.dumps(description)))

        self.assert_rejected_mutations((
            ("metadata read omitted", lambda report: report["operations"].pop(7)),
            ("metadata schema absent", missing_metadata_schema),
            ("metadata requested for wrong path", lambda report: report["operations"][7]["request"]
                ["params"]["arguments"]["arguments"].update(asset_path="/Game/Foreign/Mesh.Mesh")),
            ("metadata recorded value differs", lambda report: replace_result(report, 7,
                tool_result({"ReceiptAudit": "different"}))),
            ("metadata claim omits recorded key", lambda report: report["assets"][0].update(metadata={})),
            ("metadata recorded extra key absent from claim", lambda report: replace_result(report, 7,
                tool_result({"ReceiptAudit": "reviewed", "Unclaimed": "extra"}))),
        ), required_metadata={"ReceiptAudit": "reviewed"})

    def test_unrequested_metadata_reads_or_claims_are_rejected(self):
        def extra_metadata_read(report):
            operation = copy.deepcopy(report["operations"][6])
            operation["request"]["id"] = 8
            operation["request"]["params"]["arguments"]["tool_name"] = "get_metadata_tags"
            operation["response"]["id"] = 8
            operation["response"]["result"] = tool_result({})
            # Keep time and wire evidence valid so only the extra call differs.
            operation["started_utc"] = "2026-10-19T00:00:00.015000+00:00"
            operation["ended_utc"] = "2026-10-19T00:00:00.016000+00:00"
            seal_wire(operation)
            report["operations"][-1]["started_utc"] = "2026-10-19T00:00:00.018000+00:00"
            report["operations"][-1]["ended_utc"] = "2026-10-19T00:00:00.019000+00:00"
            report["operations"].insert(7, operation)

        self.assert_rejected_mutations((
            ("unrequested metadata call", extra_metadata_read),
            ("unrequested metadata claim", lambda report: report["assets"][0].update(
                metadata={"ReceiptAudit": "unrequested"})),
        ))

    def test_delete_must_be_present_complete_empty_and_successful(self):
        def nonempty_delete(report):
            operation = report["operations"][-1]
            operation["response"] = {"unexpected": "body"}
            seal_wire(operation)

        self.assert_rejected_mutations((
            ("DELETE missing", lambda report: report["operations"].pop()),
            ("DELETE failed", lambda report: report["operations"][-1].update(status=500)),
            ("DELETE uncertain transport error", lambda report: report["operations"][-1].update(error="reset")),
            ("DELETE response is not empty", nonempty_delete),
            ("DELETE raw whitespace", lambda report: seal_wire(report["operations"][-1], " ")),
            ("DELETE request not null", lambda report: report["operations"][-1].update(request={})),
            ("DELETE request field missing", lambda report: report["operations"][-1].pop("request")),
            ("DELETE response field missing", lambda report: report["operations"][-1].pop("response")),
        ))

    def test_report_and_operation_timestamps_must_cover_one_ordered_session(self):
        self.assert_rejected_mutations((
            ("missing report start", lambda report: report.pop("started_utc")),
            ("naive report timestamp", lambda report: report.update(started_utc="2026-10-19T00:00:00")),
            ("report end before start", lambda report: report.update(ended_utc="2026-10-18T23:59:59+00:00")),
            ("operation outside report end", lambda report: report.update(ended_utc=report["started_utc"])),
            ("operation precedes report", lambda report: report["operations"][0].update(
                started_utc="2026-10-18T23:59:59+00:00")),
            ("operation ends before start", lambda report: report["operations"][5].update(
                ended_utc=report["started_utc"])),
            ("operations overlap", lambda report: report["operations"][5].update(
                started_utc=report["operations"][4]["started_utc"])),
            ("operation time lacks timezone", lambda report: report["operations"][5].update(
                ended_utc="2026-10-19T00:00:00.013000")),
        ))

    def test_every_recorded_operation_field_is_required_even_for_a_pass_label(self):
        fields = ("label", "started_utc", "ended_utc", "http_method", "request", "status",
                  "response", "raw_text", "headers", "session_header_received",
                  "response_bytes", "response_sha256")
        self.assert_rejected_mutations(tuple(
            ("missing " + field, lambda report, field=field: report["operations"][5].pop(field))
            for field in fields))

    def test_sidecar_is_reserved_exclusively_before_auditor_and_producer_is_unchanged(self):
        before = self.saved.read_bytes()
        digest = hashlib.sha256(before).hexdigest()

        def response(contract, **kwargs):
            self.assertTrue(self.output.is_file())
            self.assertEqual(self.output.stat().st_size, 0)
            return self.successful_report(contract, **kwargs)

        self.run_fake_audit(response)
        self.assertEqual(self.saved.read_bytes(), before)
        self.assertEqual(hashlib.sha256(self.saved.read_bytes()).hexdigest(), digest)

    def test_existing_output_is_preserved_and_rejected_before_auditor(self):
        previous = b"retained prior evidence\n"
        self.output.write_bytes(previous)
        with patch.object(integration.receipt_audit, "audit") as auditor:
            with self.assertRaises(FileExistsError):
                integration.audit_saved_receipt(self.saved, self.output, **self.audit_arguments())
        auditor.assert_not_called()
        self.assertEqual(self.output.read_bytes(), previous)

    def test_producer_cannot_be_used_as_the_audit_output(self):
        before = self.saved.read_bytes()
        with patch.object(integration.receipt_audit, "audit") as auditor:
            with self.assertRaises(ValueError):
                integration.audit_saved_receipt(self.saved, self.saved, **self.audit_arguments())
        auditor.assert_not_called()
        self.assertEqual(self.saved.read_bytes(), before)

    def test_unsaved_and_foreign_profiles_fail_before_auditor_or_sidecar_creation(self):
        baseline = json.loads(self.saved.read_text(encoding="utf-8"))
        unsaved = copy.deepcopy(baseline)
        unsaved["stage"] = "batch_save_pending"
        foreign = copy.deepcopy(baseline)
        foreign["results"][0]["destination"] = "/Game/Foreign"
        for receipt in (unsaved, foreign):
            with self.subTest(stage=receipt["stage"]):
                self.saved.write_text(json.dumps(receipt), encoding="utf-8")
                with patch.object(integration.receipt_audit, "audit") as auditor:
                    with self.assertRaises(ValueError):
                        integration.audit_saved_receipt(self.saved, self.output, **self.audit_arguments())
                auditor.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_invalid_required_metadata_fails_before_auditor(self):
        with patch.object(integration.receipt_audit, "audit") as auditor:
            with self.assertRaises(ValueError):
                integration.audit_saved_receipt(self.saved, self.output,
                    **self.audit_arguments(required_metadata={"ReceiptAudit": 1}))
        auditor.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_failed_audit_is_retained_and_raises_delivery_audit_error(self):
        def response(contract, **kwargs):
            report = self.successful_report(contract, **kwargs)
            report.update(outcome="FAIL", error="asset class differs")
            return report

        retained = self.assert_retained_failure(response)
        self.assertEqual(retained["error"], "asset class differs")

    def test_cleanup_failure_blocks_completion_even_when_asset_readback_succeeded(self):
        def response(contract, **kwargs):
            report = self.successful_report(contract, **kwargs)
            report["cleanup"] = {"attempted": True, "confirmed": False, "error": "DELETE failed"}
            return report

        retained = self.assert_retained_failure(response)
        self.assertFalse(retained["cleanup"]["confirmed"])

    def test_auditor_exception_is_retained_as_failure_without_retry(self):
        def response(contract, **kwargs):
            raise ConnectionResetError("fixture uncertain response")

        retained = self.assert_retained_failure(response)
        self.assertIn("fixture uncertain response", retained["error"])

    def test_malformed_nonobject_report_is_retained_as_failure(self):
        retained = self.assert_retained_failure(lambda contract, **kwargs: None)
        self.assertIn("malformed", retained["error"])

    def test_pass_label_requires_exact_verified_paths_classes_metadata_and_cleanup(self):
        mutations = (
            lambda report: report["cleanup"].update(attempted=False),
            lambda report: report["cleanup"].update(confirmed=1),
            lambda report: report.update(asset_writes=False),
            lambda report: report.update(assets=[]),
            lambda report: report["assets"].append(copy.deepcopy(report["assets"][0])),
            lambda report: report["assets"][0].update(asset_path="/Game/Foreign/Mesh.Mesh"),
            lambda report: report["assets"][0].update(actual_class="SkeletalMesh"),
            lambda report: report["assets"][0].update(expected_class="SkeletalMesh"),
            lambda report: report["assets"][0].update(verified=1),
            lambda report: report["assets"][0].update(metadata={"ReceiptAudit": "different"}),
            lambda report: report.update(contract={}),
            lambda report: report.update(error="contradictory failure"),
            lambda report: report["cleanup"].update(error="contradictory cleanup failure"),
            lambda report: report["assets"][0].update(registry_tags=[]),
            lambda report: report["assets"][0].update(registry_tags={"Source": 7}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                self.output = self.directory / ("invalid-completion-%s.json" % index)

                def response(contract, **kwargs):
                    report = self.successful_report(contract, **kwargs)
                    mutate(report)
                    return report

                with patch.object(integration.receipt_audit, "audit", side_effect=response) as auditor:
                    with self.assertRaises(integration.DeliveryAuditError):
                        integration.audit_saved_receipt(self.saved, self.output,
                            **self.audit_arguments(required_metadata={"ReceiptAudit": "reviewed"}))
                auditor.assert_called_once()
                self.assertEqual(json.loads(self.output.read_text(encoding="utf-8"))["outcome"], "FAIL")


if __name__ == "__main__":
    unittest.main()
