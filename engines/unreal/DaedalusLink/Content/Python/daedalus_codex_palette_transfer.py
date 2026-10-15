# SPDX-License-Identifier: MIT
"""Producer-specific palette inverse; caller owns admission, saving and bindings.

Only voxel_island's PAL**(1/2.2) export is supported. This is not a universal
sRGB decoder or a lighting/BAR fix. Existing compatible materials are inspected
and reused without mutation; fresh creation returns an UNSAVED material.
"""
import json
import os
from pathlib import Path
import re
import time
import unreal

ROOT = '/Game/Daedalus/Art/Islands/CodexContest/Materials/'
PRODUCER = 'voxel_island_q_pow_1_over_2_2_v1'
METADATA = {'codex_owner': 'codex-contest', 'codex_palette_transfer':
            'ProducerPAL^(1/2.2) -> owned Power2.2 -> linear BaseColor; only new plant component overrides'}


def _destination(cfg):
    path = cfg['destination']
    if (cfg.get('producer') != PRODUCER or not isinstance(path, str) or not path.startswith(ROOT)
            or path.endswith('/') or '..' in path or re.fullmatch(r'/[A-Za-z0-9_/]+', path) is None):
        raise ValueError('explicit supported producer and owned material destination required')
    return path, path.rsplit('/', 1)[1]


def _write(path, value):
    pending = path.with_name(path.name + '.write-pending')
    with pending.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2); output.write('\n'); output.flush(); os.fsync(output.fileno())
    os.replace(pending, path)


def inspect(cfg):
    """Read only: exact three-node graph, default RGB output and proven metadata."""
    path, name = _destination(cfg)
    eal, mel = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
    material = unreal.find_object(None, path + '.' + name)
    if material is None and eal.does_asset_exist(path):
        material = eal.load_asset(path)
    if material is None:
        return {'stage': 'destination_absent', 'destination': path, 'mutations': 0}
    if not isinstance(material, unreal.Material) or material.get_path_name() != path + '.' + name:
        raise RuntimeError('existing destination is not the exact owned Material; preserve it')
    nodes = [node for node in unreal.ObjectIterator(unreal.MaterialExpression) if node.get_outer() == material]
    kinds = {node.get_class().get_name(): node for node in nodes}
    if len(nodes) != 3 or set(kinds) != {'MaterialExpressionVertexColor', 'MaterialExpressionPower', 'MaterialExpressionConstant'}:
        raise RuntimeError('unexpected existing material graph; never repair/replace automatically')
    vc, power, rough = (kinds[k] for k in ('MaterialExpressionVertexColor', 'MaterialExpressionPower', 'MaterialExpressionConstant'))
    inputs = list(mel.get_inputs_for_material_expression(material, power))
    if (inputs != [vc, None] or abs(power.get_editor_property('const_exponent') - 2.2) > 1e-5
            or abs(rough.get_editor_property('r') - .9) > 1e-5
            or mel.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR) != power
            or mel.get_material_property_input_node(material, unreal.MaterialProperty.MP_ROUGHNESS) != rough):
        raise RuntimeError('existing material transfer/roughness links differ')
    # VertexColor's first RGB output is UNNAMED. Named R/G/B/A must not pass.
    output = mel.get_input_node_output_name_for_material_expression(power, vc)
    # Installed UE5.8 Python returns str-or-None here, not a success/name tuple.
    if output != '':
        raise RuntimeError('default VertexColor RGB output could not be verified; no mutation')
    metadata = {key: eal.get_metadata_tag(material, key) for key in METADATA}
    if metadata != METADATA:
        raise RuntimeError('existing material producer/owner metadata differs')
    return {'stage': 'existing_graph_metadata_compatible_readonly', 'material': material.get_path_name(),
            'producer': PRODUCER, 'power': 2.2, 'roughness': .9, 'metadata': metadata,
            'mutations': 0, 'recompiled': False, 'saved': False, 'compile_state_rechecked': False}


def create(cfg):
    """Create+compile once, never save. Caller must gate ownership/resources first.

    cfg: destination (asset package path), producer=PRODUCER, journal (new absolute
    JSON path whose parent exists). A retained journal/pending file forbids replay.
    No actor/component/world operation or asset-save operation exists here.
    """
    path, name = _destination(cfg)
    observation = inspect(cfg)
    if observation['stage'] != 'destination_absent':
        return observation  # Existing correct material reuse is entirely read-only.
    journal = Path(cfg['journal']); pending = journal.with_name(journal.name + '.write-pending')
    if (not journal.is_absolute() or journal.suffix.lower() != '.json' or not journal.parent.is_dir()
            or journal.exists() or pending.exists()):
        raise RuntimeError('new absolute journal required; inspect any retained outcome, never replay')
    report = {'schema': 'daedalus.producer-palette-transfer.v1', 'stage': 'admitted_not_created',
              'destination': path, 'producer': PRODUCER, 'intents': [], 'replay_permitted': False,
              'saved': False, 'bindings_performed': 0, 'compile_errors': None}
    with journal.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2); output.flush(); os.fsync(output.fileno())
    def intent(operation):
        report['stage'] = operation + '_dispatch_pending'
        report['intents'].append({'operation': operation, 'epoch': time.time()}); _write(journal, report)
    try:
        intent('create_owned_material')
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, path.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
        if not isinstance(material, unreal.Material) or material.get_path_name() != path + '.' + name:
            raise RuntimeError('exact fresh Material creation did not return expected object')
        report['material'] = material.get_path_name()
        mel, eal = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
        intent('create_three_graph_nodes')
        vc = mel.create_material_expression(material, unreal.MaterialExpressionVertexColor, -600, 0)
        power = mel.create_material_expression(material, unreal.MaterialExpressionPower, -300, 0)
        rough = mel.create_material_expression(material, unreal.MaterialExpressionConstant, -300, 200)
        if any(node is None for node in (vc, power, rough)):
            raise RuntimeError('owned graph node creation incomplete')
        intent('configure_connect_tag_owned_graph')
        power.set_editor_property('const_exponent', 2.2); rough.set_editor_property('r', .9)
        if not mel.connect_material_expressions(vc, '', power, 'Base'):
            raise RuntimeError('proven unnamed VertexColor RGB to Power Base connection failed')
        if not mel.connect_material_property(power, '', unreal.MaterialProperty.MP_BASE_COLOR):
            raise RuntimeError('Power to BaseColor connection failed')
        if not mel.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS):
            raise RuntimeError('constant roughness connection failed')
        for key, value in METADATA.items():
            eal.set_metadata_tag(material, key, value)
        report['graph_readback'] = inspect(cfg)
        intent('compile_owned_material')
        started = time.perf_counter(); errors = list(mel.recompile_material(material))
        report.update(compile_call_s=round(time.perf_counter() - started, 6), compile_errors=errors,
                      stage='compile_returned'); _write(journal, report)
        if errors:
            raise RuntimeError('owned material compile errors: ' + repr(errors))
        report.update(stage='owned_material_created_compiled_unsaved', caller_save_required=True)
        _write(journal, report)
        return report
    except Exception as exc:
        report.update(stage='halted_preserve_partial', error_type=type(exc).__name__, error=str(exc))
        if not pending.exists():
            _write(journal, report)
        raise
