import copy,importlib.util,math,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'mine_sequencer_diagnostic.py'
spec=importlib.util.spec_from_file_location('mine_sequencer_test',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def channels():
 return [{'name':bone+'_CONTROL.'+kind+'.'+axis,'class':'/Script/SequencerScripting.MovieSceneScriptingFloatChannel','key_count':0,'keys':[],'stored_default_present':True,'stored_default':1 if kind=='Scale' else 0} for bone in ('forearm_l','forearm_r') for kind in ('Location','Rotation','Scale') for axis in 'XYZ']

class Decoder(unittest.TestCase):
 def test_identity_and_explicit_zero_default(self):
  value=m.decode_forearm_channels(channels(),'forearm_L',24)
  self.assertEqual(value,{'translation_cm':[0,0,0],'rotation_xyzw':[0,0,0,1],'scale':[1,1,1]})
 def test_euler_axis_known_vectors(self):
  h=math.sqrt(.5)
  for angles,expected in [([90,0,0],[-h,0,0,h]),([0,90,0],[0,-h,0,h]),([0,0,90],[0,0,h,h])]:
   with self.subTest(angles=angles):
    for actual,wanted in zip(m.quaternion_from_euler_degrees(angles),expected):self.assertAlmostEqual(actual,wanted,places=14)
 def test_exact_requested_key(self):
  rows=channels();rows[0].update(key_count=38,keys=[{'frame':0,'sub_frame':0,'value':2},{'frame':24,'sub_frame':0,'value':3}],stored_default_present=False)
  self.assertEqual(m.decode_forearm_channels(rows,'forearm_L',24)['translation_cm'][0],3)
 def test_missing_or_ambiguous_data_refused(self):
  changes=[lambda x:x[0].update(stored_default_present=False),lambda x:x[0].update(key_count=38,keys=[]),lambda x:x[0].update(name=x[1]['name']),lambda x:x[0].update(stored_default=float('nan')),lambda x:x[0].update(stored_default=True),lambda x:x[0].update(**{'class':'Other'}),lambda x:x[0].update(name='forearm_l_CONTROL.Other.X')]
  for change in changes:
   with self.subTest(change=change):
    rows=channels();change(rows)
    with self.assertRaises(m.Refused):m.decode_forearm_channels(rows,'forearm_L',0)
 def test_no_frame_or_bone_substitution(self):
  for bone,frame in [('other',0),('forearm_L',True),('forearm_L',1)]:
   with self.assertRaises(m.Refused):m.decode_forearm_channels(channels(),bone,frame)
 def test_nonfinite_euler_refused(self):
  for value in (float('inf'),float('nan'),False):
   with self.assertRaises(m.Refused):m.quaternion_from_euler_degrees([value,0,0])

if __name__=='__main__':unittest.main()
