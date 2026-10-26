# SPDX-License-Identifier: MIT
"""Offline closed-adapter policy/reconciliation tests. No Unreal/network."""
import copy
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unattended_codex_adapter as a


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.entry={'name':a.NAME,'kind':'module','fbx':{'path':str(self.root/'source.fbx'),'sha256':a.SOURCE_SHA,'bytes':19228},
          'objects':[{'triangles':416,'dims':[4.0,1.0,0.5]}]}
        self.manifest={'schema':'daedalus.codex-prepared-delivery.v1','assets':[self.entry]+[{'name':'unused'+str(i)} for i in range(23)]}
        self.cfg={'schema':a.VERSION,'selected_name':a.NAME,'expect':{'triangles':416,'material_slots':2,'nanite':False,'simple_collision':0},'start_by_utc':'2026-10-22T23:00:00Z'}
        for key in ('source_manifest','importer','native','guard','parity','baseline','material'):
            p=self.root/(key+'.fixture');p.write_bytes(b'fixture');self.cfg[key]={'path':str(p),'sha256':'0'*64,'bytes':7}
        self.item={'id':'Coupler','sources':[copy.deepcopy(self.entry['fbx'])],
            'destination':a.ROOT+'UnattendedWitness20261022/R1/Coupler',
            'policy':{'path':str(self.root/'policy.json'),'sha256':'0'*64,'bytes':7}}

    def policy(self):
        (self.root/'policy.json').write_text(json.dumps(self.cfg));Path(self.cfg['source_manifest']['path']).write_text(json.dumps(self.manifest))
        # The runner separately verifies actual bytes; this isolates policy
        # semantics without copying production files or falsifying native data.
        with patch.object(a.q,'checked_file',side_effect=lambda row:Path(row['path'])):
            return a.policy(self.item)

    def test_exact_closed_policy(self):
        self.assertEqual(self.policy()['expect']['triangles'],416)

    def test_reject_changed_source_or_unowned_destination(self):
        self.entry['fbx']['sha256']='1'*64
        with self.assertRaises(a.q.Refused):self.policy()
        self.entry['fbx']['sha256']=a.SOURCE_SHA;self.item['destination']='/Game/Other/Coupler'
        with self.assertRaises(a.q.Refused):self.policy()

    def test_no_relaxed_geometry_or_material_policy(self):
        for key,value in (('triangles',415),('simple_collision',1),('material_slots',1),('nanite',True)):
            with self.subTest(key=key):
                old=self.cfg['expect'][key];self.cfg['expect'][key]=value
                with self.assertRaises(a.q.Refused):self.policy()
                self.cfg['expect'][key]=old

    def test_naive_deadline_refused(self):
        self.cfg['start_by_utc']='2026-10-22T23:00:00'
        with self.assertRaises(a.q.Refused):self.policy()

    def instance(self):
        obj=object.__new__(a.Adapter);obj.folder=self.root
        return obj

    def test_unknown_import_never_reexecutes(self):
        obj=self.instance();obj._native=lambda *args,**kw:self.fail('No native call allowed')
        self.assertEqual(obj.reconcile(self.item,'op'),{'state':'pending'})

    def test_uncertain_validation_never_reexecutes(self):
        obj=self.instance();p=self.root/'native/op/import';p.mkdir(parents=True)
        (p/'terminal.json').write_text('{}')
        v=self.root/'native/op/validate';v.mkdir();(v/'native-dispatch.json').write_text('{}')
        obj._native=lambda *args,**kw:self.fail('No replay allowed')
        self.assertEqual(obj.reconcile(self.item,'op'),{'state':'pending'})

    def test_complete_receipt_read_without_native_replay(self):
        obj=self.instance();p=self.root/'native';p.mkdir();result={'test':'synthetic'}
        (p/'op.json').write_text(json.dumps(result))
        obj._native=lambda *args,**kw:self.fail('No replay allowed')
        self.assertEqual(obj.reconcile(self.item,'op'),{'state':'complete','result':result})

    def test_execute_dispatches_import_once_only(self):
        obj=self.instance();calls=[]
        obj._native=lambda *args,**kw:calls.append(args)
        obj._completion=lambda *args:{'test':'synthetic'}
        self.assertEqual(obj.execute(self.item,'op',[],str(self.root/'r.json')),{'test':'synthetic'})
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][1],'import')

    def test_embedded_source_compiles_without_execution(self):
        p=Path(a.__file__).with_name('unattended_codex_native.inc')
        compile(p.read_bytes(),str(p),'exec')

    def test_actual_palette_comparator_uses_object_not_path_spelling(self):
        p=Path(a.__file__).with_name('unattended_codex_native.inc')
        tree=ast.parse(p.read_bytes())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='palette_matches')
        scope={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(p),'exec'),scope)
        palette=object();other=object()
        class Mesh:
            def __init__(self,slots):self.slots=slots
            def get_material(self,i):return self.slots[i]
            def get_editor_property(self,key):return self.slots
        self.assertTrue(scope['palette_matches'](Mesh([palette,palette]),palette))
        for slots,expected in (([other,other],palette),([palette,other],palette),([palette,palette],None)):
            self.assertFalse(scope['palette_matches'](Mesh(slots),expected))


if __name__=='__main__':unittest.main()
