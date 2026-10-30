# SPDX-License-Identifier: MIT
"""Pure consumers for installed UE 5.8.3 AutomationTestToolset results.

Feed each completed ``Mcp.call`` return value in order: DiscoverTests,
ListTests narrowed to the exact requested set, then RunTests. This module does
not dispatch, poll, select a session, retry, or qualify an editor. ``accepted``
means only that the supplied receipts meet this strict acceptance contract.
Source review is not native runtime qualification.
"""
import json
import math

from .transport import TransportFailure


TOOLSET = "AutomationTestToolset.AutomationTestToolset"
NATIVE_RUNTIME_QUALIFIED = False
SOURCE_PROVENANCE = {
    "engine": "UE 5.8.3 / changelist 58210709",
    "toolset_cpp_sha256": "f4b66c8c3567810a4da11dd1298975798e576b42dd6ea4d8f843f7abb415f0b9",
    "subsystem_cpp_sha256": "f91fb0253aeecc8496fcbe63b70352afe2c985f34a9b4909428be2c3e6b46f0e",
    "state_h_sha256": "396f3e478828f70974ffba7bdcc35862dff4e31456db198056e106771dcdfb9b",
    "source_lines": "AutomationTestToolset.cpp:55-165; AutomationTestToolsetSubsystem.cpp:214-254,275-373; AutomationState.h:13-26",
    "seam": "client.Mcp.call return value; no client or transport modification",
}


class ContractViolation(ValueError):
    """A supplied receipt cannot establish the required result contract."""


def _require(condition, message):
    if not condition:
        raise ContractViolation(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON member: " + key)
        result[key] = value
    return result


def _nonfinite(_value):
    raise ContractViolation("non-finite JSON number")


def _object(value):
    # Mcp.call already unwraps returnValue. Do not guess other wire envelopes.
    if isinstance(value, str):
        try:
            value = json.loads(value, object_pairs_hook=_pairs, parse_constant=_nonfinite)
        except (ValueError, TypeError) as exc:
            raise ContractViolation("invalid tool JSON: " + str(exc)) from exc
    _require(isinstance(value, dict), "expected the completed tool's JSON object")
    return value


def _count(value, field):
    _require(type(value) is int and value >= 0, "invalid nonnegative count: " + field)
    return value


def _duration(value):
    _require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
             "invalid finite duration")


def _names(values):
    _require(isinstance(values, (list, tuple)) and bool(values),
             "requested test set must be nonempty")
    _require(all(isinstance(name, str) and name and name.strip() == name for name in values),
             "test names must be exact nonempty strings")
    _require(len(set(values)) == len(values), "duplicate test name")
    return tuple(values)


class AutomationResultContract:
    """Single-use receipt ordering and exact-set completion check.

    Successful tests with warnings are retained as ``warning``, not accepted.
    Unknown/localized state strings cannot establish terminal completion.
    A TransportFailure always leaves the native outcome unknown, even if a
    previous receipt was valid; no receipt grants permission to replay a call.
    """

    def __init__(self, requested_tests):
        self.requested = _names(requested_tests)
        self._phase = "discovery"

    def accept_discovery(self, value):
        _require(self._phase == "discovery", "DiscoverTests must complete first, once")
        self._phase = "closed"
        _require(_object(value).get("status") == "ready", "discovery is not ready")
        self._phase = "catalog"

    def accept_catalog(self, value):
        _require(self._phase == "catalog", "ListTests requires completed discovery")
        self._phase = "closed"
        result = _object(value)
        names = _names(result.get("tests"))
        total = _count(result.get("total"), "total")
        returned = _count(result.get("returned"), "returned")
        _require(total == returned == len(names), "catalog is empty, capped, or inconsistent")
        _require(set(names) == set(self.requested), "catalog differs from exact requested set")
        self._phase = "run"

    def evaluate_run(self, value):
        _require(self._phase == "run", "RunTests result requires completed exact catalog")
        self._phase = "closed"
        result = _object(value)
        rows = result.get("tests")
        _require(isinstance(rows, list), "missing test result array")
        for field in ("passed", "failed", "skipped", "total"):
            _count(result.get(field), field)
        _duration(result.get("duration"))
        _require(result["total"] == len(rows), "result total differs from rows")
        names, states = [], []
        errors, warnings = [], []
        for row in rows:
            _require(isinstance(row, dict), "invalid test result row")
            name, state = row.get("name"), row.get("state")
            _require(isinstance(name, str) and name in self.requested,
                     "unexpected result test name")
            _require(name not in names, "duplicate result test name")
            _require(isinstance(state, str) and bool(state), "invalid test state")
            _duration(row.get("duration"))
            for field in ("errors", "warnings"):
                _require(isinstance(row.get(field), list)
                         and all(isinstance(item, str) for item in row[field]),
                         "invalid test diagnostics: " + field)
            names.append(name)
            states.append(state)
            errors.extend(row["errors"])
            warnings.extend(row["warnings"])
        for field, state in (("passed", "Success"), ("failed", "Fail"), ("skipped", "Skipped")):
            _require(result[field] == states.count(state), "aggregate differs from test states: " + field)
        exact_set = set(names) == set(self.requested)
        all_completed = exact_set and all(state in ("Success", "Fail", "Skipped") for state in states)
        problems = []
        if not exact_set:
            problems.append("missing_requested_results")
        if not all_completed:
            problems.append("not_all_tests_terminal")
        if result["failed"] or errors:
            problems.append("test_failures")
        if result["skipped"]:
            problems.append("skipped_tests")
        if warnings:
            problems.append("test_warnings")
        outcome = ("failed" if "test_failures" in problems else
                   "incomplete" if not all_completed else
                   "skipped" if result["skipped"] else
                   "warning" if warnings else "passed")
        return {"accepted": not problems, "outcome": outcome,
                "all_completed": all_completed, "requested": list(self.requested),
                "problems": problems, "result": result, "retryable": False,
                "replayed": False, "native_runtime_qualified": NATIVE_RUNTIME_QUALIFIED}

    def transport_failed(self, error):
        _require(self._phase != "closed", "contract is already closed")
        _require(isinstance(error, TransportFailure), "expected existing TransportFailure")
        phase, self._phase = self._phase, "closed"
        return {"accepted": False, "outcome": "unknown", "all_completed": False,
                "requested": list(self.requested), "phase": phase,
                "problems": ["transport_outcome_unknown"], "transport": dict(error.data),
                "retryable": False, "replayed": False,
                "native_runtime_qualified": NATIVE_RUNTIME_QUALIFIED}

    def tool_failed(self, error_data):
        """Consume the explicit .data of the staged audit's McpToolError.

        A completed error reply proves neither all-test completion nor rollback.
        Generic exceptions lack this evidence and must not be reclassified here.
        """
        _require(self._phase != "closed", "contract is already closed")
        _require(isinstance(error_data, dict)
                 and error_data.get("kind") in ("mcp_tool_error", "malformed_mcp_result")
                 and error_data.get("response_complete") is True
                 and error_data.get("operation_effects_proven") is False
                 and error_data.get("effect_state") == "unknown"
                 and error_data.get("retryable") is False
                 and error_data.get("replayed") is False,
                 "expected explicit completed MCP error evidence")
        for field, maximum in (("tool_name", 160), ("content_text", 1024)):
            _require(isinstance(error_data.get(field), str) and len(error_data[field]) <= maximum,
                     "missing or unbounded MCP diagnostic: " + field)
        phase, self._phase = self._phase, "closed"
        return {"accepted": False, "outcome": "tool_error", "all_completed": False,
                "response_complete": True, "operation_effects_proven": False,
                "requested": list(self.requested), "phase": phase,
                "problems": ["completed_tool_error"], "tool_error": dict(error_data),
                "retryable": False, "replayed": False,
                "native_runtime_qualified": NATIVE_RUNTIME_QUALIFIED}
