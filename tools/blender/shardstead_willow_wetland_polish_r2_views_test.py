"""New matched-view file/contract regressions only; no bpy/render mocks."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import shardstead_willow_wetland_polish_r2_views as views


class ViewsContract(unittest.TestCase):
    def test_exact_frozen_r1_view_and_light_settings_digest(self):
        recipe=views.author.geometry.configuration()
        contract={'views':recipe['views'],'render':recipe['render']}
        pin=hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(pin,'08aee82df277979f354308a6ff204307629ff7aa2708b0c50af62b3b165a2af1')

    def test_isolated_default_invocation_does_not_import_bpy_or_write(self):
        code=r'''
import pathlib,runpy,sys
from unittest.mock import patch
script=pathlib.Path(sys.argv[1])
scope=runpy.run_path(str(script),run_name='fileonly_consumer')
with patch.object(pathlib.Path,'mkdir',side_effect=AssertionError('no directories')):
    try: scope['main'](['--scene','wrong.blend','--r1-source','unused','--r1-views','unused'])
    except ValueError as error: assert 'exact owned' in str(error)
    else: raise AssertionError('wrong scene accepted')
assert 'bpy' not in sys.modules
print('FILEONLY_NO_BPY_NO_WRITES')
'''
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(Path(views.__file__))],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('FILEONLY_NO_BPY_NO_WRITES',result.stdout)

    def test_exact_authored_inventory_contract(self):
        plan=views.author.geometry.build()
        inventory=views.expected_inventory(plan)
        self.assertEqual(len(inventory),12)
        self.assertEqual(inventory['WillowPilot_Willow'],('MESH','flora'))
        self.assertEqual(inventory['WillowPilot_Pond'],('MESH','habitats'))
        self.assertIn('Synthetic_WillowPilot_Ground',inventory)
        self.assertIn('ExistingRescuerReference',inventory)
        self.assertFalse(any(name.startswith('Willow_') for name in inventory))
        self.assertNotIn('bpy',sys.modules)

    def test_wrong_scene_and_receipt_pins_refuse_before_bpy(self):
        with self.assertRaisesRegex(ValueError,'exact owned'):
            views.preflight('other-scene.blend','unused','unused')
        correct=views.ROOT/'artifacts/biomes/shardstead/WillowWetland/pilot-r2/WillowPilotR2.blend'
        with patch.object(views.author,'digest',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'scene bytes'):
                views.preflight(correct,'unused','unused')
        def wrong_receipt(path):
            return views.SCENE_SHA if Path(path)==correct else 'wrong'
        with patch.object(views.author,'digest',side_effect=wrong_receipt):
            with self.assertRaisesRegex(ValueError,'authored receipt'):
                views.preflight(correct,'unused','unused')
        self.assertNotIn('bpy',sys.modules)

    def test_occupied_or_reparse_output_refuses_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            scene=Path(folder)/'WillowPilotR2.blend'
            target=views.fresh_output(scene)
            self.assertFalse(target.exists())
            target.mkdir()
            with self.assertRaisesRegex(ValueError,'occupied'): views.fresh_output(scene)
        ordinary=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0)
        root=Path('junction-like').absolute()
        def metadata(path):
            if path==root: return SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)
            if root in path.parents: raise FileNotFoundError('mock missing tail')
            return ordinary
        with patch.object(Path,'lstat',metadata),patch.object(Path,'mkdir',side_effect=AssertionError('no writes')):
            with self.assertRaisesRegex(ValueError,'symlink/reparse'):
                views.fresh_output(root/'missing'/'WillowPilotR2.blend')

    def test_matched_contract_refuses_camera_or_settings_change(self):
        recipe=views.author.geometry.configuration()
        receipt=dict(matched_view_contract=copy.deepcopy(recipe['views']),render_contract=copy.deepcopy(recipe['render']),
                     exports=None,views=None,reopened=None,native=None,quality_accepted=None)
        views.matched_contract(receipt,recipe)
        receipt['matched_view_contract'][0]['lens']=50
        with self.assertRaisesRegex(ValueError,'mismatch'): views.matched_contract(receipt,recipe)
        receipt['matched_view_contract']=copy.deepcopy(recipe['views'])
        receipt['render_contract']['samples']=1
        with self.assertRaisesRegex(ValueError,'mismatch'): views.matched_contract(receipt,recipe)

    def test_png_dimensions_are_read_not_assumed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'header-only.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',321,123))
            self.assertEqual(views.png_dimensions(path),[321,123])
            path.write_bytes(b'invalid')
            with self.assertRaises(ValueError): views.png_dimensions(path)

    def test_wrong_execute_sha_refuses_without_bpy_or_output(self):
        with self.assertRaisesRegex(ValueError,'SHA differs'):
            views.render('unused','unused','unused','wrong')
        self.assertNotIn('bpy',sys.modules)


if __name__=='__main__':
    unittest.main()
