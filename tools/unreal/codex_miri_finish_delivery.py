# SPDX-License-Identifier: MIT
"""Finish the exact known unsaved Miri import; this entry point never imports."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import codex_miri_delivery as miri

d = miri.catalogue
SOURCE = miri.SOURCE.with_name('daedalus_codex_miri_finish.py')
LABEL = 'Codex Miri v2 known unsaved skeletal completion'


def cfg_and_code(value, deadline):
    source_fp = d.fingerprint(SOURCE)
    cfg = miri.config(value, deadline)
    cfg.update(original_source=str(miri.SOURCE), original_fingerprint=value['native_module_fingerprint'],
               known_journal=str(miri.FOLDER / 'native.json'),
               known_journal_fingerprint=d.fingerprint(miri.FOLDER / 'native.json'),
               known_readback=str(miri.FOLDER / 'known-import-readback.json'),
               known_readback_fingerprint=d.fingerprint(miri.FOLDER / 'known-import-readback.json'),
               journal=str(miri.FOLDER / 'finish-native.json'))
    code = ('from pathlib import Path\nimport hashlib\nsource=' + repr(str(SOURCE)) + '\n'
            'raw=Path(source).read_bytes()\nif hashlib.sha256(raw).hexdigest()!=' + repr(source_fp['sha256']) +
            ":raise RuntimeError('known completion module changed')\nscope={'__name__':'_codex_miri_known_completion'}\n"
            'exec(compile(raw,source,\'exec\'),scope)\n')
    return cfg, code, source_fp


def finish():
    value = miri.prepared(); miri.protection(); d.editor(); lease = d._lease()
    known = d.load(miri.FOLDER / 'native.json')
    inspected = d.load(miri.FOLDER / 'known-import-readback.json')
    if (known.get('stage') != 'halted_preserve_partial' or known.get('outputs') != []
            or known.get('save_return') is not None or len(known.get('imported_object_paths', [])) != 17
            or inspected.get('save_called') is not False or inspected.get('import_repeated') is not False
            or inspected['inspection'].get('issues') != []):
        raise RuntimeError('exact returned unsaved import and passing read-only reconciliation required')
    for path in known['imported_object_paths']:
        if d._asset_file(path).exists():
            raise RuntimeError('owned output already on disk; inspect first-save state before dispatch')
    dispatch = miri.FOLDER / 'finish-dispatch.json'
    if dispatch.exists():
        raise RuntimeError('known completion dispatch exists; inspect before any replay')
    cfg, code, source_fp = cfg_and_code(value, min(time.time() + 600, lease['at'] + lease['ttl'] - 60))
    code += '\ndef steps():\n    return (yield from scope[\'steps\'](' + repr(cfg) + '))\n'
    d.write_new(dispatch, {'stage': 'known_completion_dispatch_pending', 'source_module': str(SOURCE),
        'source_module_fingerprint': source_fp, 'known_journal_fingerprint': cfg['known_journal_fingerprint'],
        'known_readback_fingerprint': cfg['known_readback_fingerprint'],
        'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'map_before': d.fingerprint(d.MAP_FILE)})
    reply = d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code, label=LABEL, budget_ms=1, timeout=180, side='Unreal')
    d.write_new(miri.FOLDER / 'finish-reply.json', reply)
    state = d.load(dispatch)
    state.update(stage='known_completion_returned_inspect_before_replay', reply_fingerprint=d.fingerprint(miri.FOLDER / 'finish-reply.json'))
    dispatch.write_text(json.dumps(state, indent=2) + '\n')
    if reply.get('error'):
        raise RuntimeError('inspect known completion journal; no blind save/import replay')
    native = d.load(cfg['journal'])
    if native.get('stage') != 'miri_assets_saved_world_held' or len(native.get('outputs', [])) != 17:
        raise RuntimeError('17 first saves not confirmed')
    outputs = {}
    for row in native['outputs']:
        if row.get('save_return') is not True:
            raise RuntimeError('first save not confirmed')
        outputs[row['path']] = {'class': row['class'], **d.fingerprint(d._asset_file(row['path']))}
    state.update(stage='miri_assets_saved_world_held', outputs=outputs)
    dispatch.write_text(json.dumps(state, indent=2) + '\n')
    miri.protection(); d.editor()
    if d.fingerprint(d.MAP_FILE) != state['map_before']:
        raise RuntimeError('saved world changed')
    print(json.dumps({'stage': state['stage'], 'outputs': outputs, 'import_repeated': False}, indent=2))


def readback():
    value = miri.prepared()
    state = d.load(miri.FOLDER / 'finish-dispatch.json')
    if d.fingerprint(SOURCE) != state['source_module_fingerprint']:
        raise RuntimeError('known completion source differs')
    cfg, code, _ = cfg_and_code(value, time.time() + 180)
    miri.readback('finish-dispatch.json', code, cfg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('finish', 'readback'))
    globals()[parser.parse_args().stage]()
