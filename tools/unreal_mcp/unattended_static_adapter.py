# SPDX-License-Identifier: MIT
"""Owner-only small-static profile; reuses qualified-static steps and wire.call.

Preparation/policy inspection is file-only. Only the sole editor writer may run
this adapter. No existing queue, importer, Coupler fixture or validation changes.
"""
import importlib.util
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import uuid

if __package__:
    from . import unattended_ingestion as q
else:
    import unattended_ingestion as q

VERSION = 'daedalus.qualified-static-owner-adapter.v1'
PREFIX = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/'
LABEL = 'Codex qualified small-static packet asset-only import-save'
UNIT = 'claude_raw_unit100_build1_actor001_v1'
HELPER_SHA = 'ff67f266fa45b276d287d69d5fa750b445353960d7213234dede15bc1f135df0'
SHARED_SHA = '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03'


def pin(path):
    return {'path': str(Path(path).resolve()), **q.receipts.fingerprint(path)}


def selected(item, cfg):
    """The source review is a real witness, never inferred from a sidecar/stage."""
    doc = q.load(q.checked_file(cfg['qualification']))
    if (doc.get('schema') != 'daedalus.source-qualified-small-static.v1'
            or doc.get('stage') != 'qualified_static_candidates_source_only'
            or doc.get('source_views_personally_inspected_by_operator') is not True):
        raise q.Refused('Exact operator-reviewed source qualification required')
    # Existing prepare() requires the operator's actual source-view inspection,
    # not a new human approval, reviewer identity or review-format ceremony.
    # Verify an image witness when retained, without inventing extra fields.
    review = doc.get('operator_visual_review', {})
    if isinstance(review, dict) and 'actual_image' in review:
        q.checked_file(review['actual_image'])
    for witness in doc['source_pins']:
        q.checked_file(witness)
    rows = doc['items']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        raise q.Refused('One to three explicitly qualified sources required')
    hashes, destinations, names = set(), set(), set()
    for row in rows:
        sha = row['fingerprint']['sha256']
        dest, name = row['destination'].casefold(), row['name'].casefold()
        if (sha in hashes or name in names or any(dest == old or dest.startswith(old + '/')
                or old.startswith(dest + '/') for old in destinations)):
            raise q.Refused('Duplicate source hash/name or overlapping destination')
        hashes.add(sha); destinations.add(dest); names.add(name)
        if (not row['destination'].startswith(PREFIX) or sha[:16] not in row['destination']
                or row.get('source_unit_scale_factor') != 100
                or row.get('mesh_geometry_count') != 1 or row.get('mesh_model_count') != 1
                or type(row.get('triangles')) is not int or not 1 <= row['triangles'] <= 3000
                or any(type(row.get(k)) is not int or row[k] != 0 for k in
                       ('animations', 'animation_curves', 'deformers', 'textures', 'videos', 'authored_ucx'))
                or not row.get('provenance') or not row.get('rgba_bytes')):
            raise q.Refused('Existing bounded static source policy differs')
        for pathkey, fpkey in (('fbx', 'fingerprint'), ('sidecar', 'sidecar_fingerprint')):
            q.checked_file({'path': row[pathkey], **row[fpkey]})
    matches = [row for row in rows if row['name'] == cfg['selected_name']]
    if len(matches) != 1:
        raise q.Refused('Exact selected qualified source absent')
    row = matches[0]
    sources = [{'path': row['fbx'], **row['fingerprint']},
               {'path': row['sidecar'], **row['sidecar_fingerprint']}]
    if item['sources'] != sources or item['destination'] != row['destination']:
        raise q.Refused('Selected source/sidecar/destination binding differs')
    return row


def policy(item):
    cfg = q.load(q.checked_file(item['policy']))
    required = {'schema', 'owner', 'selected_name', 'qualification', 'importer', 'shared',
                'native', 'wire', 'host', 'baseline', 'dedup', 'start_by_utc', 'unit_contract'}
    if set(cfg) != required or cfg['schema'] != VERSION or cfg['unit_contract'] != UNIT:
        raise q.Refused('Unknown small-static profile; no Coupler substitution')
    for key in ('qualification', 'importer', 'shared', 'native', 'wire', 'host', 'baseline', 'dedup'):
        q.checked_file(cfg[key])
    # Only the retained proven importer and catalogue are accepted. Context is
    # parameterized in a private helper scope; their source is never modified.
    if cfg['importer']['sha256'] != HELPER_SHA or cfg['shared']['sha256'] != SHARED_SHA:
        raise q.Refused('Retained existing importer/catalogue bytes differ')
    if cfg['native'] != pin(Path(__file__).with_name('unattended_static_native.inc')):
        raise q.Refused('Reviewed native wrapper differs')
    q.utc_seconds(cfg['start_by_utc'])
    return cfg, selected(item, cfg)


def snapshots_for(item, snapshots):
    if (not isinstance(snapshots, list) or len(snapshots) != 2
            or any({k: s[k] for k in ('sha256', 'bytes')} !=
                   {k: r[k] for k in ('sha256', 'bytes')}
                   or Path(s['path']).suffix.lower() != Path(r['path']).suffix.lower()
                   for s, r in zip(snapshots, item['sources']))):
        raise q.Refused('Immutable FBX/sidecar snapshots differ from selected source')
    for witness in snapshots:
        q.checked_file(witness)
    return snapshots


def protected(cfg, frozen):
    baseline = q.load(cfg['baseline']['path'])
    if (set(baseline) != {'schema', 'editor', 'context', 'files'}
            or baseline['schema'] != 'daedalus.static-owner-baseline.v1'
            or baseline['editor'] != frozen['editor'] or not baseline['files']
            or baseline['context'].get('world') != frozen['editor']['world']):
        raise q.Refused('Fresh exact current editor/context/protected-file baseline required')
    for witness in baseline['files']:
        q.checked_file(witness)
    # Require at least the active saved map, installed DLL and shared palette;
    # the owner also lists all other current protected files, never a directory sweep.
    files = {str(Path(r['path']).resolve()).casefold() for r in baseline['files']}
    project = Path(frozen['editor']['project']).parent
    world = frozen['editor']['world'].split('.')[0]
    required = [project / 'Content' / (world[len('/Game/'):] + '.umap'),
                project / 'Plugins/DaedalusLink/Binaries/Win64/UnrealEditor-DaedalusLink.dll',
                project / 'Content/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.uasset']
    if not {str(p.resolve()).casefold() for p in required}.issubset(files):
        raise q.Refused('Active saved map/DLL/palette must be protected')
    return baseline


def load_module(witness):
    path = q.checked_file(witness)
    # No top-level native/client requests are made by the retained modules.
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('_static_' + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Adapter:
    def __init__(self, frozen, folder):
        self.frozen, self.folder = frozen, Path(folder)
        if not 1 <= len(frozen['items']) <= 3:
            raise q.Refused('At most three qualified static items')
        hashes, destinations = set(), set()
        common = None
        for item in frozen['items']:
            cfg, row = policy(item)
            if cfg['owner'] != frozen['owner']:
                raise q.Refused('Profile owner differs')
            shared = {k: v for k, v in cfg.items() if k != 'selected_name'}
            if common is not None and shared != common:
                raise q.Refused('One shared custody/baseline/profile per queue')
            common = shared
            sha, dest = row['fingerprint']['sha256'], item['destination'].casefold()
            if sha in hashes or any(dest == old or dest.startswith(old + '/')
                                   or old.startswith(dest + '/') for old in destinations):
                raise q.Refused('Duplicate source hash or destination across policies')
            hashes.add(sha); destinations.add(dest)
            protected(cfg, frozen)
        self.host = load_module(cfg['host'])
        self.wire = self.host.g.d.wire
        if (Path(self.wire.__file__).resolve() != Path(cfg['wire']['path']).resolve()
                or self.wire.UNREAL != ('127.0.0.1', 9877)):
            raise q.Refused('Existing loopback bridge endpoint differs')
        # Pin the existing retained-call chain as well as the native importer.
        dependencies = {str(q.checked_file(p).resolve()).casefold() for p in frozen['dependencies']}
        for module in (self.host, self.host.g, self.host.g.d, self.wire):
            if str(Path(module.__file__).resolve()).casefold() not in dependencies:
                raise q.Refused('Retained host/transport dependency not pinned')

    def _call(self, item, phase, operation=None, snapshots=None, completion=None):
        cfg, row = policy(item)
        baseline = protected(cfg, self.frozen)
        if phase == 'execute':
            if time.time() > q.utc_seconds(cfg['start_by_utc']):
                raise q.Refused('Finite start window expired')
            snapshots_for(item, snapshots)
        resource = q.resources(self.folder)
        if (resource['physical'] < q.MIN_PHYSICAL or resource['commit'] < q.MIN_COMMIT
                or resource['disk'] < q.MIN_DISK):
            raise q.Refused('Resource floor; no native dispatch')
        observed = self.host.os_state()
        editors = observed['editors']
        if isinstance(editors, dict): editors = [editors]
        listeners = observed['listeners']
        if isinstance(listeners, dict): listeners = [listeners]
        editor = self.frozen['editor']
        if (len(editors) != 1 or editors[0]['Id'] != editor['pid']
                or editors[0]['StartUtc'] != editor['start_utc']
                or not any(v['LocalAddress'] == '127.0.0.1' and v['LocalPort'] == 9877
                           and v['OwningProcess'] == editor['pid'] for v in listeners)):
            raise q.Refused('Exact sole editor generation/listener required')
        locks = self.host.hub('/locks')
        own = locks.get('unreal', {})
        if (own.get('holder') != self.frozen['owner'] or locks.get('compute')
                or own.get('at', 0) + own.get('ttl', 0) < time.time() + 300):
            raise q.Refused('Ordinary current sole-writer custody/vacant compute required')
        key = operation or 'read-' + uuid.uuid4().hex
        folder = self.folder / 'native' / key
        folder.mkdir()  # Existing dispatch/result is NEVER overwritten or replayed.
        if phase in ('verify', 'admit_verify'):
            snapshots = [{'path': str(self.folder / 'inputs' / item['id'] / Path(r['path']).name),
                          **{k: r[k] for k in ('sha256', 'bytes')}} for r in item['sources']]
            snapshots_for(item, snapshots)
        known = {}
        for previous in self.frozen['items']:
            checkpoint = self.folder / 'items' / (previous['id'] + '.json')
            if not checkpoint.exists(): continue
            checkpoint = q.load(checkpoint)
            if (checkpoint.get('checkpoint_sha256') != q.digest({k: v for k, v in checkpoint.items()
                                                                  if k != 'checkpoint_sha256'})
                    or checkpoint.get('item_key') != q.digest(previous)):
                raise q.Refused('Cross-item checkpoint corrupt')
            if checkpoint.get('state') == 'DONE':
                for asset, witness in checkpoint['result']['outputs'].items():
                    q.checked_file(witness)
                    known[asset] = previous['sources'][0]['sha256']
        payload = {'phase': phase, 'operation_id': operation, 'item': item, 'selected': row,
                   'policy': cfg, 'frozen': self.frozen, 'baseline': baseline,
                   'folder': str(folder), 'snapshots': snapshots, 'completion': completion,
                   'known_outputs': known, 'receipts': pin(q.RECEIPTS),
                   'stop_path': str(self.folder / 'STOP'),
                   'receipt_path': str(self.folder / 'native' / (key + '.json'))}
        code = 'CFG = ' + repr(payload) + '\n' + Path(cfg['native']['path']).read_text(encoding='utf-8')
        if phase == 'execute' and (self.folder / 'STOP').exists():
            raise q.Refused('STOP persists; no native dispatch')
        claim = self.host.hub('/lock', {'me': self.frozen['owner'], 'name': 'compute',
            'ttl': 600, 'note': 'Bounded qualified small-static owner adapter; no world writes.'})
        claimed = claim.get('lock', {})
        def same_lease(current):
            return (claimed.get('holder') == self.frozen['owner']
                    and claimed.get('at', 0) > 0 and claimed.get('ttl', 0) > 0
                    and all(current.get(k) == claimed.get(k) for k in ('holder', 'at', 'ttl')))
        dispatched = known = False
        try:
            if not claim.get('ok') or not same_lease(self.host.hub('/locks').get('compute', {})):
                raise q.Refused('Ordinary exact compute claim not confirmed')
            q.receipts.write_receipt(folder / 'dispatch.json', {'operation_id': operation,
                'phase': phase, 'compute': claimed, 'code_sha256': q.digest(code),
                'editor': editor, 'replay_permitted': False})
            dispatched = True  # From here even a transport exception is uncertain.
            value = self.host.g.retained_call(SimpleNamespace(folder=folder), 'native',
                'daedalus.steps', code, label=LABEL, budget_ms=1, timeout=240)
            q.receipts.write_receipt(folder / 'terminal.json', value)
            known = True
            protected(cfg, self.frozen)
            return value
        finally:
            # Unknown dispatch retains its exact lease and journal for its owner;
            # expiry alone never establishes that native work stopped.
            if (known or not dispatched) and claimed.get('holder') == self.frozen['owner']:
                if not same_lease(self.host.hub('/locks').get('compute', {})):
                    raise q.Refused('Compute identity changed; never unlock another turn')
                release = self.host.hub('/unlock', {'me': self.frozen['owner'], 'name': 'compute'})
                after = self.host.hub('/locks')
                q.receipts.write_receipt(folder / 'release.json', {'reply': release, 'after': after})
                if not release.get('ok') or after.get('compute'):
                    raise q.Refused('Normal compute release not confirmed')

    def admit(self, item, phase):
        # An incomplete earlier result cannot dispatch even a read admission.
        # Complete receipt + owner-reconciled lease allow current read-only
        # admission; reconcile itself never dispatches any native call.
        if phase == 'reconcile':
            prior = q.load(self.folder / 'items' / (item['id'] + '.json'))
            result = self.reconcile(item, prior['operation_id'])
            if result['state'] != 'complete':
                raise q.Refused('Native result uncertain; owner reconciliation required, no dispatch')
        value = self._call(item, 'admit_' + phase)
        return {'state': 'ready', 'editor': self.frozen['editor'],
                'engine_version': value['engine_version'], 'holder': self.frozen['owner'],
                'exclusive_writer': True, 'idle': True, 'preserved': value['preserved'],
                'policy_verified': True, 'destination_vacant': value['destination_vacant']}

    def execute(self, item, operation_id, snapshots, native_receipt_path):
        expected = self.folder / 'native' / (operation_id + '.json')
        if Path(native_receipt_path).resolve() != expected.resolve():
            raise q.Refused('Operation receipt path differs')
        value = self._call(item, 'execute', operation_id, snapshots)
        result = q.load(expected)
        if result != value['completion']:
            raise q.Refused('Durable native completion differs')
        return result

    def reconcile(self, item, operation_id):
        # Pure file read: no import, save, validation, receipt reconstruction or
        # timestamp changes. Incomplete receipts require explicit owner recovery.
        path = self.folder / 'native' / (operation_id + '.json')
        if not path.is_file(): return {'state': 'pending'}
        result = q.load(path)
        if (result.get('operation_id') != operation_id or result.get('item_key') != q.digest(item)
                or result.get('state') != 'complete'):
            raise q.Refused('Retained operation identity differs')
        return {'state': 'complete', 'result': result}

    def verify_saved(self, item, result):
        for witness in result['outputs'].values(): q.checked_file(witness)
        return self._call(item, 'verify', completion=result)['qualified_readback'] is True


def create(frozen_manifest, state_directory):
    return Adapter(frozen_manifest, state_directory)
