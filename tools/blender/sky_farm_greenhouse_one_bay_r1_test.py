"""Portable geometry regressions, no Blender process or native claims."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bay", ROOT / "sky_farm_greenhouse_one_bay_r1.py")
bay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bay)


class GeometryTest(unittest.TestCase):
    def setUp(self):
        self.recipe = bay.load_recipe(ROOT / "sky_farm_greenhouse_one_bay_r1.recipe.json")
        self.parts = bay.geometry(self.recipe)

    def test_actual_default_has_bounded_geometry_clear_aisle_and_supported_path(self):
        stats = bay.validate_geometry(self.recipe, self.parts)
        self.assertEqual((121, 8, 1452, 81), tuple(stats[k] for k in
                          ("primitive_count", "mesh_count", "triangles", "path_samples")))
        self.assertEqual(1.4, stats["clear_aisle_width_m"])
        self.assertIsNone(stats["world_binding"])
        self.assertFalse(stats["native_collision_verified"])
        self.assertEqual(0, stats["bounds_m"][0][2])
        self.assertEqual((-5, 5), (stats["bounds_m"][0][1], stats["bounds_m"][1][1]))

    def test_all_closed_box_faces_point_outward(self):
        for part in self.parts:
            center = [sum(v[k] for v in part["vertices"])/8 for k in range(3)]
            for face in part["faces"]:
                a,b,c = (part["vertices"][i] for i in face[:3])
                u,v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
                n = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                self.assertGreater(sum(n[k]*(a[k]-center[k]) for k in range(3)), 0, part["name"])

    def test_parametric_larger_bay_preserves_relative_clear_corridor(self):
        r=dict(self.recipe,width=8.0,length=10.0,eave_height=3.0,ridge_height=4.0,bed_length=8.0)
        stats=bay.validate_geometry(r,bay.geometry(r))
        self.assertEqual(8,stats["mesh_count"])
        self.assertAlmostEqual(-6,stats["bounds_m"][0][1],places=12)
        self.assertAlmostEqual(6,stats["bounds_m"][1][1],places=12)

    def test_roof_meets_ridge_and_has_headroom_at_both_sides(self):
        roofs = [p for p in self.parts if p["name"].startswith("RoofGlass")]
        self.assertEqual(2, len(roofs))
        for roof in roofs:
            lo,hi=bay.bounds(roof)
            self.assertLess(abs(hi[2]-self.recipe["ridge_height"]), .02)
            self.assertGreater(lo[2], 2.6)

    def test_removed_path_tile_is_rejected(self):
        parts=[p for p in self.parts if p["name"] != "Path_10"]
        with self.assertRaisesRegex(ValueError,"support gap"):
            bay.validate_geometry(self.recipe,parts)

    def test_repeat_socket_accounts_for_path_aprons_without_coplanar_overlap(self):
        sockets=bay.socket_positions(self.recipe)
        self.assertEqual([0,-5,0],sockets["Entry"])
        self.assertEqual([0,5,0],sockets["Repeat"])
        pitch=sockets["Repeat"][1]-sockets["Entry"][1]
        intervals=[bay.bounds(p) for p in self.parts if p["role"]=="path"]
        end=max(hi[1] for lo,hi in intervals)
        next_start=min(lo[1] for lo,hi in intervals)+pitch
        self.assertAlmostEqual(end,next_start,places=12)

    def test_low_beam_or_crop_intruding_into_corridor_is_rejected(self):
        for name in ("Ridge","Leaf_1_0_1"):
            parts=copy.deepcopy(self.parts)
            p=next(p for p in parts if p["name"]==name)
            center=[sum(v[k] for v in p["vertices"])/8 for k in range(3)]
            p["vertices"]=[(v[0]-center[0],v[1],v[2]-center[2]+1.5) for v in p["vertices"]]
            with self.assertRaisesRegex(ValueError,"obstructs"):
                bay.validate_geometry(self.recipe,parts)

    def test_grouping_preserves_all_faces_vertices_material_roles(self):
        grouped=bay.group_geometry(self.parts)
        self.assertEqual(sum(len(p["vertices"]) for p in self.parts),sum(len(g["vertices"]) for g in grouped.values()))
        self.assertEqual(sum(len(p["faces"]) for p in self.parts),sum(len(g["faces"]) for g in grouped.values()))
        for group in grouped.values():
            self.assertTrue(all(0 <= i < len(group["vertices"]) for f in group["faces"] for i in f))

    def test_corrupt_mesh_rejected(self):
        for bad in (float("nan"),float("inf")):
            parts=copy.deepcopy(self.parts)
            parts[0]["vertices"][0]=(bad,0,0)
            with self.assertRaisesRegex(ValueError,"invalid material/vertex"):
                bay.validate_geometry(self.recipe,parts)


if __name__ == "__main__":
    unittest.main()
