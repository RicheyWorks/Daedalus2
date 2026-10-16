"""Deliver only the released TidePen Residents through the existing FBX pipeline.

The closed native adapter corrects metre/actor1 metadata; the historical plant
receiver, material, geometry/palette guards and journals remain unchanged.
"""
import argparse
import copy
import json
from pathlib import Path
import time
from types import SimpleNamespace

import codex_qualified_static_delivery as d

REPO = Path(__file__).resolve().parents[2]
TASK = REPO.parent
F = TASK / 'native-ingestion/TidePenResidentsR1'
DELIVERY = F / 'DeliveryR1'
BASELINE = TASK / 'native-ingestion/Winter4CanalStream1CoreR2/PlacementR1/VisualPolishR1/saved-production-baseline.json'
BASE_RECEIVER = d.NATIVE
NATIVE = BASE_RECEIVER.with_name('daedalus_codex_tidepen_residents.py')
QUALIFICATION = F / 'qualification.json'
QUALIFICATION_SHA = '452e0997365ec45d4e0c8a7214d62b76d18f81f5eee27b52aabca395e9a644b9'
AUDIT_SHA = 'fb3ddcb29b1f9517a70c2dde718c61b211294934756839be811b1321984a25b6'
BASELINE_SHA = 'abe95ef34ccb75b2a2e757d29923558fb0b42655307aa592de9b4315c6e08b2e'
UNIT = 'source_metres_unit100_build1_actor1_v1'


def prepare():
    """Bind the existing source qualification to the exact metre-aware adapter."""
    if DELIVERY.exists() or (F / 'receiver-admission.json').exists():
        raise RuntimeError('retained preparation; do not overwrite or replay')
    original = d.load(QUALIFICATION)
    if (d.pin(QUALIFICATION)['sha256'] != QUALIFICATION_SHA
            or d.pin(F / 'source-audit.json')['sha256'] != AUDIT_SHA
            or d.pin(BASELINE)['sha256'] != BASELINE_SHA):
        raise RuntimeError('exact reviewed source and saved baseline required')
    if (original['stage'] != 'qualified_static_candidates_source_only'
            or original.get('native_dispatch_eligible') is not False
            or original.get('source_views_personally_inspected_by_operator') is not True
            or len(original['items']) != 1
            or original['items'][0]['required_future_actor_scale'] != [1., 1., 1.]):
        raise RuntimeError('exact source-only metre-unit qualification required')
    for pin in original['source_pins']: d._check(pin)
    d.protect(d.load(BASELINE))
    log = Path('C:/Users/730ri/projects/bot-team/link/log.jsonl')
    release = next((json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()
                    if json.loads(line).get('id') == 32582), None)
    if (release is None or release.get('from') != 'unreal-team'
            or release.get('to') != 'codex-play-guard'
            or release.get('reply_to') != 32563
            or 'Asset-only import/save of small static roles into YOUR OWN CodexContest namespace is released' not in release['body']['text']):
        raise RuntimeError('exact producer source release evidence required')
    d.write_new(F / 'producer-release-32582.json', release)
    value = copy.deepcopy(original)
    value.update(utc=d._utc(), stage='qualified_static_candidates_source_only', native_dispatch_eligible=True,
        unit_metadata_blocker_resolved=True,
        prior_native_intake_profile_blocker=original['native_intake_profile_blocker'],
        native_intake_profile_blocker=None,
        receiver_profile={'native':d.pin(NATIVE),'base_receiver':d.pin(BASE_RECEIVER),
            'unit_contract':UNIT,'required_future_actor_scale':[1.,1.,1.],
            'resolution':'Closed private adapter preserves every original import/guard/palette/bounds check; corrects only Residents metre/actor1 reporting and metadata before any journal/save.',
            'historical_unit_profile_edited':False},
        original_source_qualification=d.pin(QUALIFICATION), producer_release=d.pin(F / 'producer-release-32582.json'))
    value['source_pins'] += [d.pin(QUALIFICATION), d.pin(NATIVE), d.pin(BASE_RECEIVER),
                             d.pin(__file__), d.pin(F / 'producer-release-32582.json')]
    admission = F / 'receiver-admission.json'; d.write_new(admission, value)
    d.prepare(SimpleNamespace(folder=DELIVERY, qualification=admission, baseline=BASELINE))
    print(json.dumps({'stage':'released_residents_actor1_delivery_prepared',
        'source':d.pin(QUALIFICATION),'admission':d.pin(admission),'native':d.pin(NATIVE),
        'unit_contract':UNIT,'native_calls':0}))


original_config = d.config


def config(value, args, lease):
    cfg = original_config(value, args, lease)
    base_pin = next(pin for pin in value['source_pins'] if Path(pin['path']) == BASE_RECEIVER)
    qualification_pin = next(pin for pin in value['source_pins'] if Path(pin['path']) == QUALIFICATION)
    d._check(base_pin); d._check(qualification_pin)
    cfg.update(base_receiver_source=base_pin['path'], base_receiver_source_fingerprint=d.fp(base_pin),
               qualification_source=str(QUALIFICATION), qualification_source_fingerprint=d.fp(qualification_pin))
    return cfg


def read_native(value, cfg, operation):
    """Keep the complete response envelope before using the existing decoder."""
    if operation not in ('preflight', 'readback'): raise ValueError('read-only native operation required')
    code = d.module_code(value) + '\ndef steps():\n    if False: yield\n    return scope[' + repr(operation) + '](' + repr(cfg) + ')\n'
    raw = d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
                      budget_ms=1, timeout=90, side='Unreal')
    evidence = DELIVERY / (operation + '-raw-envelope-' + str(time.time_ns()) + '.json')
    d.write_new(evidence, raw)
    result = d.wire.obj(raw, side='Unreal', what='TidePen Residents ' + operation)
    if not isinstance(result, dict):
        raise RuntimeError('native read returned no complete object; retain raw envelope and reconcile')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare','run','readback','finalize'))
    args = parser.parse_args()
    d.NATIVE = NATIVE; d.config = config; d.read_native = read_native
    if args.phase == 'prepare': prepare()
    else:
        getattr(d, args.phase)(SimpleNamespace(folder=DELIVERY, readback_names=None,
            minimum_free_physical_mib=1024, minimum_free_commit_mib=1536))
