# SPDX-License-Identifier: MIT
"""Focused offline Corn recovery regressions; no engine, network or process IO.

The native module loads against a rejecting Unreal stub. The host run function
is isolated by AST so its production transport/bootstrap cannot be imported.
Only temporary fixture journals are written. These checks are not native proof.
"""
import ast
import copy
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


REPO = Path(__file__).resolve().parents[2]
NATIVE = REPO / 'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_corn.py'
HOST = Path(__file__).with_name('codex_skyfarm_corn_delivery.py')
ROOT = '/Game/Daedalus/Art/SkyFarm/CornPolishR1'
REAL_PATHS = (
    ROOT + '/Harvest3_CornPolish_R1.Harvest3_CornPolish_R1',
    ROOT + '/H3C_R1_AFTER_stalk.H3C_R1_AFTER_stalk',
    ROOT + '/H3C_R1_AFTER_leaf.H3C_R1_AFTER_leaf',
    ROOT + '/H3C_R1_AFTER_cob.H3C_R1_AFTER_cob',
)
ORIGINAL_SHA = '69d92bbfe85c5fab610bf003ebc9f2741ff909b199ec8d226844119860754878'
NOW = datetime(2026, 10, 16, 10, 45, tzinfo=timezone.utc).timestamp()


class BoundaryReached(Exception):
    """A mocked boundary was reached; no production action was performed."""


class NoUnreal(ModuleType):
    def __getattr__(self, name):
        raise AssertionError('Unreal API forbidden in offline test: ' + name)


def load_native():
    module = ModuleType('_offline_corn_recovery')
    module.__file__ = str(NATIVE)
    with patch.dict(sys.modules, unreal=NoUnreal('unreal')):
        exec(compile(NATIVE.read_bytes(), str(NATIVE), 'exec'), module.__dict__)
    return module


def original_fixture():
    return {
        'stage': 'CORN_KNOWN_TERMINAL_PARTIAL_HOLD',
        'error': 'exact four unsaved import outputs required',
        'intents': [{'operation': 'import_exact_after_glb_once'}],
        'saves': [], 'new_actor': None, 'map_save_return': None,
        # Actual retained import order was three materials, then the mesh alias.
        'imported_object_paths': list(REAL_PATHS[1:] + REAL_PATHS[:1]),
        'before': {
            'world_digest': 'unchanged-world', 'actor_paths': ['old-world-actor'],
            'selection': [],
            'scene': {'actors': [{'path': 'old-codex-' + str(i)} for i in range(152)]},
        },
    }


class NativeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.native = load_native()
        self.tmp = tempfile.TemporaryDirectory(prefix='corn-recovery-offline-')
        self.addCleanup(self.tmp.cleanup)
        self.journal = Path(self.tmp.name) / 'native.json'
        self.cfg = {'original_import': {'sha256': ORIGINAL_SHA},
                    'journal': str(self.journal), 'original_camera': {}}
        self.original = original_fixture()
        self.pin = patch.object(self.native, '_pin', side_effect=lambda row: json.dumps(self.original).encode()).start()
        self.addCleanup(patch.stopall)

    def test_exact_real_outputs_reach_only_mocked_context(self):
        self.assertEqual(self.native.PATHS, REAL_PATHS)
        self.assertNotIn(self.native.SOURCE_MESH, self.native.NAMES)
        with patch.object(self.native, '_context', side_effect=BoundaryReached) as context:
            with self.assertRaises(BoundaryReached):
                self.native.run(self.cfg)
            context.assert_called_once_with(self.cfg)
        self.assertFalse(self.journal.exists())

    def test_missing_extra_duplicate_foreign_and_source_name_outputs_reject(self):
        paths = list(REAL_PATHS)
        variants = [paths[:-1], paths + [ROOT + '/Extra.Extra'],
                    paths[:-1] + [paths[0]],
                    [p.replace('/CornPolishR1/', '/Foreign/') for p in paths],
                    [paths[0].replace('Harvest3_CornPolish_R1', 'Prop_Harvest3_Corn_Polish_R1')] + paths[1:]]
        with patch.object(self.native, '_context', side_effect=AssertionError('engine boundary')) as context:
            for outputs in variants:
                with self.subTest(outputs=outputs):
                    self.original['imported_object_paths'] = outputs
                    with self.assertRaisesRegex(RuntimeError, 'consumed one-import/zero-save'):
                        self.native.run(self.cfg)
            context.assert_not_called()

    def test_incompatible_consumed_journal_rejects_before_context(self):
        changes = [
            {'stage': 'READY'}, {'error': 'different failure'}, {'intents': []},
            {'intents': [{'operation': 'different_import'}]},
            {'intents': [{'operation': 'import_exact_after_glb_once'}] * 2},
            {'saves': [{'path': REAL_PATHS[1], 'returned': True}]},
            {'saves': None}, {'new_actor': 'already-created'},
            {'map_save_return': False}, {'map_save_return': True},
        ]
        with patch.object(self.native, '_context', side_effect=AssertionError('engine boundary')) as context:
            for change in changes:
                with self.subTest(change=change):
                    self.original = {**original_fixture(), **change}
                    with self.assertRaisesRegex(RuntimeError, 'consumed one-import/zero-save'):
                        self.native.run(self.cfg)
            context.assert_not_called()

    def test_wrong_consumed_pin_rejects(self):
        self.cfg['original_import']['sha256'] = '0' * 64
        with patch.object(self.native, '_context') as context:
            with self.assertRaisesRegex(RuntimeError, 'consumed one-import/zero-save'):
                self.native.run(self.cfg)
            context.assert_not_called()

    def context_fixture(self):
        farm = {'_utc': lambda: '2026-10-16T10:45:00Z',
                '_farm_camera': Mock(return_value={}),
                '_farm_camera_same': Mock(return_value=True)}
        inventory = {'_flush': lambda stream, value: json.dump(value, stream),
                     '_write': lambda path, value: path.write_text(json.dumps(value))}
        return ({}, {'farm': farm, 'inventory': inventory}, {}, None, None, None)

    def dirty(self):
        return set(self.native.HELD) | {p.split('.')[0] for p in REAL_PATHS}

    def test_retained_recovery_journal_forbids_replay(self):
        self.journal.write_text('retained original evidence')
        with patch.object(self.native, '_context', return_value=self.context_fixture()), \
                patch.object(self.native, '_guard') as guard:
            with self.assertRaisesRegex(RuntimeError, 'retained recovery journal; no replay'):
                self.native.run(self.cfg)
            guard.assert_not_called()
        self.assertEqual(self.journal.read_text(), 'retained original evidence')

    def test_missing_or_extra_dirty_package_rejects_before_file_or_scene(self):
        expected = self.dirty()
        variants = [set(self.native.HELD), expected - {REAL_PATHS[0].split('.')[0]},
                    expected | {'/Game/Foreign/Dirty'}]
        with patch.object(self.native, '_context', return_value=self.context_fixture()), \
                patch.object(self.native, '_guard') as guard, \
                patch.object(self.native, '_file') as file, patch.object(self.native, '_scene') as scene:
            for dirty in variants:
                with self.subTest(dirty=dirty):
                    guard.return_value = {'dirty_content': list(dirty)}
                    with self.assertRaisesRegex(RuntimeError, 'exact six unsaved'):
                        self.native.run(self.cfg)
            file.assert_not_called()
            scene.assert_not_called()
        self.assertFalse(self.journal.exists())

    def test_any_existing_corn_save_rejects_before_scene(self):
        with patch.object(self.native, '_context', return_value=self.context_fixture()), \
                patch.object(self.native, '_guard', return_value={'dirty_content': list(self.dirty())}), \
                patch.object(self.native, '_file', return_value=SimpleNamespace(exists=lambda: True)), \
                patch.object(self.native, '_scene') as scene:
            with self.assertRaisesRegex(RuntimeError, 'first saves must be unattempted'):
                self.native.run(self.cfg)
            scene.assert_not_called()

    def test_changed_world_records_selection_and_camera_reject_before_journal(self):
        baseline = self.original['before']
        variants = []
        for key, value in [('world_digest', 'changed'), ('actor_paths', []), ('selection', ['foreign'])]:
            row = copy.deepcopy(baseline); row[key] = value; variants.append(row)
        row = copy.deepcopy(baseline); row['scene']['actors'][0]['changed'] = True; variants.append(row)
        row = copy.deepcopy(baseline); row['scene']['actors'].pop(); variants.append(row)
        context = self.context_fixture()
        with patch.object(self.native, '_context', return_value=context), \
                patch.object(self.native, '_guard', return_value={'dirty_content': list(self.dirty())}), \
                patch.object(self.native, '_file', return_value=SimpleNamespace(exists=lambda: False)), \
                patch.object(self.native, '_scene') as scene:
            for before in variants:
                scene.return_value = before
                with self.subTest(before=before), self.assertRaisesRegex(RuntimeError, 'world/152records/selection'):
                    self.native.run(self.cfg)
            scene.return_value = baseline
            context[1]['farm']['_farm_camera_same'].return_value = False
            with self.assertRaisesRegex(RuntimeError, 'original camera differs'):
                self.native.run(self.cfg)
        self.assertFalse(self.journal.exists())

    def test_loaded_inventory_missing_or_extra_rejects_before_geometry(self):
        geometry = Mock(side_effect=AssertionError('geometry boundary'))
        for paths in (REAL_PATHS[:-1], REAL_PATHS + (ROOT + '/Extra.Extra',)):
            scopes = {'inventory': {'_assets': lambda: dict.fromkeys(paths)},
                      'geometry': {'_geometry': geometry}}
            with self.subTest(paths=paths), self.assertRaisesRegex(RuntimeError, 'one mesh/three material allowlist'):
                self.native._inspect({}, {}, scopes)
        geometry.assert_not_called()

    def test_actual_inspector_accepts_exact_slots_and_rejects_class_slot_geometry_or_normals(self):
        objects = {p: SimpleNamespace(get_path_name=lambda p=p: p) for p in REAL_PATHS}
        mesh = objects[REAL_PATHS[0]]
        mesh.get_class = Mock(return_value=SimpleNamespace(get_path_name=lambda: '/Script/Engine.StaticMesh'))
        mesh.get_editor_property = Mock(return_value=[None, None, None])
        mesh.get_material = lambda i: objects[REAL_PATHS[i + 1]]
        geo = {'issues': [], 'simple_collision_count': 0}
        build = SimpleNamespace(recompute_normals=False)
        qualifier = Mock(side_effect=lambda obj, raw, graph: {'qualified': obj.get_path_name()})
        scopes = {'inventory': {'_assets': lambda: objects},
                  'geometry': {'_geometry': lambda obj, raw: geo},
                  'direct': {'qualify': qualifier}, 'graph': {}}
        packet = {'mesh': {}, 'materials': [{}, {}, {}]}
        api = SimpleNamespace(StaticMeshEditorSubsystem='mock-static-mesh-subsystem',
                              get_editor_subsystem=lambda cls: SimpleNamespace(get_lod_build_settings=lambda obj, lod: build))
        with patch.object(self.native, 'unreal', api):
            result, returned = self.native._inspect({}, packet, scopes)
            self.assertIs(returned, objects)
            self.assertEqual(result['slots'], list(REAL_PATHS[1:]))
            self.assertEqual(qualifier.call_count, 3)
            mesh.get_class.return_value = SimpleNamespace(get_path_name=lambda: '/Script/Engine.Material')
            with self.assertRaisesRegex(RuntimeError, 'StaticMesh class'):
                self.native._inspect({}, packet, scopes)
            mesh.get_class.return_value = SimpleNamespace(get_path_name=lambda: '/Script/Engine.StaticMesh')
            mesh.get_material = lambda i: objects[REAL_PATHS[3 - i]]
            with self.assertRaisesRegex(RuntimeError, 'slot order'):
                self.native._inspect({}, packet, scopes)
            mesh.get_material = lambda i: objects[REAL_PATHS[i + 1]]
            for issue, collision, normals in [(['bad bounds'], 0, False), ([], 1, False), ([], 0, True)]:
                geo.update(issues=issue, simple_collision_count=collision); build.recompute_normals = normals
                with self.subTest(issue=issue, collision=collision, normals=normals), \
                        self.assertRaisesRegex(RuntimeError, 'geometry/options/source-normal'):
                    self.native._inspect({}, packet, scopes)

    def test_mocked_existing_objects_first_save_once_and_assets_only_stop(self):
        objects = {p: SimpleNamespace(get_name=lambda p=p: p.rsplit('.', 1)[1]) for p in REAL_PATHS}
        persisted = set()
        saved = []
        def save(obj, only_if_is_dirty):
            self.assertIs(only_if_is_dirty, False)
            path = next(p for p, value in objects.items() if value is obj)
            self.assertNotIn(path, persisted)
            saved.append(path); persisted.add(path)
            return True
        editor = SimpleNamespace(set_metadata_tag=Mock(), save_loaded_asset=Mock(side_effect=save))
        api = SimpleNamespace(EditorAssetLibrary=editor)
        objects[REAL_PATHS[0]].get_bounding_box = lambda: SimpleNamespace(min=[0, 0, 0], max=[1, 1, 1])
        context = self.context_fixture(); context[2]['_xyz'] = list
        with patch.object(self.native, 'unreal', api), \
                patch.object(self.native, '_context', return_value=context), \
                patch.object(self.native, '_guard', return_value={'dirty_content': list(self.dirty())}), \
                patch.object(self.native, '_file', side_effect=lambda p: SimpleNamespace(exists=lambda: p in persisted)), \
                patch.object(self.native, '_scene', return_value=self.original['before']), \
                patch.object(self.native, '_inspect', return_value=({}, objects)), \
                patch.object(self.native, '_old', return_value={'preserved': True}), \
                patch.object(self.native, '_patch', return_value=(None, {'reason': 'no proved patch'})):
            result = self.native.run(self.cfg)
            self.assertEqual(result['stage'], 'CORN_FOUR_ASSETS_SAVED_PLACEMENT_BLOCKED', result)
            self.assertEqual(saved, list(REAL_PATHS[1:] + REAL_PATHS[:1]))
            self.assertEqual(result['new_imports'], 0)
            self.assertIsNone(result['new_actor'])
            self.assertIsNone(result['map_save_return'])
            self.assertFalse(result['replay_permitted'])
            self.assertEqual(json.loads(self.journal.read_text())['saves'], result['saves'])
            with self.assertRaisesRegex(RuntimeError, 'retained recovery journal'):
                self.native.run(self.cfg)
            self.assertEqual(editor.save_loaded_asset.call_count, 4)

    def test_source_has_no_import_rename_delete_saveall_or_overwrite_route(self):
        tree = ast.parse(NATIVE.read_text())
        calls = [n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
                 for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))]
        forbidden = {'AssetImportTask', 'import_asset_tasks', 'import_assets', 'reimport',
                     'rename_asset', 'rename_loaded_asset', 'rename', 'replace', 'delete_asset',
                     'delete_loaded_asset', 'delete_actor', 'destroy_actor', 'unlink',
                     'save_all', 'save_all_dirty_packages', 'save_dirty_packages'}
        self.assertFalse(set(calls) & forbidden)
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        opens = [n for n in ast.walk(run) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'open']
        self.assertEqual(len(opens), 1)
        self.assertEqual(opens[0].args[0].value, 'x')
        self.assertEqual(calls.count('spawn_actor_from_class'), 1)
        self.assertEqual(calls.count('save_map'), 1)


class HostGrantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='corn-grant-offline-')
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        self.args = SimpleNamespace(folder=folder, review=folder/'review.json', prerequisite=folder/'grant.json')
        self.args.review.write_text(json.dumps({'clear': True, 'prepared_sha256': 'tested-prepared'}))
        self.d = SimpleNamespace(
            fingerprint=Mock(return_value={'sha256': 'tested-prepared'}),
            load=Mock(return_value={}), protect=Mock(side_effect=BoundaryReached),
            _lease=Mock(side_effect=AssertionError('lease forbidden')),
            locks=Mock(side_effect=AssertionError('network forbidden')),
            post=Mock(side_effect=AssertionError('mutation forbidden')))
        self.receiving = SimpleNamespace(resources=Mock(side_effect=AssertionError('resource query forbidden')))
        self.process = SimpleNamespace(check_output=Mock(side_effect=AssertionError('process forbidden')))
        self.dispatch = Mock(side_effect=AssertionError('dispatch forbidden'))
        namespace = dict(prepared=Mock(return_value={'cfg': {'baseline': {'path': 'fixture-only'}}}),
                         d=self.d, receiving=self.receiving, subprocess=self.process, dispatch=self.dispatch,
                         time=SimpleNamespace(time=lambda: NOW), json=json, datetime=datetime, timezone=timezone,
                         START_BY=datetime(2026,10,16,11,30,tzinfo=timezone.utc).timestamp(),
                         RUNTIME_ASSIGNMENT='skyfarm-corn-alias-recovery-r1')
        tree = ast.parse(HOST.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(HOST), 'exec'), namespace)
        self.run_host = namespace['run']

    def grant(self, deadline='2026-10-16T11:00:00Z'):
        return {'id': 33120, 'from': 'pootscoot-coordination', 'to': 'codex-play-guard', 'type': 'grant',
                'body': {'assignment_id': 'skyfarm-corn-alias-recovery-r1', 'start_by_utc': deadline}}

    def write_grants(self, rows):
        self.args.prerequisite.write_text(json.dumps({'messages': rows}))

    def assert_no_production(self):
        self.d.protect.assert_not_called()
        self.d._lease.assert_not_called(); self.d.locks.assert_not_called(); self.d.post.assert_not_called()
        self.receiving.resources.assert_not_called(); self.process.check_output.assert_not_called()
        self.dispatch.assert_not_called()

    def test_explicit_utc_z_and_zero_offset_reach_mocked_preservation_only(self):
        for deadline in ('2026-10-16T11:00:00Z', '2026-10-16T11:00:00+00:00'):
            with self.subTest(deadline=deadline):
                self.write_grants([self.grant(deadline)])
                with self.assertRaises(BoundaryReached):
                    self.run_host(self.args)
        self.assertEqual(self.d.protect.call_count, 2)
        self.d._lease.assert_not_called(); self.process.check_output.assert_not_called()
        self.dispatch.assert_not_called()

    def test_naive_nonzero_malformed_and_expired_deadlines_reject_before_claim(self):
        for deadline in ('2026-10-16T11:00:00', '2026-10-16T11:00:00+01:00',
                         '2026-10-16T11:00:00-07:00', 'not-a-date', '',
                         '2026-10-16T10:44:59Z', '2026-10-16T10:44:59+00:00'):
            with self.subTest(deadline=deadline):
                self.write_grants([self.grant(deadline)])
                with self.assertRaises((ValueError, RuntimeError)):
                    self.run_host(self.args)
                self.assert_no_production()

    def test_source_clear_old_grants_foreign_and_duplicates_are_not_runtime_authority(self):
        grant = self.grant()
        rows = [[], [{**grant, 'type': 'source.continuation', 'id': 33103}],
                [{**grant, 'id': 33079}], [{**grant, 'id': 33091}],
                [{**grant, 'from': 'another-owner'}], [{**grant, 'to': 'another-operator'}],
                [{**grant, 'body': {**grant['body'], 'assignment_id': 'old-corn-intake'}}],
                [grant, copy.deepcopy(grant)]]
        for messages in rows:
            with self.subTest(messages=messages):
                self.write_grants(messages)
                with self.assertRaisesRegex(ValueError, 'distinct addressed'):
                    self.run_host(self.args)
                self.assert_no_production()

    def test_uncleared_or_wrong_prepared_gate_rejects_before_claim(self):
        self.write_grants([self.grant()])
        for clear in ({'clear': False, 'prepared_sha256': 'tested-prepared'},
                      {'clear': True, 'prepared_sha256': 'wrong-packet'}):
            self.args.review.write_text(json.dumps(clear))
            with self.subTest(clear=clear), self.assertRaisesRegex(RuntimeError, 'source gate missing'):
                self.run_host(self.args)
            self.assert_no_production()

    def test_retained_claim_rejects_even_with_new_grant(self):
        self.write_grants([self.grant()]); (self.args.folder/'claim.json').write_text('retained')
        with self.assertRaisesRegex(RuntimeError, 'retained claim'):
            self.run_host(self.args)
        self.assert_no_production()

    def test_original_start_by_cap_rejects_before_review_or_claim(self):
        self.run_host.__globals__['time'] = SimpleNamespace(time=lambda: NOW + 3600)
        with self.assertRaisesRegex(RuntimeError, '33079 start-by passed'):
            self.run_host(self.args)
        self.d.fingerprint.assert_not_called(); self.assert_no_production()


class NormalRepairCandidateTests(unittest.TestCase):
    """Only new33219 tests; engine/network/process/save boundaries absent."""
    def setUp(self):
        self.native=load_native()
        self.values={name:0 for name in self.native.BUILD_FIELDS}
        self.values.update(bRecomputeNormals=True,bRecomputeTangents=True,bSupportFaceRemap=True,
                           BuildScale3D=[1.,1.,1.],BuildScale_DEPRECATED=1.,DistanceFieldBias_DEPRECATED=.125,
                           DistanceFieldReplacementMesh=None,MaxLumenMeshCards=12,
                           future_exposed_field={'nested':[3,7,11]})

    def fixture(self):
        class Settings:
            def __init__(self,values):self.values=copy.deepcopy(values)
            def copy(self):return Settings(self.values)
            def to_dict(self):return copy.deepcopy(self.values)
            def get_editor_property(self,key):return self.values[key]
            def set_editor_property(self,key,value):
                if key!='recompute_normals':raise AssertionError('Only one field allowed')
                self.values['bRecomputeNormals']=value
        mesh=SimpleNamespace(get_path_name=lambda:REAL_PATHS[0],
            get_class=lambda:SimpleNamespace(get_path_name=lambda:'/Script/Engine.StaticMesh'),
            get_num_triangles=Mock(return_value=2592))
        subsystem=SimpleNamespace(current=Settings(self.values),calls=[])
        subsystem.get_lod_build_settings=lambda obj,lod:subsystem.current.copy()
        def setter(obj,lod,settings):
            subsystem.calls.append((obj.get_path_name(),lod,copy.deepcopy(settings.values)))
            subsystem.current=settings.copy()
        subsystem.set_lod_build_settings=Mock(side_effect=setter)
        report={'stage':'TEST_ONLY'};keep=Mock();guard=Mock();pre=Mock(return_value={'clear':True})
        post=Mock(return_value=dict(stored_authored_clear=True,raw_authored_clear=True,original_pbr_clear=True,preservation_clear=True))
        return mesh,subsystem,report,keep,guard,pre,post

    def test_exact_target_one_setter_changes_only_normal_flag_and_never_saves(self):
        args=self.fixture();mesh,sub,r,keep,guard,pre,post=args
        result=self.native._repair_transaction(*args)
        self.assertEqual(result['stage'],'CORN_NORMAL_REPAIR_QUALIFIED_UNSAVED')
        self.assertEqual(len(sub.calls),1);path,lod,values=sub.calls[0]
        self.assertEqual((path,lod),(REAL_PATHS[0],0))
        changed={k for k in self.values if values[k]!=self.values[k]}
        self.assertEqual(changed,{'bRecomputeNormals'})
        self.assertIs(values['bRecomputeNormals'],False)
        self.assertEqual(self.values['future_exposed_field'],values['future_exposed_field'])
        self.assertEqual(result['saves'],0);self.assertEqual(result['imports'],0)
        self.assertEqual(result['new_actors'],0);self.assertEqual(result['map_saves'],0)
        pre.assert_called_once();post.assert_called_once();self.assertTrue(result['known_terminal'])

    def test_foreign_target_or_wrong_class_cannot_reach_proofs_or_setter(self):
        for foreign in ('path','class'):
            args=list(self.fixture())
            if foreign=='path':args[0].get_path_name=lambda:'/Game/Foreign/F.F'
            else:args[0].get_class=lambda:SimpleNamespace(get_path_name=lambda:'/Script/Engine.Material')
            with self.subTest(foreign=foreign),self.assertRaisesRegex(RuntimeError,'exact retained Corn'):
                self.native._repair_transaction(*args)
            args[1].set_lod_build_settings.assert_not_called();args[5].assert_not_called()

    def test_failed_preproof_or_guard_stops_before_setter(self):
        for kind in ('preproof','guard'):
            args=list(self.fixture())
            if kind=='preproof':args[5].return_value={'clear':False}
            else:args[4].side_effect=RuntimeError('guard failed')
            result=self.native._repair_transaction(*args)
            self.assertEqual(result['stage'],'CORN_NORMAL_REPAIR_PARTIAL_HOLD')
            self.assertTrue(result['known_terminal']);args[1].set_lod_build_settings.assert_not_called();args[6].assert_not_called()

    def test_already_changed_flag_is_not_an_implicit_retry(self):
        args=self.fixture();args[1].current.values['bRecomputeNormals']=False
        result=self.native._repair_transaction(*args)
        self.assertIn('flagtrue',result['error']);args[1].set_lod_build_settings.assert_not_called()

    def test_all_other_fields_including_deprecated_and_new_exposed_are_preserved(self):
        args=self.fixture();result=self.native._repair_transaction(*args)
        self.assertEqual(result['build_after'],result['build_expected'])
        self.assertEqual(result['build_before']['native']['bSupportFaceRemap'],True)
        self.assertEqual(result['build_after']['native']['DistanceFieldBias_DEPRECATED'],.125)
        self.assertEqual(result['build_before']['exposed']['future_exposed_field'],result['build_after']['exposed']['future_exposed_field'])

    def test_unrelated_after_setting_change_holds_before_postproof(self):
        args=self.fixture();sub=args[1];original=sub.set_lod_build_settings.side_effect
        def bad_setter(*values):
            original(*values);sub.current.values['bSupportFaceRemap']=False
        sub.set_lod_build_settings.side_effect=bad_setter
        result=self.native._repair_transaction(*args)
        self.assertIn('another build setting',result['error']);args[6].assert_not_called();self.assertEqual(result['saves'],0)

    def test_each_failed_stored_raw_pbr_or_preservation_proof_stops_unsaved(self):
        for field in ('stored_authored_clear','raw_authored_clear','original_pbr_clear','preservation_clear'):
            args=self.fixture();args[6].return_value[field]=False
            with self.subTest(field=field):
                result=self.native._repair_transaction(*args)
                self.assertEqual(result['stage'],'CORN_NORMAL_REPAIR_PARTIAL_HOLD')
                self.assertEqual(result['setter_intents'],1);self.assertEqual(result['saves'],0)

    def test_postproof_exception_is_retained_without_setter_retry(self):
        args=self.fixture();args[6].side_effect=RuntimeError('PBR graph mismatch')
        result=self.native._repair_transaction(*args)
        self.assertTrue(result['known_terminal']);self.assertEqual(len(args[1].calls),1)
        with self.assertRaisesRegex(RuntimeError,'no replay'):self.native._repair_transaction(*args)
        self.assertEqual(len(args[1].calls),1)

    def test_setter_or_rebuild_barrier_exception_retains_unknown_completion(self):
        for field in ('setter','barrier'):
            args=self.fixture()
            if field=='setter':args[1].set_lod_build_settings.side_effect=RuntimeError('setter outcome uncertain')
            else:args[0].get_num_triangles.side_effect=RuntimeError('render completion unavailable')
            with self.subTest(field=field):
                result=self.native._repair_transaction(*args)
                self.assertFalse(result['known_terminal']);self.assertEqual(result['setter_intents'],1)
                self.assertEqual(result['saves'],0);args[6].assert_not_called()

    def test_changed_post_rebuild_count_stops_before_normal_or_pbr_proof(self):
        args=self.fixture();args[0].get_num_triangles.return_value=2556
        result=self.native._repair_transaction(*args)
        self.assertIn('multiplicity',result['error']);args[6].assert_not_called();self.assertEqual(result['saves'],0)

    def test_public_source_only_candidate_rejects_before_engine_context(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(self.native,'_context') as context:
            with self.assertRaisesRegex(RuntimeError,'SOURCE ONLY33219'):
                self.native.repair_normals({'normal_repair_journal':str(Path(folder)/'new.json'),'source_only':True,'repair_runtime_grant':None})
            context.assert_not_called()

    def test_retained_public_journal_rejects_before_authority_or_context(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(self.native,'_context') as context:
            path=Path(folder)/'retained.json';path.write_text('retained')
            with self.assertRaisesRegex(RuntimeError,'no replay'):
                self.native.repair_normals({'normal_repair_journal':str(path)})
            self.assertEqual(path.read_text(),'retained');context.assert_not_called()

    def test_source_assignment_cannot_substitute_for_runtime_grant(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(self.native,'_context') as context, \
                patch.object(self.native,'_pin',return_value=json.dumps({'messages':[{'id':33219,'from':'pootscoot-coordination','to':'codex-play-guard','type':'source.assignment','body':{'assignment_id':'skyfarm-corn-authored-normal-repair-r1'}}]}).encode()):
            with self.assertRaisesRegex(RuntimeError,'distinct explicit'):
                self.native.repair_normals({'normal_repair_journal':str(Path(folder)/'new.json'),'source_only':False,'repair_runtime_grant':{'path':'mocked-grant'}})
            context.assert_not_called()

    def test_repair_functions_have_no_save_import_actor_camera_or_cleanup_route(self):
        tree=ast.parse(NATIVE.read_text());names={'_repair_transaction','repair_normals','_repair_stored','_repair_raw_proof','_repair_stored_proof'}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        calls=[n.func.attr for node in nodes for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertEqual(calls.count('set_lod_build_settings'),1)
        self.assertFalse(set(calls)&{'save_loaded_asset','save_map','save_all','import_asset_tasks','spawn_actor_from_class','set_level_viewport_camera_info','rename_asset','delete_asset','destroy_actor'})
        host=HOST.read_text();self.assertIn("'prepare-normal-repair'",host)
        self.assertNotIn("choices=['prepare','run','repair'",host)

    def test_stored_component_guard_accepts_float32_noise_and_rejects_wider_drift(self):
        # Full coverage belongs to the pinned comparator. This fixture isolates
        # the NEW component check after a comparator reports complete mapping.
        source=[{'positions':[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]],'normals':[[0.,0.,1.]]*3}]
        normal={'compare':Mock(return_value={'status':'MATCH_WITHIN_EXPLICIT_TOLERANCES','matched_corners':7776,'triangle_mapping':[[0,0]]}),
                'unit':lambda v:[x/self.native.math.sqrt(sum(a*a for a in v)) for x in v]}
        for drift,accepted in ((3e-8,True),(1e-6,False)):
            stored={'triangles':[{'triangle_id':0,'positions':source[0]['positions'],'normals':[[drift,0.,1.]]*3}]}
            with self.subTest(drift=drift):
                if accepted:
                    result=self.native._repair_stored_proof(source,stored,normal)
                    self.assertLessEqual(result['maximum_normalized_component_error'],2**-22)
                else:
                    with self.assertRaisesRegex(RuntimeError,'float32 component'):
                        self.native._repair_stored_proof(source,stored,normal)

    def test_incomplete_stored_coverage_cannot_reach_component_acceptance(self):
        normal={'compare':Mock(return_value={'status':'UNPROVEN','matched_corners':7773})}
        with self.assertRaisesRegex(RuntimeError,'full stored'):
            self.native._repair_stored_proof([],{},normal)

    def test_exact_six_dirty_packages_rechecked_before_the_setter(self):
        expected=set(self.native.HELD)|{p.split('.')[0] for p in self.native.PATHS}
        with patch.object(self.native,'_guard',return_value={'dirty_content':list(expected)}) as guard, \
                patch.object(self.native,'_file',return_value=SimpleNamespace(exists=lambda:False)):
            self.assertEqual(set(self.native._repair_guard({}, {})['dirty_content']),expected)
            guard.return_value={'dirty_content':list(self.native.HELD)}
            with self.assertRaisesRegex(RuntimeError,'exact six'):self.native._repair_guard({}, {})

    def test_any_new_saved_corn_file_blocks_the_repair(self):
        expected=set(self.native.HELD)|{p.split('.')[0] for p in self.native.PATHS}
        with patch.object(self.native,'_guard',return_value={'dirty_content':list(expected)}), \
                patch.object(self.native,'_file',return_value=SimpleNamespace(exists=lambda:True)):
            with self.assertRaisesRegex(RuntimeError,'never-saved'):self.native._repair_guard({}, {})


class RepairCallerTests(unittest.TestCase):
    """NEW33230 caller checks: only temporary files and mocked external IO."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='corn-caller-offline-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.now=datetime(2026,10,16,13,0,tzinfo=timezone.utc).timestamp()
        def pin(path):
            import hashlib
            raw=Path(path).read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        self.d=SimpleNamespace(pin=pin,load=lambda p:json.loads(Path(p).read_text()),_check=Mock())
        import hashlib
        ns={'__file__':str(HOST),'TASK':self.root,'REPO':REPO,'NATIVE':self.root/'native.py',
            'PATHS':REAL_PATHS,'HELD':(), 'MARKER':'# mocked existing route', 'Path':Path,'json':json,'ast':ast,'re':re,
            'datetime':datetime,'timezone':timezone,'time':SimpleNamespace(time=lambda:self.now),
            'hashlib':hashlib,'SimpleNamespace':SimpleNamespace,'d':self.d}
        tree=ast.parse(HOST.read_text());nodes=[]
        for n in tree.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('REPAIR_') for t in n.targets):nodes.append(n)
            if isinstance(n,ast.FunctionDef) and (n.name.startswith('_repair_') or n.name in ('prepare_repair_caller','repair_caller_dry_run','run_normal_repair')):nodes.append(n)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HOST),'exec'),ns);self.ns=ns
        self.factory=Mock(side_effect=AssertionError('No real IO factory in offline tests'));ns['_repair_runtime_tools']=self.factory
        folder=ns['REPAIR_SOURCE'];folder.mkdir(parents=True);fixture=self.root/'fixture.json';fixture.write_text('{}')
        row=pin(fixture);guard=self.root/'guard.py';guard.write_text("def native():\n    code=MARKER+'\\n'+body\n")
        cfg={k:row for k in ('source','manifest','packet','baseline','snap','world_helper','original_import')};cfg.update(helpers={},repair_support={},source_only=True,repair_runtime_grant=None)
        self.prepared={'version':ns['REPAIR_VERSION'],'operation':ns['REPAIR_OPERATION'],'target':REAL_PATHS[0],'native_function':'repair_normals',
            'native_source':{**row,'path':str(ns['NATIVE']),'sha256':ns['REPAIR_NATIVE_SHA']},'host_source':{**row,'path':str(HOST),'sha256':'caller-source-pin'},
            'test_source':row,'source_candidate':{**row,'sha256':ns['REPAIR_SOURCE_SHA']},'world_guard':pin(guard),'source_scope':row,'reviewed_source_publication':row,'cfg':cfg}
        (folder/'prepared.json').write_text(json.dumps(self.prepared))
        self.args=SimpleNamespace(folder=folder,prerequisite=self.root/'grant.json',review=self.root/'review.json',
            repair_attempt='corn-normal-repair-20261016T130000Z-1234abcd',execute_approved_repair=True)
        self.args.review.write_text(json.dumps({'clear':True,'prepared_sha256':pin(folder/'prepared.json')['sha256']}))
        self.body={'assignment_id':'skyfarm-corn-authored-normal-repair-r1','caller_version':ns['REPAIR_VERSION'],'operation':ns['REPAIR_OPERATION'],
            'target':REAL_PATHS[0],'native_function':'repair_normals','prepared_sha256':pin(folder/'prepared.json')['sha256'],
            'native_source_sha256':ns['REPAIR_NATIVE_SHA'],'host_source_sha256':'caller-source-pin','source_review_sha256':pin(self.args.review)['sha256'],
            'attempt_id':self.args.repair_attempt,'attempt_directory':str(ns['REPAIR_ATTEMPTS']/self.args.repair_attempt),
            'maximum_native_callbacks':1,'maximum_targeted_normal_rebuilds':1,'maximum_imports':0,'maximum_saves':0,'maximum_new_actors':0,'maximum_map_saves':0,'maximum_camera_actions':0,'maximum_captures':0,
            'direct_user_authorization_received':True,'direct_user_authorization_reference':'UNIT TEST ONLY; no production authority',
            'resource_prerequisite_confirmed':True,'resource_prerequisite_reference':'UNIT TEST ONLY prior terminal/release fixture',
            'start_by_utc':'2026-10-16T13:05:00Z','stop_by_utc':'2026-10-16T13:15:00Z'}
        self.grant={'id':33300,'from':'pootscoot-coordination','to':'codex-play-guard','type':'grant','body':self.body};self.write_grant()
        self.result={'known_terminal':True,'stage':'CORN_NORMAL_REPAIR_QUALIFIED_UNSAVED','target':REAL_PATHS[0],'lod':0,
            'imports':0,'saves':0,'new_actors':0,'map_saves':0,'camera_actions':0,'setter_intents':1,'setter_returns':1,'rebuild_barrier_returned':True,
            'build_after':{'native':{'bRecomputeNormals':False}},'build_expected':{'native':{'bRecomputeNormals':False}},
            'after_proof':dict(stored_authored_clear=True,raw_authored_clear=True,original_pbr_clear=True,preservation_clear=True)}
        self.active=None;self.fail_files=set()
        def write(path,value):
            if path.name in self.fail_files:raise OSError('mock receipt failure: '+path.name)
            with path.open('x',encoding='utf-8') as stream:json.dump(value,stream)
        self.lease={'holder':'codex-play-guard','at':self.now-100,'ttl':3600}
        def claim():
            self.active={'holder':'codex-play-guard','at':self.now,'ttl':600}
            return {'ok':True,'lock':copy.deepcopy(self.active)}
        def release():self.active=None;return {'ok':True,'lock':None}
        self.io=SimpleNamespace(write=Mock(side_effect=write),code_write=Mock(side_effect=lambda p,c:p.write_text(c)),now=lambda:self.now,
            locks=Mock(side_effect=lambda:{'unreal':self.lease,**({'compute':self.active} if self.active else {})}),lease=Mock(return_value=self.lease),
            protect=Mock(),resources=Mock(return_value={'available_physical':2_000_000*1024,'available_commit':3_000_000*1024}),
            process=Mock(return_value={'Id':42564,'Path':ns['REPAIR_EDITOR'],'start_utc':ns['REPAIR_EDITOR_START']}),claim=Mock(side_effect=claim),
            same=lambda left,right:bool(left) and all(left.get(k)==right.get(k) for k in ('holder','at','ttl')),
            release=Mock(side_effect=release),call=Mock(side_effect=lambda code:{'result':self.result}),unwrap=lambda reply:reply['result'])

    def write_grant(self):self.args.prerequisite.write_text(json.dumps({'messages':[self.grant]}))
    def run_caller(self):return self.ns['run_normal_repair'](self.args,_io=self.io)
    def attempt(self):return self.ns['REPAIR_ATTEMPTS']/self.args.repair_attempt

    def test_default_dry_run_has_zero_external_calls_even_with_grant_options(self):
        self.args.execute_approved_repair=False;result=self.run_caller()
        self.assertEqual(result['stage'],'REPAIR_CALLER_DRY_RUN');self.factory.assert_not_called()
        self.io.locks.assert_not_called();self.io.process.assert_not_called();self.io.call.assert_not_called();self.io.claim.assert_not_called()

    def test_source_old_foreign_and_publication_messages_cannot_grant_runtime(self):
        for change in ({'id':33079},{'id':33122},{'id':33230,'type':'source.assignment'},{'id':33232,'type':'source.clear'},{'from':'another-bot'},{'to':'another-owner'}):
            original=copy.deepcopy(self.grant);self.grant.update(change);self.write_grant()
            with self.subTest(change=change):
                self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED');self.io.locks.assert_not_called();self.io.call.assert_not_called()
            self.grant=original;self.body=self.grant['body']

    def test_target_source_prepared_review_attempt_and_extra_effect_mismatches_reject_locally(self):
        for key,value in [('target','/Game/Foreign/F.F'),('native_function','run'),('native_source_sha256','wrong'),('host_source_sha256','wrong'),('prepared_sha256','wrong'),('source_review_sha256','wrong'),('attempt_directory','C:/Foreign'),('maximum_saves',1),('maximum_captures',1)]:
            old=self.body[key];self.body[key]=value;self.write_grant()
            with self.subTest(key=key):self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED')
            self.body[key]=old
        self.io.locks.assert_not_called();self.io.call.assert_not_called();self.factory.assert_not_called()

    def test_direct_human_authorization_must_be_received_not_inferred(self):
        self.body['direct_user_authorization_received']=False;self.write_grant()
        result=self.run_caller();self.assertIn('authorization still pending',result['error']);self.io.locks.assert_not_called()

    def test_naive_non_utc_expired_or_insufficient_windows_reject_before_io(self):
        for key,value in [('start_by_utc','2026-10-16T13:05:00'),('start_by_utc','2026-10-16T13:05:00-07:00'),('start_by_utc','2026-10-16T12:59:00Z'),('stop_by_utc','2026-10-16T13:04:00Z')]:
            old=self.body[key];self.body[key]=value;self.write_grant()
            with self.subTest(value=value):self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED')
            self.body[key]=old
        self.io.locks.assert_not_called()

    def test_retained_attempt_and_unreconciled_prior_outcome_cannot_replay(self):
        self.attempt().mkdir(parents=True)
        self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED');self.io.call.assert_not_called()
        self.args.repair_attempt='corn-normal-repair-20261016T130001Z-1234abcd';self.body.update(attempt_id=self.args.repair_attempt,attempt_directory=str(self.attempt()));self.write_grant()
        old=next(self.ns['REPAIR_ATTEMPTS'].iterdir());(old/'uncertain.json').write_text('{}')
        self.assertIn('unreconciled',self.run_caller()['error']);self.io.locks.assert_not_called()

    def test_changed_source_pin_rejects_before_external_io(self):
        self.d._check.side_effect=RuntimeError('pinned source changed')
        self.assertIn('pinned source changed',self.run_caller()['error']);self.io.call.assert_not_called();self.io.claim.assert_not_called()

    def test_one_repair_callback_and_strict_terminal_normal_release(self):
        result=self.run_caller();self.assertEqual(result['stage'],'TARGET_REBUILD_QUALIFIED_UNSAVED')
        self.io.call.assert_called_once();self.io.release.assert_called_once();self.assertIsNone(self.active)
        code=self.io.call.call_args.args[0];self.assertIn('scope["repair_normals"]',code);self.assertNotIn('scope["run"]',code)
        self.assertTrue(json.loads((self.attempt()/'release.json').read_text())['old_lease_absent'])
        self.assertFalse(result['release']is None);self.assertNotIn('save_map',code)

    def test_wrong_os_context_or_foreign_compute_rejects_before_claim(self):
        self.io.process.return_value={'Id':999,'Path':'foreign','start_utc':'wrong'}
        self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED');self.io.claim.assert_not_called();self.io.call.assert_not_called()

    def test_foreign_compute_is_preserved_without_unlock(self):
        self.active={'holder':'other-owner','at':self.now,'ttl':600}
        self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED');self.io.claim.assert_not_called();self.io.release.assert_not_called();self.io.call.assert_not_called()

    def test_low_memory_before_claim_has_no_dispatch_or_reservation(self):
        self.io.resources.return_value={'available_physical':1,'available_commit':1}
        self.assertEqual(self.run_caller()['stage'],'NO_DISPATCH_REJECTED');self.io.claim.assert_not_called();self.io.call.assert_not_called()

    def test_post_claim_guard_failure_closes_known_no_dispatch_normally(self):
        high={'available_physical':2_000_000*1024,'available_commit':3_000_000*1024}
        self.io.resources.side_effect=[high,{'available_physical':1,'available_commit':1}]
        result=self.run_caller();self.assertEqual(result['stage'],'NO_DISPATCH_REJECTED');self.io.call.assert_not_called();self.io.release.assert_called_once();self.assertIsNone(self.active)

    def test_dispatch_intent_receipt_failure_prevents_rpc_and_closes_reservation(self):
        self.fail_files={'dispatch-intent.json'};result=self.run_caller()
        self.assertEqual(result['stage'],'NO_DISPATCH_REJECTED');self.io.call.assert_not_called();self.io.release.assert_called_once()

    def test_timeout_after_dispatch_holds_exact_lease_without_retry(self):
        self.io.call.side_effect=TimeoutError('mock uncertain RPC');result=self.run_caller()
        self.assertEqual(result['stage'],'UNCERTAIN_DISPATCH_OR_CLOSURE');self.io.call.assert_called_once();self.io.release.assert_not_called();self.assertIsNotNone(self.active)
        uncertain=json.loads((self.attempt()/'uncertain.json').read_text());self.assertFalse(uncertain['replay_permitted']);self.assertFalse(uncertain['forced_unlock_permitted'])

    def test_reply_receipt_failure_retains_raw_evidence_and_lease(self):
        self.fail_files={'reply.json'};result=self.run_caller()
        self.assertEqual(result['stage'],'UNCERTAIN_DISPATCH_OR_CLOSURE');self.io.call.assert_called_once();self.io.release.assert_not_called()
        self.assertEqual(json.loads((self.attempt()/'uncertain.json').read_text())['raw_reply_observation']['result']['target'],REAL_PATHS[0])

    def test_native_uncertain_or_incomplete_transport_success_is_not_qualification(self):
        self.result['known_terminal']=False;result=self.run_caller()
        self.assertEqual(result['stage'],'UNCERTAIN_DISPATCH_OR_CLOSURE');self.io.release.assert_not_called()

    def test_missing_native_build_proof_is_held_despite_transport_success(self):
        self.result.pop('build_after');self.result.pop('build_expected')
        self.assertEqual(self.run_caller()['stage'],'UNCERTAIN_DISPATCH_OR_CLOSURE');self.io.release.assert_not_called()

    def test_known_native_preproof_hold_releases_without_claiming_rebuild(self):
        self.result.update(stage='CORN_NORMAL_REPAIR_PARTIAL_HOLD',setter_intents=0,setter_returns=0,rebuild_barrier_returned=False)
        result=self.run_caller();self.assertEqual(result['stage'],'KNOWN_HOLD_NO_REBUILD');self.io.release.assert_called_once()

    def test_known_completed_rebuild_qualification_hold_is_unsaved_and_released(self):
        self.result['stage']='CORN_NORMAL_REPAIR_PARTIAL_HOLD'
        result=self.run_caller();self.assertEqual(result['stage'],'TARGET_REBUILD_COMPLETED_QUALIFICATION_HOLD');self.io.release.assert_called_once();self.assertEqual(self.result['saves'],0)

    def test_release_receipt_failure_preserves_confirmed_observation_without_second_unlock(self):
        self.fail_files={'release.json'};result=self.run_caller()
        self.assertEqual(result['stage'],'UNCERTAIN_DISPATCH_OR_CLOSURE');self.io.release.assert_called_once();self.assertIsNone(self.active)
        self.assertTrue(json.loads((self.attempt()/'uncertain.json').read_text())['release_observation']['old_lease_absent'])

    def test_reviewed_native_bytes_remain_unchanged(self):
        import hashlib
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),self.ns['REPAIR_NATIVE_SHA'])

    def test_absent_compute_is_not_a_substitute_for_actual_resource_closure(self):
        self.body['resource_prerequisite_confirmed']=False;self.write_grant()
        self.assertIn('absent compute alone',self.run_caller()['error']);self.io.locks.assert_not_called();self.io.claim.assert_not_called()

    def test_complete_default_module_calls_no_network_or_process_boundary(self):
        import contextlib
        import io
        import runpy
        import socket
        import subprocess
        import urllib.request
        output=io.StringIO()
        with patch.object(sys,'argv',[str(HOST)]),patch.object(sys,'path',[str(HOST.parent),*sys.path]), \
                patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')) as connect, \
                patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')) as sock, \
                patch.object(urllib.request,'urlopen',side_effect=AssertionError('HTTP forbidden')) as http, \
                patch.object(subprocess,'Popen',side_effect=AssertionError('process forbidden')) as process, \
                contextlib.redirect_stdout(output):
            runpy.run_path(str(HOST),run_name='__main__')
        self.assertEqual(json.loads(output.getvalue())['stage'],'REPAIR_CALLER_DRY_RUN')
        connect.assert_not_called();sock.assert_not_called();http.assert_not_called();process.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
