# SPDX-License-Identifier: MIT
"""Observe a declared invocation and retain compatible build receipts.

This is not a command sandbox, dependency discovery or a native-build launcher.
Only the supplied foreground child is supervised; no process/lease discovery.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import uuid

from tools.team_handoff import packet
from tools.team_handoff.contracts import ContractError, timestamp_key

REQUEST_SCHEMA = "daedalus.build-capture-request.v1"
CAPTURE_SCHEMA = "daedalus.build-capture.v1"
SUCCESS_SCHEMA = "daedalus.build-capture-success.v1"
MAX_REQUEST = 65536
MAX_FILES = 1024
MAX_ENTRIES = 2048
MAX_DEPTH = 16
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_ARTIFACT = 16 * 1024 * 1024
MAX_LOG = 1024 * 1024
CATEGORIES = ("source", "header", "descriptor", "config", "generated")
UNKNOWN = {
    "dependency_completeness": "unknown",
    "external_dependencies": "unknown",
    "environment_identity": "unknown",
    "source_commit_verified": False,
    "toolchain_verified": False,
    "runtime_or_editor_parity": "unknown",
    "descendant_completion": "unknown",
    "artifact_causal_producer": "unknown",
    "continuous_input_immutability": "unknown",
}


def _fail(code, message):
    raise ContractError(code, message)


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("request_fields", label + " fields differ from the v1 contract")


def _text(value, label, maximum=4096):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value)):
        _fail("request_field", label + " must be nonempty text without control characters")


def validate_request(value):
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if depth > 64 or nodes > MAX_REQUEST:
            _fail("request_json", "Request exceeds JSON depth/node limits")
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                _fail("request_json", "JSON object keys must be strings")
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    try:
        encoded = packet.canonical(value)
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        _fail("request_json", "Request must be finite UTF-8 JSON: " + str(exc))
    if len(encoded) > MAX_REQUEST:
        _fail("request_size", "Canonical request exceeds 64 KiB")
    _keys(value, ("schema", "source_commit", "toolchain", "command", "inputs",
                  "artifact", "timeout_seconds", "notes"), "capture request")
    if value["schema"] != REQUEST_SCHEMA:
        _fail("request_version", "Only build-capture-request v1 is supported")
    commit = value["source_commit"]
    if (not isinstance(commit, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit)
            or not commit.strip("0")):
        _fail("request_field", "source_commit must be a full nonzero lowercase declared commit")
    _keys(value["toolchain"], ("engine", "compiler"), "toolchain")
    for key, item in value["toolchain"].items():
        _text(item, "toolchain." + key)
    command = value["command"]
    if not isinstance(command, list) or not 1 <= len(command) <= 64:
        _fail("request_field", "command must be an argv array of 1..64 strings")
    for arg in command:
        _text(arg, "command argument")
    if sum(len(arg) for arg in command) > 16384:
        _fail("request_field", "command exceeds 16384 characters")
    if type(value["timeout_seconds"]) is not int or not 1 <= value["timeout_seconds"] <= 60:
        _fail("request_field", "timeout_seconds must be an integer in 1..60")
    # Notes are retained as opaque JSON, never interpreted as build facts.
    if not isinstance(value["notes"], dict):
        _fail("request_field", "notes must be a JSON object (unknown facts may stay null)")
    if not isinstance(value["inputs"], list) or not 1 <= len(value["inputs"]) <= 64:
        _fail("request_field", "inputs must declare 1..64 nonoverlapping roots")
    roots, spellings = [], {}
    for row in value["inputs"]:
        _keys(row, ("path", "kind", "category"), "input root")
        name = packet.relative(row["path"])
        for index in range(1, len(name.split("/")) + 1):
            prefix = "/".join(name.split("/")[:index])
            old = spellings.setdefault(prefix.casefold(), prefix)
            if old != prefix:
                _fail("case_collision", "Input path prefixes differ only by case")
        if row["kind"] not in ("file", "directory") or row["category"] not in CATEGORIES:
            _fail("request_field", "Unsupported input kind/category")
        folded = name.casefold()
        if any(folded == old or folded.startswith(old + "/") or old.startswith(folded + "/")
               for old in roots):
            _fail("input_overlap", "Input roots overlap or collide by case")
        roots.append(folded)
    artifact_name = packet.relative(value["artifact"])
    for index in range(1, len(artifact_name.split("/")) + 1):
        prefix = "/".join(artifact_name.split("/")[:index])
        old = spellings.setdefault(prefix.casefold(), prefix)
        if old != prefix:
            _fail("case_collision", "Artifact/input path prefixes differ only by case")
    artifact = artifact_name.casefold()
    if any(artifact == root or artifact.startswith(root + "/") or root.startswith(artifact + "/")
           for root in roots):
        _fail("artifact_overlap", "Artifact and input roots must be disjoint")
    return value


def _request(raw):
    try:
        return validate_request(packet.decode(raw, "capture request"))
    except (UnicodeError, RecursionError) as exc:
        _fail("request_json", "Request nesting/encoding is unsupported: " + str(exc))


def _utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _identity(value):
    return {key: getattr(value, key) for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink")}


def _binding_identity(value):
    # Windows CPython 3.12.10 uses creation time for path ctime and change
    # time for handle ctime. Preserve/check each API's own ctime separately.
    return {key: item for key, item in _identity(value).items() if key != "st_ctime_ns"}


def _regular(path):
    packet._plain(path)
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        _fail("file_type", "Only ordinary files are supported: " + str(path))
    if value.st_nlink != 1:
        _fail("linked_path", "Hard-linked files are refused: " + str(path))
    return value


def _file(path, limit, copy_to=None):
    before = _regular(path)
    if before.st_size > limit:
        _fail("file_size", "Declared file exceeds capture limit: " + str(path))
    digest, size = hashlib.sha256(), 0
    target = copy_to.open("xb") if copy_to is not None else None
    try:
        with path.open("rb") as stream:
            handle_before = os.fstat(stream.fileno())
            if _binding_identity(handle_before) != _binding_identity(before):
                _fail("input_race", "File identity changed before read: " + str(path))
            while True:
                raw = stream.read(min(65536, limit - size + 1))
                if not raw:
                    break
                size += len(raw)
                if size > limit:
                    _fail("file_size", "File grew beyond capture limit: " + str(path))
                digest.update(raw)
                if target is not None:
                    target.write(raw)
            if _identity(os.fstat(stream.fileno())) != _identity(handle_before):
                _fail("input_race", "File changed during read: " + str(path))
        if _identity(_regular(path)) != _identity(before):
            _fail("input_race", "File identity changed after read: " + str(path))
        if target is not None:
            target.flush()
            os.fsync(target.fileno())
    finally:
        if target is not None:
            target.close()
    return {"sha256": digest.hexdigest(), "bytes": size}, _identity(before)


def _new_json(path, value):
    packet._write_new(path, packet.canonical(value))


def _scan(workspace, request, copies=None):
    files, identities, seen, entries, total = [], {}, set(), 0, 0

    def visit(name, category, depth, expected=None):
        nonlocal entries, total
        entries += 1
        if entries > MAX_ENTRIES or depth > MAX_DEPTH:
            _fail("input_limit", "Declared closure exceeds entry/depth limits")
        path = packet._path(workspace, name)
        folded = packet.relative(name).casefold()
        if folded in seen:
            _fail("case_collision", "Input identities collide by case: " + name)
        seen.add(folded)
        value = path.lstat()
        is_dir = stat.S_ISDIR(value.st_mode)
        if expected is not None and is_dir != (expected == "directory"):
            _fail("input_kind", "Input root type differs: " + name)
        identities[name] = _identity(value)
        if is_dir:
            if copies is not None:
                packet._path(copies, name).mkdir(parents=True, exist_ok=True)
            children, child_names = [], set()
            with os.scandir(path) as iterator:
                for child in iterator:
                    if entries + len(children) >= MAX_ENTRIES:
                        _fail("input_limit", "Declared closure exceeds entry limit")
                    packet.relative(name + "/" + child.name)
                    if child.name.casefold() in child_names:
                        _fail("case_collision", "Input directory entries collide by case: " + name)
                    child_names.add(child.name.casefold())
                    children.append(child.name)
            for child in sorted(children):
                visit(name + "/" + child, category, depth + 1)
        else:
            if len(files) >= MAX_FILES:
                _fail("input_limit", "Declared closure exceeds file count limit")
            target = None
            if copies is not None:
                target = packet._path(copies, name)
                target.parent.mkdir(parents=True, exist_ok=True)
            pin, identity = _file(path, min(MAX_FILE, MAX_TOTAL - total), target)
            total += pin["bytes"]
            identities[name] = identity
            files.append(dict(path=name, category=category, **pin))
    for root in sorted(request["inputs"], key=lambda row: row["path"]):
        visit(root["path"], root["category"], 0, root["kind"])
    if not files:
        _fail("empty_inputs", "Declared closure must contain at least one file")
    return {"schema": "daedalus.build-inputs.v1", "commit": request["source_commit"],
            "files": sorted(files, key=lambda row: row["path"])}, identities


def _run(command, workspace, output, timeout):
    """Bound retained output and supervise only this direct child."""
    observed = {"started_utc": _utc(), "ended_utc": None, "exit_code": None,
                "status": "launching", "log_truncated": False, "child_reaped": False}
    overflow, read_error = threading.Event(), []
    process = None
    reader = None
    started = time.monotonic()
    try:
        log = (output / "command.log").open("xb")
        try:
            process = subprocess.Popen(command, cwd=workspace, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       shell=False, bufsize=0)

            def drain():
                retained = 0
                try:
                    while True:
                        raw = process.stdout.read(65536)
                        if not raw:
                            break
                        keep = raw[:max(0, MAX_LOG - retained)]
                        log.write(keep)
                        retained += len(keep)
                        if len(keep) != len(raw):
                            overflow.set()
                            break
                except OSError as exc:
                    read_error.append(str(exc))
                finally:
                    try:
                        log.flush()
                        os.fsync(log.fileno())
                    except OSError as exc:
                        read_error.append(str(exc))
                    finally:
                        log.close()
                        process.stdout.close()

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            while process.poll() is None:
                if overflow.is_set():
                    observed["status"] = "output_limit"
                    break
                if time.monotonic() - started >= timeout:
                    observed["status"] = "timeout"
                    break
                time.sleep(0.01)
            else:
                observed["status"] = "exited"
        finally:
            if process is None:
                log.close()
    except KeyboardInterrupt:
        observed["status"] = "interrupted"
    except OSError as exc:
        observed.update(status="launch_error", error=str(exc))
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                observed["exit_code"] = process.wait(timeout=2)
                observed["child_reaped"] = True
            except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
                observed["status"] = "child_uncertain"
            if reader is not None:
                reader.join(timeout=min(2, max(0.01, timeout - (time.monotonic() - started))))
                if reader.is_alive():
                    observed["status"] = "output_incomplete"
                elif read_error:
                    observed.update(status="log_error", error=read_error[0])
            observed["log_truncated"] = overflow.is_set()
            if overflow.is_set() and observed["status"] == "exited":
                observed["status"] = "output_limit"
        observed["ended_utc"] = _utc()
    return observed


def capture(request_path, workspace, output, fault=None):
    """Execute once; never resume or relabel an earlier command as build-time."""
    request_path = Path(os.path.abspath(request_path))
    packet._root(request_path.parent)
    _regular(request_path)
    raw = packet._read(request_path, MAX_REQUEST)
    request = _request(raw)
    workspace = packet._root(workspace)
    output = Path(os.path.abspath(output))
    packet._root(output.parent)
    packet._plain(output)
    if output == workspace or workspace in output.parents or output in workspace.parents:
        _fail("output_overlap", "Workspace and fresh output must be disjoint")
    if output == request_path or output in request_path.parents:
        _fail("output_overlap", "Output cannot contain the request")
    output.mkdir()  # Exclusive reservation; existing/partial captures are never reused.
    result = {"schema": CAPTURE_SCHEMA, "capture_id": uuid.uuid4().hex,
              "created_utc": _utc(), "finished_utc": None, "status": "incomplete",
              "request_sha256": packet.digest(raw),
              "command_sha256": packet.digest(packet.canonical(request["command"])),
              "command": request["command"], "process": None, "error": None,
              "artifact": {"path": request["artifact"], "before": None, "after": None,
                           "before_observed_utc": None, "after_observed_utc": None,
                           "observation": "not_observed"},
              "unknowns": dict(UNKNOWN), "notes": request["notes"]}
    def inject(phase):
        if fault:
            fault(phase)
    try:
        packet._write_new(output / "request.json", raw)
        _new_json(output / "capture.json", result)
        copies = output / "inputs"
        copies.mkdir()
        before, identities = _scan(workspace, request, copies)
        _new_json(output / "inputs-before.json", before)
        _new_json(output / "identities-before.json", identities)
        artifact = packet._path(workspace, request["artifact"])
        if artifact.exists():
            result["artifact"]["before"] = _file(artifact, MAX_ARTIFACT)[0]
            result["artifact"]["before_observed_utc"] = _utc()
            _fail("stale_artifact", "Artifact exists before launch; preserve it and choose a fresh declared artifact")
        result["artifact"]["before_observed_utc"] = _utc()
        inject("before_command")
        result["process"] = _run(request["command"], workspace, output, request["timeout_seconds"])
        inject("after_command")
        observation_errors = []
        after, after_identities = None, None
        try:
            after, after_identities = _scan(workspace, request)
            _new_json(output / "inputs-after.json", after)
            _new_json(output / "identities-after.json", after_identities)
        except (ContractError, OSError) as exc:
            observation_errors.append({"code": getattr(exc, "code", "io_error"), "message": str(exc)})
        try:
            artifact = packet._path(workspace, request["artifact"])
            if artifact.exists():
                result["artifact"]["after"] = _file(artifact, MAX_ARTIFACT, output / "artifact.bin")[0]
                result["artifact"]["observation"] = "absent_before_present_after"
            result["artifact"]["after_observed_utc"] = _utc()
        except (ContractError, OSError) as exc:
            observation_errors.append({"code": getattr(exc, "code", "io_error"), "message": str(exc)})
        result["observation_errors"] = observation_errors
        if observation_errors:
            _fail("observation_incomplete", "Post-command evidence is incomplete; retained errors identify the failed observations")
        if before != after or identities != after_identities:
            _fail("inputs_changed", "Declared input membership, content or metadata changed during invocation")
        process = result["process"]
        if process["status"] != "exited" or process["exit_code"] != 0 or not process["child_reaped"]:
            _fail("command_failed", "Observed command did not finish successfully: " + process["status"])
        if result["artifact"]["after"] is None:
            _fail("artifact_missing", "Command produced no observable fresh artifact")
        # Existing strict consumer requires these exact keys; extra observations
        # and all uncertainty remain in the separate capture record.
        source_raw = packet.canonical(before)
        provenance = {"schema": "daedalus.build-provenance.v1", "recorded_at_build_time": True,
                      "source_commit": request["source_commit"],
                      "inputs_before_sha256": packet.digest(source_raw),
                      "inputs_after_sha256": packet.digest(packet.canonical(after)),
                      "artifact_sha256": result["artifact"]["after"]["sha256"],
                      "toolchain": request["toolchain"], "command": request["command"], "exit_code": 0}
        staging = output / (".receipts-" + uuid.uuid4().hex)
        staging.mkdir()
        packet._write_new(staging / "source.json", source_raw)
        _new_json(staging / "build.json", provenance)
        result.update(status="captured", finished_utc=_utc())
        packet._replace_json(output / "capture.json", result)
        pins = {}
        for name in ("request.json", "capture.json", "inputs-before.json", "inputs-after.json",
                     "identities-before.json", "identities-after.json", "artifact.bin", "command.log"):
            pins[name] = _file(output / name, MAX_TOTAL)[0]
        for name in ("source.json", "build.json"):
            pins["receipts/" + name] = _file(staging / name, MAX_REQUEST * 8)[0]
        _verify_receipts(output, staging, pins, result)
        _new_json(staging / "success.json", {"schema": SUCCESS_SCHEMA, "capture_id": result["capture_id"], "files": pins})
        packet._sync_dir(staging)
        inject("before_publish")
        packet._plain(output / "receipts")
        if (output / "receipts").exists():
            _fail("publication_collision", "Receipt destination appeared; preserve and reconcile it")
        os.rename(staging, output / "receipts")  # Complete receipt bundle becomes visible last.
        packet._sync_dir(output)
        return result
    except (ContractError, OSError, KeyboardInterrupt) as exc:
        result.update(status="failed", finished_utc=_utc(), error={
            "code": getattr(exc, "code", "interrupted" if isinstance(exc, KeyboardInterrupt) else "io_error"),
            "message": str(exc) or "Capture interrupted"})
        # If publication itself completed before a durability error, leave the
        # directory intact: inspect will refuse the changed final capture pin.
        packet._replace_json(output / "capture.json", result)
        return result


def _verify_receipts(output, receipts, pins, result):
    _keys(result, ("schema", "capture_id", "created_utc", "finished_utc", "status", "request_sha256",
                   "command_sha256", "command", "process", "error", "artifact", "unknowns", "notes",
                   "observation_errors"), "successful capture record")
    if (result["schema"] != CAPTURE_SCHEMA or not isinstance(result["capture_id"], str)
            or not re.fullmatch(r"[0-9a-f]{32}", result["capture_id"])):
        _fail("capture_integrity", "Unsupported capture record version/identity")
    request = _request(packet._read(output / "request.json", MAX_REQUEST))
    before = packet.read_json(output / "inputs-before.json")
    after = packet.read_json(output / "inputs-after.json")
    source_raw = packet._read(receipts / "source.json", MAX_REQUEST * 8)
    source_pin, build_pin = pins["receipts/source.json"], pins["receipts/build.json"]
    checkpoint = {
        "source": {"status": "recorded", "commit": request["source_commit"], "manifest_sha256": source_pin["sha256"]},
        "build": {"status": "bound", "receipt_sha256": build_pin["sha256"],
                  "source_manifest_sha256": source_pin["sha256"], "artifact_sha256": pins["artifact.bin"]["sha256"]},
        "runtime": {"artifact_sha256": pins["artifact.bin"]["sha256"]},
        "evidence": {"source": {"status": "present", "path": "source.json"},
                     "build": {"status": "present", "path": "build.json"}},
    }
    packet._provenance(checkpoint, {"source.json": source_pin, "build.json": build_pin}, receipts)
    build = packet.read_json(receipts / "build.json")
    observed = result.get("process")
    if (source_raw != packet.canonical(before) or before != after
            or packet.read_json(output / "identities-before.json") != packet.read_json(output / "identities-after.json")
            or build["command"] != request["command"] or build["toolchain"] != request["toolchain"]
            or result.get("request_sha256") != pins["request.json"]["sha256"]
            or result.get("command_sha256") != packet.digest(packet.canonical(request["command"]))
            or result.get("command") != request["command"] or result.get("unknowns") != UNKNOWN
            or result.get("notes") != request["notes"] or result.get("error") is not None
            or result.get("observation_errors") != [] or not isinstance(observed, dict)
            or observed.get("status") != "exited" or type(observed.get("exit_code")) is not int
            or observed["exit_code"] != 0 or observed.get("child_reaped") is not True
            or observed.get("log_truncated") is not False
            or not isinstance(result.get("artifact"), dict)):
        _fail("capture_integrity", "Capture observations and compatible receipt binding differ")
    artifact = result["artifact"]
    _keys(observed, ("started_utc", "ended_utc", "exit_code", "status", "log_truncated", "child_reaped"), "successful child observation")
    if artifact != {"path": request["artifact"], "before": None, "after": pins["artifact.bin"],
                    "observation": "absent_before_present_after",
                    "before_observed_utc": artifact.get("before_observed_utc"),
                    "after_observed_utc": artifact.get("after_observed_utc")}:
        _fail("capture_integrity", "Artifact observation differs")
    times = [result.get("created_utc"), artifact.get("before_observed_utc"), observed.get("started_utc"),
             observed.get("ended_utc"), artifact.get("after_observed_utc"), result.get("finished_utc")]
    instants = [timestamp_key(value) for value in times]
    if sorted(instants) != instants:
        _fail("capture_integrity", "Observed timestamps are out of order; no refreshed build time is allowed")
    # Copies are scanned through the same finite closure rules. Extra files
    # outside declared roots are checked separately, without trusting a glob.
    if _scan(output / "inputs", request)[0] != before:
        _fail("capture_integrity", "Frozen source closure differs")
    identities = packet.read_json(output / "identities-before.json")
    expected = set()
    for name in identities:
        parts = packet.relative(name).split("/")
        expected.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    actual, entries = set(), 0
    def inventory(path):
        nonlocal entries
        with os.scandir(path) as iterator:
            for row in iterator:
                entries += 1
                if entries > MAX_ENTRIES:
                    _fail("capture_integrity", "Frozen input copy inventory exceeds limit")
                child = Path(row.path)
                packet._plain(child)
                actual.add(packet.relative(child.relative_to(output / "inputs").as_posix()))
                if row.is_dir(follow_symlinks=False):
                    inventory(child)
    inventory(output / "inputs")
    if actual != expected:
        _fail("capture_integrity", "Frozen input copies have missing/unexpected files")


def inspect_capture(output):
    """Verify the published bundle and retained bytes; never refresh timestamps."""
    output = packet._root(output)
    success = packet.read_json(packet._path(output, "receipts/success.json"))
    _keys(success, ("schema", "capture_id", "files"), "success marker")
    if success["schema"] != SUCCESS_SCHEMA or not isinstance(success["files"], dict):
        _fail("capture_integrity", "Unsupported success marker")
    expected = {"request.json", "capture.json", "inputs-before.json", "inputs-after.json",
                "identities-before.json", "identities-after.json", "artifact.bin", "command.log",
                "receipts/source.json", "receipts/build.json"}
    if set(success["files"]) != expected:
        _fail("capture_integrity", "Published evidence inventory differs")
    for name, pin in success["files"].items():
        limit = {"request.json": MAX_REQUEST, "command.log": MAX_LOG, "artifact.bin": MAX_ARTIFACT,
                 "receipts/source.json": MAX_REQUEST * 8, "receipts/build.json": MAX_REQUEST * 8}.get(name, packet.MAX_JSON_BYTES)
        if (not isinstance(pin, dict) or set(pin) != {"sha256", "bytes"}
                or not isinstance(pin["sha256"], str) or not packet.HASH.fullmatch(pin["sha256"])
                or type(pin["bytes"]) is not int or not 0 <= pin["bytes"] <= limit):
            _fail("capture_integrity", "Invalid published evidence pin: " + name)
        if _file(packet._path(output, name), limit)[0] != pin:
            _fail("capture_integrity", "Published evidence hash/size differs: " + name)
    result = packet.read_json(output / "capture.json")
    if not isinstance(result, dict) or result.get("status") != "captured" or result.get("capture_id") != success["capture_id"]:
        _fail("capture_integrity", "Final capture and success marker differ")
    if sorted(path.name for path in (output / "receipts").iterdir()) != ["build.json", "source.json", "success.json"]:
        _fail("capture_integrity", "Receipt bundle has unexpected/missing entries")
    _verify_receipts(output, output / "receipts", success["files"], result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    run = commands.add_parser("capture", help="Observe one explicitly declared command")
    run.add_argument("--request", required=True)
    run.add_argument("--workspace", required=True)
    run.add_argument("--output", required=True)
    check = commands.add_parser("inspect", help="Verify a complete capture without executing anything")
    check.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        value = (capture(args.request, args.workspace, args.output) if args.operation == "capture"
                 else inspect_capture(args.output))
        print(json.dumps(value, sort_keys=True, ensure_ascii=True))
        return 0 if value["status"] == "captured" else 3
    except (ContractError, OSError) as exc:
        print(json.dumps({"error": {"code": getattr(exc, "code", "io_error"), "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
