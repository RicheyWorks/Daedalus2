# SPDX-License-Identifier: MIT
"""Closed, file-only TidePen R3 PenWater receiving contract.

Reuses the retained GLB decoder. No Unreal, network, subprocess, import, save,
placement or source adoption occurs here. A source-qualified contract is never
a native execution grant. Existing receipts and producer files are not replaced.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from codex_tidepen_queue_manifest import glb

SCHEMA = 'daedalus.tidepen-r3-penwater-receiver.v1'
ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/TidePenR3PenWaterR1_e76ccbfa471a5da0'
PARENT = ROOT + '/OwnedParents/M_Codex_TidePenR3_PenWater_RawAlpha_R1'
PINS = {
    'TidePen_r3_PenWater.glb': 'e76ccbfa471a5da029794d95e1836244c39a2897224db345f46e8ce7c8661a75',
    'TidePen_r3.layout.json': '4facb66004a4a793a1f7e59e628b48dd3e338d8aa678918c8101c6d41f46a9c5',
    'TidePen_r3.tides.json': 'a854a14ed417182586d3af1bb7fc563cc7341a348649740d7bbc46cc605e1656',
}
RELEASE_SHA = '24fc312a7e50ab06da18ff3cf8da59b6ceb5e3feea9d7b1e4c1d0756bbe8fb2e'
MATERIAL_HELPER_SHA = '75c6d1eecef4d2c42d47db0b3a52033024f8bc7ac67efa58aeff83ad00f62000'
RAW_MATERIAL = {
    'name': 'HD_PenWaterClear', 'alphaMode': 'BLEND', 'doubleSided': True,
    'pbrMetallicRoughness': {
        'baseColorFactor': [0.3199999928474426, 0.7200000286102295,
                            0.7400000095367432, 0.3199999928474426],
        'roughnessFactor': 0.05000000074505806, 'metallicFactor': 0,
    },
}
ROOT_Y_METRES = -0.07999999821186066
TIDE_OFFSETS_METRES = {'low': -0.5, 'normal': 0.0, 'high': 0.6}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def semantic_material(raw):
    """Retain raw exporter data; expand only the omitted glTF emission default."""
    if canonical_sha(raw) != canonical_sha(RAW_MATERIAL):
        raise ValueError('only the exact retained PenWater raw material is supported')
    result = deepcopy(raw)
    result['emissiveFactor'] = [0.0, 0.0, 0.0]
    return result


def expected_native_bounds():
    """Conditional expectation for the existing root-baked XZY*100 receiver."""
    return {'min': [-750.0, -550.0, ROOT_Y_METRES * 100.0],
            'max': [750.0, 550.0, ROOT_Y_METRES * 100.0]}


def tide_placement(state, anchor_cm=(0.0, 0.0, 0.0), *, retain_logical_pivot=False):
    """Future placement arithmetic, conditional on observed root-baked geometry.

    With a neutral actor the already-baked root stays in mesh vertices. A future
    movable logical root may instead sit at the authored node origin only if a
    child component cancels that root translation. Neither recipe assigns an
    Ocean/world anchor or proves a native component/pivot representation.
    """
    if state not in TIDE_OFFSETS_METRES:
        raise ValueError('unknown tide state')
    if (len(anchor_cm) != 3 or any(type(x) not in (int, float) or not math.isfinite(x)
                                 for x in anchor_cm)):
        raise ValueError('finite three-component anchor required')
    root_z = ROOT_Y_METRES * 100.0
    actor = list(anchor_cm)
    actor[2] += TIDE_OFFSETS_METRES[state] * 100.0
    child = [0.0, 0.0, 0.0]
    if retain_logical_pivot:
        actor[2] += root_z
        child[2] = -root_z
    return {'actor_translation_cm': actor, 'mesh_relative_translation_cm': child,
            'actor_scale': [1.0, 1.0, 1.0], 'rotation_degrees': [0.0, 0.0, 0.0],
            'surface_z_cm': actor[2] + child[2] + root_z,
            'native_observed': False, 'world_anchor_assigned': False}


def validate_imported_inventory(objects):
    """Check a future actual import receipt, never fabricate native object names.

    Objects are exact {'path': object path, 'class': class name} readbacks.
    One StaticMesh + one MIC is required before creating the one private parent.
    A direct Material, alias guess, foreign object or extra output is a HOLD.
    """
    if not isinstance(objects, list) or len(objects) != 2:
        raise ValueError('exactly two actual imported objects required')
    found = {}
    for item in objects:
        if not isinstance(item, dict) or set(item) != {'path', 'class'}:
            raise ValueError('actual path/class pairs required')
        path, cls = item['path'], item['class']
        if (not isinstance(path, str) or not path.startswith(ROOT + '/')
                or '/OwnedParents/' in path
                or not re.fullmatch(r'[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.[A-Za-z0-9_]+',
                                    path.removeprefix(ROOT + '/'))
                or path.split('.')[-1] != path.split('/')[-1].split('.')[0]
                or cls not in ('StaticMesh', 'MaterialInstanceConstant') or cls in found):
            raise ValueError('unexpected imported path/class or duplicate class')
        found[cls] = path
    if len(set(found.values())) != 2:
        raise ValueError('duplicate imported object path')
    return {'mesh': found['StaticMesh'], 'instance': found['MaterialInstanceConstant'],
            'parent_package': PARENT, 'imported_objects': 2,
            'private_parents': 1, 'expected_saved_packages': 3,
            'native_saved': False}


def build_contract(source_root, producer_release):
    """Qualify exact released bytes; all native acceptance remains conditional."""
    if canonical_sha(producer_release) != RELEASE_SHA:
        raise ValueError('exact retained producer release 32741 required')
    source_root = Path(source_root)
    pins = {}
    for name, wanted in PINS.items():
        data = (source_root / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != wanted:
            raise ValueError('retained producer payload changed: ' + name)
        pins[name] = {'bytes': len(data), 'sha256': actual}
    decoded = glb(source_root / 'TidePen_r3_PenWater.glb')
    if (decoded['scene_roots'] != [0] or len(decoded['nodes']) != 1
            or decoded['materials'] != [RAW_MATERIAL] or decoded['extensions_used']
            or decoded['extensions_required'] or decoded['images'] or decoded['textures']):
        raise ValueError('closed one-root, one-material factor-only GLB required')
    node = decoded['nodes'][0]
    primitive, = node['primitives']
    if (node['classification'] != 'render'
            or node['authored_transform_fields'] != {'translation': [0, ROOT_Y_METRES, 0]}
            or primitive['position_count_decoded'] != 41
            or primitive['triangles_decoded_from_index_count'] != 40
            or set(primitive['attributes']) != {'POSITION', 'NORMAL'}):
        raise ValueError('exact released PenWater geometry/transform required')
    layout = json.loads((source_root / 'TidePen_r3.layout.json').read_text(encoding='utf-8'))
    tides = json.loads((source_root / 'TidePen_r3.tides.json').read_text(encoding='utf-8'))
    role = layout['roles']['PenWater']
    if (role['file'] != 'TidePen_r3_PenWater.glb' or role['triangles'] != 40
            or role['materials'] != ['HD_PenWaterClear'] or role['collision'] != []
            or role['anchor'] != [0.0, 0.0, -0.08]):
        raise ValueError('exact one-role producer layout required')
    states = layout['habitat']['water_states']
    if ({s['id']: s['offset_m'] for s in states} != TIDE_OFFSETS_METRES
            or [s['water_state'] for s in tides['shots']] != states):
        raise ValueError('layout/tide evidence differs')
    raw = deepcopy(decoded['materials'][0])
    semantic = semantic_material(raw)
    # The retained decoder/sidecar readers reopen paths. Fail closed if their
    # producer changes any source during qualification; never repin that change.
    for name, wanted in PINS.items():
        if hashlib.sha256((source_root / name).read_bytes()).hexdigest() != wanted:
            raise ValueError('producer payload changed during qualification: ' + name)
    return {
        'schema': SCHEMA, 'stage': 'SOURCE_QUALIFIED_NATIVE_NOT_ADMITTED',
        'source_qualified': True, 'native_ready': False,
        'scope': {'roles': ['PenWater'], 'native_execution_authorized': False,
                  'imported': False, 'saved': False, 'placed': False},
        'producer': {'team': 'TeamClaude / unreal-team', 'individual_author': None,
                     'release_hub_id': 32741, 'release_record_sha256': RELEASE_SHA,
                     'layout_provenance': layout['provenance']},
        'source_pins': pins, 'raw_material': raw,
        'raw_material_canonical_sha256': canonical_sha(raw),
        'semantic_material': semantic,
        'semantic_material_canonical_sha256': canonical_sha(semantic),
        'semantic_default_expansion': {'emissiveFactor': [0.0, 0.0, 0.0]},
        'geometry': {'decoded': decoded, 'units': 'glTF Y-up metres',
                     'conditional_native_conversion': 'root-baked XZY * 100; verify readback',
                     'expected_native_bounds_cm': expected_native_bounds(),
                     'zero_z_extent_intentional': True, 'render_triangles': 40,
                     'collision_primitives': 0, 'actor_scale': [1, 1, 1]},
        'tides': {'offsets_metres': TIDE_OFFSETS_METRES,
                  'neutral_actor_examples': {s: tide_placement(s) for s in TIDE_OFFSETS_METRES},
                  'logical_pivot_examples': {s: tide_placement(s, retain_logical_pivot=True)
                                             for s in TIDE_OFFSETS_METRES},
                  'placement_status': 'conditional arithmetic only; no native pivot/world assignment'},
        'native_plan': {
            'destination': ROOT, 'private_parent_package': PARENT,
            'backend': 'existing AssetImportTask; actual Interchange receipt required',
            'task': {'replace_existing': False, 'save': False, 'options': None},
            'expected_imported_classes': ['StaticMesh', 'MaterialInstanceConstant'],
            'expected_imported_objects': 2, 'expected_private_parents': 1,
            'expected_saved_packages': 3, 'actual_imported_object_paths': None,
            'material_helper': {'file': 'daedalus_codex_canal_material.py',
                                'sha256': MATERIAL_HELPER_SHA,
                                'reuse': 'private scope; build_parent, bind_instance, inspect only',
                                'adapter': 'daedalus_codex_tidepen_penwater_policy.py',
                                'helper_metadata_hash_represents': 'original raw exporter material',
                                'defaults_boundary': 'only private _source validation expands omitted emission'},
            'mesh_options': {'nanite': False, 'generate_lightmap_uvs': False,
                             'auto_generate_collision': False, 'simple_collision_count': 0},
            'required_before_first_save': [
                'new native execution assignment; fresh ownership/resource/PIE/inflight/dirty checks',
                'protect 184 accepted sources, 218 saved packages, 145 actors and map f77f83a2',
                'pin source/helper bytes; exact fresh destination and retained intent/raw envelope',
                'journal original backend return before unwrap; never replay an uncertain import',
                'actual paths/classes inventory exactly one StaticMesh and one MIC',
                'mesh slot0 binds that exact imported MIC; complete namespace has no unexpected outputs',
                '40 triangles, local/root-baked bounds, scale1, flat Z and zero collision readbacks',
                'private translucent two-sided raw linear RGBA/PBR parent; no gamma/vertex multiplier',
                'full existing material graph/parameters/opacity/witness checks and new-object metadata',
                'unchanged queue/deadline/preservation guards; all three objects verified before save',
                'parent-first saves with true returns, independent readback and output/backup hashes',
            ],
            'receiver_execution': 'not implemented or invoked by this file-only profile',
        },
        'limitations': ['source/tide renders are Blender evidence only',
                        'no native import/save/placement/pivot/material visual acceptance',
                        'no canonical Ocean anchor, tide animation or care/gate gameplay acceptance',
                        'other TidePen roles and source/build adoption remain separate'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True,
                        help='retained independent source qualification with producer_release')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qualification = json.loads(args.qualification.read_text(encoding='utf-8'))
    contract = build_contract(args.source_root, qualification['producer_release'])
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(contract, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'stage': contract['stage'],
                      'bytes': args.output.stat().st_size,
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
