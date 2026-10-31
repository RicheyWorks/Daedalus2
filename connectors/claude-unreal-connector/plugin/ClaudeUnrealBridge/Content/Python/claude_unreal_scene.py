# SPDX-License-Identifier: MIT
"""Scoped read-only value observations. No native object is retained between calls.

Paths/epochs are observation identities, not permanent IDs. Each page is a new read,
not an atomic multi-page snapshot; unloaded World Partition actors are not observed.
"""
import json
import math
import uuid

SCHEMA_VERSION = 1
MAX_ACTORS = 128
CONTEXT_KEYS = {"session_id", "world_path", "world_kind", "world_epoch"}
VECTOR_FIELDS = {"location", "rotation", "scale"}
ACTOR_FIELDS = VECTOR_FIELDS | {"parent_path", "selected", "components"}


class SceneWorldUnavailable(RuntimeError):
    pass


def _number(value, label):
    try:
        finite = math.isfinite(value)
    except (TypeError, OverflowError):
        finite = False
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite:
        raise ValueError("expected_schema: %s must be a finite number" % label)
    return value


def _path(value, label, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value:
        raise ValueError("expected_schema: %s must be a nonempty object path%s" %
                         (label, " or null" if nullable else ""))


class SceneCommands:
    def __init__(self, source, serialize):
        self.source, self.serialize = source, serialize
        self.session_id = uuid.uuid4().hex
        self.world_key, self.world_epoch = None, None

    def _read(self):
        world, kind, actors, selected = self.source()
        # UE's object repr includes the native object identity (PyWrapperObject.cpp).
        # Keep only values, avoiding a Python reference that could retain an old world.
        # This is an observed identity hint, not a native generation/lifetime guarantee.
        key = (kind, world.get_path_name(), repr(world))
        if key != self.world_key:
            self.world_key, self.world_epoch = key, uuid.uuid4().hex
        context = {"session_id": self.session_id, "world_path": key[1],
                   "world_kind": kind, "world_epoch": self.world_epoch}
        return context, actors, selected

    @staticmethod
    def _base(context=None):
        return {"schema_version": SCHEMA_VERSION, "context": context}

    def _observe(self, actor, selected, expected_path):
        value = self.serialize(actor, precise=True, selected=selected)
        # A partial/opaque/non-finite native value is unavailable, never an empty JSON substitute.
        json.dumps(value, allow_nan=False)
        if value["path"] != expected_path:
            raise ValueError("actor identity changed during observation: catalogued %r, observed %r" %
                             (expected_path, value["path"]))
        return value

    @staticmethod
    def _catalog(actors, folder=None):
        values, errors, duplicates = {}, [], set()
        error_count = 0
        for actor in actors:
            path = None
            try:
                path = actor.get_path_name()
                _path(path, "observed actor path")
                actor_folder = str(actor.get_folder_path())
                if folder and actor_folder != folder and not actor_folder.startswith(folder.rstrip("/") + "/"):
                    continue
                if path in values or path in duplicates:
                    values.pop(path, None)
                    duplicates.add(path)
                    raise ValueError("duplicate full actor path")
                values[path] = actor
            except Exception as e:
                error_count += 1
                if len(errors) < MAX_ACTORS:
                    errors.append({"path": path, "code": "AMBIGUOUS_ACTOR_PATH" if path in duplicates else
                                   "ACTOR_UNOBSERVABLE", "message": str(e)[:1000]})
        return values, errors, error_count, duplicates

    def snapshot(self, params):
        folder = params.get("folder")
        if folder is not None and not isinstance(folder, str):
            raise ValueError("expected_schema: folder must be a string or null")
        offset, limit = params.get("offset", 0), params.get("limit", 32)
        if (type(offset) is not int or offset < 0 or type(limit) is not int or
                not 1 <= limit <= MAX_ACTORS):
            raise ValueError("expected_schema: offset >= 0; limit in 1..%d" % MAX_ACTORS)
        scope = {"loaded_only": True, "atomic": False, "folder": folder,
                 "offset": offset, "limit": limit, "total_loaded": None,
                 "total_matching": None, "matched_known": 0, "returned": 0, "complete": False,
                 "next_offset": None, "error_count": 0, "errors_truncated": False}
        try:
            context, actors, selected = self._read()
        except Exception as e:
            return dict(self._base(), available=False,
                        code="WORLD_UNAVAILABLE" if isinstance(e, SceneWorldUnavailable) else "OBSERVATION_UNAVAILABLE",
                        message=str(e)[:1000],
                        scope=scope, actors=[], errors=[])
        by_path, errors, error_count, _duplicates = self._catalog(actors, folder)
        catalog_error_count = error_count
        matches = sorted(by_path.items())
        page = matches[offset:offset + limit]
        values = []
        for path, actor in page:
            try:
                values.append(self._observe(actor, selected, path))
            except Exception as e:
                error_count += 1
                if len(errors) < MAX_ACTORS:
                    errors.append({"path": path, "code": "ACTOR_UNAVAILABLE", "message": str(e)[:1000]})
        end = offset + len(page)
        scope.update(total_loaded=len(actors), total_matching=None if catalog_error_count else len(matches),
                     matched_known=len(matches), returned=len(values), error_count=error_count,
                     errors_truncated=error_count > len(errors),
                     complete=offset == 0 and len(values) == len(matches) and not errors,
                     next_offset=end if end < len(matches) else None)
        return dict(self._base(context), available=True, scope=scope, actors=values, errors=errors)

    @staticmethod
    def _validate(params):
        if type(params.get("schema_version")) is not int or params["schema_version"] != SCHEMA_VERSION:
            raise ValueError("expected_schema: schema_version must be 1")
        context = params.get("context")
        if (not isinstance(context, dict) or set(context) != CONTEXT_KEYS or
                any(not isinstance(v, str) or not v for v in context.values())):
            raise ValueError("expected_schema: context must be the complete snapshot context")
        actors = params.get("actors")
        if not isinstance(actors, list) or not 1 <= len(actors) <= MAX_ACTORS:
            raise ValueError("expected_schema: actors must contain 1..%d checks" % MAX_ACTORS)
        seen = set()
        for item in actors:
            if not isinstance(item, dict) or set(item) != {"path", "expected"}:
                raise ValueError("expected_schema: actor check requires path and expected")
            _path(item["path"], "actor path")
            if item["path"] in seen:
                raise ValueError("expected_schema: duplicate actor check path")
            seen.add(item["path"])
            expected = item["expected"]
            if not isinstance(expected, dict) or not expected or not set(expected) <= ACTOR_FIELDS:
                raise ValueError("expected_schema: expected requires supported nonempty predicates")
            for field in VECTOR_FIELDS & set(expected):
                value = expected[field]
                if not isinstance(value, list) or len(value) != 3:
                    raise ValueError("expected_schema: %s must have three numbers" % field)
                for n in value:
                    _number(n, field)
            if "parent_path" in expected:
                _path(expected["parent_path"], "parent_path", nullable=True)
            if "selected" in expected and type(expected["selected"]) is not bool:
                raise ValueError("expected_schema: selected must be boolean")
            if "components" in expected:
                components = expected["components"]
                if not isinstance(components, list) or len(components) > MAX_ACTORS:
                    raise ValueError("expected_schema: components must be a bounded list")
                component_paths = set()
                for component in components:
                    if (not isinstance(component, dict) or "path" not in component or
                            not set(component) <= {"path", "mesh", "materials"} or len(component) < 2):
                        raise ValueError("expected_schema: component requires path and mesh/materials")
                    _path(component["path"], "component path")
                    if component["path"] in component_paths:
                        raise ValueError("expected_schema: duplicate component check path")
                    component_paths.add(component["path"])
                    if "mesh" in component:
                        _path(component["mesh"], "mesh", nullable=True)
                    if "materials" in component:
                        materials = component["materials"]
                        if not isinstance(materials, list) or len(materials) > MAX_ACTORS:
                            raise ValueError("expected_schema: materials must be a bounded slot list")
                        for material in materials:
                            _path(material, "material", nullable=True)
        tolerance = params.get("tolerance", {})
        if not isinstance(tolerance, dict) or not set(tolerance) <= VECTOR_FIELDS:
            raise ValueError("expected_schema: tolerance supports location/rotation/scale")
        for field, value in tolerance.items():
            if _number(value, field + " tolerance") < 0:
                raise ValueError("expected_schema: tolerances must be nonnegative")

    def verify(self, params):
        self._validate(params)  # Reject malformed checks before reading any native object.
        try:
            context, actors, selected = self._read()
        except Exception as e:
            return dict(self._base(), passed=False,
                        code="WORLD_UNAVAILABLE" if isinstance(e, SceneWorldUnavailable) else "OBSERVATION_UNAVAILABLE",
                        message=str(e)[:1000], checks=[])
        if context != params["context"]:
            return dict(self._base(context), passed=False, code="STALE_CONTEXT", checks=[])
        by_path, observation_errors, error_count, duplicates = self._catalog(actors)
        checks = []
        for item in params["actors"]:
            path, expected = item["path"], item["expected"]
            actor = by_path.get(path)
            if actor is None:
                code = "AMBIGUOUS_ACTOR_PATH" if path in duplicates else "ACTOR_UNOBSERVABLE" if error_count else "ACTOR_NOT_LOADED"
                checks.append({"path": path, "status": "unavailable", "code": code,
                               "observed": None, "mismatches": []})
                continue
            try:
                observed = self._observe(actor, selected, path)
            except Exception as e:
                checks.append({"path": path, "status": "unavailable", "code": "ACTOR_UNAVAILABLE",
                               "message": str(e)[:1000], "observed": None, "mismatches": []})
                continue
            mismatches = self._compare(expected, observed, params.get("tolerance", {}))
            checks.append({"path": path, "status": "mismatch" if mismatches else "match",
                           "observed": observed, "mismatches": mismatches})
        return dict(self._base(context), passed=all(c["status"] == "match" for c in checks), checks=checks,
                    observation_errors=observation_errors, error_count=error_count,
                    errors_truncated=error_count > len(observation_errors))

    @staticmethod
    def _compare(expected, observed, tolerance):
        mismatches = []

        def mismatch(predicate, want, actual, code=None):
            entry = {"predicate": predicate, "expected": want, "observed": actual}
            if code is not None:
                entry["code"] = code
            mismatches.append(entry)

        for field in VECTOR_FIELDS & set(expected):
            actual, want = observed[field], expected[field]
            differences = [abs(a - b) for a, b in zip(actual, want)]
            if field == "rotation":
                differences = [abs((a - b + 180) % 360 - 180) for a, b in zip(actual, want)]
            if any(not math.isfinite(d) or d > tolerance.get(field, 0) for d in differences):
                mismatch(field, want, actual)
        for field in ("parent_path", "selected"):
            if field in expected and observed[field] != expected[field]:
                mismatch(field, expected[field], observed[field])
        if "components" in expected:
            by_path = {c["path"]: c for c in observed["components"]}
            for component in expected["components"]:
                actual = by_path.get(component["path"])
                for field in ("mesh", "materials"):
                    if field in component and (actual is None or field not in actual or actual[field] != component[field]):
                        mismatch("components.%s.%s" % (component["path"], field), component[field],
                                 actual.get(field) if actual is not None else None,
                                 "COMPONENT_NOT_LOADED" if actual is None else
                                 "UNSUPPORTED_COMPONENT_FIELD" if field not in actual else None)
            if not expected["components"] and observed["components"]:
                mismatch("components", [], observed["components"])
        return mismatches
