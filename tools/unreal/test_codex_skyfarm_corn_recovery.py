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


if __name__ == '__main__':
    unittest.main(verbosity=2)
