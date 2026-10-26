# SPDX-License-Identifier: MIT
"""Explicit offline receipt copies -> existing sealed packets; no live providers.

The R22 profile reads exported copies only. Original path references are data,
never discovery instructions. Observation time never becomes a saved event or
process-start time. Supplemental receipts form a separately pinned capture
manifest; consumers must verify the composite with read_snapshot().
"""
import os
from pathlib import Path

from . import contracts as c
from . import packet

SCHEMA = "daedalus.source-snapshot-request.v1"
PROFILE = "legacy-r22-saved-boundary.v1"
CAPTURE_SCHEMA = "daedalus.source-snapshot-capture.v1"
RESULT_SCHEMA = "daedalus.source-snapshot-result.v1"
ROLES = ("session", "launch", "config", "owner", "terminal", "ledger", "monitor",
         "native", "catalog", "journal", "source", "build")
PACKET_ROLES = {"checkpoint": "monitor", "owner": "owner", "ledger": "ledger",
                "native": "native", "catalog": "catalog", "source": "source", "build": "build"}
ESSENTIAL = set(ROLES) - {"source", "build"}


def validate_request(value):
    c._object(value, ("schema", "profile", "campaign", "captured_utc", "max_source_age_seconds",
                      "identity", "session_ref", "runtime", "source_state", "inputs"), "source snapshot")
    if value["schema"] != SCHEMA or value["profile"] != PROFILE:
        raise c.ContractError("UNSUPPORTED_SOURCE_PROFILE", "Explicit source snapshot v1/R22 saved-boundary profile required")
    for key in ("campaign", "session_ref"):
        c._string(value[key], key)
    c.timestamp_key(value["captured_utc"])
    c._integer(value["max_source_age_seconds"], "max_source_age_seconds", 1, 3600)
    c._object(value["identity"], ("owner", "session", "host"), "identity")
    for key, text in value["identity"].items():
        c._string(text, "identity." + key)
    c._object(value["runtime"], ("name", "version", "artifact_sha256", "generation"), "runtime")
    for key in ("name", "version", "generation"):
        c._string(value["runtime"][key], "runtime." + key)
    c._hash(value["runtime"]["artifact_sha256"], "runtime.artifact_sha256")
    c._object(value["source_state"], ("dirty", "exceptions"), "source_state")
    if value["source_state"]["dirty"] is not None:
        c._boolean(value["source_state"]["dirty"], "source_state.dirty")
    c._strings(value["source_state"]["exceptions"], "source_state.exceptions")
    c._object(value["inputs"], ROLES, "inputs")
    paths = set()
    for role, row in value["inputs"].items():
        c._object(row, ("status", "path", "logical_path", "sha256", "bytes", "reason"), "inputs." + role)
        c._enum(row["status"], ("present", "unknown"), "inputs." + role + ".status")
        if row["status"] == "present":
            name = packet.relative(row["path"])
            if name.casefold() in paths:
                raise c.ContractError("duplicate_path", "Input roles must reference distinct portable paths")
            paths.add(name.casefold())
            c._string(row["logical_path"], "inputs." + role + ".logical_path")
            c._hash(row["sha256"], "inputs." + role + ".sha256")
            c._integer(row["bytes"], "inputs." + role + ".bytes", 0, packet.MAX_EVIDENCE_BYTES)
            if row["reason"] is not None:
                raise c.ContractError("INVALID_FIELD", "Present inputs require a null absence reason")
        else:
            if any(row[key] is not None for key in ("path", "logical_path", "sha256", "bytes")):
                raise c.ContractError("INVALID_FIELD", "Unknown inputs require null path/reference/pins")
            c._string(row["reason"], "inputs." + role + ".reason")


def _require(condition, code, message):
    if not condition:
        raise c.ContractError(code, message)


def _elapsed(later, earlier):
    return c._seconds(c.timestamp_key(later), c.timestamp_key(earlier))


def _same_time(left, right):
    return c.timestamp_key(left) == c.timestamp_key(right)


def _reference(value):
    c._string(value, "retained logical reference")
    return value.replace("\\", "/")


def _interpret(request, documents, pins):
    """Map supported retained facts. Never read a source path or consult a clock."""
    session, launch, config, owner, terminal, ledger, monitor, native, journal = (
        documents[name] for name in ("session", "launch", "config", "owner", "terminal", "ledger", "monitor", "native", "journal"))
    for name, doc in documents.items():
        if name != "catalog":
            _require(isinstance(doc, dict), "SOURCE_FORMAT", name + " must be a retained JSON object")
    _require(session.get("schema") == "daedalus-r22-session/1" and config.get("schema") == "daedalus-r22-resume/1",
             "SOURCE_FORMAT", "Unsupported retained session/config profile")
    identity = request["identity"]
    _require(session.get("owner") == config.get("lease_owner") == owner.get("lease_owner") == identity["owner"],
             "SOURCE_MISMATCH", "Session/config/owner actual owner differs")
    _require(session.get("session_id") == identity["session"] == _reference(request["session_ref"]).rstrip("/").rsplit("/", 1)[-1],
             "SOURCE_MISMATCH", "Session ID differs from the explicit original session reference")
    _require(_reference(owner.get("r22_session")) == _reference(terminal.get("r22_session")) == _reference(request["session_ref"]),
             "SOURCE_MISMATCH", "Owner/terminal original session references differ")
    c._integer(launch.get("pid"), "launch.pid", 1)
    for label, value in (("owner.pid", owner.get("pid")), ("terminal.pid", terminal.get("pid")),
                         ("monitor.owner_pid", monitor.get("owner_pid"))):
        c._integer(value, label, 1)
    _require(launch["pid"] == owner.get("pid") == terminal.get("pid") == monitor.get("owner_pid"),
             "SOURCE_MISMATCH", "Producer PID differs across retained receipts")
    c.timestamp_key(launch.get("start"))  # Only this launch field supplies producer generation.
    for key in ("owner", "session", "host"):
        if key in owner:
            _require(owner[key] == identity[key], "SOURCE_MISMATCH", "Retained owner " + key + " differs")
    if "start_utc" in owner:
        _require(_same_time(owner["start_utc"], launch["start"]), "SOURCE_MISMATCH", "Retained producer generation differs")
    editor = session.get("editor_receipt")
    _require(isinstance(editor, dict), "SOURCE_FORMAT", "Retained editor generation receipt is required")
    if "schema" in editor:
        _require(editor["schema"] == "daedalus-r22-editor-generation/1", "SOURCE_FORMAT", "Unsupported embedded editor generation format")
    if "editor_receipt_sha256" in session:
        c._hash(session["editor_receipt_sha256"], "session.editor_receipt_sha256")
    c._integer(editor.get("pid"), "editor_receipt.pid", 1)
    c.timestamp_key(editor.get("start_utc"))
    c._integer(config.get("expected_editor_pid"), "config.expected_editor_pid", 1)
    c._integer(owner.get("sole_editor"), "owner.sole_editor", 1)
    if "editor_pid" in monitor:
        c._integer(monitor["editor_pid"], "monitor.editor_pid", 1)
        _require(monitor["editor_pid"] == editor["pid"], "SOURCE_MISMATCH", "Monitor editor PID differs")
    if "configured_owner" in editor:
        _require(editor["configured_owner"] == identity["owner"], "SOURCE_MISMATCH", "Embedded editor receipt actual owner differs")
    _require(editor["pid"] == config.get("expected_editor_pid") == owner.get("sole_editor")
             and _same_time(editor["start_utc"], owner.get("editor_start_utc")),
             "SOURCE_MISMATCH", "Editor PID/start differs across session/config/owner")
    _require(request["runtime"]["generation"] == "editor:%d@%s" % (editor["pid"], editor["start_utc"]),
             "SOURCE_MISMATCH", "Declared runtime generation differs from the retained editor receipt")
    started, deadline = session.get("started_utc"), session.get("deadline_utc")
    _require(_elapsed(deadline, started) > 0 and _elapsed(started, launch["start"]) >= 0,
             "INVALID_WINDOW", "Original nonnull session window must follow its launch generation")
    _require(_elapsed(started, editor["start_utc"]) >= 0, "SOURCE_MISMATCH", "Editor generation starts after the session")
    if "window_hours" in config:
        c._integer(config["window_hours"], "config.window_hours", 1)
        _require(_elapsed(deadline, started) == config["window_hours"] * 3600,
                 "INVALID_WINDOW", "Retained session duration differs from its configured original window")
    for key in ("initial_checkpoint", "speed_profile"):
        if key in config and key in session:
            _require(packet.canonical(config[key]) == packet.canonical(session[key]),
                     "SOURCE_MISMATCH", "Retained session/config " + key + " differs")
    if "editor_launch_receipt" in owner:
        _require(_reference(owner["editor_launch_receipt"]) == _reference(request["session_ref"]).rstrip("/") + "/editor-launch.json",
                 "SOURCE_MISMATCH", "Owner editor launch reference differs from its session")
    status = terminal.get("status")
    _require(isinstance(status, dict) and status.get("stage") == "paused_saved_boundary",
             "PENDING_WORK", "Only the retained terminal paused saved-boundary profile is supported")
    active = monitor.get("active")
    _require(isinstance(active, dict) and active.get("stage") in ("chunk_saved", "paused_saved_boundary"),
             "PENDING_WORK", "Monitor does not retain a supported saved stage")
    for label, state in (("terminal", status), ("monitor", active)):
        _require(state.get("pending") is None, "PENDING_WORK", label + " retains pending effects")
        if "r22_session" in state:
            _require(_reference(state["r22_session"]) == _reference(request["session_ref"]),
                     "SOURCE_MISMATCH", label + " nested session reference differs")
        if "campaign_deadline_utc" in state:
            _require(_same_time(state["campaign_deadline_utc"], deadline), "INVALID_WINDOW", label + " deadline differs from the original session")
    counts, next_index = ledger.get("saved_counts"), ledger.get("next_index")
    _require(isinstance(counts, dict) and counts, "SOURCE_FORMAT", "Ledger saved counts are required")
    for kind, count in counts.items():
        c._string(kind, "saved count kind")
        c._integer(count, "saved count")
    c._integer(next_index, "ledger.next_index", 1)
    for label, state in (("ledger", ledger), ("terminal", status), ("monitor", monitor), ("monitor active", active)):
        for key in ("saved_counts", "source_counts"):
            if key not in state and key == "source_counts":
                continue
            _require(isinstance(state.get(key), dict), "SOURCE_FORMAT", label + " " + key + " must be integer counts")
            for kind, count in state[key].items():
                c._string(kind, label + " count kind")
                c._integer(count, label + " " + key + "." + kind)
        c._integer(state.get("next_index"), label + ".next_index", 1)
        if "owner_pid" in state:
            c._integer(state["owner_pid"], label + ".owner_pid", 1)
            _require(state["owner_pid"] == launch["pid"], "SOURCE_MISMATCH", label + " nested owner PID differs")
        _require(state.get("saved_counts") == counts and state.get("next_index") == next_index,
                 "SOURCE_MISMATCH", label + " saved counts/next index differ")
        if "source_counts" in state:
            _require(state["source_counts"] == counts, "PENDING_WORK", label + " has source work ahead of the saved boundary")
    _require(_reference(ledger.get("last_native_receipt")) == _reference(request["inputs"]["native"]["logical_path"]),
             "SOURCE_MISMATCH", "Ledger native reference differs from the explicit allowlisted receipt")
    if "last_native_receipt" in monitor:
        _require(_reference(monitor["last_native_receipt"]) == _reference(ledger["last_native_receipt"]),
                 "SOURCE_MISMATCH", "Monitor native receipt reference differs")
    native = native.get("native", native)
    _require(isinstance(native, dict) and native.get("saved") is True
             and native.get("dirty") == {"maps": [], "content": []}
             and native.get("play") is False and native.get("import_active") is False
             and native.get("pending") is None, "PENDING_WORK", "Native saved/clean/no-Play/no-import facts are not established")
    if "open_sequence" in native:
        _require(native["open_sequence"] in (None, "None"), "PENDING_WORK", "Native receipt retains an open sequence")
    world = ledger.get("last_world")
    c._string(world, "ledger.last_world")
    _require(native.get("world") == world + "." + world.rsplit("/", 1)[-1], "SOURCE_MISMATCH", "Native world differs from ledger")
    targets = native.get("item_records")
    _require(isinstance(targets, dict) and targets, "SOURCE_FORMAT", "Native stable item identities are required")
    for target in targets:
        c._string(target, "native stable item identity")
    terminal_utc, monitor_utc = terminal.get("utc"), monitor.get("utc")
    _require(_elapsed(terminal_utc, started) >= 0 and _elapsed(monitor_utc, terminal_utc) >= 0,
             "SOURCE_MISMATCH", "Original session/terminal/monitor event order differs")
    if "utc" in owner:
        _require(_same_time(owner["utc"], started), "SOURCE_MISMATCH", "Retained R22 owner assignment time differs from session start")
    for label, timestamp in (("terminal", terminal_utc), ("monitor", monitor_utc)):
        age = _elapsed(request["captured_utc"], timestamp)
        _require(0 <= age <= request["max_source_age_seconds"], "STALE_SOURCE", label + " event is future-dated or outside the explicit source-age limit")
    _require(journal.get("schema") == "daedalus.source-operation-journal.v1"
             and journal.get("session_id") == identity["session"] and journal.get("complete") is True,
             "JOURNAL_UNKNOWN", "Explicit complete same-session journal inventory is required")
    through = journal.get("through_utc")
    _require(_elapsed(through, monitor_utc) >= 0 and _elapsed(request["captured_utc"], through) >= 0,
             "JOURNAL_UNKNOWN", "Journal inventory must cover the monitor event without a future cutoff")
    operations = journal.get("operations")
    _require(isinstance(operations, list) and operations, "JOURNAL_UNKNOWN", "Retained saved-operation journal is required")
    normalized = []
    for op in operations:
        c._object(op, ("id", "intent_sha256", "target_ids", "outcome", "result_sha256", "reconciled", "event_utc"), "source journal operation")
        c.timestamp_key(op["event_utc"])
        stripped = {key: value for key, value in op.items() if key != "event_utc"}
        normalized.append(stripped)
        _require(_elapsed(op["event_utc"], terminal_utc) <= 0, "LATER_OPERATION", "Journal retains an operation after the terminal boundary; reconcile it before capture")
        _require(op["outcome"] in ("saved", "failed_no_effect") and op["reconciled"] is True,
                 "PENDING_WORK", "Unresolved/partial/unknown journal effects require reconciliation, never replay")
    c._operations(normalized, "source journal operations")
    matches = [op for op in operations if op["outcome"] == "saved" and op["result_sha256"] == pins["native"]["sha256"]]
    _require(len(matches) == 1, "SOURCE_MISMATCH", "Exactly one saved result must bind the current native receipt")
    last = matches[0]
    _require(last["intent_sha256"] == pins["ledger"]["sha256"], "SOURCE_MISMATCH", "Saved operation intent does not bind the retained ledger")
    _require(set(last["target_ids"]) == set(targets), "SOURCE_MISMATCH", "Journal targets differ from retained native stable identities")
    _require(all(_elapsed(last["event_utc"], op["event_utc"]) >= 0 for op in operations), "LATER_OPERATION", "A journal operation follows the verified save")
    _require(_elapsed(last["event_utc"], started) >= 0, "SOURCE_MISMATCH", "Saved operation precedes the original session")
    _require(0 <= _elapsed(request["captured_utc"], last["event_utc"]) <= request["max_source_age_seconds"],
             "STALE_SOURCE", "Verified saved event is outside the explicit source-age limit")
    source_input, build_input = request["inputs"]["source"], request["inputs"]["build"]
    source = dict(status="unknown", commit=None, manifest_sha256=None, dirty=request["source_state"]["dirty"],
                  exceptions=request["source_state"]["exceptions"], reason=source_input["reason"] or "Original dirty/input completeness state was not recorded")
    if source_input["status"] == "present" and request["source_state"]["dirty"] is not None:
        source = dict(status="recorded", commit=documents["source"].get("commit"), manifest_sha256=pins["source"]["sha256"],
                      dirty=request["source_state"]["dirty"], exceptions=request["source_state"]["exceptions"], reason=None)
    build = dict(status="unknown", source_manifest_sha256=None, artifact_sha256=None, receipt_sha256=None,
                 reason=build_input["reason"] or "No complete retained build-time source/artifact binding was established")
    if (build_input["status"] == "present" and source["status"] == "recorded"
            and documents["build"].get("recorded_at_build_time") is True):
        build = dict(status="bound", source_manifest_sha256=source["manifest_sha256"],
                     artifact_sha256=documents["build"].get("artifact_sha256"), receipt_sha256=pins["build"]["sha256"], reason=None)
    evidence = {}
    for role, original in PACKET_ROLES.items():
        row = request["inputs"][original]
        evidence[role] = (dict(status="present", path=original + ".json", reason=None) if row["status"] == "present"
                          else dict(status="unknown", path=None, reason=row["reason"]))
    checkpoint = dict(schema=c.CHECKPOINT_SCHEMA, campaign=request["campaign"], sequence=1, prior_sha256=None,
                      saved_utc=last["event_utc"], phase="saved",
                      owner=dict(identity, pid=launch["pid"], start_utc=launch["start"]),
                      runtime=dict(request["runtime"], config_sha256=pins["config"]["sha256"]),
                      window=dict(start_utc=started, deadline_utc=deadline),
                      progress=dict(counts=counts, next_index=next_index, last_operation_id=last["id"]),
                      source=source, build=build, evidence=evidence,
                      operations=[{key: value for key, value in last.items() if key != "event_utc"}])
    c.validate_checkpoint(checkpoint)
    holds = [{"code": "LIVENESS_NOT_OBSERVED", "message": "Source copies do not establish current producer death, custody or live admission"}]
    if source["status"] == "unknown":
        holds.append({"code": "SOURCE_PROVENANCE_UNKNOWN", "message": source["reason"]})
    if build["status"] == "unknown":
        holds.append({"code": "BUILD_PROVENANCE_UNKNOWN", "message": build["reason"]})
    if source["dirty"] or source["exceptions"]:
        holds.append({"code": "SOURCE_EXCEPTIONS", "message": "Dirty inputs/exceptions require a separately reviewed transition"})
    if _elapsed(deadline, request["captured_utc"]) <= 0:
        holds.append({"code": "WINDOW_CLOSED", "message": "The original session window expired; capture does not reset it"})
    return checkpoint, holds


def _issue(code, message):
    return {"code": code, "message": message}


def capture(request, source_root, store, fault=None):
    """Capture an explicit immutable export into a fresh store, or retain a HOLD.

    Complete byte-hash rounds bracket all copies and final validation. They detect observable
    changes, not arbitrary ABA races or later live effects. The caller must use
    quiescent exported copies; this function never fences a production writer.
    """
    request = packet.decode(packet.canonical(request), "source snapshot request")
    validate_request(request)
    source = packet._root(source_root)
    target = Path(os.path.abspath(store))
    packet._root(target.parent)
    _require(not (source == target or source in target.parents or target in source.parents),
             "overlapping_store", "Source exports and fresh output store must be disjoint")
    packet._plain(target)
    try:
        target.mkdir()
    except FileExistsError:
        raise c.ContractError("snapshot_store_exists", "Capture requires a fresh store; inspect any prior outcome without overwriting it")
    audit = target / "source-snapshot"
    audit.mkdir()
    copies = audit / "copies"
    copies.mkdir()
    request_raw = packet.canonical(request)
    packet._write_new(audit / "request.json", request_raw)
    observations, pins, issues = {}, {}, []
    total = 0
    for role in ROLES:
        row = request["inputs"][role]
        observation = dict(path=None, before=None, after=None, copy=None)
        observations[role] = observation
        if row["status"] == "unknown":
            if role in ESSENTIAL:
                issues.append(_issue("JOURNAL_UNKNOWN" if role == "journal" else "INPUT_MISSING", role + ": " + row["reason"]))
            continue
        try:
            raw = packet._read(packet._path(source, row["path"]), packet.MAX_EVIDENCE_BYTES)
            total += len(raw)
            _require(total <= packet.MAX_TOTAL_BYTES, "evidence_size", "Source export copies exceed 64 MiB")
            pin = {"sha256": packet.digest(raw), "bytes": len(raw)}
            observation.update(path="copies/" + role + ".json", before=pin, copy=pin)
            packet._write_new(copies / (role + ".json"), raw)
            pins[role] = pin
            if any(pin[key] != row[key] for key in ("sha256", "bytes")):
                issues.append(_issue("INPUT_CHANGED", role + " differs from its explicit request pin"))
        except (OSError, c.ContractError) as exc:
            issues.append(_issue(getattr(exc, "code", "INPUT_MISSING"), role + ": " + str(exc)))
    if fault:
        fault("after_copy")
    # This is a second complete round, after ALL source copies, not per-file
    # before/after checks which could miss a mixed cross-file generation.
    def recheck_sources():
        for role in ROLES:
            row = request["inputs"][role]
            if row["status"] == "unknown":
                continue
            try:
                raw = packet._read(packet._path(source, row["path"]), packet.MAX_EVIDENCE_BYTES)
                pin = {"sha256": packet.digest(raw), "bytes": len(raw)}
                observations[role]["after"] = pin
                if pin != observations[role]["before"]:
                    issues.append(_issue("INPUT_CHANGED", role + " changed across the complete capture rounds"))
            except (OSError, c.ContractError) as exc:
                issues.append(_issue(getattr(exc, "code", "INPUT_MISSING"), role + " recheck: " + str(exc)))
    recheck_sources()
    checkpoint, admission_holds = None, []
    if not issues:
        try:
            documents = {role: packet.read_json(copies / (role + ".json")) for role in pins if role != "catalog"}
            checkpoint, admission_holds = _interpret(request, documents, pins)
        except (c.ContractError, KeyError, TypeError) as exc:
            issues.append(_issue(getattr(exc, "code", "SOURCE_FORMAT"), "Retained source set: " + str(exc)))
    if fault:
        fault("after_validation")
    recheck_sources()
    manifest = dict(schema=CAPTURE_SCHEMA, captured_utc=request["captured_utc"], request_sha256=packet.digest(request_raw),
                    copies=observations, checkpoint_sha256=packet.digest(packet.canonical(checkpoint)) if checkpoint else None)
    manifest_raw = packet.canonical(manifest)
    packet._write_new(audit / "capture.json", manifest_raw)
    packet_hash = None
    if not issues:
        try:
            sealed = packet.seal(target / "packet", checkpoint, copies)
            packet_hash = sealed["sha256"]
        except c.ContractError as exc:
            if (target / "packet/current.json").exists():
                raise c.ContractError("snapshot_publication_uncertain", "Packet may be published; inspect retained evidence before any further action")
            issues.append(_issue(exc.code, "Sealed-packet validation: " + str(exc)))
    if fault:
        fault("after_seal")
    result = dict(schema=RESULT_SCHEMA, status="held" if issues else "sealed", admission_status="held", may_execute=False,
                  liveness="not_observed", captured_utc=request["captured_utc"], source_boundary_verified=not bool(issues),
                  source_event_utc=checkpoint["saved_utc"] if checkpoint else None, packet_sha256=packet_hash,
                  capture_sha256=packet.digest(manifest_raw), request_sha256=packet.digest(request_raw),
                  reasons=issues if issues else admission_holds)
    if fault:
        fault("before_result")
    packet._write_new(audit / "result.json", packet.canonical(result))
    return read_snapshot(target)


def read_snapshot(store, expected_sha256=None):
    """Verify the composite capture receipt, supplemental bytes and sealed packet.

    Pin the returned receipt_sha256 AND packet_sha256 through the trusted handoff
    route. A current packet without this completed receipt is an incomplete
    adapter outcome and must not be treated as a source snapshot success.
    """
    root = packet._root(store)
    audit = packet._path(root, "source-snapshot")
    try:
        result_raw = packet._read(audit / "result.json")
    except FileNotFoundError:
        raise c.ContractError("snapshot_incomplete", "Completed capture receipt is absent; inspect partial files/current packet without replaying or overwriting")
    result_hash = packet.digest(result_raw)
    if expected_sha256 is not None:
        c._hash(expected_sha256, "expected capture receipt hash")
        _require(result_hash == expected_sha256, "snapshot_receipt_hash", "Capture result differs from the advertised receipt digest")
    result = packet.decode(result_raw, "source snapshot result")
    c._object(result, ("schema", "status", "admission_status", "may_execute", "liveness", "captured_utc",
                       "source_boundary_verified", "source_event_utc", "packet_sha256", "capture_sha256", "request_sha256", "reasons"), "snapshot result")
    _require(result["schema"] == RESULT_SCHEMA and result["status"] in ("held", "sealed")
             and result["admission_status"] == "held" and result["may_execute"] is False
             and result["liveness"] == "not_observed", "snapshot_result", "Unsupported or unsafe source snapshot result")
    manifest_raw = packet._read(audit / "capture.json")
    request_raw = packet._read(audit / "request.json")
    _require(packet.digest(manifest_raw) == result["capture_sha256"] and packet.digest(request_raw) == result["request_sha256"],
             "snapshot_evidence_hash", "Capture manifest/request bytes differ")
    request, manifest = packet.decode(request_raw), packet.decode(manifest_raw)
    validate_request(request)
    c._object(manifest, ("schema", "captured_utc", "request_sha256", "copies", "checkpoint_sha256"), "capture manifest")
    _require(manifest["schema"] == CAPTURE_SCHEMA and manifest["request_sha256"] == result["request_sha256"]
             and manifest["captured_utc"] == request["captured_utc"] == result["captured_utc"],
             "snapshot_manifest", "Capture manifest identity differs")
    c._object(manifest["copies"], ROLES, "capture copies")
    pins, documents, stable = {}, {}, True
    expected_files = {"request.json", "capture.json", "result.json"}
    for role, observation in manifest["copies"].items():
        c._object(observation, ("path", "before", "after", "copy"), "capture copy " + role)
        if observation["path"] is None:
            stable = stable and request["inputs"][role]["status"] == "unknown"
            continue
        _require(observation["path"] == "copies/" + role + ".json", "snapshot_path", "Unexpected capture copy path")
        expected_files.add(observation["path"])
        raw = packet._read(packet._path(audit, observation["path"]), packet.MAX_EVIDENCE_BYTES)
        pin = {"sha256": packet.digest(raw), "bytes": len(raw)}
        _require(pin == observation["copy"] == observation["before"], "snapshot_copy_hash", "Captured original bytes differ: " + role)
        pins[role] = pin
        stable = stable and pin == observation["after"] and all(pin[key] == request["inputs"][role][key] for key in pin)
        if role != "catalog":
            try:
                documents[role] = packet.decode(raw, role)
            except c.ContractError:
                if result["status"] == "sealed":
                    raise
    actual_files = set()
    for path in audit.rglob("*"):
        packet._plain(path)
        if path.is_file():
            actual_files.add(path.relative_to(audit).as_posix())
    _require(actual_files == expected_files, "snapshot_inventory", "Capture has missing or unexpected files")
    if result["status"] == "sealed":
        _require(stable and ESSENTIAL <= set(pins), "snapshot_unstable", "Sealed capture lacks stable essential source copies")
        checkpoint, holds = _interpret(request, documents, pins)
        sealed = packet.read_packet(root / "packet")
        _require(sealed["sha256"] == result["packet_sha256"]
                 and packet.digest(packet.canonical(checkpoint)) == manifest["checkpoint_sha256"]
                 and sealed["checkpoint"] == checkpoint and result["reasons"] == holds
                 and result["source_event_utc"] == checkpoint["saved_utc"] and result["source_boundary_verified"] is True,
                 "snapshot_binding", "Capture/retained source facts/sealed checkpoint binding differs")
        for role, original in PACKET_ROLES.items():
            if request["inputs"][original]["status"] == "present":
                _require(sealed["files"][original + ".json"] == pins[original], "snapshot_binding", "Packet source evidence differs: " + role)
    else:
        _require(result["packet_sha256"] is None and result["source_boundary_verified"] is False
                 and isinstance(result["reasons"], list) and bool(result["reasons"])
                 and not (root / "packet/current.json").exists(), "snapshot_result", "Held source capture cannot advertise a packet or live boundary")
    return dict(result, receipt_sha256=result_hash)
