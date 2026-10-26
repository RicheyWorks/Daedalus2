import os
import tempfile
import unittest

import audit_core as ac


def mesh(name="Prop_Crate", **over):
    row = {"path": "/Game/T/" + name, "class": "StaticMesh", "name": name,
           "slots": ["M_BB_Wood_01"], "simple_collision": 1, "bounds_cm": [100.0, 80.0, 60.0]}
    row.update(over)
    return row


class AuditTests(unittest.TestCase):
    def test_clean_mesh_passes(self):
        self.assertEqual(ac.audit([mesh()])["verdict"], "PASS")

    def test_misnamed_copy_is_flagged(self):
        out = ac.audit([mesh(), mesh("Cube.001")])
        self.assertEqual(out["verdict"], "FLAGGED")
        self.assertEqual(out["flagged"][0]["findings"], ["name"])

    def test_unknown_kind_flagged(self):
        self.assertIn("name", ac.check_row(mesh("Creature_CaneCorso")))

    def test_material_and_instance_prefixes(self):
        self.assertEqual(ac.check_row({"class": "Material", "name": "M_BB_Wood_01"}), [])
        self.assertEqual(ac.check_row({"class": "MaterialInstanceConstant", "name": "MI_Coat"}), [])
        self.assertIn("name", ac.check_row({"class": "MaterialInstanceConstant", "name": "M_Coat"}))

    def test_blender_style_slot_names_flagged(self):
        found = ac.check_row(mesh(slots=["Wood.001", "Glow#2", "OK_Slot"]))
        self.assertEqual(found, ["slot_name:Wood.001", "slot_name:Glow#2"])

    def test_zero_collision_flagged_unless_allowed(self):
        self.assertIn("no_simple_collision", ac.check_row(mesh(simple_collision=0)))
        self.assertEqual(ac.check_row(mesh(simple_collision=0, no_collision_ok=True)), [])

    def test_missing_facts_are_findings_not_passes(self):
        row = mesh()
        del row["simple_collision"]
        del row["bounds_cm"]
        self.assertEqual(ac.check_row(row), ["collision_unknown", "bounds_unknown"])

    def test_bounds_limits(self):
        self.assertIn("bounds_out_of_range", ac.check_row(mesh(bounds_cm=[0.5, 0.2, 0.1])))
        self.assertIn("bounds_out_of_range", ac.check_row(mesh(bounds_cm=[20000.0, 1.0, 1.0])))
        self.assertIn("bounds_unknown", ac.check_row(mesh(bounds_cm=[1.0, 2.0])))

    def test_empty_audit_fails(self):
        self.assertEqual(ac.audit([])["verdict"], "FAIL")

    def test_folder_digest_detects_writes(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "a.uasset"), "wb") as handle:
                handle.write(b"x")
            before = ac.folder_digest(root)
            self.assertTrue(ac.unchanged(before, ac.folder_digest(root)))
            with open(os.path.join(root, "b.uasset"), "wb") as handle:
                handle.write(b"y")
            self.assertFalse(ac.unchanged(before, ac.folder_digest(root)))


if __name__ == "__main__":
    unittest.main()
