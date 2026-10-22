# SPDX-License-Identifier: MIT
"""Offline queue witnesses. ALL native-looking adapter results here are SYNTHETIC."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unattended_ingestion as q
from test_native_validation_snapshot_consumer import base


def enough(_):
    return {'physical': q.MIN_PHYSICAL, 'commit': q.MIN_COMMIT, 'disk': q.MIN_DISK}


class SyntheticAdapter:
    """No Unreal imports, network or process launch; fake assets are local text."""
    def __init__(self, frozen, folder):
        self.frozen, self.folder = frozen, Path(folder)
        self.calls = []; self.mode = 'pass'; self.guard_change = {}

    def admit(self, item, phase):
        self.calls.append(('admit', phase))
        return {'state': 'ready', 'editor': self.frozen['editor'],
            'engine_version': self.frozen['engine_version'], 'holder': self.frozen['owner'],
            'exclusive_writer': True, 'idle': True, 'preserved': True,
            'policy_verified': True, 'destination_vacant': True, **self.guard_change}

    def verify_saved(self, item, result):
        self.calls.append(('verify', item['id']))
        return True

    def reconcile(self, item, operation):
        self.calls.append(('reconcile', operation))
        path = self.folder / 'native' / (operation + '.json')
        return {'state': 'complete', 'result': q.load(path)} if path.exists() else {'state': 'pending'}

    def execute(self, item, operation, snapshots, receipt_path):
        self.calls.append(('execute', operation))
        if self.mode == 'timeout':
            raise TimeoutError('SYNTHETIC unknown transport outcome')
        if self.mode == 'stop':
            (self.folder / 'STOP').touch()
        asset = item['destination'] + '/Mesh.Mesh'
        output = Path(self.frozen['editor']['project']).parent / 'Content' / (asset.split('.')[0][len('/Game/'):] + '.uasset')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b'SYNTHETIC NOT AN UNREAL ASSET')
        now = datetime.now(timezone.utc).isoformat()
        doc = base();old = next(iter(doc['results']['AssetsDetails']))
        detail = doc['results']['AssetsDetails'].pop(old)
        detail.update(PackageName=asset.split('.')[0], AssetName='Mesh')
        doc['results']['AssetsDetails'][asset] = detail
        doc['requested_assets'] = [asset]
        doc['settings']['ValidationUsecase'] = 'Script'
        doc['provenance'] = {'fresh_out_results': 'attested', 'native_invocation': 'attested', 'captured_at_utc': now}
        envelope = {'status': 'Valid', 'accepted': True, 'native_invoked': True,
                    'cancellation_observed': False, 'native_return': 0, 'snapshot_json': json.dumps(doc)}
        result = {'schema': q.VERSION, 'state': 'complete', 'operation_id': operation,
            'item_key': q.digest(item), 'destination': item['destination'],
            'engine_version': self.frozen['engine_version'], 'assets': [asset],
            'outputs': {asset: {'path': str(output), **q.receipts.fingerprint(output)}},
            'validation': envelope, 'preserved': True,
            'capture': {'editor': self.frozen['editor'], 'operation_id': operation,
                        'start_utc': now, 'end_utc': now, 'route': 'SYNTHETIC_NO_EDITOR'}}
        q.receipts.write_receipt(receipt_path, result)
        if self.mode == 'exit':
            os._exit(73) # child-only abrupt exit, no finally, AFTER receipt/before DONE
        return result


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, data in [('adapter.py', b'VERSION="synthetic-v1"\n'),
                           ('binary.dll', b'SYNTHETIC dependency'), ('source.glb', b'SYNTHETIC source'),
                           ('policy.json', b'{"profile":"strict-test-only"}')]:
            (self.root / name).write_bytes(data)
        def pin(name):
            p = self.root / name
            return {'path': str(p), **q.receipts.fingerprint(p)}
        self.doc = {'schema': q.VERSION, 'owner': 'codex-play-guard',
            'owned_destination': '/Game/CodexToolEvaluation/QueueOffline', 'engine_version': 'SYNTHETIC',
            'editor': {'pid': 123, 'start_utc': '2026-10-22T00:00:00Z',
                       'project': str(self.root / 'Synthetic.uproject'), 'world': '/Game/Synthetic.Synthetic'},
            'adapter': {'file': pin('adapter.py'), 'version': 'synthetic-v1'},
            'dependencies': [pin('binary.dll')],
            'items': [{'id': 'One', 'destination': '/Game/CodexToolEvaluation/QueueOffline/One',
                       'sources': [pin('source.glb')], 'policy': pin('policy.json')}]}
        self.source = self.root / 'manifest.json'
        self.folder = self.root / 'state'
        self.write_manifest()

    def write_manifest(self):
        self.source.write_text(json.dumps(self.doc))

    def ready(self):
        q.prepare(self.source, self.folder)
        backend = SyntheticAdapter(q.manifest(self.folder / 'manifest.json'), self.folder)
        return q.Runner(self.folder, backend, sample=enough), backend

    def item(self):
        return q.load(self.folder / 'items/One.json')

    def test_happy_and_resume_no_second_effect(self):
        run, backend = self.ready();result = run.run()
        self.assertEqual(result['items']['One']['state'], 'DONE')
        run.run();self.assertEqual(sum(c[0] == 'execute' for c in backend.calls), 1)
        self.assertIn(('verify', 'One'), backend.calls)
        self.assertFalse(result['production_adoption'])

    def test_actual_child_process_interruption_and_resume(self):
        self.ready()
        code = """import sys;sys.path.insert(0,sys.argv[1]);import test_unattended_ingestion as t
p=t.Path(sys.argv[2]);b=t.SyntheticAdapter(t.q.manifest(p/'manifest.json'),p);b.mode=sys.argv[3]
t.q.Runner(p,b,sample=t.enough).run()
"""
        first = subprocess.run([sys.executable, '-c', code, str(Path(__file__).parent), str(self.folder), 'exit'], capture_output=True)
        self.assertEqual(first.returncode, 73, first.stderr)
        self.assertEqual(self.item()['state'], 'INFLIGHT')
        before = list((self.folder / 'native').glob('*.json'));self.assertEqual(len(before), 1)
        second = subprocess.run([sys.executable, '-c', code, str(Path(__file__).parent), str(self.folder), 'pass'], capture_output=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.item()['state'], 'DONE')
        self.assertEqual(list((self.folder / 'native').glob('*.json')), before)

    def test_uncertain_stays_uncertain_without_second_execute(self):
        run, backend = self.ready();backend.mode = 'timeout';run.run()
        operation = self.item()['operation_id'];run.run()
        self.assertEqual(self.item()['state'], 'UNCERTAIN')
        self.assertEqual(sum(c[0] == 'execute' for c in backend.calls), 1)
        self.assertIn(('reconcile', operation), backend.calls)

    def test_stop_before_effect_and_after_active_terminal(self):
        run, backend = self.ready();(self.folder / 'STOP').touch();run.run()
        self.assertFalse(backend.calls)
        (self.folder / 'STOP').unlink();backend.mode = 'stop'
        result = run.run();self.assertTrue(result['stopped']);self.assertEqual(self.item()['state'], 'DONE')

    def test_stop_during_admission_prevents_effect(self):
        run, backend = self.ready();original = backend.admit
        def admit(*args):
            (self.folder / 'STOP').touch();return original(*args)
        backend.admit = admit;run.run()
        self.assertFalse(any(c[0] == 'execute' for c in backend.calls))

    def test_existing_state_preserved(self):
        self.ready();before = (self.folder / 'queue.json').read_bytes()
        with self.assertRaises(q.Refused):q.prepare(self.source, self.folder)
        self.assertEqual((self.folder / 'queue.json').read_bytes(), before)

    def test_duplicate_content_paths_and_nested_destinations_refused(self):
        (self.root / 'other.glb').write_bytes((self.root / 'source.glb').read_bytes())
        two = copy.deepcopy(self.doc['items'][0]);two.update(id='Two', destination=self.doc['owned_destination']+'/Two')
        two['sources'][0]['path'] = str(self.root / 'other.glb')
        self.doc['items'].append(two);self.write_manifest()
        with self.assertRaisesRegex(q.Refused, 'Duplicate source'):q.prepare(self.source, self.folder)
        self.doc['items'][1]['sources'][0] = self.doc['dependencies'][0]
        self.doc['items'][1]['destination'] = self.doc['items'][0]['destination']+'/Nested';self.write_manifest()
        with self.assertRaisesRegex(q.Refused, 'Duplicate/outside'):q.prepare(self.source, self.folder)

    def test_source_or_adapter_change_refused_without_backend(self):
        run, backend = self.ready();(self.root / 'source.glb').write_bytes(b'changed')
        with self.assertRaises(q.Refused):run.run()
        self.assertFalse(backend.calls)

    def test_freeze_wrong_runner_and_corrupt_record_refused(self):
        run, backend = self.ready();q.receipts.write_receipt(self.folder/'items/One.json', {'schema': 'wrong'})
        with self.assertRaises(q.Refused):run.run()
        self.assertFalse(backend.calls)
        meta=q.load(self.folder/'queue.json');meta['runner_sha256']='0'*64
        q.receipts.write_receipt(self.folder/'queue.json', meta)
        with self.assertRaises(q.Refused):q.Runner(self.folder,backend,sample=enough)

    def test_kernel_lock_blocks_competing_runner(self):
        run, backend = self.ready()
        with q.exclusive(self.folder):
            with self.assertRaises(q.Refused):run.run()
        self.assertFalse(backend.calls)

    def test_memory_retry_bound_without_dispatch_or_lower_floor(self):
        run, backend = self.ready();clock=[time.time()]
        run.clock=lambda:clock[0]
        run.sample=lambda _:dict(physical=q.MIN_PHYSICAL-1,commit=q.MIN_COMMIT,disk=q.MIN_DISK)
        for _ in range(4):run.run();clock[0]+=61
        self.assertEqual(self.item()['state'],'QUARANTINED')
        self.assertEqual(self.item()['attempts'],3);self.assertFalse(backend.calls)

    def test_done_low_memory_keeps_done_without_native_read(self):
        run, backend = self.ready();run.run();backend.calls.clear()
        run.sample=lambda _:dict(physical=0,commit=q.MIN_COMMIT,disk=q.MIN_DISK)
        result=run.run();self.assertEqual(self.item()['state'],'DONE');self.assertFalse(backend.calls)
        self.assertEqual(result['hold']['reason'],'low_memory')

    def test_only_known_predispatch_transient_can_wait(self):
        run, backend = self.ready()
        backend.guard_change={'state':'retry','code':'editor_busy','native_dispatched':False}
        run.run();self.assertEqual(self.item()['state'],'WAITING')
        self.assertFalse(any(c[0]=='execute' for c in backend.calls))

    def test_wrong_owner_editor_or_dirty_state_stops_before_effect(self):
        for changed in ({'holder':'other'}, {'idle':False},{'policy_verified':False},{'destination_vacant':False}):
            with self.subTest(changed=changed):
                temp=self.folder;self.folder=self.root/('state_'+str(len(list(self.root.glob('state*')))))
                run,backend=self.ready();backend.guard_change=changed;run.run()
                self.assertEqual(self.item()['state'],'QUARANTINED')
                self.assertFalse(any(c[0]=='execute' for c in backend.calls));self.folder=temp

    def test_saved_output_tamper_quarantined_no_reimport(self):
        run,backend=self.ready();run.run()
        Path(next(iter(self.item()['result']['outputs'].values()))['path']).write_bytes(b'tampered')
        run.run();self.assertEqual(self.item()['state'],'QUARANTINED')
        self.assertEqual(sum(c[0]=='execute' for c in backend.calls),1)

    def test_validation_refusal_and_identity_negatives(self):
        run,backend=self.ready();item=run.frozen['items'][0]
        result=backend.execute(item,'op',[item['sources'][0]],self.folder/'native/op.json')
        cases=[('NotValidated',lambda r:r['validation'].update(status='NotValidated',accepted=False)),
          ('Skipped',lambda r:r['validation'].update(status='Skipped',accepted=False)),
          ('no invocation',lambda r:r['validation'].update(native_invoked=False)),
          ('bool return',lambda r:r['validation'].update(native_return=False)),
          ('wrong op',lambda r:r.update(operation_id='other')),
          ('wrong namespace',lambda r:r.update(destination='/Game/Other')),
          ('not preserved',lambda r:r.update(preserved=False)),
          ('wrong output file',lambda r:next(iter(r['outputs'].values())).update(path=str(self.root/'source.glb'))),
          ('old time',lambda r:r['capture'].update(end_utc='2020-01-01T00:00:00Z'))]
        for name,change in cases:
            with self.subTest(name=name):
                altered=copy.deepcopy(result);change(altered)
                with self.assertRaises(q.Refused):q.validation(altered,item,run.frozen,'op',time.time())

    def test_unknown_provenance_and_warning_message_refused(self):
        run,backend=self.ready();item=run.frozen['items'][0]
        result=backend.execute(item,'op',item['sources'],self.folder/'native/op.json')
        for field in ('provenance','messages'):
            with self.subTest(field=field):
                altered=copy.deepcopy(result);doc=json.loads(altered['validation']['snapshot_json'])
                if field=='provenance':doc['provenance']['native_invocation']='unknown'
                else:next(iter(doc['results']['AssetsDetails'].values()))['ValidationMessages']=[{'Severity':'Warning','Text':'not accepted'}]
                altered['validation']['snapshot_json']=json.dumps(doc)
                with self.assertRaises(q.Refused):q.validation(altered,item,run.frozen,'op',time.time())

    def test_invalid_utc_and_duplicate_json_refused(self):
        for value in ('2026-10-22T00:00:00','2026-10-22T00:00:00+02:00','malformed'):
            with self.assertRaises(q.Refused):q.utc_seconds(value)
        self.source.write_text('{"schema":1,"schema":2}')
        with self.assertRaises(q.Refused):q.manifest(self.source)


if __name__ == '__main__':unittest.main()
