# SPDX-License-Identifier: MIT
"""Pure receipt fixtures; no Mcp instance, socket, native call, or polling."""
import copy
import json
import unittest

from tools.unreal_mcp.automation_result_contract import AutomationResultContract, ContractViolation
from tools.unreal_mcp.transport import TransportFailure


FIRST = "AI.Toolsets.AutomationTestToolset.AutomationTestToolsetTest.Subsystem_IsAvailable"
SECOND = "Example.Second"


def run_result(*entries):
    rows = [{"name": name, "state": state, "duration": 0.01,
             "errors": [], "warnings": []} for name, state in entries]
    return {"tests": rows, "total": len(rows), "duration": 0.01 * len(rows),
            "passed": sum(row["state"] == "Success" for row in rows),
            "failed": sum(row["state"] == "Fail" for row in rows),
            "skipped": sum(row["state"] == "Skipped" for row in rows)}


def prepared(names=(FIRST,)):
    contract = AutomationResultContract(list(names))
    contract.accept_discovery('{"status":"ready"}')
    contract.accept_catalog(json.dumps({"tests": list(names), "total": len(names), "returned": len(names)}))
    return contract


class AutomationResultContractTests(unittest.TestCase):
    def test_exact_completed_set_passes_without_claiming_native_qualification(self):
        result = prepared((FIRST, SECOND)).evaluate_run(json.dumps(run_result(
            (SECOND, "Success"), (FIRST, "Success"))))
        self.assertTrue(result["accepted"])
        self.assertTrue(result["all_completed"])
        self.assertFalse(result["native_runtime_qualified"])

    def test_empty_or_duplicate_requests_cannot_be_accepted(self):
        for names in ([], [FIRST, FIRST], "one.string", [" "]):
            with self.subTest(names=names), self.assertRaises(ContractViolation):
                AutomationResultContract(names)

    def test_discovery_must_complete_before_list_or_run(self):
        with self.assertRaises(ContractViolation):
            AutomationResultContract([FIRST]).accept_catalog({"tests": [FIRST], "total": 1, "returned": 1})
        with self.assertRaises(ContractViolation):
            AutomationResultContract([FIRST]).evaluate_run(run_result((FIRST, "Success")))
        with self.assertRaises(ContractViolation):
            AutomationResultContract([FIRST]).accept_discovery({"status": "discovering"})

    def test_empty_capped_wrong_or_duplicate_catalog_never_passes(self):
        for names, total, returned in (([], 0, 0), ([FIRST], 2, 1),
                                       ([SECOND], 1, 1), ([FIRST, FIRST], 2, 2)):
            contract = AutomationResultContract([FIRST])
            contract.accept_discovery({"status": "ready"})
            with self.subTest(names=names, total=total), self.assertRaises(ContractViolation):
                contract.accept_catalog({"tests": names, "total": total, "returned": returned})

    def test_one_failed_test_is_retained_even_when_other_test_passes(self):
        value = run_result((FIRST, "Success"), (SECOND, "Fail"))
        value["tests"][1]["errors"] = ["actual fixture failure"]
        result = prepared((FIRST, SECOND)).evaluate_run(value)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["all_completed"])
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["result"]["tests"][1]["errors"], ["actual fixture failure"])

    def test_skip_is_terminal_but_is_not_acceptance(self):
        result = prepared().evaluate_run(run_result((FIRST, "Skipped")))
        self.assertEqual(result["outcome"], "skipped")
        self.assertTrue(result["all_completed"])
        self.assertFalse(result["accepted"])

    def test_success_with_error_or_warning_is_not_accepted(self):
        for field, outcome in (("errors", "failed"), ("warnings", "warning")):
            value = run_result((FIRST, "Success"))
            value["tests"][0][field] = ["diagnostic"]
            with self.subTest(field=field):
                self.assertEqual(prepared().evaluate_run(value)["outcome"], outcome)

    def test_missing_running_and_unknown_states_are_incomplete(self):
        values = (run_result(), run_result((FIRST, "In Process")),
                  run_result((FIRST, "Unrecognized Future State")))
        for value in values:
            with self.subTest(value=value):
                result = prepared().evaluate_run(value)
                self.assertFalse(result["accepted"])
                self.assertFalse(result["all_completed"])
                self.assertEqual(result["outcome"], "incomplete")

    def test_aggregate_mismatch_duplicate_extra_or_nonfinite_row_is_rejected(self):
        baseline = run_result((FIRST, "Success"))
        variants = []
        wrong = copy.deepcopy(baseline)
        wrong["passed"] = 0
        variants.append(wrong)
        variants.append(run_result((FIRST, "Success"), (FIRST, "Success")))
        variants.append(run_result((SECOND, "Success")))
        for bad in (True, -1, float("nan")):
            wrong = copy.deepcopy(baseline)
            wrong["tests"][0]["duration"] = bad
            variants.append(wrong)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ContractViolation):
                prepared().evaluate_run(value)

    def test_duplicate_json_members_are_rejected(self):
        with self.assertRaises(ContractViolation):
            AutomationResultContract([FIRST]).accept_discovery('{"status":"pending","status":"ready"}')

    def test_transport_failure_preserves_unknown_without_replay(self):
        error = TransportFailure("body_read", "partial body", 20, 100)
        result = prepared().transport_failed(error)
        self.assertEqual(result["outcome"], "unknown")
        self.assertFalse(result["all_completed"])
        self.assertEqual(result["transport"], error.data)
        self.assertFalse(result["retryable"])
        self.assertFalse(result["replayed"])

    def test_complete_native_tool_error_does_not_prove_test_completion_or_effects(self):
        data = {"kind": "mcp_tool_error", "tool_name": "set_properties",
                "content_text": "UserRaisedError in ObjectTools.set_properties",
                "response_complete": True, "operation_effects_proven": False,
                "effect_state": "unknown", "retryable": False, "replayed": False}
        result = prepared().tool_failed(data)
        self.assertEqual(result["outcome"], "tool_error")
        self.assertTrue(result["response_complete"])
        self.assertFalse(result["all_completed"])
        self.assertFalse(result["operation_effects_proven"])
        self.assertEqual(result["tool_error"]["content_text"], data["content_text"])
        with self.assertRaises(ContractViolation):
            prepared().tool_failed({"outcome": "unknown"})

    def test_consumer_is_single_use(self):
        contract = prepared()
        contract.evaluate_run(run_result((FIRST, "Success")))
        with self.assertRaises(ContractViolation):
            contract.evaluate_run(run_result((FIRST, "Success")))


if __name__ == "__main__":
    unittest.main()
