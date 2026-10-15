"""Release the known completed turn using only files and the coordination hub.

The original release stopped at a resource check before its hub POST. This
does not dispatch native work, change floors, renew custody or replay a save.
"""
import json

import codex_canal_visual_delivery as v

d = v.d


def main():
    f = v.F
    d._lease()
    completed = d.load(f / 'completion.json')
    readback = d.load(f / 'readback-return.json')
    saved = d.load(f / 'native-finish.json')
    if (completed.get('stage') != 'winter4_local_visual_comparison_complete'
            or readback.get('stage') != 'winter4_local_visual_saved_readback'
            or readback['dirty'] != {'maps': [], 'content': []}
            or saved.get('save_return') is not True or completed.get('save_return') is not True):
        raise RuntimeError('known clean completed native readback and true save required')
    if (f / 'compute-release.json').exists() or (f / 'compute-release-file-only.json').exists():
        raise RuntimeError('release may already exist; inspect rather than replay')
    for pin in d.load(f / 'prepared.json')['sources'].values(): d._check(pin)
    continuation = d.load(f / 'viewport-size-value-continuation.json')
    d._check(continuation['source']); d._check(continuation['new_helper'])
    d._check(completed['baseline']); d._check(completed['readback'])
    d.protect(d.load(completed['baseline']['path']))
    claim = d.load(f / 'compute-claim.json')['claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute', {}), claim):
        raise RuntimeError('exact completed compute claim must still be held')
    d.write_new(f / 'compute-file-only-release-intent.json', {'utc': d._utc(),
        'source': d.pin(__file__), 'claim': claim, 'readback': completed['readback'],
        'reason': 'Original release failed at memory floor before hub POST; file/hub-only completion needs no native allocation.',
        'native_calls': 0, 'native_operations_after_saved_readback': 0, 'resource_floor_changes': 0})
    result = d.post('/unlock', {'me': d.OWNER, 'name': 'compute'})
    after = d.locks()
    receipt = {'utc': d._utc(), 'stage': 'completed_compute_released_file_hub_only',
        'result': result, 'locks_after': after, 'native_calls': 0,
        'last_native': completed['readback'], 'source': d.pin(__file__)}
    d.write_new(f / 'compute-release-file-only.json', receipt)
    if result.get('ok') is not True or d.same_compute_lease(after.get('compute', {}), claim):
        raise RuntimeError('completed compute release unconfirmed; do not repeat uncertain hub request')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
