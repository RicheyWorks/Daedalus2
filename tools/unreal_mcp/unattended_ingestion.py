# SPDX-License-Identifier: MIT
"""Deterministic owner-adapter queue. No LLM, importer, service or editor launch.

Reuses the published ingestion receipt primitives. Native adoption requires a
reviewed, hash-pinned adapter implementing the narrow protocol in the README.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = ROOT / 'engines/unreal/DaedalusLink/Content/Python/daedalus_ingestion_receipts.py'
RECEIPTS_SHA = '1fe687e4658cfa28a5b47035bbecb32d1e1de75ead1ec0ea6d3450dce59b7117'
raw = RECEIPTS.read_bytes()
if hashlib.sha256(raw).hexdigest() != RECEIPTS_SHA:
    raise RuntimeError('Canonical published receipt primitive differs')
receipts = type(sys)('_unattended_published_receipts')
exec(compile(raw, str(RECEIPTS), 'exec'), receipts.__dict__)
if __package__:
    from . import native_validation_snapshot_consumer as consumer
else:
    import native_validation_snapshot_consumer as consumer

VERSION = 'daedalus.unattended-ingestion.v1'
MAX_ITEMS, MAX_ATTEMPTS = 256, 3
MIN_PHYSICAL, MIN_COMMIT, MIN_DISK = 1700000 * 1024, 2200000 * 1024, 10 * 1024**3
SAFE_TRANSIENT = {'low_memory', 'low_disk', 'editor_busy', 'lease_busy'}
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,79}\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')


class Refused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path, cap=2 * 1024**2):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > cap:
        raise Refused('Symlink or oversized JSON')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise Refused('Duplicate JSON key')
            out[key] = value
        return out
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused('Nonfinite JSON')))


def checked_file(row):
    if not isinstance(row, dict) or set(row) != {'path', 'sha256', 'bytes'}:
        raise Refused('Require exact path/SHA256/bytes witness')
    if not isinstance(row['path'], str) or not Path(row['path']).is_absolute():
        raise Refused('Require absolute local path')
    path = Path(row['path'])
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise Refused('Require regular nonsymlink local file')
    if (type(row['bytes']) is not int or not 0 < row['bytes'] <= 256 * 1024**2
            or not isinstance(row['sha256'], str) or not SHA.fullmatch(row['sha256'])
            or receipts.fingerprint(path) != {k: row[k] for k in ('sha256', 'bytes')}):
        raise Refused('File witness differs')
    return path


def utc_seconds(text):
    if not isinstance(text, str):
        raise Refused('Explicit UTC timestamp required')
    try:
        # Windows StartTime emits seven fractional digits; Python3.10 accepts
        # only microseconds. Normalize ONLY this numeric conversion; keep the
        # original full text unchanged for exact process/capture identity.
        numeric = re.sub(r'(\.\d{6})\d(?=(?:Z|\+00:00)$)', r'\1', text)
        stamp = datetime.fromisoformat(numeric.replace('Z', '+00:00'))
        if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError()
        return stamp.timestamp()
    except (ValueError, OverflowError):
        raise Refused('Malformed/nonUTC timestamp') from None


def manifest(path):
    value = load(path)
    if (not isinstance(value, dict) or set(value) != {'schema', 'owner', 'owned_destination',
            'engine_version', 'editor', 'adapter', 'dependencies', 'items'} or value['schema'] != VERSION):
        raise Refused('Unknown manifest/schema')
    if not NAME.fullmatch(value['owner'].replace('-', '_')):
        raise Refused('Explicit hub owner required')
    root = value['owned_destination']
    if (not isinstance(root, str) or not root.startswith('/Game/') or root.count('/') < 3
            or any(not NAME.fullmatch(p) for p in root.split('/')[2:])):
        raise Refused('Explicit narrow owned /Game destination required')
    if not isinstance(value['engine_version'], str) or not 1 <= len(value['engine_version']) <= 128:
        raise Refused('Exact engine version required')
    editor = value['editor']
    if (set(editor) != {'pid', 'start_utc', 'project', 'world'} or type(editor['pid']) is not int
            or editor['pid'] <= 0 or not Path(editor['project']).is_absolute()
            or not isinstance(editor['world'], str) or not editor['world'].startswith('/Game/')):
        raise Refused('Exact editor identity required')
    utc_seconds(editor['start_utc'])
    adapter = value['adapter']
    if not isinstance(adapter, dict) or set(adapter) != {'file', 'version'} or not adapter['version']:
        raise Refused('Pinned owner adapter required')
    if checked_file(adapter['file']).suffix != '.py':
        raise Refused('Owner adapter must be Python source')
    if not isinstance(value['dependencies'], list) or not 1 <= len(value['dependencies']) <= 32:
        raise Refused('Pin installed binary, helpers and policy dependencies')
    for dep in value['dependencies']:
        checked_file(dep)
    items = value['items']
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise Refused('Require 1..256 explicit items')
    ids, destinations, content = set(), set(), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {'id', 'sources', 'destination', 'policy'}:
            raise Refused('Unknown item contract')
        if not isinstance(item['id'], str) or not NAME.fullmatch(item['id']) or item['id'] in ids:
            raise Refused('Duplicate/invalid item identity')
        dest = item['destination']
        if (not isinstance(dest, str) or not dest.startswith(root + '/')
                or any(not NAME.fullmatch(p) for p in dest.split('/')[2:])
                or any(dest.lower() == p or dest.lower().startswith(p + '/')
                       or p.startswith(dest.lower() + '/') for p in destinations)):
            raise Refused('Duplicate/outside owned destination')
        if not isinstance(item['sources'], list) or not 1 <= len(item['sources']) <= 8:
            raise Refused('Require 1..8 explicit source files')
        names = set()
        for source in item['sources']:
            name = checked_file(source).name.lower()
            if name in names:
                raise Refused('Ambiguous snapshot filenames')
            names.add(name)
        checked_file(item['policy'])
        key = digest({'sources': [{k: s[k] for k in ('sha256', 'bytes')} for s in item['sources']],
                      'policy': {k: item['policy'][k] for k in ('sha256', 'bytes')}})
        if key in content:
            raise Refused('Duplicate source/policy item refused')
        ids.add(item['id']); destinations.add(dest.lower()); content.add(key)
    return value


@contextmanager
def exclusive(folder):
    """Kernel lock survives a stale file and releases on process exit/crash."""
    stream = (folder / 'runner.lock').open('a+b')
    stream.seek(0, 2)
    if not stream.tell():
        stream.write(b'0'); stream.flush()
    stream.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        stream.close()
        raise Refused('Another runner holds this state directory') from None
    try:
        yield
    finally:
        stream.close()  # OS releases lock; never unlink/reclaim another owner's lock.


def resources(folder):
    if os.name != 'nt':
        raise Refused('Live resource admission currently supports Windows only')
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
            (n, ctypes.c_uint64) for n in ('total_physical', 'physical', 'total_commit',
                                         'commit', 'total_virtual', 'virtual', 'extended')]
    state = Memory(); state.length = ctypes.sizeof(state)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        raise Refused('Memory observation unavailable')
    return {'physical': state.physical, 'commit': state.commit, 'disk': shutil.disk_usage(folder).free}


def validation(result, item, frozen, operation, now):
    """Actual adapter attestation + unchanged canonical consumer; never enum coercion."""
    required = {'schema', 'operation_id', 'item_key', 'destination', 'engine_version',
                'state', 'assets', 'outputs', 'validation', 'capture', 'preserved'}
    if not isinstance(result, dict) or set(result) != required:
        raise Refused('Incomplete native completion receipt')
    if (result['schema'] != VERSION or result['operation_id'] != operation
            or result['item_key'] != digest(item) or result['destination'] != item['destination']
            or result['engine_version'] != frozen['engine_version'] or result['state'] != 'complete'
            or result['preserved'] is not True):
        raise Refused('Native completion/preservation identity mismatch')
    capture = result['capture']
    if (not isinstance(capture, dict) or set(capture) != {'editor', 'operation_id', 'start_utc', 'end_utc', 'route'}
            or capture['editor'] != frozen['editor'] or capture['operation_id'] != operation
            or not isinstance(capture['route'], str) or not capture['route']):
        raise Refused('Missing actual native capture identity')
    start, end = utc_seconds(capture['start_utc']), utc_seconds(capture['end_utc'])
    if not start <= end <= now + 5 or not 0 <= now - end <= 300:
        raise Refused('Stale/future/inverted native evidence; reconcile, never reimport')
    assets = result['assets']
    if (not isinstance(assets, list) or not 1 <= len(assets) <= 16 or len(set(assets)) != len(assets)
            or any(not isinstance(p, str) or not p.startswith(item['destination'] + '/')
                   or not re.fullmatch(r'/Game/(?:[A-Za-z][A-Za-z0-9_]*/)*[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*', p) for p in assets)):
        raise Refused('Exact owned native asset identities required')
    outputs = result['outputs']
    if not isinstance(outputs, dict) or set(outputs) != set(assets):
        raise Refused('Exact saved asset hashes required')
    content = Path(frozen['editor']['project']).parent / 'Content'
    for asset, row in outputs.items():
        path = checked_file(row)
        expected = content / (asset.split('.')[0][len('/Game/'):] + '.uasset')
        if path.resolve() != expected.resolve():
            raise Refused('Saved file is not the exact owned asset package')
    envelope = result['validation']
    if (not isinstance(envelope, dict) or envelope.get('status') != 'Valid'
            or envelope.get('accepted') is not True or envelope.get('native_invoked') is not True
            or envelope.get('cancellation_observed') is not False
            or type(envelope.get('native_return')) is not int or envelope['native_return'] != 0
            or not isinstance(envelope.get('snapshot_json'), str) or not envelope['snapshot_json']):
        raise Refused('Validation is not actual complete Valid; quarantine with exact original status')
    parsed = consumer.consume(envelope['snapshot_json'], consumer.OutputCaps(
        max_bytes=256 * 1024, max_requested_assets=16, max_details=16,
        max_messages_per_list=32, max_string_chars=2048, max_total_messages=128))
    snap = parsed.snapshot
    if (not parsed.accepted or list(snap.requested_assets) != assets
            or snap.provenance.fresh_out_results != 'attested' or snap.provenance.native_invocation != 'attested'
            or snap.settings.validation_usecase != 'EDataValidationUsecase::Script' or snap.results.counts['NumExternalObjects'] != 0
            or any(detail.external_objects or any(m.severity != 'Info' for m in detail.validation_messages)
                   for detail in snap.results.details)):
        raise Refused('Canonical validation/request/policy attestation refused')
    captured = utc_seconds(snap.provenance.captured_at_utc)
    if not start <= captured <= end:
        raise Refused('Canonical native timestamp outside actual capture')
    return result


class Runner:
    def __init__(self, folder, backend, sample=resources, clock=time.time):
        self.folder, self.backend, self.sample, self.clock = Path(folder), backend, sample, clock
        self.frozen = manifest(self.folder / 'manifest.json')
        if self.folder.resolve().drive.lower() != Path(self.frozen['editor']['project']).drive.lower():
            raise Refused('State and Unreal output must share the observed disk volume')
        self.meta = load(self.folder / 'queue.json')
        if self.meta != {'schema': VERSION, 'manifest_sha256': digest(self.frozen),
                         'runner_sha256': receipts.fingerprint(__file__)['sha256']}:
            raise Refused('Queue/runner changed; create reviewed new state, never resume differently')

    def write(self, path, value):
        receipts.write_receipt(path, value)

    def record(self, item, state, **fields):
        path = self.folder / 'items' / (item['id'] + '.json')
        value = {'schema': VERSION, 'item_key': digest(item), 'state': state,
                 'updated_utc': receipts.utc_now(), **fields}
        value['checkpoint_sha256'] = digest(value)
        self.write(path, value)
        with (self.folder / 'events.jsonl').open('ab') as log:
            log.write(canonical({'utc': value['updated_utc'], 'item': item['id'], 'state': state,
                                 'operation_id': fields.get('operation_id'),
                                 'attempts': fields.get('attempts'), 'reason': fields.get('reason')}) + b'\n')
            log.flush(); os.fsync(log.fileno())
        return value

    def finish(self, item, operation, result, attempts):
        # Capture is evaluated before committing DONE. Any refusal retains the raw
        # receipt in quarantine; no fallback, deletion, save or import replay.
        try:
            validation(result, item, self.frozen, operation, self.clock())
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return self.record(item, 'QUARANTINED', operation_id=operation, attempts=attempts,
                               reason=str(exc), result=result)
        return self.record(item, 'DONE', operation_id=operation, attempts=attempts, result=result)

    def run(self, maximum=1):
        if type(maximum) is not int or not 1 <= maximum <= MAX_ITEMS:
            raise Refused('Invalid bounded item count')
        handled = 0
        with exclusive(self.folder):
            for item in self.frozen['items']:
                if handled >= maximum or (self.folder / 'STOP').exists():
                    break
                # Recheck all pins immediately before every item/adapter call.
                if manifest(self.folder / 'manifest.json') != self.frozen:
                    raise Refused('Frozen manifest changed')
                if receipts.fingerprint(__file__)['sha256'] != self.meta['runner_sha256']:
                    raise Refused('Runner source changed during execution')
                path = self.folder / 'items' / (item['id'] + '.json')
                prior = load(path) if path.exists() else {}
                if prior and (prior.get('schema') != VERSION or prior.get('item_key') != digest(item)
                        or prior.get('checkpoint_sha256') != digest({k:v for k,v in prior.items() if k != 'checkpoint_sha256'})):
                    raise Refused('Mismatched/corrupt item checkpoint')
                state, attempts = prior.get('state'), prior.get('attempts', 0)
                if state == 'QUARANTINED':
                    continue
                if state not in (None, 'WAITING', 'DONE', 'INFLIGHT', 'UNCERTAIN'):
                    raise Refused('Unknown checkpoint; manual reconciliation required')
                if state in (None, 'WAITING') and attempts >= MAX_ATTEMPTS:
                    self.record(item, 'QUARANTINED', attempts=attempts, reason='Bounded predispatch retries exhausted')
                    continue
                if prior.get('not_before', 0) > self.clock():
                    break
                sample = self.sample(self.folder)
                code = ('low_memory' if sample['physical'] < MIN_PHYSICAL or sample['commit'] < MIN_COMMIT
                        else 'low_disk' if sample['disk'] < MIN_DISK else None)
                if code:
                    if state in ('DONE', 'INFLIGHT', 'UNCERTAIN'):
                        self.write(self.folder / 'hold.json', {'reason': code, 'resources': sample,
                                   'item': item['id'], 'state_preserved': state})
                    else:
                        self.record(item, 'WAITING', attempts=attempts + 1, reason=code,
                                    resources=sample, not_before=self.clock() + 60)
                    break
                phase = 'verify' if state == 'DONE' else 'reconcile' if state in ('INFLIGHT', 'UNCERTAIN') else 'execute'
                if state == 'WAITING' and prior.get('not_before', 0) > self.clock():
                    break
                admission = self.backend.admit(item, phase)
                if (isinstance(admission, dict) and admission.get('state') == 'retry'
                        and admission.get('code') in SAFE_TRANSIENT and admission.get('native_dispatched') is False):
                    if phase == 'execute':
                        self.record(item, 'WAITING', attempts=attempts + 1, reason=admission['code'],
                                    not_before=self.clock() + 60, admission=admission)
                    else:
                        self.write(self.folder / 'hold.json', {'reason': admission['code'], 'item': item['id'], 'state_preserved': state})
                    break
                if (not isinstance(admission, dict) or admission.get('state') != 'ready'
                        or admission.get('editor') != self.frozen['editor']
                        or admission.get('engine_version') != self.frozen['engine_version']
                        or admission.get('holder') != self.frozen['owner']
                        or any(admission.get(k) is not True for k in ('exclusive_writer', 'idle', 'preserved', 'policy_verified'))
                        or phase == 'execute' and admission.get('destination_vacant') is not True):
                    if phase == 'execute':
                        self.record(item, 'QUARANTINED', attempts=attempts, reason='Native ownership/policy admission refused', admission=admission)
                    else:
                        self.write(self.folder / 'hold.json', {'reason': 'Native ownership/policy admission refused', 'item': item['id'], 'state_preserved': state, 'admission': admission})
                    break
                if (self.folder / 'hold.json').exists():
                    (self.folder / 'hold.json').unlink()
                if state == 'DONE':
                    # Immutable saved files and adapter's current guard/readback
                    # are both required; an old DONE string never authorizes a skip.
                    try:
                        for row in prior['result']['outputs'].values(): checked_file(row)
                        if self.backend.verify_saved(item, prior['result']) is not True:
                            raise Refused('Saved native readback differs')
                    except Exception as exc:
                        self.record(item, 'QUARANTINED', attempts=attempts, result=prior.get('result'), reason=str(exc))
                        break
                    continue
                if state in ('INFLIGHT', 'UNCERTAIN'):
                    # Read-only reconciliation ONLY; NEVER execute this item again.
                    recovered = self.backend.reconcile(item, prior['operation_id'])
                    if isinstance(recovered, dict) and recovered.get('state') == 'complete':
                        finished = self.finish(item, prior['operation_id'], recovered.get('result'), attempts)
                        handled += 1
                        if finished['state'] == 'QUARANTINED':
                            break
                        continue
                    break
                snapshots = []
                for row in item['sources']:
                    source = receipts.verified_snapshot(row['path'], {k: row[k] for k in ('sha256', 'bytes')},
                                                        self.folder / 'inputs' / item['id'])
                    snapshots.append({'path': source, **receipts.fingerprint(source)})
                if (self.folder / 'STOP').exists():
                    break
                operation = str(uuid.uuid4())
                self.record(item, 'INFLIGHT', operation_id=operation, attempts=attempts + 1,
                            snapshots=snapshots, native_receipt=str(self.folder / 'native' / (operation + '.json')))
                try:
                    result = self.backend.execute(item, operation, snapshots,
                            str(self.folder / 'native' / (operation + '.json')))
                except Exception as exc:
                    self.record(item, 'UNCERTAIN', operation_id=operation, attempts=attempts + 1,
                                reason=type(exc).__name__ + ': ' + str(exc), snapshots=snapshots)
                    break
                finished = self.finish(item, operation, result, attempts + 1)
                handled += 1
                if finished['state'] == 'QUARANTINED':
                    break
            return self.summary()

    def summary(self):
        states = {}
        for item in self.frozen['items']:
            path = self.folder / 'items' / (item['id'] + '.json')
            row = load(path) if path.exists() else {'state': 'PENDING'}
            states[item['id']] = {'state': row['state'], 'reason': row.get('reason')}
        value = {'schema': VERSION, 'utc': receipts.utc_now(), 'items': states,
                 'stopped': (self.folder / 'STOP').exists(), 'native_runtime_qualified': False,
                 'production_adoption': False,
                 'hold': load(self.folder / 'hold.json') if (self.folder / 'hold.json').exists() else None}
        self.write(self.folder / 'summary.json', value)
        return value


def prepare(source, folder):
    frozen = manifest(source)
    folder = Path(folder)
    if folder.exists():
        raise Refused('Existing state directory; resume, never overwrite')
    # The manifest is immutable configuration, not a folder to sweep for new work.
    folder.mkdir(parents=True)
    for name in ('items', 'inputs', 'native'): (folder / name).mkdir()
    receipts.write_receipt(folder / 'manifest.json', frozen)
    receipts.write_receipt(folder / 'queue.json', {'schema': VERSION,
        'manifest_sha256': digest(frozen), 'runner_sha256': receipts.fingerprint(__file__)['sha256']})
    return {'state': 'PREPARED', 'items': len(frozen['items']), 'native_operations': 0}


def backend(folder):
    frozen = manifest(Path(folder) / 'manifest.json')
    row = frozen['adapter'];path = checked_file(row['file'])
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != row['file']['sha256']:
        raise Refused('Adapter changed while loading')
    module = type(sys)('_frozen_owner_ingestion_adapter')
    module.__file__ = str(path)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    if module.VERSION != row['version']:
        raise Refused('Adapter ABI differs')
    return module.create(frozen, str(Path(folder).resolve()))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run', 'resume', 'stop', 'status'))
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--max-items', type=int, default=1)
    a = p.parse_args(argv)
    if a.action == 'prepare':
        if not a.manifest: p.error('--manifest required')
        result = prepare(a.manifest, a.state)
    elif a.action == 'stop':
        if not (a.state / 'queue.json').is_file(): raise Refused('Unknown state directory')
        (a.state / 'STOP').touch(exist_ok=True)
        result = {'state': 'STOP_REQUESTED', 'active_call_killed': False}
    elif a.action == 'status':
        result = load(a.state / 'summary.json') if (a.state / 'summary.json').exists() else load(a.state / 'queue.json')
    else:
        if a.action == 'resume' and (a.state / 'STOP').exists():
            raise Refused('Stop persists; remove only this owned STOP file to explicitly resume')
        result = Runner(a.state, backend(a.state)).run(a.max_items)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'state': 'HOLD', 'error': str(exc), 'retry_authorized': False}), file=sys.stderr)
        raise SystemExit(2)
