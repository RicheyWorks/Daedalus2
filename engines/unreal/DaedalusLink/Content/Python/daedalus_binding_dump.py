# SPDX-License-Identifier: MIT
"""Read-only editor capture for tools/realms/check_bindings.py. No scan, load, save or rebind."""
import datetime
import unreal

ROOT = '/Game/Daedalus/Art/Cast'


def capture():
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if subsystem.get_game_world() is not None:
        raise RuntimeError('Binding dump requires editor idle, not PIE')
    world = subsystem.get_editor_world()
    if world is None:
        raise RuntimeError('Editor world unavailable')
    assets = []
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    for asset in registry.get_assets_by_path(ROOT, recursive=True):
        assets.append({'path': str(asset.package_name)+'.'+str(asset.asset_name),
                       'class': str(asset.asset_class_path.asset_name)})
    roles, errors = [], []
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        if not isinstance(actor, unreal.DaedalusTalker):
            continue
        path = actor.get_path_name()
        try:
            figure = actor.get_editor_property('figure')
            mesh = figure.get_editor_property('skeletal_mesh_asset') if figure else None
            roles.append({'path': path, 'cast': actor.get_editor_property('cast'),
                          'who': actor.get_editor_property('who'),
                          'candidate_ids': list(actor.art_ids()),
                          'art_found': actor.get_editor_property('art_found'),
                          'has_art': actor.get_editor_property('has_art'),
                          'mesh': mesh.get_path_name() if mesh else None})
        except Exception as exc:
            errors.append({'path': path, 'error': str(exc)})
    if subsystem.get_game_world() is not None or subsystem.get_editor_world() != world:
        raise RuntimeError('World changed during binding capture')
    return {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'world_path': world.get_path_name(), 'loaded_only': True, 'atomic': False,
            'registry_root': ROOT, 'roles': sorted(roles, key=lambda row: row['path']),
            'assets': sorted(assets, key=lambda row: row['path']), 'errors': errors}
