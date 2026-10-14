# SPDX-License-Identifier: MIT
"""Bounded, read-only observations on the editor thread; no engine flushing.

The two warm-up / consecutive idle observations are independently implemented,
inspired by SPEAR's MIT async_loading_service at commit 6d5957f8. This module
uses only reflected Python predicates and never claims all rendering completed.
"""
import math
import time


DEFAULT_TIMEOUT = 10.0
MAX_TIMEOUT = 30.0
MAX_FRAMES = 1800
GAPS = {
    "async_loading": "No reflected global async-loading predicate in the audited Python API",
    "asset_compilation": "Asset compiling manager count is not a reflected Python API",
    "shader_compilation": "Shader job count is not a reflected Python API",
    "distance_fields": "Distance-field task count is not a reflected Python API",
    "texture_streaming": "Global texture streaming counts are not a reflected Python API",
    "streaming_levels": "No audited reflected enumeration of world streaming levels",
    "render_completion": "Editor ticks and idle observations are not a GPU/render fence",
}


def validate_timeout(value):
    if isinstance(value, bool):
        raise ValueError("readiness_timeout must be a finite number > 0 and <= 30 seconds")
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= MAX_TIMEOUT:
        raise ValueError("readiness_timeout must be a finite number > 0 and <= 30 seconds")
    return value


class ReadinessProbe:
    """Discover the finite capability set once and sample only read-only bools."""

    def __init__(self, api, world):
        self.checks = {name: {"supported": False, "state": "unsupported", "reason": reason}
                       for name, reason in GAPS.items()}
        self.predicates = {}
        self._resolve("asset_registry_initial_scan", lambda: self._asset_registry(api), False)
        self._resolve("world_partition", lambda: self._world_partition(api, world), True)

    @staticmethod
    def _asset_registry(api):
        helpers = getattr(api, "AssetRegistryHelpers", None)
        get = getattr(helpers, "get_asset_registry", None)
        if not callable(get):
            return None, "AssetRegistryHelpers.get_asset_registry is unavailable"
        registry = get()
        predicate = getattr(registry, "is_loading_assets", None)
        return predicate, "AssetRegistry.is_loading_assets is unavailable"

    @staticmethod
    def _world_partition(api, world):
        library = getattr(api, "SubsystemBlueprintLibrary", None)
        get = getattr(library, "get_world_subsystem", None)
        cls = getattr(api, "WorldPartitionSubsystem", None)
        if not callable(get) or cls is None or world is None:
            return None, "WorldPartitionSubsystem or its world-context accessor is unavailable"
        subsystem = get(world, cls)
        predicate = getattr(subsystem, "is_all_streaming_completed", None)
        return predicate, "WorldPartitionSubsystem is absent or its idle predicate is unavailable"

    def _resolve(self, name, resolve, idle_value):
        try:
            predicate, reason = resolve()
            if not callable(predicate):
                self.checks[name] = {"supported": False, "state": "unsupported", "reason": reason}
                return
            self.predicates[name] = (predicate, idle_value)
            self.checks[name] = {"supported": True, "state": "not_checked"}
        except Exception as e:
            # An exposed API failing to resolve is unknown, not silently unsupported.
            self.checks[name] = {"supported": True, "state": "error",
                                 "reason": "%s: %s" % (type(e).__name__, str(e)[:300])}

    def sample(self):
        for name, (predicate, idle_value) in self.predicates.items():
            try:
                value = predicate()
                if type(value) is not bool:
                    raise TypeError("readiness predicate did not return a bool")
                self.checks[name] = {"supported": True, "state": "idle" if value == idle_value else "busy",
                                     "value": value}
            except Exception as e:
                self.checks[name] = {"supported": True, "state": "error",
                                     "reason": "%s: %s" % (type(e).__name__, str(e)[:300])}
        observed = [c for c in self.checks.values() if c["supported"]]
        if any(c["state"] == "error" for c in observed):
            return "probe_error"
        if not observed:
            return "unsupported"
        return "idle" if all(c["state"] == "idle" for c in observed) else "busy"


def wait_for_readiness(api, world, timeout=DEFAULT_TIMEOUT, *, cancelled=lambda: False,
                       clock=time.monotonic, deadline=None, warmup_frames=2, fail_on_busy=False):
    """Yield editor ticks, then return a structured observation report.

    No sleeps, workers, global waits or engine mutations. After a capture, use
    warmup_frames=0 and fail_on_busy=True: a newly busy signal invalidates that
    image instead of approving an old image after more loading completes.
    """
    timeout = validate_timeout(timeout)
    start = clock()
    deadline = min(start + timeout, deadline) if deadline is not None else start + timeout
    frames, idle_frames = 0, 0
    probe = None

    def result(status):
        checks = probe.checks if probe else {
            **{n: {"supported": False, "state": "unsupported", "reason": r} for n, r in GAPS.items()},
            "asset_registry_initial_scan": {"supported": None, "state": "not_checked"},
            "world_partition": {"supported": None, "state": "not_checked"},
        }
        reasons = ["%s: %s" % (n, c.get("reason", c["state"]))
                   for n, c in checks.items() if c["state"] != "idle"]
        if status != "observed_idle":
            reasons.append("readiness condition not met: " + status)
        return {"schema_version": 1, "status": status, "condition_met": status == "observed_idle",
                "condition": "supported_checks_idle_for_two_consecutive_ticks",
                "all_rendering_complete": False, "coverage_complete": False,
                "warmup_frames": warmup_frames, "frames_waited": frames,
                "idle_frames_required": 2, "consecutive_idle_frames": idle_frames,
                "elapsed_seconds": round(max(0, clock() - start), 6),
                "supported_checks": [n for n, c in checks.items() if c["supported"] is True],
                "unsupported_checks": [n for n, c in checks.items() if c["supported"] is False],
                "checks": checks, "incomplete_reasons": reasons}

    def interrupted():
        if cancelled():
            return "cancelled"
        if clock() >= deadline:
            return "timeout"
        if frames >= MAX_FRAMES:
            return "frame_limit"
        return None

    for _ in range(warmup_frames):
        status = interrupted()
        if status:
            return result(status)
        yield
        frames += 1

    while True:
        # Each idle observation has its own tick after the warm-up ticks.
        status = interrupted()
        if status:
            return result(status)
        yield
        frames += 1
        status = interrupted()
        if status:
            return result(status)
        if probe is None:
            probe = ReadinessProbe(api, world)
        state = probe.sample()
        # Predicates themselves can consume time or trigger lifecycle changes.
        status = interrupted()
        if status:
            return result(status)
        if state in ("probe_error", "unsupported"):
            return result(state)
        if state == "busy":
            idle_frames = 0
            if fail_on_busy:
                return result("capture_invalidated")
        else:
            idle_frames += 1
            if idle_frames == 2:
                return result("observed_idle")
