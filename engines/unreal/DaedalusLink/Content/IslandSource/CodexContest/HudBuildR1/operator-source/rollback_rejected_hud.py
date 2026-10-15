"""Restore five known pre-HUD leaves after a rejected loaded HUD candidate.

Only the sole operator executes these phases. This script never launches or
kills an editor, starts PIE, saves a map, or modifies the original activation
journal. Main performs the separate normal visible reopen and records its PID.
"""
import argparse
import hashlib
import json
from pathlib import Path

import activate_hud_native as h

OUT = h.BASE / 'codex-hud-rejected-rollback.json'
ORIGINAL = h.BASE / 'codex-hud-normal-activation.json'
REJECTED_DLL = 'e2b00824589b97a2795abb686614b28868d38bcd77b7535de64ee3adf61e8680'
RESTORED_DLL = '80eca0a812b19e2e6a0d79d17b454eb9863bffbae72c36983206373f5d812e1d'


def retain(record):
    OUT.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def inputs():
    prepared = h.load(h.SHADOW / 'prepared.json')
    preflight = h.load(h.PREFLIGHT)
    h.check_preflight(prepared, preflight)
    original = h.load(ORIGINAL)
    rows = h.payloads(prepared)
    if (original.get('reopen_dispatched') is not True or original.get('forced_close') is not False
            or original.get('payloads') != rows or len(original.get('installations', [])) != 5
            or any(row.get('state') != 'installed_and_verified' for row in original['installations'])):
        raise RuntimeError('require exact previously installed/reopened five-leaf HUD journal')
    binaries = {Path(row['target']).suffix: row for row in rows if Path(row['target']).suffix in ('.dll', '.pdb')}
    if (set(binaries) != {'.dll', '.pdb'} or binaries['.dll']['expected']['sha256'] != REJECTED_DLL
            or binaries['.dll']['before']['sha256'] != RESTORED_DLL):
        raise RuntimeError('rejected/restored binary identity differs; preserve')
    packages = h.package_rows(preflight)
    return prepared, preflight, original, rows, packages


def preserve(prepared, preflight, rows, packages, restored=False):
    expected_source = dict(prepared['live_source_baseline'])
    if not restored:
        for row in rows:
            target = Path(row['target'])
            if target.suffix not in ('.dll', '.pdb'):
                expected_source[str(target.relative_to(h.LIVE)).replace('\\', '/')] = row['expected']
    if len(expected_source) != 140 or h.source_snapshot() != expected_source:
        raise RuntimeError('current full 140-file source identity differs; preserve')
    for row in rows:
        expected = row['before'] if restored else row['expected']
        if h.fp(row['target']) != expected or h.fp(row['backup']) != row['before']:
            raise RuntimeError('current candidate/restored bytes or exact backup differ: ' + row['target'])
        if h.fp(row['source']) != row['expected']:
            raise RuntimeError('retained rejected source/binary candidate changed')
    if h.fp(h.MODULE) != h.fingerprint(prepared['current_module_receipt']):
        raise RuntimeError('canonical modules receipt changed; never overwrite')
    for rel, expected in prepared['runtime_catalogs'].items():
        if h.fp(h.LIVE / rel) != h.fingerprint(expected):
            raise RuntimeError('runtime catalog drift: ' + rel)
    h.check_packages(packages)
    h.check_map_backup(preflight)


def scene(expected):
    actual, compare = h.native_snapshot()
    comparison = compare(expected['actors'], actual['actors'])
    if not comparison['equivalent']:
        raise RuntimeError('production actor snapshots drifted: ' + repr(comparison['issues']))
    h.same_camera(actual, expected)
    return actual


def single_editor(pid):
    observed = h.processes()
    if len(observed) != 1 or observed[0]['ProcessId'] != pid:
        raise RuntimeError('single current editor identity differs: ' + repr(observed))
    if 'DaedalusRealm.uproject' not in observed[0].get('CommandLine', ''):
        raise RuntimeError('current editor project identity unsupported')
    return {'utc': h.now(), 'processes': observed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'request-close', 'install'))
    parser.add_argument('--pid', type=int, required=True)
    args = parser.parse_args()
    prepared, preflight, original, rows, packages = inputs()
    preserve(prepared, preflight, rows, packages)
    if args.phase == 'prepare':
        if OUT.exists():
            raise RuntimeError('exclusive rejected-HUD rollback journal exists; inspect, never replay')
        if original.get('new_editor_pid') != args.pid:
            raise RuntimeError('rejected editor PID differs from activation witness')
        process = single_editor(args.pid)
        actual = scene(preflight['scene'])
        record = {'schema': 'daedalus.codex-rejected-hud-controlled-rollback.v1',
                  'utc': h.now(), 'stage': 'prepared_clean_production_boundary_normal_close_pending',
                  'reason': 'Loaded HUD candidate rejected by bounded native acceptance; restore known prior five leaves.',
                  'rejected_editor_pid': args.pid, 'process_before': process, 'native_before': actual,
                  'original_activation': {'path': str(ORIGINAL), **h.fp(ORIGINAL)},
                  'preflight': {'path': str(h.PREFLIGHT), **h.fp(h.PREFLIGHT)},
                  'payloads': rows, 'tracked_packages': packages, 'map_before': h.fp(h.MAP),
                  'map_backup': preflight['map_backup'], 'unchanged_modules': h.fp(h.MODULE),
                  'rejected_dll_sha256': REJECTED_DLL, 'restored_dll_sha256': RESTORED_DLL,
                  'normal_close_requested': False, 'forced_close': False, 'settings_changed': False,
                  'reopen_dispatched': False, 'restorations': [], 'issues': []}
        with OUT.open('x', encoding='utf-8') as output:
            json.dump(record, output, indent=2, allow_nan=False)
            output.write('\n')
    else:
        record = h.load(OUT)
        if (record['rejected_editor_pid'] != args.pid or record['payloads'] != rows
                or record['tracked_packages'] != packages
                or h.fp(h.PREFLIGHT) != h.fingerprint(record['preflight'])
                or h.fp(ORIGINAL) != h.fingerprint(record['original_activation'])):
            raise RuntimeError('rollback inputs/history changed; preserve and reconcile')
        if args.phase == 'request-close':
            if record['stage'] != 'prepared_clean_production_boundary_normal_close_pending' or record['normal_close_requested']:
                raise RuntimeError('normal close already dispatched or wrong phase; inspect')
            single_editor(args.pid)
            scene(record['native_before'])
            code = '''# Codex rejected HUD NORMAL mainframe close, never forced
import unreal,sys
b=sys.modules['claude_unreal_bridge']
others=[req.get('type') for gen,req,box in b._running if req.get('type')!='execute_python' or not (req.get('params') or {}).get('code','').startswith('# Codex rejected HUD NORMAL mainframe close')]
if others or b._jobs.qsize() or b._remote_lock.locked():raise RuntimeError('new conflicting native work')
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE remains active')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('unsaved user work; preserve')
unreal.SystemLibrary.execute_console_command(None,'CLOSE_SLATE_MAINFRAME')
result={'normal_close_requested':True,'forced':False}
'''
            record.update(stage='normal_close_dispatched_outcome_requires_process_readback',
                          normal_close_requested=True, normal_close_utc=h.now(),
                          close_code_sha256=hashlib.sha256(code.encode()).hexdigest())
            retain(record)
            try:
                record['normal_close_reply'] = h.wire.call(h.wire.UNREAL, 'execute_python', code=code,
                                                           unattended=False, timeout=15, side='Unreal')
            except Exception as exc:
                record['normal_close_transport_observation'] = str(exc)
            retain(record)
        else:
            if record['stage'] != 'normal_close_dispatched_outcome_requires_process_readback' or record['restorations']:
                raise RuntimeError('restore install cannot be replayed; inspect partial outcome')
            record['zero_editor_witness'] = h.require_zero_editors()
            preserve(prepared, preflight, rows, packages)
            record['stage'] = 'normal_editor_exited_five_original_leaves_restoring'
            retain(record)
            # Redirect the existing atomic-copy helper solely to this new journal.
            # The retained original activation journal is never its write target.
            h.OUT = OUT
            for row in rows:
                event = {'target': row['target'], 'source': row['backup'], 'expected': row['before'],
                         'rejected_before': row['expected'], 'state': 'stage_pending'}
                record['restorations'].append(event)
                retain(record)
                h.atomic_copy(row['backup'], row['target'], row['before'], event, record,
                              '.codex-rejected-hud-restore-staged')
            preserve(prepared, preflight, rows, packages, restored=True)
            if h.fp(ORIGINAL) != h.fingerprint(record['original_activation']):
                raise RuntimeError('original activation journal changed during rollback; preserve')
            record.update(stage='five_original_leaves_restored_normal_visible_reopen_pending',
                          restored_utc=h.now(), source_files_restored=140,
                          tracked_package_files_preserved=120, saved_map_unchanged=True,
                          module_receipt_unchanged=True)
            retain(record)
    print(json.dumps({'stage': record['stage'], 'journal': str(OUT), **h.fp(OUT),
                      'restored_leaves': len(record['restorations']), 'tracked_packages': 120}, indent=2))


if __name__ == '__main__':
    main()
