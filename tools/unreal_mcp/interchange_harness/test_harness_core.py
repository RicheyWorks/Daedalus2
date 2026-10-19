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
             "nanite": True, "collision": {"convex": 1}, "sockets": [{"name": "Top"}]}
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