# SPDX-License-Identifier: MIT
"""Pure consumers of operator-supplied official Details-panel observations.

No Unreal, client, transport, native calls, input, observer changes or file I/O.
Supplied receipts are evidence from a separately qualified operator, not an
authentication mechanism or permission to execute a plan.
"""
import datetime
import hashlib
import json
import math
import re
import uuid

from tools.unreal_mcp import slate_inspector_results as results
from tools.unreal_mcp import slate_inspector_packet as packets
from tools.unreal_mcp.slate_inspector_results import ContractViolation


SCOPE = "existing_primary_level_editor_details"
TAB_ID = "LevelEditorSelectionDetails"
BINDING_CONTRACT_SHA256 = "cba01057e2bcf49f2f6f70bb4bde62c6c53cd4a2a6aa384e0b6656efcd367bfa"
CAPTURE_CONTRACT_SHA256 = "4e930cd79e430f1a9151831cc07b709f936b871abec2577503b829f02f1189d4"
CAPTURE_SCHEMA = "daedalus.official-slate-panel-capture.v1"
MAX_CAPTURE_AGE_SECONDS = 300
_CAPTURE_FIELDS = {
    "schema", "capture_id", "editor", "route", "binding", "snapshot_request",
    "call", "raw_return_text", "raw_return_utf8_sha256", "preservation", "state_effects",
}
_PRESERVED_FIELDS = (
    "project", "world", "pie", "game_world", "dirty_maps", "dirty_content",
    "scene", "selection", "camera",
)
_TRUE_FLAGS = (
    "owning_manager_agrees", "window_identity_agrees", "panel_visible",
    "tab_foreground", "window_visible", "cache_roundtrip",
    "keyboard_focus_preserved", "active_window_preserved",
)
_BINDING_FIELDS = {
    "scope", "status", "bound", "approved_ref", "process_id", "world",
    "tab_id", "tab_label", "panel_type", "window_title", "ref_preexisting",
    "diagnostic", *_TRUE_FLAGS,
}


def _require(condition, message):
    if not condition:
        raise ContractViolation(message)


def _text(value, field, *, allow_empty=False, maximum=4096):
    _require(type(value) is str and len(value) <= maximum, "invalid " + field)
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ContractViolation("invalid Unicode in " + field) from error
    _require(len(raw) <= maximum and "\x00" not in value, "invalid " + field)
    _require(allow_empty or bool(value.strip()), "empty " + field)
    return raw


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "duplicate JSON member: " + key)
        result[key] = value
    return result


def _constant(_):
    raise ContractViolation("non-finite JSON constant")


def _object(return_value):
    _text(return_value, "decoded FString JSON return", maximum=results.MAX_RETURN_BYTES)
    try:
        value = json.loads(return_value, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as error:
        raise ContractViolation("invalid JSON return") from error
    _require(type(value) is dict, "JSON object return required")
    return value


def _process_id(value):
    return type(value) is int and 0 < value <= 4294967295


def read_details_binding(return_value, *, expected_process_id, expected_world):
    """Validate the exact native binding schema against external receiver identity.

    PID/world expectations must come from the operator's current receiver, not
    from the supplied binding itself. This validates data, not its authenticity.
    """
    _require(_process_id(expected_process_id), "invalid expected process ID")
    _text(expected_world, "expected world")
    binding = _object(return_value)
    _require(set(binding) == _BINDING_FIELDS, "unknown or missing binding fields")
    _require(binding["scope"] == SCOPE and binding["status"] == "Bound"
             and binding["bound"] is True, "native binding was not Bound")
    _require(_process_id(binding["process_id"])
             and binding["process_id"] == expected_process_id, "binding process ID mismatch")
    _text(binding["world"], "binding world")
    _require(binding["world"] == expected_world, "binding world mismatch")
    _require(binding["tab_id"] == TAB_ID, "unapproved Details tab")
    results.PanelResults(binding["approved_ref"], 2)
    for flag in _TRUE_FLAGS:
        _require(binding[flag] is True, "binding flag must be true: " + flag)
    _require(type(binding["ref_preexisting"]) is bool, "ref_preexisting must be bool")
    _require(binding["diagnostic"] == "", "Bound binding contains a diagnostic")
    for field in ("tab_label", "panel_type", "window_title"):
        _text(binding[field], field, allow_empty=field != "panel_type")
    return binding


def _utc_now():
    # Deliberately no caller-supplied clock/freshness override in the public API.
    return datetime.datetime.now(datetime.timezone.utc)


def _iso_for_datetime(value):
    # Python 3.10 accepts only three/six fractional digits; Windows StartUtc
    # retains seven. Normalize only for comparison, keeping original identity
    # strings and hashes unchanged (and checking process-start text exactly).
    value = value.replace("Z", "+00:00")
    return re.sub(r"\.(\d{1,7})(?=[+-]\d{2}:\d{2}$)",
                  lambda match: "." + match.group(1)[:6].ljust(6, "0"), value)


def _utc(value, field):
    _text(value, field, maximum=64)
    _require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|\+00:00)", value)
             is not None, "explicit UTC required: " + field)
    try:
        return datetime.datetime.fromisoformat(_iso_for_datetime(value))
    except ValueError as error:
        raise ContractViolation("invalid UTC: " + field) from error


def _keys(value, expected, field):
    _require(type(value) is dict and set(value) == set(expected), "unknown or missing " + field + " fields")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value, expected, field):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None
             and value == expected, "hash mismatch: " + field)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ContractViolation("malformed supplied JSON data") from error


def _snapshot_time(value):
    # The existing preservation helper retains an ISO timestamp, possibly with
    # a local UTC offset. Preserve it verbatim; only compare aware instants.
    _text(value, "preservation timestamp", maximum=64)
    try:
        instant = datetime.datetime.fromisoformat(_iso_for_datetime(value))
    except ValueError as error:
        raise ContractViolation("invalid preservation timestamp") from error
    _require(instant.tzinfo is not None and instant.utcoffset() is not None,
             "timezone required on preservation timestamp")
    return instant


def _check_preservation(preservation, expected_world, started, ended, checked):
    _keys(preservation, {"before", "after", "equal_fields", "accepted"}, "preservation")
    _require(preservation["accepted"] is True, "preservation was not accepted")
    _keys(preservation["equal_fields"], _PRESERVED_FIELDS, "preservation equality")
    required = {"utc", "writes", "bridge_before", "bridge_after", "errors", "interchange", *_PRESERVED_FIELDS}
    for state in (preservation["before"], preservation["after"]):
        _keys(state, required, "preservation snapshot")
        _require(type(state["errors"]) is dict and not state["errors"], "snapshot field errors")
        _require(type(state["writes"]) is int and state["writes"] == 0, "snapshot reported writes")
        _text(state["project"], "snapshot project")
        _require(state["world"] == expected_world and state["pie"] is False
                 and state["game_world"] is None, "snapshot world/PIE differs")
        for field in ("dirty_maps", "dirty_content"):
            _require(type(state[field]) is list and not state[field], "dirty snapshot packages")
        for field in ("bridge_before", "bridge_after"):
            pending = state[field]
            _keys(pending, {"queue", "other_running", "remote_locked", "unfinished_async"}, "bridge state")
            _require(type(pending["queue"]) is int and pending["queue"] == 0
                     and pending["remote_locked"] is False, "bridge queue/lock not idle")
            for jobs in ("other_running", "unfinished_async"):
                _require(type(pending[jobs]) is list and not pending[jobs], "bridge work remains")
        scene = state["scene"]
        _keys(scene, {"actors", "sha256", "scope"}, "scene identity")
        _require(type(scene["actors"]) is int and scene["actors"] >= 0
                 and type(scene["sha256"]) is str
                 and re.fullmatch(r"[0-9a-f]{64}", scene["sha256"]) is not None
                 and scene["scope"] == "actor path/class/label/location/rotation/scale", "invalid scene identity")
        _require(type(state["selection"]) is list, "selection must be a list")
        for selected in state["selection"]:
            _text(selected, "selected object path")
        _keys(state["camera"], {"location", "rotation"}, "camera")
        for vector in state["camera"].values():
            _require(type(vector) is list and len(vector) == 3
                     and all(type(component) in (int, float) and math.isfinite(component)
                             for component in vector), "invalid camera vector")
        _require(type(state["interchange"]) is dict, "interchange snapshot must be an object")
    before, after = preservation["before"], preservation["after"]
    for field in _PRESERVED_FIELDS:
        _require(preservation["equal_fields"][field] is True
                 and _canonical(before[field]) == _canonical(after[field]), "preservation differs: " + field)
    before_time, after_time = _snapshot_time(before["utc"]), _snapshot_time(after["utc"])
    _require(before_time <= started <= ended <= after_time <= checked,
             "preservation snapshots do not bracket the captured call")
    _require((checked - before_time).total_seconds() <= MAX_CAPTURE_AGE_SECONDS,
             "historical preservation cannot qualify as current evidence")


def _accessibility_text(text):
    # Installed SnapshotRenderer emits line-oriented role/geometry/ref records;
    # do not interpret source tags as labels or build a new widget/action model.
    _require(type(text) is str, "decoded Snapshot FString required")
    _require(not any(ord(char) < 32 and char not in "\r\n" for char in text),
             "control character in accessibility text")
    lines = text.splitlines()
    _require(0 < len(lines) <= results.MAX_ROWS, "bounded accessibility lines required")
    pattern = re.compile(r'^(?:  )*[a-z][a-z0-9_-]*(?: .*?)?'
                         r' \[pos=-?\d+,-?\d+ size=-?\d+,-?\d+\]'
                         r'(?: \[src=[^\]\r\n]+\])? \[ref=([a-z]+[1-9][0-9]{0,9})\]$')
    for line in lines:
        match = pattern.fullmatch(line)
        _require(match is not None, "malformed accessibility record")
        results.PanelResults(match.group(1), 2)


def read_panel_capture(capture, *, expected_process_id, expected_process_start_utc,
                       expected_world, expected_capture_id, expected_request_id,
                       consumed_capture_ids):
    """Consume retained terminal['result'] once as caller-attested capture evidence.

    Receiver identity and outstanding capture/request IDs must be independently
    retained by the operator. Keep the consumed-ID set across calls. Hashes do
    not authenticate supplied evidence. Old captures remain historical artifacts;
    this current-capture check rejects them without changing their timestamps.
    The embedded existing packet remains plan-only and natively unqualified.
    """
    _keys(capture, _CAPTURE_FIELDS, "capture")
    _require(capture["schema"] == CAPTURE_SCHEMA, "unknown capture schema")
    _require(type(consumed_capture_ids) is set, "caller-owned consumed-ID set required")
    _text(expected_capture_id, "expected capture ID", maximum=64)
    try:
        _require(str(uuid.UUID(expected_capture_id)) == expected_capture_id, "canonical UUID capture ID required")
    except ValueError as error:
        raise ContractViolation("invalid capture ID") from error
    _text(expected_request_id, "expected retained request ID", maximum=256)
    _require(capture["capture_id"] == expected_capture_id, "unexpected capture ID")
    replay_keys = {"capture:" + expected_capture_id, "request:" + expected_request_id}
    _require(not replay_keys.intersection(consumed_capture_ids), "capture/request already consumed")
    _require(len(_canonical(capture)) <= 2097152, "capture exceeds evidence byte budget")

    editor = capture["editor"]
    _keys(editor, {"pid", "process_start_utc", "world"}, "editor")
    _require(_process_id(expected_process_id) and type(editor["pid"]) is int
             and editor["pid"] == expected_process_id, "capture process ID mismatch")
    _text(expected_world, "expected world")
    _require(editor["world"] == expected_world, "capture world mismatch")
    process_start = _utc(editor["process_start_utc"], "editor process start")
    _require(editor["process_start_utc"] == expected_process_start_utc
             and process_start == _utc(expected_process_start_utc, "expected process start"),
             "capture process start mismatch")

    route = capture["route"]
    _keys(route, {"kind", "bridge_command", "bridge_address", "request_id",
                  "toolset_object_path", "toolset_class_path", "reflected_method"}, "route")
    _require(route["kind"] == "existing_bridge_reflected_uobject_call"
             and route["bridge_command"] == "execute_python"
             and route["bridge_address"] == "127.0.0.1:9877"
             and route["request_id"] == expected_request_id
             and route["toolset_class_path"] == "/Script/SlateInspectorToolset.SlateInspectorToolset"
             and route["reflected_method"] == "Snapshot", "unqualified capture route")
    _text(route["toolset_object_path"], "actual toolset CDO path")

    binding_slice = capture["binding"]
    _keys(binding_slice, {"raw_return_json", "payload", "utf8_sha256"}, "binding slice")
    binding = read_details_binding(binding_slice["raw_return_json"],
                                   expected_process_id=expected_process_id, expected_world=expected_world)
    _require(_canonical(binding_slice["payload"]) == _canonical(binding), "binding payload differs from raw return")
    _digest(binding_slice["utf8_sha256"], _sha256(binding_slice["raw_return_json"].encode("utf-8")), "binding")
    request = capture["snapshot_request"]
    _keys(request, {"Ref", "MaxDepth", "bIncludeSourceLocations"}, "Snapshot request")
    _require(request["Ref"] == binding["approved_ref"] and type(request["MaxDepth"]) is int
             and request["MaxDepth"] == 2 and request["bIncludeSourceLocations"] is True,
             "Snapshot request differs from approved single-panel request")

    call = capture["call"]
    _keys(call, {"started_utc", "ended_utc"}, "call")
    started = _utc(call["started_utc"], "call start")
    ended = _utc(call["ended_utc"], "call end")
    checked = _utc_now()
    _require(process_start <= started <= ended <= checked, "unordered or future capture provenance")
    _require((checked - ended).total_seconds() <= MAX_CAPTURE_AGE_SECONDS,
             "historical capture cannot qualify as current evidence")

    text = capture["raw_return_text"]
    snapshot = results.PanelResults(binding["approved_ref"], 2).snapshot(
        text, ref=request["Ref"], max_depth=2, include_source_locations=True)
    _accessibility_text(text)
    _digest(capture["raw_return_utf8_sha256"], snapshot["content_sha256"], "Snapshot")
    _check_preservation(capture["preservation"], expected_world, started, ended, checked)
    effects = capture["state_effects"]
    _keys(effects, {"assets", "world", "input", "observers", "ref_cache"}, "state effects")
    for field in ("assets", "world", "input", "observers"):
        _require(type(effects[field]) is int and effects[field] == 0, "unexpected state effect: " + field)
    # Snapshot registers refs for rendered descendants too. R2 deliberately
    # rejects R1's unsupported exactly-one-ref claim; no cache count is inferred.
    _require(effects["ref_cache"] == "scoped_shared_ref_append_or_reuse", "unexpected ref-cache effect")

    packet = packets.build_execution_packet(
        approved_ref=binding["approved_ref"], max_depth=2, purpose="official_existing_details_capture",
        snapshot_return=text, snapshot_ref=request["Ref"], snapshot_max_depth=2,
        include_source_locations=True)
    receipt = {
        "kind": "official_slate_panel_capture_evidence", "version": 1, "scope": SCOPE,
        "capture_id": expected_capture_id, "request_id": expected_request_id,
        "editor": dict(editor), "call": dict(call), "binding": binding,
        "snapshot_sha256": snapshot["content_sha256"], "snapshot_utf8_bytes": snapshot["utf8_bytes"],
        "capture_evidence": "caller_attested_capture", "fresh_at_check": True,
        "checked_utc": checked.isoformat(), "current_receiver_rechecked": False,
        "preservation_checked": True, "execution_authorized": False,
        "native_runtime_qualified": False, "packet": packet,
        "binding_contract_sha256": BINDING_CONTRACT_SHA256,
        "capture_contract_sha256": CAPTURE_CONTRACT_SHA256,
    }
    consumed_capture_ids.update(replay_keys)
    return receipt
