"""Focused portable cabbage geometry/provenance tests; no Blender mocks."""
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("cabbage_r1",HERE/"harvest3_cabbage_polish_r1.py")
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)


class Cabbage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=g.load_recipe(HERE/"harvest3_cabbage_polish_r1.recipe.json")
        cls.parts=g.geometry(cls.recipe)

    def test_actual_decoded_cabbage_identity_and_layout_facts(self):
        r=self.recipe
        self.assertEqual((r["source_node_index"],r["source_mesh_index"],r["source_material_index"]),(491,108,32))
        self.assertEqual(r["source_accessors"],{"POSITION":299,"NORMAL":300,"indices":301})
        self.assertEqual(r["plant_count"],len(r["source_geometry"]["component_vertices"]))
        self.assertEqual(r["plant_count"],18)  # Observed cabbage result, not a generator assumption.
        self.assertEqual(set(r["source_geometry"]["component_vertices"]),{20})
        self.assertEqual(len({tuple(v) for v in r["plant_centres_m"]}),18)
        self.assertEqual(r["source_anchor_blender_m"],[-56.0,-51.20000076293945,0.10000020265579224])

    def test_explicit_compact_material_and_triangle_budgets(self):
        stats=g.validate_geometry(self.recipe,self.parts)
        self.assertEqual((stats["triangles"],stats["material_slots"],stats["export_meshes"]),(2592,3,1))
        self.assertEqual(len(self.parts),126)
        self.assertIsNone(stats["world_binding"])
        self.assertFalse(stats["native_accepted"])
        self.assertFalse(stats["visual_accepted"])
        self.assertNotIn("bpy",sys.modules)

    def test_every_component_closed_oriented_with_positive_volume(self):
        for part in self.parts:
            edges=Counter();volume=0
            for face in part["faces"]:
                a,b,c=(part["vertices"][i] for i in face)
                volume+=sum(a[k]*v for k,v in enumerate((b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])))/6
                for i,j in zip(face,face[1:]+face[:1]):edges[(i,j)]+=1
            with self.subTest(part=part["name"]):
                self.assertGreater(volume,0)
                self.assertTrue(all(count==1 and edges[(b,a)]==1 for (a,b),count in edges.items()))

    def test_concave_inner_leaf_triangulation_covers_projected_outline(self):
        for part in (p for p in self.parts if p["role"]=="inner_leaf"):
            outline=part["vertices"][:5]
            polygon_area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(outline,outline[1:]+outline[:1])))/2
            areas=[]
            for face in part["faces"]:
                if all(i<5 for i in face):
                    a,b,c=(part["vertices"][i] for i in face)
                    areas.append(((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2)
            self.assertEqual(len(areas),3)
            self.assertTrue(all(a>0 for a in areas))
            self.assertAlmostEqual(sum(areas),polygon_area,places=11)
            self.assertGreater(max(v[2] for v in outline)-min(v[2] for v in outline),.7*self.recipe["height_m"])

    def test_each_original_centre_has_head_and_two_complete_leaf_layers(self):
        h=self.recipe["height_m"]
        for index,centre in enumerate(self.recipe["plant_centres_m"]):
            group=[p for p in self.parts if p["plant"]==index]
            self.assertEqual(Counter(p["role"] for p in group),{"head":1,"outer_leaf":3,"inner_leaf":3})
            heart=next(p for p in group if p["role"]=="head")
            self.assertEqual(heart["vertices"][-1],(centre[0],centre[1],centre[2]+h))

    def test_original_base_height_envelope_and_pivot_preserved(self):
        lo,hi=g.validate_geometry(self.recipe,self.parts)["bounds_m"]
        self.assertAlmostEqual(lo[2],0)
        self.assertAlmostEqual(hi[2],self.recipe["height_m"])
        for k in (0,1):self.assertAlmostEqual(lo[k]+hi[k],0)
        original=self.recipe["source_bounds_blender_m"];anchor=self.recipe["source_anchor_blender_m"]
        self.assertTrue(all(original[0][k]-1e-8<=lo[k]+anchor[k] and hi[k]+anchor[k]<=original[1][k]+1e-8 for k in range(3)))

    def test_missing_inner_leaf_or_displaced_head_is_rejected(self):
        parts=copy.deepcopy(self.parts);parts.remove(next(p for p in parts if p["role"]=="inner_leaf"))
        with self.assertRaisesRegex(ValueError,"leaf layer"):g.validate_geometry(self.recipe,parts)
        parts=copy.deepcopy(self.parts);heart=next(p for p in parts if p["role"]=="head" and p["plant"]==4)
        heart["vertices"]=[(x+.05,y,z) for x,y,z in heart["vertices"]]
        with self.assertRaisesRegex(ValueError,"planting centre"):g.validate_geometry(self.recipe,parts)

    def test_corrupt_vertices_indices_and_degenerate_faces_rejected(self):
        for mutate in (lambda p:p[0]["vertices"].__setitem__(0,(float("nan"),0,0)),
                       lambda p:p[0]["faces"].__setitem__(0,(0,1,99999)),
                       lambda p:p[0]["faces"].__setitem__(0,(0,0,0))):
            parts=copy.deepcopy(self.parts);mutate(parts)
            with self.assertRaises(ValueError):g.validate_geometry(self.recipe,parts)

    def test_declared_lower_triangle_or_slot_budget_rejected(self):
        for key,value in (("max_triangles",2591),("max_material_slots",2)):
            r=copy.deepcopy(self.recipe);r["budgets"][key]=value
            with self.assertRaisesRegex(ValueError,"budget"):g.validate_geometry(r,self.parts)

    def test_nonfinite_or_translucent_palette_rejected_before_build(self):
        for color in ([float("nan"),.7,.25,1],[.5,.7,.25,.5]):
            r=copy.deepcopy(self.recipe);r["materials"]["heart"]["base_color_factor"]=color
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"recipe.json";path.write_text(json.dumps(r),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"opaque farm palette"):g.load_recipe(path)

    def test_changed_original_pin_rejected_before_any_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"changed.glb";path.write_bytes(b"unrelated bytes")
            with self.assertRaisesRegex(ValueError,"original GLB pin changed"):g.inspect_original(path)

    def test_deterministic_source_and_future_scene_contract(self):
        self.assertEqual(self.parts,g.geometry(self.recipe))
        self.assertEqual(self.recipe["future_selected_allowlist"],{"before":["Reference_Harvest3_Cabbage_Before_R1"],"after":["Prop_Harvest3_Cabbage_Polish_R1"]})
        self.assertIn("SIX",self.recipe["future_route"]["preserve"])
        self.assertIn("Mesh.bl_rna.functions",self.recipe["future_route"]["required"])


if __name__=="__main__":unittest.main()
