// SPDX-License-Identifier: MIT
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { classifySecurityAlerts, createSecurityAlertObserver, SecurityAlertError, contextMetadata } =
  require('../extension/server/security-alert-observer');

const CONTEXT = { command_id: 'fixture-1', command: 'fixture_task',
  artifact: { path: 'C:\\Project\\Build\\fixture-task.exe', sha256: 'a'.repeat(64) } };
const CLOCK = '2026-10-12T23:00:00.000Z';
const alert = (extra = {}) => ({ pid: 100, process: 'NortonUI', hwnd: '1001', visible: true,
  title: 'Norton security alert', text: 'Program blocked: C:\\Project\\Build\\fixture-task.exe', ...extra });
const snapshot = (...windows) => ({ ok: true, windows });
const empty = () => snapshot();
const never = () => new Promise(() => {});
const options = inspect => ({ inspect, pollMs: 2, probeTimeoutMs: 20, hookTimeoutMs: 10, nowUtc: () => CLOCK });
const HISTORY_SOURCE = 'Norton autosandbox.log';
const historyEvent = (extra = {}) => ({ source: HISTORY_SOURCE, event_at: CLOCK,
  artifact_path: CONTEXT.artifact.path, kind: 'notice', result: 'Sandboxing(no custody)',
  process: 'Norton log', pid: null, hwnd: null, ...extra });
const historySnapshot = (events, extra = {}) => ({ available: false, reason: 'inspection_unavailable', windows: [],
  history_source: HISTORY_SOURCE, history: events, ...extra });
const historyScope = { sinceUtc: CLOCK, observedUtc: CLOCK };
const securityError = dispatched => error => {
  assert.ok(error instanceof SecurityAlertError);
  assert.equal(error.state, 'security_alert_observed');
  assert.equal(error.code, 'SECURITY_ALERT_OBSERVED');
  assert.equal(error.dispatched, dispatched);
  assert.equal(error.outcome_uncertain, dispatched);
  return true;
};

test('visible Norton alert records exact artifact correlation and session identity', () => {
  const result = classifySecurityAlerts(snapshot(alert({ start_time: CLOCK })), CONTEXT);
  assert.equal(result.state, 'alert');
  assert.equal(result.alert.artifact_correlation, 'exact_path');
  assert.equal(result.alert.process_start_time, CLOCK);
  assert.equal(result.alert.pid, 100);
  assert.equal(result.alert.hwnd, '1001');
  assert.equal(result.alert.causality, 'unconfirmed');
  assert.equal(result.alert.detection_verdict, 'not_assessed');
  assert.equal(result.alert.blocked, true);
  assert.equal(result.alert.severity, 'blocked');
  assert.match(result.alert.alert_id, /^[a-f0-9]{64}$/);
});

test('provider aliases and explicit basename match remain labeled inference', () => {
  const result = classifySecurityAlerts({ available: true, windows: [alert({ process: undefined,
    processName: 'NortonUI.exe', text: 'Program blocked: fixture-task.exe' })] }, CONTEXT);
  assert.equal(result.state, 'alert');
  assert.equal(result.alert.artifact_correlation, 'basename_inference');
});

test('unrelated processes, missing identity, nonvisible windows and Norton home are excluded', () => {
  for (const extra of [
    { process: 'UnrealEditor' }, { process: 'FakeNortonUI' }, { process: 'C:\\Fake\\NortonUI.exe' },
    { pid: 0 }, { visible: false },
    { title: 'Norton', text: 'Welcome home. Auto-Protect enabled. fixture-task.exe is safe.' },
  ]) {
    assert.equal(classifySecurityAlerts(snapshot(alert(extra)), CONTEXT).state, 'not_observed');
  }
});

test('an alert for another file or an explicit different path cannot pause this artifact', () => {
  for (const text of [
    'Program blocked: other.exe', 'Program blocked: fixture-task.exe.backup',
    'Program blocked: prefix-fixture-task.exe', 'Program blocked: C:\\Other\\fixture-task.exe',
    'Program blocked: "C:\\Other Folder\\fixture-task.exe"',
    'Program blocked: C:\\Project\\Build\\fixture-task.exe.bak',
  ]) assert.equal(classifySecurityAlerts(snapshot(alert({ text })), CONTEXT).state, 'not_observed');
});

test('missing inspection/context/text is unavailable rather than verified absence', () => {
  assert.deepEqual(classifySecurityAlerts({ available: false, reason: 'private arbitrary error' }, CONTEXT),
    { state: 'unavailable', reason: 'inspection_unavailable' });
  assert.equal(classifySecurityAlerts(snapshot(alert()), {}).reason, 'artifact_context_unavailable');
  assert.equal(classifySecurityAlerts(snapshot(alert({ title: 'Norton', text: undefined, text_available: false })), CONTEXT).reason,
    'alert_text_unavailable');
});

test('title-only correlated alert works while text unavailability stays explicit', () => {
  const result = classifySecurityAlerts(snapshot(alert({ title: 'Security alert: fixture-task.exe blocked',
    text: undefined, text_available: false })), CONTEXT);
  assert.equal(result.state, 'alert');
  assert.equal(result.alert.text_available, false);
});

test('only relevant bounded lines are retained and personal text is redacted', () => {
  const result = classifySecurityAlerts(snapshot(alert({
    text: 'Unrelated personal conversation\nProgram blocked: fixture-task.exe. person@example.test https://example.test/private\n' +
      'Security risk User=someone\nProgram blocked fixture-task.exe C:\\Users\\someone\\private\nUnrelated settings value',
  })), CONTEXT);
  assert.equal(result.state, 'alert');
  assert.doesNotMatch(result.alert.text, /personal conversation|settings value|person@example|someone|https:/);
  assert.match(result.alert.text, /\[email redacted\]/);
  assert.match(result.alert.text, /\[URL redacted\]/);
  assert.match(result.alert.text, /\[identity redacted\]/);
  assert.match(result.alert.text, /\[path redacted\]/);
  assert.ok(result.alert.text.length <= 1024);
});

test('context excludes code, arguments, extra fields and invalid hashes', () => {
  const actual = contextMetadata({ ...CONTEXT, code: 'private code', args: ['private argument'],
    artifact: { ...CONTEXT.artifact, sha256: 'not-a-hash', token: 'private token' } });
  assert.deepEqual(actual, { command_id: 'fixture-1', command: 'fixture_task', artifact: {
    path: CONTEXT.artifact.path, sha256: null, sha256_status: 'unavailable',
  } });
  assert.equal(contextMetadata({ artifact_path: 'https://private.test/task.exe' }).artifact, undefined);
  assert.equal(contextMetadata({ artifact_path: '..\\relative.exe' }).artifact, undefined);
});

test('informational sandbox/analysis popup records once and normal commands continue', async () => {
  let writes = 0, pauses = 0, calls = 0;
  const observer = createSecurityAlertObserver({ ...options(async ({ context }) => {
    assert.equal(context.artifact.path, CONTEXT.artifact.path);
    return snapshot(alert({ title: 'Norton Auto-Sandbox', text: 'Sandboxing (no custody): fixture-task.exe is being analyzed.' }));
  }), onPause: () => { pauses++; }, onEvidence: ({ evidence }) => {
    writes++; assert.equal(evidence.state, 'security_alert_notice');
    assert.equal(evidence.alert.blocked, false); assert.equal(evidence.alert.severity, 'informational');
  } });
  for (let i = 0; i < 2; i++) {
    assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => { calls++; return 'done'; } }), 'done');
  }
  assert.equal(calls, 2);
  assert.equal(writes, 1);
  assert.equal(pauses, 0);
  assert.equal(observer.status(CONTEXT).pause.state, 'not_required');
});

test('informational notice can later become a real quarantine hold', async () => {
  let offset = 0, paused = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => snapshot(alert({
    text: ++offset === 1 ? 'Auto-Sandbox: fixture-task.exe is being analyzed' : 'fixture-task.exe was quarantined',
  }))), onPause: () => { paused++; } });
  assert.equal((await observer.check({ context: CONTEXT })).state, 'security_alert_notice');
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.equal(paused, 1);
  assert.equal(observer.status(CONTEXT).alert.blocked, true);
});

test('a transient informational notice remains retrievable after disappearance without pausing', async () => {
  let inspections = 0, writes = 0, finish;
  const outcome = new Promise(resolve => { finish = resolve; });
  const observer = createSecurityAlertObserver({ ...options(async () => {
    inspections++;
    if (inspections === 2) { finish('completed'); return snapshot(alert({ text: 'Auto-Sandbox: fixture-task.exe is being analyzed' })); }
    return empty();
  }), onEvidence: () => { writes++; } });
  assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => outcome }), 'completed');
  assert.equal(observer.status(CONTEXT).state, 'not_observed');
  assert.equal(observer.status(CONTEXT).last_notice.state, 'security_alert_notice');
  assert.equal(observer.status(CONTEXT).last_notice.alert.blocked, false);
  assert.equal(writes, 1);
});

test('explicitly negated quarantine or stopping analysis is informational', () => {
  for (const text of ['Security alert: fixture-task.exe not quarantined', 'Auto-Sandbox: fixture-task.exe never quarantined',
    'Security alert: fixture-task.exe has not been quarantined', 'Auto-Sandbox: fixture-task.exe. We stopped analyzing']) {
    const result = classifySecurityAlerts(snapshot(alert({ text })), CONTEXT);
    assert.equal(result.state, 'alert');
    assert.equal(result.alert.blocked, false);
  }
});

test('provider matched-path metadata cannot turn another artifact into a match', () => {
  const result = classifySecurityAlerts(snapshot(alert({ matched_path: 'C:\\Other\\fixture-task.exe' })), CONTEXT);
  assert.equal(result.state, 'not_observed');
});

test('another blocked file in the same Norton window cannot hold the current sandbox notice', () => {
  for (const text of [
    'Program blocked: other.exe\nAuto-Sandbox: fixture-task.exe is being analyzed',
    'File blocked: [path redacted]\nAuto-Sandbox: fixture-task.exe is being analyzed',
  ]) {
    const result = classifySecurityAlerts(snapshot(alert({ text })), CONTEXT);
    assert.equal(result.state, 'alert');
    assert.equal(result.alert.blocked, false);
    assert.doesNotMatch(result.alert.text, /other\.exe|File blocked/);
  }
});

test('separate accessible block label and artifact filename can identify a real block', () => {
  const result = classifySecurityAlerts(snapshot(alert({ text: 'Program blocked\nfixture-task.exe' })), CONTEXT);
  assert.equal(result.state, 'alert');
  assert.equal(result.alert.blocked, true);
});

test('preflight alert blocks dispatch, pauses once and records UTC/path/hash', async () => {
  let calls = 0, pauses = 0, writes = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => snapshot(alert())),
    onPause: ({ evidence }) => { pauses++; assert.equal(evidence.pause.scope, 'artifact'); },
    onEvidence: ({ evidence }) => { writes++; assert.equal(evidence.observed_at, CLOCK);
      assert.equal(evidence.context.artifact.path, CONTEXT.artifact.path);
      assert.equal(evidence.context.artifact.sha256, 'a'.repeat(64)); },
  });
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 100, call: () => { calls++; } }), securityError(false));
  assert.equal(calls, 0);
  assert.equal(pauses, 1);
  assert.equal(writes, 1);
  assert.equal(observer.status(CONTEXT).pause.hook, 'completed');
});

test('transient in-flight alert stays latched after disappearance and aborts call once', async () => {
  let inspections = 0, paused = 0, callSignal;
  const observer = createSecurityAlertObserver({ ...options(async () => ++inspections === 2 ? snapshot(alert()) : empty()),
    onPause: () => { paused++; },
  });
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 100,
    call: ({ signal }) => { callSignal = signal; return never(); } }), securityError(true));
  assert.equal(callSignal.aborted, true);
  assert.equal(paused, 1);
  assert.equal(classifySecurityAlerts(empty(), CONTEXT).state, 'not_observed');
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.equal(observer.status(CONTEXT).state, 'security_alert_observed');
  assert.equal(inspections, 2);
});

test('repeated windows and later commands deduplicate evidence and per-artifact pause', async () => {
  let writes = 0, pauses = 0, inspections = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => {
    inspections++; return snapshot(alert(), alert());
  }), onPause: () => { pauses++; }, onEvidence: () => { writes++; } });
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  await assert.rejects(observer.run({ context: { ...CONTEXT, command_id: 'fixture-2' },
    timeoutMs: 100, call: () => assert.fail('held artifact must not dispatch') }), securityError(false));
  assert.equal(writes, 1);
  assert.equal(pauses, 1);
  assert.equal(inspections, 1);
});

test('concurrent repeated observations cannot duplicate pause/evidence', async () => {
  let pauses = 0, writes = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => snapshot(alert())),
    onPause: () => { pauses++; }, onEvidence: () => { writes++; } });
  const results = await Promise.allSettled([observer.check({ context: CONTEXT }), observer.check({ context: CONTEXT })]);
  assert.ok(results.every(result => result.status === 'rejected' && result.reason instanceof SecurityAlertError));
  assert.equal(pauses, 1);
  assert.equal(writes, 1);
});

test('an unrelated artifact task can still complete after another artifact is paused', async () => {
  const observer = createSecurityAlertObserver(options(async () => snapshot(alert())));
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  const result = await observer.run({ context: { ...CONTEXT, artifact: {
    path: 'C:\\Project\\Build\\independent-task.exe', sha256: 'b'.repeat(64),
  } }, timeoutMs: 100, call: () => 'independent-result' });
  assert.equal(result, 'independent-result');
  assert.equal(observer.status(CONTEXT).state, 'security_alert_observed');
});

test('screenshot is opt-in; unavailable capture preserves the alert and pause', async () => {
  let captureCalls = 0;
  const inspect = async ({ screenshot }) => { assert.equal(screenshot, false); return snapshot(alert()); };
  const capture = () => { captureCalls++; throw new Error('blocked screenshot with private data'); };
  const off = createSecurityAlertObserver({ ...options(inspect), capture });
  await assert.rejects(off.check({ context: CONTEXT }), securityError(false));
  assert.equal(captureCalls, 0);
  assert.equal(off.status(CONTEXT).screenshot.status, 'not_requested');
  const on = createSecurityAlertObserver({ ...options(inspect), capture, requestScreenshot: true });
  await assert.rejects(on.check({ context: CONTEXT }), securityError(false));
  assert.equal(captureCalls, 1);
  assert.deepEqual(on.status(CONTEXT).screenshot, { status: 'unavailable' });
});

test('optional screenshot hook output never forwards pixels, paths or URLs', async () => {
  const observer = createSecurityAlertObserver({ ...options(async () => snapshot(alert())), requestScreenshot: true,
    capture: async () => ({ status: 'captured', png: 'private pixels', path: 'private path', url: 'https://private.test' }),
  });
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.deepEqual(observer.status(CONTEXT).screenshot, { status: 'captured_locally' });
});

test('inspection unavailable continues independently and deduplicates unavailable evidence', async () => {
  let writes = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => { throw new Error('private denied error'); }),
    onEvidence: ({ evidence }) => { writes++; assert.equal(evidence.reason, 'adapter_unavailable'); },
  });
  assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => 42 }), 42);
  assert.equal(observer.status(CONTEXT).state, 'unavailable');
  assert.equal(writes, 1);
  assert.doesNotMatch(JSON.stringify(observer.status()), /private denied/);
});

test('no artifact context performs no desktop inspection but continues the command', async () => {
  let inspections = 0;
  const observer = createSecurityAlertObserver(options(() => { inspections++; return empty(); }));
  assert.equal(await observer.run({ context: { command_id: 'no-artifact' }, timeoutMs: 100, call: () => 'value' }), 'value');
  assert.equal(inspections, 0);
  assert.equal(observer.status().reason, 'artifact_context_unavailable');
});

test('noncooperative inspection is bounded and its abort signal is closed', async () => {
  let signal;
  const observer = createSecurityAlertObserver({ ...options(({ signal: incoming }) => { signal = incoming; return never(); }),
    probeTimeoutMs: 5,
  });
  const start = performance.now();
  assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => 'done' }), 'done');
  assert.ok(performance.now() - start < 5000);
  assert.equal(signal.aborted, true);
  assert.equal(observer.status().reason, 'inspection_timeout');
});

test('an overdue preflight cannot dispatch when event-loop delay outruns the deadline', async () => {
  let calls = 0;
  const observer = createSecurityAlertObserver(options(() => {
    const until = performance.now() + 5;
    while (performance.now() < until) { /* deterministic simulated synchronous adapter delay */ }
    return empty();
  }));
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 1,
    call: () => { calls++; return 'must-not-start'; } }), error => {
    assert.equal(error.code, 'SECURITY_OBSERVATION_TIMEOUT');
    assert.equal(error.dispatched, false);
    return true;
  });
  assert.equal(calls, 0);
});

test('noncooperative command stops at the authorized deadline and no polling continues', async () => {
  let inspections = 0, callSignal;
  const observer = createSecurityAlertObserver(options(async () => { inspections++; return empty(); }));
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 20,
    call: ({ signal }) => { callSignal = signal; return never(); } }), error => {
    assert.equal(error.code, 'SECURITY_OBSERVATION_TIMEOUT');
    assert.equal(error.dispatched, true);
    assert.equal(error.outcome_uncertain, true);
    return true;
  });
  assert.equal(callSignal.aborted, true);
  const finalCount = inspections;
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(inspections, finalCount);
});

test('a completion reply cannot bypass the final matching-alert check', async () => {
  let inspections = 0;
  const observer = createSecurityAlertObserver(options(async () => ++inspections === 2 ? snapshot(alert()) : empty()));
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 100, call: () => 'must-not-succeed' }), securityError(true));
});

test('pause/evidence hooks failing cannot remove the in-memory hold', async () => {
  const observer = createSecurityAlertObserver({ ...options(async () => snapshot(alert())),
    onPause: () => { throw new Error('private hold-file path'); }, onEvidence: () => never(), hookTimeoutMs: 3,
  });
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.equal(observer.status().pause.hook, 'unavailable');
  assert.equal(observer.status().evidence_storage.reason, 'evidence_hook_timeout');
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
});

test('external cancellation closes the inspector and prevents dispatch', async () => {
  const abort = new AbortController();
  const observer = createSecurityAlertObserver(options(never));
  const reason = new Error('owner stopped command');
  const pending = observer.run({ context: CONTEXT, timeoutMs: 100, signal: abort.signal,
    call: () => assert.fail('must not dispatch') });
  abort.abort(reason);
  await assert.rejects(pending, error => error === reason);
});

test('invalid options, malformed probe bounds and excessive snapshots are rejected', async () => {
  assert.throws(() => createSecurityAlertObserver({}), TypeError);
  assert.throws(() => createSecurityAlertObserver({ inspect: empty, pollMs: 0 }), TypeError);
  assert.throws(() => createSecurityAlertObserver({ inspect: empty, requestScreenshot: 'yes' }), TypeError);
  const observer = createSecurityAlertObserver(options(empty));
  await assert.rejects(observer.run({ context: CONTEXT, timeoutMs: 0, call: empty }), TypeError);
  await assert.rejects(observer.check({ context: CONTEXT, timeoutMs: 0 }), TypeError);
  assert.equal(classifySecurityAlerts(snapshot(...Array.from({ length: 65 }, alert)), CONTEXT).reason, 'provider_window_limit');
});

test('current exact-artifact Norton history fallback has honest source/event identity and continues', async () => {
  let pauses = 0, writes = 0;
  const observer = createSecurityAlertObserver({ ...options(async ({ sinceUtc }) => {
    assert.equal(sinceUtc, CLOCK); return historySnapshot([historyEvent()]);
  }), onPause: () => { pauses++; }, onEvidence: ({ evidence }) => {
    writes++; assert.equal(evidence.alert.source, HISTORY_SOURCE);
    assert.equal(evidence.alert.event_at, CLOCK);
    assert.equal(evidence.alert.process, 'Norton log');
    assert.equal(evidence.alert.pid, null); assert.equal(evidence.alert.hwnd, null);
  } });
  assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => 'complete' }), 'complete');
  assert.equal(pauses, 0); assert.equal(writes, 1);
  assert.equal(observer.status(CONTEXT).state, 'security_alert_notice');
});

test('history cannot correlate stale/future/invalid/other-artifact or untrusted source records', () => {
  for (const extra of [
    { event_at: '2026-10-12T22:59:58.999Z' }, { event_at: '2026-10-12T23:00:00.001Z' },
    { event_at: 'invalid-time' }, { event_at: '2026-10-12T23:00:00+00:00' },
    { artifact_path: 'C:\\Other\\fixture-task.exe' }, { artifact_path: 'fixture-task.exe' },
    { source: 'unrelated history' }, { kind: 'unknown' }, { result: 'Welcome home' },
  ]) assert.equal(classifySecurityAlerts(historySnapshot([historyEvent(extra)]), CONTEXT, historyScope).state, 'unavailable');
  assert.equal(classifySecurityAlerts(historySnapshot([historyEvent()], { history_source: 'untrusted source' }), CONTEXT, historyScope).reason,
    'log_history_invalid');
  assert.equal(classifySecurityAlerts(historySnapshot([historyEvent()]), CONTEXT).reason, 'log_history_scope_unavailable');
});

test('history block requires explicit blocking result instead of a kind label alone', async () => {
  const informational = classifySecurityAlerts(historySnapshot([historyEvent({ kind: 'block' })]), CONTEXT, historyScope);
  assert.equal(informational.alert.blocked, false);
  const observer = createSecurityAlertObserver(options(async () => historySnapshot([
    historyEvent({ kind: 'block', result: 'Execution denied' }),
  ])));
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.equal(observer.status(CONTEXT).alert.source, HISTORY_SOURCE);
  assert.equal(observer.status(CONTEXT).alert.blocked, true);
  assert.equal(observer.status(CONTEXT).alert.pid, null);
  assert.equal(observer.status(CONTEXT).alert.result, 'denied');
  assert.equal(observer.status(CONTEXT).alert.text, 'Execution denied');
});

test('a log event never invents a window for optional capture', async () => {
  let captures = 0;
  const observer = createSecurityAlertObserver({ ...options(async () => historySnapshot([
    historyEvent({ kind: 'block', result: 'File was quarantined' }),
  ])), requestScreenshot: true, capture: () => { captures++; return { status: 'captured' }; } });
  await assert.rejects(observer.check({ context: CONTEXT }), securityError(false));
  assert.equal(captures, 0);
  assert.deepEqual(observer.status(CONTEXT).screenshot, { status: 'unavailable', reason: 'window_unavailable_for_log_event' });
});

test('history permits only the documented one-second timestamp rounding window', () => {
  const rounded = classifySecurityAlerts(historySnapshot([historyEvent({ event_at: '2026-10-12T22:59:59.000Z' })]), CONTEXT, historyScope);
  assert.equal(rounded.state, 'alert');
  assert.equal(rounded.alert.timestamp_resolution_ms, 1000);
  assert.equal(classifySecurityAlerts(historySnapshot([historyEvent({ event_at: '2026-10-12T22:59:58.999Z' })]), CONTEXT, historyScope).state,
    'unavailable');
});

test('an informational window or earlier history notice cannot hide a current block', () => {
  const notices = [historyEvent(), historyEvent({ kind: 'block', result: 'File was quarantined' })];
  const result = classifySecurityAlerts(historySnapshot(notices, { available: true,
    windows: [alert({ text: 'Auto-Sandbox: fixture-task.exe being analyzed' })] }), CONTEXT, historyScope);
  assert.equal(result.alert.blocked, true);
  assert.equal(result.alert.result, 'quarantined');
  const windows = classifySecurityAlerts(snapshot(alert({ text: 'Auto-Sandbox: fixture-task.exe being analyzed' }), alert()), CONTEXT);
  assert.equal(windows.alert.blocked, true);
});

test('history scope stays at authorized run start across every poll', async () => {
  let clock = Date.parse(CLOCK), inspections = 0, finish;
  const outcome = new Promise(resolve => { finish = resolve; });
  const observer = createSecurityAlertObserver({ ...options(async ({ sinceUtc }) => {
    assert.equal(sinceUtc, CLOCK);
    if (++inspections === 2) finish('done');
    clock += 1;
    return historySnapshot([historyEvent()]);
  }), nowUtc: () => new Date(clock).toISOString() });
  assert.equal(await observer.run({ context: CONTEXT, timeoutMs: 100, call: () => outcome }), 'done');
  assert.ok(inspections >= 3);
});
