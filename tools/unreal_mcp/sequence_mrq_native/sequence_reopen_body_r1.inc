# Source only. Prepend public R2 helper definitions (db56feec) and OWNED R2
# function definitions (9580b647), split before '\nresult = {'. Never its ENTRY.
# Host supplies actual plan/process_generation/unreal/before/snapshot/qualify/record.
_sr_receipt_path = _sc_Path('C:/Users/730ri/Documents/Codex/2026-10-14/task-2/native-ingestion/AnimationSequenceAdoption20261021/OwnedSequenceR2Host/sequence-operation-receipt.json')
_sr_receipt_sha = '18a82e48b57eedd5fceb881d46810282bf0175017e95deb91b8435e5528a5947'
_sr_saved_sha = 'b876240a5c09bf5fc55960f8e6f0b4d62723c9d75dbbd1c3ad07dff26d6dee9d'
result = {'schema': 'daedalus.named-sequence-reopen-readback.v1', 'state': 'HELD',
          'native_invoked': True, 'errors': [], 'plan_id': plan.get('plan_id'),
          'explicit_asset_load_requests': 0, 'duplicate_calls': 0, 'key_edit_calls': 0, 'save_calls': 0,
          'normal_close_attested': False, 'normal_release': False, 'sequence_accepted': False,
          'native_runtime_qualified': False, 'adopted': False,
          'generation_boundary': 'Actual host-supplied current generation; prior normal close and final consumer acceptance remain host responsibilities.'}
_sc_actor_api = _sc_editor_api = None
_sc_original_selection = _sc_original_camera = None
try:
    qualify(before)
    _sc_need(callable(globals().get('public_sequence_facts')) and callable(globals().get('_sc_copy_snapshot')),
             'Frozen public R2 and OWNED R2 definitions are required; never execute prior operation ENTRY')
    _sc_need(process_generation['pid'] == _sc_os.getpid() and process_generation['project_path'] == _SC_PROJECT,
             'Current independently verified editor process/project differs')
    with _sr_receipt_path.open('rb') as _sr_stream:
        _sr_raw = _sr_stream.read(256 * 1024 + 1)
    _sc_need(0 < len(_sr_raw) <= 256 * 1024 and _sc_hashlib.sha256(_sr_raw).hexdigest() == _sr_receipt_sha,
             'Actual completed owned-copy operation receipt changed')
    _sr_prior = _sc_json.loads(_sr_raw)
    _sr_operation = _sr_prior['operation']
    _sc_need(plan == _sr_prior['prepared_plan'] and plan['plan_id'] == _sc_digest({k: v for k, v in plan.items() if k != 'plan_id'})
             and _sr_operation.get('state') == 'AWAITING_FRESH_REOPEN' and _sr_operation.get('errors') == []
             and _sr_prior.get('preserved') is True and _sr_operation.get('key_edit_count') == 1,
             'Exact successful saved-copy plan and preservation receipt required')
    _sr_old = _sr_operation['after_edit']
    _sc_need((process_generation['pid'], process_generation['process_started_utc'])
             != (_sr_old['pid'], _sr_old['process_started_utc']), 'Reopen readback requires a genuinely different editor generation')
    _sc_need(_sr_operation['edited_saved_file']['sha256'] == _sr_saved_sha
             and _sr_old['package_sha256'] == _sr_saved_sha, 'Prior saved copy hash differs')
    _sr_saved_before = _sc_disk(plan['copy_sequence'])
    _sc_need(_sr_saved_before['sha256'] == _sr_saved_sha, 'Saved edited package differs before any asset load')
    result['savedfile_before'] = _sr_saved_before
    result['source_package_before'] = _sc_disk(_SC_SOURCE)['sha256']
    _sc_need(result['source_package_before'] == _SC_SOURCE_SHA, 'Original source package changed before reopen readback')
    _sr_library = unreal.LevelSequenceEditorBlueprintLibrary
    _sc_need(_sr_library.get_current_level_sequence() is None and _sr_library.get_focused_level_sequence() is None,
             'Existing Sequencer context is unsupported; no load or context hijack')
    _sc_actor_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    _sc_editor_api = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    _sc_original_selection = list(_sc_actor_api.get_selected_level_actors())
    _sc_original_camera = _sc_editor_api.get_level_viewport_camera_info()
    _sc_need(len(_sc_original_selection) <= 4096 and len(_sc_original_camera) == 2, 'Current selection/camera restoration unavailable')
    _sr_copy = unreal.find_object(None, plan['copy_sequence'], follow_redirectors=False)
    if _sr_copy is None:
        record('OWNED_SEQUENCE_REOPEN_EXACT_LOAD_INTENT', {'copy': plan['copy_sequence'], 'saved_sha256': _sr_saved_sha})
        result['explicit_asset_load_requests'] = 1
        _sr_copy = unreal.load_asset(plan['copy_sequence'])
    _sc_need(_sc_id(_sr_copy) == {'path': plan['copy_sequence'], 'class': '/Script/LevelSequence.LevelSequence'},
             'Exact saved owned LevelSequence could not be loaded; no alternate target')
    _sr_loaded = snapshot()
    qualify(_sr_loaded)
    _sc_need(all(_sr_loaded[k] == before[k] for k in _SC_FIELDS), 'Protected state changed during exact owned-copy load')
    _sr_after, _sr_projection, _sr_key, _sr_saved_after = _sc_copy_snapshot(_sr_copy, True)
    result['after_reopen'] = _sr_after
    result['savedfile'] = _sr_saved_after
    _sc_need(_sr_saved_after['sha256'] == _sr_saved_sha and _sr_after['package_sha256'] == _sr_saved_sha,
             'Owned copy bytes changed during readback/evaluation; no save attempted')
    for _sr_field in ('display_rate', 'tick_resolution', 'playback_range_display', 'camera_cut_binding_guid',
                      'other_sequence_data_sha256', 'key', 'evaluated_camera_samples', 'protected_state_sha256'):
        _sc_need(_sr_after[_sr_field] == _sr_old[_sr_field], 'Saved edited readback differs from actual prior operation: ' + _sr_field)
    result['current_generation_differs_from_saved_operation'] = True
    result['state'] = 'REOPEN_READBACK_COMPLETE_AWAITING_CONSUMER'
except Exception as _sr_error:
    result['errors'].append(type(_sr_error).__name__ + ': ' + str(_sr_error))
    result['state'] = 'HELD'
finally:
    if _sc_actor_api is not None and _sc_editor_api is not None and _sc_original_selection is not None and _sc_original_camera is not None:
        try:
            _sc_restore_selection_camera()
        except Exception as _sr_cleanup:
            result['errors'].append('Restoration: ' + type(_sr_cleanup).__name__ + ': ' + str(_sr_cleanup))
            result['state'] = 'HELD'
    try:
        result['source_package_after'] = _sc_disk(_SC_SOURCE)['sha256']
        _sc_need(result['source_package_after'] == _SC_SOURCE_SHA, 'Original source bytes changed at reopen terminal')
        _sr_final = snapshot()
        result['after'] = _sr_final
        result['preservation'] = {k: _sr_final.get(k) == before.get(k) for k in _SC_FIELDS}
        result['preserved'] = all(result['preservation'].values())
        qualify(_sr_final)
        _sc_need(result['preserved'], 'Final protected nine-field state differs')
    except Exception as _sr_final_error:
        result['errors'].append('Final state: ' + type(_sr_final_error).__name__ + ': ' + str(_sr_final_error))
        result['state'] = 'HELD'
    record('OWNED_SEQUENCE_REOPEN_READBACK_KNOWN_TERMINAL', {'state': result['state'], 'errors': result['errors'],
                                                          'explicit_asset_load_requests': result['explicit_asset_load_requests'],
                                                          'duplicate_calls': 0, 'key_edit_calls': 0, 'save_calls': 0})
