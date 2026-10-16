"""Thin adapter file/binding contract tests, no Blender mocks or execution."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import stat

import shardstead_willow_wetland_polish_r2_blender as adapter


class AdapterContract(unittest.TestCase):
    def test_nonfollowing_metadata_accepts_ordinary_ancestors(self):
        ordinary=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0)
        with patch.object(Path,'lstat',return_value=ordinary), \
             patch.object(Path,'stat',side_effect=AssertionError('must not follow')):
            adapter.no_reparse(Path('ordinary')/'source.blend')
        self.assertNotIn('bpy',sys.modules)

    def test_missing_tail_cannot_hide_junction_like_parent(self):
        target=Path('ordinary')/'junction-like'/'missing'/'source.blend'
        junction=target.absolute().parents[1]
        ordinary=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0)
        def metadata(path):
            if path==junction:
                return SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)
            if path in (target.absolute(),target.absolute().parent):
                raise FileNotFoundError('mock missing output tail')
            return ordinary
        with patch.object(Path,'lstat',metadata), \
             patch.object(Path,'stat',side_effect=AssertionError('must not follow')):
            with self.assertRaisesRegex(ValueError,'symlink/reparse'):
                adapter.no_reparse(target)
        self.assertNotIn('bpy',sys.modules)

    def test_metadata_errors_fail_closed(self):
        with patch.object(Path,'lstat',side_effect=PermissionError('metadata unavailable')):
            with self.assertRaises(PermissionError): adapter.no_reparse('unreadable')

    def test_output_guard_refuses_before_writes_or_bpy(self):
        root=(Path('ordinary')/'junction-like').absolute()
        def metadata(path):
            if path==root:
                return SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)
            if root in path.parents: raise FileNotFoundError('mock missing tail')
            return SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0)
        with patch.object(Path,'lstat',metadata), \
             patch.object(Path,'open',side_effect=AssertionError('no file writes')), \
             patch.object(Path,'mkdir',side_effect=AssertionError('no directory writes')):
            with self.assertRaisesRegex(ValueError,'symlink/reparse'): adapter.output_path(root)
        self.assertNotIn('bpy',sys.modules)

    def test_pure_import_and_descriptor_consumption(self):
        self.assertNotIn('bpy',sys.modules)
        plan=adapter.geometry.build()
        adapter.validate_descriptors(plan)
        self.assertEqual(sum(len(m['triangles']) for m in plan['exported']),6496)

    def test_exact_owned_binding_inventory(self):
        inventory,replaced=adapter.bindings()
        adapter.validate_inventory(inventory)
        self.assertEqual(len([name for name in inventory if name.endswith('_Trunk')]),4)
        self.assertEqual(len([name for name in inventory if name.startswith('DecorativeReed_')]),40)
        self.assertNotIn('Synthetic_WillowPilot_Ground',replaced)
        self.assertNotIn('ExistingRescuerReference',replaced)
        self.assertEqual(len(replaced),78)

    def test_missing_extra_wrong_type_or_role_refuses(self):
        expected,_=adapter.bindings()
        for mutation in ('missing','extra','type','role'):
            with self.subTest(mutation=mutation):
                actual=expected.copy()
                if mutation=='missing': actual.pop('Synthetic_North_Path')
                elif mutation=='extra': actual['OtherOwnerProp']=('MESH',None)
                elif mutation=='type': actual['Willow_0_Trunk']=('MESH','flora')
                else: actual['Willow_0_Trunk']=('CURVE','resources')
                with self.assertRaises(ValueError): adapter.validate_inventory(actual)

    def test_unknown_role_material_or_index_refuses(self):
        for mutation in ('role','material','index','pivot'):
            with self.subTest(mutation=mutation):
                plan=adapter.geometry.build()
                mesh=plan['exported'][0]
                if mutation=='role': mesh['role']='unknown'
                elif mutation=='material': mesh['materials'][0]='external'
                elif mutation=='index': mesh['material_indices'][0]=999
                else: mesh['pivot']=[1,0,0]
                with self.assertRaises(ValueError): adapter.validate_descriptors(plan)

    def test_new_output_only_no_directory_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            output=adapter.output_path(root)
            self.assertFalse(output.exists())
            output.mkdir(parents=True)
            with self.assertRaises(ValueError): adapter.output_path(root)

    def test_source_hash_checks_actual_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.blend'
            path.write_bytes(b'not-a-real-blend')
            self.assertEqual(adapter.digest(path),hashlib.sha256(b'not-a-real-blend').hexdigest())
            self.assertNotEqual(adapter.digest(path),adapter.SCENE_SHA)

    def test_execute_requires_correct_adapter_pin_before_bpy_import(self):
        with self.assertRaises(ValueError): adapter.author('unused.blend','wrong')
        self.assertNotIn('bpy',sys.modules)

    def test_material_aliases_preserve_r1_intent(self):
        self.assertEqual(adapter.MATERIALS['leaf_sage'],adapter.MATERIALS['leaf_light'])
        self.assertEqual(adapter.MATERIALS['reed'],adapter.MATERIALS['reed_seed'])
        self.assertEqual(adapter.MATERIALS['shore_soil'][0],'Pilot_SageGround')

    def test_ordinary_cli_refuses_implicit_author_without_bpy(self):
        script=Path(adapter.__file__)
        result=subprocess.run([sys.executable,'-B',str(script),'--stage','author',
                               '--r1-scene','unused.blend'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Author requires explicit',result.stderr)
        self.assertNotIn('No module named',result.stderr)


if __name__=='__main__':
    unittest.main()
