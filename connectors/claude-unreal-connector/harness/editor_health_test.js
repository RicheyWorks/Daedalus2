// SPDX-License-Identifier: MIT
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { classify, guardedCall, EditorHealthError } = require('../extension/server/editor-health.js');

const PID = 4200;
const START_TIME = '2026-10-12T22:00:00.000Z';
const process = (pid = PID, name = 'UnrealEditor') => ({ pid, name });
const mainWindow = (pid = PID, extra = {}) => ({
  pid, process: 'UnrealEditor', title: 'Daedalus - Unreal Editor',
  main: true, owner: 0, enabled: true, hwnd: String(pid), ...extra,
});
const healthy = (pid = PID) => ({ ok: true, processes: [process(pid)], windows: [mainWindow(pid)] });
const session = (startTime = START_TIME) => ({
  ...healthy(), processes: [{ ...process(), start_time: startTime }],
});
const recovery = () => ({
  ok: true, processes: [process()], windows: [mainWindow(PID, { title: 'Restore Packages' })],
});
const exited = () => ({ ok: true, processes: [], windows: [] });
const crashed = () => ({
  ok: true, processes: [process(9000, 'CrashReportClient')],
  windows: [{ pid: 9000, process: 'CrashReportClient', title: 'DaedalusRealm Crash Reporter', main: true, owner: 0, enabled: true, hwnd: '9000' }],
});
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const never = () => new Promise(() => {});

test('a health error rejected by an in-flight probe aborts the dispatched call', async () => {
  let probes = 0, signal;
  await assert.rejects(guardedCall({
    timeoutMs: 100, pollMs: 5,
    probe: async () => {
      if (++probes === 1) return healthy();
      throw new EditorHealthError('recovery_required', { reason: 'provider_detected_recovery' });
    },
    call: ({ signal: callSignal }) => { signal = callSignal; return never(); },
  }), error => error.state === 'recovery_required' && error.dispatched && error.outcome_uncertain);
  assert.equal(signal.aborted, true);
});

function sequence(...snapshots) {
  const requests = [];
  let offset = 0;
  const probe = async request => {
    requests.push(request);
    const value = snapshots[Math.min(offset++, snapshots.length - 1)];
    return typeof value === 'function' ? value(request) : value;
  };
  return { probe, requests };
}

function expectHealthError(state, dispatched) {
  return error => {
    assert.ok(error instanceof EditorHealthError);
    assert.equal(error.state, state);
    assert.equal(error.code, state.toUpperCase());
    assert.equal(error.dispatched, dispatched);
    assert.equal(error.outcome_uncertain, dispatched);
    assert.equal(typeof error.details, 'object');
    return true;
  };
}

test('a healthy editor is available without claiming the bridge is ready', () => {
  const result = classify(healthy());
  assert.equal(result.state, 'available');
  assert.equal(result.pid, PID);
  assert.equal(result.details.bridge_ready, false);
});

test('Restore Packages blocks even when Windows reports it as the main window', () => {
  assert.equal(classify(recovery()).state, 'recovery_required');
});

test('a secondary Restore Packages window takes priority over an available main window', () => {
  const snapshot = healthy();
  snapshot.windows.push(mainWindow(PID, { title: 'Restore Packages', main: false, owner: PID }));
  assert.equal(classify(snapshot).state, 'recovery_required');
});

test('recovery takes priority when a crash reporter is also present', () => {
  const snapshot = recovery();
  snapshot.processes.push(process(9000, 'CrashReportClient'));
  assert.equal(classify(snapshot).state, 'recovery_required');
});

test('a crash reporter process blocks editor dispatch', () => {
  const snapshot = healthy();
  snapshot.processes.push(process(9000, 'CrashReportClient'));
  assert.equal(classify(snapshot).state, 'crash_reporter_present');
});

test('a crash reporter window blocks editor dispatch', () => {
  const snapshot = healthy();
  snapshot.windows.push({ pid: 9000, process: 'CrashReportClient', title: 'DaedalusRealm Crash Reporter', main: true, owner: 0, enabled: true, hwnd: '9000' });
  assert.equal(classify(snapshot).state, 'crash_reporter_present');
});

test('a missing bound editor with a crash reporter is crashed with unconfirmed association', () => {
  const health = classify(crashed(), PID);
  assert.equal(health.state, 'crashed');
  assert.equal(health.details.reason, 'editor_exited_with_crash_reporter');
  assert.equal(health.details.association, 'unconfirmed');
});

test('no editor plus the reported DaedalusRealm crash reporter title is crashed', () => {
  const snapshot = crashed();
  snapshot.processes = [];
  const health = classify(snapshot);
  assert.equal(health.state, 'crashed');
  assert.equal(health.details.reason, 'editor_exited_with_crash_reporter');
  assert.equal(health.details.association, 'unconfirmed');
});

test('project-scoped crash metadata retains safe labels without claiming association', () => {
  const crash_evidence = {
    project: 'DaedalusRealm', signature: 'DXGI_ERROR_INVALID_CALL',
    backend: 'D3D12', renderer: 'NVIDIA GeForce RTX',
  };
  const health = classify({ ...crashed(), crash_evidence }, PID);
  assert.equal(health.state, 'crashed');
  assert.deepEqual(health.details.crash_evidence, crash_evidence);
  assert.equal(health.details.association, 'unconfirmed');
});

test('arbitrary and invalid crash metadata fields are excluded', () => {
  const health = classify({
    ...crashed(),
    crash_evidence: {
      project: 'DaedalusRealm', signature: 'DXGI_ERROR_INVALID_CALL',
      backend: 12, renderer: 'x'.repeat(257),
      file_path: 'C:\\fake\\private.log', token: 'unsafe-placeholder', payload: { arbitrary: true },
    },
  }, PID);
  assert.deepEqual(health.details.crash_evidence, {
    project: 'DaedalusRealm', signature: 'DXGI_ERROR_INVALID_CALL',
  });
  assert.equal(health.details.association, 'unconfirmed');
});

test('crash metadata without a bounded nonblank project is omitted', () => {
  for (const project of [undefined, null, '', '  ', 'x'.repeat(257), 42]) {
    const health = classify({
      ...crashed(), crash_evidence: { project, signature: 'DXGI_ERROR_INVALID_CALL', backend: 'D3D12' },
    }, PID);
    assert.equal(health.state, 'crashed');
    assert.equal(Object.hasOwn(health.details, 'crash_evidence'), false);
    assert.equal(health.details.association, 'unconfirmed');
  }
});

test('absence distinguishes no editor from an exited bound editor', () => {
  assert.equal(classify(exited()).state, 'editor_not_running');
  assert.equal(classify(exited(), PID).state, 'editor_exited');
  assert.equal(classify(healthy(PID + 1), PID).state, 'editor_exited');
});

test('an editor process without a visible root window is still loading', () => {
  assert.equal(classify({ ok: true, processes: [process()], windows: [] }).state, 'editor_loading');
  assert.equal(classify({
    ok: true, processes: [process()],
    windows: [mainWindow(PID, { title: 'Output Log', main: false, owner: PID })],
  }).state, 'editor_loading');
});

test('multiple editors are ambiguous until a PID is supplied', () => {
  const snapshot = healthy();
  snapshot.processes.push(process(PID + 1));
  snapshot.windows.push(mainWindow(PID + 1));
  assert.equal(classify(snapshot).state, 'editor_ambiguous');
  assert.equal(classify(snapshot, PID).state, 'available');
  assert.equal(classify(snapshot, PID).pid, PID);
});

test('an unknown owned secondary window is a modal blocker', () => {
  const snapshot = healthy();
  snapshot.windows.push(mainWindow(PID, { title: 'Confirm overwrite', main: false, owner: PID, hwnd: '4300' }));
  assert.equal(classify(snapshot).state, 'modal_blocked');
});

test('a disabled root window blocks even without a visible dialog', () => {
  const snapshot = healthy();
  snapshot.windows[0].enabled = false;
  assert.equal(classify(snapshot).state, 'modal_blocked');
});

test('Save Content blocks even when misreported as an unowned main window', () => {
  const snapshot = healthy();
  snapshot.windows[0].title = 'Save Content';
  assert.equal(classify(snapshot).state, 'modal_blocked');
});

test('a known Unreal tool panel does not block an enabled editor', () => {
  const snapshot = healthy();
  snapshot.windows.push(mainWindow(PID, { title: 'Output Log', main: false, owner: PID, hwnd: '4400' }));
  assert.equal(classify(snapshot).state, 'available');
});

test('failed and malformed snapshots fail closed', () => {
  for (const snapshot of [null, undefined, {}, { ok: false, error: 'probe unavailable' }, { ok: true, processes: 'bad', windows: [] }]) {
    assert.equal(classify(snapshot).state, 'probe_failed');
  }
});

test('healthy dispatch returns the actual value after a fresh final probe', async () => {
  const value = { accepted: true, nested: { untouched: 1 } };
  const fake = sequence(healthy());
  let calls = 0;
  let request;
  const result = await guardedCall({
    probe: fake.probe,
    call: async args => { calls++; request = args; return value; },
    timeoutMs: 500, pollMs: 100, probeTimeoutMs: 100,
  });
  assert.strictEqual(result, value);
  assert.equal(calls, 1);
  assert.ok(request.signal instanceof AbortSignal);
  assert.equal(request.expectedPid, PID);
  assert.ok(request.remainingMs > 0 && request.remainingMs <= 500);
  assert.ok(fake.requests.length >= 2);
  for (const request of fake.requests.slice(1)) assert.equal(request.expectedPid, PID);
});

test('a recovery window before dispatch rejects without calling or retrying', async () => {
  let calls = 0;
  await assert.rejects(guardedCall({
    probe: async () => recovery(), call: async () => { calls++; }, timeoutMs: 500,
  }), expectHealthError('recovery_required', false));
  assert.equal(calls, 0);
});

test('an absent editor before dispatch rejects without invoking the call', async () => {
  let calls = 0;
  await assert.rejects(guardedCall({
    probe: async () => exited(), call: async () => { calls++; }, timeoutMs: 500,
  }), expectHealthError('editor_not_running', false));
  assert.equal(calls, 0);
});

test('no editor and the reported crash title block before dispatch with a certain outcome', async () => {
  let calls = 0;
  const evidence = [];
  const snapshot = crashed();
  snapshot.processes = [];
  await assert.rejects(guardedCall({
    probe: async () => snapshot, call: async () => { calls++; },
    onEvidence: value => evidence.push(value), timeoutMs: 500,
  }), error => {
    expectHealthError('crashed', false)(error);
    assert.equal(error.details.reason, 'editor_exited_with_crash_reporter');
    assert.equal(error.details.association, 'unconfirmed');
    return true;
  });
  assert.equal(calls, 0);
  assert.equal(evidence.at(-1).state, 'crashed');
  assert.equal(evidence.at(-1).details.windows[0].title, 'DaedalusRealm Crash Reporter');
});

test('a hung initial probe is bounded and does not dispatch', async () => {
  let calls = 0;
  let probeSignal;
  const started = Date.now();
  await assert.rejects(guardedCall({
    probe: ({ signal }) => { probeSignal = signal; return never(); },
    call: async () => { calls++; }, timeoutMs: 500, probeTimeoutMs: 30,
  }), expectHealthError('probe_failed', false));
  assert.equal(calls, 0);
  assert.ok(probeSignal.aborted);
  assert.ok(Date.now() - started < 1500, 'hung probe must not wait indefinitely');
});

test('a shorter overall deadline reports timeout before a hung initial probe limit', async () => {
  let calls = 0;
  let probeSignal;
  await assert.rejects(guardedCall({
    probe: ({ signal }) => { probeSignal = signal; return never(); },
    call: async () => { calls++; }, timeoutMs: 40, probeTimeoutMs: 500,
  }), expectHealthError('timeout', false));
  assert.equal(calls, 0);
  assert.ok(probeSignal.aborted);
});

test('a recovery window during a call aborts it and marks the outcome uncertain', async () => {
  let calls = 0;
  let callSignal;
  const fake = sequence(healthy(), recovery());
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: ({ signal }) => { calls++; callSignal = signal; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), expectHealthError('recovery_required', true));
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(fake.requests[1].expectedPid, PID);
});

test('a bound editor exiting during a call aborts it', async () => {
  let callSignal;
  const fake = sequence(healthy(), exited());
  await assert.rejects(guardedCall({
    probe: fake.probe, call: ({ signal }) => { callSignal = signal; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), expectHealthError('editor_exited', true));
  assert.ok(callSignal.aborted);
});

test('crash evidence after dispatch aborts the call and never retries it', async () => {
  const fake = sequence(healthy(), crashed());
  const evidence = [];
  let calls = 0;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: ({ signal }) => { calls++; callSignal = signal; return never(); },
    onEvidence: value => evidence.push(value), timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), error => {
    expectHealthError('crashed', true)(error);
    assert.equal(error.details.reason, 'editor_exited_with_crash_reporter');
    assert.equal(error.details.association, 'unconfirmed');
    return true;
  });
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(evidence.at(-1).state, 'crashed');
  assert.equal(evidence.at(-1).details.windows[0].title, 'DaedalusRealm Crash Reporter');
  assert.equal(fake.requests[1].expectedPid, PID);
});

test('a completed call is rejected when its final probe discovers recovery', async () => {
  let calls = 0;
  let callSignal;
  const evidence = [];
  const fake = sequence(healthy(), recovery());
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: async ({ signal }) => { calls++; callSignal = signal; return 'stale success'; },
    timeoutMs: 500, pollMs: 100, probeTimeoutMs: 100,
    onEvidence: value => evidence.push(value),
  }), expectHealthError('recovery_required', true));
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(evidence.at(-1).state, 'recovery_required');
  assert.equal(evidence.at(-1).details.windows[0].title, 'Restore Packages');
});

test('call completion waits for an in-progress monitor before considering success', async () => {
  const monitorStarted = deferred();
  const monitorResult = deferred();
  const callResult = deferred();
  let probes = 0;
  let callSignal;
  const run = guardedCall({
    probe: async () => {
      probes++;
      if (probes === 1) return healthy();
      monitorStarted.resolve();
      return monitorResult.promise;
    },
    call: ({ signal }) => { callSignal = signal; return callResult.promise; },
    timeoutMs: 1000, pollMs: 5, probeTimeoutMs: 500,
  });
  await monitorStarted.promise;
  callResult.resolve('stale success');
  monitorResult.resolve(recovery());
  await assert.rejects(run, expectHealthError('recovery_required', true));
  assert.ok(callSignal.aborted);
});

test('the guard does not migrate to a replacement editor PID', async () => {
  let calls = 0;
  const fake = sequence(healthy(), healthy(PID + 1));
  await assert.rejects(guardedCall({
    probe: fake.probe, call: () => { calls++; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), expectHealthError('editor_exited', true));
  assert.equal(calls, 1);
  assert.equal(fake.requests[1].expectedPid, PID);
});

test('the initial editor generation is bound into call and later probe requests', async () => {
  const fake = sequence(session());
  let request;
  assert.equal(await guardedCall({
    probe: fake.probe, call: async args => { request = args; return 'done'; },
    timeoutMs: 500, pollMs: 100, probeTimeoutMs: 100,
  }), 'done');
  assert.equal(request.expectedPid, PID);
  assert.equal(request.expectedStartTime, START_TIME);
  assert.ok(fake.requests.length >= 2);
  for (const request of fake.requests.slice(1)) {
    assert.equal(request.expectedPid, PID);
    assert.equal(request.expectedStartTime, START_TIME);
  }
});

test('a replacement session reusing the same PID aborts the dispatched call', async () => {
  const fake = sequence(session(), session('2026-10-12T22:01:00.000Z'));
  let calls = 0;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: ({ signal }) => { calls++; callSignal = signal; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), error => {
    expectHealthError('editor_exited', true)(error);
    assert.equal(error.details.reason, 'session_changed');
    return true;
  });
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(fake.requests[1].expectedStartTime, START_TIME);
});

test('missing generation evidence cannot inherit an already bound session', async () => {
  const fake = sequence(session(), healthy());
  let callSignal;
  await assert.rejects(guardedCall({
    probe: fake.probe, call: ({ signal }) => { callSignal = signal; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 100,
  }), error => {
    expectHealthError('editor_exited', true)(error);
    assert.equal(error.details.reason, 'session_changed');
    return true;
  });
  assert.ok(callSignal.aborted);
});

test('an explicit PID selects one editor and remains bound through the final probe', async () => {
  const snapshot = healthy();
  snapshot.processes.push(process(PID + 1));
  snapshot.windows.push(mainWindow(PID + 1));
  const fake = sequence(snapshot);
  let callPid;
  assert.equal(await guardedCall({
    expectedPid: PID + 1, probe: fake.probe,
    call: async ({ expectedPid }) => { callPid = expectedPid; return 'done'; },
    timeoutMs: 500, pollMs: 100, probeTimeoutMs: 100,
  }), 'done');
  assert.equal(callPid, PID + 1);
  for (const request of fake.requests) assert.equal(request.expectedPid, PID + 1);
});

test('a hung call reaches the overall deadline and receives an abort signal', async () => {
  let calls = 0;
  let callSignal;
  const started = Date.now();
  await assert.rejects(guardedCall({
    probe: async () => healthy(),
    call: ({ signal }) => { calls++; callSignal = signal; return never(); },
    timeoutMs: 40, pollMs: 5, probeTimeoutMs: 20,
  }), expectHealthError('timeout', true));
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.ok(Date.now() - started < 1500, 'hung call must not wait indefinitely');
});

test('a hung monitor probe is bounded and aborts the dispatched call', async () => {
  let probes = 0;
  let monitorSignal;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: ({ signal }) => {
      if (++probes === 1) return healthy();
      monitorSignal = signal;
      return never();
    },
    call: ({ signal }) => { callSignal = signal; return never(); },
    timeoutMs: 500, pollMs: 5, probeTimeoutMs: 30,
  }), expectHealthError('probe_failed', true));
  assert.ok(monitorSignal.aborted);
  assert.ok(callSignal.aborted);
});

test('a hung final probe cannot return stale success', async () => {
  let probes = 0;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: () => ++probes === 1 ? healthy() : never(),
    call: async ({ signal }) => { callSignal = signal; return 'stale success'; },
    timeoutMs: 500, pollMs: 100, probeTimeoutMs: 30,
  }), expectHealthError('probe_failed', true));
  assert.ok(callSignal.aborted);
});

test('new explicitly requested operation with caller recovery gate resolved', async () => {
  let calls = 0;
  let recoveryHeld = true;
  const call = async () => { calls++; return 'new success'; };
  const beforeDispatch = () => {
    if (recoveryHeld) throw new EditorHealthError('recovery_required', { reason: 'caller_recovery_hold' });
  };
  await assert.rejects(guardedCall({ probe: async () => recovery(), call, beforeDispatch, timeoutMs: 500 }), expectHealthError('recovery_required', false));
  assert.equal(calls, 0);
  await assert.rejects(guardedCall({ probe: async () => healthy(), call, beforeDispatch, timeoutMs: 500 }), expectHealthError('recovery_required', false));
  assert.equal(calls, 0);
  recoveryHeld = false;
  assert.equal(await guardedCall({ probe: async () => healthy(), call, beforeDispatch, timeoutMs: 500 }), 'new success');
  assert.equal(calls, 1);
});

test('a caller recovery hold in beforeDispatch prevents invocation', async () => {
  let calls = 0;
  let gates = 0;
  let request;
  await assert.rejects(guardedCall({
    probe: async () => session(),
    beforeDispatch: args => {
      gates++;
      request = args;
      throw new EditorHealthError('recovery_required', { reason: 'caller_recovery_hold' });
    },
    call: async () => { calls++; }, timeoutMs: 500,
  }), error => {
    expectHealthError('recovery_required', false)(error);
    assert.equal(error.details.reason, 'caller_recovery_hold');
    return true;
  });
  assert.equal(gates, 1);
  assert.equal(calls, 0);
  assert.equal(request.expectedPid, PID);
  assert.equal(request.expectedStartTime, START_TIME);
  assert.ok(request.signal instanceof AbortSignal);
});

test('a hung beforeDispatch hook reaches the deadline without dispatching', async () => {
  let calls = 0;
  let gateSignal;
  await assert.rejects(guardedCall({
    probe: async () => healthy(),
    beforeDispatch: ({ signal }) => { gateSignal = signal; return never(); },
    call: async () => { calls++; }, timeoutMs: 40,
  }), expectHealthError('timeout', false));
  assert.equal(calls, 0);
  assert.ok(gateSignal.aborted);
});

test('an ordinary call failure is wrapped once and preserves its cause', async () => {
  const cause = new Error('transport failure');
  const fake = sequence(healthy());
  let calls = 0;
  await assert.rejects(guardedCall({
    probe: fake.probe, call: async () => { calls++; throw cause; }, timeoutMs: 500,
  }), error => {
    assert.ok(error instanceof EditorHealthError);
    assert.equal(error.code, 'CALL_FAILED');
    assert.strictEqual(error.cause, cause);
    assert.equal(error.dispatched, true);
    assert.equal(error.outcome_uncertain, true);
    return true;
  });
  assert.equal(calls, 1);
  assert.ok(fake.requests.length >= 2, 'ordinary failures require fresh health evidence');
});

test('immediate transport EOF yields recovery evidence instead of masking it as call failure', async () => {
  const cause = new Error('transport EOF');
  const fake = sequence(healthy(), recovery());
  const evidence = [];
  let calls = 0;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: ({ signal }) => { calls++; callSignal = signal; throw cause; },
    onEvidence: value => evidence.push(value), timeoutMs: 500, pollMs: 100,
  }), expectHealthError('recovery_required', true));
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(evidence.at(-1).state, 'recovery_required');
  assert.equal(evidence.at(-1).details.windows[0].title, 'Restore Packages');
  assert.equal(fake.requests.length, 2);
});

test('a transported health error preserves its state and details without another probe', async () => {
  const details = { reason: 'transport_recovery_hold', origin: 'socket_gate', window: { title: 'Restore Packages' } };
  const cause = new Error('recovery gate latched');
  const transportError = new EditorHealthError('recovery_required', details, false, cause);
  const fake = sequence(healthy());
  let calls = 0;
  let callSignal;
  await assert.rejects(guardedCall({
    probe: fake.probe,
    call: async ({ signal }) => { calls++; callSignal = signal; throw transportError; },
    timeoutMs: 500, pollMs: 100,
  }), error => {
    expectHealthError('recovery_required', true)(error);
    assert.deepEqual(error.details, details);
    assert.strictEqual(error.cause, transportError);
    assert.strictEqual(error.cause.cause, cause);
    return true;
  });
  assert.equal(calls, 1);
  assert.ok(callSignal.aborted);
  assert.equal(fake.requests.length, 1);
});

test('health evidence is emitted for preflight and final verification', async () => {
  const evidence = [];
  await guardedCall({
    probe: async () => healthy(), call: async () => 7, timeoutMs: 500,
    onEvidence: value => evidence.push(value),
  });
  assert.ok(evidence.length >= 2);
  assert.ok(evidence.every(value => value && typeof value === 'object'));
});
