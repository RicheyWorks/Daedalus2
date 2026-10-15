# SPDX-License-Identifier: MIT
"""Exact observed-alias recovery of four unsaved Canal outputs; never import.

prepare clones immutable receipts into a new folder, preserving the original
claim as provenance. An explicit terminal/release/new-claim transition may admit
a fresh bounded remaining phase. run executes only the remaining parent/save
tail. Partial or uncertain recovery forbids replay. Use the existing delivery
adapter's readback/finalize afterwards with this recovery folder.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import textwrap
import time
from types import SimpleNamespace

import codex_canal_water_delivery as h
from codex_static_intake_delivery import _snap_definition

d = h.d
ORIGINAL = h.TASK / 'native-ingestion/Winter4CanalStream1CoreR2'
PROOF = {'bytes': 192153, 'sha256': 'e7172ea7a2399ba4bf60d3de6b509cefc08f745235f852fc76499a98c52a23cf'}
PREDECESSOR = ORIGINAL / 'RecoveryObservedAliasR1'
SECOND_PREDECESSOR = ORIGINAL / 'RecoveryObservedAliasR2'
THIRD_PREDECESSOR = ORIGINAL / 'RecoveryObservedAliasR3'
FOURTH_PREDECESSOR = ORIGINAL / 'RecoveryObservedAliasR4'
QUALIFICATION = ORIGINAL / 'PartialParentQualificationR1'
DEFAULT_FOLDER = ORIGINAL / 'RecoveryObservedAliasR5'
WATER_ROLE = 'Octet_Winter_4_Canal_Stream1'
WATER_PARENT = h.DEST + '/OwnedParents/M_Codex_Winter4_Water_RawAlpha_R1'
WATER_OBJECT = WATER_PARENT + '.' + WATER_PARENT.rsplit('/', 1)[1]
PREDECESSOR_FILES = {
    'prepared.json': {'bytes': 9544, 'sha256': '47f523ca9cf37f8acb94264a49cc5c475d7caa7d212b7a755ba7ce6f46ea9735'},
    'dispatch.json': {'bytes': 2378, 'sha256': 'b7eb7acfadc271d084ef238228645d2879e7dfb2acccc6152f64512f6ad79691'},
    'native.json': {'bytes': 8828, 'sha256': '42f973c110da75e4badcf0a1fa6aa3e649c52acbe08dedc7c382b3a4f58f21ec'},
    'recovery-executed-code.py': {'bytes': 11665, 'sha256': 'f169705f3fa7edd8c3da52923d5c99653f5cfa2f0d78163369e0e537b9c81e76'},
    'source-archive-receipt.json': {'bytes': 3986, 'sha256': '9224ad32dba9bcd156170f0be538aac8cd49e90303dc7ba12667832e35f601c0'},
}
SECOND_PREDECESSOR_FILES = {
    'prepared.json': {'bytes': 21823, 'sha256': '8abc1727c11b60cf24e47f93b3794f0c4f618eee085285b88a64ef6531ebd457'},
    'dispatch.json': {'bytes': 2379, 'sha256': 'c0f0f476388c8d07db1383927e8e36d1007a5a43b80e82288c3e85b01509da43'},
    'native.json': {'bytes': 8851, 'sha256': '8e1b670e54f89507bb9a1b8572d2eebfa8326a70c0f20202a450268a2a04eae9'},
    'recovery-executed-code.py': {'bytes': 11665, 'sha256': '143d9bb498c63dba84a26d34c86d17a33683f2e392d4a0be410dfce2bec76927'},
    'terminal-file-closeout.json': {'bytes': 6538, 'sha256': '387d37335fdeededec9a956f2a3adaa3cc2f29bf721c66861321cc26ce0145a3'},
}
TEXT_WITNESS = ORIGINAL / 'MaterialTextWitnessR2'
TEXT_WITNESS_FILES = {
    'receipt.json': {'bytes': 355493, 'sha256': 'c8669675c4ddb2e235e23445ab89c855ce5656fe6277e30c9eb2429e2f0e64c5'},
    'MaterialEditorOnlyDataClassDefault.t3d': {'bytes': 4821, 'sha256': 'f841d58deb60ba2fd9485331cce15953d2383e059df6ad8178a5f654dd839ee4'},
    'executed-code.json': {'bytes': 8498, 'sha256': 'a41ad26dd787eac952e7ef828ebf9bf619e41411930d8dfc5080a153d0ba8e06'},
}
THIRD_PREDECESSOR_FILES = {
    'prepared.json': {'bytes': 33570, 'sha256': 'f252e07b6a79ecbd47f67866555f0cd56645464aa1ea0b49f4edd2a24cb2fe84'},
    'dispatch.json': {'bytes': 2408, 'sha256': '48fab7f6e430f108c07eb5b86271c214aee02c293fe7dd5965edc02aaefd9859'},
    'native.json': {'bytes': 8830, 'sha256': '08657b59441b051a12d2c8c76dd8a552535589f6bb592e16764f6ca9505aa3bc'},
    'recovery-executed-code.py': {'bytes': 11665, 'sha256': 'c29c628ac7b0a9d85f577711e37187a50a8c36f6019a9e075fd85a6e7b4878f1'},
    'queue-reconciliation.json': {'bytes': 186648, 'sha256': '444ab0728a810c5e3ef9ccc0bd6f86535030471e5381fa824cd60ea1b6a05b7c'},
    'source-archive-receipt.json': {'bytes': 4283, 'sha256': 'e9d2b059578bfb5d76450aa63f04e156c7c69230c4c48f65bbef28d77829a67e'},
}
FOURTH_PREDECESSOR_FILES = {
    'prepared.json': {'bytes': 46439, 'sha256': '8d7e900eb946d8e3a3166ce2466e2efd612fe590832fa075380195451769966e'},
    'dispatch.json': {'bytes': 2408, 'sha256': '0b5cdc56726131227090e14b29f82d8811c90b9ad265480b77fd58c6b1a47f9d'},
    'native.json': {'bytes': 19296, 'sha256': '56cc9e73749b9ae98c418580d33259e1a0b4935554b17769ab9fdb6576fcdde8'},
    'guard-rejection.json': {'bytes': 1468, 'sha256': '7bb76c1ddd141fc0c0cd051b252bfaaa5f38539d46095768e612b6574040f920'},
    'terminal-file-closeout.json': {'bytes': 5861, 'sha256': 'c26b8b74302f5ee5fae843737536eedcbba10bdc27300d7dbec6ea9f3111d83d'},
    'recovery-executed-code.py': {'bytes': 13097, 'sha256': '42c22ca246c677fcf033a9eaf21c65226c80b8bb35b223d654d433805c1ec984'},
}
QUALIFICATION_FILE = {'bytes': 379462, 'sha256': '7dfe6b75cb5bb39d73e5c62e71672f7039425173c98624a6bf2581c950e9ec50'}


def archived_helpers(value):
    """Verify executed old helpers at immutable archives, never current paths."""
    archives = {}
    for key, pin in value['helpers'].items():
        path = ORIGINAL / 'source-used' / Path(pin['path']).name
        archived = {'path': str(path), **d.fp(pin)}
        d._check(archived)
        archives[key] = archived
    return archives


def predecessor(paths):
    """R2 admits only the pinned terminal R1 failure before its first intent."""
    pins = {name: {'path': str(PREDECESSOR / name), **expected}
            for name, expected in PREDECESSOR_FILES.items()}
    for pin in pins.values():
        d._check(pin)
    previous = d.load(PREDECESSOR / 'prepared.json')
    dispatch = d.load(PREDECESSOR / 'dispatch.json')
    native = d.load(PREDECESSOR / 'native.json')
    if (native.get('stage') != 'halted_preserve_partial'
            or native.get('error') != 'exact reflected CustomizedUV property unavailable: 0'
            or native.get('error_type') != 'RuntimeError'
            or native.get('mutation_intents') != [] or native.get('outputs') != []
            or native.get('completed_count') != 0 or native.get('save_return') is not None
            or native.get('imports_replayed') != 0 or native.get('world_placed') != 0
            or native.get('world_saved') is not False
            or set(native.get('imported_object_paths', [])) != set(paths)
            or dispatch.get('stage') != 'hold_reconcile_outcome_never_replay'
            or dispatch.get('compute_claim') != previous['recovery']['selected_compute_claim']):
        raise RuntimeError('only exact zero-intent/zero-parent/zero-save R1 terminal failure admits R2')
    observed = native['before_parent_creation']
    if (observed.get('created_parent_count') != 0
            or {row['path'] for row in observed['assets']} != set(paths)
            or sorted(row['class'] for row in observed['assets']) !=
               ['MaterialInstanceConstant', 'MaterialInstanceConstant', 'StaticMesh', 'StaticMesh']):
        raise RuntimeError('R1 must retain exactly the same four objects and no owned parents')
    archive = d.load(PREDECESSOR / 'source-archive-receipt.json')['sources']
    expected_sources = {'adapter': previous['recovery']['adapter_source'],
                        'native_source': previous['native_source'], **previous['helpers']}
    for key, expected in expected_sources.items():
        pin = archive[key]
        if (d.fp(pin) != d.fp(expected)
                or Path(pin['path']).resolve().parent != (PREDECESSOR / 'source-used').resolve()):
            raise RuntimeError('exact executed R1 source archive differs: ' + key)
        d._check(pin)
    code = d.load(PREDECESSOR / 'recovery-executed-code.py')
    if not isinstance(code, str) or hashlib.sha256(code.encode()).hexdigest() != dispatch['code_sha256']:
        raise RuntimeError('R1 executed-code witness differs from terminal dispatch')
    return previous, dispatch, {'files': pins, 'executed_sources': archive}


def second_predecessor(paths):
    """Pin both terminal revisions and the successful read-only class-default proof."""
    r1, r1_dispatch, r1_pins = predecessor(paths)
    pins = {name: {'path': str(SECOND_PREDECESSOR / name), **expected}
            for name, expected in SECOND_PREDECESSOR_FILES.items()}
    text_pins = {name: {'path': str(TEXT_WITNESS / name), **expected}
                 for name, expected in TEXT_WITNESS_FILES.items()}
    for pin in [*pins.values(), *text_pins.values()]:
        d._check(pin)
    previous = d.load(SECOND_PREDECESSOR / 'prepared.json')
    dispatch = d.load(SECOND_PREDECESSOR / 'dispatch.json')
    native = d.load(SECOND_PREDECESSOR / 'native.json')
    closeout = d.load(SECOND_PREDECESSOR / 'terminal-file-closeout.json')
    if (previous['recovery'].get('revision') != 2
            or previous['recovery'].get('zero_mutation_predecessor') != r1_pins
            or dispatch.get('compute_claim') != r1_dispatch['compute_claim']
            or native.get('stage') != 'halted_preserve_partial'
            or native.get('error') != 'supported disconnected material property unavailable: MP_PIXEL_DEPTH_OFFSET'
            or native.get('error_type') != 'RuntimeError'
            or native.get('mutation_intents') != [] or native.get('outputs') != []
            or native.get('completed_count') != 0 or native.get('save_return') is not None
            or native.get('imports_replayed') != 0 or native.get('world_placed') != 0
            or native.get('world_saved') is not False
            or set(native.get('imported_object_paths', [])) != set(paths)
            or native['before_parent_creation'].get('created_parent_count') != 0
            or dispatch.get('stage') != 'hold_reconcile_outcome_never_replay'):
        raise RuntimeError('only the pinned zero-intent/zero-parent/zero-save R2 failure admits R3')
    if (closeout.get('stage') != 'known_terminal_zero_mutation_preserved_file_boundary_compute_released'
            or closeout.get('terminal_journal') != pins['native.json']
            or closeout.get('compute_claim') != dispatch['compute_claim']
            or closeout.get('compute_release', {}).get('ok') is not True
            or closeout['compute_release'].get('lock') is not None
            or 'compute' in closeout.get('locks_after', {})
            or any(closeout.get(key) != 0 for key in
                   ('new_parents', 'new_first_saves', 'imports_replayed', 'world_placed'))
            or closeout.get('world_saved') is not False):
        raise RuntimeError('pinned R2 terminal closeout and explicit compute release required')
    archive = closeout['executed_source_archives']
    expected_sources = {'adapter': previous['recovery']['adapter_source'],
                        'native_source': previous['native_source'], **previous['helpers']}
    for key, pin in archive.items():
        if Path(pin['path']).resolve().parent != (SECOND_PREDECESSOR / 'source-used').resolve():
            raise RuntimeError('R2 sources must remain in their executed immutable archive')
        if key in expected_sources and d.fp(pin) != d.fp(expected_sources[key]):
            raise RuntimeError('executed R2 source archive differs: ' + key)
        d._check(pin)
    if not set(expected_sources).issubset(archive):
        raise RuntimeError('complete R2 executed source archive required')
    code = d.load(SECOND_PREDECESSOR / 'recovery-executed-code.py')
    if not isinstance(code, str) or hashlib.sha256(code.encode()).hexdigest() != dispatch['code_sha256']:
        raise RuntimeError('R2 executed-code witness differs from terminal dispatch')
    witness = d.load(TEXT_WITNESS / 'receipt.json')
    observed = witness['native']
    if (witness.get('stage') != 'read_only_material_text_export_complete'
            or observed.get('stage') != witness['stage']
            or witness.get('terminal_predecessor') != pins['native.json']
            or witness.get('terminal_reply_received') is not True
            or witness.get('compute_release', {}).get('ok') is not True
            or witness['compute_release'].get('lock') is not None
            or 'compute' in witness.get('locks_after', {})
            or any(witness.get(key) != 0 or observed.get(key) != 0 for key in
                   ('asset_imports', 'content_saves', 'world_saves', 'material_mutations', 'world_placed'))
            or witness.get('file_exports') != [text_pins['MaterialEditorOnlyDataClassDefault.t3d']]):
        raise RuntimeError('complete guarded read-only T3D class-default witness and release required')
    exports = observed.get('exports', [])
    if (len(exports) != 1 or exports[0].get('return') is not True or exports[0].get('errors') != []
            or exports[0].get('class') != 'MaterialEditorOnlyData'
            or exports[0].get('object') != '/Script/Engine.Default__MaterialEditorOnlyData'):
        raise RuntimeError('actual correct MaterialEditorOnlyData class-default export required')
    allowed = {path.split('.')[0] for path in paths}
    for key in ('pre', 'post'):
        gate = observed[key]
        if (gate.get('editor_world') != '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
                or gate.get('dirty_map_packages') != []
                or set(gate.get('dirty_content_packages', [])) != allowed
                or gate.get('other_running_generators') != []
                or gate.get('queued_jobs') != 0 or gate.get('unfinished_async_job_boxes') != 0
                or gate.get('pie_running') is not False or gate.get('remote_execution_lock_locked') is not False):
            raise RuntimeError('known-four-only guarded text export required')
    d._same_scene(observed['scene_before'], observed['scene_after'])
    d._same_scene(observed['scene_after'], d.load(previous['baseline']['path'])['scene'])
    return previous, dispatch, {'files': pins, 'executed_sources': archive,
                                'r1': r1_pins, 'material_text_witness': text_pins}


def third_predecessor(paths):
    """R4 continues only a zero-effect R3 rejection after a fresh full guard proof."""
    r2, r2_dispatch, r2_pins = second_predecessor(paths)
    pins = {name: {'path': str(THIRD_PREDECESSOR / name), **expected}
            for name, expected in THIRD_PREDECESSOR_FILES.items()}
    for pin in pins.values():
        d._check(pin)
    previous = d.load(THIRD_PREDECESSOR / 'prepared.json')
    dispatch = d.load(THIRD_PREDECESSOR / 'dispatch.json')
    native = d.load(THIRD_PREDECESSOR / 'native.json')
    if (previous['recovery'].get('revision') != 3
            or previous['recovery'].get('zero_mutation_predecessor') != r2_pins
            or native.get('stage') != 'halted_preserve_partial'
            or native.get('error') != 'conflicting/unfinished bridge operation; preserve work'
            or native.get('mutation_intents') != [] or native.get('outputs') != []
            or native.get('completed_count') != 0 or native.get('save_return') is not None
            or native.get('imports_replayed') != 0 or native.get('world_placed') != 0
            or native.get('world_saved') is not False
            or native['before_parent_creation'].get('created_parent_count') != 0
            or set(native.get('imported_object_paths', [])) != set(paths)
            or dispatch.get('stage') != 'hold_reconcile_outcome_never_replay'
            or dispatch['compute_claim'] != previous['recovery']['selected_compute_claim']):
        raise RuntimeError('exact pinned zero-effect R3 guard rejection required')
    archive = d.load(THIRD_PREDECESSOR / 'source-archive-receipt.json')['sources']
    expected = {'adapter': previous['recovery']['adapter_source'],
                'native_source': previous['native_source'], **previous['helpers']}
    for key, wanted in expected.items():
        pin = archive[key]
        if (d.fp(pin) != d.fp(wanted)
                or Path(pin['path']).resolve().parent != (THIRD_PREDECESSOR / 'source-used').resolve()):
            raise RuntimeError('executed R3 source archive differs: ' + key)
        d._check(pin)
    proof = d.load(THIRD_PREDECESSOR / 'queue-reconciliation.json')
    observed = proof['native']
    if (proof.get('stage') != 'exact_four_zero_parent_scene_guard_verified'
            or observed.get('stage') != proof['stage']
            or proof.get('terminal') != pins['native.json']
            or proof.get('native_mutations') != 0 or observed.get('native_mutations') != 0
            or observed['geometry'].get('issues') != []
            or observed['geometry'].get('triangles') != 2912
            or observed['geometry'].get('created_parent_count') != 0
            or {row['path'] for row in observed['geometry']['assets']} != set(paths)):
        raise RuntimeError('fresh exact-four/zero-parent guard reconciliation required')
    allowed = {path.split('.')[0] for path in paths}
    for key in ('pre', 'post'):
        gate = observed[key]
        if (gate.get('dirty_map_packages') != [] or set(gate.get('dirty_content_packages', [])) != allowed
                or gate.get('other_running_generators') != [] or gate.get('queued_jobs') != 0
                or gate.get('unfinished_async_job_boxes') != 0 or gate.get('pie_running') is not False
                or gate.get('remote_execution_lock_locked') is not False):
            raise RuntimeError('normal known-four guard proof required before R4')
    for key in ('diagnostic_before', 'diagnostic_after'):
        item = observed[key]
        if (item.get('queued_jobs') != 0 or item.get('remote_execution_lock_locked') is not False
                or item.get('expected_step_frame_found') is not True
                or item.get('expected_type_label_match') is not True or item.get('running_total') != 1
                or len(item.get('running', [])) != 1
                or item['running'][0].get('is_exact_expected_running') is not True
                or item.get('unfinished_async_job_boxes') != [] or item.get('snapshot_error_type')):
            raise RuntimeError('fresh exact-one-frame empty-queue diagnostic proof required')
    d._same_scene(observed['scene'], d.load(previous['baseline']['path'])['scene'])
    diagnostic = proof['existing_diagnostic_source']; d._check(diagnostic)
    return previous, dispatch, {'files': pins, 'executed_sources': archive, 'r2': r2_pins,
                                'diagnostic_source': diagnostic}


def _evidence_pins(value):
    """Flatten only retained file pins; provenance remains nested in prepared.json."""
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'}.issubset(value):
            yield value
        else:
            for child in value.values():
                yield from _evidence_pins(child)
    elif isinstance(value, list):
        for child in value:
            yield from _evidence_pins(child)


def fourth_predecessor(paths):
    """Admit only the exact four-node Water partial, never a replay of R4."""
    r3, r3_dispatch, r3_pins = third_predecessor(paths)
    pins = {name: {'path': str(FOURTH_PREDECESSOR / name), **expected}
            for name, expected in FOURTH_PREDECESSOR_FILES.items()}
    qualification_pin = {'path': str(QUALIFICATION / 'receipt.json'), **QUALIFICATION_FILE}
    for pin in [*pins.values(), qualification_pin]:
        d._check(pin)
    previous = d.load(FOURTH_PREDECESSOR / 'prepared.json')
    dispatch = d.load(FOURTH_PREDECESSOR / 'dispatch.json')
    native = d.load(FOURTH_PREDECESSOR / 'native.json')
    closeout = d.load(FOURTH_PREDECESSOR / 'terminal-file-closeout.json')
    operations = [row.get('operation') for row in native.get('mutation_intents', [])]
    expected_operations = (['create_owned_factor_alpha_parent'] + ['set_owned_parent_property'] * 7
        + sum((['create_owned_parameter_node'] + ['set_owned_parameter_property'] * count
               for count in (3, 3, 3, 1)), []))
    if (previous['recovery'].get('revision') != 4
            or previous['recovery'].get('zero_mutation_predecessor') != r3_pins
            or previous['recovery'].get('same_active_predecessor_compute_claim') != r3_dispatch['compute_claim']
            or dispatch.get('compute_claim') != r3_dispatch['compute_claim']
            or dispatch.get('stage') != 'hold_reconcile_outcome_never_replay'
            or native.get('stage') != 'halted_preserve_partial'
            or native.get('error') != 'conflicting/unfinished bridge operation; preserve work'
            or operations != expected_operations or len(operations) != 22
            or native.get('outputs') != [] or native.get('completed_count') != 0
            or native.get('save_return') is not None or native.get('imports_replayed') != 0
            or native.get('world_placed') != 0 or native.get('world_saved') is not False
            or set(native.get('imported_object_paths', [])) != set(paths)):
        raise RuntimeError('only pinned R4 exact22-intent/four-node Water partial admits R5')
    if (closeout.get('stage') != 'known_terminal_one_partial_parent_zero_saves_compute_released'
            or closeout.get('terminal') != pins['native.json']
            or closeout.get('rejection') != pins['guard-rejection.json']
            or closeout.get('previous_claim') != dispatch['compute_claim']['lock']
            or closeout.get('compute_release') != {'ok': True, 'lock': None}
            or 'compute' in closeout.get('locks_after', {})
            or any(closeout.get(key) != expected for key, expected in
                   (('imports_replayed', 0), ('new_parents_created', 1), ('new_parameter_nodes_created', 4),
                    ('first_saves', 0), ('mic_bindings', 0), ('world_placed', 0), ('world_saves', 0)))):
        raise RuntimeError('exact R4 partial closeout and compute release required')
    archive = closeout['executed_source_archives']
    expected_sources = {'adapter': previous['recovery']['adapter_source'],
                        'native_source': previous['native_source'], **previous['helpers']}
    for key, wanted in expected_sources.items():
        pin = archive[key]
        if (d.fp(pin) != d.fp(wanted)
                or Path(pin['path']).resolve().parent != (FOURTH_PREDECESSOR / 'source-used').resolve()):
            raise RuntimeError('executed R4 source archive differs: ' + key)
        d._check(pin)
    d._check(archive['delivery_adapter'])
    code = d.load(FOURTH_PREDECESSOR / 'recovery-executed-code.py')
    if not isinstance(code, str) or hashlib.sha256(code.encode()).hexdigest() != dispatch['code_sha256']:
        raise RuntimeError('R4 executed code differs from terminal dispatch')
    rejection = d.load(FOURTH_PREDECESSOR / 'guard-rejection.json')
    diagnostic = rejection['diagnostic']
    if (rejection.get('guard_changed') is not False or rejection.get('queue_mutations') != 0
            or diagnostic.get('queued_jobs') != 1 or diagnostic.get('queued_request_rows_truncated') is not False
            or len(diagnostic.get('queued_request_rows', [])) != 1
            or diagnostic['queued_request_rows'][0].get('type') != 'ping'
            or diagnostic['queued_request_rows'][0].get('code_sha256') != hashlib.sha256(b'').hexdigest()
            or diagnostic.get('running_total') != 1 or len(diagnostic.get('running', [])) != 1
            or diagnostic['running'][0].get('is_exact_expected_running') is not True
            or diagnostic.get('unfinished_async_job_boxes') != []
            or diagnostic.get('remote_execution_lock_locked') is not False):
        raise RuntimeError('pinned R4 exact queued READping rejection witness differs')
    proof = d.load(qualification_pin['path']); observed = proof['native']
    expected_paths = sorted([*paths, WATER_OBJECT])
    partial = observed['observed'].get('partial_parent', {})
    if (proof.get('stage') != 'exact_five_objects_partial_water_parent_qualified'
            or observed.get('stage') != proof['stage']
            or proof.get('terminal') != pins['native.json']
            or proof.get('terminal_closeout') != pins['terminal-file-closeout.json']
            or proof.get('rejection') != pins['guard-rejection.json']
            or sorted(proof.get('expected_paths', [])) != expected_paths
            or any(proof.get(key) != 0 or observed.get(key) != 0 for key in
                   ('native_mutations', 'asset_imports', 'content_saves', 'map_saves', 'world_placed'))
            or proof.get('compute_release') != {'ok': True, 'lock': None}
            or 'compute' in proof.get('locks_after', {})
            or observed['observed'].get('issues') != []
            or observed['observed'].get('created_parent_count') != 1
            or observed['observed'].get('triangles') != 2912
            or {row['path'] for row in observed['observed']['assets']} != set(expected_paths)
            or partial.get('stage') != 'exact_r4_water_four_node_partial_verified'
            or partial.get('saved') is not False or partial.get('bindings_completed') != 0
            or partial.get('mutations') != 0 or partial.get('issues') != []
            or len(partial.get('nodes', [])) != 4):
        raise RuntimeError('pinned fresh exact-five/four-node/zero-mutation qualification required')
    allowed = {path.split('.')[0] for path in expected_paths}
    for key in ('pre', 'post'):
        gate = observed[key]
        if (gate.get('dirty_map_packages') != [] or set(gate.get('dirty_content_packages', [])) != allowed
                or gate.get('other_running_generators') != [] or gate.get('queued_jobs') != 0
                or gate.get('unfinished_async_job_boxes') != 0 or gate.get('pie_running') is not False
                or gate.get('remote_execution_lock_locked') is not False):
            raise RuntimeError('fresh normal exact-five guard proof required')
    baseline = d.load(previous['baseline']['path'])
    if proof.get('baseline') != previous['baseline'] or proof.get('unchanged_map') != baseline['map']:
        raise RuntimeError('partial qualification preservation baseline differs')
    for key in ('scene_before', 'scene_after'):
        d._same_scene(observed[key], baseline['scene'])
    for pin in [proof['source'], proof['native_source'], *proof['helpers'].values()]:
        d._check(pin)
    return previous, dispatch, {'files': pins, 'executed_sources': archive, 'r3': r3_pins,
                                'qualification': qualification_pin}, proof


def original():
    value = d.load(ORIGINAL / 'prepared.json')
    old_source = ORIGINAL / 'source-used' / Path(value['native_source']['path']).name
    if d.fingerprint(old_source) != d.fp(value['native_source']):
        raise RuntimeError('exact executed original native source archive required')
    for pin in [value['baseline'], value['manifest'], value['glb'], *value['source_pins']]:
        d._check(pin)
    archived_helpers(value)
    h.validate_release(d.load(d.load(value['manifest']['path'])['release']['path']))
    native = d.load(ORIGINAL / 'native.json')
    dispatch = d.load(ORIGINAL / 'dispatch.json')
    if (native.get('stage') != 'halted_preserve_partial' or native.get('completed_count') != 0
            or native.get('outputs') != [] or native.get('save_return') is not None
            or native.get('world_placed') != 0 or native.get('world_saved') is not False
            or native.get('error') != 'unambiguous actual two-role mesh mapping required'):
        raise RuntimeError('only exact original zero-save alias failure may recover')
    operations = [row['operation'] for row in native['mutation_intents']]
    if operations != ['import_exact_released_derived_glb', 'set_new_owned_mesh_nanite_false', 'set_new_owned_mesh_nanite_false']:
        raise RuntimeError('unexpected original effects; preserve partial state')
    paths = native.get('imported_object_paths', [])
    if len(paths) != 4 or len(set(paths)) != 4 or any(not p.startswith(h.DEST + '/') for p in paths):
        raise RuntimeError('exact four unique owned imported paths required')
    proof_path = ORIGINAL / 'naming-reconciliation.json'
    if d.fingerprint(proof_path) != PROOF:
        raise RuntimeError('exact successful current read-only reconciliation required')
    proof = d.load(proof_path)
    for key in ('original_native', 'original_dispatch', 'baseline'):
        d._check(proof[key])
    observed = proof.get('native', {})
    if (proof.get('stage') != 'exact_four_unsaved_alias_geometry_raw_pbr_reconciled'
            or proof.get('native_mutations') != 0
            or observed.get('stage') != proof['stage'] or observed.get('native_mutations') != 0
            or len(observed.get('items', [])) != 2
            or {r['path'] for r in observed.get('assets', [])} != set(paths)
            or sorted(r['class'] for r in observed['assets']) != ['MaterialInstanceConstant', 'MaterialInstanceConstant', 'StaticMesh', 'StaticMesh']
            or {r['source_role'] for r in observed['items']} != set(h.NAMES)
            or {r[k] for r in observed['items'] for k in ('mesh', 'material')} != set(paths)):
        raise RuntimeError('complete exact four-role/geometry/PBR reconciliation required')
    for path in paths:
        if d._asset_file(path).exists():
            raise RuntimeError('an original output is already saved; no first-save replay')
    d.protect(d.load(value['baseline']['path']))
    return value, native, dispatch, proof, sorted(paths), old_source


def custody(args, claim):
    d._lease(); h.resources(args)
    if not d.same_compute_lease(d.locks().get('compute', {}), claim):
        raise RuntimeError('exact selected compute claim required; no implicit renewal/replacement')
    if time.time() > claim['at'] + claim['ttl'] - 120:
        raise RuntimeError('selected compute deadline reserve reached; do not dispatch recovery')


def selected_claim(old_dispatch, transition_pin=None):
    if transition_pin is None:
        raise ValueError('R5 requires an explicit fresh bounded claim-transition receipt')
    d._check(transition_pin)
    transition = d.load(transition_pin['path'])
    previous = old_dispatch['compute_claim']['lock']
    for key, path, expected in (
            ('terminal_proof', FOURTH_PREDECESSOR / 'native.json', FOURTH_PREDECESSOR_FILES['native.json']),
            ('terminal_closeout', FOURTH_PREDECESSOR / 'terminal-file-closeout.json', FOURTH_PREDECESSOR_FILES['terminal-file-closeout.json']),
            ('partial_qualification', QUALIFICATION / 'receipt.json', QUALIFICATION_FILE)):
        pin = transition[key]
        d._check(pin)
        if d.fp(pin) != expected or Path(pin['path']).resolve() != path.resolve():
            raise RuntimeError('exact R4 terminal/release and fresh partial qualification pins required')
    if (transition.get('schema') != 'daedalus.canal-water-recovery-r5-claim-transition.v1'
            or transition.get('previous_claim') != previous):
        raise RuntimeError('explicit R4-to-R5 fresh claim transition required; no blind renewal')
    closeout = d.load(FOURTH_PREDECESSOR / 'terminal-file-closeout.json')
    qualification = d.load(QUALIFICATION / 'receipt.json')
    releases = [closeout, qualification]
    # This phase was deliberately held for another owner's active compute turn.
    # Its retained terminal/release proof is required; waiting is not release.
    intervening_pin = transition.get('intervening_phase_release')
    if not isinstance(intervening_pin, dict):
        raise RuntimeError('actual intervening compute phase terminal/release receipt required')
    d._check(intervening_pin)
    intervening = d.load(intervening_pin['path'])
    if (intervening.get('schema') != 'daedalus.canal-water-intervening-phase-release.v1'
            or intervening.get('stage') != 'ACTUAL_INTERVENING_GRANT_TERMINAL_RELEASED'
            or intervening.get('holder') != 'buckwild-sol' or intervening.get('grant_id') != 32445
            or any(intervening.get(key) is not True for key in
                   ('producer_terminal_confirmed', 'owner_release_confirmed', 'operator_semantic_ack_verified'))
            or not isinstance(intervening.get('actualGETlocks_after'), dict)
            or 'compute' in intervening['actualGETlocks_after']):
        raise RuntimeError('actual full intervening grant terminal/release semantic witness required')
    terminal_pins = intervening.get('actual_terminal_receipt')
    if isinstance(terminal_pins, dict):terminal_pins = [terminal_pins]
    if not isinstance(terminal_pins, list) or not terminal_pins:
        raise RuntimeError('at least one retained actual full-grant terminal receipt required')
    for pin in terminal_pins:d._check(pin)
    terminal_message = intervening.get('actualhub_terminal_message', {})
    unlock = intervening.get('actualhub_unlock_message', {})
    if (terminal_message.get('from') != 'buckwild-sol'
            or type(terminal_message.get('id')) is not int or terminal_message['id'] <= 32445
            or not terminal_message.get('body', {}).get('text')
            or unlock.get('from') != 'buckwild-sol' or unlock.get('type') != 'unlock'
            or type(unlock.get('id')) is not int or unlock['id'] <= 32445
            or unlock.get('body', {}).get('name') != 'compute'
            or unlock['body'].get('forced') is not False):
        raise RuntimeError('actual owner full-grant terminal and nonforced compute unlock messages required')
    released_after = max([datetime.datetime.fromisoformat(row['utc']).timestamp() for row in releases]
                         + [datetime.datetime.fromisoformat(intervening['observed_utc']).timestamp()])
    fresh = transition.get('new_claim', {})
    lock = fresh.get('lock', {})
    if (fresh.get('ok') is not True or lock.get('holder') != d.OWNER
            or type(lock.get('at')) not in (int, float) or not math.isfinite(lock['at'])
            or lock['at'] <= max(previous['at'], released_after)
            or type(lock.get('ttl')) not in (int, float)
            or not math.isfinite(lock['ttl']) or not 0 < lock['ttl'] <= 600
            or not d.same_compute_lease(d.locks().get('compute', {}), lock)):
        raise RuntimeError('new exact bounded claim after all actual terminal/releases required')
    measured = transition.get('fresh_resources')
    if (not isinstance(measured, dict)
            or any(type(measured.get(key)) not in (int, float) or not math.isfinite(measured[key])
                   for key in ('available_physical', 'available_commit'))
            or measured.get('available_physical', 0) < 1024 * 1024 * 1024
            or measured.get('available_commit', 0) < 1536 * 1024 * 1024
            or not isinstance(measured.get('observed_utc'), str)
            or datetime.datetime.fromisoformat(measured['observed_utc']).timestamp() <= released_after):
        raise RuntimeError('fresh transition resource-floor witness after all releases required')
    return fresh


def scene(value, args, claim, paths):
    """Existing labelled read-only route admits only the explicitly known dirty files."""
    cfg = h.configuration(value, args, claim)
    code = d.module_code(value) + '\nimport unreal\n' + _snap_definition() + '\n'
    code += 'cfg=' + repr(cfg) + '\nallowed=' + repr([path.split('.')[0] for path in paths]) + '\n'
    code += textwrap.dedent('''\
        def steps():
            result={'stage':'read_only_scene_started','native_mutations':0,'guard_waits':[]}
            try:
                packet,nodes,scopes=scope['_config'](cfg)
                guard=scopes['catalogue_source'];queue=scopes['queue_source']
                result['pre']=yield from queue['_preflight_steps'](guard,cfg,allowed,on_wait=result['guard_waits'].append)
                editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
                p,r=editor.get_level_viewport_camera_info()
                result['scene']={'world':editor.get_editor_world().get_path_name(),'actors':[snap(a) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('Codex')],'camera':{'location':{'x':p.x,'y':p.y,'z':p.z},'rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}}
                result['post']=yield from queue['_preflight_steps'](guard,cfg,allowed,on_wait=result['guard_waits'].append)
                result['stage']='read_only_scene_verified'
            except Exception as exc:
                result.update(stage='read_only_scene_failed',error=str(exc),error_type=type(exc).__name__)
                if 'queue' in locals():result['guard_diagnostic']=queue['_guard_snapshot']()
            return result
        ''')
    # run_steps can return {result: None, error: traceback}. Preserve the entire
    # envelope before obj() unwraps it; every attempt is exclusive and read-only.
    attempt = args.folder.parent / (args.folder.name + '-preparation-attempts') / str(time.time_ns())
    attempt.mkdir(parents=True)
    d.write_new(attempt / 'executed-code.json', code)
    d.write_new(attempt / 'dispatch.json', {'utc':d._utc(), 'stage':'read_only_scene_dispatch_pending',
        'source':d.pin(__file__), 'code':d.pin(attempt / 'executed-code.json'),
        'compute_claim':claim, 'native_mutations':0})
    try:
        raw = d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code,
            label=value['label'], budget_ms=1, timeout=60, side='Unreal')
    except Exception as exc:
        d.write_new(attempt / 'transport-error.json', {'utc':d._utc(),
            'error':str(exc), 'error_type':type(exc).__name__, 'outcome':'reconcile_before_retry'})
        raise
    d.write_new(attempt / 'raw-envelope.json', raw)
    result = d.wire.obj(raw, side='Unreal', what='Canal known-partial-dirty read-only scene preservation')
    if (result.get('stage') != 'read_only_scene_verified' or result.get('native_mutations') != 0
            or result.get('error') or len(result.get('scene', {}).get('actors', [])) != 143):
        raise RuntimeError('explicit exact143-actor scene witness required; no mutation')
    return result['scene']


def reviewed_sources(value, qualification):
    reviewed_native = d.pin(h.NATIVE)
    reviewed = h.constants()['PINS']
    old_keys = set(value['helpers'])
    if set(reviewed) != old_keys | {'queue_source'} or 'queue_source' in old_keys:
        raise RuntimeError('R5 admits exactly the original six helpers plus existing queue_source')
    locations = h.helper_paths(SimpleNamespace(subset_source=Path(value['helpers']['subset_source']['path'])))
    current = {key: d.pin(path) for key, path in locations.items()}
    if (set(current) != set(reviewed)
            or any(d.fp(pin) != reviewed[key] for key, pin in current.items())
            or reviewed_native != qualification['native_source']
            or current != qualification['helpers']):
        raise RuntimeError('current reviewed seven helpers/native differ from actual partial qualification')
    for pin in [reviewed_native, *current.values()]:
        d._check(pin)
    return reviewed_native, current


def prepare(args):
    if args.folder.resolve() != DEFAULT_FOLDER.resolve():
        raise ValueError('this revision admits only fresh RecoveryObservedAliasR5; never replay R1/R2/R3/R4')
    if args.folder.exists():
        raise RuntimeError('retained recovery folder exists; never overwrite/replay')
    value, native, dispatch, proof, paths, old_source = original()
    prior, prior_dispatch, prior_pins, qualification = fourth_predecessor(paths)
    if args.claim_transition is None or not args.claim_transition.is_absolute():
        raise ValueError('explicit absolute R5 new-claim transition receipt required')
    transition_pin = d.pin(args.claim_transition)
    selected = selected_claim(prior_dispatch, transition_pin)
    claim = selected['lock']; custody(args, claim)
    prepared = copy.deepcopy(value)
    reviewed_native, current_helpers = reviewed_sources(value, qualification)
    pins = [d.pin(ORIGINAL / name) for name in ('prepared.json', 'native.json', 'dispatch.json', 'naming-reconciliation.json')]
    pins.append(d.pin(old_source))
    pins.extend(archived_helpers(value).values())
    pins.extend(_evidence_pins(prior_pins))
    pins.extend([qualification['source'], qualification['native_source'], *qualification['helpers'].values()])
    pins.extend([transition_pin, d.load(transition_pin['path'])['intervening_phase_release']])
    delivery_source = d.pin(h.__file__)
    pins.append(delivery_source)
    expected_paths = sorted([*paths, WATER_OBJECT])
    prepared.update(native_source=reviewed_native, helpers=current_helpers,
        source_pins=[*prepared['source_pins'], *pins],
        recovery={'stage': 'observed_exact_water_partial_remaining_tail_only', 'original_folder': str(ORIGINAL),
                  'revision': 5, 'partial_predecessor': prior_pins,
                  'proof': d.pin(ORIGINAL / 'naming-reconciliation.json'), 'expected_paths': paths,
                  'expected_partial_paths': expected_paths, 'partial_qualification': prior_pins['qualification'],
                  'old_native_source': d.pin(old_source), 'original_compute_claim': dispatch['compute_claim'],
                  'released_partial_predecessor_compute_claim': prior_dispatch['compute_claim'],
                  'predecessor_claim_transition': prior['recovery']['claim_transition'],
                  'selected_compute_claim': selected, 'claim_transition': transition_pin,
                  'delivery_adapter_source': delivery_source,
                  'adapter_source': d.pin(__file__), 'imports_replayed': 0, 'replay_permitted': False})
    before = scene(prepared, args, claim, expected_paths)
    d._same_scene(before, d.load(value['baseline']['path'])['scene'])
    args.folder.mkdir(parents=True)
    d.write_new(args.folder / 'prepared.json', prepared)
    d.write_new(args.folder / 'dispatch.json', {'utc': d._utc(), 'stage': 'recovery_prepared_not_dispatched',
        'compute_claim': selected, 'prepared': d.pin(args.folder / 'prepared.json'),
        'original_native': d.pin(ORIGINAL / 'native.json'), 'read_only_proof': prepared['recovery']['proof'],
        'partial_qualification': prior_pins['qualification'], 'imports_replayed': 0, 'replay_permitted': False})
    print(json.dumps({'stage': 'remaining_tail_recovery_prepared', 'folder': str(args.folder)}, indent=2))


def native_parts(value):
    """Extract the frozen generator intent and no-import tail, changing one factory site."""
    source = Path(value['native_source']['path']).read_text(encoding='utf-8')
    tree = ast.parse(source)
    steps = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'steps')
    intent = next(node for node in steps.body if isinstance(node, ast.FunctionDef) and node.name == 'intent')
    block = next(node for node in steps.body if isinstance(node, ast.Try))
    start = next(i for i, node in enumerate(block.body) if isinstance(node, ast.For)
                 and isinstance(node.target, ast.Name) and node.target.id == 'source'
                 and isinstance(node.iter, ast.Name) and node.iter.id == 'nodes')
    selected = block.body[start:]
    if not isinstance(selected[-1], ast.Return):
        raise RuntimeError('pinned remaining tail must end in explicit native report return')
    lines = source.splitlines()
    tail = '\n'.join(textwrap.dedent('\n'.join(lines[node.lineno - 1:node.end_lineno])) for node in selected)
    callback = textwrap.dedent('\n'.join(lines[intent.lineno - 1:intent.end_lineno]))
    factory = "    parent, graph = yield from scopes['material_source']['build_parent'](_parent_path(source['name']), definition, intent)"
    replacement = """    if source['name'] == 'Octet_Winter_4_Canal_Stream1':
        existing = helper['_assets']()
        if set(existing) != set(expected_paths):raise RuntimeError('Water resume requires fresh exact five-object inventory')
        water_path = _parent_path(source['name'])
        water_object = water_path + '.' + water_path.rsplit('/', 1)[1]
        if water_object not in existing:raise RuntimeError('qualified existing Water parent missing')
        parent, graph = yield from scopes['material_source']['resume_parent'](existing[water_object], definition, intent, existing)
        report['resumed_water_parent'] = graph
        helper['_write'](journal, report)
    else:
        if source['name'] != 'Octet_Winter_4_Canal_Stream1_Core':raise RuntimeError('unexpected recovery role')
        parent, graph = yield from scopes['material_source']['build_parent'](_parent_path(source['name']), definition, intent)"""
    if tail.count(factory) != 1:
        raise RuntimeError('exact single reviewed parent-factory callsite required')
    tail = tail.replace(factory, replacement, 1)
    if (any(token in tail for token in ('AssetImportTask', 'import_asset_tasks', 'preflight(cfg)', 'set_nanite_settings'))
            or "yield from scopes['queue_source']['_preflight_steps']" not in callback):
        raise RuntimeError('recovery tail/callback contains forbidden or unsupported path')
    return callback, tail


PREFIX = r'''
packet,nodes,scopes=_config(cfg)
helper=scopes['sunspool_source'];guard=scopes['catalogue_source'];journal=Path(cfg['journal'])
guard['_deadline'](cfg);prefix_waits=[]
def initial_wait(row):prefix_waits.append(row)
initial=yield from scopes['queue_source']['_preflight_steps'](guard,cfg,[p.split('.')[0] for p in expected_paths],on_wait=initial_wait)
_pin(proof_pin['path'],_fp(proof_pin))
proof=json.loads(Path(proof_pin['path']).read_text(encoding='utf-8'))
if proof['stage']!='exact_four_unsaved_alias_geometry_raw_pbr_reconciled' or proof['native_mutations']!=0:raise RuntimeError('exact read-only source proof changed')
for file in expected_files:
 if Path(file).exists():raise RuntimeError('prior saved output found; preserve instead of replay')
geometry_report,objects=_inspect(cfg,nodes,scopes,partial=True)
if set(objects)!=set(expected_paths) or len(objects)!=5:raise RuntimeError('exact known five existing unsaved objects required')
partial=geometry_report.get('partial_parent',{})
if partial.get('stage')!='exact_r4_water_four_node_partial_verified' or partial.get('issues')!=[] or partial.get('saved') is not False or partial.get('bindings_completed')!=0:raise RuntimeError('fresh closed Water4-node proof required')
for row in proof['native']['items']:
 mic=objects[row['material']]
 vectors={str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(mic)}
 scalars={str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mic)}
 for name,wanted in row['native_values'].items():
  if isinstance(wanted,list):
   if name not in vectors:raise RuntimeError('raw vector parameter presence changed')
   v=unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mic,name)
   actual=[float(getattr(v,k)) for k in ('r','g','b','a')]
   if len(wanted)!=4 or any(not math.isfinite(a) or abs(a-b)>.0001 for a,b in zip(actual,wanted)):raise RuntimeError('raw imported RGBA/emission changed')
  else:
   if name not in scalars:raise RuntimeError('raw scalar parameter presence changed')
   actual=float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mic,name))
   if not math.isfinite(actual) or abs(actual-wanted)>.0001:raise RuntimeError('raw imported scalar changed')
if journal.exists() or journal.with_name(journal.name+'.write-pending').exists():raise RuntimeError('retained recovery journal forbids replay')
imported_paths=sorted(row['path'] for row in proof['native']['assets'])
report={'schema':'daedalus.canal-water-existing-five-water-partial-recovery.v1','utc':_utc(),'stage':'remaining_parent_tail_dispatch_pending','outputs':[],'completed_count':0,'save_return':None,'mutation_intents':[],'world_placed':0,'world_saved':False,'replay_permitted':False,'imports_replayed':0,'imported_object_paths':imported_paths,'before_parent_creation':geometry_report,'read_only_proof':proof_pin,'guard_waits':prefix_waits}
with journal.open('x',encoding='utf-8',newline='\n') as f:helper['_flush'](f,report)
'''


def run(args):
    if args.folder.resolve() != DEFAULT_FOLDER.resolve():
        raise ValueError('this revision cannot dispatch R1/R2/R3/R4 or alternative recovery folders')
    value = h.prepared(args); recovery = value['recovery']; d._check(recovery['adapter_source'])
    if d.pin(h.__file__) != recovery.get('delivery_adapter_source'):
        raise RuntimeError('prepared delivery adapter source changed')
    original_value, failed, old_dispatch, proof, paths, old_source = original()
    prior, prior_dispatch, prior_pins, qualification = fourth_predecessor(paths)
    expected_paths = sorted([*paths, WATER_OBJECT])
    if (recovery.get('revision') != 5 or recovery.get('partial_predecessor') != prior_pins
            or recovery.get('expected_paths') != paths
            or recovery.get('expected_partial_paths') != expected_paths
            or recovery.get('partial_qualification') != prior_pins['qualification']):
        raise RuntimeError('exact pinned R4 partial chain and fresh qualification required')
    reviewed_native, current_helpers = reviewed_sources(original_value, qualification)
    if value['native_source'] != reviewed_native or value['helpers'] != current_helpers:
        raise RuntimeError('prepared reviewed native/helper sources changed')
    dispatch = d.load(args.folder / 'dispatch.json')
    if dispatch.get('stage') != 'recovery_prepared_not_dispatched' or (args.folder / 'native.json').exists():
        raise RuntimeError('retained recovery dispatch/outcome forbids replay')
    transition_pin = recovery.get('claim_transition')
    if args.claim_transition is not None and (transition_pin is None
            or args.claim_transition.resolve() != Path(transition_pin['path']).resolve()):
        raise RuntimeError('prepared claim transition cannot be replaced')
    selected = selected_claim(prior_dispatch, transition_pin)
    claim = selected['lock']
    if (dispatch['compute_claim'] != selected or recovery['selected_compute_claim'] != selected
            or recovery.get('released_partial_predecessor_compute_claim') != prior_dispatch['compute_claim']
            or recovery.get('predecessor_claim_transition') != prior['recovery']['claim_transition']
            or recovery['original_compute_claim'] != old_dispatch['compute_claim']):
        raise RuntimeError('exact selected/original/released claim provenance changed')
    custody(args, claim)
    base = d.load(value['baseline']['path']); d.protect(base)
    before = scene(value, args, claim, expected_paths); d._same_scene(before, base['scene'])
    cfg = h.configuration(value, args, claim)
    callback, tail = native_parts(value)
    body = 'def _recover_steps(cfg,expected_paths,expected_files,proof_pin):\n'
    body += textwrap.indent(textwrap.dedent(PREFIX).strip() + '\n', '    ')
    body += textwrap.indent(callback + '\n', '    ')
    body += '    try:\n' + textwrap.indent(tail + '\n', '        ')
    body += "    except Exception as exc:\n        report.update(stage='halted_preserve_partial',error=str(exc),error_type=type(exc).__name__,failure_utc=_utc(),guard_diagnostic=getattr(exc,'codex_guard_diagnostics',None))\n        if not journal.with_name(journal.name+'.write-pending').exists():helper['_write'](journal,report)\n        raise\n"
    ast.parse(body)
    code = d.module_code(value) + '\nexec(compile(' + repr(body) + ",'<pinned-canal-water-partial-remaining-tail-recovery>','exec'),scope)\n"
    code += '\ndef steps():\n    return (yield from scope[\'_recover_steps\'](' + repr(cfg) + ',' + repr(expected_paths) + ','
    final_paths = sorted([*expected_paths, WATER_OBJECT.replace('_Water_', '_Foam_')])
    code += repr([str(d._asset_file(path)) for path in final_paths]) + ',' + repr(recovery['proof']) + '))\n'
    dispatch.update(stage='remaining_tail_native_dispatch_pending', resources=h.resources(args),
                    code_sha256=hashlib.sha256(code.encode()).hexdigest(), imports_replayed=0)
    d._write(args.folder / 'dispatch.json', dispatch)
    d.write_new(args.folder / 'recovery-executed-code.py', code)
    try:
        reply = d.wire.obj(d.wire.call(d.wire.UNREAL, 'daedalus.steps', code=code, label=value['label'],
            budget_ms=1, timeout=180, side='Unreal'), side='Unreal', what='Canal exact existing-five Water-partial remaining tail recovery')
        d.write_new(args.folder / 'reply.json', reply)
        if not isinstance(reply, dict):
            raise RuntimeError('null/unsupported recovery response; inspect journal, never retry')
        native = d.load(args.folder / 'native.json'); rows = native.get('outputs', [])
        if (native.get('stage') != h.SAVED or native.get('save_return') is not True
                or native.get('completed_count') != 6 or len(rows) != 6
                or any(row.get('save_return') is not True for row in rows)):
            raise RuntimeError('all six exact first saves not confirmed; preserve partial state')
        h.validate_native(native['final_observed'], [row['path'] for row in rows], value)
        for row in rows:
            d.fingerprint(d._asset_file(row['path']))
        d.protect(base)
        dispatch.update(stage='canal_existing_four_recovery_six_first_saves_complete', native=d.pin(args.folder / 'native.json'))
        d._write(args.folder / 'dispatch.json', dispatch)
        print(json.dumps({'stage': h.SAVED, 'completed_count': 6, 'imports_replayed': 0}, indent=2))
    except Exception as error:
        dispatch.update(stage='hold_reconcile_outcome_never_replay', error=str(error), error_type=type(error).__name__)
        d._write(args.folder / 'dispatch.json', dispatch)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--folder', type=Path, default=DEFAULT_FOLDER)
    parser.add_argument('--claim-transition', type=Path,
                        help='Explicit terminal/unlock/fresh bounded claim receipt; prepare pins it immutably.')
    parser.add_argument('--minimum-free-physical-mib', type=float, default=1024)
    parser.add_argument('--minimum-free-commit-mib', type=float, default=1536)
    args = parser.parse_args()
    if (not args.folder.is_absolute() or any(not math.isfinite(v) for v in
            (args.minimum_free_physical_mib, args.minimum_free_commit_mib))
            or args.minimum_free_physical_mib < 1024 or args.minimum_free_commit_mib < 1536):
        parser.error('absolute fresh folder and unchanged resource floors required')
    globals()[args.phase](args)
