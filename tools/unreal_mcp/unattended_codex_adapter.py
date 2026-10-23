# SPDX-License-Identifier: MIT
"""Closed one-Codex-coupler adapter to the existing owner importer and guards.

No editor/service launch, settings edit, reimport, world placement or generic
graph evaluation. Uses the existing local retained-call guard; no new transport.
"""
import importlib
import json
from pathlib import Path
import sys
import time
import uuid

if __package__:
    from . import unattended_ingestion as q
else:
    import unattended_ingestion as q

VERSION = 'daedalus.codex-coupler-owner-adapter.v1'
NAME = 'CodexModule_CopperPatina_BridgeCoupler_85000'
SOURCE_SHA = 'd09d0b1aaacea5d4474ed8745733cba69a9793172cd69c76a0fd44d78d118714'
MATERIAL = '/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/'


def policy(item):
    q.checked_file(item['policy'])
    cfg = q.load(item['policy']['path'])
    if cfg.get('schema') != VERSION or cfg.get('selected_name') != NAME:
        raise q.Refused('Only the qualified original Codex coupler is supported')
    for key in ('source_manifest', 'importer', 'native', 'guard', 'parity', 'baseline', 'material'):
        q.checked_file(cfg[key])
    raw = q.load(cfg['source_manifest']['path'])
    rows = raw.get('assets', [])
    if raw.get('schema') != 'daedalus.codex-prepared-delivery.v1' or len(rows) != 24:
        raise q.Refused('Exact original24 manifest required')
    selected = [r for r in rows if r['name'] == NAME]
    if (len(selected) != 1 or selected[0]['kind'] != 'module' or len(selected[0]['objects']) != 1
            or selected[0]['fbx']['sha256'] != SOURCE_SHA or item['sources'] != [selected[0]['fbx']]
            or selected[0]['objects'][0]['triangles'] != 416
            or selected[0]['objects'][0]['dims'] != [4.0, 1.0, 0.5]
            or not item['destination'].startswith(ROOT + 'UnattendedWitness20261022/')):
        raise q.Refused('Closed source/profile/owned destination differs')
    if cfg.get('expect') != {'triangles': 416, 'material_slots': 2, 'nanite': False, 'simple_collision': 0}:
        raise q.Refused('Do not relax the qualified source profile')
    q.utc_seconds(cfg['start_by_utc'])
    return cfg


class Adapter:
    def __init__(self, frozen, folder):
        self.frozen, self.folder = frozen, Path(folder)
        if len(frozen['items']) != 1:
            raise q.Refused('One isolated witness only; no bulk adoption')
        self.cfg = policy(frozen['items'][0])
        parent = str(Path(self.cfg['guard']['path']).parent)
        sys.path.insert(0, parent)
        self.guard = importlib.import_module(Path(self.cfg['guard']['path']).stem)
        self.parity = importlib.import_module(Path(self.cfg['parity']['path']).stem)
        if Path(self.guard.__file__).resolve() != Path(self.cfg['guard']['path']).resolve():
            raise q.Refused('Guard module origin differs')
        self.guard.verify = self.parity.verify  # existing supported composition, same protected files/parity
        self.guard.launch = lambda: {'pid': frozen['editor']['pid'], 'start_utc': frozen['editor']['start_utc']}
        if self.guard.BASELINE != q.load(self.cfg['baseline']['path'])['result']['after']['snapshot']:
            raise q.Refused('Existing exact native baseline differs')

    def _native(self, item, phase, operation=None, snapshots=None, assets=None):
        cfg = policy(item);host = self.guard.p.b
        host.g.resources()
        locks = host.hub('/locks')
        if (locks.get('unreal', {}).get('holder') != self.frozen['owner']
                or locks.get('compute', {}).get('holder') not in (None, self.frozen['owner'])):
            raise q.Refused('Normal owner custody/compute unavailable')
        # Never silently take over a retained compute turn from another call.
        if locks.get('compute'):
            raise q.Refused('Existing compute turn must reach terminal/release first')
        claim = host.hub('/lock', {'me': self.frozen['owner'], 'name': 'compute', 'ttl': 600,
            'note': 'One closed Codex coupler unattended-runner witness; no world writes/reimport/bulk.'})
        if not claim.get('ok'):
            raise q.Refused('Atomic ordinary compute claim refused')
        key = operation or 'read-' + uuid.uuid4().hex
        out = self.folder / 'native' / key
        out.mkdir(exist_ok=True)
        self.guard.OUT = out
        native_cfg = {'phase': phase, 'operation_id': operation, 'item': item,
            'snapshots': snapshots, 'assets': assets, 'policy': cfg,
            'folder': str(out), 'frozen': self.frozen}
        body = Path(cfg['native']['path']).read_text(encoding='utf-8')
        action = 'CFG = ' + repr(native_cfg) + '\n' + body
        known = False
        try:
            # Existing guard enforces same PID/listener, exact9native baseline,
            # empty queue/inflight, normal RAM and retained no-replay dispatch.
            result = self.guard.invoke(phase, action, vacant=False)
            known = True
            return result
        finally:
            not_dispatched = not (out / phase / 'native-dispatch.json').exists()
            if known or not_dispatched:
                released = host.hub('/unlock', {'me': self.frozen['owner'], 'name': 'compute'})
                after = host.hub('/locks')
                q.receipts.write_receipt(out / (phase + '-compute-release.json'),
                    {'utc': q.receipts.utc_now(), 'unlock': released, 'readback': after})
                if not released.get('ok') or released.get('lock') is not None or 'compute' in after:
                    raise q.Refused('Normal compute release/readback failed')
            # Unknown dispatch retains its lease/journal for reconciliation;
            # no force unlock, timeout replay or TTL-as-handover.

    def admit(self, item, phase):
        if phase == 'execute' and time.time() > q.utc_seconds(self.cfg['start_by_utc']):
            raise q.Refused('Finite witness start window expired; no new import')
        result = self._native(item, 'admit')
        value = result['action']
        return {'state': 'ready', 'editor': self.frozen['editor'],
            'engine_version': value['engine_version'], 'holder': self.frozen['owner'],
            'exclusive_writer': True, 'idle': value['idle'], 'preserved': result['preserved'],
            'policy_verified': value['policy_verified'], 'destination_vacant': value['destination_vacant']}

    def _completion(self, item, operation, receipt_path):
        folder = self.folder / 'native' / operation
        imported = q.load(folder / 'import/terminal.json')['result']['action']
        terminal = folder / 'validate/terminal.json'
        if terminal.exists():
            actual = q.load(terminal)['result']
        else:
            actual = self._native(item, 'validate', operation, assets=imported['assets'])
        value = actual['action']
        output = {p: {'path': str(Path(self.frozen['editor']['project']).parent / 'Content' /
                     (p.split('.')[0][len('/Game/'):] + '.uasset'))} for p in imported['assets']}
        for row in output.values():row.update(q.receipts.fingerprint(row['path']))
        result = {'schema': q.VERSION, 'state': 'complete', 'operation_id': operation,
            'item_key': q.digest(item), 'destination': item['destination'],
            'engine_version': value['engine_version'], 'assets': imported['assets'], 'outputs': output,
            'validation': value['envelope'], 'preserved': actual['preserved'],
            'capture': {'editor': self.frozen['editor'], 'operation_id': operation,
                'start_utc': value['start_utc'], 'end_utc': value['end_utc'], 'route': 'existing:execute_python/DaedalusEditorAcceptanceLibrary.ValidateNamedAssets'}}
        q.receipts.write_receipt(receipt_path, result)
        return result

    def execute(self, item, operation, snapshots, receipt_path):
        self._native(item, 'import', operation, snapshots=snapshots)
        return self._completion(item, operation, receipt_path)

    def reconcile(self, item, operation):
        path = self.folder / 'native' / (operation + '.json')
        if path.exists():return {'state': 'complete', 'result': q.load(path)}
        folder = self.folder / 'native' / operation
        # No import dispatch is ever retried. Only known import terminal can
        # advance to the once-only validation/read step; unknown stays pending.
        if not (folder / 'import/terminal.json').exists():return {'state': 'pending'}
        if (folder / 'validate/native-dispatch.json').exists() and not (folder / 'validate/terminal.json').exists():
            return {'state': 'pending'}
        return {'state': 'complete', 'result': self._completion(item, operation, path)}

    def verify_saved(self, item, result):
        read = self._native(item, 'verify', assets=result['assets'])
        return read['preserved'] is True and read['action']['qualified_readback'] is True


def create(frozen, folder):
    return Adapter(frozen, folder)
