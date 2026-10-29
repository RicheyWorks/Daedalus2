# SPDX-License-Identifier: MIT
"""Contract tests for the island receiving adapter (mock path + R27-aligned native path). Synthetic data only;
no Codex code is imported. Native fixtures copy the key set of a real R27 batch-complete.json (Island10403)."""
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


def request(generation=0, mode="mock"):
    seed = 10392 + generation
    owner = c.RUNTIME_CUSTODIAN if mode == "native" else "mock-owner-1"
    world = "/Synthetic/World" if mode == "mock" else c.native_world("/Game/Synthetic/World")
    dest = "/Synthetic/Island%d" % seed if mode == "mock" else "/Game/Synthetic/Islands/Island%d" % seed
    item = {"seed": seed, "source_id": "synthetic-%d" % seed, "source": pin("source.glb", 29),
            "sidecar": pin("sidecar.json", 3), "destination": dest}
    return {"schema": "island-receiving-invocation/v1", "session_id": "synthetic-session-1",
            "invocation_id": "synthetic-session-1:%d" % generation, "generation": generation, "seed": seed,
            "receiving_owner": owner,
            "window": {"not_before_utc": "2030-01-02T11:59:00+00:00", "expires_utc": "2030-01-02T13:00:00+00:00"},
            "editor_generation": {"pid": 12345, "start_utc": "2030-01-02T11:00:00+00:00"}, "item": item,
            "expected_world": world, "protected_manifest": pin("protected.json"),
            "recipe_pins": [pin("recipe.py")], "receiving_adapter_required": True,
            "legacy_run_seed_is_directly_safe": False, "automatic_restart": False, "automatic_lease_mutation": False,
            "execution_mode": mode, "native_admission": False}


def preflight(req):
    owner = req["receiving_owner"]
    return {"schema": "island-mock-preflight/v1", "execution_mode": req["execution_mode"], "native_admission": False,
            "observed_utc": "2030-01-02T12:00:00+00:00", "session_id": req["session_id"], "generation": req["generation"],
            "receiving_owner": owner, "lease_holders": {"compute": owner, "unreal": owner},
            "editor_generation": req["editor_generation"], "world": req["expected_world"], "single_writer": True,
            "editor_idle": True, "other_producers": [], "dirty": {"maps": [], "content": []},
            "bridge": {"queue": 0, "remote_locked": False, "other_running": [], "unfinished_async": []},
            "play": False, "native_import_active": False, "sequence_open": False, "movie_executor": False,
            "stop_requested": False, "resources": {"available_physical_bytes": 1740800000,
                                                   "available_commit_bytes": 2252800000, "free_disk_bytes": 30 * 1024 ** 3},
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


# ----- native fixtures (R27 batch-complete.json key set) -----
PID = 12345


def r27_receipt(req, admitted=True):
    dest = req["item"]["destination"]
    stem = "Island%d" % req["seed"]
    asset = "%s/%s.%s" % (dest, stem, stem)
    report = {"name": stem, "source": req["item"]["source"], "derived": pin("derived.glb", 10),
              "sidecar": req["item"]["sidecar"], "asset": asset, "saved": True, "source_visible_instances": 3,
              "native_meshes": 1, "limitations": [], "source_to_native_material_names": {}, "source_triangles": 100,
              "native_triangles": 100, "geometry_matches": True, "material_mapping_matches": True, "slots": 1,
              "bounds_cm": [1, 1, 1], "vertex_colour_readback": {}, "source_factor_bindings_match": True,
              "vertex_colour_sample_matches": True, "admitted": admitted,
              "validation": {"status": "Valid", "native_invoked": True, "accepted": True, "cancellation_observed": False,
                             "native_return": 0}}
    if not admitted:
        report["validation"] = {"status": "Invalid", "native_invoked": True, "accepted": False}
    action = {"prepared": 1, "imported": 1, "saved": 1, "admitted": int(admitted), "held": int(not admitted), "reused": 0,
              "failed": 0, "items": [report], "held_before_import": [], "reused_items": [],
              "preservation": {"world": True, "actors": True, "camera": True, "selection": True, "clean": True},
              "native_import_active": False, "created_assets": [asset], "dirty": {"maps": [], "content": []}}
    saved_path = "C:/Unreal/DaedalusRealm/Content/" + dest.replace("/Game/", "", 1) + "/%s.uasset" % stem
    return {"utc": "2030-01-02T12:05:00+00:00", "manifest": None, "scope": None,
            "result": {"pid": PID, "action": action, "known_terminal": True,
                       "bridge_after": {"queue": 0, "remote_locked": False, "other_running": [], "unfinished_async": []}},
            "saved_files": [{"path": saved_path, "bytes": 10, "sha256": SHA}]}


def live(utc):
    return {"observed_utc": utc, "pid": PID, "play": False, "sequence_open": False, "dirty": {"maps": [], "content": []},
            "native_import_active": False,
            "bridge": {"queue": 0, "remote_locked": False, "other_running": [], "unfinished_async": []}}


def rehash(req):
    pins = [req["item"]["source"], req["item"]["sidecar"], req["protected_manifest"]] + req["recipe_pins"]
    return {p["path"]: p["sha256"] for p in pins}


def queue_entry(req):
    return {"seed": req["seed"], "source_path": req["item"]["source"]["path"], "source_sha256": req["item"]["source"]["sha256"],
            "planned_destination_folder": req["item"]["destination"]}


def native_map(req, **changes):
    rc = r27_receipt(req, **changes)
    return c.map_r27_receipt(req, rc, rehash(req), live("2030-01-02T12:04:00+00:00"), live("2030-01-02T12:06:00+00:00"), PID)


class RequestContract(unittest.TestCase):
    def test_exact_build_request_key_set(self):
        self.assertEqual(set(request()), c.REQUEST_KEYS)
        self.assertEqual(c.validate_request(request()), request())

    def test_safety_flags_refused(self):
        for key, value in (("receiving_adapter_required", False), ("legacy_run_seed_is_directly_safe", True),
                           ("automatic_restart", True), ("automatic_lease_mutation", True),
                           ("native_admission", True), ("execution_mode", "replay")):
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

    def test_native_request_rules(self):
        self.assertEqual(c.validate_request(request(mode="native")), request(mode="native"))
        r = request(mode="native")
        r["receiving_owner"] = "unreal-epic-boss"          # OPEN-leases: custodian only
        with self.assertRaises(c.ContractError):
            c.validate_request(r)
        r = request(mode="native")
        r["expected_world"] = "/Game/X/W.L_Daedalus_MorningReview"   # OPEN-world: protected showcase
        with self.assertRaises(c.ContractError):
            c.validate_request(r)
        r = request(mode="native")
        r["expected_world"] = "/Game/X/W"                    # not native_world(world)
        with self.assertRaises(c.ContractError):
            c.validate_request(r)
        r = request(mode="native")
        r["recipe_pins"] = [pin("continue_native_islands_24h_20261023.py")]
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
                           ("execution_mode", "native"),
                           ("source_target_binding", dict(r["item"], destination="/Other")),
                           ("recipe_pins_verified", [])):
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.validate_preflight_shape(r, dict(preflight(r), **{key: value}))
        with self.assertRaises(c.ContractError):
            c.validate_preflight_shape(r, dict(preflight(r), extra=True))

    def test_editor_floors(self):
        r = request(mode="native")
        c.check_editor_floors(preflight(r))
        low = preflight(r)
        low["resources"]["available_physical_bytes"] = 1_000_000_000
        with self.assertRaises(c.ContractError):
            c.check_editor_floors(low)
        for key, value in (("single_writer", False), ("editor_idle", False), ("other_producers", [999]), ("play", True),
                           ("sequence_open", True), ("dirty", {"maps": ["/x"], "content": []}),
                           ("bridge", {"queue": 1, "remote_locked": False, "other_running": [], "unfinished_async": []}),
                           ("lease_holders", {"compute": c.RUNTIME_CUSTODIAN, "unreal": "unreal-epic-boss"})):
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.check_editor_floors(dict(preflight(r), **{key: value}))


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
        self.assertNotIn("source", candidate["preservation"])
        self.assertNotIn("pending_native_operations", candidate)
        self.assertNotIn("request_sha256", candidate)
        for oid in ("OPEN-preservation-source", "OPEN-pending", "OPEN-identity", "OPEN-native-schema"):
            self.assertIn(oid, open_ids)
            self.assertIn(oid, c.RESOLVED)    # every legacy OPEN id now has a recorded resolution
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


class NativeR27Path(unittest.TestCase):
    """Boss answers 1-8 (PR #906 comment, Oct 29)."""

    def test_no_open_items_remain(self):
        self.assertEqual(c.OPEN, {})
        self.assertEqual(len(c.RESOLVED), 8)
        self.assertEqual(c.RUNTIME_CUSTODIAN, "codex-play-guard")

    def test_native_world_matches_receiver(self):
        self.assertEqual(c.native_world("/Game/Daedalus/Maps/L_Realm"), "/Game/Daedalus/Maps/L_Realm.L_Realm")

    def test_r27_receipt_accepted_and_mapped(self):
        r = request(mode="native")
        candidate, sealed = native_map(r)
        self.assertEqual(set(candidate), c.RESULT_KEYS)
        self.assertTrue(candidate["native_admission"])
        self.assertFalse(candidate["simulated"])
        self.assertEqual(candidate["preservation"], {k: True for k in c.PRESERVATION_KEYS})
        self.assertEqual(sealed["custodian"], c.RUNTIME_CUSTODIAN)
        self.assertEqual(sealed["result_sha256"], c.canonical_sha256(r27_receipt(r)))
        self.assertEqual(sealed["request_sha256"], c.request_sha256(r))
        self.assertEqual(c.validate_native_result(r, candidate, sealed), candidate)

    def test_held_island_is_refused_not_admitted(self):
        r = request(mode="native")
        candidate, sealed = native_map(r, admitted=False)
        self.assertFalse(candidate["native_admission"])
        self.assertTrue(sealed["held"])
        with self.assertRaises(c.ContractError):
            c.validate_native_result(r, candidate, sealed)

    def test_receiver_validate_result_rules(self):
        r = request(mode="native")
        base = r27_receipt(r)
        mutations = {
            "known_terminal": lambda d: d["result"].update(known_terminal=False),
            "bridge_after": lambda d: d["result"]["bridge_after"].update(queue=1),
            "native_import_active": lambda d: d["result"]["action"].update(native_import_active=True),
            "preservation": lambda d: d["result"]["action"]["preservation"].update(camera=False),
            "failed": lambda d: d["result"]["action"].update(failed=1),
            "prepared": lambda d: d["result"]["action"].update(prepared=2),
            "counts_close": lambda d: d["result"]["action"].update(held=1),
            "saved_imported": lambda d: d["result"]["action"].update(saved=0),
            "dirty": lambda d: d["result"]["action"].update(dirty={"maps": ["/x"], "content": []}),
            "item_totals": lambda d: d["result"]["action"].update(items=[]),
            "valid_evidence": lambda d: d["result"]["action"]["items"][0]["validation"].update(status="Warning"),
            "saved_files_pin": lambda d: d.update(saved_files=[{"path": "x"}]),
            "no_action": lambda d: d["result"].pop("action"),
        }
        for name, mutate in mutations.items():
            d = copy.deepcopy(base)
            mutate(d)
            with self.subTest(name=name), self.assertRaises(c.ContractError):
                c.validate_r27_receipt(d)

    def test_pin_rehash_refuses_change_or_omission(self):
        r = request(mode="native")
        h = rehash(r)
        h[r["recipe_pins"][0]["path"]] = "b" * 64
        with self.assertRaises(c.ContractError):
            c.verify_rehash(r, h)
        h = rehash(r)
        h.pop(r["protected_manifest"]["path"])
        with self.assertRaises(c.ContractError):
            c.verify_rehash(r, h)
        self.assertEqual(len(c.verify_rehash(r, rehash(r))), 4)

    def test_live_reads_required_clean_and_ordered(self):
        r = request(mode="native")
        rc = r27_receipt(r)
        good_b, good_a = live("2030-01-02T12:04:00+00:00"), live("2030-01-02T12:06:00+00:00")
        for bad in (dict(good_a, play=True), dict(good_a, sequence_open=True), dict(good_a, pid=999),
                    dict(good_a, dirty={"maps": ["/x"], "content": []}), dict(good_a, native_import_active=True)):
            with self.assertRaises(c.ContractError):
                c.map_r27_receipt(r, rc, rehash(r), good_b, bad, PID)
        with self.assertRaises(c.ContractError):
            c.map_r27_receipt(r, rc, rehash(r), good_a, good_b, PID)     # reversed order
        with self.assertRaises(c.ContractError):
            c.map_r27_receipt(r, rc, rehash(r), good_b, good_a, 999)     # wrong editor pid

    def test_destination_proved_before_and_after(self):
        r = request(mode="native")
        c.prove_destination(r, queue_entry(r))
        q = queue_entry(r)
        q["source_path"] = "C:/Unreal/legacy/source_for.glb"           # legacy source_for constant refused
        with self.assertRaises(c.ContractError):
            c.prove_destination(r, q)
        q = queue_entry(r)
        q["planned_destination_folder"] = "/Game/Daedalus/Art/Islands/HDNative20261023/x"
        with self.assertRaises(c.ContractError):
            c.prove_destination(r, q)
        rc = r27_receipt(r)
        rc["result"]["action"]["items"][0]["asset"] = "/Game/Elsewhere/Mesh.Mesh"   # outside owned folder
        with self.assertRaises(c.ContractError):
            c.map_r27_receipt(r, rc, rehash(r), live("2030-01-02T12:04:00+00:00"), live("2030-01-02T12:06:00+00:00"), PID)
        rc = r27_receipt(r)
        rc["saved_files"] = [{"path": "C:/Unreal/DaedalusRealm/Content/Elsewhere/x.uasset", "bytes": 1, "sha256": SHA}]
        with self.assertRaises(c.ContractError):
            c.map_r27_receipt(r, rc, rehash(r), live("2030-01-02T12:04:00+00:00"), live("2030-01-02T12:06:00+00:00"), PID)

    def test_identity_sealed_not_asserted_by_recipe(self):
        r = request(mode="native")
        candidate, sealed = native_map(r)
        tampered = copy.deepcopy(r)
        tampered["generation"] = 7
        tampered["invocation_id"] = "synthetic-session-1:7"
        with self.assertRaises(c.ContractError):
            c.validate_native_result(tampered, candidate, sealed)
        bad_seal = dict(sealed, custodian="unreal-epic-boss")
        with self.assertRaises(c.ContractError):
            c.validate_native_result(r, candidate, bad_seal)

    def test_mock_request_cannot_use_native_mapper(self):
        r = request()
        with self.assertRaises(c.ContractError):
            c.map_r27_receipt(r, r27_receipt(r), rehash(r), live("a"), live("b"), PID)


class StubAndScope(unittest.TestCase):
    def test_proposed_native_adapter_refuses(self):
        adapter = c.ProposedNativeAdapter()
        self.assertEqual(adapter.status, c.CONTRACT_STATUS)
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
