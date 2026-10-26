import json
import os
import unittest

import plan_core as pc

HERE = os.path.dirname(os.path.abspath(__file__))
CRATE_SHA = "b1453d459a26a767b6140bf2a0e17496325c3f1d932a916e98ce0516394538c3"
EVAL = "C:/Unreal/EvalDisposable/EvalDisposable.uproject"


def crate_spec(**over):
    spec = {"asset": "Prop_PracticeCrate", "source_path": "Prop_PracticeCrate.glb",
            "sha256": CRATE_SHA, "project": EVAL,
            "expect": {"triangles": 132, "slots": ["Prop_PracticeCrate_M0", "Prop_PracticeCrate_M1"],
                       "simple_collision": 0, "lods": 1}}
    spec.update(over)
    return spec


def crate_observed(plan, **changes):
    results = {
        "CheckTriangleCount[0]": 132, "CheckMaterialSlotCount[]": 2,
        "CheckImportedMaterialSlotName[0]": "Prop_PracticeCrate_M0",
        "CheckImportedMaterialSlotName[1]": "Prop_PracticeCrate_M1",
        "CheckSimpleCollisionPrimitiveCount[]": 0, "CheckLodCount[]": 1}
    results.update(changes)
    return {"sha256": plan["sha256"], "results": results}


class PlanTests(unittest.TestCase):
    def test_crate_plan_has_the_five_checks_in_order(self):
        plan = pc.plan_from_spec(crate_spec())
        self.assertEqual([c["function"] for c in plan["checks"]],
                         ["CheckTriangleCount", "CheckMaterialSlotCount", "CheckImportedMaterialSlotName",
                          "CheckImportedMaterialSlotName", "CheckSimpleCollisionPrimitiveCount", "CheckLodCount"])

    def test_crate_pass(self):
        plan = pc.plan_from_spec(crate_spec())
        self.assertEqual(pc.evaluate(plan, crate_observed(plan))["verdict"], "PASS")

    def test_wrong_triangles_fail(self):
        plan = pc.plan_from_spec(crate_spec())
        out = pc.evaluate(plan, crate_observed(plan, **{"CheckTriangleCount[0]": 120}))
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual([r["check"] for r in out["rows"] if not r["pass"]], ["CheckTriangleCount[0]"])

    def test_missing_observation_fails(self):
        plan = pc.plan_from_spec(crate_spec())
        obs = crate_observed(plan)
        del obs["results"]["CheckLodCount[]"]
        self.assertEqual(pc.evaluate(plan, obs)["verdict"], "FAIL")

    def test_changed_source_fails(self):
        plan = pc.plan_from_spec(crate_spec())
        obs = crate_observed(plan)
        obs["sha256"] = "0" * 64
        self.assertEqual(pc.evaluate(plan, obs)["verdict"], "FAIL")

    def test_empty_plan_refused(self):
        with self.assertRaises(pc.PlanError):
            pc.plan_from_spec(crate_spec(expect={}))

    def test_daedalusrealm_refused(self):
        with self.assertRaises(pc.PlanError):
            pc.plan_from_spec(crate_spec(project="C:\\Unreal\\DaedalusRealm\\DaedalusRealm.uproject"))

    def test_bad_sha_refused(self):
        with self.assertRaises(pc.PlanError):
            pc.plan_from_spec(crate_spec(sha256="ABC"))

    def test_duplicate_slots_refused(self):
        with self.assertRaises(pc.PlanError):
            pc.plan_from_spec(crate_spec(expect={"slots": ["M", "M"]}))

    def test_bool_is_not_a_count(self):
        with self.assertRaises(pc.PlanError):
            pc.plan_from_spec(crate_spec(expect={"triangles": True}))

    def test_fail_variant_is_deterministic_and_leaves_original(self):
        plan = pc.plan_from_spec(crate_spec())
        bad = pc.expected_fail_variant(plan, "CheckTriangleCount", 131)
        self.assertEqual(plan["checks"][0]["expected"], 132)
        self.assertEqual(bad["expect_verdict"], "FAIL")
        out = pc.evaluate(bad, crate_observed(plan))
        self.assertEqual([r["check"] for r in out["rows"] if not r["pass"]], ["CheckTriangleCount[0]"])

    def test_fail_variant_needs_a_real_difference(self):
        plan = pc.plan_from_spec(crate_spec())
        with self.assertRaises(pc.PlanError):
            pc.expected_fail_variant(plan, "CheckTriangleCount", 132)

    def test_receiver_profile_terrain_33(self):
        path = os.path.join(HERE, "..", "interchange_harness", "profiles", "flagship_terrain_33.json")
        with open(path, encoding="utf-8") as handle:
            profile = json.load(handle)
        plan = pc.plan_from_receiver_profile(profile, "flagship_terrain_33", EVAL)
        self.assertEqual(plan["checks"][0], {"function": "CheckTriangleCount", "lod": 0, "expected": 669})
        names = [c["expected"] for c in plan["checks"] if c["function"] == "CheckImportedMaterialSlotName"]
        self.assertEqual(names, ["M_BB_Grass", "M_BB_Sand", "M_BB_Dirt", "M_BB_ShoreWater", "M_BB_Rock"])
        self.assertIn({"function": "CheckSimpleCollisionPrimitiveCount", "expected": 0}, plan["checks"])


if __name__ == "__main__":
    unittest.main()
