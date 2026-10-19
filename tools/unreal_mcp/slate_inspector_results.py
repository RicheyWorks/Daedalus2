# SPDX-License-Identifier: MIT
"""Pure consumers of installed UE 5.8.3 Slate Inspector FString returns.

Supply the decoded returnValue from an independently qualified caller, not a
guessed MCP envelope. No Unreal/client/transport imports, calls, observer changes,
or input simulation occur here. Fixtures establish source contracts, not runtime
qualification. Caller request identity and ownership attestations remain trusted
inputs; neither hashes nor text authenticate them.

Snapshot is plain accessibility text, NOT JSON. Its normal path may return an
observer cache without a generation timestamp. Even source-location requests
that bypass that cache cannot prove current editor state from supplied text.
Windows(list) has indices/titles only: it cannot bind a window to a widget ref.
"""
import hashlib
import json
import re


TOOLSET = "SlateInspectorToolset.SlateInspectorToolset"
NATIVE_RUNTIME_QUALIFIED = False
MAX_RETURN_BYTES = 262144
MAX_ROWS = 1024
MAX_DEPTH = 64  # Adapter budget, not an asserted native limit.
CACHED_SNAPSHOT_SIZE_UNITS = "FString::Len; UTF-16 code units on the installed Windows receiver"
_INT32_MAX = 2147483647
_REF = re.compile(r"[a-z]+([1-9][0-9]{0,9})\Z")
_OBSERVER = re.compile(r"observer_([1-9][0-9]{0,9})\Z")
SOURCE_PROVENANCE = {
    "engine": "installed UE 5.8.3",
    "plugin": "Engine/Plugins/Experimental/Toolsets/SlateInspectorToolset",
    "header_sha256": "ead2edba7f9aa524a26318bddc1f959b44e011841ff863887f279b38afb39425",
    "implementation_sha256": "55afda70382aac27e71e18676164ef51a767f90e22ecf1f84d567a18d2215a95",
    "observer_manager_sha256": "0b07188ebf6956d26cf78a2f050f214c425cb14be3252582b2f989cb7ada92ef",
    "snapshot_renderer_sha256": "24ff38a135526a90033ec33ce3653495e141e19743af8df71210db48800499c4",
    "source_lines": "SlateInspectorToolset.h:81-113,164-168; .cpp:167-194,218-251,618-668; SnapshotRenderer.cpp:138-169",
    "seam": "qualified caller's decoded FString returnValue only",
}


class ContractViolation(ValueError):
    """Supplied data does not satisfy this bounded source-derived contract."""


def _require(condition, message):
    if not condition:
        raise ContractViolation(message)


def _raw_text(value):
    _require(type(value) is str, "decoded FString returnValue required")
    _require(len(value) <= MAX_RETURN_BYTES, "return exceeds adapter byte budget")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ContractViolation("invalid Unicode return") from error
    _require(len(raw) <= MAX_RETURN_BYTES, "return exceeds adapter byte budget")
    _require(not value.lstrip().startswith("Error:"), "native error return")
    return raw


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "duplicate JSON member: " + key)
        result[key] = value
    return result


def _constant(_):
    raise ContractViolation("non-finite JSON constant")


def _array(value):
    _raw_text(value)
    try:
        rows = json.loads(value, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as error:
        raise ContractViolation("invalid JSON return: " + str(error)) from error
    _require(type(rows) is list and len(rows) <= MAX_ROWS, "bounded JSON array required")
    return rows


def _integer(value, maximum=_INT32_MAX):
    return type(value) is int and 0 <= value <= maximum


def _ref(value):
    match = _REF.fullmatch(value) if type(value) is str else None
    return match is not None and int(match.group(1)) <= _INT32_MAX


def _identifier(value):
    match = _OBSERVER.fullmatch(value) if type(value) is str else None
    return match is not None and int(match.group(1)) <= _INT32_MAX


def read_observers(return_value):
    """Validate ListObservers' exact JSON array; empty is not a failure or health proof.

    cachedSnapshotSize is native FString::Len(), NOT UTF-8 bytes, cache age,
    widget count, or proof that any widget/observer belongs to this caller.
    Non-root rootRef may be empty when its weak root/ref is unavailable.
    """
    rows = _array(return_value)
    identities = set()
    root_count = 0
    fields = {"identifier", "root", "rootRef", "maxDepth", "cachedSnapshotSize"}
    for row in rows:
        _require(type(row) is dict and set(row) == fields, "unknown observer row schema")
        _require(_identifier(row["identifier"]), "invalid observer identifier")
        _require(row["identifier"] not in identities, "duplicate observer identifier")
        identities.add(row["identifier"])
        _require(type(row["root"]) is bool, "root must be bool")
        _require(row["rootRef"] == "" or _ref(row["rootRef"]), "invalid root ref")
        _require(not row["root"] or row["rootRef"] == "", "root observer cannot have a widget ref")
        _require(_integer(row["maxDepth"]) and _integer(row["cachedSnapshotSize"]), "invalid observer counts")
        root_count += int(row["root"])
    _require(root_count <= 1, "multiple root observers")
    return rows


def read_windows(return_value, *, action):
    """Consume ONLY an explicitly list-qualified Windows return, never select/close."""
    _require(action == "list", "only explicit Windows(action=list) results are supported")
    rows = _array(return_value)
    for index, row in enumerate(rows):
        _require(type(row) is dict and set(row) == {"index", "title"}, "unknown window row schema")
        _require(type(row["index"]) is int and row["index"] == index, "window indices must preserve native array order")
        _require(type(row["title"]) is str, "window title must be string")
        try:
            row["title"].encode("utf-8", errors="strict")
        except UnicodeError as error:
            raise ContractViolation("invalid Unicode window title") from error
    return rows


class PanelResults:
    """One caller-approved ref and bounded depth; no all-windows snapshot fallback.

    Approval and qualified request/result pairing come from the external caller.
    Native refs are session-local cache identities, not durable asset identities.
    This class neither discovers approval nor certifies a live panel's identity.
    """

    def __init__(self, approved_ref, max_depth=30):
        _require(_ref(approved_ref), "explicit single approved panel ref required")
        _require(_integer(max_depth, MAX_DEPTH), "depth exceeds adapter budget")
        self.approved_ref = approved_ref
        self.max_depth = max_depth

    def snapshot(self, return_value, *, ref, max_depth, include_source_locations):
        """Qualify supplied request metadata/content without parsing a widget schema."""
        _require(ref == self.approved_ref, "request ref differs from approved panel")
        _require(_integer(max_depth, self.max_depth), "request depth exceeds approved budget")
        _require(type(include_source_locations) is bool, "explicit source-location bool required")
        raw = _raw_text(return_value)
        _require("\x00" not in return_value, "NUL in snapshot text")
        _require(bool(return_value.strip()), "empty snapshot cannot qualify panel content")
        return {
            "toolset": TOOLSET, "tool": "Snapshot", "approved_ref": self.approved_ref,
            "requested_depth": max_depth, "include_source_locations": include_source_locations,
            "contract_valid": True, "content_present": True, "outcome": "supplied_text",
            "content_sha256": hashlib.sha256(raw).hexdigest(), "utf8_bytes": len(raw),
            "text": return_value, "representation": "plain_accessibility_text",
            "panel_binding": "qualified_caller_request_only", "freshness": "unproven",
            "cache": "lookup_bypassed_by_request" if include_source_locations else "possibly_observer_cached",
            "native_runtime_qualified": False, "automatic_actions": False,
        }

    def cleanup_plan(self, before_return_value, after_return_value, *,
                     observe_return_value, caller_owns_observer=False):
        """Produce an inert plan only for a caller-attested newly owned observer.

        Observe may return a PREEXISTING observer and widen its depth. Its return
        alone therefore establishes no ownership. Require the caller's explicit
        attestation plus exact before/after/returned-ID/ref agreement. This does
        not resolve concurrent ownership or authenticate observations. A native
        owner must revalidate live custody before any separately authorized action.
        """
        _require(type(caller_owns_observer) is bool and caller_owns_observer,
                 "explicit qualified-caller ownership attestation required")
        _require(_identifier(observe_return_value), "exact Observe identifier required")
        before = read_observers(before_return_value)
        after = read_observers(after_return_value)
        _require(all(row["identifier"] != observe_return_value for row in before),
                 "preexisting/shared observer is not eligible for this cleanup plan")
        matching = [row for row in after if row["identifier"] == observe_return_value]
        _require(len(matching) == 1, "owned observer absent from supplied after observation")
        observer = matching[0]
        _require(not observer["root"] and observer["rootRef"] == self.approved_ref,
                 "root, unresolved or foreign observer cannot be cleaned up")
        return {
            "toolset": TOOLSET, "planned_tool": "Unobserve", "identifier": observe_return_value,
            "approved_ref": self.approved_ref, "caller_attested_ownership": True,
            "before_sha256": hashlib.sha256(_raw_text(before_return_value)).hexdigest(),
            "after_sha256": hashlib.sha256(_raw_text(after_return_value)).hexdigest(),
            "plan_only": True, "execution_authorized": False, "live_revalidation_required": True,
            "native_runtime_qualified": False,
        }
