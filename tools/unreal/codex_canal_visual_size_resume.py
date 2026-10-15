"""Continue R1 after a proved IntPoint display-address comparison false hold.

Retain the original code/returns/PNG. Only numeric viewport size is compared.
No native phase or capture is replayed; the same bounded claim remains in force.
"""
import argparse
import copy
import re
from pathlib import Path

import codex_canal_visual_delivery as v

d = v.d
NEW_HELPER = Path(__file__).with_name('codex_canal_visual_native_size_r2.py')
CONTINUATION = v.F / 'viewport-size-value-continuation.json'
ORIGINAL_HOST = '7780f710fdd2e14899d2e611fb8b9cb3909c85d7119567815c8242bbd9db405c'
ORIGINAL_HELPER = '15b0a65a38409cc29cf765753776b10cc18486b0f0116a72e8720d64f1c0f464'


def numeric_settings(value):
    result = copy.deepcopy(value); viewport = result.get('viewport', {})
    viewport.pop('camera', None)
    size = viewport.get('size', {})
    if size.get('available') is True and isinstance(size.get('value'), str):
        match = re.fullmatch(r"<Struct 'IntPoint' \(0x[0-9A-Fa-f]+\) \{x: (\d+), y: (\d+)\}>", size['value'])
        if not match: raise RuntimeError('unexpected original viewport-size display shape')
        size['value'] = dict(zip(('x', 'y'), map(int, match.groups())))
    return result


def prepare():
    """Qualify the existing image from its two retained, identical-value reads."""
    old = d.load(v.F / 'prepared.json')
    for pin in old['sources'].values(): d._check(pin)
    if old['sources']['host']['sha256'] != ORIGINAL_HOST or old['sources']['visual_helper']['sha256'] != ORIGINAL_HELPER:
        raise RuntimeError('exact known R1 source required')
    if (v.F / 'candidate-dispatch.json').exists() or (v.F / 'native-candidate.json').exists():
        raise RuntimeError('continuation admits only the known zero-candidate hold')
    before = d.load(v.F / 'before-forward-return.json')
    after = d.load(v.F / 'before-forward-capture-witness-return.json')
    if before['stage'] != 'winter4_visual_camera_only' or after['stage'] != 'winter4_visual_capture_postreadback':
        raise RuntimeError('exact completed camera/capture witness stages required')
    if before['scene'] != after['scene'] or numeric_settings(before['renderer']) != numeric_settings(after['renderer']):
        raise RuntimeError('known display-pointer-only false hold not established')
    if numeric_settings(before['renderer'])['viewport']['size'] != {'available': True, 'value': {'x': 2033, 'y': 1216}}:
        raise RuntimeError('exact actual two size values required')
    old_helper = Path(old['sources']['visual_helper']['path']).read_text()
    old_line = "viewport['size'] = _visual_read(lambda:str(e.get_level_viewport_size()))"
    new_line = "viewport['size'] = _visual_read(lambda:{axis:int(getattr(e.get_level_viewport_size(),axis)) for axis in ('x','y')})"
    if old_helper.count(old_line) != 1 or NEW_HELPER.read_text() != old_helper.replace(old_line, new_line):
        raise RuntimeError('new helper must differ only in numeric size getter')
    image = v.F / 'before-forward.png'
    with image.open('rb') as f:
        if f.read(8) != b'\x89PNG\r\n\x1a\n': raise RuntimeError('existing actual PNG required')
    value = {'utc': d._utc(), 'stage': 'known_display_address_only_false_hold_continuation',
        'source': d.pin(__file__), 'new_helper': d.pin(NEW_HELPER), 'original_prepared': d.pin(v.F / 'prepared.json'),
        'before': d.pin(v.F / 'before-forward-return.json'), 'after': d.pin(v.F / 'before-forward-capture-witness-return.json'),
        'existing_image': d.pin(image), 'same_claim': d.load(v.F / 'compute-claim.json'),
        'native_calls_in_preparation': 0, 'mutation_replays': 0,
        'normalization': 'Only IntPoint display address excluded; both numeric x/y remain exact. All other renderer fields and complete scene dictionaries are identical.'}
    d.write_new(CONTINUATION, value)
    v.p.exclusive_copy(__file__, v.F / 'viewport-size-continuation-source-used.py')
    v.p.exclusive_copy(NEW_HELPER, v.F / 'visual-size-helper-r2-source-used.py')
    d.write_new(v.F / 'before-forward-image.json', {'utc': d._utc(), 'image': d.pin(image),
        'scene_camera': before['scene']['camera'], 'renderer': before['renderer'],
        'stage': 'actual_editor_viewport_capture', 'sort_state': {'Water': 0, 'FoamCore': 0},
        'post_capture': value['after'], 'not_gameplay': True, 'qualification_continuation': d.pin(CONTINUATION)})
    print('existing forward baseline qualified from retained reads; no camera/capture replay')


original_custody = v.custody


def custody():
    claim = original_custody(); continuation = d.load(CONTINUATION)
    for key in ('source', 'new_helper', 'original_prepared', 'before', 'after', 'existing_image'):
        d._check(continuation[key])
    if continuation['same_claim'] != d.load(v.F / 'compute-claim.json'):
        raise RuntimeError('continuation cannot replace or extend the original bounded claim')
    return claim


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('phase', choices=('prepare', 'camera', 'candidate', 'finish', 'readback', 'reconcile', 'abort', 'release'))
    a.add_argument('--view', choices=('forward', 'reverse')); a.add_argument('--state', choices=('before', 'after'))
    a.add_argument('--decision', choices=('keep', 'revert')); args = a.parse_args()
    if args.phase == 'prepare': prepare()
    else:
        v.custody = custody; v.HELPER = NEW_HELPER; v.render_settings = numeric_settings
        if args.phase == 'camera': v.camera(args.view, args.state)
        elif args.phase == 'finish': v.finish(args.decision)
        else: getattr(v, args.phase)()
