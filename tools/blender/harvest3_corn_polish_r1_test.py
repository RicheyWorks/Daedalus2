"""Tiny source geometry checks. No Blender, export, render, native or service calls."""
import collections
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("corn",HERE/"harvest3_corn_polish_r1.py")
corn=importlib.util.module_from_spec(spec)
spec.loader.exec_module(corn)


class CornGeometryTest(unittest.TestCase):
    def setUp(self):
        self.r=corn.load_recipe(HERE/"harvest3_corn_polish_r1.recipe.json")
        self.parts=corn.geometry(self.r)

    def test_prop_budget_and_decorative_qualification(self):
        stats=corn.validate_geometry(self.r,self.parts)
        self.assertEqual((18,2592,3,1),tuple(stats[k] for k in ("plant_count","triangles","material_slots","export_meshes")))
        self.assertIsNone(stats["world_binding"])
        self.assertFalse(stats["visual_accepted"])
        self.assertFalse(stats["native_accepted"])

    def test_eighteen_stalk_feet_preserve_exact_original_centres(self):
        centres=[]
        for part in self.parts:
            if part["role"]=="stalk":
                ring=part["vertices"][:6]
                centres.append(tuple(sum(v[k] for v in ring)/6 for k in range(3)))
        self.assertEqual(18,len(centres))
        for actual,expected in zip(centres,self.r["plant_centres_m"]):
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=12)

    def test_closed_consistently_oriented_positive_volume_parts_after_mirroring(self):
        for part in self.parts:
            edges=collections.Counter()
            volume=0
            for a,b,c in part["faces"]:
                for i,j in ((a,b),(b,c),(c,a)):edges[(i,j)]+=1
                p,q,r=(part["vertices"][i] for i in (a,b,c))
                volume+=(p[0]*(q[1]*r[2]-q[2]*r[1])+p[1]*(q[2]*r[0]-q[0]*r[2])+p[2]*(q[0]*r[1]-q[1]*r[0]))/6
            self.assertGreater(volume,0,part["name"])
            self.assertTrue(all(count==1 and edges[(j,i)]==1 for (i,j),count in edges.items()),part["name"])

    def test_new_shape_has_exposed_ears_broad_leaves_husks_and_tassels(self):
        for plant in range(18):
            parts=[p for p in self.parts if p["plant"]==plant]
            roles=collections.Counter(p["role"] for p in parts)
            self.assertEqual({"stalk":1,"leaf":3,"ear":1,"husk":2,"tassel":3},dict(roles))
            ear=next(p for p in parts if p["role"]=="ear")
            lo,hi=corn.bounds(ear["vertices"])
            self.assertGreater(hi[2]-lo[2],.3)
            self.assertGreater(max(hi[0]-lo[0],hi[1]-lo[1]),.12)
            self.assertEqual("cob",ear["material"])

    def test_original_base_height_and_envelope_are_preserved(self):
        stats=corn.validate_geometry(self.r,self.parts)
        lo,hi=stats["bounds_m"]
        source_lo,source_hi=self.r["source_bounds_blender_m"]
        anchor=self.r["source_anchor_blender_m"]
        self.assertEqual(0,lo[2])
        self.assertAlmostEqual(self.r["height_m"],hi[2],places=12)
        for k in range(3):
            self.assertGreaterEqual(lo[k]+anchor[k],source_lo[k]-1e-10)
            self.assertLessEqual(hi[k]+anchor[k],source_hi[k]+1e-10)
        self.assertAlmostEqual(0,lo[0]+hi[0],places=12)
        self.assertAlmostEqual(0,lo[1]+hi[1],places=12)

    def test_missing_ear_does_not_pass_silhouette_check(self):
        with self.assertRaisesRegex(ValueError,"incomplete corn"):
            corn.validate_geometry(self.r,[p for p in self.parts if p["name"]!="Ear_0"])

    def test_corrupt_or_degenerate_triangles_are_rejected(self):
        for change in ("nan","index","flat"):
            parts=copy.deepcopy(self.parts)
            if change=="nan":parts[0]["vertices"][0]=(float("nan"),0,0)
            elif change=="index":parts[0]["faces"][0]=(0,1,999999)
            else:parts[0]["faces"][0]=(0,0,0)
            with self.subTest(change=change),self.assertRaises(ValueError):corn.validate_geometry(self.r,parts)

    def test_changed_original_pin_is_refused_before_decoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"wrong.glb";path.write_bytes(b"not the immutable original")
            with self.assertRaisesRegex(ValueError,"original GLB pin changed"):corn.inspect_original(path)

    def test_declared_lower_triangle_budget_is_enforced(self):
        r=copy.deepcopy(self.r);r["budgets"]["max_triangles"]=2500
        with self.assertRaisesRegex(ValueError,"prop budget exceeded"):corn.validate_geometry(r,self.parts)

    def test_nonfinite_or_translucent_palette_is_rejected_before_build(self):
        for channel,value in ((0,float("nan")),(3,.5)):
            with tempfile.TemporaryDirectory() as directory:
                r=copy.deepcopy(self.r);r["materials"]["leaf"]["base_color_factor"][channel]=value
                path=Path(directory)/"bad.recipe.json";path.write_text(json.dumps(r))
                with self.assertRaisesRegex(ValueError,"invalid opaque farm palette"):corn.load_recipe(path)

    def test_before_after_share_exact_camera_and_explicit_single_node_allowlists(self):
        self.assertEqual([corn.ASSET],self.r["future_selected_allowlist"]["after"])
        self.assertEqual(["Reference_Harvest3_Corn_Before_R1"],self.r["future_selected_allowlist"]["before"])
        self.assertEqual([1100,825],self.r["matched_before_after_camera"]["resolution"])
        self.assertEqual(492,self.r["source_node_index"])
        self.assertEqual(109,self.r["source_mesh_index"])


if __name__=="__main__":
    unittest.main()
