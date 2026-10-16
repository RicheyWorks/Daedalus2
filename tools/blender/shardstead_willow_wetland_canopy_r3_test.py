"""New pure pendulous-shape/unchanged-context tests; no visual acceptance."""
import hashlib
import math
from pathlib import Path
import subprocess
import sys
import unittest

import shardstead_willow_wetland_canopy_r3 as canopy


class PendulousCanopy(unittest.TestCase):
    def test_branch_orientation_independent_radial_and_cap_oracle(self):
        r2=canopy.reference()
        def normal(mesh,face):
            a,b,c=[mesh['vertices'][i] for i in face]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        dot=lambda a,b:sum(x*y for x,y in zip(a,b))
        profiles=[[(0.,0.,0.),(.5,0.,1.)],[(0.,0.,1.),(.5,0.,0.)],
                  [(r,0.,z) for r,z in canopy.configuration()['branch_profile']]]
        for points in profiles:
            mesh=r2.mesh('orientation','flora',['bark'])
            canopy.branch_sweep(mesh,points,.035,0,(0.,1.,0.),r2.append)
            for segment in range(len(points)-1):
                a,b=points[segment:segment+2];axis=[b[i]-a[i] for i in range(3)]
                for face in mesh['triangles'][segment*8:(segment+1)*8]:
                    centre=[sum(mesh['vertices'][v][i] for v in face)/3 for i in range(3)]
                    offset=[centre[i]-a[i] for i in range(3)]
                    projection=dot(offset,axis)/dot(axis,axis)
                    outward=[offset[i]-projection*axis[i] for i in range(3)]
                    self.assertGreater(dot(normal(mesh,face),outward),0)
            first_axis=[points[1][i]-points[0][i] for i in range(3)]
            last_axis=[points[-1][i]-points[-2][i] for i in range(3)]
            for face in mesh['triangles'][-4:-2]: self.assertLess(dot(normal(mesh,face),first_axis),0)
            for face in mesh['triangles'][-2:]: self.assertGreater(dot(normal(mesh,face),last_axis),0)
        # Actual old helper on a descending segment reproduces the reviewed sign.
        old=r2.mesh('old-oracle','flora',['bark'])
        r2.tube(old,[(0.,0.,1.),(0.,0.,0.)],.035,0,sides=4)
        face=old['triangles'][0]
        centre=[sum(old['vertices'][v][i] for v in face)/3 for i in range(3)]
        self.assertLess(dot(normal(old,face),(centre[0],centre[1],0.)),0)

    @classmethod
    def setUpClass(cls):
        cls.plan=canopy.build()
        cls.r2=canopy.reference().build()

    def test_exact_other_roles_path_layout_and_material_schema(self):
        self.assertEqual(self.plan['exported'][1:],self.r2['exported'][1:])
        self.assertEqual(self.plan['path_context'],self.r2['path_context'])
        self.assertEqual(self.plan['context_recipe'],self.r2['recipe'])
        old,new=self.r2['exported'][0],self.plan['exported'][0]
        for key in ('name','role','pivot','units','materials'):
            self.assertEqual(new[key],old[key])
        self.assertLessEqual(len(new['triangles']),len(old['triangles']))

    def test_real_geometry_finite_indexed_and_nondegenerate(self):
        mesh=self.plan['exported'][0]
        self.assertEqual(len(mesh['triangles']),len(mesh['material_indices']))
        for vertex in mesh['vertices']:
            self.assertTrue(all(math.isfinite(v) for v in vertex))
        for face,material in zip(mesh['triangles'],mesh['material_indices']):
            self.assertEqual(len(set(face)),3)
            self.assertTrue(all(type(i) is int and 0<=i<len(mesh['vertices']) for i in face))
            a,b,c=[mesh['vertices'][i] for i in face]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            self.assertGreater(sum(n*n for n in normal),1e-14)
            self.assertTrue(0<=material<len(mesh['materials']))

    def test_each_tree_stays_inside_its_actual_r2_envelope_with_same_trunk(self):
        old=self.r2['exported'][0]['vertices'];new=self.plan['exported'][0]['vertices']
        self.assertEqual(len(old)%4,0);self.assertEqual(len(new)%4,0)
        for tree in range(4):
            before=old[tree*(len(old)//4):(tree+1)*(len(old)//4)]
            after=new[tree*(len(new)//4):(tree+1)*(len(new)//4)]
            # R2's exact original tube has 3 rings * 6 sides at each tree start.
            self.assertEqual(after[:18],before[:18])
            for axis in range(3):
                self.assertGreaterEqual(min(p[axis] for p in after),min(p[axis] for p in before)-1e-9)
                self.assertLessEqual(max(p[axis] for p in after),max(p[axis] for p in before)+1e-9)

    def test_actual_downcurving_branches_and_attached_tapered_hanging_mesh(self):
        mesh=self.plan['exported'][0]
        self.assertEqual({s['tree_index'] for s in self.plan['structures']},{0,3,6,9})
        self.assertEqual(len(self.plan['structures']),32)
        for structure in self.plan['structures']:
            line=structure['centreline']
            self.assertGreater(line[1][2],line[0][2])
            self.assertTrue(all(b[2]<a[2] for a,b in zip(line[1:],line[2:])))
            self.assertGreater(line[1][2]-line[-1][2],2.)
            for ribbon in structure['curtains']:
                centres=ribbon['centres'];start,end=ribbon['vertex_range']
                self.assertEqual(centres[0],ribbon['attachment'])
                self.assertIn(centres[0],line)
                self.assertTrue(all(b[2]<a[2] for a,b in zip(centres,centres[1:])))
                self.assertGreater(centres[0][2]-centres[-1][2],2.)
                vertices=mesh['vertices'][start:end]
                self.assertEqual(len(vertices),4*len(centres))
                for ring,centre in enumerate(centres):
                    measured=[sum(v[i] for v in vertices[4*ring:4*ring+4])/4 for i in range(3)]
                    for actual,expected in zip(measured,centre): self.assertAlmostEqual(actual,expected)
                span=lambda row:math.dist(row[0],row[1])
                self.assertLess(span(vertices[-4:]),span(vertices[:4])*.2)

    def test_reserved_path_and_refuge_clearance_unchanged(self):
        for x,y,_ in self.plan['exported'][0]['vertices']:
            self.assertFalse(-2<=x<=2 and 8<=y<=26)
            self.assertGreater(math.hypot(x,y),6.)

    def test_deterministic_default_no_bpy_or_file_writes(self):
        self.assertEqual(canopy.build(),self.plan)
        self.assertNotIn('bpy',sys.modules)
        pins={p:hashlib.sha256((canopy.ROOT/p).read_bytes()).hexdigest() for p in canopy.FROZEN}
        output=canopy.ROOT/self.plan['canopy_recipe']['output']
        before=output.exists()
        run=subprocess.run([sys.executable,'-B',str(Path(canopy.__file__))],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('SOURCE_ONLY_UNRENDERED_UNACCEPTED',run.stdout)
        self.assertEqual(output.exists(),before)
        self.assertEqual(pins,{p:hashlib.sha256((canopy.ROOT/p).read_bytes()).hexdigest() for p in canopy.FROZEN})
        self.assertTrue(all(v is None for v in self.plan['actual'].values()))


if __name__=='__main__':
    unittest.main()
