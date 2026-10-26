"""Engine-free authoring core for Interchange import test plans (Epic P1 candidate 1).

Turns a Blender hand-off spec, or an interchange_harness receiver profile, into an
ordered list of checks named after the installed UE 5.8 InterchangeTests functions
(Public/ImportTestFunctions/StaticMeshImportTestFunctions.h), and judges observed
results without the engine. Building the UInterchangeImportTestPlan asset and running
it is editor work for the custodian, in a disposable project only (never DaedalusRealm).

Rules:
- A plan with no checks is refused (no vacuous pass).
- A missing observation is a FAIL, never a skip.
- Every plan carries the source sha256 so a changed file cannot pass silently.
"""
import copy
import json
import re

SCHEMA = "daedalus.interchange_test_plan.v1"

# Function names exactly as in StaticMeshImportTestFunctions.h (UE 5.8).
CHECK_TRIANGLES = "CheckTriangleCount"
CHECK_SLOT_COUNT = "CheckMaterialSlotCount"
CHECK_SLOT_NAME = "CheckImportedMaterialSlotName"
CHECK_LODS = "CheckLodCount"
CHECK_UV_CHANNELS = "CheckUVChannelCount"
CHECK_SIMPLE_COLLISION = "CheckSimpleCollisionPrimitiveCount"

KNOWN = (CHECK_TRIANGLES, CHECK_SLOT_COUNT, CHECK_SLOT_NAME, CHECK_LODS,
         CHECK_UV_CHANNELS, CHECK_SIMPLE_COLLISION)

_SHA = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PROJECT = "daedalusrealm"


class PlanError(ValueError):
    pass


def _nonneg_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PlanError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def plan_from_spec(spec):
    """spec: {asset, source_path, sha256, project, expect:{triangles, slots, simple_collision, lods, uv_channels}}"""
    if not isinstance(spec, dict):
        raise PlanError("spec must be an object")
    asset = spec.get("asset")
    if not isinstance(asset, str) or not asset:
        raise PlanError("asset name required")
    sha = spec.get("sha256", "")
    if not isinstance(sha, str) or not _SHA.match(sha):
        raise PlanError("sha256 must be 64 lowercase hex characters")
    project = str(spec.get("project", ""))
    if not project:
        raise PlanError("project required (a disposable evaluation project)")
    if _FORBIDDEN_PROJECT in project.replace("\\", "/").lower():
        raise PlanError("test plans run in a disposable project only, never DaedalusRealm")
    expect = spec.get("expect") or {}
    checks = []
    if "triangles" in expect:
        checks.append({"function": CHECK_TRIANGLES, "lod": 0,
                       "expected": _nonneg_int(expect["triangles"], "triangles")})
    if "slots" in expect:
        slots = expect["slots"]
        if not isinstance(slots, list) or not all(isinstance(s, str) and s for s in slots):
            raise PlanError("slots must be a list of non-empty names")
        if len(set(slots)) != len(slots):
            raise PlanError("slot names must be unique")
        checks.append({"function": CHECK_SLOT_COUNT, "expected": len(slots)})
        for index, name in enumerate(slots):
            checks.append({"function": CHECK_SLOT_NAME, "slot": index, "expected": name})
    if "simple_collision" in expect:
        checks.append({"function": CHECK_SIMPLE_COLLISION,
                       "expected": _nonneg_int(expect["simple_collision"], "simple_collision")})
    if "lods" in expect:
        lods = _nonneg_int(expect["lods"], "lods")
        if lods < 1:
            raise PlanError("lods must be at least 1")
        checks.append({"function": CHECK_LODS, "expected": lods})
    if "uv_channels" in expect:
        checks.append({"function": CHECK_UV_CHANNELS, "lod": 0,
                       "expected": _nonneg_int(expect["uv_channels"], "uv_channels")})
    if not checks:
        raise PlanError("a plan needs at least one check")
    return {"schema": SCHEMA, "asset": asset, "source_path": spec.get("source_path", ""),
            "sha256": sha, "project": project, "checks": checks}


def plan_from_receiver_profile(profile, asset, project):
    """Derive a plan from an interchange_harness receiver profile (e.g. flagship_terrain_33.json)."""
    packet = profile.get("packet") or {}
    expect = profile.get("expect") or {}
    options = profile.get("interchange_requested_options") or {}
    spec_expect = {}
    if "triangles" in expect:
        spec_expect["triangles"] = expect["triangles"]
    if "slots" in expect:
        spec_expect["slots"] = list(expect["slots"])
    if options.get("collision") is False:
        spec_expect["simple_collision"] = 0
    return plan_from_spec({"asset": asset, "source_path": packet.get("path", ""),
                           "sha256": packet.get("sha256", ""), "project": project,
                           "expect": spec_expect})


def expected_fail_variant(plan, function, wrong_value):
    """A deterministic FAIL fixture: same plan, one expectation deliberately wrong."""
    if function not in KNOWN:
        raise PlanError("unknown check %r" % function)
    variant = copy.deepcopy(plan)
    hits = [c for c in variant["checks"] if c["function"] == function]
    if not hits:
        raise PlanError("plan has no %s check" % function)
    if hits[0]["expected"] == wrong_value:
        raise PlanError("wrong_value equals the real expectation")
    hits[0]["expected"] = wrong_value
    variant["expect_verdict"] = "FAIL"
    variant["expect_failing_check"] = function
    return variant


def _key(check):
    return "%s[%s]" % (check["function"], check.get("slot", check.get("lod", "")))


def evaluate(plan, observed):
    """observed: {"sha256": ..., "results": {key: value}} with keys like CheckTriangleCount[0]."""
    rows = []
    if observed.get("sha256") != plan["sha256"]:
        rows.append({"check": "source_sha256", "expected": plan["sha256"],
                     "observed": observed.get("sha256"), "pass": False})
    results = observed.get("results") or {}
    for check in plan["checks"]:
        key = _key(check)
        if key not in results:
            rows.append({"check": key, "expected": check["expected"], "observed": None, "pass": False})
            continue
        rows.append({"check": key, "expected": check["expected"], "observed": results[key],
                     "pass": results[key] == check["expected"]})
    verdict = "PASS" if rows and all(r["pass"] for r in rows) else "FAIL"
    return {"verdict": verdict, "rows": rows}


def keys(plan):
    return [_key(c) for c in plan["checks"]]


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(plan_from_spec(json.load(handle)), indent=2))
