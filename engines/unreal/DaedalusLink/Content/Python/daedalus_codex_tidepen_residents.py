# SPDX-License-Identifier: MIT
"""Closed metre/actor1 metadata adapter for the qualified TidePen Residents FBX.

Import, guards, deadlines, queue yields, palette, bounds, material binding and
save behavior come from the unchanged pinned qualified-static/catalogue sources.
Only unit reporting and the same nine metadata values receive the metre policy.
No native action occurs until an entry point is called with its pinned config.
"""
import hashlib
import json
import math
from pathlib import Path

LABEL = 'Codex TidePen Residents metre actor1 asset-only import-save'
UNIT_CONTRACT = 'source_metres_unit100_build1_actor1_v1'
BASE_FINGERPRINT = {
    'bytes': 28818,
    'sha256': 'ff67f266fa45b276d287d69d5fa750b445353960d7213234dede15bc1f135df0',
}
QUALIFICATION_FINGERPRINT = {
    'bytes': 12428,
    'sha256': '452e0997365ec45d4e0c8a7214d62b76d18f81f5eee27b52aabca395e9a644b9',
}
AUDIT_FINGERPRINT = {
    'bytes': 9022,
    'sha256': 'fb3ddcb29b1f9517a70c2dde718c61b211294934756839be811b1321984a25b6',
}
FBX_FINGERPRINT = {
    'bytes': 22588,
    'sha256': 'a82c0e1ee724138fabad7996a5b623a41a6f74c2a200ddfa4e405a404cd5b4bd',
}
LAYOUT_FINGERPRINT = {
    'bytes': 7265,
    'sha256': 'c0c171cbd73371a4d6f6342a8141a07fa69ed45f3cd96c1ab26106c4bc973314',
}
SOURCE_BOUNDS = {
    'min': [-11.925145149230957, -7.020364284515381, -0.5],
    'max': [14.629093170166016, 8.424022674560547, 2.5],
}
MODEL_TRANSFORM = {
    'Lcl Rotation': [0.0, -0.0, 180.00000500895632],
    'DefaultAttributeIndex': [0], 'InheritType': [1],
}
NAME = 'TidePen_r1_Residents'
REPORT_SCHEMA = 'daedalus.codex-tidepen-residents-native.v1'
OLD_REPORT_SCHEMA = 'daedalus.codex-qualified-static-packet-native.v1'


def _read_pinned(path, expected, supplied=None):
    path = Path(path)
    raw = path.read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if actual != expected or (supplied is not None and supplied != expected):
        raise RuntimeError('exact retained source fingerprint required: ' + str(path))
    return raw


def _dimensions(values):
    if (not isinstance(values, list) or len(values) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values)):
        raise RuntimeError('finite positive three-axis native dimensions required')
    return values


def _qualified_item(cfg):
    raw = _read_pinned(cfg['qualification_source'], QUALIFICATION_FINGERPRINT,
                       cfg['qualification_source_fingerprint'])
    qualification = json.loads(raw)
    if (qualification['schema'] != 'daedalus.tidepen-residents-qualified-source.v1'
            or qualification['stage'] != 'qualified_static_candidates_source_only'
            or qualification['source_views_personally_inspected_by_operator'] is not True
            or len(qualification['items']) != 1):
        raise RuntimeError('exact source-qualified Residents receipt required')
    item = qualification['items'][0]
    audit_path = item['provenance']['source_audit']
    audit = json.loads(_read_pinned(audit_path, AUDIT_FINGERPRINT))
    measurement = audit['measurement']
    if (item['name'] != NAME or item['fingerprint'] != FBX_FINGERPRINT
            or item['sidecar_fingerprint'] != LAYOUT_FINGERPRINT
            or item['source_bounds'] != SOURCE_BOUNDS or item['triangles'] != 650
            or item['source_unit_scale_factor'] != 100
            or item['required_future_actor_scale'] != [1., 1., 1.]
            or item['source_model_transform'] != MODEL_TRANSFORM
            or measurement['source_geometry_local_bounds'] != SOURCE_BOUNDS
            or measurement['model_transform_properties'] != MODEL_TRANSFORM
            or measurement['source_global_properties']['UnitScaleFactor'] != [100.]
            or measurement['source_global_properties']['OriginalUnitScaleFactor'] != [100.]
            or measurement['triangles'] != 650
            or measurement['all_source_faces_flat'] is not True
            or measurement['rgba_bytes'] != item['rgba_bytes']):
        raise RuntimeError('closed Residents geometry/model/metre source policy differs')
    return item


def _configured(cfg):
    """Fresh private scope; wrapping callbacks never rewrites source text."""
    source = Path(cfg['base_receiver_source'])
    if source.name != 'daedalus_codex_qualified_static.py':
        raise RuntimeError('unchanged qualified-static base filename required')
    raw = _read_pinned(source, BASE_FINGERPRINT, cfg['base_receiver_source_fingerprint'])
    base = {'__name__': '_codex_tidepen_residents_private_qualified_static'}
    exec(compile(raw, str(source), 'exec'), base)
    base['LABEL'] = LABEL
    original_items = base['_items']
    original_shared = base['_shared']
    original_metadata = base['_metadata']
    original_flush = base['_flush']

    def items(current):
        result = original_items(current)
        exact = _qualified_item(current)
        if len(result) != 1 or result[0] != exact:
            raise RuntimeError('only the exact qualified Residents item is admitted')
        return result

    def shared(current):
        scope = original_shared(current)
        if scope['UNIT_CONTRACT'] != 'claude_raw_unit100_build1_actor001_v1':
            raise RuntimeError('unexpected base catalogue unit policy')
        original_inspect = scope['inspect_mesh']
        scope['UNIT_CONTRACT'] = UNIT_CONTRACT

        def display_units(observed):
            # The original inspector also carries its raw observation on failure.
            # Correct those display fields before the existing error is journaled;
            # retain every raw measurement and the original refusal unchanged.
            if isinstance(observed, dict) and 'required_future_actor_scale' in observed:
                observed['required_future_actor_scale'] = [1., 1., 1.]
                if isinstance(observed.get('native_dimensions_cm'), list):
                    observed['projected_dimensions_cm_at_required_actor_scale'] = list(observed['native_dimensions_cm'])
                observed['unit_contract'] = UNIT_CONTRACT
                observed['source_units'] = 'metres; FBX UnitScaleFactor100; native centimetres; build1; actor1'
            return observed

        def inspect_mesh(mesh, item):
            try:
                observed = original_inspect(mesh, item)
            except scope['NativeContractError'] as error:
                display_units(error.observed)
                raise
            dims = _dimensions(observed['native_dimensions_cm'])
            if (observed['required_future_actor_scale'] != [.01, .01, .01]
                    or observed['projected_dimensions_cm_at_required_actor_scale'] != [v * .01 for v in dims]
                    or observed['unit_contract'] != UNIT_CONTRACT):
                raise RuntimeError('unexpected unchanged catalogue unit display fields')
            return display_units(observed)

        scope['inspect_mesh'] = inspect_mesh
        return scope

    def metadata(item, scope):
        values = original_metadata(item, scope)
        dimensions = [item['source_bounds']['max'][i] - item['source_bounds']['min'][i] for i in range(3)]
        if (len(values) != 9 or tuple(values) != tuple(scope['METADATA_KEYS'])
                or values['codex_unit_contract'] != UNIT_CONTRACT
                or values['codex_required_actor_scale'] != '0.01,0.01,0.01'
                or values['codex_intended_dimensions_cm'] != ','.join(format(v, '.12g') for v in dimensions)):
            raise RuntimeError('unexpected unchanged qualified-static metadata shape')
        values['codex_required_actor_scale'] = '1,1,1'
        values['codex_intended_dimensions_cm'] = ','.join(format(v * 100, '.12g') for v in dimensions)
        return values

    def flush(output, value):
        if (not isinstance(value, dict) or value.get('schema') not in (OLD_REPORT_SCHEMA, REPORT_SCHEMA)
                or value.get('requested_count') != 1 or value.get('unit_contract') != UNIT_CONTRACT
                or value.get('required_future_actor_scale') not in ([.01, .01, .01], [1., 1., 1.])):
            raise RuntimeError('closed one-item Residents report required before every durable write')
        value['schema'] = REPORT_SCHEMA
        value['required_future_actor_scale'] = [1., 1., 1.]
        value['source_units'] = 'metres; FBX UnitScaleFactor100; native centimetres; build1; actor1'
        original_flush(output, value)

    base['_items'] = items
    base['_shared'] = shared
    base['_metadata'] = metadata
    base['_flush'] = flush
    return base


def preflight(cfg):
    return _configured(cfg)['preflight'](cfg)


def readback(cfg):
    return _configured(cfg)['readback'](cfg)


def steps(cfg):
    return (yield from _configured(cfg)['steps'](cfg))


def generatorsteps(cfg):
    return (yield from steps(cfg))
