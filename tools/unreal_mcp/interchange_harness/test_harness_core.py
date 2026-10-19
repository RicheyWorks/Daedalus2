"""Engine-free tests for harness_core (python -m unittest test_harness_core)."""
import hashlib
import json
import os
import shutil
import struct
import tempfile
import unittest

import harness_core as h

HERE = os.path.dirname(os.path.abspath(__file__))


def make_glb(alpha="OPAQUE", socket=True, ucx=True):
    nodes = [{"name": "Crate", "mesh": 0, "children": []}]
    if socket:
        nodes.append({"name": "SOCKET_Top", "translation": [0, 0.5, 0]})
        nodes[0]["children"].append(len(nodes) - 1)
    if ucx:
        nodes.append({"name": "UCX_Crate", "mesh": 0})
        nodes[0]["children"].append(len(nodes) - 1)
    mat = {"name": "Crate_M0"}
    if alpha != "OPAQUE":
        mat["alphaMode"] = alpha
    gl = {"asset": {"version": "2.0"}, "nodes": nodes, "meshes": [{"primitives": []}], "materials": [mat]}
    js = json.dumps(gl).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def glb(self, data, name="Crate.glb"):
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p

    def side(self, obj, name="Crate.sockets.json"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return p


class PlanTests(Base):
    def test_requires_checkpoint(self):
        with self.assertRaises(h.PlanError):
            h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", checkpoint=None)

    def test_sha_mismatch_refused(self):
        with self.assertRaises(h.PlanError):
            h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", sha256="0" * 64, checkpoint="cp.json")

    def test_destination_must_be_game(self):
        with self.assertRaises(h.PlanError):
            h.build_plan(self.glb(make_glb()), "C:/x", "Crate", checkpoint="cp.json")

    def test_nanite_default_on(self):
        p = h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", checkpoint="cp.json")
        self.assertTrue(p["options"]["build_nanite"])
        self.assertNotIn("nanite_reason", p)

    def test_nanite_override_off(self):
        p = h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", checkpoint="cp.json", overrides={"build_nanite": False, "nanite_reason": "packet says off"})
        self.assertFalse(p["options"]["build_nanite"])
        self.assertEqual(p["nanite_reason"], "packet says off")

    def test_material_flags_independent(self):
        p = h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", checkpoint="cp.json", overrides={"reuse_existing_materials": True, "create_new_materials": False})
        self.assertTrue(p["options"]["reuse_existing_materials"])
        self.assertFalse(p["options"]["create_new_materials"])

    def test_masked_and_translucent_flagged(self):
        for alpha in ("MASK", "BLEND"):
            p = h.build_plan(self.glb(make_glb(alpha=alpha), "c_%s.glb" % alpha), "/Game/T", "Crate", checkpoint="cp.json")
            self.assertEqual(len(p["material_review"]), 1)
        p = h.build_plan(self.glb(make_glb()), "/Game/T", "Crate", checkpoint="cp.json")
        self.assertEqual(p["material_review"], [])


class SocketTests(Base):
    def test_sample_sidecar(self):
        socks = h.load_sidecar(os.path.join(HERE, "samples", "Prop_PracticeCrate.sockets.json"))
        self.assertEqual(socks, [{"name": "Top", "parent": "Prop_PracticeCrate", "location_cm": [0.0, 0.0, 50.0], "rotation_pyr": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]}])

    def test_blender_team_fixture_shape(self):
        # exact shape delivered by blender-team in interchange-fixture-20261019/B (48521)
        obj = {"asset": "Prop_PracticeCrate", "units": "cm", "space": "unreal",
               "sockets": [{"name": "SOCKET_Top", "parent": "Prop_PracticeCrate", "location": [0.0, 0.0, 50.0], "rotation": [0.0, 0.0, 0.0]}]}
        socks = h.load_sidecar(self.side(obj))
        self.assertEqual(socks, [{"name": "Top", "parent": "Prop_PracticeCrate", "location_cm": [0.0, 0.0, 50.0], "rotation_pyr": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]}])
        with self.assertRaises(h.PlanError):
            h.load_sidecar(self.side(dict(obj, units="m"), "m.json"))

    def test_sidecar_next_to_glb_used(self):
        g = self.glb(make_glb())
        self.side([{"name": "Top", "parent": "Crate", "location_cm": [0, 0, 50], "rotation": [0, 90, 0]}])
        sp = h.socket_plan(g)
        self.assertEqual(sp["sockets"][0]["rotation_pyr"], [0.0, 90.0, 0.0])
        self.assertEqual(sp["warnings"], [])

    def test_missing_sidecar_warns_when_socket_empties(self):
        sp = h.socket_plan(self.glb(make_glb()))
        self.assertEqual(sp["sockets"], [])
        self.assertIn("SOCKET_Top", sp["warnings"][0])

    def test_missing_sidecar_no_empties_no_warning(self):
        self.assertEqual(h.socket_plan(self.glb(make_glb(socket=False)))["warnings"], [])

    def test_sidecar_missing_glb_socket_warns(self):
        g = self.glb(make_glb())
        self.side([{"name": "Grip", "parent": "Crate", "location_cm": [1, 2, 3], "rotation": [0, 0, 0]}])
        self.assertIn("Top", h.socket_plan(g)["warnings"][0])

    def test_bad_entries_rejected(self):
        bad = [[{"name": "Top", "parent": "Crate", "location_cm": [0, 0]  , "rotation": [0, 0, 0]}],
               [{"name": "Top", "parent": "Crate", "rotation": [0, 0, 0]}],
               [{"name": "Top", "parent": "C", "location_cm": [0, 0, 0], "rotation": [0, 0, 0]}, {"name": "SOCKET_Top", "parent": "C", "location_cm": [0, 0, 0], "rotation": [0, 0, 0]}]]
        for i, b in enumerate(bad):
            with self.assertRaises(h.PlanError):
                h.load_sidecar(self.side(b, "b%d.json" % i))


class EvaluateTests(Base):
    def plan(self):
        g = self.glb(make_glb())
        self.side([{"name": "Top", "parent": "Crate", "location_cm": [0, 0, 50], "rotation": [0, 0, 0]}])
        p = h.build_plan(g, "/Game/T", "Crate", checkpoint="cp.json")
        p["expect"] = {"inventory_count": 2, "slots": ["Crate_M0"], "triangles": 12, "min_cm": [0, 0, 0], "max_cm": [1, 1, 1]}
        return p

    def facts(self, **kw):
        f = {"inventory": ["a", "b"], "materials": [{"slot": "Crate_M0"}], "tris_lod0": 12, "bounds_min_cm": [0, 0, 0], "bounds_max_cm": [1, 1, 1.1],
             "nanite": True, "collision": {"convex": 1}, "sockets": [{"name": "Top", "location_cm": [0, 0, 50], "rotation_pyr": [0, 0, 0]}]}
        f.update(kw)
        return f

    def test_started_is_not_done(self):
        r = h.evaluate(self.plan(), {"done": False}, self.facts())
        self.assertFalse(r["ok"])

    def test_full_pass_with_second_save_note(self):
        r = h.evaluate(self.plan(), {"done": True}, self.facts(), before_identity={"same_uobject": True}, save_passes={"passes": 2, "dirty_after": []})
        self.assertTrue(r["ok"], r)
        self.assertTrue(any("2 save passes" in n for n in r["notes"]))

    def test_failures_detected(self):
        p = self.plan()
        cases = {"nanite_as_planned": {"nanite": False}, "sockets_added": {"sockets": []}, "ucx_convex": {"collision": {"convex": 0}},
                 "slots_exact_order": {"materials": [{"slot": "X"}]}, "inventory_exact": {"inventory": ["a", "b", "c"]}, "bounds": {"bounds_max_cm": [1, 1, 2]}}
        for key, kw in cases.items():
            r = h.evaluate(p, {"done": True}, self.facts(**kw))
            self.assertFalse(r["checks"][key], key)

    def test_identity_change_fails(self):
        r = h.evaluate(self.plan(), {"done": True}, self.facts(), before_identity={"same_uobject": False})
        self.assertFalse(r["checks"]["same_uobject"])


class ReviewFixTests(Base):
    """Review 48565 (buffffff) fixes and nice-to-haves."""

    def test_close_requires_three_values_both_sides(self):
        self.assertTrue(h._close([0, 0, 0], [0, 0, 0.1], 0.2))
        for a, b in [([], []), ([], [0, 0, 0]), ([0, 0, 0], []), ([0, 0], [0, 0]), ([0, 0], [0, 0, 0]),
                     ([0, 0, 0, 0], [0, 0, 0, 0]), (None, [0, 0, 0]), ([0, 0, "x"], [0, 0, 0])]:
            self.assertFalse(h._close(a, b, 0.2), (a, b))

    def test_bounds_fail_when_facts_missing_or_short(self):
        ev = EvaluateTests("test_started_is_not_done")
        ev.tmp = self.tmp
        p = ev.plan()
        for kw in ({"bounds_min_cm": [], "bounds_max_cm": []}, {"bounds_max_cm": [1, 1]}):
            f = ev.facts(**kw)
            self.assertFalse(h.evaluate(p, {"done": True}, f)["checks"]["bounds"], kw)
        f = ev.facts()
        del f["bounds_min_cm"]
        self.assertFalse(h.evaluate(p, {"done": True}, f)["checks"]["bounds"])
        p["expect"]["min_cm"] = [0, 0]
        self.assertFalse(h.evaluate(p, {"done": True}, ev.facts())["checks"]["bounds"])

    def test_mesh_none_fails_nanite_off_plan(self):
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), "/Game/T", "Crate", checkpoint="cp.json",
                         overrides={"build_nanite": False})
        p["expect"] = {}  # no inventory_count: mesh_found alone must catch it
        r = h.evaluate(p, {"done": True}, {"mesh": None, "mesh_found": False, "inventory": []})
        self.assertFalse(r["ok"])
        self.assertFalse(r["checks"]["mesh_found"])
        self.assertFalse(r["checks"]["nanite_as_planned"])
        r = h.evaluate(p, {"done": True}, {"mesh": None, "inventory": []})  # older facts shape
        self.assertFalse(r["checks"]["mesh_found"])
        self.assertFalse(r["checks"]["nanite_as_planned"])

    def test_mesh_found_and_nanite_off_passes(self):
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), "/Game/T", "Crate", checkpoint="cp.json",
                         overrides={"build_nanite": False})
        p["expect"] = {}
        r = h.evaluate(p, {"done": True}, {"mesh_found": True, "nanite": False, "inventory": ["a"]})
        self.assertTrue(r["ok"], r)

    def test_nanite_missing_fact_fails(self):
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), "/Game/T", "Crate", checkpoint="cp.json",
                         overrides={"build_nanite": False})
        p["expect"] = {}
        self.assertFalse(h.evaluate(p, {"done": True}, {"mesh_found": True})["checks"]["nanite_as_planned"])

    def test_profile_overrides_explicit_overrides(self):
        prof = {"interchange_requested_options": {"build_nanite": False}, "expect": {}}
        g = self.glb(make_glb(socket=False, ucx=False))
        p = h.build_plan(g, "/Game/T", "Crate", checkpoint="cp.json", overrides={"build_nanite": True}, profile=prof)
        self.assertFalse(p["options"]["build_nanite"])
        p = h.build_plan(g, "/Game/T", "Crate", checkpoint="cp.json", overrides={"build_nanite": False})
        self.assertFalse(p["options"]["build_nanite"])
        self.assertIn("overrides", h.build_plan.__doc__)

    def test_ue_harness_modify_before_sockets_and_no_dead_branch(self):
        with open(os.path.join(HERE, "ue_harness.py"), encoding="utf-8") as fh:
            src = fh.read()
        body = src[src.index("def add_sockets"):src.index("def set_nanite")]
        self.assertLess(body.index("mesh.modify()"), body.index("mesh.add_socket("))
        self.assertNotIn('get_editor_property("sockets")', src)  # protected in UE 5.8
        self.assertEqual(body.count("mesh.modify()"), 1)
        self.assertNotIn("material_import", src[src.index("def _pipeline"):src.index("def _on_done")])

    def test_ue_harness_override_pipelines_soft_paths(self):
        with open(os.path.join(HERE, "ue_harness.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("override_pipelines = [unreal.SoftObjectPath(", src)
        self.assertNotIn("override_pipelines = [_pipeline(", src)


class CollisionAndLightmapTests(Base):
    """buffffff 48710: collision=false means 0 simple collision primitives; lightmap prop name (UE 5.8)."""

    def plan(self, **ov):
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), "/Game/T", "Crate", checkpoint="cp.json", overrides=ov)
        p["expect"] = {}
        return p

    def test_collision_false_plans_no_generation(self):
        self.assertFalse(self.plan(collision=False)["options"]["generate_collision"])
        self.assertTrue(self.plan()["options"]["generate_collision"])

    def test_collision_false_requires_zero_simple(self):
        p = self.plan(collision=False, build_nanite=False)
        ok = h.evaluate(p, {"done": True}, {"mesh_found": True, "nanite": False, "simple_collision_count": 0})
        self.assertTrue(ok["ok"], ok)
        for bad in ({"mesh_found": True, "nanite": False, "simple_collision_count": 1},
                    {"mesh_found": True, "nanite": False},
                    {"mesh": None, "simple_collision_count": 0}):
            r = h.evaluate(p, {"done": True}, bad)
            self.assertFalse(r["checks"]["no_simple_collision"], bad)
            self.assertFalse(r["ok"])

    def test_collision_true_does_not_assert_zero(self):
        r = h.evaluate(self.plan(), {"done": True}, {"mesh_found": True, "nanite": True, "simple_collision_count": 3})
        self.assertNotIn("no_simple_collision", r["checks"])

    def test_terrain33_profile_asserts_zero_collision(self):
        with open(os.path.join(HERE, "profiles", "flagship_terrain_33.json"), encoding="utf-8") as fh:
            prof = json.load(fh)
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), prof["destination"], "Crate", checkpoint="cp.json", profile=prof)
        self.assertFalse(p["options"]["generate_collision"])

    def test_ue_harness_pipeline_names(self):
        with open(os.path.join(HERE, "ue_harness.py"), encoding="utf-8") as fh:
            src = fh.read()
        pipe = src[src.index("def _pipeline"):src.index("def _on_done")]
        self.assertIn('_try_set(mesh, "generate_lightmap_u_vs"', pipe)
        self.assertNotIn('_try_set(common, "generate_lightmap_u_vs"', pipe)
        self.assertIn('_try_set(mesh, "collision", False', pipe)
        self.assertIn("InterchangeMeshCollision.NONE", pipe)
        self.assertIn('"simple_collision_count"', src)
        cnt = src[src.index("def _simple_count"):src.index("def strip_simple_collision")]
        self.assertIn('"convex_elems"', cnt)
        self.assertNotIn("get_simple_collision_count(mesh)", cnt)  # excludes convex in 5.8


class SidecarRotationTests(Base):
    """Sidecar is the rotation carrier; native socket kept, rotation from sidecar if position within 0.5 cm."""

    def plan(self, **ov):
        g = self.glb(make_glb(ucx=False))
        self.side({"units": "cm", "sockets": [{"name": "SOCKET_Top", "parent": "Crate", "location": [0, 0, 50], "rotation": [0, 90, 0]}]})
        p = h.build_plan(g, "/Game/T", "Crate", checkpoint="cp.json", overrides=ov)
        p["expect"] = {}
        return p

    def facts(self, loc=(0, 0, 50), rot=(0, 90, 0)):
        return {"mesh_found": True, "nanite": True, "sockets": [{"name": "Top", "location_cm": list(loc), "rotation_pyr": list(rot)}]}

    def test_default_on_and_opt_out(self):
        self.assertTrue(self.plan()["options"]["sidecar_rotation"])
        self.assertFalse(self.plan(sidecar_rotation=False)["options"]["sidecar_rotation"])

    def test_position_tolerance(self):
        self.assertTrue(h.socket_position_ok([0, 0, 50.4], [0, 0, 50]))
        self.assertFalse(h.socket_position_ok([0, 0, 50.6], [0, 0, 50]))
        self.assertFalse(h.socket_position_ok([], [0, 0, 50]))

    def test_rotation_wrap(self):
        self.assertTrue(h.rotation_close([0, 180, -90], [0, -180, -90]))
        self.assertTrue(h.rotation_close([-90, 0, 0], [-90.01, 0, 360]))
        self.assertFalse(h.rotation_close([0, 180, -90], [-90, 0, 0]))
        self.assertFalse(h.rotation_close(None, [0, 0, 0]))

    def test_evaluate_passes_with_sidecar_rotation(self):
        r = h.evaluate(self.plan(), {"done": True}, self.facts())
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["checks"]["socket_rotations"])

    def test_native_basis_artefact_fails(self):
        r = h.evaluate(self.plan(), {"done": True}, self.facts(rot=(0, 180, -90)))
        self.assertFalse(r["checks"]["socket_rotations"])
        self.assertFalse(r["ok"])

    def test_position_mismatch_fails(self):
        r = h.evaluate(self.plan(), {"done": True}, self.facts(loc=(0, 0, 51)))
        self.assertFalse(r["checks"]["socket_positions"])

    def test_opt_out_skips_rotation_checks(self):
        r = h.evaluate(self.plan(sidecar_rotation=False), {"done": True}, self.facts(rot=(0, 180, -90)))
        self.assertNotIn("socket_rotations", r["checks"])
        self.assertTrue(r["ok"], r)

    def test_ue_harness_existing_socket_branch(self):
        with open(os.path.join(HERE, "ue_harness.py"), encoding="utf-8") as fh:
            src = fh.read()
        body = src[src.index("def add_sockets"):src.index("def set_nanite")]
        kept = body[body.index("if s[\"name\"] in existing:"):body.index("continue")]
        self.assertLess(kept.index("socket_position_ok("), kept.index('set_editor_property("relative_rotation"'))
        for k in ("native_rotation_pyr", "sidecar_rotation_pyr", "sidecar_rotation"):
            self.assertIn(k, kept)


class QuatAndLod1Tests(Base):
    def test_gimbal_equivalent_rotators_pass(self):
        self.assertTrue(h.rotation_close([90, 0, -90], [90, 90, 0]))
        self.assertLess(h.rotation_angle_deg([90, 0, -90], [90, 90, 0]), 0.01)

    def test_genuinely_different_fails(self):
        self.assertFalse(h.rotation_close([90, 0, -90], [0, -90, 90]))
        self.assertFalse(h.rotation_close([0, 0, 0], [0, 1, 0]))
        self.assertTrue(h.rotation_close([0, 0, 0], [0, 0.4, 0]))
        self.assertAlmostEqual(h.rotation_angle_deg([0, 0, 0], [0, 90, 0]), 90.0, places=6)

    def test_quat_matches_ue_formula_identity_and_q_minus_q(self):
        self.assertEqual(tuple(round(v, 9) for v in h.rotator_to_quat([0, 0, 0])), (0.0, 0.0, 0.0, 1.0))
        self.assertTrue(h.rotation_close([0, 180, 0], [0, -180, 0]))

    def _asset(self, report=None, lod=True, lod_bytes=b"lod1"):
        g = self.glb(make_glb(socket=False, ucx=False), "Gate.glb")
        if lod:
            with open(os.path.join(self.tmp, "Gate_LOD1.glb"), "wb") as fh:
                fh.write(lod_bytes)
        if report is not None:
            with open(os.path.join(self.tmp, "build_report.json"), "w", encoding="utf-8") as fh:
                json.dump(report, fh)
        return g

    def test_lod1_found_with_build_report(self):
        sha = hashlib.sha256(b"lod1").hexdigest()
        g = self._asset({"files": {"Gate_LOD1.glb": {"sha256": sha}}, "lod1": {"triangles": 264}})
        p = h.build_plan(g, "/Game/T", "Gate", checkpoint="cp.json")
        self.assertEqual(p["lod1"]["expected_tris"], 264)
        self.assertTrue(p["lod1"]["path"].endswith("Gate_LOD1.glb"))
        p["expect"] = {}
        ok = h.evaluate(p, {"done": True}, {"mesh_found": True, "nanite": True, "lods": 2, "lod1_source_tris": 264})
        self.assertTrue(ok["ok"], ok)
        self.assertTrue(any("fallback" in n for n in ok["notes"]))
        bad = h.evaluate(p, {"done": True}, {"mesh_found": True, "nanite": True, "lods": 1})
        self.assertFalse(bad["checks"]["lod1_attached"])
        self.assertFalse(bad["checks"]["lod1_tris"])

    def test_lod1_sha_mismatch_refused(self):
        g = self._asset({"files": {"Gate_LOD1.glb": {"sha256": "0" * 64}}})
        with self.assertRaises(h.PlanError):
            h.build_plan(g, "/Game/T", "Gate", checkpoint="cp.json")

    def test_no_lod1_file(self):
        p = h.build_plan(self._asset(lod=False), "/Game/T", "Gate", checkpoint="cp.json")
        self.assertIsNone(p["lod1"])
        p["expect"] = {}
        self.assertNotIn("lod1_attached", h.evaluate(p, {"done": True}, {"mesh_found": True, "nanite": True})["checks"])

    def test_lod1_default_name_without_report(self):
        p = h.build_plan(self._asset(), "/Game/T", "Gate", checkpoint="cp.json")
        self.assertIsNone(p["lod1"]["expected_tris"])

    def test_ue_harness_uses_import_lod(self):
        with open(os.path.join(HERE, "ue_harness.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("import_lod(mesh, 1, lod1[\"path\"])", src)
        self.assertIn('"lod1_source_tris"', src)


class MaterialSearchTests(Base):
    """buffffff 49583: BIP1 packets reuse the shared M_BB_* set (search UNDER_PARENT), no per-packet copies."""

    def plan(self, **ov):
        return h.build_plan(self.glb(make_glb(socket=False, ucx=False)), "/Game/T", "Crate", checkpoint="cp.json", overrides=ov)

    def test_default_is_local(self):
        self.assertEqual(self.plan()["options"]["material_search_location"], "LOCAL")

    def test_under_parent_accepted_case_insensitive(self):
        self.assertEqual(self.plan(material_search_location="under_parent")["options"]["material_search_location"], "UNDER_PARENT")

    def test_unknown_location_refused(self):
        with self.assertRaises(h.PlanError):
            self.plan(material_search_location="EVERYWHERE")

    def test_ue_harness_sets_search_location(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ue_harness.py"), encoding="utf-8").read()
        self.assertIn('"search_location"', src)
        self.assertIn("InterchangeMaterialSearchLocation", src)

class TerrainProfileTests(Base):
    def packet(self):
        sp = {"triangles": 669, "slots": [{"slot": i, "material": {"name": n}} for i, n in [(1, "Sand"), (0, "Grass")]],
              "source_pins": {"packet": {"path": "x.glb"}},
              "transform_contract": {"expected_native_min_cm": [0, 0, 0], "expected_native_max_cm": [1, 1, 1], "bounds_tolerance_cm": 0.2},
              "receiving_contract": {"proposed_root": "/Game/X/Terrain33R1", "interchange_requested_options": {"build_nanite": False, "collision": False}}}
        p = os.path.join(self.tmp, "sp.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(sp, fh)
        return p

    def test_profile_slots_in_order_and_nanite_off(self):
        prof = h.terrain_profile(self.packet())
        self.assertEqual(prof["expect"]["slots"], ["Grass", "Sand"])
        self.assertEqual(prof["expect"]["inventory_count"], 3)
        p = h.build_plan(self.glb(make_glb(socket=False, ucx=False)), prof["destination"], "Crate", checkpoint="cp.json", profile=prof)
        self.assertFalse(p["options"]["build_nanite"])
        self.assertFalse(p["options"]["collision_from_ucx"])
        self.assertIn("freezes build_nanite=false", p["nanite_reason"])

    def test_profile_sha_pin(self):
        with self.assertRaises(h.PlanError):
            h.terrain_profile(self.packet(), expected_sha256="0" * 64)

    def test_committed_terrain33_profile(self):
        with open(os.path.join(HERE, "profiles", "flagship_terrain_33.json"), encoding="utf-8") as fh:
            prof = json.load(fh)
        self.assertEqual(prof["source_packet_sha256"], "519f28bb926d480b8d9644c5497f387331004a98381ca87f00b65d8793804750")
        self.assertEqual(len(prof["expect"]["slots"]), 5)
        self.assertFalse(prof["interchange_requested_options"]["build_nanite"])


if __name__ == "__main__":
    unittest.main()