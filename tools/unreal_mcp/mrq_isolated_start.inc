# Source-only body. Sole operator embeds in the existing protected native route.
# Required bindings: unreal, plan, before, snapshot(), qualify(), record().
# Replace __OPERATION_ID__ and __MRQ_JOURNAL_PATH__ with host-allocated reprs.
# Returns mrq_result (dispatch only). Retained module.reconcile(snapshot, qualify) is called by a
# later protected callback after actual async events; it never dispatches again.
import copy as _mq_copy
import datetime as _mq_dt
import hashlib as _mq_hash
import json as _mq_json
import re as _mq_re
import sys as _mq_sys
import types as _mq_types
from pathlib import Path as _mq_Path

_MQ_SOURCE = '/Game/CodexToolEvaluation/MRQMinimalScene/R1/WB_YTM_Translated.WB_YTM_Translated'
_MQ_SHA = '754bf546aa0ab0faee47d894e273d2cb4144ceb4e472b563b05f1b0ba207d461'
_MQ_MAP = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
_MQ_FIELDS = ('project', 'world', 'pie', 'game_world', 'dirty_maps', 'dirty_content', 'scene', 'selection', 'camera')


def _mq_need(ok, message):
    if not ok:
        raise RuntimeError(message)


def _mq_digest(value):
    return _mq_hash.sha256(_mq_json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _mq_utc():
    return _mq_dt.datetime.now(_mq_dt.timezone.utc).isoformat()


def _mq_identity(obj):
    return None if obj is None else {'path': obj.get_path_name(), 'class': obj.get_class().get_path_name()}


def _mq_transient_package(obj):
    # Package residency of newly constructed owned objects, not an RF_Transient
    # reflection claim. No flags are read, changed, or inferred for other objects.
    cursor = obj
    for _ in range(12):
        parent = cursor.get_outer()
        if parent is None:
            return cursor.get_path_name() == '/Engine/Transient'
        cursor = parent
    raise RuntimeError('Owned outer chain exceeds bound')


def _mq_file(path, cap):
    _mq_need(not path.is_symlink() and not (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400), 'Reparse file refused')
    first = path.stat()
    _mq_need(0 < first.st_size <= cap, 'File exceeds finite admission bound')
    raw = path.read_bytes()
    last = path.stat()
    _mq_need(len(raw) == first.st_size == last.st_size and first.st_mtime_ns == last.st_mtime_ns, 'File changed while read')
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': _mq_hash.sha256(raw).hexdigest()}


def _mq_empty_shared(subsystem):
    # This minimal adapter refuses populated shared queues rather than pretending
    # a selected-property projection covers arbitrary unrelated configurations.
    queue = subsystem.get_queue()
    _mq_need(queue is not None, 'Shared queue getter returned null')
    jobs = queue.get_jobs()
    _mq_need(len(jobs) == 0, 'Populated shared queue is outside this minimal adapter; no jobs cleared')
    return {'queue': _mq_identity(queue), 'dirty': bool(queue.is_dirty()), 'jobs': []}


def _mq_build_start():
    for name in ('unreal', 'plan', 'before', 'snapshot', 'qualify', 'record'):
        _mq_need(name in globals(), 'Existing operator binding absent: ' + name)
    _mq_need(_mq_sys.modules.get('unreal') is unreal, 'Actual Unreal module required')
    local_plan = _mq_copy.deepcopy(plan)
    _mq_need(type(local_plan) is dict and local_plan.get('schema') == 'daedalus.owned-mrq-acceptance.v1', 'Exact MRQ schema required')
    _mq_need(local_plan.get('plan_id') == _mq_digest({k: v for k, v in local_plan.items() if k != 'plan_id'}), 'Plan digest differs')
    _mq_need(local_plan.get('sequence') == _MQ_SOURCE and local_plan.get('sequence_package_sha256') == _MQ_SHA and local_plan.get('map') == _MQ_MAP, 'Exact source sequence/map required')
    _mq_need(local_plan.get('frames') == [90] and type(local_plan['frames'][0]) is int, 'This adapter renders exactly frame 90')
    _mq_need(local_plan.get('resolution') == [320, 180] and all(type(v) is int for v in local_plan['resolution']), 'Exact tiny resolution required')
    _mq_need(type(local_plan.get('spatial_samples')) is int and local_plan['spatial_samples'] == 1 and type(local_plan.get('temporal_samples')) is int and local_plan['temporal_samples'] == 1 and local_plan.get('overwrite') is False, 'AA 1/1 and overwrite false required')
    operation_id = __OPERATION_ID__
    _mq_need(isinstance(operation_id, str) and _mq_re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', operation_id), 'Fresh host UUID required')
    alias = '_codex_owned_mrq_' + operation_id.replace('-', '_')
    _mq_need(alias not in _mq_sys.modules, 'Retained operation exists; no replay or replacement')
    journal = _mq_Path(__MRQ_JOURNAL_PATH__)
    output = _mq_Path(local_plan['output_dir'])
    _mq_need(journal.is_absolute() and not journal.exists() and journal.parent.is_dir(), 'Fresh journal outside output required')
    _mq_need(output.is_absolute() and not output.exists() and output.parent.is_dir(), 'Fresh exclusive render directory required')
    _mq_need(journal.resolve().parent != output.resolve(), 'Journal must not enter PNG inventory')
    for path in (journal.parent, output.parent):
        _mq_need(not path.is_symlink() and not (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400), 'Reparse parent refused')
    packet = _mq_Path('C:\\Users\\730ri\\Documents\\Codex\\2026-10-14\\task-2\\native-ingestion\\MRQMinimalScene20261021\\RenderR1\\plan.json')
    _mq_need(_mq_file(packet, 65536)['sha256'] == 'e0c053a31d0e65be5d35059e5c0e8cc14bc1ce4467f7a9e9f63226602b0af4db', 'Current finite render plan differs')
    source_file = _mq_Path('C:\\Unreal\\DaedalusRealm\\Content\\CodexToolEvaluation\\MRQMinimalScene\\R1\\WB_YTM_Translated.uasset')
    _mq_need(_mq_file(source_file, 8 * 1024 * 1024)['sha256'] == _MQ_SHA, 'Saved/reloaded private shot differs')
    qualify(before)
    initial = snapshot()
    qualify(initial)
    _mq_need(all(initial.get(k) == before.get(k) for k in _MQ_FIELDS), 'Fresh protected state changed before dispatch')
    _mq_need(initial.get('pie') is False and not initial.get('game_world'), 'Fresh non-PIE state required')
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    _mq_need(subsystem is not None and subsystem.get_active_executor() is None, 'An executor already owns the subsystem')
    shared_before = _mq_empty_shared(subsystem)
    state = {
        'schema': 'daedalus.owned-mrq-acceptance.v1', 'plan_id': local_plan['plan_id'],
        'operation_id': operation_id, 'retained_module': alias, 'state': 'prepared',
        'native_invoked': False, 'plugin_loaded': True, 'explicit_queue_api_bound': True,
        'sequence': _MQ_SOURCE, 'sequence_package_sha256': _MQ_SHA, 'map': _MQ_MAP,
        'executor_finished': False, 'executor_success': None, 'cancelled': None,
        'errors': [], 'callback_errors': [], 'completed_jobs': 0, 'job_results': [],
        'finished_events': [], 'outputs': [], 'dispatch_returned': False,
        'unrelated_queue_before': _mq_digest(shared_before), 'unrelated_queue_after': None,
        'protected_before': _mq_digest({k: initial.get(k) for k in _MQ_FIELDS}),
        'protected_after': None, 'normal_release': False,
        'scene_review': {'reviewed': False, 'real_scene_content': False},
        'native_runtime_qualified': False, 'render_accepted': False,
        'error_scope': 'Owned executor callbacks and adapter checks only; engine log review remains operator-owned',
    }
    retained = _mq_types.ModuleType(alias)
    retained.state = state
    retained.plan = local_plan
    retained.before = _mq_copy.deepcopy(initial)
    _mq_sys.modules[alias] = retained  # Keep callbacks/objects even if dispatch throws.

    def write_event(kind, payload):
        raw = _mq_json.dumps({'utc': _mq_utc(), 'operation_id': operation_id, 'event': kind, 'data': payload}, allow_nan=False, separators=(',', ':')).encode('utf-8') + b'\n'
        _mq_need(len(raw) <= 32768 and (not journal.exists() or journal.stat().st_size + len(raw) <= 262144), 'Owned journal bound exceeded')
        with journal.open('ab' if journal.exists() else 'xb') as stream:
            stream.write(raw)

    def callback_failure(name, exc):
        row = {'callback': name, 'error': str(exc)[:2048]}
        state['callback_errors'].append(row)
        state['state'] = 'held_callback_error'
        try:
            write_event('callback_error', row)
        except Exception as journal_exc:
            # Preserve the original callback failure even if its journal fails.
            state['journal_error'] = str(journal_exc)[:2048]

    def finished(executor, success):
        try:
            _mq_need(executor == retained.executor and type(success) is bool, 'Unexpected finished identity/type')
            event = {'utc': _mq_utc(), 'success': success}
            state['finished_events'].append(event)
            _mq_need(len(state['finished_events']) <= 4, 'Unexpected repeated finished events')
            state['executor_finished'] = True
            state['executor_success'] = success
            state['state'] = 'callbacks_received_requires_fresh_reconciliation'
            write_event('executor_finished', event)
        except Exception as exc:
            callback_failure('finished', exc)

    def errored(executor, pipeline, fatal, message):
        try:
            _mq_need(executor == retained.executor and type(fatal) is bool, 'Unexpected error identity/type')
            _mq_need(len(state['errors']) < 16, 'Error callback count bound exceeded')
            row = {'utc': _mq_utc(), 'fatal': fatal, 'message': str(message)[:4096]}
            state['errors'].append(row)
            write_event('executor_error', row)
        except Exception as exc:
            callback_failure('errored', exc)

    def job_finished(data):
        try:
            job_object = data.get_editor_property('job')
            success = data.get_editor_property('success')
            _mq_need(job_object == retained.job and type(success) is bool, 'Unexpected job identity/type')
            _mq_need(state['completed_jobs'] == 0, 'More than one owned job callback')
            shots = data.get_editor_property('shot_data')
            _mq_need(len(shots) <= 8, 'Shot output bound exceeded')
            files = []
            for shot in shots:
                passes = shot.get_editor_property('render_pass_data')
                _mq_need(len(passes) <= 8, 'Render pass bound exceeded')
                for pass_data in passes.values():
                    paths = pass_data.get_editor_property('file_paths')
                    _mq_need(len(paths) <= 3, 'Output path bound exceeded')
                    files.extend(str(path) for path in paths)
            _mq_need(len(files) <= 3 and len(set(files)) == len(files), 'Unexpected duplicate/output count')
            row = {'utc': _mq_utc(), 'job': _mq_identity(job_object), 'success': success, 'file_paths': files}
            state['job_results'].append(row)
            state['completed_jobs'] = 1
            write_event('individual_job_work_finished', row)
        except Exception as exc:
            callback_failure('job_finished', exc)

    def reconcile(fresh_snapshot, fresh_qualify):
        # Required helpers belong to the CURRENT protected callback request.
        # Never retain/reuse the start request's snapshot/qualification context.
        # No sleeps, polling loop, cancellation, second dispatch, save or input.
        _mq_need(callable(fresh_snapshot) and callable(fresh_qualify), 'Current callback snapshot/qualification helpers required')
        _mq_need(state['native_invoked'], 'Dispatch never reached the native call')
        fresh = fresh_snapshot()
        fresh_qualify(fresh)
        active = subsystem.get_active_executor()
        state['terminal_readback_utc'] = _mq_utc()
        state['terminal_active_executor'] = _mq_identity(active)
        state['terminal_pie'] = fresh.get('pie')
        state['terminal_game_world'] = fresh.get('game_world')
        state['preservation'] = {k: fresh.get(k) == initial.get(k) for k in _MQ_FIELDS}
        state['protected_after'] = _mq_digest({k: fresh.get(k) for k in _MQ_FIELDS})
        shared_after = _mq_empty_shared(subsystem)
        state['unrelated_queue_after'] = _mq_digest(shared_after)
        _mq_need(state['executor_finished'] and len(state['finished_events']) == 1 and state['executor_success'] is True, 'No unique successful executor terminal')
        _mq_need(active is None and fresh.get('pie') is False and not fresh.get('game_world'), 'PIE/executor still active; retain operation')
        _mq_need(state['completed_jobs'] == 1 and state['job_results'][0]['success'] is True and not state['errors'] and not state['callback_errors'], 'Actual job success/error prerequisites failed')
        _mq_need(all(state['preservation'].values()) and state['unrelated_queue_before'] == state['unrelated_queue_after'], 'Protected state/shared queue differs')
        _mq_need(_mq_file(source_file, 8 * 1024 * 1024)['sha256'] == _MQ_SHA, 'Original sequence bytes changed')
        expected = output / 'mrq_0090.png'
        _mq_need(state['job_results'][0]['file_paths'] and [_mq_Path(p).resolve() for p in state['job_results'][0]['file_paths']] == [expected.resolve()], 'Actual job callback output does not match frame90 filename')
        _mq_need(output.is_dir() and not output.is_symlink() and not (getattr(output.lstat(), 'st_file_attributes', 0) & 0x400), 'Missing/reparse output root')
        _mq_need(sorted(p.name for p in output.iterdir()) == [expected.name], 'Unexpected output inventory')
        pin = _mq_file(expected, 4 * 1024 * 1024)
        state['outputs'] = [{'frame': 90, 'file': expected.name, 'sha256': pin['sha256'], 'bytes': pin['bytes']}]
        state['cancelled'] = False  # Successful job + executor terminal, not a guessed early state.
        state['state'] = 'complete'
        state['operation_terminal_utc'] = _mq_utc()
        write_event('native_terminal_reconciled_not_yet_accepted', {k: state[k] for k in ('state', 'outputs', 'preservation', 'unrelated_queue_after')})
        return _mq_copy.deepcopy(state)

    retained.callbacks = (finished, errored, job_finished)
    retained.reconcile = reconcile
    retained.journal_path = str(journal)
    retained.queue = unreal.MoviePipelineQueue()
    _mq_need(_mq_transient_package(retained.queue), 'Owned queue is not under transient package')
    retained.job = retained.queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    retained.job.set_editor_property('job_name', 'CodexOwnedMRQ_' + operation_id)
    retained.job.set_editor_property('sequence', unreal.SoftObjectPath(_MQ_SOURCE))
    retained.job.set_editor_property('map', unreal.SoftObjectPath(_MQ_MAP))
    config = retained.job.get_configuration()
    retained.config = config
    _mq_need(config is not None and _mq_transient_package(config), 'Owned config is not under transient package')
    setting = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    for name, value in {
        'output_directory': unreal.DirectoryPath(str(output)), 'file_name_format': 'mrq_{frame_number}',
        'output_resolution': unreal.IntPoint(320, 180), 'use_custom_frame_rate': False,
        'output_frame_step': 1, 'handle_frame_count': 0, 'use_custom_playback_range': True,
        'custom_start_frame': 90, 'custom_end_frame': 91, 'override_existing_output': False,
        'zero_pad_frame_numbers': 4, 'frame_number_offset': 0, 'auto_version': False,
        'flush_disk_writes_per_shot': True,
    }.items():
        setting.set_editor_property(name, value)
    aa = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    for name, value in {'spatial_sample_count': 1, 'temporal_sample_count': 1, 'render_warm_up_count': 0, 'engine_warm_up_count': 0, 'use_camera_cut_for_warm_up': False, 'render_warm_up_frames': False}.items():
        aa.set_editor_property(name, value)
    retained.settings = (setting, aa, config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase), config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG))
    retained.executor = unreal.MoviePipelinePIEExecutor()
    retained.executor.set_is_rendering_offscreen(True)
    retained.executor.set_post_render_action(unreal.MoviePipelinePostRenderActionType.DO_NOTHING)
    retained.executor.on_executor_finished_delegate.add_callable_unique(finished)
    retained.executor.on_executor_errored_delegate.add_callable_unique(errored)
    retained.executor.on_individual_job_work_finished_delegate.add_callable_unique(job_finished)
    state.update(queue_transient=True, config_transient=True,
                 transient_proof='Actual owned outer chains terminate at /Engine/Transient',
                 owned_queue_id=retained.queue.get_path_name(), shared_queue_id=shared_before['queue']['path'])
    _mq_need(state['owned_queue_id'] != state['shared_queue_id'], 'Owned queue aliases shared queue')
    _mq_need(_mq_empty_shared(subsystem) == shared_before and subsystem.get_active_executor() is None, 'Subsystem changed before dispatch')
    write_event('dispatch_intent', {'plan': local_plan, 'queue': _mq_identity(retained.queue), 'executor': _mq_identity(retained.executor)})
    record('OWNED_MRQ_ASYNC_DISPATCH_INTENT', {'operation_id': operation_id, 'plan_id': local_plan['plan_id'], 'retained_module': alias})
    state['native_invoked'] = True
    state['state'] = 'dispatch_entered_outcome_pending'
    state['dispatch_started_utc'] = _mq_utc()
    # A throwing return is uncertain. Retained module/journal MUST be reconciled;
    # no replay, force-clear, cancellation or callback removal is performed here.
    subsystem.render_queue_instance_with_executor_instance(retained.queue, retained.executor)
    state['dispatch_returned'] = True
    state['dispatch_returned_utc'] = _mq_utc()
    write_event('dispatch_returned_not_terminal', {'state': state['state']})
    return _mq_copy.deepcopy(state)


mrq_result = _mq_build_start()
