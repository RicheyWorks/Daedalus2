# SPDX-License-Identifier: MIT
"""Qualify the delivered TidePen Residents source; no native or network calls.

Reuses the retained Blender binary FBX reader without bpy or worker threads.
The shared qualified-static receiver remains the sole import/save implementation.
Preparation never imports that receiver or claims native/placement acceptance.
"""
import argparse
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

PACKET = Path('C:/Users/730ri/projects/D2-build/engines/unreal/art/claude-lands/ocean-tidepen-r1')
NAME = 'TidePen_r1_Residents'
FBX_PIN = (22588, 'a82c0e1ee724138fabad7996a5b623a41a6f74c2a200ddfa4e405a404cd5b4bd')
GLB_PIN = (45920, 'a139bf338cb358f09be673963f05e05b4e158cbe03af5d98a2f8f15d0f4b2583')
LAYOUT_PIN = (7265, 'c0c171cbd73371a4d6f6342a8141a07fa69ed45f3cd96c1ab26106c4bc973314')
BASELINE_SHA = 'abe95ef34ccb75b2a2e757d29923558fb0b42655307aa592de9b4315c6e08b2e'
PARSER_PINS = {
    'parse_fbx.py': (11409, '8252e933c94934b2271b72b31045683fcb56ead4804ff1d8f3a851ae2dad6241'),
    'data_types.py': (1726, '24328144f5b60338b1b47cc47ff76e8aee5c97c89ca4a419482978bb961f18fa'),
}
DESTINATION = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/TidePenResidentsR1_a82c0e1ee724138f'
RECEIVER_BLOCKER = (
    'Existing daedalus_codex_qualified_static.py metadata path hardcodes '
    'claude_raw_unit100_build1_actor001_v1, actor0.01, and unscaled source delta as intended cm. '
    'Residents geometry is metres: actor1 and source delta x100 intended cm are required. '
    'Do not dispatch/save through that unchanged plant profile; use an explicitly reviewed '
    'bounded metre/actor1 adapter with matching native readback, preserving plant semantics.'
)


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def exact(path, expected):
    value = pin(path)
    if (value['bytes'], value['sha256']) != expected:
        raise ValueError('Pinned source differs: ' + str(path))
    return value


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def child(node, name):
    return next(row for row in node.elems if row.id == name)


def properties(node):
    return {row.props[0].decode(): [value.decode() if isinstance(value, bytes) else value for value in row.props[4:]]
            for row in child(node, b'Properties70').elems if row.id == b'P'}


def bounds(points):
    return {edge: [operation(row[i] for row in points) for i in range(3)]
            for edge, operation in [('min', min), ('max', max)]}


def reader(folder):
    """Load unchanged pinned parser; scheduling-only shim executes callbacks serially."""
    package_name = '_codex_tidepen_retained_fbx'
    package = types.ModuleType(package_name)
    package.__path__ = [str(folder)]
    sys.modules[package_name] = package
    scheduling = types.ModuleType(package_name + '.fbx_utils_threading')
    class SerialConsumer:
        @staticmethod
        def new_cpu_bound_cm(callback, **_kwargs):
            return nullcontext(callback)
    scheduling.MultiThreadedTaskConsumer = SerialConsumer
    sys.modules[scheduling.__name__] = scheduling
    for name in ('data_types', 'parse_fbx'):
        path = folder / (name + '.py')
        exact(path, PARSER_PINS[path.name])
        module = types.ModuleType(package_name + '.' + name)
        module.__file__, module.__package__ = str(path), package_name
        sys.modules[module.__name__] = module
        setattr(package, name, module)
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return package.parse_fbx


def inspect_fbx(path, parser):
    root, version = parser.parse(str(path))
    objects = child(root, b'Objects').elems
    counts = Counter(row.id.decode() for row in objects)
    meshes = [row for row in objects if row.id == b'Geometry' and row.props[2] == b'Mesh']
    models = [row for row in objects if row.id == b'Model' and row.props[2] == b'Mesh']
    materials = [row for row in objects if row.id == b'Material']
    if len(meshes) != 1 or len(models) != 1 or len(materials) != 1:
        raise ValueError('Exactly one source mesh, model and material required')
    forbidden = ('AnimationStack', 'AnimationLayer', 'AnimationCurve', 'AnimationCurveNode',
                 'Deformer', 'Texture', 'Video')
    if any(counts[key] for key in forbidden) or any(b'UCX_' in str(row.props).encode() for row in objects):
        raise ValueError('Static/no texture/no UCX source profile differs')
    mesh, model = meshes[0], models[0]
    coordinates = child(mesh, b'Vertices').props[0]
    points = list(zip(*[iter(coordinates)] * 3))
    if not points or len(points) * 3 != len(coordinates) or not all(math.isfinite(v) for p in points for v in p):
        raise ValueError('Finite complete source vertices required')
    indices = child(mesh, b'PolygonVertexIndex').props[0]
    polygons, start = [], 0
    for i, vertex in enumerate(indices):
        if vertex < 0:
            polygons.append(list(indices[start:i + 1]))
            start = i + 1
    if start != len(indices) or any(len(row) < 3 for row in polygons):
        raise ValueError('Complete polygon stream required')
    layers = [row for row in mesh.elems if row.id == b'LayerElementColor']
    if len(layers) != 1:
        raise ValueError('One source colour layer required')
    layer = layers[0]
    mapping = child(layer, b'MappingInformationType').props[0]
    reference = child(layer, b'ReferenceInformationType').props[0]
    if (mapping, reference) != (b'ByPolygonVertex', b'IndexToDirect'):
        raise ValueError('Retained flat indexed polygon-corner colour profile differs')
    raw_colours = child(layer, b'Colors').props[0]
    colours = list(zip(*[iter(raw_colours)] * 4))
    colour_indices = child(layer, b'ColorIndex').props[0]
    if len(colour_indices) != len(indices) or len(colours) * 4 != len(raw_colours):
        raise ValueError('Complete RGBA corner stream required')
    offset = 0
    for polygon in polygons:
        face = [colours[i] for i in colour_indices[offset:offset + len(polygon)]]
        if len(set(face)) != 1:
            raise ValueError('Source face colour is not flat')
        offset += len(polygon)
    palette = sorted(set(tuple(round(v * 255) for v in row) for row in colours))
    if len(palette) != 7 or any(row[3] != 255 for row in palette):
        raise ValueError('Exact seven-colour opaque source palette required')
    transform = properties(model)
    if transform.get('RotationOrder', [0]) != [0]:
        raise ValueError('Expected XYZ source model rotation order required')
    if (transform.get('Lcl Translation', [0., 0., 0.]) != [0., 0., 0.]
            or transform.get('Lcl Scaling', [1., 1., 1.]) != [1., 1., 1.]):
        raise ValueError('Source model translation/scale differs; no hidden recenter')
    rotation = transform.get('Lcl Rotation', [0., 0., 0.])
    if any(abs(v) > 1e-5 for v in rotation[:2]) or abs(rotation[2] - 180.) > 1e-4:
        raise ValueError('Expected source 180-degree Z model conversion differs')
    for key, expected in [('GeometricTranslation', [0., 0., 0.]),
                          ('GeometricRotation', [0., 0., 0.]), ('GeometricScaling', [1., 1., 1.]),
                          ('RotationPivot', [0., 0., 0.]), ('ScalingPivot', [0., 0., 0.]),
                          ('PreRotation', [0., 0., 0.]), ('PostRotation', [0., 0., 0.])]:
        if transform.get(key, expected) != expected:
            raise ValueError('Unsupported extra model transform: ' + key)
    angle = math.radians(rotation[2]); c, s = math.cos(angle), math.sin(angle)
    baked = [(c*x-s*y, s*x+c*y, z) for x, y, z in points]
    global_props = properties(child(root, b'GlobalSettings'))
    if global_props['UnitScaleFactor'] != [100.]:
        raise ValueError('Absolute source unit100 required')
    triangles = sum(len(row) - 2 for row in polygons)
    if version != 7400 or triangles != 650 or len(polygons) != 325:
        raise ValueError('Exact delivered mesh topology differs')
    return {'fbx_version': version, 'object_counts': dict(counts), 'control_points': len(points),
            'polygon_count': len(polygons), 'polygon_sizes': dict(Counter(map(len, polygons))),
            'triangles': triangles, 'all_source_faces_flat': True, 'rgba_bytes': palette,
            'raw_rgba_float': sorted(set(colours)), 'source_geometry_local_bounds': bounds(points),
            'model_transform_properties': transform, 'model_baked_bounds': bounds(baked),
            'source_global_properties': global_props, 'material_names': [row.props[1].decode().split('\x00')[0] for row in materials],
            'bounds_contract': 'item.source_bounds is exact geometry-local data. Existing receiver bakes model transform and accepts XY swaps/signs at x100, unchanged Z, <=0.1cm. This exact 180deg Z conversion fits that contract; actual native conversion still requires readback.',
            'required_future_actor_scale': [1., 1., 1.],
            'unit_explanation': 'Geometry is metres and FBX UnitScaleFactor100. Native raw vertices are x100 centimetres: actor scale1 preserves the 26.55x15.44x3 metre assembly. No individual recenter/rescale.'}


def png_binding(path, sidecar):
    raw = path.read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG evidence')
    retained, offset, removed = raw[:8], 8, []
    while offset < len(raw):
        size = struct.unpack_from('>I', raw, offset)[0]
        end = offset + size + 12
        if end > len(raw):
            raise ValueError('Incomplete PNG chunk')
        if raw[offset + 4:offset + 8] == b'caBX':
            removed.append({'offset': offset, 'total_bytes': size + 12})
        else:
            retained += raw[offset:end]
        offset = end
    expected = load(sidecar)
    actual = {'bytes': len(retained), 'sha256': hashlib.sha256(retained).hexdigest()}
    if len(removed) != 1 or actual != {key: expected[key] for key in actual}:
        raise ValueError('Only-caBX source-image binding failed')
    return {'actual_png': pin(path), 'sidecar': pin(sidecar), 'removed_in_memory_only': removed,
            'producer_original_pin': actual, 'exact_binding': True, 'files_modified': False}


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-root', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    task = args.task_root.resolve(); folder = task / 'native-ingestion/TidePenResidentsR1'
    audit_path, qualification_path = folder / 'source-audit.json', folder / 'qualification.json'
    if audit_path.exists() or qualification_path.exists():
        raise RuntimeError('Retained preparation exists; no overwrite or automatic rerun')
    fbx, glb, layout_path = PACKET / (NAME + '.fbx'), PACKET / (NAME + '.glb'), PACKET / 'TidePen_r1.layout.json'
    exact(fbx, FBX_PIN); exact(glb, GLB_PIN); exact(layout_path, LAYOUT_PIN)
    baseline = task / 'native-ingestion/Winter4CanalStream1CoreR2/PlacementR1/VisualPolishR1/saved-production-baseline.json'
    baseline_pin = pin(baseline)
    if baseline_pin['sha256'] != BASELINE_SHA:
        raise ValueError('Selected217/145/184 baseline changed')
    helper = task / 'native-ingestion/MarshFloweringDistinctR1/Source'
    measurement = inspect_fbx(fbx, reader(helper))
    views = [png_binding(PACKET / ('TidePen_r1.after.' + view + '.png'), PACKET / ('TidePen_r1.after.' + view + '.json')) for view in ('hero', 'detail', 'top')]
    layout = load(layout_path)
    item = {'name': NAME, 'fbx': str(fbx), 'fingerprint': {k: pin(fbx)[k] for k in ('bytes', 'sha256')},
            'sidecar': str(layout_path), 'sidecar_fingerprint': {k: pin(layout_path)[k] for k in ('bytes', 'sha256')},
            'triangles': 650, 'source_bounds': measurement['source_geometry_local_bounds'],
            'rgba_bytes': measurement['rgba_bytes'], 'source_unit_scale_factor': 100,
            'mesh_geometry_count': 1, 'mesh_model_count': 1, 'animations': 0, 'animation_curves': 0,
            'deformers': 0, 'textures': 0, 'videos': 0, 'authored_ucx': 0, 'destination': DESTINATION,
            'author': 'Team Claude; individual unknown',
            'provenance': {'team': 'Team Claude / unreal-team', 'individual_author': 'unknown',
                           'producer_handoff_id': 32536, 'owner_reported_source_commit': '94f8507e3',
                           'source_glb': pin(glb), 'layout': pin(layout_path),
                           'source_story': layout['story'], 'realm_intent': 'OCEAN design, not a native realm binding',
                           'frame': layout['frame'], 'source_audit': str(audit_path)},
            'source_dimensions_metres': [measurement['source_geometry_local_bounds']['max'][i] - measurement['source_geometry_local_bounds']['min'][i] for i in range(3)],
            'source_model_transform': measurement['model_transform_properties'],
            'required_future_actor_scale': [1., 1., 1.],
            'frame_limits': 'Four creatures remain one shared metre-frame role; no individual-small-prop assumption, pivot change, collision, animation or gameplay claim.'}
    utc = datetime.now(timezone.utc).isoformat()
    audit = {'schema': 'daedalus.tidepen-residents-source-audit.v1', 'utc': utc,
             'stage': 'source_measured_native_unexecuted', 'measurement': measurement,
             'source_fbx': pin(fbx), 'source_glb': pin(glb), 'layout': pin(layout_path), 'views': views,
             'selected_baseline': baseline_pin, 'parser': [pin(helper / name) for name in PARSER_PINS],
             'native_intake_profile_blocker': RECEIVER_BLOCKER,
             'parser_method': 'Unmodified pinned Blender FBX reader/data_types; serial scheduling-only callback shim; no bpy, subprocess, thread, native or network call.',
             'limits': 'Source facts only. Actual native palette/material/bounds/options/save readback and receiving placement remain separate. Existing M_VoxelVertexColour profile does not claim exact source roughness or two-sided PBR reproduction.'}
    folder.mkdir(parents=True, exist_ok=True)
    write_new(audit_path, audit)
    source_paths = [fbx, glb, layout_path, PACKET / 'TidePen_r1.showcase.json', audit_path, Path(__file__).resolve()]
    source_paths += [helper / name for name in PARSER_PINS]
    source_paths += [Path(row[key]['path']) for row in views for key in ('actual_png', 'sidecar')]
    shared_material = Path('C:/Unreal/DaedalusRealm/Content/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.uasset')
    if shared_material.is_file():
        source_paths.append(shared_material)
    qualification = {'schema': 'daedalus.tidepen-residents-qualified-source.v1',
                     'stage': 'qualified_static_candidates_source_only', 'utc': utc, 'items': [item],
                     'native_dispatch_eligible': False, 'native_intake_profile_blocker': RECEIVER_BLOCKER,
                     'source_pins': [pin(path) for path in source_paths],
                     'source_views_personally_inspected_by_operator': True,
                     'operator_view_acceptance': {'operator': 'codex-play-guard',
                         'basis': 'Direct parent report and instruction received during this preparation, approximately2026-10-15T23:53UTC; root personally inspected actual hero/detail/top with view_image.',
                         'observations': ['Turtle block body in central pen, crab in right pool, seahorse in left pool, red starfish offshore.',
                                          'Four combined residents share a26.55x15.44x3m frame; not a single animated creature.'],
                         'limits': 'Full-scene Blender renders only; no isolated detail of each resident, native appearance, collision or gameplay acceptance.'},
                     'source_views': views, 'selected_baseline': baseline_pin,
                     'limits': 'Producer delivered32536; source qualification only, no native claim/admission/save/placement. Keep other five TidePen roles and all original files unchanged.'}
    write_new(qualification_path, qualification)
    print(json.dumps({'source_audit': pin(audit_path), 'qualification': pin(qualification_path),
                      'operator_view_flag': True, 'native_dispatch_eligible': False,
                      'next': RECEIVER_BLOCKER}, indent=2))


if __name__ == '__main__':
    main()
