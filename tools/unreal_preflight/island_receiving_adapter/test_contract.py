# SPDX-License-Identifier: MIT
"""Contract tests for the PROPOSED island receiving adapter. Synthetic data only; no Codex code is imported."""
import ast
import copy
import unittest
from pathlib import Path

import contract as c

SHA = "a" * 64


def pin(name, size=None):
    p = {"path": "C:/SYNTHETIC/" + name, "sha256": SHA}
    if size is not None:
        p["bytes"] = size
    return p


def request(generation=0):
    seed = 10392 + generation
    item = {"seed": seed, "source_id": "synthetic-%d" % seed, "source": pin("source.glb", 29),
            "sidecar": pin("sidecar.json", 3), "destination": "/Synthetic/Island%d" % seed}
    return {"schema": "island-receiving-invocation/v1", "session_id": "synthetic-session-1",
            "invocation_id": "synthetic-session-1:%d" % generation, "generation": generation, "seed": seed,
            "receiving_owner": "mock-owner-1",
            "window": {"not_before_utc": "2030-01-02T11:59:00+00:00", "expires_utc": "2030-01-02T13:00:00+00:00"},
            "editor_generation": {"pid": 12345, "start_utc": "2030-01-02T11:00:00+00:00"}, "item": item,
            "expected_world": "/Synthetic/World", "protected_manifest": pin("protected.json"),
            "recipe_pins": [pin("recipe.py")], "receiving_adapter_required": True,
            "legacy_run_seed_is_directly_safe": False, "automatic_restart": False, "automatic_lease_mutation": False,
            "execution_mode": "mock", "native_admission": False}


def preflight(req):
    owner = req["receiving_owner"]
    return {"schema": "island-mock-preflight/v1", "execution_mode": "mock", "native_admission": False,
            "observed_utc": "2030-01-02T12:00:00+00:00", "session_id": req["session_id"], "generation": req["generation"],
            "receiving_owner": owner, "lease_holders": {"compute": owner, "unreal": owner},
            "editor_generation": req["editor_generation"], "world": req["expected_world"], "single_writer": True,
            "editor_idle": True, "other_producers": [], "dirty": {"maps": [], "content": []},
            "bridge": {"queue": 0, "remote_locked": False, "other_running": [], "unfinished_async": []},
            "play": False, "native_import_active": False, "sequence_open": False, "movie_executor": False,
            "stop_requested": False, "resources": {"available_physical_bytes": 1740800000,
                                                   "available_commit_bytes": 2252800000, "free_disk_bytes": 10 * 1024 ** 3},
            "editor_private_bytes": 1024, "source_target_binding": req["item"], "source_target_verified": True,
            "protected_manifest_sha256": req["protected_manifest"]["sha256"], "protected_bytes_verified": True,
            "recipe_pins_verified": req["recipe_pins"]}


def result(req):
    value = {k: (1 if k in ("imported", "saved", "admitted") else 0) for k in c.TOTAL_KEYS}
    value.update(schema="island-mock-result/v1", simulated=True, native_admission=False, known_terminal=True,
                 pending_native_operations=False, session_id=req["session_id"], invocation_id=req["invocation_id"],
                 seed=req["seed"], request_sha256=c.request_sha256(req),
                 recipe_checks={k: True for k in c.RECIPE_CHECK_KEYS},
                 preservation={k: True for k in c.PRESERVATION_KEYS})
    return value


def legacy_action(req, admitted=True):
    """Synthetic object with the key set of the legacy AdmitSavedWholeIsland `value`."""
    report = {"name": "Synthetic", "source": req["item"]["source"], "derived": pin("derived.glb", 10),
              "sidecar": req["item"]["sidecar"], "asset": "/Synthetic/Island/Mesh.Mesh", "saved": True,
              "source_visible_instances": 3, "native_meshes": 1, "limitations": [],
              "source_factor_bindings_match": True, "vertex_colour_sample_matches": True,
              "validation": {"status": "Valid", "native_invoked": True, "accepted": True}, "admitted": admitted}
    return {"prepared": 1, "imported": 1, "saved": 1, "admitted": int(admitted), "held": int(not admitted), "reused": 0,
            "failed": 0, "source_instances": 3, "source_triangles": 100, "native_triangles": 100,
            "geometry_matches": True, "material_mapping_matches": True, "items": [report],
            "created_assets": ["/Synthetic/Island/Mesh.Mesh"], "native_import_active": False,
            "preservation": {"world": True, "actors": True, "camera": True, "selection": True, "clean": True},
            "dirty": {"maps": [], "content": []}}


class RequestContract(unittest.TestCase):
    def test_exact_build_request_key_set(self):
        self.assertEqual(set(request()), c.REQUEST_KEYS)
        self.assertEqual(c.validate_request(request()), request())

    def test_safety_flags_and_native_mode_refused(self):
        for key, value in (("receiving_adapter_required", False), ("legacy_run_seed_is_directly_safe", True),
                           ("automatic_restart", True), ("automatic_lease_mutation", True),
                           ("native_admission", True), ("execution_mode", "native")):
            r = request()
            r[key] = value
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.validate_request(r)

    def test_item_seed_and_invocation_binding(self):
        r = request()
        r["item"]["seed"] = 10393
        with self.assertRaises(c.ContractError):
            c.validate_request(r)
        r = request()
        r["invocation_id"] = "other:0"
        with self.assertRaises(c.ContractError):
            c.validate_request(r)
        r = request()
        r["extra"] = 1  # no invented fields
        with self.assertRaises(c.ContractError):
            c.validate_request(r)


class PreflightContract(unittest.TestCase):
    def test_mock_guard_shape_accepted(self):
        r = request()
        self.assertEqual(set(preflight(r)), c.PREFLIGHT_KEYS)
        c.validate_preflight_shape(r, preflight(r))

    def test_binding_differences_refused(self):
        r = request()
        for key, value in (("receiving_owner", "wrong"), ("lease_holders", {"compute": "x", "unreal": "x"}),
                           ("generation", 1), ("world", "/Other"), ("native_admission", True),
                           ("source_target_binding", dict(r["item"], destination="/Other")),
                           ("recipe_pins_verified", [])):
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.validate_preflight_shape(r, dict(preflight(r), **{key: value}))
        with self.assertRaises(c.ContractError):
            c.validate_preflight_shape(r, dict(preflight(r), extra=True))


class ResultContract(unittest.TestCase):
    def test_mock_receipt_shape_accepted(self):
        r = request()
        self.assertEqual(set(result(r)), c.RESULT_KEYS)
        c.validate_result(r, result(r))

    def test_partial_held_unknown_or_mismatched_refused(self):
        r = request()
        changes = [("saved", 0), ("held", 1), ("failed", 1), ("reused", 1), ("known_terminal", False),
                   ("pending_native_operations", True), ("native_admission", True), ("simulated", False),
                   ("seed", 10393), ("request_sha256", SHA), ("invocation_id", "x:0"),
                   ("recipe_checks", dict({k: True for k in c.RECIPE_CHECK_KEYS}, geometry_matches=False)),
                   ("preservation", {k: True for k in c.PRESERVATION_KEYS if k != "source"})]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.validate_result(r, dict(result(r), **{key: value}))

    def test_request_hash_binds_whole_request(self):
        r = request()
        tampered = copy.deepcopy(r)
        tampered["receiving_owner"] = "other-owner"
        with self.assertRaises(c.ContractError):
            c.validate_result(tampered, result(r))


class LegacyMapping(unittest.TestCase):
    def test_checks_map_but_open_fields_keep_result_refused(self):
        r = request()
        candidate, open_ids = c.map_legacy_action(r, legacy_action(r), known_terminal_observed=True)
        self.assertEqual(candidate["recipe_checks"], {k: True for k in c.RECIPE_CHECK_KEYS})
        self.assertNotIn("source", candidate["preservation"])          # never defaulted
        self.assertNotIn("pending_native_operations", candidate)      # never defaulted
        self.assertNotIn("request_sha256", candidate)                 # never invented
        for oid in ("OPEN-preservation-source", "OPEN-pending", "OPEN-identity", "OPEN-native-schema"):
            self.assertIn(oid, open_ids)
            self.assertIn(oid, c.OPEN)
        with self.assertRaises(c.ContractError):
            c.validate_result(r, candidate)

    def test_known_terminal_is_open_without_journal_observation(self):
        r = request()
        candidate, open_ids = c.map_legacy_action(r, legacy_action(r), known_terminal_observed=False)
        self.assertNotIn("known_terminal", candidate)
        self.assertIn("OPEN-known-terminal", open_ids)

    def test_legacy_held_island_maps_to_held(self):
        r = request()
        candidate, _ = c.map_legacy_action(r, legacy_action(r, admitted=False), True)
        self.assertEqual((candidate["admitted"], candidate["held"]), (0, 1))

    def test_dirty_busy_or_wrong_source_refused(self):
        r = request()
        for mutate in (lambda a: a.update(dirty={"maps": ["/x"], "content": []}),
                       lambda a: a.update(native_import_active=True),
                       lambda a: a["items"][0].update(source=dict(r["item"]["source"], sha256="b" * 64)),
                       lambda a: a.update(items=[]),
                       lambda a: a.pop("preservation")):
            a = legacy_action(r)
            mutate(a)
            with self.assertRaises(c.ContractError):
                c.map_legacy_action(r, a, True)


class StubAndScope(unittest.TestCase):
    def test_proposed_native_adapter_refuses(self):
        adapter = c.ProposedNativeAdapter()
        self.assertEqual(adapter.status, "PROPOSED-for-Boss-review")
        for call in (adapter.preflight, adapter.invoke):
            with self.assertRaises(NotImplementedError):
                call(request())

    def test_contract_module_has_no_io_or_side_effect_imports(self):
        tree = ast.parse(Path(c.__file__).read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                 for a in (n.names if isinstance(n, ast.Import) else [type("m", (), {"name": n.module or ""})])}
        self.assertFalse(names & {"os", "subprocess", "urllib", "socket", "shutil", "pathlib", "importlib", "unreal"})


if __name__ == "__main__":
    unittest.main()