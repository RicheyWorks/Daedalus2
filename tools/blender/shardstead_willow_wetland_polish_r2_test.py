"""Pure geometry/contract checks, not rendered visual acceptance."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

import shardstead_willow_wetland_polish_r2 as source


def area2(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return sum(n*n for n in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))


def projected_height(mesh,x,y):
    hits=[]
    for face in mesh['triangles']:
        a,b,c=[mesh['vertices'][i] for i in face]
        denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denominator)<1e-12: continue
        u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
        v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
        if min(u,v,1-u-v)>=-1e-8:
            hits.append(u*a[2]+v*b[2]+(1-u-v)*c[2])
    return max(hits) if hits else None


class Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=source.build();cls.recipe=cls.plan['recipe']

    def test_no_bpy_import_or_production_receipts(self):
        self.assertNotIn('bpy',sys.modules)
        self.assertTrue(all(value is None for value in self.plan['actual'].values()))

    def test_exact_retained_r1_layout_camera_and_settings_contract(self):
        # Digests computed independently from frozen R1 recipe and authored plan,
        # not from the new mesh implementation or a newly randomized placement.
        keys=['seed','units','frame','terrain','pond','paths','refuges','unknown_shapes',
              'cast_reference','population','first_intake','views','render','actual']
        contract={k:self.recipe[k] for k in keys}
        pin=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(pin(contract),'c1618f4af22ea7deae42cd341fe3e9b7cf3d676b53c7d68ebdc563dbe75e5003')
        self.assertEqual(pin(self.recipe['placements']),'252332d7b62e9161ae65f9c357660bed083931c8236a0d8750e99424f29ab84d')

    def test_actual_flora_vertices_respect_reserved_xy_shapes(self):
        x0,y0,x1,y1=self.recipe['paths'][0]['aabb']
        for mesh in self.plan['exported'][:2]:
            for x,y,_ in mesh['vertices']:
                self.assertFalse(x0<=x<=x1 and y0<=y<=y1)
                self.assertGreater(math.hypot(x,y),self.recipe['refuges'][0]['circle'][2])

    def test_all_actual_triangles_finite_indexed_nondegenerate(self):
        for mesh in self.plan['exported']+[self.plan['path_context']]:
            self.assertEqual(mesh['pivot'],[0,0,0])
            self.assertEqual(len(mesh['triangles']),len(mesh['material_indices']))
            for vertex in mesh['vertices']:
                self.assertTrue(all(math.isfinite(v) for v in vertex))
            for face,material in zip(mesh['triangles'],mesh['material_indices']):
                self.assertEqual(len(set(face)),3)
                self.assertTrue(all(0<=i<len(mesh['vertices']) for i in face))
                self.assertGreater(area2(*(mesh['vertices'][i] for i in face)),1e-14)
                self.assertLess(material,len(mesh['materials']))

    def test_role_identities_budget_and_grounded_growth_bounds(self):
        self.assertEqual([(m['name'],m['role']) for m in self.plan['exported']],
                         [(r['name'],r['role']) for r in self.recipe['first_intake']])
        self.assertLessEqual(sum(len(m['triangles']) for m in self.plan['exported']),8000)
        willows=self.plan['exported'][0]
        centres=[p['position'] for i,p in enumerate(self.recipe['placements']) if i%3==0]
        self.assertEqual(len(centres),4)
        for x,y,z in willows['vertices']:
            centre=min(centres,key=lambda p:math.hypot(x-p[0],y-p[1]))
            self.assertLessEqual(math.hypot(x-centre[0],y-centre[1]),1.655)
            self.assertGreaterEqual(z,centre[2]-.021)
            self.assertLessEqual(z,centre[2]+3.9)

    def test_leaf_volume_and_reed_readability_are_real_meshes(self):
        willow,reeds,_=self.plan['exported']
        self.assertGreater(sum(i>0 for i in willow['material_indices']),2000)
        # Forty stems each have an actual seed-head mesh, not empty markers.
        seed_faces=sum(i==1 for i in reeds['material_indices'])
        self.assertEqual(seed_faces,40*36)
        self.assertGreater(max(v[2] for v in reeds['vertices']),1.5)

    def test_water_edge_collar_shares_contact_and_normals(self):
        pond=self.plan['exported'][2]
        water_vertices=set(tuple(v) for f,m in zip(pond['triangles'],pond['material_indices']) if m==0 for v in [pond['vertices'][i] for i in f])
        bank_vertices=set(tuple(v) for f,m in zip(pond['triangles'],pond['material_indices']) if m==1 for v in [pond['vertices'][i] for i in f])
        self.assertEqual(len(water_vertices & bank_vertices),64)
        for x,y,z in bank_vertices:
            if abs(math.hypot(x,y)-8.5)<1e-6:
                self.assertAlmostEqual(z,source.height(self.recipe,x,y))
        for face in pond['triangles']:
            a,b,c=[pond['vertices'][i] for i in face]
            self.assertGreater((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]),0)

    def test_path_contact_against_actual_collar_triangles(self):
        path=self.plan['path_context'];pond=self.plan['exported'][2]
        for x,y,z in path['vertices']:
            self.assertTrue(-2<=x<=2 and 8<=y<=26)
            self.assertAlmostEqual(z-source.surface_height(self.recipe,x,y),.025)
            contact=projected_height(pond,x,y)
            if contact is not None:
                self.assertGreater(z-contact,.015)
                self.assertLess(z-contact,.05)
        # R1's single corner plane cannot represent this midpoint contact.
        self.assertGreater(len(path['triangles']),2)

    def test_determinism_and_file_only_default(self):
        self.assertEqual(source.build(),self.plan)
        pin=hashlib.sha256(source.RECIPE.read_bytes()).hexdigest()
        result=subprocess.run([sys.executable,'-B',str(Path(source.__file__))],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SOURCE_ONLY_UNRENDERED_UNACCEPTED',result.stdout)
        self.assertEqual(hashlib.sha256(source.RECIPE.read_bytes()).hexdigest(),pin)


if __name__=='__main__':
    unittest.main()
