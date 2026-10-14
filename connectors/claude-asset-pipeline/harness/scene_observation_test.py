# SPDX-License-Identifier: MIT
"""Pinned producer fixtures and consumer-specific shape/diagnostic regressions; no editor."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asset_pipeline import scene_observation as scene

FIXTURE=json.loads((Path(__file__).parent/'fixtures'/'scene_v1_offline.json').read_text(encoding='utf-8'))


class ConsumerTest(unittest.TestCase):
    def test_actual_pinned_producer_snapshots(self):
        for name in ('snapshot_reply','empty_snapshot_reply','partial_page_reply'):
            with self.subTest(name=name):
                scene.snapshot(FIXTURE[name]['result'])

    def test_actual_pinned_producer_verifications(self):
        for name in ('match','mismatch','unavailable','stale'):
            with self.subTest(name=name):
                scene.verification(FIXTURE['verify_'+name+'_reply']['result'],FIXTURE['verify_'+name+'_request'])

    def test_empty_exception_message_is_valid_but_missing_is_not(self):
        row={'path':None,'code':'OBSERVATION_ERROR','message':''}
        scene.errors([row],'errors')
        del row['message']
        with self.assertRaises(scene.SceneSchemaError): scene.errors([row],'errors')

    def test_unavailable_requires_explicit_null(self):
        reply=copy.deepcopy(FIXTURE['verify_unavailable_reply']['result'])
        request=FIXTURE['verify_unavailable_request']
        scene.verification(reply,request)
        del reply['checks'][0]['observed']
        with self.assertRaises(scene.SceneSchemaError): scene.verification(reply,request)

    def test_error_metadata_cannot_contradict_diagnostics(self):
        request=FIXTURE['verify_match_request']
        for count,truncated in ((0,True),(1,False)):
            reply=copy.deepcopy(FIXTURE['verify_match_reply']['result'])
            reply.update(observation_errors=[],error_count=count,errors_truncated=truncated)
            with self.assertRaises(scene.SceneSchemaError): scene.verification(reply,request)
        reply.update(observation_errors=[],error_count=1,errors_truncated=True)
        scene.verification(reply,request)
        del reply['error_count']
        with self.assertRaises(scene.SceneSchemaError): scene.verification(reply,request)

    def test_observed_predicate_cannot_be_forged_as_match(self):
        reply=copy.deepcopy(FIXTURE['verify_mismatch_reply']['result'])
        reply['passed']=True
        for row in reply['checks']:
            row['status']='match';row['mismatches']=[]
        with self.assertRaises(scene.SceneSchemaError):
            scene.verification(reply,FIXTURE['verify_mismatch_request'])


if __name__=='__main__':unittest.main()
