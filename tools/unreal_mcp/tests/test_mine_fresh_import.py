import copy
import importlib.util
import math
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'mine_fresh_import.py'
spec=importlib.util.spec_from_file_location('mine_fresh_test_policy',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
T={'translation_cm':[0,0,0],'rotation_xyzw':[0,0,0,1],'scale':[1,1,1]}

def source():
 names=list(m.PARENTS)
 rows=[{'name':n,'parent_index':-1 if m.PARENTS[n] is None else names.index(m.PARENTS[n]),'local':copy.deepcopy(T)} for n in names]
 return {'schema':'daedalus.mine-fresh-source.v1','native_invoked':True,'state':'complete','errors':[],
  'pid':123,'source_sha256':m.SOURCE_SHA,'mesh_path':m.MESH,'skeleton_path':m.SKELETON,
  'mesh_reference':copy.deepcopy(rows),'skeleton_reference':copy.deepcopy(rows),
  'live_profile':{'factory_uid':m.UID,'skeleton_path':m.SKELETON,'sample_rate':24,'range_start':0,'range_stop':37/24,
    'bone_tracks':True,'bake_meshes':True,'global_offset':copy.deepcopy(T)},
  'source_oracle':{'source_sha256':m.SOURCE_SHA,'coordinate_space':'UE_LOCAL_CM',
   'source_unchanged_after_payload':True,'conversion_contract':'PINNED_GLTF_CANONICAL_TRANSLATOR_IDENTITY_ROOT_BAKED_FRAME_V1',
   'bone_parents':dict(m.PARENTS),'reference_pose':{n:copy.deepcopy(T) for n in names},
   'samples':[{'time_s':t,'poses':{n:copy.deepcopy(T) for n in names}} for t in (0.,1.)]}}

def clip(s):
 return {'schema':'daedalus.mine-fresh-clip.v1','native_invoked':True,'state':'complete','errors':[],
  'pid':123,'source_sha256':m.SOURCE_SHA,'mesh_path':m.MESH,'skeleton_path':m.SKELETON,
  'clip_skeleton_path':m.SKELETON,'asset_path':m.ASSET,'stored_source_path':'C:/owned/source.glb',
  'sample_rate':24,'range_start':0,'range_stop':37/24,'length_s':37/24,
  'track_names':[n.casefold() for n in m.PARENTS], 'skeleton_reference':copy.deepcopy(s['skeleton_reference']),
  'samples':[dict(copy.deepcopy(x),valid=True,bone_names_verified=True,
    evaluation='Source_NoRetarget_NoRootExtraction_NoCurves') for x in s['source_oracle']['samples']]}

class Proof(unittest.TestCase):
 def test_positive_and_windows_path(self):
  s=source();self.assertTrue(m.qualify_source(s,expected_pid=123)['source_qualified'])
  self.assertTrue(m.qualify_clip(s,clip(s),expected_pid=123,expected_source_path='c:\\owned\\source.glb')['fresh_clip_pose_accepted'])
 def test_double_rounding_and_sign(self):
  a=copy.deepcopy(T);b=copy.deepcopy(T);a['rotation_xyzw']=[-.605126486804856,0,0,-.7961293456262069]
  b['rotation_xyzw']=[-.6051264868048561,0,0,-.7961293456262071]
  self.assertTrue(m.equivalent(a,b));b['rotation_xyzw']=[-v for v in b['rotation_xyzw']];self.assertTrue(m.equivalent(a,b))
 def test_refuse_large_rotation_translation_scale(self):
  for key,value in [('translation_cm',[.001,0,0]),('scale',[1.001,1,1]),('rotation_xyzw',[0,0,math.sin(.001),math.cos(.001)])]:
   with self.subTest(key=key):
    other=copy.deepcopy(T);other[key]=value;self.assertFalse(m.equivalent(T,other))
 def test_refuse_nonfinite_and_nonunit(self):
  for value in (float('nan'),float('inf'),True):
   with self.subTest(value=value),self.assertRaises(m.Refused):m.close(0,value)
  other=copy.deepcopy(T);other['rotation_xyzw']=[0,0,0,2]
  with self.assertRaises(m.Refused):m.equivalent(T,other)
 def test_source_counterexamples(self):
  changes={
   'same_count_wrong_parent':lambda s:s['source_oracle']['bone_parents'].update(foot_L='spine'),
   'wrong_skeleton':lambda s:s.update(skeleton_path='/Game/Other.Other'),
   'wrong_factory_skeleton':lambda s:s['live_profile'].update(skeleton_path='/Game/Other.Other'),
   'boolean_start':lambda s:s['live_profile'].update(range_start=False),
   'wrong_source_hash':lambda s:s.update(source_sha256='0'*64),
   'missing_common':lambda s:s.pop('live_profile'),
   'range':lambda s:s['live_profile'].update(range_stop=2),
   'rate':lambda s:s['live_profile'].update(sample_rate=30),
   'bake_false':lambda s:s['live_profile'].update(bake_meshes=False),
   'offset':lambda s:s['live_profile']['global_offset']['translation_cm'].__setitem__(0,1),
   'source_pose':lambda s:s['source_oracle']['reference_pose']['foot_L']['scale'].__setitem__(0,1.01),
   'reference_parent':lambda s:s['skeleton_reference'][10].update(parent_index=2),
   'held':lambda s:s.update(state='held'),
   'missing_bone':lambda s:s['source_oracle']['reference_pose'].pop('head')}
  for name,change in changes.items():
   with self.subTest(name=name):
    s=source();change(s)
    with self.assertRaises((m.Refused,KeyError)):m.qualify_source(s,expected_pid=123)
 def test_clip_counterexamples(self):
  changes={
   'wrong_source':lambda c:c.update(stored_source_path='C:/other.glb'),
   'wrong_skeleton':lambda c:c.update(clip_skeleton_path='/Game/Other.Other'),
   'wrong_asset':lambda c:c.update(asset_path=m.MESH),
   'same_count_wrong_tracks':lambda c:c['track_names'].__setitem__(0,'other_root'),
   'wrong_timing':lambda c:c.update(length_s=1.9),
   'sample_changed':lambda c:c['samples'][1]['poses']['head']['translation_cm'].__setitem__(0,.001),
   'missing_sample':lambda c:c['samples'].pop(),
   'wrong_evaluation':lambda c:c['samples'][0].update(evaluation='Compressed'),
   'stale_pid':lambda c:c.update(pid=321)}
  for name,change in changes.items():
   with self.subTest(name=name):
    s=source();c=clip(s);change(c)
    with self.assertRaises(m.Refused):m.qualify_clip(s,c,expected_pid=123,expected_source_path='C:/owned/source.glb')

if __name__=='__main__':unittest.main()
