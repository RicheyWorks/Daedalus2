# SPDX-License-Identifier: MIT
"""Strict, engine-free takeover contracts and a deterministic admission planner.

These contracts describe retained evidence and operator attestations. They neither
authenticate an owner nor acquire custody. A ready plan still requires the live
owner's normal generation, lease, resource and native admission checks.
"""

import copy
import datetime as dt
import re

from .evidence_paths import evidence_path_issue


CHECKPOINT_SCHEMA = "daedalus.takeover-checkpoint.v1"
ADMISSION_SCHEMA = "daedalus.takeover-admission.v1"
PLAN_SCHEMA = "daedalus.takeover-plan.v1"
EVIDENCE_ROLES = ("checkpoint", "owner", "ledger", "source", "build", "native", "catalog")
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,9}))?(?:Z|\+00:00)\Z")


class ContractError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _fail(code, message):
    raise ContractError(code, message)


def _object(value, keys, at):
    if not isinstance(value, dict):
        _fail("INVALID_FIELD", at + " must be an object")
    if set(value) != set(keys):
        missing = sorted(set(keys) - set(value))
        extra = sorted(set(value) - set(keys), key=str)
        _fail("INVALID_FIELD", "%s fields differ (missing=%s, unexpected=%s)" % (at, missing, extra))


def _string(value, at, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or any(ord(c) < 32 for c in value):
        _fail("INVALID_FIELD", at + " must be a nonempty string without control characters (max 4096)")


def _integer(value, at, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        _fail("INVALID_FIELD", at + " must be an integer in the supported range")


def _boolean(value, at):
    if type(value) is not bool:
        _fail("INVALID_FIELD", at + " must be a boolean")


def _hash(value, at, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        _fail("INVALID_SHA256", at + " must be a lowercase SHA-256 digest")


def _enum(value, choices, at):
    if not isinstance(value, str) or value not in choices:
        _fail("INVALID_FIELD", "%s must be one of %s" % (at, ", ".join(choices)))


def _strings(value, at, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        _fail("INVALID_FIELD", at + " must be a list" + (" with at least one item" if nonempty else ""))
    for index, item in enumerate(value):
        _string(item, "%s[%d]" % (at, index))
    if len(value) != len(set(value)):
        _fail("INVALID_FIELD", at + " must not contain duplicate identities")


def _instant(value, at):
    """UTC parsing compatible with Python 3.10, retaining generation precision."""
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        _fail("INVALID_TIMESTAMP", at + " must be an explicit UTC timestamp (Z or +00:00, up to 9 fractional digits)")
    match = UTC_RE.fullmatch(value)
    fraction = (match.group(1) or "").ljust(9, "0")
    base = value[:19] + "." + fraction[:6] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(base)
    except ValueError:
        _fail("INVALID_TIMESTAMP", at + " is not a valid calendar timestamp")
    return parsed, int(fraction[6:])


def _seconds(left, right):
    a, ar = left
    b, br = right
    return (a - b).total_seconds() + (ar - br) / 1_000_000_000


def timestamp_key(value):
    """Comparable UTC key retaining submicrosecond generation precision."""
    return _instant(value, "timestamp")


def _path(value, at):
    _string(value, at)
    issue = evidence_path_issue(value)
    if issue == "shape":
        _fail("INVALID_PATH", at + " must be a portable relative evidence path (max 220 ASCII characters)")
    if issue == "components":
        _fail("INVALID_PATH", at + " must be a normalized relative POSIX path")
    if issue == "nonportable_component":
        _fail("INVALID_PATH", at + " is not portable between supported filesystems")
    if issue == "reserved_component":
        _fail("INVALID_PATH", at + " uses a reserved device name")


def _identity(value, at):
    _object(value, ("owner", "session", "host", "pid", "start_utc"), at)
    for name in ("owner", "session", "host"):
        _string(value[name], at + "." + name)
    _integer(value["pid"], at + ".pid", 1)
    _instant(value["start_utc"], at + ".start_utc")


def _identity_key(value):
    return tuple(value[k] for k in ("owner", "session", "host", "pid")) + (_instant(value["start_utc"], "identity.start_utc"),)


def _runtime(value, at):
    _object(value, ("name", "version", "config_sha256", "artifact_sha256", "generation"), at)
    for name in ("name", "version", "generation"):
        _string(value[name], at + "." + name)
    for name in ("config_sha256", "artifact_sha256"):
        _hash(value[name], at + "." + name)


def _operations(value, at):
    if not isinstance(value, list):
        _fail("INVALID_FIELD", at + " must be a list")
    seen = set()
    for index, item in enumerate(value):
        loc = "%s[%d]" % (at, index)
        _object(item, ("id", "intent_sha256", "target_ids", "outcome", "result_sha256", "reconciled"), loc)
        _string(item["id"], loc + ".id")
        if item["id"] in seen:
            _fail("INVALID_FIELD", at + " has duplicate operation IDs")
        seen.add(item["id"])
        _hash(item["intent_sha256"], loc + ".intent_sha256")
        _strings(item["target_ids"], loc + ".target_ids", nonempty=True)
        _enum(item["outcome"], ("pending", "saved", "partial", "unknown", "failed_no_effect"), loc + ".outcome")
        _hash(item["result_sha256"], loc + ".result_sha256", nullable=True)
        _boolean(item["reconciled"], loc + ".reconciled")
        if item["outcome"] in ("saved", "partial", "failed_no_effect") and item["result_sha256"] is None:
            _fail("INVALID_FIELD", loc + " requires a retained result digest for its stated outcome")
        if item["reconciled"] and item["outcome"] in ("pending", "partial", "unknown"):
            _fail("INVALID_FIELD", loc + " cannot label an unresolved outcome reconciled")


def validate_checkpoint(doc):
    _object(doc, ("schema", "campaign", "sequence", "prior_sha256", "saved_utc", "phase", "owner", "runtime", "window", "progress", "source", "build", "evidence", "operations"), "checkpoint")
    if doc["schema"] != CHECKPOINT_SCHEMA:
        _fail("UNSUPPORTED_VERSION", "checkpoint schema must be " + CHECKPOINT_SCHEMA)
    _string(doc["campaign"], "checkpoint.campaign")
    _integer(doc["sequence"], "checkpoint.sequence", 1)
    _hash(doc["prior_sha256"], "checkpoint.prior_sha256", nullable=True)
    if (doc["sequence"] == 1) != (doc["prior_sha256"] is None):
        _fail("INVALID_FIELD", "checkpoint prior digest must be absent exactly for sequence 1")
    _instant(doc["saved_utc"], "checkpoint.saved_utc")
    _enum(doc["phase"], ("saved", "in_flight", "uncertain", "stopped"), "checkpoint.phase")
    _identity(doc["owner"], "checkpoint.owner")
    _runtime(doc["runtime"], "checkpoint.runtime")
    _object(doc["window"], ("start_utc", "deadline_utc"), "checkpoint.window")
    window_start = _instant(doc["window"]["start_utc"], "checkpoint.window.start_utc")
    window_deadline = _instant(doc["window"]["deadline_utc"], "checkpoint.window.deadline_utc")
    if window_deadline <= window_start:
        _fail("INVALID_WINDOW", "checkpoint window deadline must follow its original start")
    progress = doc["progress"]
    _object(progress, ("counts", "next_index", "last_operation_id"), "checkpoint.progress")
    if not isinstance(progress["counts"], dict) or not progress["counts"]:
        _fail("INVALID_FIELD", "checkpoint.progress.counts must be a nonempty object")
    for kind, count in progress["counts"].items():
        _string(kind, "checkpoint.progress.counts key")
        _integer(count, "checkpoint.progress.counts." + kind)
    _integer(progress["next_index"], "checkpoint.progress.next_index", 1)
    _string(progress["last_operation_id"], "checkpoint.progress.last_operation_id", nullable=True)
    source = doc["source"]
    _object(source, ("status", "commit", "manifest_sha256", "dirty", "exceptions", "reason"), "checkpoint.source")
    _enum(source["status"], ("recorded", "unknown"), "checkpoint.source.status")
    _string(source["commit"], "checkpoint.source.commit", nullable=True)
    _hash(source["manifest_sha256"], "checkpoint.source.manifest_sha256", nullable=True)
    if source["dirty"] is not None:
        _boolean(source["dirty"], "checkpoint.source.dirty")
    _strings(source["exceptions"], "checkpoint.source.exceptions")
    _string(source["reason"], "checkpoint.source.reason", nullable=True)
    if source["status"] == "recorded":
        if any(source[k] is None for k in ("commit", "manifest_sha256", "dirty")) or source["reason"] is not None:
            _fail("INVALID_FIELD", "recorded source requires commit, manifest, dirty status and a null absence reason")
        if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", source["commit"]) is None:
            _fail("INVALID_FIELD", "recorded source commit must be an exact lowercase Git commit identity")
    elif source["reason"] is None:
        _fail("INVALID_FIELD", "unknown source provenance requires an explicit reason")
    build = doc["build"]
    _object(build, ("status", "source_manifest_sha256", "artifact_sha256", "receipt_sha256", "reason"), "checkpoint.build")
    _enum(build["status"], ("bound", "unknown"), "checkpoint.build.status")
    for name in ("source_manifest_sha256", "artifact_sha256", "receipt_sha256"):
        _hash(build[name], "checkpoint.build." + name, nullable=True)
    _string(build["reason"], "checkpoint.build.reason", nullable=True)
    if build["status"] == "bound":
        if any(build[k] is None for k in ("source_manifest_sha256", "artifact_sha256", "receipt_sha256")) or build["reason"] is not None:
            _fail("INVALID_FIELD", "bound build requires source, artifact and build receipt digests and a null absence reason")
    elif build["reason"] is None:
        _fail("INVALID_FIELD", "unknown build provenance requires an explicit reason")
    _object(doc["evidence"], EVIDENCE_ROLES, "checkpoint.evidence")
    paths = set()
    for role, evidence in doc["evidence"].items():
        at = "checkpoint.evidence." + role
        _object(evidence, ("status", "path", "reason"), at)
        _enum(evidence["status"], ("present", "unknown"), at + ".status")
        if evidence["status"] == "present":
            _path(evidence["path"], at + ".path")
            if evidence["reason"] is not None:
                _fail("INVALID_FIELD", at + " present evidence must have a null absence reason")
            normalized = evidence["path"].casefold()
            if normalized in paths:
                _fail("INVALID_PATH", "named evidence roles must reference distinct portable paths")
            paths.add(normalized)
        else:
            if evidence["path"] is not None:
                _fail("INVALID_FIELD", at + " unknown evidence requires a null path and explicit absence reason")
            _string(evidence["reason"], at + ".reason")
    _operations(doc["operations"], "checkpoint.operations")
    last = progress["last_operation_id"]
    if last is not None and last not in {op["id"] for op in doc["operations"]}:
        _fail("INVALID_FIELD", "last_operation_id must refer to retained checkpoint operation evidence")


def validate_request(doc):
    _object(doc, ("schema", "packet_sha256", "evaluated_utc", "successor", "previous_owner", "custody", "runtime", "source_manifest_sha256", "build_receipt_sha256", "journal", "window"), "admission")
    if doc["schema"] != ADMISSION_SCHEMA:
        _fail("UNSUPPORTED_VERSION", "admission schema must be " + ADMISSION_SCHEMA)
    _hash(doc["packet_sha256"], "admission.packet_sha256")
    _instant(doc["evaluated_utc"], "admission.evaluated_utc")
    successor = doc["successor"]
    _object(successor, ("owner", "session", "host", "authority_ref"), "admission.successor")
    for key, value in successor.items():
        _string(value, "admission.successor." + key)
    previous = doc["previous_owner"]
    _object(previous, ("identity", "state", "observed_utc", "max_age_seconds"), "admission.previous_owner")
    _identity(previous["identity"], "admission.previous_owner.identity")
    _enum(previous["state"], ("alive", "absent", "exited", "unknown", "reused"), "admission.previous_owner.state")
    _instant(previous["observed_utc"], "admission.previous_owner.observed_utc")
    _integer(previous["max_age_seconds"], "admission.previous_owner.max_age_seconds", 1, 3600)
    custody = doc["custody"]
    _object(custody, ("owner", "unreal", "compute", "authority_ref"), "admission.custody")
    _string(custody["owner"], "admission.custody.owner")
    _string(custody["authority_ref"], "admission.custody.authority_ref")
    for name in ("unreal", "compute"):
        _enum(custody[name], ("held", "unknown", "foreign"), "admission.custody." + name)
    _runtime(doc["runtime"], "admission.runtime")
    _hash(doc["source_manifest_sha256"], "admission.source_manifest_sha256", nullable=True)
    _hash(doc["build_receipt_sha256"], "admission.build_receipt_sha256", nullable=True)
    journal = doc["journal"]
    _object(journal, ("complete", "through_utc", "later_operations"), "admission.journal")
    _boolean(journal["complete"], "admission.journal.complete")
    _instant(journal["through_utc"], "admission.journal.through_utc")
    _operations(journal["later_operations"], "admission.journal.later_operations")
    _object(doc["window"], ("start_utc", "deadline_utc"), "admission.window")
    for name, value in doc["window"].items():
        _instant(value, "admission.window." + name)


def plan(checkpoint, request, packet_sha256, *, selection="current"):
    """Describe supported next steps without executing or authorizing live work.

    All time comparisons use supplied timestamps; no clock, process, network or
    filesystem access occurs. Next index is retained exactly, never recalculated
    from a partial result, operation count, heartbeat or source inventory.
    """
    validate_checkpoint(checkpoint)
    validate_request(request)
    _hash(packet_sha256, "packet_sha256")
    _enum(selection, ("current", "previous", "explicit"), "selection")
    reasons = []

    def hold(code, message):
        reasons.append({"code": code, "message": message})

    if request["packet_sha256"] != packet_sha256:
        hold("PACKET_CHANGED", "Requested packet digest differs from the verified sealed packet")
    if selection != "current":
        hold("NONCURRENT_PACKET", "A retained packet is inspectable; reconcile the current pointer and all later operations before continuation")
    if checkpoint["phase"] not in ("saved", "stopped"):
        hold("UNRESOLVED_PHASE", "Checkpoint phase is " + checkpoint["phase"] + "; preserve effects and reconcile before continuation")
    observed = request["previous_owner"]
    if _identity_key(observed["identity"]) != _identity_key(checkpoint["owner"]):
        hold("OWNER_IDENTITY_CHANGED", "Observed owner identity does not match retained owner/session/host/PID/start generation")
    if observed["state"] not in ("absent", "exited"):
        hold("OWNER_" + observed["state"].upper(), "Previous owner state is " + observed["state"] + "; silence and stale heartbeat do not establish termination")
    now = _instant(request["evaluated_utc"], "evaluated_utc")
    observed_at = _instant(observed["observed_utc"], "observed_utc")
    age = _seconds(now, observed_at)
    if age < 0 or age > observed["max_age_seconds"]:
        hold("STALE_OWNER_OBSERVATION", "Previous owner observation is future-dated or outside its explicit freshness limit")
    if _seconds(now, _instant(checkpoint["saved_utc"], "saved_utc")) < 0:
        hold("FUTURE_CHECKPOINT", "Checkpoint is newer than the supplied evaluation time")
    successor = request["successor"]
    if successor["session"] == checkpoint["owner"]["session"]:
        hold("SESSION_REUSED", "A successor requires a fresh session; retained predecessor configuration must remain unchanged")
    if successor["host"] != checkpoint["owner"]["host"]:
        hold("HOST_CHANGED", "Cross-host transfer requires a separately reviewed integration contract")
    custody = request["custody"]
    if custody["owner"] != successor["owner"] or any(custody[k] != "held" for k in ("unreal", "compute")):
        hold("CUSTODY_UNESTABLISHED", "Both normal unreal and compute custody observations must belong to the actual successor owner")
    if request["runtime"] != checkpoint["runtime"]:
        hold("RUNTIME_CHANGED", "Runtime version, generation, configuration or artifact digest differs; retain evidence and establish a new supported binding")
    source, build = checkpoint["source"], checkpoint["build"]
    if source["status"] != "recorded":
        hold("SOURCE_PROVENANCE_UNKNOWN", source["reason"])
    if source["exceptions"]:
        hold("SOURCE_EXCEPTIONS", "Source exceptions require a separately reviewed transition; v1 does not admit an exception bypass")
    if source["dirty"] is True:
        hold("DIRTY_SOURCE", "Dirty source requires a separately reviewed input transition; v1 retains its manifest but does not admit continuation from it")
    if build["status"] != "bound":
        hold("BUILD_PROVENANCE_UNKNOWN", build["reason"])
    if source["manifest_sha256"] != request["source_manifest_sha256"]:
        hold("SOURCE_CHANGED", "Current source manifest differs from the checkpoint; current bytes do not prove historical build inputs")
    if build["receipt_sha256"] != request["build_receipt_sha256"]:
        hold("BUILD_CHANGED", "Current build receipt differs from the retained build binding")
    if build["status"] == "bound" and (build["source_manifest_sha256"] != source["manifest_sha256"] or build["artifact_sha256"] != checkpoint["runtime"]["artifact_sha256"]):
        hold("BUILD_BINDING_MISMATCH", "Build receipt must bind the exact source manifest and runtime artifact")
    for role in EVIDENCE_ROLES:
        if checkpoint["evidence"][role]["status"] != "present":
            hold("EVIDENCE_UNKNOWN", role + ": " + checkpoint["evidence"][role]["reason"])
    journal = request["journal"]
    through = _instant(journal["through_utc"], "through_utc")
    if not journal["complete"] or _seconds(through, observed_at) < 0 or _seconds(now, through) < 0:
        hold("JOURNAL_INCOMPLETE", "Complete journal inventory must cover the owner observation and must not claim a future cutoff")
    if _seconds(through, _instant(checkpoint["saved_utc"], "saved_utc")) < 0:
        hold("JOURNAL_PRECEDES_CHECKPOINT", "Journal inventory cutoff precedes the retained checkpoint")
    start = _instant(request["window"]["start_utc"], "window.start_utc")
    deadline = _instant(request["window"]["deadline_utc"], "window.deadline_utc")
    original_start = _instant(checkpoint["window"]["start_utc"], "checkpoint.window.start_utc")
    original_deadline = _instant(checkpoint["window"]["deadline_utc"], "checkpoint.window.deadline_utc")
    if start != original_start or deadline != original_deadline:
        hold("WINDOW_CHANGED", "Requested window differs from the retained original run window; continuation must not reset a consumed window")
    if _seconds(deadline, start) <= 0 or _seconds(now, start) < 0 or _seconds(deadline, now) <= 0:
        hold("WINDOW_CLOSED", "Supplied authorized window is invalid, not started or expired; do not reset it")
    operations = []
    retained = {op["id"]: op for op in checkpoint["operations"]}
    last_operation = retained.get(checkpoint["progress"]["last_operation_id"])
    if checkpoint["progress"]["last_operation_id"] is None and any(checkpoint["progress"]["counts"].values()):
        hold("LAST_OPERATION_MISSING", "Nonzero saved counts require the exact last saved operation and result evidence")
    if last_operation is not None and (last_operation["outcome"] != "saved" or not last_operation["reconciled"]):
        hold("LAST_OPERATION_UNSAVED", "The last verified saved operation must have retained saved and reconciled result evidence")
    for op in checkpoint["operations"]:
        action = "already_recorded" if op["reconciled"] else "reconcile"
        operations.append({"id": op["id"], "outcome": op["outcome"], "reconciled": op["reconciled"], "action": action})
        if not op["reconciled"]:
            hold("OPERATION_UNRECONCILED", "Retained operation " + op["id"] + " requires result/save/readback reconciliation; replay is not admitted")
    for op in journal["later_operations"]:
        old = retained.get(op["id"])
        if old is not None and old != op:
            hold("OPERATION_CHANGED", "Later operation evidence differs for retained ID " + op["id"])
        if old is None:
            operations.append({"id": op["id"], "outcome": op["outcome"], "reconciled": op["reconciled"], "action": "reconcile"})
        hold("LATER_OPERATION", "Journal reports later operation " + op["id"] + "; publish a reconciled checkpoint rather than replaying or advancing it here")
    return {
        "schema": PLAN_SCHEMA,
        "status": "held" if reasons else "ready_for_live_admission",
        "packet_sha256": packet_sha256,
        "selection": selection,
        "owner": copy.deepcopy(checkpoint["owner"]),
        "successor": copy.deepcopy(successor),
        "window": copy.deepcopy(checkpoint["window"]),
        "progress": copy.deepcopy(checkpoint["progress"]),
        "reasons": reasons,
        "operations": operations,
        "live_integration_required": True,
        "may_execute": False,
    }
