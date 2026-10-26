import types,hashlib,copy
module=types.ModuleType('_codex_mrq_private_camera_copy_r1')
exec(compile(READER_SOURCE,READER_PATH,'exec'),module.__dict__)
sys.modules[module.__name__]=module
need=module.need
source=unreal.find_object(None,module.SEQUENCE,follow_redirectors=False)
need(source is not None,'Original sequence must already be loaded')
need(not unreal.EditorAssetLibrary.does_asset_exist(COPY_PACKAGE),'Private destination exists; no overwrite')
api=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
viewport=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=viewport.get_editor_world()
scene=module.scene_facts(unreal,world,api)
spawn=[x for x in scene['actors'] if x['label']=='YTM_Island_Spawn']
need(len(spawn)==1 and scene['streaming']['is_level_loaded'] and scene['streaming']['is_level_visible'],'Exact visible YTM scene required')

def projection(sequence):
    opaque,local,guid=module.camera_binding(unreal,sequence)
    seq,bind,track_api,sec_api=unreal.MovieSceneSequenceExtensions,unreal.MovieSceneBindingExtensions,unreal.MovieSceneTrackExtensions,unreal.MovieSceneSectionExtensions
    bindings=[p for p in seq.get_bindings(sequence) if module.binding_key(unreal,p,sequence)==guid]
    tracks=[t for t in bind.get_tracks(bindings[0]) if t.get_class().get_path_name()=='/Script/MovieSceneTracks.MovieScene3DTransformTrack']
    need(len(tracks)==1,'Single bound camera transform track required')
    sections=list(track_api.get_sections(tracks[0]));need(len(sections)==1,'Single camera transform section required')
    channels=list(sec_api.get_all_channels(sections[0]));need(len(channels)==9,'Exact nine transform channels required')
    result={};handles={}
    for ch in channels:
        name=str(ch.get_editor_property('channel_name'))
        need(name not in result and ch.get_class().get_path_name()=='/Script/SequencerScripting.MovieSceneScriptingDoubleChannel','Unique Double transform channels required')
        count=ch.get_num_keys();need(type(count) is int and 0<=count<=8,'Finite recipe keys required')
        keys=list(ch.get_keys());need(len(keys)==count,'Changing key inventory')
        rows=[]
        for key in keys:
            when=key.get_time(unreal.MovieSceneTimeUnit.DISPLAY_RATE)
            row={'frame':when.get_editor_property('frame_number').get_editor_property('value'),'subframe':when.get_editor_property('sub_frame'),'value':key.get_value()}
            for method in ('get_interpolation_mode','get_tangent_mode','get_arrive_tangent','get_leave_tangent','get_arrive_tangent_weight','get_leave_tangent_weight'):
                value=getattr(key,method)();row[method]=value if type(value) in (int,float) else str(value)
            rows.append(row)
        result[name]={'has_default':ch.has_default(),'default':ch.get_default() if ch.has_default() else None,'keys':rows}
        handles[name]=keys
    return {'guid':guid,'channels':result,'display_rate':[sequence.get_display_rate().numerator,sequence.get_display_rate().denominator],
            'tick_resolution':[sequence.get_tick_resolution().numerator,sequence.get_tick_resolution().denominator],
            'playback':[sequence.get_playback_start(),sequence.get_playback_end()]},handles

original,unused=projection(source)
need(original['display_rate']==[30,1] and original['playback']==[0,360],'Exact original shot rate/range required')
names=['Location.X','Location.Y','Location.Z']
need(all(n in original['channels'] for n in names),'Expected named location channels absent')
rows=[]
for k in range(7):
    keys=[original['channels'][n]['keys'] for n in names]
    need(all(len(items)==7 and items[k]['frame']==60*k and items[k]['subframe']==0 for items in keys),'Exact recipe times required')
    rows.append({'frame':60*k,'position':[items[k]['value'] for items in keys]})
translation=module.island_camera_translation(rows,spawn[0]['location_cm'])
record('PRIVATE_YTM_SEQUENCE_DUPLICATE_INTENT',{'source':module.SEQUENCE,'copy':COPY_ASSET,'translation':translation})
private=unreal.EditorAssetLibrary.duplicate_asset(module.SEQUENCE.split('.')[0],COPY_PACKAGE)
need(private is not None and private.get_path_name()==COPY_ASSET,'Exact private duplicate required')
baseline,handles=projection(private);need(baseline==original,'Private supported projection differs before edit')
expected=copy.deepcopy(baseline);edited=[]
for axis,name in enumerate(names):
    delta=translation['translation_cm'][axis]
    if delta==0:continue
    for k,key in enumerate(handles[name]):
        value=expected['channels'][name]['keys'][k]['value']+delta
        key.set_value(value);expected['channels'][name]['keys'][k]['value']=value
        edited.append({'channel':name,'frame':60*k,'before':baseline['channels'][name]['keys'][k]['value'],'after':value})
actual,handles=projection(private);need(actual==expected,'Unexpected supported channel/tangent/rate/binding change')
camera=module.evaluate_frame90(unreal,private,api,viewport,scene)
need(len(camera['targets'])==2 and all(t['relation']['center_in_fov_angular_test'] for t in camera['targets']),'Ground/Spawn remain outside corrected camera FOV')
saved=unreal.EditorAssetLibrary.save_loaded_asset(private,only_if_is_dirty=False)
need(saved is True,'Private sequence save failed; no retry')
clean=snapshot();qualify(clean)
need(not clean['dirty_content'] and not clean['dirty_maps'],'Dirty work prevents isolated reload')
package=private.get_outer();private=None;handles=None
reload=unreal.EditorLoadingAndSavingUtils.reload_packages([package],interaction_mode=unreal.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
need(isinstance(reload,tuple) and reload[0] is True and not str(reload[1]),'Private clean reload failed: '+str(reload))
private=unreal.find_object(None,COPY_ASSET,follow_redirectors=False);need(private is not None,'Reloaded exact copy absent')
persisted,handles=projection(private);need(persisted==expected,'Private supported projection did not persist')
camera_after=module.evaluate_frame90(unreal,private,api,viewport,scene)
need(camera_after['location_cm']==camera['location_cm'] and camera_after['rotation_pitch_yaw_roll_deg']==camera['rotation_pitch_yaw_roll_deg'],'Reloaded camera differs')
source_after,unused=projection(source);need(source_after==original,'Original resident projection changed')
after=snapshot();qualify(after);preserved={k:before[k]==after[k] for k in FIELDS}
need(all(preserved.values()),'Final protected state changed')
result={'copy':COPY_ASSET,'translation':translation,'edited_keys':edited,'saved':saved,'reloaded':True,'camera_before_reload':camera,'camera_after_reload':camera_after,
        'source_projection_unchanged':True,'supported_copy_projection_persisted':True,'projection_scope':'Nine typed transform channels/defaults/keys/tangents, frame90 cut GUID, display/tick rates/playback range. No full template/hidden metadata claim.',
        'projection_before':original,'projection_after':persisted,'preservation':preserved,'after':after,'render_invoked':False,'scene_render_accepted':False}
