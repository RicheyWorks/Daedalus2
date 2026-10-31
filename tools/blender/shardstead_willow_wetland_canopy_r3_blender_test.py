"""Only new R3 consumer contracts; no Blender/API execution or fake render proof."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import shardstead_willow_wetland_canopy_r3_blender as entry


class CopyAuthorViews(unittest.TestCase):
    def test_actual_3072_willow_only_replacement_contract(self):
        plan=entry.canopy.build();reference=entry.canopy.reference().build()
        entry.replacement_contract(plan,reference)
        self.assertEqual(len(plan['exported'][0]['triangles']),3072)
        for mutation in ('nonwillow','material','pivot','count'):
            changed=copy.deepcopy(plan)
            if mutation=='nonwillow': changed['exported'][1]['vertices'][0]=(999,999,999)
            elif mutation=='material': changed['exported'][0]['materials'][0]='unknown'
            elif mutation=='pivot': changed['exported'][0]['pivot']=[1,0,0]
            else: changed['exported'][0]['triangles'].pop()
            with self.assertRaises(ValueError): entry.replacement_contract(changed,reference)

    def test_literal_new_root_and_partial_no_replay(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(entry,'ROOT',Path(folder)):
            output=entry.destination()
            self.assertEqual(output.name,'pilot-r3')
            self.assertFalse(output.exists())
            output.mkdir(parents=True)
            (output/'R2-input-copy.blend').write_bytes(b'partial retained fixture')
            with self.assertRaisesRegex(ValueError,'partial'): entry.destination()
            self.assertEqual((output/'R2-input-copy.blend').read_bytes(),b'partial retained fixture')

    def test_pin_and_execute_boundary_precedes_bpy(self):
        with self.assertRaisesRegex(ValueError,'Self SHA'): entry.execute('wrong')
        with patch.object(entry.r2views.author,'digest',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'R3 source pin'): entry.preflight()
        self.assertNotIn('bpy',sys.modules)

    def test_protected_snapshot_includes_nonwillow_and_excludes_only_willow(self):
        def marker(name):
            return SimpleNamespace(name=name,type='EMPTY',location=[1.,2.,3.],rotation_euler=[0.,0.,0.],
                                   scale=[1.,1.,1.],parent=None,users_collection=[])
        willow=marker('WillowPilot_Willow');protected=marker('ExistingRescuerReference')
        model=SimpleNamespace(data=SimpleNamespace(objects=[willow,protected]))
        first=entry.protected_snapshot(model)
        willow.location[0]=100
        self.assertEqual(entry.protected_snapshot(model),first)
        protected.location[0]=100
        self.assertNotEqual(entry.protected_snapshot(model),first)

    def test_matched_settings_remain_exact_r2_and_material_aliases(self):
        plan=entry.canopy.build();r2=entry.canopy.reference().build()
        self.assertEqual(plan['context_recipe']['views'],r2['recipe']['views'])
        self.assertEqual(plan['context_recipe']['render'],r2['recipe']['render'])
        labels=plan['exported'][0]['materials']
        self.assertEqual([entry.r2views.author.MATERIALS[label][0] for label in labels],
                         [entry.r2views.author.PREFIX+'_willow_bark']+[entry.r2views.author.PREFIX+'_willow_leaf']*2)

    def test_isolated_bootstrap_and_inert_default(self):
        code=r'''
import pathlib,runpy,sys
from unittest.mock import patch
script=pathlib.Path(sys.argv[1])
assert str(script.parent) not in sys.path
scope=runpy.run_path(str(script),run_name='inert_r3_consumer')
plan=scope['canopy'].build()
main=scope['main']
fixture=lambda:(plan,None,pathlib.Path('not-created'),{}, {})
with patch.dict(main.__globals__,{'preflight':fixture}), patch.object(pathlib.Path,'mkdir',side_effect=AssertionError('no writes')):
    main([])
assert 'bpy' not in sys.modules
print('ISOLATED_DEFAULT_NO_BPY_NO_WRITES')
'''
        run=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(Path(entry.__file__))],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('SOURCE_ONLY_DRY_RUN',run.stdout)
        self.assertIn('ISOLATED_DEFAULT_NO_BPY_NO_WRITES',run.stdout)


if __name__=='__main__':
    unittest.main()
