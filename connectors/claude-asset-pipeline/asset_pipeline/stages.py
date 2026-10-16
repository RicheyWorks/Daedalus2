# SPDX-License-Identifier: MIT
"""Offline, immutable stage receipts and conservative recovery advice.

No bridge, subprocess, HTTP, lease or editor APIs. Publication creates a fresh
receipt; verification and legacy adaptation only read explicitly supplied files.
The existing native batch journal remains its operator's reconciliation surface.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SCHEMA = "daedalus.stage-evidence.v1"
MAX_JSON = 1 << 20
MAX_FILE = 64 << 20
MAX_TOTAL = 256 << 20
MAX_PINS = 256
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, required, optional=()):
    need(isinstance(value, dict), "expected object")
    need(set(required) <= value.keys() <= set(required) | set(optional),
         "missing or unknown fields: " + repr(sorted(value)))


def text(value, label, maximum=1024):
    need(isinstance(value, str) and 0 < len(value) <= maximum
         and "\x00" not in value, "invalid " + label)
    return value


def ident(value):
    need(isinstance(value, str) and ID.fullmatch(value), "invalid explicit identity")
    return value


def stamp(value):
    text(value, "UTC timestamp", 40)
    need(value.endswith(("Z", "+00:00")), "timestamp must be explicit UTC")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(parsed.utcoffset().total_seconds() == 0, "timestamp must be UTC")
    return parsed


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    with open(path, "rb") as source:
        raw = source.read(MAX_JSON + 1)
    need(len(raw) <= MAX_JSON, "JSON exceeds 1 MiB")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("nonfinite JSON number: " + value)))


def pin_shape(value):
    keys(value, ("path", "bytes", "sha256"))
    text(value["path"], "pin path", 4096)
    need(type(value["bytes"]) is int and 0 <= value["bytes"] <= MAX_FILE,
         "pin size must be 0..64 MiB")
    need(isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]),
         "pin requires lowercase SHA256")


def fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as source:
        while True:
            chunk = source.read(min(1 << 20, MAX_FILE + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            need(size <= MAX_FILE, "file exceeds 64 MiB")
            digest.update(chunk)
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def resolve(pin, root):
    return Path(root) / pin["path"]


class Reader:
    def __init__(self, root):
        self.root, self.count, self.size = Path(root), 0, 0

    def verify(self, pin):
        pin_shape(pin)
        self.count += 1
        self.size += pin["bytes"]
        need(self.count <= MAX_PINS and self.size <= MAX_TOTAL,
             "receipt pin work budget exceeded")
        actual = fingerprint(resolve(pin, self.root))
        need((actual["bytes"], actual["sha256"]) == (pin["bytes"], pin["sha256"]),
             "changed pin: " + pin["path"])
        return actual


def typed_identity(value):
    keys(value, ("type", "value"))
    need(value["type"] in ("string", "integer"), "identity type must be explicit")
    if value["type"] == "string":
        text(value["value"], "identity", 128)
    else:
        need(type(value["value"]) is int and 0 <= value["value"] < 2**63,
             "identity must be a nonnegative signed64 integer")


def validate(document):
    """Strict structural validation; no file existence or process inference."""
    need(len(json.dumps(document, allow_nan=False).encode("utf-8")) <= MAX_JSON,
         "receipt exceeds 1 MiB")
    keys(document, ("schema", "job_id", "observed_at_utc", "identities", "stages"),
         ("previous", "provenance"))
    need(document["schema"] == SCHEMA, "unsupported stage evidence schema")
    ident(document["job_id"])
    observed = stamp(document["observed_at_utc"])
    keys(document["identities"], (), ("realmAuthoringKey", "runtimeWorldId", "catalogueId"))
    for value in document["identities"].values():
        typed_identity(value)
    if "previous" in document:
        pin_shape(document["previous"])
    if "provenance" in document:
        text(document["provenance"], "provenance", 2048)
    stages = document["stages"]
    need(isinstance(stages, list) and 1 <= len(stages) <= 32, "require 1..32 stages")
    seen = set()
    for stage in stages:
        keys(stage, ("stage_id", "requires", "effect", "required_outputs", "attempts"))
        name = ident(stage["stage_id"])
        need(name not in seen, "duplicate stage")
        deps = stage["requires"]
        need(isinstance(deps, list) and len(deps) <= 32 and len(set(deps)) == len(deps)
             and all(isinstance(d, str) and d in seen for d in deps),
             "dependencies must reference distinct earlier stages")
        seen.add(name)
        need(stage["effect"] in ("local-files", "external"), "invalid stage effect")
        roles = stage["required_outputs"]
        need(isinstance(roles, list) and 1 <= len(roles) <= 32, "require output roles")
        need(len(set(roles)) == len(roles), "duplicate required output")
        for role in roles:
            ident(role)
        attempts = stage["attempts"]
        need(isinstance(attempts, list) and len(attempts) <= 16, "attempt limit exceeded")
        attempt_ids = set()
        previous_time = None
        for attempt in attempts:
            keys(attempt, ("attempt_id", "inputs", "events"))
            aid = ident(attempt["attempt_id"])
            need(aid not in attempt_ids, "duplicate attempt")
            attempt_ids.add(aid)
            inputs = attempt["inputs"]
            need(isinstance(inputs, dict) and len(inputs) <= 32, "invalid input pins")
            for role, pin in inputs.items():
                ident(role)
                pin_shape(pin)
            events = attempt["events"]
            need(isinstance(events, list) and 1 <= len(events) <= 3, "require 1..3 events")
            states = [e.get("state") for e in events if isinstance(e, dict)]
            need(states in (["accepted"], ["accepted", "running"],
                            ["accepted", "terminal"], ["accepted", "running", "terminal"]),
                 "invalid lifecycle order")
            for event in events:
                if event["state"] != "terminal":
                    keys(event, ("state", "observed_at_utc"))
                else:
                    keys(event, ("state", "observed_at_utc", "outcome", "effects", "outputs"),
                         ("process", "compute_release", "progress", "materials", "gui_operation"))
                    need(event["outcome"] in ("succeeded", "failed", "unknown"), "invalid outcome")
                    need(event["effects"] in ("none", "complete", "partial", "unknown"), "invalid effects")
                    need(isinstance(event["outputs"], dict) and len(event["outputs"]) <= 32,
                         "invalid outputs")
                    for role, pin in event["outputs"].items():
                        ident(role)
                        pin_shape(pin)
                    if "gui_operation" in event:
                        gui = event["gui_operation"]
                        keys(gui, ("operation_id", "allocation_id", "evidence", "output_fields"), ("baseline",))
                        need(ident(gui["operation_id"]) == aid, "GUI operation/attempt identity mismatch")
                        need(type(gui["allocation_id"]) is int and gui["allocation_id"] > 0,
                             "invalid GUI allocation identity")
                        pin_shape(gui["evidence"])
                        need(isinstance(gui["output_fields"], dict)
                             and set(gui["output_fields"]) == set(roles), "GUI output role contract differs")
                        for selector in gui["output_fields"].values():
                            text(selector, "GUI output selector", 256)
                        if "baseline" in gui:
                            pin_shape(gui["baseline"])
                        need("process" not in event, "GUI completion cannot supply a process exit")
                        if "compute_release" in event:
                            need(isinstance(event["compute_release"], dict)
                                 and event["compute_release"].get("proof_kind") == "gui-release-v1",
                                 "GUI release requires its operation-bound proof kind")
                    for kind in ("process", "compute_release", "progress"):
                        if kind in event:
                            item = event[kind]
                            field = {"process": "exit_code", "compute_release": "released",
                                     "progress": "state"}[kind]
                            optional = ("field",) if kind == "progress" else ("proof_kind", "owner") if kind == "compute_release" else ()
                            keys(item, (field, "evidence"), optional)
                            need("owner" not in item or item.get("proof_kind") == "gui-release-v1",
                                 "unexpected release owner")
                            if "proof_kind" in item:
                                need(item["proof_kind"] in ("nursery-release-v1", "gui-release-v1"), "unknown release proof kind")
                                if item["proof_kind"] == "gui-release-v1":
                                    need("gui_operation" in event, "GUI release requires GUI operation evidence")
                                    text(item.get("owner"), "explicit release owner", 128)
                                else:
                                    need("owner" not in item, "unexpected release owner")
                            if "field" in item:
                                text(item["field"], "progress field", 128)
                            pin_shape(item["evidence"])
                            if kind == "process":
                                need(item[field] is None or type(item[field]) is int, "invalid exit code")
                            elif kind == "compute_release":
                                need(item[field] is None or type(item[field]) is bool, "invalid release")
                            else:
                                text(item[field], "progress state", 128)
                    if "materials" in event:
                        item = event["materials"]
                        keys(item, ("used", "retained", "validated_unused", "evidence"))
                        pin_shape(item["evidence"])
                        for field in ("used", "retained", "validated_unused"):
                            need(isinstance(item[field], list) and len(item[field]) <= 128
                                 and all(isinstance(n, str) and 0 < len(n) <= 128 for n in item[field])
                                 and len(set(item[field])) == len(item[field]), "invalid material list")
                tick = stamp(event["observed_at_utc"])
                need(tick <= observed and (previous_time is None or previous_time <= tick),
                     "contradictory observation order")
                previous_time = tick
    return document


def extension(previous, current):
    """Append events/attempts/stages only; earlier evidence cannot be rewritten."""
    need(previous["job_id"] == current["job_id"] and previous["identities"] == current["identities"],
         "job/realm identities changed")
    need(stamp(previous["observed_at_utc"]) <= stamp(current["observed_at_utc"]), "snapshot time reversed")
    need("provenance" not in previous or previous["provenance"] == current.get("provenance"),
         "prior provenance changed")
    need(len(previous["stages"]) <= len(current["stages"]), "prior stages removed")
    for old, new in zip(previous["stages"], current["stages"]):
        for key in ("stage_id", "requires", "effect", "required_outputs"):
            need(old[key] == new[key], "prior stage contract changed")
        need(len(old["attempts"]) <= len(new["attempts"]), "prior attempts removed")
        for a, b in zip(old["attempts"], new["attempts"]):
            need(a["attempt_id"] == b["attempt_id"] and a["inputs"] == b["inputs"],
                 "prior attempt/inputs changed")
            need(a["events"] == b["events"][:len(a["events"])], "prior events changed")


def inspect(document, root=".", now=None, stale_after=300):
    validate(document)
    now = stamp(now) if now else datetime.now(timezone.utc)
    need(type(stale_after) is int and 0 < stale_after <= 86400, "invalid stale interval")
    need(now >= stamp(document["observed_at_utc"]), "observation is in the future")
    reader = Reader(root)
    if "previous" in document:
        reader.verify(document["previous"])
        previous = validate(read_json(resolve(document["previous"], root)))
        extension(previous, document)
    rows, completed = [], set()
    for stage in document["stages"]:
        row = {"stage_id": stage["stage_id"], "status": "missing", "verified_outputs": {},
               "advice": "prepare-only-after-explicit-owner-acceptance", "issues": []}
        blocked = [dep for dep in stage["requires"] if dep not in completed]
        row["blocked_by"] = blocked
        unsafe_history = False
        history = []
        attempt_fields = ("attempt_id", "observed_state", "status", "verified_outputs", "issues",
                          "advice", "process", "compute_release", "progress", "stale_running", "gui_operation")
        for attempt in stage["attempts"]:
            if "attempt_id" in row:
                history.append({key: copy.deepcopy(row[key]) for key in attempt_fields if key in row})
            for key in attempt_fields:
                row.pop(key, None)
            row.update(status="missing", verified_outputs={}, issues=[],
                       advice="prepare-only-after-explicit-owner-acceptance")
            for pin in attempt["inputs"].values():
                reader.verify(pin)
            event = attempt["events"][-1]
            row.update(attempt_id=attempt["attempt_id"], observed_state=event["state"])
            if event["state"] != "terminal":
                age = (now - stamp(event["observed_at_utc"])).total_seconds()
                row["status"] = "stale-running" if event["state"] == "running" and age > stale_after else event["state"]
                row["stale_running"] = row["status"] == "stale-running"
                row["advice"] = "observe-existing-attempt-do-not-replay"
                if event["state"] == "running":
                    unsafe_history = True
                continue
            verified = {}
            for role, pin in event["outputs"].items():
                reader.verify(pin)
                verified[role] = copy.deepcopy(pin)
            row["verified_outputs"] = verified
            row["status"] = event["outcome"]
            row["advice"] = "inspect-failure-and-retained-outputs"
            exit_code = None
            gui_result = None
            if "gui_operation" in event:
                gui_result = inspect_gui(event["gui_operation"], event["outputs"], reader,
                                         attempt["attempt_id"], document["observed_at_utc"])
                row["gui_operation"] = gui_result
                row["issues"].extend(gui_result["issues"])
                need(event["outcome"] == gui_result["declared_outcome"], "GUI source outcome differs")
                expected_effects = {"succeeded": "complete", "failed": "partial", "unknown": "unknown"}
                need(event["effects"] == expected_effects[event["outcome"]], "GUI source effects differ")
            for kind, field in (("process", "exit_code"), ("compute_release", "released"), ("progress", "state")):
                if kind in event:
                    value = event[kind]
                    reader.verify(value["evidence"])
                    proof = read_json(resolve(value["evidence"], root))
                    proof_field = value.get("field", field)
                    if kind == "compute_release" and value.get("proof_kind") == "gui-release-v1":
                        released = gui_released(proof, event["gui_operation"]["allocation_id"],
                                                value["owner"], gui_result["finished_at_utc"],
                                                document["observed_at_utc"])
                        need(value[field] is (True if released else None), "contradictory GUI release evidence")
                    elif kind == "compute_release" and "proof_kind" in value:
                        need(value[field] is True and nursery_released(proof), "contradictory Nursery release evidence")
                    else:
                        need(isinstance(proof, dict) and proof_field in proof
                             and type(proof[proof_field]) is type(value[field])
                             and proof[proof_field] == value[field], "contradictory " + kind + " evidence")
                    row[kind] = value[field]
                    if kind == "process":
                        exit_code = value[field]
                    if kind == "progress" and (value[field].upper().endswith("_RENDERING")
                                                or value[field].lower() in ("running", "rendering")):
                        row["issues"].append("nonterminal progress retained after terminal process evidence")
            if "materials" in event:
                mat = event["materials"]
                reader.verify(mat["evidence"])
                proof = read_json(resolve(mat["evidence"], root))
                need(proof == {k: mat[k] for k in ("used", "retained", "validated_unused")},
                     "material usage proof mismatch")
                need(set(mat["used"]) <= set(mat["retained"]), "missing USED material")
                need(not set(mat["validated_unused"]) & set(mat["used"]), "used material marked unused")
            if event["outcome"] == "succeeded":
                if gui_result is None:
                    need("process" in event and exit_code == 0, "success lacks retained actual exit0 evidence")
                    need(set(stage["required_outputs"]) <= verified.keys()
                         and all(verified[r]["bytes"] > 0 for r in stage["required_outputs"]),
                         "success lacks required nonempty pinned outputs")
                elif not gui_result["operation_completed"] or row.get("compute_release") is not True:
                    unsafe_history = True
                    if row.get("compute_release") is not True:
                        row["issues"].append("GUI compute release is not separately verified")
                need(event["effects"] in ("none", "complete"), "success contradicts uncertain effects")
            elif event["outcome"] == "failed":
                if gui_result is None:
                    need("process" in event and exit_code is not None and exit_code != 0,
                         "failed outcome lacks actual nonzero exit evidence")
            if event["effects"] in ("partial", "unknown") or event["outcome"] == "unknown":
                unsafe_history = True
            if event["outcome"] == "succeeded":
                row["advice"] = "retain-pinned-output-no-replay"
        if unsafe_history or (stage["effect"] == "external" and stage["attempts"]):
            row.update(status="reconciliation-required", advice="operator-reconciliation-only-no-replay")
        elif row["status"] == "succeeded" and not blocked:
            completed.add(stage["stage_id"])
        if blocked:
            row["advice"] = "upstream-incomplete-no-dispatch"
        row["previous_attempts"] = history
        rows.append(row)
    return {"schema": "daedalus.stage-report.v1", "job_id": document["job_id"],
            "identities": copy.deepcopy(document["identities"]), "stages": rows,
            "complete": len(completed) == len(rows), "native_qualified": False,
            "execution": False, "pins_checked": reader.count,
            "scope": "Retained source evidence at observation time; advice only. No native or visual acceptance."}


def publish(document, path, root=".", now=None):
    """Flush complete bytes, exclusively link, read back; never replace a receipt."""
    inspect(document, root, now)
    raw = (json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    need(len(raw) <= MAX_JSON, "receipt exceeds 1 MiB")
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".stage-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Same exclusive atomic-publication primitive as the subset producer.
        # Unsupported filesystem: fail without a non-atomic overwrite fallback.
        os.link(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        need(read_json(path) == document, "publication readback differs; reconcile retained receipt")
        inspect(document, root, now)
    finally:
        os.unlink(temporary)
    return fingerprint(path)


def field(value, path):
    text(path, "output selector", 256)
    for key in path.split("."):
        if isinstance(value, list):
            need(key.isdecimal(), "list selector requires a nonnegative integer index")
            index = int(key)
            need(index < len(value), "output selector index out of range")
            value = value[index]
        else:
            need(isinstance(value, dict) and key in value, "output selector requires an existing object field")
            value = value[key]
    return value


GUI_SCHEMA = "daedalus.copperfall.existing-session.v1"
GUI_GREENHOUSE_SCHEMA = "daedalus.sky-farm.existing-session.v1"
GUI_SCHEMAS = (GUI_SCHEMA, GUI_GREENHOUSE_SCHEMA)
GUI_SUCCEEDED = "TERMINAL_SOURCE_HERO_CREATED_REVIEW_PENDING"
GUI_FAILED = {"TERMINAL_FAILED_PARTIAL_OUTPUTS_RECONCILE", "TERMINAL_CONTEXT_RECONCILIATION_REQUIRED"}


def gui_clock(value):
    """Exact UTC ordering of retained Python/.NET clocks, including 100 ns ticks."""
    text(value, "GUI UTC timestamp", 40)
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(?:Z|\+00:00)", value)
    need(match is not None, "GUI timestamp requires explicit UTC and at most nine fraction digits")
    return stamp(match[1] + "Z"), int((match[2] or "0").ljust(9, "0"))


def gui_outcome(proof):
    state = proof.get("state")
    return "succeeded" if state == GUI_SUCCEEDED else "failed" if isinstance(state, str) and state in GUI_FAILED else "unknown"


def gui_finished(proof, observed):
    start, end = gui_clock(proof.get("started_at_utc")), gui_clock(proof.get("finished_at_utc"))
    need(start <= end <= gui_clock(observed), "GUI completion clock order differs")
    return proof["finished_at_utc"]


def inspect_gui(witness, outputs, reader, attempt_id, observed):
    """Qualify the known retained GUI schema, never fabricate a process exit."""
    reader.verify(witness["evidence"])
    proof = read_json(resolve(witness["evidence"], reader.root))
    need(isinstance(proof, dict) and proof.get("schema") in GUI_SCHEMAS, "unsupported GUI receipt schema")
    greenhouse = proof["schema"] == GUI_GREENHOUSE_SCHEMA
    need(proof.get("operation_id") == witness["operation_id"] == attempt_id
         and type(proof.get("accepted_allocation_hub")) is int
         and proof["accepted_allocation_hub"] == witness["allocation_id"], "GUI source identity mismatch")
    issues = []
    need(set(outputs) <= set(witness["output_fields"]), "GUI output role lacks a terminal binding")
    exit_null = "process_exit_code" in proof and proof["process_exit_code"] is None
    need("process_exit_code" not in proof or exit_null, "persistent GUI receipt must not claim process exit0/exit")
    if not exit_null or proof.get("process_launched") is not False:
        issues.append("persistent GUI process lifecycle witness missing")
    pid = proof.get("existing_blender_pid")
    if type(pid) is not int or pid <= 0:
        issues.append("existing GUI process identity missing")
    finished = None
    try:
        finished = gui_finished(proof, observed)
    except ValueError:
        issues.append("GUI terminal timestamps missing or contradictory")
    outcome = gui_outcome(proof)
    if outcome != "succeeded":
        issues.append("GUI operation failed/partial or terminal outcome is unknown")
    operator_fields = ("startup_copy_result", "source_copy_result", "render_operator_result")
    if greenhouse:
        operator_fields += ("glb_operator_result",)
    for name in operator_fields:
        if proof.get(name) != ["FINISHED"]:
            issues.append("GUI FINISHED witness missing: " + name)
    backup = proof.get("startup_backup")
    if isinstance(backup, dict):
        reader.verify(backup)
        if backup["bytes"] == 0:
            issues.append("startup/session backup is empty")
    else:
        issues.append("verified startup/session backup pin missing")
    for role, selector in witness["output_fields"].items():
        try:
            selected = field(proof, selector)
        except ValueError:
            selected = None
        if selected is None:
            need(role not in outputs, "GUI output has no source witness")
            issues.append("GUI required output witness missing: " + role)
            continue
        need(isinstance(selected, dict), "GUI output witness must be a pin")
        need({"path", "bytes", "sha256"} <= selected.keys(), "GUI output witness lacks pin fields")
        selected = {key: selected[key] for key in ("path", "bytes", "sha256")}
        pin_shape(selected)
        need(role in outputs and outputs[role] == selected, "GUI output pin differs from retained terminal")
        if selected["bytes"] == 0:
            issues.append("GUI required output is empty: " + role)
    # Greenhouse's frozen producer hashes EVERY retained scene, including the
    # startup scene, and its context-restored predicate includes the filepath.
    # It has no separate startup_objects_preserved flag. Never synthesize one
    # or relax Copperfall's three existing flags. A supplied false flag holds.
    restoration_fields = ("original_context_restored", "retained_scenes_preserved")
    if not greenhouse or "startup_objects_preserved" in proof:
        restoration_fields += ("startup_objects_preserved",)
    restored = all(proof.get(k) is True for k in restoration_fields)
    baseline_ok = False
    if "baseline" in witness:
        reader.verify(witness["baseline"])
        baseline = read_json(resolve(witness["baseline"], reader.root))
        if isinstance(baseline, dict):
            hashes = baseline.get("scene_hashes")
            valid_hashes = (isinstance(hashes, dict) and 1 <= len(hashes) <= 32
                            and all(isinstance(k, str) and 0 < len(k) <= 128
                                    and isinstance(v, str) and SHA.fullmatch(v) for k, v in hashes.items()))
            context = proof.get("original_context")
            active_key = "active" if greenhouse else "active_object"
            mapping = {"scene": "original_scene", "mode": "mode", "active_object": "active",
                       "selected": "selected", "filepath": "filepath"}
            context_ok = (isinstance(context, dict)
                          and all(isinstance(context.get(k), str) and 0 < len(context[k]) <= 128
                                  for k in ("scene", "mode", "view_layer"))
                          and (context.get(active_key) is None or isinstance(context.get(active_key), str))
                          and isinstance(context.get("filepath"), str)
                          and isinstance(context.get("selected"), list) and len(context["selected"]) <= 1024
                          and all(isinstance(k, str) and 0 < len(k) <= 128 for k in context["selected"]))
            baseline_ok = (valid_hashes and baseline.get("read_only") is True
                           and baseline.get("run_called") is False and type(baseline.get("pid")) is int
                           and baseline.get("pid") == pid
                           and hashes == proof.get("retained_scene_hashes")
                           and context_ok
                           and (isinstance(baseline.get("context"), dict)
                                and all(k in context for k in ("scene", "view_layer", "active", "selected", "mode", "filepath"))
                                and context == baseline["context"] if greenhouse else
                                all(a in context and b in baseline and context[a] == baseline[b]
                                    for a, b in mapping.items()))
                           )
            try:
                baseline_ok = baseline_ok and gui_clock(baseline.get("observed_at_utc")) <= gui_clock(proof.get("started_at_utc"))
            except ValueError:
                baseline_ok = False
    if not restored or not baseline_ok:
        issues.append("GUI restoration flags and pinned retained-scene baseline do not verify")
    return {"operation_id": witness["operation_id"], "allocation_id": witness["allocation_id"],
            "source_state": proof.get("state"), "declared_outcome": outcome,
            "operation_terminal": outcome != "unknown" and finished is not None,
            "operation_completed": not issues, "restoration_verified": restored and baseline_ok,
            "process_exit_code": None, "existing_pid": pid, "finished_at_utc": finished,
            "retained_partial_scene": proof.get("scene"), "issues": issues}


def gui_released(proof, allocation_id, owner, finished, observed):
    """Historical release of this exact operation/owner, not a live lease query."""
    if not isinstance(proof, dict) or finished is None:
        return False
    before, after = proof.get("before"), proof.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    lease = before.get("compute")
    unlock = proof.get("unlock")
    try:
        ordered = gui_clock(finished) <= gui_clock(proof.get("observed_at_utc")) <= gui_clock(observed)
    except ValueError:
        return False
    return (type(proof.get("grant")) is int and proof["grant"] == allocation_id
            and isinstance(lease, dict) and lease.get("holder") == owner
            and isinstance(unlock, dict) and set(unlock) == {"ok", "lock"}
            and unlock["ok"] is True and unlock["lock"] is None
            and "compute" not in after and ordered)


def adapt_gui(terminal_path, job_id, stage_id, attempt_id, selections, observed_at_utc,
              baseline_path=None, release_path=None, release_owner=None):
    """Normalize actual persistent-GUI receipts read-only; no execution/adoption."""
    proof = read_json(terminal_path)
    need(isinstance(proof, dict) and proof.get("schema") in GUI_SCHEMAS, "unsupported GUI receipt schema")
    need(ident(attempt_id) == proof.get("operation_id"), "caller attempt ID must equal actual GUI operation ID")
    witness = {"operation_id": attempt_id, "allocation_id": proof.get("accepted_allocation_hub"),
               "evidence": fingerprint(terminal_path), "output_fields": copy.deepcopy(selections)}
    if baseline_path:
        witness["baseline"] = fingerprint(baseline_path)
    outputs = {}
    for role, selector in selections.items():
        try:
            pin = field(proof, selector)
        except ValueError:
            continue  # Missing required evidence stays missing, never reconstructed.
        need(isinstance(pin, dict), "GUI output field is not a pin")
        need({"path", "bytes", "sha256"} <= pin.keys(), "GUI output field lacks pin fields")
        outputs[role] = {key: pin[key] for key in ("path", "bytes", "sha256")}
    outcome = gui_outcome(proof)
    terminal = {"state": "terminal", "observed_at_utc": observed_at_utc, "outcome": outcome,
                "effects": "complete" if outcome == "succeeded" else "partial" if outcome == "failed" else "unknown",
                "outputs": outputs, "gui_operation": witness}
    if release_path:
        text(release_owner, "explicit release owner", 128)
        release = read_json(release_path)
        try:
            finished = gui_finished(proof, observed_at_utc)
        except ValueError:
            finished = None
        released = gui_released(release, witness["allocation_id"], release_owner,
                                finished, observed_at_utc)
        terminal["compute_release"] = {"released": True if released else None, "owner": release_owner,
            "proof_kind": "gui-release-v1", "evidence": fingerprint(release_path)}
    return validate({"schema": SCHEMA, "job_id": ident(job_id), "observed_at_utc": observed_at_utc,
        "identities": {}, "provenance": "Known persistent-GUI receipt adapter; no process exit or native qualification inferred.",
        "stages": [{"stage_id": ident(stage_id), "requires": [], "effect": "local-files",
                    "required_outputs": list(selections), "attempts": [{"attempt_id": attempt_id,
                    "inputs": {}, "events": [{"state": "accepted", "observed_at_utc": observed_at_utc}, terminal]}]}]})


def nursery_released(process):
    """Retained historical unlock+readback, never a current lease query."""
    if not isinstance(process, dict):
        return False
    release = process.get("release") if isinstance(process, dict) else None
    return (process.get("schema") == "daedalus.nursery-one-preview-execution.v1"
            and process.get("terminal_known") is True and isinstance(release, dict)
            and release.get("status") == "OURS_RELEASED_VERIFIED"
            and release.get("unlock_attempted") is True
            and release.get("response") == {"ok": True, "lock": None}
            and isinstance(release.get("after"), dict) and "compute" not in release["after"])


def adapt_process(process_path, manifest_path, job_id, stage_id, selections,
                  observed_at_utc, progress_path=None, progress_field="stage", attempt_id=None):
    """Explicit legacy process/manifest adapter, never promoting progress to terminal."""
    process, manifest = read_json(process_path), read_json(manifest_path)
    need(isinstance(process, dict) and type(process.get("exit_code")) is int,
         "legacy adapter requires retained actual exit_code")
    outputs = {}
    for role, selection in selections.items():
        ident(role)
        source = field(manifest, selection)
        need(isinstance(source, dict), "selected output must be a pin object")
        outputs[role] = {k: source[k] for k in ("path", "bytes", "sha256")}
        pin_shape(outputs[role])
    succeeded = process["exit_code"] == 0
    terminal = {"state": "terminal", "observed_at_utc": observed_at_utc,
                "outcome": "succeeded" if succeeded else "failed",
                "effects": "complete" if succeeded else "partial" if outputs else "unknown",
                "outputs": outputs, "process": {"exit_code": process["exit_code"],
                                                      "evidence": fingerprint(process_path)}}
    if nursery_released(process):
        terminal["compute_release"] = {"released": True, "proof_kind": "nursery-release-v1",
                                       "evidence": fingerprint(process_path)}
    if progress_path:
        progress = read_json(progress_path)
        need(isinstance(progress, dict) and isinstance(progress.get(progress_field), str),
             "progress adapter needs explicit object/state field")
        terminal["progress"] = {"state": progress[progress_field], "field": progress_field,
                                "evidence": fingerprint(progress_path)}
    return validate({"schema": SCHEMA, "job_id": ident(job_id), "observed_at_utc": observed_at_utc,
                     "identities": {}, "provenance": "Legacy process/manifest adapter; only selected pinned outputs, no native acceptance.",
                     "stages": [{"stage_id": ident(stage_id), "requires": [], "effect": "local-files",
                                 "required_outputs": list(selections), "attempts": [{"attempt_id": ident(attempt_id),
                                 "inputs": {"manifest": fingerprint(manifest_path)}, "events": [
                                     {"state": "accepted", "observed_at_utc": observed_at_utc}, terminal]}]}]})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "publish"):
        command = sub.add_parser(name)
        command.add_argument("receipt")
        command.add_argument("--root", default=".")
        command.add_argument("--now")
        if name == "publish":
            command.add_argument("--output", required=True)
    command = sub.add_parser("adapt-process")
    for name in ("process", "manifest", "job-id", "stage-id", "attempt-id", "observed-at-utc"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--output-field", action="append", default=[])
    command.add_argument("--progress")
    command.add_argument("--progress-field", default="stage")
    command = sub.add_parser("adapt-gui")
    for name in ("terminal", "job-id", "stage-id", "attempt-id", "observed-at-utc"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--output-field", action="append", default=[])
    command.add_argument("--baseline")
    command.add_argument("--release")
    command.add_argument("--release-owner")
    args = parser.parse_args(argv)
    try:
        if args.command in ("adapt-process", "adapt-gui"):
            selections = {}
            for item in args.output_field:
                role, selection = item.split("=", 1)
                need(role not in selections, "duplicate output role")
                selections[role] = selection
            if args.command == "adapt-process":
                result = adapt_process(args.process, args.manifest, args.job_id, args.stage_id,
                                       selections, args.observed_at_utc, args.progress, args.progress_field, args.attempt_id)
            else:
                result = adapt_gui(args.terminal, args.job_id, args.stage_id, args.attempt_id,
                                   selections, args.observed_at_utc, args.baseline, args.release, args.release_owner)
            code = 0
        else:
            document = read_json(args.receipt)
            if args.command == "publish":
                result = {"published": publish(document, args.output, args.root, args.now)}
                code = 0
            else:
                result = inspect(document, args.root, args.now)
                code = 0 if result["complete"] else 2
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return code
    except (ValueError, OSError, KeyError, TypeError, RecursionError, OverflowError) as error:
        print(json.dumps({"error": type(error).__name__ + ": " + str(error),
                          "complete": False, "execution": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
