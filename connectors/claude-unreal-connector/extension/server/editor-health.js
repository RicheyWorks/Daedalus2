// SPDX-License-Identifier: MIT
'use strict';

const { performance } = require('node:perf_hooks');

const CRASH = /CrashReportClient|Crash Reporter/i;
const EDITOR = /^UnrealEditor(?:-[\w-]+)?(?:\.exe)?$/i;
const TOOL = /^(Message Log|Output Log|Content Browser|Content Drawer|Details|Outliner|World Settings|Project Settings|Editor Preferences|Plugins|Sequencer|Niagara Editor|Material Editor|Material Instance Editor|Blueprint Editor|Static Mesh Editor|Landscape|Modeling|Session Frontend|Widget Reflector)\b/i;
const ASSET_TOOL = / - (Material|Material Instance|Blueprint|Static Mesh|Niagara|Animation|Skeleton|Widget)(?: Editor)?$/i;
const DIALOG = /^(Save (Content|Packages|Assets|Changes|All)|Unsaved Changes|Confirm(?:ation)?|Warning|Error|Message Box)\b/i;
const positivePid = pid => Number.isSafeInteger(pid) && pid > 0;
const owned = window => window.owner !== undefined && window.owner !== null && String(window.owner) !== '0' && window.owner !== '';
const evidenceWindow = ({ pid, process, title, main, owner, enabled, hwnd }) =>
  ({ pid, process, title, main, owner, enabled, hwnd });
function crashMetadata(value) {
  if (!value || typeof value.project !== 'string' || !value.project.trim() || value.project.length > 256) return undefined;
  const safe = {};
  for (const key of ['project', 'signature', 'backend', 'renderer']) {
    if (typeof value[key] === 'string' && value[key].trim() && value[key].length <= 256) safe[key] = value[key];
  }
  return safe;
}

/** Classifies outside-editor evidence only; available does not establish bridge readiness. */
function classify(snapshot, expectedPid, expectedStartTime) {
  const report = (state, pid = expectedPid, details = {}) => ({ state, pid, expectedPid, details });
  if (expectedPid !== undefined && !positivePid(expectedPid)) {
    return report('probe_failed', undefined, { reason: 'invalid_expected_pid' });
  }
  if (!snapshot || snapshot.ok !== true || !Array.isArray(snapshot.processes) || !Array.isArray(snapshot.windows)) {
    return report('probe_failed', undefined, { reason: 'invalid_probe', error: String(snapshot?.error || '') });
  }
  if (snapshot.processes.some(p => !p || !positivePid(p.pid) || typeof p.name !== 'string') ||
      snapshot.windows.some(w => !w || !positivePid(w.pid) || typeof w.title !== 'string')) {
    return report('probe_failed', undefined, { reason: 'malformed_process_or_window' });
  }
  const editors = [...new Set(snapshot.processes.filter(p => EDITOR.test(p.name) && !CRASH.test(p.name)).map(p => p.pid))];
  const windows = snapshot.windows.filter(w => editors.includes(w.pid) && (expectedPid === undefined || w.pid === expectedPid));
  const recovery = windows.find(w => /Restore Packages/i.test(w.title));
  if (recovery) return report('recovery_required', recovery.pid, { windows: [evidenceWindow(recovery)] });
  const crashes = snapshot.processes.filter(p => CRASH.test(p.name));
  const crashWindows = snapshot.windows.filter(w => CRASH.test(w.process || '') || CRASH.test(w.title));
  if (crashes.length || crashWindows.length) {
    const editorAbsent = expectedPid === undefined ? !editors.length : !editors.includes(expectedPid);
    const details = {
      processes: crashes.map(({ pid, name }) => ({ pid, name })), windows: crashWindows.map(evidenceWindow),
      association: 'unconfirmed'
    };
    if (editorAbsent) details.reason = 'editor_exited_with_crash_reporter';
    const metadata = crashMetadata(snapshot.crash_evidence);
    if (metadata) details.crash_evidence = metadata;
    return report(editorAbsent ? 'crashed' : 'crash_reporter_present', expectedPid, details);
  }
  if (expectedPid !== undefined && !editors.includes(expectedPid)) return report('editor_exited');
  if (!editors.length) return report('editor_not_running', undefined);
  if (expectedPid === undefined && editors.length !== 1) {
    return report('editor_ambiguous', undefined, { pids: editors });
  }
  const pid = expectedPid === undefined ? editors[0] : expectedPid;
  const startTime = snapshot.processes.find(p => p.pid === pid && EDITOR.test(p.name))?.start_time;
  if (expectedStartTime !== undefined && startTime !== expectedStartTime) {
    return report('editor_exited', pid, { reason: 'session_changed',
      expected_start_time: expectedStartTime, start_time: startTime });
  }
  const selected = windows.filter(w => w.pid === pid);
  const blocked = selected.filter(w => DIALOG.test(w.title) || w.enabled === false ||
    ((w.main !== true || owned(w)) && !TOOL.test(w.title) && !ASSET_TOOL.test(w.title)));
  if (blocked.length) return report('modal_blocked', pid, { windows: blocked.map(evidenceWindow) });
  if (!selected.some(w => w.main === true && !owned(w) && w.enabled !== false)) {
    return report('editor_loading', pid, { reason: 'no_visible_root' });
  }
  return { ...report('available', pid, { bridge_ready: false }), start_time: startTime };
}

class EditorHealthError extends Error {
  constructor(state, details = {}, dispatched = false, cause) {
    super(`Editor operation blocked: ${state}`, cause === undefined ? undefined : { cause });
    this.name = 'EditorHealthError';
    this.code = state.toUpperCase();
    this.state = state;
    this.details = details;
    this.dispatched = dispatched;
    this.outcome_uncertain = dispatched;
  }
}

/** One explicit operation, with bounded probes and no UI actions or automatic retries.
 * call must honor signal by closing its socket; aborting cannot undo work already dispatched.
 */
async function guardedCall({ probe, call, timeoutMs, pollMs = 1000, probeTimeoutMs = 5000,
  onEvidence, beforeDispatch, expectedPid, expectedStartTime } = {}) {
  if (typeof probe !== 'function' || typeof call !== 'function' ||
      !Number.isFinite(timeoutMs) || timeoutMs <= 0 || !Number.isFinite(pollMs) || pollMs <= 0 ||
      !Number.isFinite(probeTimeoutMs) || probeTimeoutMs <= 0) {
    throw new TypeError('probe/call and positive finite time bounds are required');
  }
  const deadline = performance.now() + timeoutMs;
  const callController = new AbortController();
  let dispatched = false;
  let activeProbe;
  let fatal;
  let rejectDeadline;
  const expired = new Promise((_, reject) => { rejectDeadline = reject; });
  expired.catch(() => {});
  const fail = (state, details = {}, cause) => {
    if (!fatal) fatal = new EditorHealthError(state, details, dispatched, cause);
    callController.abort(fatal);
    activeProbe?.abort(fatal);
    return fatal;
  };
  const remaining = () => Math.max(0, deadline - performance.now());
  const overallTimer = setTimeout(() => rejectDeadline(fail('timeout', { reason: 'overall_deadline' })), timeoutMs);
  const emit = value => {
    if (!onEvidence) return;
    try { Promise.resolve(onEvidence(value)).catch(() => {}); } catch (_) { /* diagnostic hook only */ }
  };
  async function check() {
    if (fatal) throw fatal;
    if (!remaining()) throw fail('timeout', { reason: 'overall_deadline' });
    const controller = new AbortController();
    activeProbe = controller;
    let probeTimer;
    const probeBudget = remaining();
    const bounded = new Promise((_, reject) => {
      const overallFirst = probeBudget <= probeTimeoutMs;
      probeTimer = setTimeout(() => reject(fail(overallFirst ? 'timeout' : 'probe_failed', {
        reason: overallFirst ? 'overall_deadline' : 'probe_timeout'
      })), Math.min(probeTimeoutMs, probeBudget));
    });
    try {
      const snapshot = await Promise.race([
        Promise.resolve().then(() => probe({ signal: controller.signal, expectedPid, expectedStartTime })), bounded, expired
      ]);
      if (!remaining()) throw fail('timeout', { reason: 'overall_deadline' });
      const health = classify(snapshot, expectedPid, expectedStartTime);
      emit(health);
      if (health.state !== 'available') throw fail(health.state, health.details);
      return health;
    } catch (error) {
      if (error instanceof EditorHealthError) throw fail(error.state, error.details, error);
      throw fail('probe_failed', { reason: 'probe_rejected', error: String(error?.message || error) }, error);
    } finally {
      clearTimeout(probeTimer);
      if (activeProbe === controller) activeProbe = undefined;
    }
  }
  async function tick(outcome) {
    let timer;
    try {
      return await Promise.race([outcome, expired, new Promise(resolve => {
        timer = setTimeout(() => resolve({ tick: true }), Math.min(pollMs, remaining()));
      })]);
    } finally { clearTimeout(timer); }
  }
  try {
    const initial = await check();
    expectedPid = initial.pid;
    expectedStartTime = initial.start_time;
    if (beforeDispatch !== undefined) {
      if (typeof beforeDispatch !== 'function') throw new TypeError('beforeDispatch must be a function');
      try {
        await Promise.race([Promise.resolve().then(() => beforeDispatch({
          signal: callController.signal, remainingMs: remaining(), expectedPid, expectedStartTime
        })), expired]);
      } catch (error) {
        if (error instanceof EditorHealthError) throw fail(error.state, error.details, error);
        throw fail('dispatch_blocked', { error: String(error?.message || error) }, error);
      }
    }
    if (!remaining()) throw fail('timeout', { reason: 'overall_deadline' });
    dispatched = true;
    // Attach rejection handling immediately, including synchronous transport failures.
    let outcome;
    try {
      outcome = Promise.resolve(call({ signal: callController.signal, remainingMs: remaining(), expectedPid, expectedStartTime }))
        .then(value => ({ value }), error => ({ error }));
    } catch (error) { outcome = Promise.resolve({ error }); }
    for (;;) {
      const event = await tick(outcome);
      if (event.tick) { await check(); continue; }
      if (Object.hasOwn(event, 'error')) {
        if (event.error instanceof EditorHealthError) {
          throw fail(event.error.state, event.error.details, event.error);
        }
        // A connection failure can arrive before the monitor sees a crash or modal.
        await check();
        throw fail('call_failed', { error: String(event.error?.message || event.error) }, event.error);
      }
      // A reply cannot bypass an in-progress monitor probe, nor this fresh final probe.
      await check();
      if (fatal) throw fatal;
      return event.value;
    }
  } finally {
    clearTimeout(overallTimer);
    activeProbe?.abort(fatal);
  }
}

module.exports = { classify, guardedCall, EditorHealthError };
