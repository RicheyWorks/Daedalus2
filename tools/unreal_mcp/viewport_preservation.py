"""Remaining-only viewport restoration; no map/content save or editor action."""
import hashlib
import json
import math
import time
from pathlib import Path


def _load(pin):
    raw = Path(pin['path']).read_bytes()
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise RuntimeError('retained camera proof/source pin differs')
    return raw


def run(cfg):
    import unreal
    if time.time() > cfg['deadline_epoch']:
        raise RuntimeError('new camera restoration deadline elapsed')
    journal = Path(cfg['journal'])
    if journal.exists():
        raise RuntimeError('retained camera intent/outcome; reconcile without replay')
    original = json.loads(_load(cfg['original']).decode('utf-8'))
    held = json.loads(_load(cfg['held']).decode('utf-8'))
    scope = {'__name__': '_codex_camera_preservation_guard', '__file__': cfg['guard']['path']}
    exec(compile(_load(cfg['guard']), cfg['guard']['path'], 'exec'), scope)
    before = scope['run']({**cfg['guard_cfg'], 'journal': cfg['before_journal'],
                           'deadline_epoch': cfg['deadline_epoch']})
    if before['stage'] != 'CURRENT_MAIN_CLEAN_NO_PENDING_WORK' or before['scene'] != held['scene']:
        raise RuntimeError('camera-only held state changed; no setter')
    target = original['scene']['scene']['camera']
    values = [*target['location'].values(), *target['rotation'].values()]
    if len(values) != 6 or not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise RuntimeError('recorded target camera differs')
    report = {'stage': 'ONE_CAMERA_RESTORE_INTENT', 'known_terminal': False,
        'target': target, 'observed_before': before['scene']['scene']['camera'],
        'camera_calls': 0, 'save_calls': 0, 'actor_mutations': 0, 'replay_permitted': False}
    with journal.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    def keep():
        journal.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    location = unreal.Vector()
    rotation = unreal.Rotator()
    for name, value in target['location'].items():
        setattr(location, name, value)
    for name, value in target['rotation'].items():
        setattr(rotation, name, value)
    if time.time() > cfg['deadline_epoch']:
        raise RuntimeError('deadline reached before setter; intent retained')
    report['camera_calls'] = 1
    keep()
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(location, rotation)
    after = scope['run']({**cfg['guard_cfg'], 'journal': cfg['after_journal'],
                          'deadline_epoch': cfg['deadline_epoch']})
    actual = after.get('scene', {}).get('scene', {}).get('camera')
    report['observed_after'] = actual
    # Only float roundoff in the supported camera setter gets the established
    # tolerance. Actor records, complete world digest and selection stay exact.
    expected = json.loads(json.dumps(original['scene']))
    received = json.loads(json.dumps(after.get('scene')))
    expected['scene'].pop('camera')
    received['scene'].pop('camera')
    matches = (after['stage'] == 'CURRENT_MAIN_CLEAN_NO_PENDING_WORK' and expected == received
        and isinstance(actual, dict) and all(abs(actual[k][axis] - value) <= 1e-5
            for k, values in target.items() for axis, value in values.items()))
    report.update(stage='CAMERA_RESTORED_PRESERVATION_PASS' if matches else 'CAMERA_RESTORATION_HOLD',
                  known_terminal=True, other_scene_exact=expected == received,
                  camera_tolerance=1e-5, dirty_maps=after['dirty_maps'], dirty_content=after['dirty_content'])
    keep()
    return report
