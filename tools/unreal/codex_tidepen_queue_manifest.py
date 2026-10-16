# SPDX-License-Identifier: MIT
"""Summarize the six retained TidePen roles and receiving seams, file-only.

No export, native import, bridge, network, subprocess or dependency installation.
An existing output is never replaced. Decoded GLB data is distinguished from
declared accessor bounds and from native receiving observations.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct

ROLES = ('Residents', 'CareStation', 'Landing', 'Pen', 'Habitat', 'Shelf')
COLLISION = ('UCX_', 'UBX_', 'USP_', 'UCP_')
FORMATS = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2),
           5125: ('I', 4), 5126: ('f', 4)}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def bounds(rows):
    return {key: [fn(row[i] for row in rows) for i in range(3)]
            for key, fn in [('min', min), ('max', max)]}


def glb(path):
    raw = path.read_bytes()
    if len(raw) > 2_000_000 or struct.unpack_from('<III', raw) != (0x46546C67, 2, len(raw)):
        raise ValueError('bounded GLB2 payload required')
    chunks, offset = {}, 12
    while offset < len(raw):
        length, kind = struct.unpack_from('<II', raw, offset); offset += 8
        if offset + length > len(raw) or kind in chunks:
            raise ValueError('invalid or duplicate GLB chunk')
        chunks[kind] = raw[offset:offset + length]; offset += length
    if offset != len(raw):
        raise ValueError('incomplete GLB')
    data, binary = json.loads(chunks[0x4E4F534A]), chunks.get(0x004E4942, b'')

    def accessor(index):
        a = data['accessors'][index]
        if a.get('sparse') or a['count'] > 200000 or a['type'] not in WIDTHS:
            raise ValueError('unsupported bounded accessor')
        v = data['bufferViews'][a['bufferView']]
        if v.get('buffer', 0) != 0 or data['buffers'][0].get('uri'):
            raise ValueError('only retained embedded GLB buffer supported')
        fmt, size = FORMATS[a['componentType']]; width = WIDTHS[a['type']]
        stride = v.get('byteStride', size * width)
        start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        end = start + (a['count'] - 1) * stride + size * width
        if stride < size * width or end > v.get('byteOffset', 0) + v['byteLength'] or end > len(binary):
            raise ValueError('accessor exceeds retained buffer view')
        rows = [struct.unpack_from('<' + fmt * width, binary, start + i * stride) for i in range(a['count'])]
        if any(not math.isfinite(x) for row in rows for x in row):
            raise ValueError('nonfinite decoded accessor')
        return a, rows

    def transformed(point, node):
        if 'matrix' in node:
            m = node['matrix']
            return [sum(m[c * 4 + r] * point[c] for c in range(3)) + m[12 + r] for r in range(3)]
        t, s = node.get('translation', [0, 0, 0]), node.get('scale', [1, 1, 1])
        x, y, z, w = node.get('rotation', [0, 0, 0, 1])
        matrix = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
        return [sum(matrix[r][c] * s[c] * point[c] for c in range(3)) + t[r] for r in range(3)]

    nodes = data.get('nodes', [])
    parents = {}
    for i, n in enumerate(nodes):
        for child in n.get('children', []):
            if child in parents:
                raise ValueError('ambiguous node parent')
            parents[child] = i

    def world(point, index):
        visited = set()
        while True:
            if index in visited or len(visited) >= 64:
                raise ValueError('cyclic or excessive node hierarchy')
            visited.add(index); point = transformed(point, nodes[index])
            if index not in parents:
                return point
            index = parents[index]

    result, totals = [], Counter()
    for i, node in enumerate(nodes):
        if 'mesh' not in node:
            continue
        name = node.get('name', '')
        collision = name.startswith(COLLISION)
        primitives = []
        for p in data['meshes'][node['mesh']]['primitives']:
            a, points = accessor(p['attributes']['POSITION'])
            mode = p.get('mode', 4)
            count = len(accessor(p['indices'])[1]) if 'indices' in p else len(points)
            if mode != 4 or count % 3:
                raise ValueError('this manifest only counts complete triangle primitives')
            triangle_count = count // 3
            totals['collision_triangles' if collision else 'render_triangles'] += triangle_count
            colour = None
            if 'COLOR_0' in p['attributes']:
                c, colours = accessor(p['attributes']['COLOR_0'])
                colour = {'accessor': p['attributes']['COLOR_0'], 'count': c['count'],
                          'component_type': c['componentType'], 'type': c['type'],
                          'normalized': c.get('normalized', False), 'decoded_encoded_values_unique': len(set(colours)),
                          'normalization_applied': False}
            primitives.append({'material_index': p.get('material'), 'attributes': p['attributes'],
                               'triangles_decoded_from_index_count': triangle_count,
                               'position_count_decoded': len(points),
                               'position_bounds_declared': {k: a.get(k) for k in ('min', 'max')},
                               'position_bounds_decoded_local': bounds(points),
                               'position_bounds_decoded_node_world': bounds([world(point, i) for point in points]),
                               'COLOR_0': colour})
        result.append({'node_index': i, 'name': name, 'mesh_name': data['meshes'][node['mesh']].get('name'),
                       'classification': 'authored_collision_proxy' if collision else 'render',
                       'authored_transform_fields': {k: node[k] for k in ('translation', 'rotation', 'scale', 'matrix') if k in node},
                       'omitted_TRS_defaults': 'translation0, quaternion identity, scale1 under glTF2 semantics',
                       'primitives': primitives})
    return {'coordinate_system': 'glTF Y-up metres; not native transform/pivot acceptance',
            'scene_roots': data.get('scenes', [])[data.get('scene', 0)].get('nodes', []),
            'nodes': result, 'triangle_totals_decoded': dict(totals), 'materials': data.get('materials', []),
            'extensions_used': data.get('extensionsUsed', []), 'extensions_required': data.get('extensionsRequired', []),
            'images': len(data.get('images', [])), 'textures': len(data.get('textures', [])),
            'pivots': 'node origin/TRS retained; no native pivot, recenter or world assignment inferred'}


def fbx_summary(path, parser, prep):
    tree, version = parser.parse(str(path))
    objects = prep['child'](tree, b'Objects').elems
    geometries, models = [], []
    for row in objects:
        if row.id not in (b'Geometry', b'Model') or row.props[2] != b'Mesh':
            continue
        name = row.props[1].decode().split('\x00')[0]
        value = {'name': name, 'classification': 'authored_collision_proxy' if name.startswith(COLLISION) else 'render'}
        if row.id == b'Model':
            value['authored_transform_and_pivot_properties'] = prep['properties'](row)
            models.append(value)
        else:
            xyz = prep['child'](row, b'Vertices').props[0]
            points = list(zip(*[iter(xyz)] * 3))
            indices = prep['child'](row, b'PolygonVertexIndex').props[0]
            sizes, count = [], 0
            for index in indices:
                count += 1
                if index < 0:
                    sizes.append(count); count = 0
            if count or any(n < 3 for n in sizes):
                raise ValueError('incomplete FBX polygons')
            value.update(control_points=len(points), geometry_local_bounds_decoded=bounds(points),
                         triangles_decoded=sum(n - 2 for n in sizes), polygon_sizes=dict(Counter(sizes)))
            geometries.append(value)
    return {'version': version, 'object_counts': dict(Counter(row.id.decode() for row in objects)),
            'geometry': geometries, 'models': models,
            'global_properties': prep['properties'](prep['child'](tree, b'GlobalSettings')),
            'limits': 'Source object properties/local geometry only; no FBX transform bake or native collision acceptance inferred'}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--task-root', type=Path, default=Path(__file__).resolve().parents[3])
    args = cli.parse_args(); task = args.task_root.resolve()
    output = task / 'native-ingestion/TidePenResidentsR1/next-intake-manifest.json'
    if output.exists():
        raise RuntimeError('retained manifest exists; no overwrite')
    source = Path(__file__).with_name('codex_tidepen_residents_prepare.py')
    prep = {'__name__': '_codex_tidepen_queue_retained_preparation', '__file__': str(source)}
    exec(compile(source.read_bytes(), str(source), 'exec'), prep)
    pin, packet = prep['pin'], prep['PACKET']
    layout_path, showcase_path = packet / 'TidePen_r1.layout.json', packet / 'TidePen_r1.showcase.json'
    prep['exact'](layout_path, prep['LAYOUT_PIN'])
    layout = load(layout_path)
    parser = prep['reader'](task / 'native-ingestion/MarshFloweringDistinctR1/Source')
    seams = {
        'Residents': ['Already imported/saved once; do not replay. Appearance, placement and creature/gameplay acceptance remain unverified.'],
        'CareStation': ['Closed7-slot rawPBR plus COLOR_0 multiplication proof for actual imported MI/parent graph.',
                        'KHR_materials_emissive_strength2.55: installed importer supports scalar; existing subset producer rejects extensions.',
                        'Preserve authored translated root; require metre/build1/actor1 and exact output/slot readback.'],
        'Landing': ['3130 visible triangles exceeds existing3000-triangle qualified profile; no arbitrary limit increase.',
                    'Closed multi-slot receiver with two authored UCX proxies excluded from visible output; preserve proxy bytes/names.',
                    'Retain translated root/pivot and qualify collision separately; current no-UCX single-static profile does not admit it.'],
        'Pen': ['Producer HOLD for later assembly intake.', '15188 triangles plus4 rawPBR slots/KHRstrength require bounded reviewed receiving scope.'],
        'Habitat': ['Producer HOLD for later assembly intake.', '11496 triangles exceeds current qualified-static budget; do not raise limits arbitrarily.'],
        'Shelf': ['Producer HOLD for later island-base intake.', 'Mixed OPAQUE/BLEND rawPBR and COLOR_0, two distinct water alpha factors, authored UCX proxy.',
                  'Requires closed mixed-alpha/material and collision-exclusion contract; current opaque profile is incompatible.'],
    }
    roles, payloads = [], []
    for role in ROLES:
        stem = 'TidePen_r1_' + role
        files = {suffix: pin(packet / (stem + '.' + suffix)) for suffix in ('glb', 'fbx')}
        for entry in files.values():
            if [entry['bytes'], entry['sha256']] != layout['hashes'][Path(entry['path']).name]:
                raise ValueError('payload differs from exact layout pin')
            payloads.append(entry)
        roles.append({'role': role, 'payloads': files, 'all_payload_pins_match_layout': True,
                      'layout_declared_role': layout.get('roles', {}).get(role),
                      'producer_release': 'released_asset_only_owned_namespace' if role in ('Residents', 'CareStation', 'Landing') else 'HOLD_later_intake',
                      'producer_release_hub_id': 32582, 'source_candidate_profile_ready': role == 'Residents',
                      'receiving_stage': 'saved_native_asset_world_held' if role == 'Residents' else 'candidate_not_native_admitted',
                      'blockers_or_limits': seams[role], 'glb': glb(Path(files['glb']['path'])),
                      'fbx': fbx_summary(Path(files['fbx']['path']), parser, prep)})
    folder = task / 'native-ingestion/TidePenResidentsR1/DeliveryR1'
    readback_path = folder / 'readback.json'; readback = load(readback_path)
    native = load(folder / 'native.json')
    if (readback['issues'] or readback['stage'] != 'qualified_static_assets_saved_readback_complete'
            or native['save_return'] is not True or native['completed_count'] != 1):
        raise ValueError('actual Residents saved receipt required')
    observed = readback['native_readback']['items'][0]
    saved = {'readback_receipt': pin(readback_path), 'native_journal': pin(folder / 'native.json'),
             'stage': readback['stage'], 'save_return': native['save_return'], 'asset': observed,
             'outputs': readback['outputs'], 'baseline': readback['baseline'],
             'map': readback['map'], 'scene_actor_count': len(readback['scene']['actors']),
             'total_tracked_packages': readback['total_tracked_packages'],
             'source_files_preserved': readback['source_files_preserved'],
             'world_references': readback['native_readback']['world_references'],
             'world_placed': readback['world_placed'], 'world_saved': readback['world_saved'],
             'limits': readback['limits']}
    hub_path = Path('C:/Users/730ri/projects/bot-team/link/log.jsonl')
    messages = []
    with hub_path.open(encoding='utf-8') as lines:
        for line in lines:
            row = json.loads(line)
            if row.get('id') in (32573, 32581, 32582):
                messages.append(row)
    engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
    capabilities = [
        ('Plugins/Interchange/Runtime/Source/Parsers/GLTFCore/Private/GLTF/ExtensionsHandler.cpp', '404-411', 'Parses KHR_materials_emissive_strength.'),
        ('Plugins/Interchange/Runtime/Source/Import/Private/Gltf/InterchangeGLTFMaterial.cpp', '483-490', 'Emits EmissiveFactor and EmissiveStrength typed parameters.'),
        ('Plugins/Interchange/Runtime/Source/Pipelines/Private/InterchangeglTFPipeline.cpp', '303-407', 'Selects existing glTF parent and transfers typed MI parameters; actual parent graph still requires readback.'),
        ('Plugins/Interchange/Runtime/Source/Import/Private/Gltf/InterchangeGltfTranslator.cpp', '758-768', 'Computed bUseVertexColor is not forwarded by this material call; no proven vertex multiplication topology.'),
        ('Source/Editor/MaterialEditor/Private/MaterialEditingLibrary.cpp', '1585-1593;1899-1912', 'Enumerate static-switch names first: value getter returns false for both absent and disabled.'),
    ]
    value = {'schema': 'daedalus.tidepen-next-intake-manifest.v1', 'utc': datetime.now(timezone.utc).isoformat(),
             'stage': 'file_only_next_intake_handoff_native_not_dispatched', 'generator_source': pin(__file__),
             'reused_preparation_source': pin(source), 'layout': pin(layout_path), 'showcase': pin(showcase_path),
             'frame_declared': layout['frame'], 'source_provenance': layout['provenance'],
             'payload_pin_count': len(payloads), 'all12_payload_pins_match_layout': True,
             'roles': roles, 'residents_saved_native_scope': saved,
             'source_views': [prep['png_binding'](packet / ('TidePen_r1.after.' + v + '.png'), packet / ('TidePen_r1.after.' + v + '.json')) for v in ('hero', 'detail', 'top')],
             'retained_coordination_messages': messages,
             'installed_source_capabilities': [{'source': pin(engine / p), 'lines': lines, 'fact': fact} for p, lines, fact in capabilities],
             'other_held_work': {'Willow': '32573 quality failed/held;32581 reopen blocked before launch by resource floors, explicitly released, no successful reopen.',
                                 'R4': 'Separate candidate held: mixed alpha, six materials, nonzero root and local rotor pivot; not TidePen admission.'},
             'native_calls': 0, 'source_assets_modified': False, 'imports': 0, 'saves': 0,
             'limits': 'File-only inventory/capability handoff. Remaining five roles are not profile-ready or native-admitted. No new creature actors, world placement, collision/gameplay, native appearance or measured production speed claim. No profile limit/global renderer setting changes requested.'}
    with output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, allow_nan=False); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps(pin(output)))


if __name__ == '__main__':
    main()
