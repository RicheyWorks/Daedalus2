# SPDX-License-Identifier: MIT
"""Durable private operation history; never dispatches, probes or replays work.

A reservation consumes a stable key even if its caller loses the reply. Only the
invocation creating and publishing a new intent can return a local dispatch
grant. That grant is one input to the future producer's normal guards, not live
authority or a guarantee of exactly-once effects.
"""
import base64
import binascii
import os
from pathlib import Path
import re

from . import contracts as c
from . import packet

STORE_SCHEMA = "daedalus.operation-journal-store.v1"
INTENT_SCHEMA = "daedalus.operation-journal-intent.v1"
RECORD_SCHEMA = "daedalus.operation-journal-record.v1"
COVERAGE_SCHEMA = "daedalus.operation-journal-coverage.v1"
EVENT_SCHEMA = "daedalus.operation-journal-event.v1"
HEAD_SCHEMA = "daedalus.operation-journal-head.v1"
RESERVATION_SCHEMA = "daedalus.operation-journal-reservation.v1"
MAX_RECEIPT_BYTES = 512 * 1024
MAX_EVENT_EVIDENCE_BYTES = 1024 * 1024
MAX_STORE_BYTES = 32 * 1024 * 1024
MAX_OPERATIONS = 128
MAX_EVENTS = 512
REFS = ("result_sha256", "save_sha256", "native_sha256", "ledger_sha256")
EVENT_NAME = re.compile(r"([0-9]{8})-([0-9a-f]{64})\.json\Z")


def _require(condition, code, message):
    if not condition:
        raise c.ContractError(code, message)


def _clone(value):
    return packet.decode(packet.canonical(value), "journal request")


def _same(left, right):
    return packet.canonical(left) == packet.canonical(right)


def _time(value):
    return c.timestamp_key(value)


def _strings(value, at):
    c._strings(value, at, nonempty=True)
    _require(len(value) <= 128, "journal_bounds", at + " exceeds 128 identities")
    _require(len({_logical(item) for item in value}) == len(value), "journal_identity_conflict", at + " contains normalized aliases")


def _descriptor(row, at):
    c._object(row, ("path", "logical_path", "sha256", "bytes"), at)
    packet.relative(row["path"])
    c._string(row["logical_path"], at + ".logical_path")
    c._hash(row["sha256"], at + ".sha256")
    c._integer(row["bytes"], at + ".bytes", 0, MAX_RECEIPT_BYTES)


def validate_config(value):
    c._object(value, ("schema", "identity", "window", "scope", "created_utc", "authority_ref"), "journal store")
    _require(value["schema"] == STORE_SCHEMA, "journal_version", "Unsupported journal store version")
    c._object(value["identity"], ("owner", "session", "host"), "store.identity")
    for name, text in value["identity"].items():
        c._string(text, "store.identity." + name)
    c._object(value["window"], ("start_utc", "deadline_utc"), "store.window")
    _require(_time(value["window"]["start_utc"]) < _time(value["window"]["deadline_utc"]),
             "journal_window", "Original journal window must be increasing")
    c._object(value["scope"], ("kind", "id"), "store.scope")
    _require(value["scope"]["kind"] == "declared-store-only", "journal_scope", "A private store cannot assert producer-wide scope")
    c._string(value["scope"]["id"], "store.scope.id")
    c._string(value["authority_ref"], "store.authority_ref")
    _require(_time(value["created_utc"]) <= _time(value["window"]["deadline_utc"]),
             "journal_window", "Store declaration follows its original deadline")


def validate_intent(value):
    c._object(value, ("schema", "operation_key", "operation_id", "session_id", "event_utc", "kind",
                      "expected_predecessor_sha256", "target_ids", "output_refs", "inputs"), "intent")
    _require(value["schema"] == INTENT_SCHEMA, "journal_version", "Unsupported intent version")
    for name in ("operation_key", "operation_id", "session_id", "kind"):
        c._string(value[name], "intent." + name)
    _time(value["event_utc"])
    c._hash(value["expected_predecessor_sha256"], "intent.expected_predecessor_sha256", nullable=True)
    _strings(value["target_ids"], "intent.target_ids")
    _strings(value["output_refs"], "intent.output_refs")
    _require(isinstance(value["inputs"], list) and 1 <= len(value["inputs"]) <= 16,
             "journal_bounds", "Intent requires 1..16 explicit input receipts")
    paths, logical = set(), set()
    for row in value["inputs"]:
        _descriptor(row, "intent input")
        _require(row["path"].casefold() not in paths and _logical(row["logical_path"]) not in logical,
                 "journal_input_alias", "Input paths/logical references must be distinct")
        paths.add(row["path"].casefold())
        logical.add(_logical(row["logical_path"]))


def validate_record(value):
    c._object(value, ("schema", "stage", "operation_key", "operation_id", "session_id", "event_utc", "intent_sha256",
                      "target_ids", "outcome", "references", "evidence", "reason"), "record")
    _require(value["schema"] == RECORD_SCHEMA, "journal_version", "Unsupported operation record version")
    c._enum(value["stage"], ("result", "save", "readback"), "record.stage")
    for name in ("operation_key", "operation_id", "session_id"):
        c._string(value[name], "record." + name)
    _time(value["event_utc"])
    c._hash(value["intent_sha256"], "record.intent_sha256")
    _strings(value["target_ids"], "record.target_ids")
    c._object(value["references"], REFS, "record.references")
    for name, digest in value["references"].items():
        c._hash(digest, "record.references." + name, nullable=True)
    c._object(value["evidence"], ("receipt", "native", "ledger"), "record.evidence")
    _descriptor(value["evidence"]["receipt"], "record receipt")
    for name in ("native", "ledger"):
        if value["evidence"][name] is not None:
            _descriptor(value["evidence"][name], name + " receipt")
    choices = {"result": ("success", "partial", "unknown", "failed_no_effect"),
               "save": ("saved", "partial", "unknown"), "readback": ("saved", "failed_no_effect", "unknown")}
    c._enum(value["outcome"], choices[value["stage"]], "record.outcome")
    if value["outcome"] in ("partial", "unknown"):
        c._string(value["reason"], "record.reason")
    else:
        _require(value["reason"] is None, "journal_record", "Known outcomes require a null uncertainty reason")
    refs, evidence = value["references"], value["evidence"]
    if value["stage"] == "result":
        _require(all(item is None for item in refs.values()) and evidence["native"] is None and evidence["ledger"] is None,
                 "journal_record", "A result cannot claim later save/native/ledger evidence")
    elif value["stage"] == "save":
        _require(refs["result_sha256"] is not None and refs["save_sha256"] is None,
                 "journal_record", "Save requires the original result reference and no self reference")
        _require((evidence["native"] is None) == (evidence["ledger"] is None), "journal_record", "Native and ledger witnesses must be supplied together")
        for name in ("native", "ledger"):
            pin = evidence[name]
            _require((pin is None and refs[name + "_sha256"] is None) or
                     (pin is not None and pin["sha256"] == refs[name + "_sha256"]),
                     "journal_record", "Save witness descriptor/reference differs: " + name)
        if value["outcome"] == "saved":
            _require(evidence["native"] is not None, "journal_record", "Saved requires retained native AND ledger bytes")
    else:
        _require(refs["result_sha256"] is not None and evidence["native"] is None and evidence["ledger"] is None,
                 "journal_record", "Readback references retained evidence rather than replacing it")


def validate_coverage(value):
    c._object(value, ("schema", "session_id", "event_utc", "through_utc", "authority_ref", "window", "scope_id",
                      "covers_head_sha256", "operation_keys", "producer_complete", "receipt"), "coverage")
    _require(value["schema"] == COVERAGE_SCHEMA, "journal_version", "Unsupported coverage attestation version")
    for name in ("session_id", "authority_ref", "scope_id"):
        c._string(value[name], "coverage." + name)
    _require(_time(value["through_utc"]) <= _time(value["event_utc"]), "journal_coverage", "Coverage cutoff cannot follow its original attestation event")
    c._object(value["window"], ("start_utc", "deadline_utc"), "coverage.window")
    _require(_time(value["window"]["start_utc"]) < _time(value["window"]["deadline_utc"]), "journal_coverage", "Coverage window must be increasing")
    c._hash(value["covers_head_sha256"], "coverage.covers_head_sha256", nullable=True)
    c._strings(value["operation_keys"], "coverage.operation_keys")
    c._boolean(value["producer_complete"], "coverage.producer_complete")
    _descriptor(value["receipt"], "coverage receipt")


def _logical(value):
    return value.replace("\\", "/").casefold()


def _intent_digest(spec):
    return packet.digest(packet.canonical(spec))


def _fingerprint(spec):
    return packet.digest(packet.canonical({
        "session_id": spec["session_id"], "kind": spec["kind"],
        "expected_predecessor_sha256": spec["expected_predecessor_sha256"],
        "target_ids": sorted(_logical(item) for item in spec["target_ids"]),
        "output_refs": sorted(_logical(item) for item in spec["output_refs"]),
        "inputs": sorted(({key: row[key] for key in ("logical_path", "sha256", "bytes")} for row in spec["inputs"]), key=lambda row: row["logical_path"])}))


def _descriptors(spec, stage):
    if stage == "intent":
        return {"input_%d" % i: row for i, row in enumerate(spec["inputs"])}
    if stage == "coverage":
        return {"receipt": spec["receipt"]}
    return {name: row for name, row in spec["evidence"].items() if row is not None}


def _proof(payload, stage):
    spec = payload["request"]
    raw = base64.b64decode(payload["blobs"][payload["receipts"]["receipt"]["sha256"]], validate=True)
    proof = packet.decode(raw, "retained " + stage + " proof")
    _require(isinstance(proof, dict), "journal_proof", "Retained proof must be a JSON object")
    if stage == "coverage":
        expected = {name: item for name, item in spec.items() if name not in ("schema", "receipt")}
        expected["schema"] = "daedalus.operation-journal-coverage-proof.v1"
    else:
        expected = {name: spec[name] for name in ("stage", "operation_id", "session_id", "event_utc", "intent_sha256", "target_ids", "outcome", "references", "reason")}
        expected["schema"] = "daedalus.operation-journal-proof.v1"
    _require(all(name in proof and _same(proof[name], item) for name, item in expected.items()),
             "journal_proof", "Retained proof contradicts its original operation/session/time/hash references")
    if stage == "save":
        _require(proof.get("saved") is True if spec["outcome"] == "saved" else (proof.get("saved") is None or proof.get("saved") is False),
                 "journal_proof", "Save proof cannot promote uncertain persistence to saved")
    elif stage == "readback":
        _require(proof.get("matches") is (spec["outcome"] != "unknown"), "journal_proof", "Readback matching fact differs from the recorded outcome")
    return proof


def _payload_check(payload, stage):
    c._object(payload, ("request", "receipts", "blobs"), "event payload")
    spec = payload["request"]
    {"intent": validate_intent, "coverage": validate_coverage}.get(stage, validate_record)(spec)
    if stage not in ("intent", "coverage"):
        _require(spec["stage"] == stage, "journal_event", "Envelope/record stage differs")
    descriptors = _descriptors(spec, stage)
    c._object(payload["receipts"], descriptors, "event receipt pins")
    _require(isinstance(payload["blobs"], dict), "journal_evidence", "Event blobs must be an object")
    expected_hashes = {row["sha256"] for row in descriptors.values()}
    _require(set(payload["blobs"]) == expected_hashes, "journal_evidence", "Receipt blob inventory differs")
    total = 0
    for label, row in descriptors.items():
        pin = {key: row[key] for key in ("logical_path", "sha256", "bytes")}
        _require(_same(payload["receipts"][label], pin), "journal_evidence", "Receipt pin differs: " + label)
    for digest, encoded in payload["blobs"].items():
        c._hash(digest, "event blob digest")
        _require(isinstance(encoded, str), "journal_evidence", "Receipt blob must be base64 text")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise c.ContractError("journal_evidence", "Malformed retained receipt bytes")
        _require(len(raw) <= MAX_RECEIPT_BYTES and packet.digest(raw) == digest,
                 "journal_evidence", "Retained receipt hash/size differs")
        _require(all(row["bytes"] == len(raw) for row in descriptors.values() if row["sha256"] == digest),
                 "journal_evidence", "Declared receipt byte size differs")
        total += len(raw)
    _require(total <= MAX_EVENT_EVIDENCE_BYTES, "journal_bounds", "Event evidence exceeds 1 MiB")
    if stage != "intent":
        _proof(payload, stage)
    if stage == "save" and spec["outcome"] == "saved":
        def doc(label):
            return packet.decode(base64.b64decode(payload["blobs"][payload["receipts"][label]["sha256"]]), label)
        native, ledger = doc("native"), doc("ledger")
        _require(isinstance(native, dict) and isinstance(ledger, dict), "journal_save", "Native/ledger witnesses must be retained JSON objects")
        native = native.get("native", native)
        _require(isinstance(native, dict) and native.get("saved") is True and native.get("dirty") == {"maps": [], "content": []}
                 and native.get("play") is False and native.get("import_active") is False and native.get("pending") is None,
                 "journal_save", "Native saved/clean/no-Play/no-import evidence is incomplete")
        _require(native.get("open_sequence") in (None, "None"), "journal_save", "Native receipt retains an open sequence")
        _require(isinstance(native.get("item_records"), dict) and set(native["item_records"]) == set(spec["target_ids"]),
                 "journal_save", "Native stable identities differ from the reserved operation")
        _require(isinstance(ledger.get("saved_counts"), dict) and ledger["saved_counts"], "journal_save", "Saved counts are missing")
        for key in ("saved_counts", "source_counts"):
            _require(isinstance(ledger.get(key), dict), "journal_save", "Ledger count evidence is missing")
            for kind, count in ledger[key].items():
                c._string(kind, "ledger count identity")
                c._integer(count, "ledger count")
        c._integer(ledger.get("next_index"), "ledger.next_index", 1)
        c._string(ledger.get("last_native_receipt"), "ledger.last_native_receipt")
        c._string(ledger.get("last_world"), "ledger.last_world")
        _require(native.get("world") == ledger["last_world"] + "." + ledger["last_world"].rsplit("/", 1)[-1],
                 "journal_save", "Native saved world differs from the retained ledger")
        _require(ledger["source_counts"] == ledger["saved_counts"] and
                 _logical(ledger.get("last_native_receipt", "")) == _logical(spec["evidence"]["native"]["logical_path"]),
                 "journal_save", "Ledger source/saved counts or native reference differs")


def _capture(root, source_root, spec, stage):
    source = packet._root(source_root)
    _require(source != root and source not in root.parents and root not in source.parents,
             "overlapping_store", "Receipt inputs and private journal store must be disjoint")
    descriptors = _descriptors(spec, stage)
    blobs, pins, total = {}, {}, 0
    for label, row in descriptors.items():
        raw = packet._read(packet._path(source, row["path"]), MAX_RECEIPT_BYTES)
        _require(len(raw) == row["bytes"] and packet.digest(raw) == row["sha256"], "journal_input_hash", "Explicit receipt bytes differ: " + label)
        if row["sha256"] not in blobs:
            total += len(raw)
            blobs[row["sha256"]] = base64.b64encode(raw).decode("ascii")
        pins[label] = {key: row[key] for key in ("logical_path", "sha256", "bytes")}
    _require(total <= MAX_EVENT_EVIDENCE_BYTES, "journal_bounds", "Event evidence exceeds 1 MiB")
    for label, row in descriptors.items():
        raw = packet._read(packet._path(source, row["path"]), MAX_RECEIPT_BYTES)
        _require(len(raw) == row["bytes"] and packet.digest(raw) == row["sha256"], "journal_input_changed", "Receipt changed during the complete capture rounds: " + label)
    payload = {"request": spec, "receipts": pins, "blobs": blobs}
    _payload_check(payload, stage)
    return payload


def _context(spec, config, stage):
    _require(spec["session_id"] == config["identity"]["session"], "journal_session", "Original session differs from the private store")
    _require(_time(spec["event_utc"]) >= _time(config["created_utc"]), "journal_order", "Event predates the original store declaration")
    if stage == "intent":
        _require(_time(config["window"]["start_utc"]) <= _time(spec["event_utc"]) < _time(config["window"]["deadline_utc"]),
                 "journal_window", "Intent is outside the original admission window; it cannot reset that window")


def _alias_check(spec, reservations):
    targets = {_logical(item) for item in spec["target_ids"]}
    outputs = {_logical(item) for item in spec["output_refs"]}
    for key, reservation in reservations.items():
        prior = reservation["intent"]
        if key == spec["operation_key"]:
            continue
        _require(prior["operation_id"] != spec["operation_id"] and reservation["logical_sha256"] != _fingerprint(spec)
                 and not targets.intersection(_logical(item) for item in prior["target_ids"])
                 and not outputs.intersection(_logical(item) for item in prior["output_refs"]),
                 "journal_identity_conflict", "Operation/effect/target/output aliases an existing reserved key: " + key)


def _event_check(value, digest, sequence, config_sha):
    c._integer(sequence, "event filename sequence", 1, MAX_EVENTS)
    c._object(value, ("schema", "sequence", "prior_sha256", "config_sha256", "stage", "operation_key", "event_utc", "payload"), "journal event")
    _require(value["schema"] == EVENT_SCHEMA and type(value["sequence"]) is int and value["sequence"] == sequence,
             "journal_event", "Event version/sequence differs from its immutable filename")
    _require(value["config_sha256"] == config_sha, "journal_config", "Event binds another original store configuration")
    c._hash(value["prior_sha256"], "event.prior_sha256", nullable=True)
    _require((sequence == 1) == (value["prior_sha256"] is None), "journal_chain", "Event predecessor is absent at the wrong sequence")
    c._enum(value["stage"], ("intent", "result", "save", "readback", "coverage"), "event.stage")
    _time(value["event_utc"])
    _payload_check(value["payload"], value["stage"])
    spec = value["payload"]["request"]
    _require(value["event_utc"] == spec["event_utc"] and
             value["operation_key"] == (None if value["stage"] == "coverage" else spec["operation_key"]),
             "journal_event", "Event identity/time differs from its original payload")
    return dict(value, sha256=digest)


def _transition(operations, event, config, reservations):
    stage, payload = event["stage"], event["payload"]
    spec = payload["request"]
    _context(spec, config, stage)
    if stage == "coverage":
        _require(spec["covers_head_sha256"] == event["prior_sha256"], "journal_coverage", "Coverage does not bind the exact preceding journal head")
        _require(spec["authority_ref"] == config["authority_ref"] and spec["scope_id"] == config["scope"]["id"],
                 "journal_coverage", "Declared coverage authority/scope differs")
        _require(all(_time(spec["window"][key]) == _time(config["window"][key]) for key in ("start_utc", "deadline_utc")),
                 "journal_coverage", "Coverage cannot change the original window")
        _require(set(spec["operation_keys"]) == set(operations) and len(spec["operation_keys"]) == len(operations),
                 "journal_coverage", "Coverage operation inventory differs from this head")
        latest = max((_time(row[stage]["event_utc"]) for row in operations.values() for stage in ("intent_event", "result", "save", "readback") if row.get(stage)), default=_time(config["created_utc"]))
        _require(_time(spec["through_utc"]) >= latest, "journal_coverage", "Coverage cutoff predates retained operation evidence")
        if spec["producer_complete"]:
            _require(bool(operations) and all(_operation_summary(row)["reconciled"] for row in operations.values()),
                     "journal_coverage", "Pending/unknown/partial outcomes cannot be declared complete")
        return
    key = spec["operation_key"]
    if stage == "intent":
        _require(key not in operations, "journal_duplicate_intent", "A stable key cannot have a second intent event")
        _require(key in reservations and _same(reservations[key]["intent"], spec), "journal_reservation", "Intent has no exact durable reservation")
        _alias_check(spec, {name: row for name, row in reservations.items() if name in operations})
        operations[key] = {"request": spec, "intent_sha256": _intent_digest(spec), "intent_event": event,
                           "result": None, "save": None, "readback": None}
        return
    _require(key in operations, "journal_order", "Result/save/readback requires its committed intent")
    row = operations[key]
    _require(row[stage] is None, "journal_stage_conflict", "An immutable operation stage is already recorded")
    _require(spec["operation_id"] == row["request"]["operation_id"] and spec["intent_sha256"] == row["intent_sha256"]
             and set(spec["target_ids"]) == set(row["request"]["target_ids"]),
             "journal_identity", "Operation ID/intent/target identity differs from its reservation")
    if stage == "result":
        _require(row["save"] is None and row["readback"] is None, "journal_order", "Result follows a later operation stage")
    else:
        _require(row["result"] is not None, "journal_order", "Save/readback cannot precede an actual result receipt")
        result = row["result"]
        result_sha = result["payload"]["receipts"]["receipt"]["sha256"]
        _require(spec["references"]["result_sha256"] == result_sha, "journal_reference", "Stage does not bind the original result bytes")
        if stage == "save":
            _require(result["payload"]["request"]["outcome"] == "success" and row["readback"] is None,
                     "journal_order", "Unknown/partial/no-effect result cannot be promoted to saved")
            if spec["outcome"] == "saved":
                ledger = packet.decode(base64.b64decode(payload["blobs"][payload["receipts"]["ledger"]["sha256"]]), "ledger")
                _require(_logical(ledger["last_world"]) in {_logical(item) for item in row["request"]["output_refs"]},
                         "journal_identity", "Saved world is outside the reserved logical outputs")
        else:
            save = row["save"]
            refs = {"result_sha256": result_sha, "save_sha256": None, "native_sha256": None, "ledger_sha256": None}
            if save:
                refs.update(save_sha256=save["payload"]["receipts"]["receipt"]["sha256"],
                            native_sha256=save["payload"]["request"]["references"]["native_sha256"],
                            ledger_sha256=save["payload"]["request"]["references"]["ledger_sha256"])
            _require(_same(spec["references"], refs), "journal_reference", "Readback does not bind all original result/save/native/ledger witnesses")
            if spec["outcome"] == "saved":
                _require(save is not None and save["payload"]["request"]["outcome"] == "saved"
                         and result["payload"]["request"]["outcome"] == "success",
                         "journal_order", "Saved readback requires separate successful result and saved evidence")
            if spec["outcome"] == "failed_no_effect":
                _require(save is None and result["payload"]["request"]["outcome"] == "failed_no_effect",
                         "journal_order", "No-effect reconciliation requires the explicit matching result and no save")
    row[stage] = event


def _apply(events, config, reservations):
    operations, coverage = {}, None
    previous_time = _time(config["created_utc"])
    previous_hash = None
    for sequence, event in enumerate(events, 1):
        _require(event["sequence"] == sequence and event["prior_sha256"] == previous_hash,
                 "journal_chain", "Selected event chain has a gap or wrong predecessor")
        _require(_time(event["event_utc"]) >= previous_time, "journal_order", "Immutable event time moves backwards")
        _transition(operations, event, config, reservations)
        if event["stage"] == "coverage":
            coverage = event
        previous_time, previous_hash = _time(event["event_utc"]), event["sha256"]
    return operations, coverage


def _operation_summary(row):
    intent_event = row.get("intent_event")
    stages = {}
    for name in ("result", "save", "readback"):
        event = row.get(name)
        if event:
            stages[name] = dict(event_sha256=event["sha256"], event_utc=event["event_utc"],
                                outcome=event["payload"]["request"]["outcome"],
                                receipt_sha256=event["payload"]["receipts"]["receipt"]["sha256"],
                                references=event["payload"]["request"]["references"])
    outcome, reconciled, stamp = "pending", False, row["request"]["event_utc"]
    if "result" in stages:
        outcome = stages["result"]["outcome"]
        outcome = "unknown" if outcome == "success" else outcome
        stamp = stages["result"]["event_utc"]
    if "save" in stages:
        outcome = "partial" if stages["save"]["outcome"] == "partial" else "unknown"
        stamp = stages["save"]["event_utc"]
    if "readback" in stages:
        outcome = stages["readback"]["outcome"]
        reconciled = outcome in ("saved", "failed_no_effect")
        stamp = stages["save"]["event_utc"] if outcome == "saved" else stages["readback"]["event_utc"]
    if intent_event is None:
        outcome = "unknown"
    return dict(operation_id=row["request"]["operation_id"], intent_sha256=row["intent_sha256"],
                intent_event_sha256=intent_event["sha256"] if intent_event else None,
                outcome=outcome, reconciled=reconciled, event_utc=stamp,
                target_ids=row["request"]["target_ids"], stages=stages)


def _load(root):
    config_raw = packet._read(root / "store.json")
    config = packet.decode(config_raw, "journal store")
    validate_config(config)
    config_sha = packet.digest(config_raw)
    head = packet.read_json(root / "current.json")
    c._object(head, ("schema", "config_sha256", "sequence", "event_sha256"), "journal head")
    _require(head["schema"] == HEAD_SCHEMA and head["config_sha256"] == config_sha, "journal_head", "Head version/original store binding differs")
    c._integer(head["sequence"], "head.sequence", 0, MAX_EVENTS)
    c._hash(head["event_sha256"], "head.event_sha256", nullable=True)
    _require((head["sequence"] == 0) == (head["event_sha256"] is None), "journal_head", "Head sequence/hash absence differs")
    issues, warnings, total, entries = [], [], 0, 0
    # The store grammar is flat. Do not recursively inventory unknown trees or
    # let zero-byte partial files evade the byte bound and exhaust inspection.
    for directory in (root, root / "events", root / "reservations"):
        packet._plain(directory)
        for path in directory.iterdir():
            entries += 1
            _require(entries <= MAX_EVENTS * 2 + MAX_OPERATIONS + 16, "journal_bounds", "Private journal entry count exceeds its inspection bound")
            packet._plain(path)
            if path.is_file():
                total += path.stat().st_size
    _require(total <= MAX_STORE_BYTES, "journal_bounds", "Private journal exceeds its 32 MiB inspection bound")
    for path in root.iterdir():
        if path.name in ("store.json", "current.json", ".publish.lock", "events", "reservations"):
            continue
        if path.is_file() and path.name.startswith("current.json.") and path.name.endswith(".tmp"):
            warnings.append("Retained interrupted pointer temporary: " + path.name)
        else:
            issues.append({"code": "journal_inventory", "message": "Unexpected retained store entry: " + path.name})
    reservations = {}
    reservation_paths = list((root / "reservations").iterdir())
    _require(len(reservation_paths) <= MAX_OPERATIONS, "journal_bounds", "Reservation entry capacity exceeded, including partial originals")
    for path in reservation_paths:
        try:
            _require(path.is_file() and re.fullmatch(r"[0-9a-f]{64}\.json", path.name), "journal_reservation", "Unsupported reservation entry: " + path.name)
            value = packet.read_json(path)
            c._object(value, ("schema", "intent", "intent_sha256", "logical_sha256"), "reservation")
            _require(value["schema"] == RESERVATION_SCHEMA, "journal_version", "Unsupported reservation version")
            validate_intent(value["intent"])
            key = value["intent"]["operation_key"]
            _context(value["intent"], config, "intent")
            _require(path.stem == packet.digest(key.encode("utf-8")) and value["intent_sha256"] == _intent_digest(value["intent"])
                     and value["logical_sha256"] == _fingerprint(value["intent"]), "journal_reservation", "Reservation key/original intent/effect binding differs")
            _alias_check(value["intent"], reservations)
            reservations[key] = value
        except (c.ContractError, OSError) as exc:
            issues.append({"code": getattr(exc, "code", "journal_io"), "message": "Reservation " + path.name + ": " + str(exc)})
    _require(len(reservations) <= MAX_OPERATIONS, "journal_bounds", "Private store exceeds 128 operation reservations")
    events = {}
    event_paths = list((root / "events").iterdir())
    _require(len(event_paths) <= MAX_EVENTS, "journal_bounds", "Private store exceeds 512 immutable events")
    for path in event_paths:
        try:
            match = EVENT_NAME.fullmatch(path.name)
            _require(path.is_file() and match is not None, "journal_event", "Unsupported event entry: " + path.name)
            raw = packet._read(path)
            digest = match.group(2)
            _require(packet.digest(raw) == digest, "journal_event_hash", "Immutable event bytes/hash differ")
            value = packet.decode(raw, "journal event")
            events[digest] = _event_check(value, digest, int(match.group(1)), config_sha)
        except (c.ContractError, OSError) as exc:
            issues.append({"code": getattr(exc, "code", "journal_io"), "message": "Event " + path.name + ": " + str(exc)})
    selected, cursor = [], head["event_sha256"]
    while cursor is not None:
        _require(cursor in events and len(selected) <= MAX_EVENTS, "journal_chain", "Selected chain has missing/corrupt event evidence")
        event = events[cursor]
        _require(cursor not in {row["sha256"] for row in selected}, "journal_chain", "Selected event chain cycles")
        selected.append(event)
        cursor = event["prior_sha256"]
    selected.reverse()
    _require(len(selected) == head["sequence"], "journal_chain", "Selected head count differs from retained chain")
    operations, coverage = _apply(selected, config, reservations)
    selected_hashes = {row["sha256"] for row in selected}
    orphans = {digest: event for digest, event in events.items() if digest not in selected_hashes}
    for digest in orphans:
        issues.append({"code": "journal_orphan_event", "message": "Unpublished event retained: " + digest})
    for key in set(reservations) - set(operations):
        issues.append({"code": "journal_orphan_reservation", "message": "Reserved key has no selected intent; never grant again: " + key})
    return dict(root=root, config=config, config_sha256=config_sha, head=head, reservations=reservations,
                events=events, selected=selected, operations=operations, coverage=coverage, orphans=orphans,
                issues=issues, warnings=warnings, total_bytes=total)


def _public(state):
    rows = {key: _operation_summary(value) for key, value in state["operations"].items()}
    for key in set(state["reservations"]) - set(rows):
        reservation = state["reservations"][key]
        rows[key] = _operation_summary({"request": reservation["intent"], "intent_sha256": reservation["intent_sha256"]})
    held = bool(state["issues"]) or any(not row["reconciled"] for row in rows.values())
    return dict(schema="daedalus.operation-journal-inspection.v1", status="held" if held else "consistent",
                config=state["config"], config_sha256=state["config_sha256"], head_sha256=state["head"]["event_sha256"],
                sequence=state["head"]["sequence"], operations=rows, issues=state["issues"], warnings=state["warnings"],
                orphans=list(state["orphans"]), orphan_events=[{key: event[key] for key in ("sha256", "stage", "operation_key", "event_utc")} for event in state["orphans"].values()],
                dispatch_granted=False, may_execute=False, scope=state["config"]["scope"])


def inspect(store):
    """Read private history, including held/orphan outcomes, without any grant."""
    root = packet._root(store)
    try:
        return _public(_load(root))
    except (c.ContractError, OSError) as exc:
        return dict(schema="daedalus.operation-journal-inspection.v1", status="held", config=None, config_sha256=None,
                    head_sha256=None, sequence=None, operations={}, orphans=[], warnings=[],
                    issues=[{"code": getattr(exc, "code", "journal_io"), "message": str(exc)}], dispatch_granted=False, may_execute=False)


def _inject(fault, stage):
    if fault:
        fault(stage)


def create(store, config, fault=None):
    """Create an explicitly fresh private store; never reset an existing one."""
    config = _clone(config)
    validate_config(config)
    root = Path(os.path.abspath(store))
    packet._root(root.parent)
    packet._plain(root)
    try:
        root.mkdir()
    except FileExistsError:
        raise c.ContractError("journal_store_exists", "Existing journal cannot be reset; inspect its retained history")
    (root / "events").mkdir()
    (root / "reservations").mkdir()
    raw = packet.canonical(config)
    packet._write_new(root / "store.json", raw)
    _inject(fault, "after_store")
    packet._replace_json(root / "current.json", dict(schema=HEAD_SCHEMA, config_sha256=packet.digest(raw), sequence=0, event_sha256=None),
                         lambda: _inject(fault, "before_pointer_replace"))
    _inject(fault, "after_pointer")
    return inspect(root)


def _usable(state):
    _require(not state["issues"], "journal_held", "Journal has retained incomplete/conflicting evidence: " + ", ".join(sorted({row["code"] for row in state["issues"]})))


def _append(state, stage, payload, fault):
    sequence = state["head"]["sequence"] + 1
    _require(sequence <= MAX_EVENTS, "journal_bounds", "Journal event capacity reached; preserve this store")
    event = dict(schema=EVENT_SCHEMA, sequence=sequence, prior_sha256=state["head"]["event_sha256"],
                 config_sha256=state["config_sha256"], stage=stage,
                 operation_key=None if stage == "coverage" else payload["request"]["operation_key"],
                 event_utc=payload["request"]["event_utc"], payload=payload)
    raw = packet.canonical(event)
    _require(len(raw) <= packet.MAX_JSON_BYTES and state["total_bytes"] + len(raw) <= MAX_STORE_BYTES,
             "journal_bounds", "Journal transaction/store byte capacity exceeded")
    digest = packet.digest(raw)
    checked = _event_check(event, digest, sequence, state["config_sha256"])
    _apply(state["selected"] + [checked], state["config"], state["reservations"])
    path = state["root"] / "events" / ("%08d-%s.json" % (sequence, digest))
    packet._write_new(path, raw)
    packet._sync_dir(path.parent)
    _inject(fault, "after_event")
    packet._replace_json(state["root"] / "current.json", dict(schema=HEAD_SCHEMA, config_sha256=state["config_sha256"], sequence=sequence, event_sha256=digest),
                         lambda: _inject(fault, "before_pointer_replace"))
    _inject(fault, "after_pointer")
    return checked


def _answer(state, event, recorded, dispatch=False):
    return dict(schema="daedalus.operation-journal-write.v1", recorded=recorded, dispatch_granted=dispatch,
                may_execute=False, live_integration_required=True, scope=state["config"]["scope"],
                operation_key=event["operation_key"], intent_sha256=(_intent_digest(event["payload"]["request"])
                    if event["stage"] == "intent" else event["payload"]["request"].get("intent_sha256")),
                event_sha256=event["sha256"], head_sha256=state["head"]["event_sha256"])


def intent(store, spec, evidence_root, fault=None):
    """Persist intent before the caller may consider dispatch under normal guards.

    Only this synchronous first successful invocation returns a local grant.
    Inspect/retry/recovery never reproduce it, even after a lost response.
    """
    spec = _clone(spec)
    validate_intent(spec)
    root = packet._root(store)
    with packet._writer(root):
        state = _load(root)
        _usable(state)
        _context(spec, state["config"], "intent")
        key = spec["operation_key"]
        if key in state["reservations"]:
            _require(_same(state["reservations"][key]["intent"], spec), "journal_intent_conflict", "Stable key already binds different original intent fields/timestamp")
            return _answer(state, state["operations"][key]["intent_event"], False)
        _require(len(state["reservations"]) < MAX_OPERATIONS, "journal_bounds", "Operation reservation capacity reached")
        _alias_check(spec, state["reservations"])
        _inject(fault, "before_reservation")
        reservation = dict(schema=RESERVATION_SCHEMA, intent=spec, intent_sha256=_intent_digest(spec), logical_sha256=_fingerprint(spec))
        reservation_path = root / "reservations" / (packet.digest(key.encode("utf-8")) + ".json")
        packet._write_new(reservation_path, packet.canonical(reservation))
        packet._sync_dir(reservation_path.parent)
        _inject(fault, "after_reservation")
        state["reservations"][key] = reservation
        state["total_bytes"] += reservation_path.stat().st_size
        payload = _capture(root, evidence_root, spec, "intent")
        _inject(fault, "after_inputs")
        event = _append(state, "intent", payload, fault)
        return _answer(_load(root), event, True, True)


def record(store, spec, evidence_root, fault=None):
    """Retain an actual supplied result/save/readback proof; dispatch nothing."""
    spec = _clone(spec)
    validate_record(spec)
    root = packet._root(store)
    with packet._writer(root):
        state = _load(root)
        _usable(state)
        _context(spec, state["config"], spec["stage"])
        key, stage = spec["operation_key"], spec["stage"]
        _require(key in state["operations"], "journal_order", "Original committed intent is missing")
        old = state["operations"][key].get(stage)
        if old:
            _require(_same(old["payload"]["request"], spec), "journal_stage_conflict", "Immutable stage already binds different evidence/timestamp")
            return _answer(state, old, False)
        payload = _capture(root, evidence_root, spec, stage)
        _inject(fault, "after_inputs")
        event = _append(state, stage, payload, fault)
        return _answer(_load(root), event, True)


def cover(store, spec, evidence_root, fault=None):
    """Record an explicit coverage attestation, never infer one from scanning."""
    spec = _clone(spec)
    validate_coverage(spec)
    root = packet._root(store)
    with packet._writer(root):
        state = _load(root)
        _usable(state)
        for old in state["selected"]:
            if old["stage"] == "coverage" and _same(old["payload"]["request"], spec):
                return _answer(state, old, False)
        payload = _capture(root, evidence_root, spec, "coverage")
        _inject(fault, "after_inputs")
        event = _append(state, "coverage", payload, fault)
        return _answer(_load(root), event, True)


def recover(store, fault=None):
    """Select complete unambiguous orphan history, without recreating any grant.

    Missing/partial reservations/events/proofs stay held. No bytes are removed,
    repaired, reconstructed or declared effect-free to obtain forward progress.
    """
    root = packet._root(store)
    with packet._writer(root):
        try:
            state = _load(root)
            if any(row["code"] not in ("journal_orphan_event", "journal_orphan_reservation") for row in state["issues"]):
                return dict(_public(state), adopted_events=0)
            remaining = dict(state["orphans"])
            selected = list(state["selected"])
            cursor, sequence = state["head"]["event_sha256"], state["head"]["sequence"]
            while remaining:
                candidates = [row for row in remaining.values() if row["prior_sha256"] == cursor and row["sequence"] == sequence + 1]
                _require(len(candidates) == 1, "journal_recovery_ambiguous", "Missing/forked orphan history cannot be selected safely")
                event = candidates[0]
                selected.append(event)
                _apply(selected, state["config"], state["reservations"])
                cursor, sequence = event["sha256"], event["sequence"]
                del remaining[cursor]
            adopted = sequence - state["head"]["sequence"]
            if adopted:
                packet._replace_json(root / "current.json", dict(schema=HEAD_SCHEMA, config_sha256=state["config_sha256"], sequence=sequence, event_sha256=cursor),
                                     lambda: _inject(fault, "before_pointer_replace"))
                _inject(fault, "after_pointer")
            return dict(_public(_load(root)), adopted_events=adopted)
        except (c.ContractError, OSError) as exc:
            summary = inspect(root)
            summary["issues"].append({"code": getattr(exc, "code", "journal_io"), "message": str(exc)})
            return dict(summary, status="held", adopted_events=0)


def inventory(store, through_utc):
    """Export the existing inventory wire shape with explicit coverage limits.

    Saved-row intent/result fields are compatibility boundary witnesses L/N,
    not the genuine pre-dispatch intent I or original response R. Those original
    records remain independently hash-bound in the retained immutable chain.
    """
    cutoff = _time(through_utc)
    root = packet._root(store)
    with packet._writer(root):
        state = _load(root)
        summary = _public(state)
        reasons = list(summary["issues"])
        rows = []
        for key, op in summary["operations"].items():
            result_sha = None
            digest = op["intent_sha256"]
            if op["reconciled"] and op["outcome"] == "saved":
                refs = op["stages"]["save"]["references"]
                digest, result_sha = refs["ledger_sha256"], refs["native_sha256"]
            elif op["reconciled"] and op["outcome"] == "failed_no_effect":
                result_sha = op["stages"]["result"]["receipt_sha256"]
            elif op["stages"]:
                stage = next(name for name in ("readback", "save", "result") if name in op["stages"])
                result_sha = op["stages"][stage]["receipt_sha256"]
            rows.append(dict(id=op["operation_id"], intent_sha256=digest, target_ids=op["target_ids"],
                             outcome=op["outcome"], result_sha256=result_sha, reconciled=op["reconciled"], event_utc=op["event_utc"]))
            if not op["reconciled"]:
                reasons.append({"code": "OPERATION_UNRECONCILED", "message": "Retained operation requires reconciliation without replay: " + key})
        c._operations([{name: item for name, item in row.items() if name != "event_utc"} for row in rows], "exported operations")
        operation_events = [row for row in state["selected"] if row["stage"] != "coverage"]
        if cutoff < _time(state["config"]["created_utc"]) or any(_time(row["event_utc"]) > cutoff for row in operation_events):
            reasons.append({"code": "JOURNAL_CUTOFF", "message": "Cutoff excludes retained later operation evidence"})
        coverage = state["coverage"]
        scope = dict(kind="declared-store-only", id=state["config"]["scope"]["id"], verification="producer-coverage-not-established",
                     config_sha256=state["config_sha256"], head_sha256=state["head"]["event_sha256"],
                     genuine_intent_digest="canonical intent retained in reservation/event chain", legacy_saved_fields="final ledger/native boundary witnesses")
        if (coverage is None or coverage["sha256"] != state["head"]["event_sha256"]
                or not coverage["payload"]["request"]["producer_complete"]
                or cutoff > _time(coverage["payload"]["request"]["through_utc"])):
            reasons.append({"code": "PRODUCER_COVERAGE_UNKNOWN", "message": "A private-store scan cannot establish producer-wide completeness at this cutoff"})
        else:
            scope.update(kind="producer-session-declared", verification="caller-attestation-only", coverage_event_sha256=coverage["sha256"],
                         coverage_receipt_sha256=coverage["payload"]["receipts"]["receipt"]["sha256"], authority_ref=coverage["payload"]["request"]["authority_ref"])
        return dict(schema="daedalus.source-operation-journal.v1", session_id=state["config"]["identity"]["session"],
                    complete=not bool(reasons), through_utc=through_utc, operations=rows, scope=scope,
                    window=state["config"]["window"], head_sha256=state["head"]["event_sha256"],
                    status="held" if reasons else "declared_complete", reasons=reasons, dispatch_granted=False, may_execute=False)
