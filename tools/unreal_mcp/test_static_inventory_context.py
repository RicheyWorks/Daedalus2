# SPDX-License-Identifier: MIT
"""Focused refusal diagnostics with fake native state; no editor/client imports.

The retained production failure has no failing operands. Synthetic differences
below test evidence retention, and do not claim to reproduce its unknown cause.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_static_registry_pages import functions


class InventoryContextTests(unittest.TestCase):
    def setUp(self):
        self.context = {'world': '/Game/Synthetic.Synthetic', 'camera': [1.0, 2.0, 3.0, 0.0, 0.0, 0.0],
            'actors': [{'path': '/Game/Synthetic.Synthetic:PersistentLevel.Actor_0', 'class': 'Actor',
                'transform': "<Struct 'Transform' (0x11111111) {translation: {x: 0.000000}}>", 'meshes': []}]}
        self.baseline = {'editor': {'pid': 123, 'start_utc': '2026-10-23T00:00:00Z',
            'project': 'C:/Synthetic/Synthetic.uproject', 'world': self.context['world']},
            'context': copy.deepcopy(self.context)}
        self.config = {'editor': copy.deepcopy(self.baseline['editor']), 'engine_version': 'synthetic-engine',
                       'baseline': {'sha256': 'a' * 64}, 'offset': 0,
                       'reader': {'sha256': 'b' * 64, 'bytes': 12345}}
        self.observed, self.pid, self.engine, self.captures, self.engine_reads = copy.deepcopy(self.context), 123, 'synthetic-engine', 0, 0
        idle = SimpleNamespace(is_in_play_in_editor=lambda: False, get_active_executor=lambda: None)
        unreal = SimpleNamespace(SystemLibrary=SimpleNamespace(get_engine_version=self.engine_version),
            EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: [], get_dirty_map_packages=lambda: []),
            LevelEditorSubsystem=object(), MoviePipelineQueueSubsystem=object(), AutomationTestToolset=object(),
            get_editor_subsystem=lambda _: idle,
            AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: SimpleNamespace(is_loading_assets=lambda: False)),
            InterchangeManager=SimpleNamespace(get_interchange_manager_scripted=lambda: SimpleNamespace(is_interchange_active=lambda: False)),
            get_default_object=lambda _: SimpleNamespace(call_method=lambda _: '{"state":"Idle"}'))
        self.scope = functions(['inventory_difference', 'inventory_refusal', 'inventory_admission'],
            json=json, hashlib=hashlib, datetime=datetime, timezone=timezone,
            memory=lambda _: None, source=lambda _: json.dumps(self.baseline).encode(),
            os=SimpleNamespace(getpid=lambda: self.pid), context=self.capture, unreal=unreal)

    def capture(self):
        self.captures += 1
        return copy.deepcopy(self.observed)

    def engine_version(self):
        self.engine_reads += 1
        return self.engine

    def admission(self, phase='before_metadata', loads=0):
        return self.scope['inventory_admission'](self.config, phase=phase, metadata_load_calls=loads)

    def refused(self, comparison, phase='before_metadata', loads=0):
        with self.assertRaisesRegex(RuntimeError, 'Inventory editor/current protected context differs: ') as caught:
            self.admission(phase, loads)
        error = caught.exception
        self.assertNotIn('\n', str(error))
        self.assertLess(len(str(error)), 4096)
        report = json.loads(str(error).split(': ', 1)[1])
        self.assertEqual(report, error.inventory_evidence)
        self.assertEqual((report['comparison'], report['phase'], report['metadata_load_calls']), (comparison, phase, loads))
        self.assertLessEqual(datetime.fromisoformat(report['capture_started_utc']), datetime.fromisoformat(report['capture_finished_utc']))
        self.assertEqual(report['baseline_sha256'], self.config['baseline']['sha256'])
        self.assertEqual((report['reader_sha256'], report['reader_bytes']), ('b' * 64, 12345))
        return report

    def test_equal_context_passes_without_diagnostic_or_second_capture(self):
        self.assertIsNone(self.admission())
        self.assertEqual((self.captures, self.engine_reads), (1, 1))

    def test_editor_and_pid_refusals_keep_original_short_circuit_order(self):
        self.config['editor']['start_utc'] = 'different-generation'
        report = self.refused('editor')
        self.assertEqual(report['first_difference']['path'], ['editor', 'start_utc'])
        self.assertEqual((self.captures, self.engine_reads), (0, 0))
        self.config['editor'] = copy.deepcopy(self.baseline['editor'])
        self.pid = 456
        report = self.refused('pid')
        self.assertEqual(report['first_difference']['actual'], {'type': 'int', 'json': '456', 'truncated': False})
        self.assertEqual((self.captures, self.engine_reads), (0, 0))

    def test_real_transform_change_stays_refused_with_exact_actor_identity(self):
        self.observed['actors'][0]['transform'] = self.observed['actors'][0]['transform'].replace('0.000000', '1.000000')
        report = self.refused('context', 'after_metadata', 32)
        self.assertEqual(report['first_difference']['path'], ['context', 'actors', 0, 'transform'])
        self.assertEqual(report['actor_identity']['actual'], self.context['actors'][0]['path'])
        self.assertIn('1.000000', report['first_difference']['actual']['json'])
        self.assertEqual((self.captures, self.engine_reads), (1, 0))

    def test_pointer_text_is_not_normalized_or_asserted_as_production_cause(self):
        self.observed['actors'][0]['transform'] = self.observed['actors'][0]['transform'].replace('0x11111111', '0x22222222')
        report = self.refused('context')
        self.assertIn('0x11111111', report['first_difference']['expected']['json'])
        self.assertIn('0x22222222', report['first_difference']['actual']['json'])

    def test_camera_world_component_and_actor_changes_remain_refused(self):
        changes = [('camera', lambda c: c['camera'].__setitem__(0, 1.000001)),
                   ('world', lambda c: c.__setitem__('world', '/Game/Other.Other')),
                   ('meshes', lambda c: c['actors'][0]['meshes'].append(['component', 'mesh'])),
                   ('actors', lambda c: c['actors'].clear())]
        for field, change in changes:
            with self.subTest(field=field):
                self.observed = copy.deepcopy(self.context)
                change(self.observed)
                report = self.refused('context')
                self.assertIn(field, report['first_difference']['path'])
                if field == 'actors':
                    self.assertEqual(report['first_difference']['actual']['type'], 'absent')
                    self.assertEqual(report['actor_identity']['expected'], self.context['actors'][0]['path'])

    def test_oversized_actor_identity_keeps_parseable_bounded_error_and_full_journal_evidence(self):
        self.observed['actors'][0]['path'] = 'x' * 10000
        with self.assertRaises(RuntimeError) as caught:
            self.admission()
        error = caught.exception
        report = json.loads(str(error).split(': ', 1)[1])
        self.assertTrue(report['evidence_summary'])
        self.assertLess(len(str(error)), 4096)
        self.assertEqual(len(error.inventory_evidence['actor_identity']['actual']), 10000)

    def test_engine_refusal_remains_after_exact_context_capture(self):
        self.engine = 'different-engine'
        report = self.refused('engine_version')
        self.assertEqual(report['first_difference']['actual']['type'], 'str')
        self.assertEqual((self.captures, self.engine_reads), (1, 1))

    def test_scalar_type_and_bounded_value_are_retained(self):
        self.observed['camera'][0] = 'x' * 2000
        report = self.refused('context')
        self.assertEqual(report['first_difference']['expected']['type'], 'float')
        self.assertEqual(report['first_difference']['actual']['type'], 'str')
        self.assertTrue(report['first_difference']['actual']['truncated'])
        self.assertNotEqual(report['expected_sha256'], report['actual_sha256'])

    def test_serialization_is_diagnostic_only_python_equal_values_stay_equal(self):
        self.observed['camera'][0] = 1  # Existing Python guard treats int 1 == float 1.0.
        self.assertIsNone(self.admission())


if __name__ == '__main__':
    unittest.main()
