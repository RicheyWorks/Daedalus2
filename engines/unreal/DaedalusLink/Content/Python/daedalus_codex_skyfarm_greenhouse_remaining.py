# SPDX-License-Identifier: MIT
"""Remaining-only receiver for the observed base-Material greenhouse import.

The original import profile/journal stay frozen. This adapter has no importer,
factory, reimport, delete or replacement operation. It qualifies the existing
closed glTF function graph before metadata and thirteen unattempted first saves.
"""
import ast
import hashlib
import json
from pathlib import Path
import time


def install(profile,cfg):
    import unreal
    original_setup=profile['setup']
    scope={'__name__':'_codex_skyfarm_direct_material','__file__':cfg['direct_receiver']['path']}
    raw=profile['pin'](cfg['direct_receiver']['path'],cfg['direct_receiver']['sha256'])
    exec(compile(raw,cfg['direct_receiver']['path'],'exec'),scope)
    graph={'__name__':'_codex_skyfarm_graph_defaults','__file__':cfg['graph_helper']['path']}
    raw=profile['pin'](cfg['graph_helper']['path'],cfg['graph_helper']['sha256'])
    exec(compile(raw,cfg['graph_helper']['path'],'exec'),graph)
    graph['WITNESS_DIRECTORY']=cfg['graph_witness_directory']
    def setup(current):
        packet,scopes=original_setup(current)
        scopes['geometry']['_material']=lambda material,source,miri,helper:scope['qualify'](material,source,graph)
        return packet,scopes
    profile['setup']=setup
    # Retain the original exact partition, geometry, slots, source and metadata
    # checks; change only the observed material class to its actual base class.
    tree=ast.parse(Path(profile['__file__']).read_text(encoding='utf-8'))
    inspect=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
    class ActualMaterial(ast.NodeTransformer):
        def visit_Attribute(self,node):
            node=self.generic_visit(node)
            if isinstance(node.value,ast.Name) and node.value.id=='unreal' and node.attr=='MaterialInstanceConstant':node.attr='Material'
            return node
        def visit_Constant(self,node):
            if isinstance(node.value,str):node.value=node.value.replace('MIC','base Material')
            return node
    inspect=ActualMaterial().visit(inspect)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[inspect],type_ignores=[])),profile['__file__']+':actual-base-Material','exec'),profile)
    profile['remaining_steps']=lambda current:remaining(profile,current)
    return profile


def remaining(p,cfg):
    import unreal
    packet,scopes=p['setup'](cfg);helper=scopes['sunspool'];guard=scopes['catalogue']
    original=json.loads(p['pin'](cfg['original_asset_journal']['path'],cfg['original_asset_journal']['sha256']))
    if (original.get('stage')!='halted_preserve_partial' or original.get('error')!='actual inventory must account for all8 meshes and7 MICs'
            or original.get('saves')!=[] or len(original['intents'])!=1
            or original['intents'][0]['operation']!='import_exact_original_greenhouse_glb'
            or len(original['imported_object_paths'])!=15):
        raise RuntimeError('exact known terminal one-import/zero-save boundary required')
    journal=Path(cfg['journal'])
    if journal.exists():raise RuntimeError('retained remaining-only journal; no replay')
    objects=helper['_assets']()
    if set(objects)!=set(original['imported_object_paths']) or any(p['_file'](o,cfg).exists() for o in objects.values()):
        raise RuntimeError('exact retained unsaved fifteen-object import required')
    report={'stage':'REMAINING_ONLY_ADMITTED','original_import_journal':cfg['original_asset_journal'],
        'imported_object_paths':original['imported_object_paths'],'import_seconds':original['import_seconds'],
        'new_imports':0,'intents':[],'saves':[],'material_class':'Material','held_glass':'UNSAVED_UNPLACED'}
    with journal.open('x',encoding='utf-8') as stream:helper['_flush'](stream,report)
    def keep():helper['_write'](journal,report)
    def wait(row):report.setdefault('guard_waits',[]).append(row);keep()
    def intent(operation,**fields):
        p['_memory']()
        yield from scopes['queue']['_preflight_steps'](guard,cfg,[q.split('.')[0] for q in helper['_assets']()],on_wait=wait)
        report['intents'].append({'utc':p['_utc'](),'operation':operation,**fields});keep()
    try:
        yield from intent('qualify_retained_base_material_graphs_no_import')
        observed,objects,accepted,held,roles=p['inspect'](cfg,packet,scopes)
        report['before_metadata']=observed;keep()
        for path,obj in accepted.items():
            yield from intent('first_tag_only_retained_accepted_object',path=path)
            for key,value in p['_tags'](roles[path]).items():unreal.EditorAssetLibrary.set_metadata_tag(obj,key,value)
        observed,objects,accepted,held,roles=p['inspect'](cfg,packet,scopes,metadata=True)
        report['before_first_save']=observed;keep()
        if any(p['_file'](o,cfg).exists() for o in objects.values()):raise RuntimeError('unexpected save before qualification')
        for path,obj in sorted(accepted.items(),key=lambda row:(isinstance(row[1],unreal.StaticMesh),row[0])):
            yield from intent('unattempted_first_save_accepted_opaque',path=path)
            started=time.perf_counter();saved=bool(unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False))
            report['saves'].append({'path':path,'returned':saved,'seconds':time.perf_counter()-started});keep()
            if saved is not True or not p['_file'](obj,cfg).exists():raise RuntimeError('first save unconfirmed; preserve no replay')
        observed,objects,accepted,held,roles=p['inspect'](cfg,packet,scopes,metadata=True)
        if any(p['_file'](o,cfg).exists() for o in held.values()):raise RuntimeError('held glass unexpectedly saved')
        report.update(stage='PARTIAL_OPAQUE13_SAVED_GLASS2_HELD',final=observed,
                      post_guard=guard['_preflight']([q.split('.')[0] for q in held]));keep();return report
    except Exception as exc:
        report.update(stage='HALTED_PRESERVE_REMAINING_PARTIAL',error=str(exc),error_type=type(exc).__name__);keep();raise
