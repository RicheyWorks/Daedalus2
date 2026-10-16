# SPDX-License-Identifier: MIT
"""Closed R3 PenWater material seam; source only until separately admitted.

Reuses the unchanged, pinned Winter4 graph implementation in a private scope.
Only its source-factor validator receives a temporary glTF-default expansion;
all graph, metadata and hash functions receive the original raw definition.
Importing this file performs no native work. Creating a policy loads the pinned
helper but does not call Unreal. This is NOT an import/save/placement runner.

The receiving host must first verify the actual import inventory and fresh
ownership, resources, baseline, deadline and queue. Write calls are generators
and require that host's existing cooperative durable intent callback. Native
behavior, generated graph and material appearance remain unverified for R3.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/TidePenR3PenWaterR1_e76ccbfa471a5da0'
PARENT = ROOT + '/OwnedParents/M_Codex_TidePenR3_PenWater_RawAlpha_R1'
HELPER_SHA = '75c6d1eecef4d2c42d47db0b3a52033024f8bc7ac67efa58aeff83ad00f62000'
RAW_MATERIAL = {
    'name': 'HD_PenWaterClear', 'alphaMode': 'BLEND', 'doubleSided': True,
    'pbrMetallicRoughness': {
        'baseColorFactor': [0.3199999928474426, 0.7200000286102295,
                            0.7400000095367432, 0.3199999928474426],
        'roughnessFactor': 0.05000000074505806, 'metallicFactor': 0,
    },
}


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _raw(source):
    if _sha(source) != _sha(RAW_MATERIAL):
        raise ValueError('exact raw R3 PenWater material required')
    return deepcopy(source)


class PenWaterPolicy:
    """One fresh actual MIC and one fixed parent, with no recovery/retry API."""

    def __init__(self, instance_object_path, witness_directory):
        suffix = instance_object_path.removeprefix(ROOT + '/') if isinstance(instance_object_path, str) else ''
        if (not isinstance(instance_object_path, str) or not instance_object_path.startswith(ROOT + '/')
                or not re.fullmatch(r'[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.[A-Za-z0-9_]+', suffix)
                or suffix.split('/')[-1].split('.')[0] != suffix.split('.')[-1]
                or '/OwnedParents/' in instance_object_path
                or not suffix.split('.')[-1].lower().endswith('hd_penwaterclear')):
            raise ValueError('exact actual source-named MIC object path inside fresh R3 namespace required')
        witness = Path(witness_directory)
        if not witness.is_absolute() or not witness.is_dir():
            raise ValueError('existing absolute retained material-witness directory required')
        helper = Path(__file__).with_name('daedalus_codex_canal_material.py')
        data = helper.read_bytes()
        if hashlib.sha256(data).hexdigest() != HELPER_SHA:
            raise ValueError('unchanged pinned material helper required')
        scope = {'__name__': '_codex_tidepen_penwater_private_material', '__file__': str(helper)}
        exec(compile(data, str(helper), 'exec'), scope)
        scope['ROOT'] = ROOT
        scope['POLICY'] = 'owned_tidepen_r3_penwater_raw_alpha_v1'
        scope['WITNESS_DIRECTORY'] = str(witness)
        pbr = RAW_MATERIAL['pbrMetallicRoughness']
        scope['SOURCE_VALUES'] = {'HD_PenWaterClear': {
            'base': list(pbr['baseColorFactor']), 'roughness': pbr['roughnessFactor'],
            'metallic': pbr['metallicFactor'], 'emissive': [0.0, 0.0, 0.0]}}
        original_source = scope['_source']

        def source_with_defaults(source):
            expanded = _raw(source)
            expanded['emissiveFactor'] = [0.0, 0.0, 0.0]
            return original_source(expanded)

        scope['_source'] = source_with_defaults
        # Winter4 partial-recovery routes and paths do not belong to this profile.
        for name in ('inspect_partial_parent', 'resume_parent', 'PARTIAL_WATER', 'PARTIAL_NODES'):
            scope.pop(name, None)
        self._scope = scope
        self.instance_object_path = instance_object_path

    def _instance(self, instance):
        if instance.get_path_name() != self.instance_object_path:
            raise ValueError('the exact observed new MIC is required')

    @staticmethod
    def _parent(parent):
        name = PARENT.rsplit('/', 1)[1]
        if parent.get_path_name() != PARENT + '.' + name:
            raise ValueError('the one fixed private parent is required')

    def source_parameters(self):
        """Pure factor mapping after pinned-source load; no native API calls."""
        return self._scope['_source'](deepcopy(RAW_MATERIAL))

    def source_identity(self):
        semantic = deepcopy(RAW_MATERIAL)
        semantic['emissiveFactor'] = [0.0, 0.0, 0.0]
        return {'raw_material_sha256': _sha(RAW_MATERIAL),
                'semantic_material_sha256': _sha(semantic),
                'helper_raw_metadata_sha256': self._scope['_source_sha'](RAW_MATERIAL),
                'helper_source_sha256': HELPER_SHA, 'native_verified': False}

    def build_parent(self, intent):
        """yield-from only, after receiving host admission; returns UNSAVED."""
        return (yield from self._scope['build_parent'](PARENT, deepcopy(RAW_MATERIAL), intent))

    def bind_instance(self, instance, parent, intent):
        """yield-from only; existing graph/unsaved/intent checks remain intact."""
        self._instance(instance)
        self._parent(parent)
        return (yield from self._scope['bind_instance'](instance, parent, deepcopy(RAW_MATERIAL), intent))

    def inspect(self, instance, parent, miri_scope=None):
        """Existing complete graph readback; emits retained public text witnesses."""
        self._instance(instance)
        self._parent(parent)
        return self._scope['inspect'](instance, parent, deepcopy(RAW_MATERIAL), miri_scope)
