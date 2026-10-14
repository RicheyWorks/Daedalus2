# SPDX-License-Identifier: MIT
"""One-shot diagnostics with explicit source, time, availability and uncertainty.

No UI automation, application control, watcher, admission policy or TMOG private
API. Windows system memory is read directly from PSAPI. Existing vitals records
can be normalized without executing their collector. TMOG artifacts are opaque
imports until a supported export contract has actually been verified.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

SCHEMA_VERSION = 1
UNITS = {
    "physical_total_bytes": "bytes",
    "physical_available_bytes": "bytes",
    "committed_bytes": "bytes",
    "commit_limit_bytes": "bytes",
    "cpu_pct": "percent",
    "ram_pct": "percent",
    "editor_resident_bytes": "bytes",
    "gpu_pct": "percent",
}
AVAILABILITY = frozenset(("available", "unavailable", "unsupported", "failed"))
PROVENANCE = frozenset(("live", "imported"))
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc)


def _utc(value):
    """Reject naive times; never infer the machine's timezone for an import."""
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def _iso(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z") if value else None


def _number(value, unit):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0 and (unit != "percent" or value <= 100)
    except OverflowError:
        return False


def _identity(value):
    """A provider token or process PID plus creation time, never loose equality."""
    if isinstance(value, str) and value.strip() and len(value) <= 256:
        return ("token", value)
    if isinstance(value, Mapping) and set(value) == {"pid", "created_at"}:
        pid, created = value["pid"], value["created_at"]
        if (type(pid) is int and 0 < pid <= 0xFFFFFFFF and isinstance(created, str)
                and _utc(created) is not None):
            return ("process", pid, _iso(_utc(created)))
    return None


def snapshot(provider_id, metrics, *, provenance, sampled_at, observed_at,
             availability="available", reason=None, instance_id=None,
             expected_instance_id=None, max_age_seconds=30):
    """Normalize only supported metrics; unavailable/stale values are always null.

    Age equal to the freshness budget is stale. Future or missing source times
    are unknown, even if an imported file was just read. Instance matching is
    explicit: a nonempty provider token or a mapping containing exactly `pid`
    (positive integer) and `created_at` (aware timestamp string). Process times
    compare in UTC; PID alone, booleans and empty identifiers cannot match.
    """
    observed = _utc(observed_at)
    if observed is None:
        raise ValueError("observed_at must be an aware timestamp")
    if (not isinstance(availability, str) or availability not in AVAILABILITY or
            not isinstance(provenance, str) or provenance not in PROVENANCE):
        raise ValueError("invalid availability or provenance")
    if not isinstance(provider_id, str) or not provider_id or len(provider_id) > 128:
        raise ValueError("invalid provider_id")
    if not _number(max_age_seconds, "seconds") or max_age_seconds == 0:
        raise ValueError("max_age_seconds must be finite and positive")
    if not isinstance(metrics, Mapping):
        raise ValueError("metrics must be a mapping")
    captured = _utc(sampled_at)
    age = (observed - captured).total_seconds() if captured else None
    actual_identity = _identity(instance_id)
    expected_identity = _identity(expected_instance_id)
    if ((instance_id is not None and actual_identity is None) or
            (expected_instance_id is not None and
             (expected_identity is None or actual_identity != expected_identity))):
        availability, reason = "unavailable", "instance_mismatch"
    if availability != "available":
        freshness = "unavailable"
    elif age is None or age < 0:
        freshness = "unknown"
    elif age >= max_age_seconds:
        freshness = "stale"
    else:
        freshness = "current"
    normalized = {}
    for name, unit in UNITS.items():
        value = metrics.get(name)
        if availability != "available":
            status = "unsupported" if availability == "unsupported" else "unavailable"
        elif name not in metrics or value is None:
            status = "missing"
        elif not _number(value, unit):
            status = "invalid"
        else:
            status = freshness
        normalized[name] = {"value": value if status == "current" else None,
                            "unit": unit, "status": status}
    return {
        "schema_version": SCHEMA_VERSION,
        "provider_id": provider_id,
        "availability": availability,
        "reason": reason,
        "provenance": provenance,
        "sampled_at": _iso(captured),
        "observed_at": _iso(observed),
        "age_seconds": age if age is not None and age >= 0 else None,
        "max_age_seconds": max_age_seconds,
        "freshness": freshness,
        "instance_id": (actual_identity[1] if actual_identity[0] == "token" else
                        {"pid": actual_identity[1], "created_at": actual_identity[2]})
                       if actual_identity is not None else None,
        "metrics": normalized,
        "capabilities": {"minimized_live_read": "unverified"},
    }


def from_vitals(payload, *, observed_at, sampled_at=None, collector_ok=True,
                max_age_seconds=30):
    """Normalize an existing OS vitals record, never label it TMOG telemetry.

    Its legacy `when` is usually naive and therefore cannot establish freshness.
    collector_ok=False refuses partial output from a failed collection. The top
    twelve processes cannot establish editor absence or a process incarnation.
    Raw GPU CSV and cumulative CPU seconds are intentionally not translated.
    """
    if not isinstance(payload, Mapping) or collector_ok is not True:
        return snapshot("windows_vitals", {}, provenance="imported", sampled_at=None,
                        observed_at=observed_at, availability="failed", reason="collection_failed",
                        max_age_seconds=max_age_seconds)
    values = {}
    total, free = payload.get("total_mb"), payload.get("free_mb")
    if (_number(total, "bytes") and total > 0 and _number(free, "bytes") and free <= total):
        values["physical_total_bytes"] = total * 1024 * 1024
        values["physical_available_bytes"] = free * 1024 * 1024
        values["ram_pct"] = 100 * (total - free) / total
    values["cpu_pct"] = payload.get("cpu_pct")
    # Require a structurally valid process list; do not trust a derived editor_mb
    # with no matching row, and do not select one of several editor processes.
    rows = payload.get("top")
    if isinstance(rows, list) and all(isinstance(row, Mapping) for row in rows):
        editors = [row for row in rows if isinstance(row.get("ProcessName"), str)
                   and row["ProcessName"].lower().startswith("unrealeditor")]
        if len(editors) == 1 and _number(editors[0].get("mb"), "bytes"):
            values["editor_resident_bytes"] = editors[0]["mb"] * 1024 * 1024
    return snapshot("windows_vitals", values, provenance="imported",
                    sampled_at=sampled_at if sampled_at is not None else payload.get("when"),
                    observed_at=observed_at, max_age_seconds=max_age_seconds)


def _windows_memory():
    """GetPerformanceInfo counts are pages; convert with its returned page size."""
    from ctypes import wintypes

    class PerformanceInfo(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal",
                "PhysicalAvailable", "SystemCache", "KernelTotal", "KernelPaged",
                "KernelNonpaged", "PageSize")] + [
            (name, wintypes.DWORD) for name in ("HandleCount", "ProcessCount", "ThreadCount")]

    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_info = psapi.GetPerformanceInfo
    get_info.argtypes = [ctypes.POINTER(PerformanceInfo), wintypes.DWORD]
    get_info.restype = wintypes.BOOL
    info = PerformanceInfo()
    info.cb = ctypes.sizeof(info)
    if not get_info(ctypes.byref(info), info.cb):
        raise OSError(ctypes.get_last_error(), "GetPerformanceInfo failed")
    if info.PageSize <= 0 or info.PhysicalTotal <= 0 or info.PhysicalAvailable > info.PhysicalTotal:
        raise ValueError("invalid physical memory counters")
    if info.CommitLimit <= 0 or info.CommitTotal > info.CommitLimit:
        raise ValueError("invalid commit counters")
    return {
        "physical_total_bytes": info.PhysicalTotal * info.PageSize,
        "physical_available_bytes": info.PhysicalAvailable * info.PageSize,
        "committed_bytes": info.CommitTotal * info.PageSize,
        "commit_limit_bytes": info.CommitLimit * info.PageSize,
        "ram_pct": 100 * (info.PhysicalTotal - info.PhysicalAvailable) / info.PhysicalTotal,
    }


def collect_windows(*, observed_at=None):
    """One system-memory read; no subprocess, top-process scan or policy action."""
    if os.name != "nt":
        now = observed_at if observed_at is not None else _now()
        return snapshot("windows_psapi", {}, provenance="live", sampled_at=None,
                        observed_at=now, availability="unsupported", reason="windows_only")
    try:
        values = _windows_memory()
    except (OSError, ValueError):
        now = observed_at if observed_at is not None else _now()
        return snapshot("windows_psapi", {}, provenance="live", sampled_at=None,
                        observed_at=now, availability="failed", reason="collection_failed")
    # Capture time comes from the post-read clock. A caller's observation time
    # may compare ages but cannot relabel a live measurement as historical data.
    captured = _now()
    observed = observed_at if observed_at is not None else captured
    result = snapshot("windows_psapi", values, provenance="live", sampled_at=captured, observed_at=observed)
    result["capabilities"]["minimized_live_read"] = "not_applicable"
    return result


def tmog_snapshot(*, observed_at):
    return snapshot("tmog", {}, provenance="live", sampled_at=None,
                    observed_at=observed_at, availability="unavailable",
                    reason="live_binding_unverified")


def artifact_snapshot(path, *, observed_at, sampled_at=None, max_bytes=MAX_ARTIFACT_BYTES):
    """Hash one explicitly selected opaque import; do not expose its contents.

    No recursive scan, export parser or mtime-as-capture-time assumption. Bound
    both the size check and streaming read, and reject links/nonregular files.
    """
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 0 < max_bytes <= MAX_ARTIFACT_BYTES:
        raise ValueError("invalid artifact byte budget")
    result = snapshot("tmog_artifact", {}, provenance="imported", sampled_at=sampled_at,
                      observed_at=observed_at, availability="unavailable", reason="artifact_unverified")
    try:
        selected = Path(path)
        initial = selected.lstat()
        if not stat.S_ISREG(initial.st_mode) or selected.is_symlink():
            result["reason"] = "not_regular_file"
            return result
        if initial.st_size > max_bytes:
            result["reason"] = "artifact_too_large"
            return result
        digest, size = hashlib.sha256(), 0
        with selected.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino):
                result["reason"] = "artifact_changed"
                return result
            while True:
                chunk = stream.read(min(65536, max_bytes - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    result["reason"] = "artifact_too_large"
                    return result
                digest.update(chunk)
            final = os.fstat(stream.fileno())
        after = selected.lstat()
        if ((opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) !=
                (final.st_size, final.st_mtime_ns, final.st_ctime_ns) or size != final.st_size or
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns, final.st_ctime_ns)):
            result["reason"] = "artifact_changed"
            return result
    except (OSError, ValueError):
        result["reason"] = "artifact_unreadable"
        return result
    suffix = selected.suffix.lower()
    kind = {".tmogtrace": "opaque_trace", ".txt": "unverified_text_export",
            ".png": "unverified_image", ".jpg": "unverified_image",
            ".jpeg": "unverified_image"}.get(suffix, "opaque_file")
    result["artifact"] = {"availability": "available", "kind": kind, "size_bytes": size, "sha256": digest.hexdigest(),
                          "schema_verified": False}
    # The artifact itself is available; live metrics and capture time are not.
    result["reason"] = "opaque_import_no_metric_binding"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, help="explicit local TMOG artifact; metadata only")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    providers = [collect_windows(), tmog_snapshot(observed_at=now)]
    if args.artifact is not None:
        providers.append(artifact_snapshot(args.artifact, observed_at=now))
    print(json.dumps({"schema_version": SCHEMA_VERSION, "providers": providers}, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
