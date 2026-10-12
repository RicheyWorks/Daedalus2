#!/usr/bin/env node
'use strict';

// Offline integration tests of the real stdio gateway. All sockets, process
// inventory commands, filesystem writes, and stdio are replaced in the VM.
// The actual health classifier/guard and persistent recovery latch are used.
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const health = require('../extension/server/editor-health');
const hold = require('../extension/server/recovery-hold');
const security = require('../extension/server/security-alert-observer');
const securityHold = require('../extension/server/security-alert-hold');
const securityLog = require('../extension/server/security-alert-log');

const serverPath = path.resolve(__dirname, '../extension/server/index.js');
const source = fs.readFileSync(serverPath, 'utf8');
const HOLD_FILE = 'C:\\offline-gateway\\recovery-hold.json';
const EVIDENCE_DIR = 'C:\\offline-gateway\\evidence';
const LOG_FILE = 'C:\\offline-gateway\\Unreal.log';
const copy = value => JSON.parse(JSON.stringify(value));

function inventory() {
  return { ok: true,
    processes: [{ pid: 101, name: 'UnrealEditor', start_time: 'session-1' }],
    windows: [{ pid: 101, process: 'UnrealEditor', title: 'Daedalus - Unreal Editor',
      main: true, owner: 0, enabled: true, hwnd: 1001 }] };
}
function recovery() {
  const value = inventory();
  value.windows.push({ pid: 101, process: 'UnrealEditor', title: 'Restore Packages',
    main: false, owner: 1001, enabled: true, hwnd: 1002 });
  return value;
}
function modal() {
  const value = inventory();
  value.windows.push({ pid: 101, process: 'UnrealEditor', title: 'Unidentified blocking prompt',
    main: false, owner: 1001, enabled: true, hwnd: 1003 });
  return value;
}
function crashed() {
  const value = inventory();
  value.processes.push({ pid: 202, name: 'CrashReportClient', start_time: 'crash-1' });
  value.windows.push({ pid: 202, process: 'CrashReportClient', title: 'Unreal Engine Crash Reporter',
    main: false, owner: 0, enabled: true, hwnd: 2001 });
  return value;
}

function memoryFs() {
  const files = new Map();
  const descriptors = new Map();
  const directories = new Set();
  let nextDescriptor = 10;
  const missing = () => Object.assign(new Error('Offline fixture file absent'), { code: 'ENOENT' });
  const stat = bytes => ({ size: bytes.length, isFile: () => true });
  const nameFor = target => {
    if (typeof target !== 'number') return String(target);
    if (!descriptors.has(target)) throw new Error('Invalid fixture descriptor');
    return descriptors.get(target);
  };
  const impl = {
    constants: fs.constants,
    lstatSync(name) {
      if (!files.has(String(name))) throw missing();
      return stat(files.get(String(name)));
    },
    openSync(name, flags) {
      name = String(name);
      if (flags === 'wx') {
        if (files.has(name)) throw Object.assign(new Error('Fixture file exists'), { code: 'EEXIST' });
        files.set(name, Buffer.alloc(0));
      } else if (!files.has(name)) throw missing();
      const descriptor = nextDescriptor++;
      descriptors.set(descriptor, name);
      return descriptor;
    },
    fstatSync(descriptor) { return stat(files.get(nameFor(descriptor))); },
    readSync(descriptor, buffer, offset, length, position) {
      const bytes = files.get(nameFor(descriptor));
      return bytes.copy(buffer, offset, position, Math.min(bytes.length, position + length));
    },
    writeFileSync(target, bytes) { files.set(nameFor(target), Buffer.from(bytes)); },
    fsyncSync(descriptor) { nameFor(descriptor); },
    closeSync(descriptor) {
      if (!descriptors.delete(descriptor)) throw new Error('Fixture descriptor already closed');
    },
    mkdirSync(name) { directories.add(String(name)); },
  };
  return { impl, files, descriptors, directories };
}

function gateway(options = {}) {
  const disk = options.disk || memoryFs();
  const state = {
    current: copy(options.inventory || inventory()), sockets: [], writes: [], probes: [], securityProbes: [],
    inputAttempts: [], stdout: [], stderr: [], streams: [], uuids: 0, replies: 0,
  };
  const env = { UNREAL_BRIDGE_HOST: '127.0.0.1', UNREAL_BRIDGE_PORT: '9877',
    UNREAL_RECOVERY_HOLD_FILE: HOLD_FILE, UNREAL_DIAGNOSTICS_DIR: EVIDENCE_DIR,
    ...(options.env || {}) };
  class Socket extends EventEmitter {
    constructor() { super(); this.destroyed = false; this.destroyCalls = 0; }
    write(bytes) {
      assert.equal(this.destroyed, false, 'A destroyed socket must not receive a dispatch');
      state.writes.push(JSON.parse(String(bytes)));
      if (options.onWrite) options.onWrite(state, this);
      else queueMicrotask(() => this.reply({ status: 'ok', result: { fixture: 'one reply' } }));
      return true;
    }
    reply(value) {
      if (!this.destroyed) {
        state.replies++;
        this.emit('data', Buffer.from(JSON.stringify(value) + '\n'));
      }
    }
    destroy() {
      this.destroyCalls++;
      if (this.destroyed) return this;
      this.destroyed = true;
      queueMicrotask(() => this.emit('close'));
      return this;
    }
  }
  const fakeNet = {
    createConnection(address) {
      assert.deepEqual(copy(address), { host: env.UNREAL_BRIDGE_HOST, port: Number(env.UNREAL_BRIDGE_PORT) });
      const socket = new Socket();
      state.sockets.push(socket);
      queueMicrotask(() => {
        if (options.onConnect) options.onConnect(state, socket);
        if (!socket.destroyed) socket.emit('connect');
      });
      return socket;
    },
  };
  const fakeChildProcess = {
    execFile(command, args, execOptions, callback) {
      assert.equal(command, 'powershell.exe');
      if (args.some(arg => String(arg).endsWith('security-alert-observer.ps1'))) {
        assert.equal(args.includes('-ExecutionPolicy'), false);
        assert.equal(execOptions.windowsHide, true);
        state.securityProbes.push({ args: [...args], signal: execOptions.signal });
        const snapshot = options.securitySnapshot || { available: false, reason: 'fixture_unavailable', windows: [] };
        queueMicrotask(() => callback(null, JSON.stringify(snapshot), ''));
        return {};
      }
      const op = args[args.indexOf('-Op') + 1];
      if (op !== 'list') {
        state.inputAttempts.push({ command, args: [...args] });
        throw new Error('Offline gateway test forbids automatic UI input or other process commands');
      }
      assert.equal(execOptions.windowsHide, true);
      const probe = { args: [...args], signal: execOptions.signal };
      state.probes.push(probe);
      if (options.onProbe) options.onProbe(state, probe);
      const snapshot = copy(state.current);
      queueMicrotask(() => callback(null, JSON.stringify(snapshot) + '\n', ''));
      return { kill() { throw new Error('No process exists in this offline fixture'); } };
    },
  };
  const fakeProcess = {
    platform: 'win32', env, stdin: new EventEmitter(),
    stdout: { write: bytes => state.stdout.push(String(bytes)) },
    stderr: { write: bytes => state.stderr.push(String(bytes)) },
    on() {}, exit() { throw new Error('Offline stdio must not exit the test process'); },
  };
  const allowed = {
    net: fakeNet, path, child_process: fakeChildProcess,
    readline: { createInterface() { const stream = new EventEmitter(); state.streams.push(stream); return stream; } },
    fs: disk.impl, os: { tmpdir: () => 'C:\\offline-gateway' },
    crypto: { randomUUID: () => 'evidence-' + (++state.uuids) },
    './editor-health': health, './recovery-hold': hold,
    './security-alert-observer': security, './security-alert-hold': securityHold,
    './security-alert-log': securityLog,
  };
  const context = { Buffer, AbortController, setTimeout, clearTimeout, queueMicrotask,
    process: fakeProcess, __dirname: path.dirname(serverPath), console,
    require(name) {
      if (!Object.hasOwn(allowed, name)) throw new Error('Unmocked gateway dependency: ' + name);
      return allowed[name];
    } };
  vm.runInNewContext(source + '\n;globalThis.gatewayUnderTest = {runTool, callUnreal, recoveryHold, TOOLS};',
    context, { filename: serverPath });
  return { ...context.gatewayUnderTest, state, disk };
}

function errorState(result, expected) {
  assert.equal(result.isError, true);
  const evidence = JSON.parse(result.content[0].text);
  assert.equal(evidence.state, expected);
  assert.equal(evidence.retry_safe, false);
  return evidence;
}
function noUi(subject) { assert.equal(subject.state.inputAttempts.length, 0); }
function noDispatch(subject) {
  assert.equal(subject.state.writes.length, 0);
  noUi(subject);
}
function persisted(subject) {
  assert.equal(subject.disk.files.has(HOLD_FILE), true, 'Recovery hold must be persisted');
  const value = JSON.parse(subject.disk.files.get(HOLD_FILE).toString('utf8'));
  assert.equal(value.state, 'recovery_required');
  assert.equal(value.version, 1);
  assert.equal(subject.disk.descriptors.size, 0, 'Fixture descriptors must be closed');
  return value;
}

const tests = [];
const test = (name, run) => tests.push({ name, run });

test('Restore Packages preflight blocks socket creation and persists recovery', async () => {
  const g = gateway({ inventory: recovery() });
  const evidence = errorState(await g.runTool('execute_python', { code: 'result = 1' }), 'recovery_required');
  assert.equal(evidence.dispatched, false);
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
  persisted(g);
});

test('Healthy inventory after a recovery dialog disappears does not release the live hold', async () => {
  const g = gateway({ inventory: recovery() });
  errorState(await g.runTool('unreal_status', {}), 'recovery_required');
  g.state.current = inventory();
  const result = errorState(await g.runTool('save', {}), 'recovery_required');
  assert.equal(result.details.reason, 'recovery_hold');
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
});

test('A new gateway instance reads the persistent hold even with healthy inventory', async () => {
  const disk = memoryFs();
  const first = gateway({ disk, inventory: recovery() });
  errorState(await first.runTool('unreal_status', {}), 'recovery_required');
  const second = gateway({ disk });
  const evidence = errorState(await second.runTool('get_level_info', {}), 'recovery_required');
  assert.equal(evidence.details.reason, 'recovery_hold');
  assert.equal(second.state.sockets.length, 0);
  noDispatch(second);
  persisted(second);
});

test('window_input cannot dismiss or close a held recovery dialog', async () => {
  const g = gateway({ inventory: recovery() });
  errorState(await g.runTool('unreal_status', {}), 'recovery_required');
  for (const args of [{ hwnd: 1002, keys: 'escape' }, { hwnd: 1002, action: 'close' }]) {
    errorState(await g.runTool('window_input', args), 'recovery_required');
  }
  noDispatch(g);
});

test('Manual window input preflight observes and holds new recovery before any UI input', async () => {
  const g = gateway({ inventory: recovery() });
  errorState(await g.runTool('window_input', { hwnd: 1002, keys: 'escape' }), 'recovery_required');
  noDispatch(g);
  persisted(g);
});

test('Manual window input preflight blocks an unknown modal without answering it', async () => {
  const g = gateway({ inventory: modal() });
  errorState(await g.runTool('window_input', { hwnd: 1003, action: 'close' }), 'modal_blocked');
  noDispatch(g);
});

test('Read-only window inventory remains usable while recovery is held', async () => {
  const g = gateway({ inventory: recovery() });
  errorState(await g.runTool('unreal_status', {}), 'recovery_required');
  const result = await g.runTool('editor_windows', { max_images: 0 });
  assert.equal(result.isError, undefined);
  assert.equal(JSON.parse(result.content.at(-1).text).windows[1].title, 'Restore Packages');
  noDispatch(g);
  persisted(g);
});

test('Healthy central call dispatches once and checks health at connect and after reply', async () => {
  const g = gateway();
  const result = await g.runTool('unreal_status', {});
  assert.equal(result.isError, undefined);
  assert.deepEqual(JSON.parse(result.content[0].text), { fixture: 'one reply' });
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.replies, 1);
  assert.equal(g.state.writes[0].type, 'ping');
  assert.equal(g.state.writes[0].params.bridge_timeout > 0, true);
  assert.equal(g.state.probes.length, 3, 'Preflight, socket-connect, and fresh final probes are required');
  assert.equal(g.state.sockets[0].destroyed, true);
  noUi(g);
});

test('An unknown modal blocks dispatch without automatic Escape or WM_CLOSE', async () => {
  const g = gateway({ inventory: modal() });
  const evidence = errorState(await g.runTool('save', {}), 'modal_blocked');
  assert.equal(evidence.dispatched, false);
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
});

test('CrashReportClient preflight blocks socket creation', async () => {
  const g = gateway({ inventory: crashed() });
  errorState(await g.runTool('unreal_status', {}), 'crash_reporter_present');
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
});

test('CrashReportClient after editor exit blocks dispatch as crashed', async () => {
  const snapshot = crashed();
  snapshot.processes = snapshot.processes.filter(item => item.name === 'CrashReportClient');
  snapshot.windows = snapshot.windows.filter(item => item.process === 'CrashReportClient');
  const g = gateway({ inventory: snapshot });
  errorState(await g.runTool('unreal_status', {}), 'crashed');
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
});

test('Recovery appearing as the socket connects blocks the first write', async () => {
  const g = gateway({ onConnect: state => { state.current = recovery(); } });
  errorState(await g.runTool('save', {}), 'recovery_required');
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.sockets[0].destroyed, true);
  noDispatch(g);
  persisted(g);
});

test('A changed editor PID at connect fails closed before a write', async () => {
  const g = gateway({ onConnect: state => {
    state.current.processes[0].pid = 102;
    state.current.windows[0].pid = 102;
  } });
  errorState(await g.runTool('execute_python', { code: 'result = 1' }), 'editor_exited');
  assert.equal(g.state.sockets.length, 1);
  noDispatch(g);
});

test('A reused editor PID with a new process session fails closed at connect', async () => {
  const g = gateway({ onConnect: state => { state.current.processes[0].start_time = 'session-2'; } });
  const evidence = errorState(await g.runTool('save', {}), 'editor_exited');
  assert.equal(evidence.details.reason, 'session_changed');
  noDispatch(g);
});

test('Transport EOF followed by recovery is classified and held without retry', async () => {
  const g = gateway({ onWrite(state, socket) {
    state.current = recovery();
    queueMicrotask(() => socket.emit('close'));
  } });
  const evidence = errorState(await g.runTool('save', {}), 'recovery_required');
  assert.equal(evidence.dispatched, true);
  assert.equal(evidence.outcome_uncertain, true);
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.sockets[0].destroyed, true);
  noUi(g);
  persisted(g);
});

test('The health monitor aborts a pending socket and never retries its dispatch', async () => {
  const g = gateway({ onWrite(state) { state.current = recovery(); } });
  const evidence = errorState(await g.runTool('save', {}), 'recovery_required');
  assert.equal(evidence.dispatched, true);
  assert.equal(evidence.outcome_uncertain, true);
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.sockets[0].destroyed, true);
  assert.equal(g.state.sockets[0].destroyCalls, 1);
  g.state.sockets[0].emit('connect');
  g.state.sockets[0].emit('data', Buffer.from('{"status":"ok","result":{"late":true}}\n'));
  await Promise.resolve();
  assert.equal(g.state.sockets.length, 1, 'Late socket events must not trigger a retry');
  assert.equal(g.state.writes.length, 1, 'Late socket events must not dispatch again');
  noUi(g);
  persisted(g);
});

test('A nominally successful reply racing recovery cannot be returned as success', async () => {
  const g = gateway({ onWrite(state, socket) {
    state.current = recovery();
    queueMicrotask(() => socket.reply({ status: 'ok', result: { saved: true } }));
  } });
  const evidence = errorState(await g.runTool('save', {}), 'recovery_required');
  assert.equal(evidence.dispatched, true);
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.probes.length >= 3, true);
  noUi(g);
  persisted(g);
});

test('Invalid configured editor PIDs fail closed before any socket dispatch', async () => {
  for (const value of ['0', '-1', '1.5', 'not-a-pid', '9007199254740992']) {
    const g = gateway({ env: { UNREAL_EDITOR_PID: value } });
    errorState(await g.runTool('unreal_status', {}), 'probe_failed');
    assert.equal(g.state.sockets.length, 0, 'Invalid PID ' + value);
    noDispatch(g);
  }
});

test('A bridge reply cannot succeed after the selected editor process exits', async () => {
  const g = gateway({ onWrite(state, socket) {
    state.current = { ok: true, processes: [], windows: [] };
    queueMicrotask(() => socket.reply({ status: 'ok', result: { saved: true } }));
  } });
  const evidence = errorState(await g.runTool('save', {}), 'editor_exited');
  assert.equal(evidence.dispatched, true);
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.sockets[0].destroyed, true);
  noUi(g);
});

test('Explicit localhost stand-in on a different port is allowed with an unverified warning', async () => {
  const g = gateway({ inventory: recovery(), env: { UNREAL_BRIDGE_TARGET: 'standin', UNREAL_BRIDGE_PORT: '12345' } });
  const result = await g.runTool('unreal_status', {});
  assert.equal(result.isError, undefined);
  assert.equal(g.state.sockets.length, 1);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.probes.length, 0);
  const resultValue = JSON.parse(result.content[0].text);
  assert.deepEqual(resultValue, { fixture: 'one reply' });
  assert.deepEqual(copy(result._meta.editor_health), { verified: false, reason: 'explicit_standin' });
  noUi(g);
});

for (const [label, value] of [
  ['null', null], ['false', false], ['zero', 0], ['true', true],
  ['string', 'scalar result'], ['array', ['fixture', false]],
]) {
  test(`Stand-in ${label} result is preserved with unverified metadata outside the payload`, async () => {
    const g = gateway({ env: { UNREAL_BRIDGE_TARGET: 'standin', UNREAL_BRIDGE_PORT: '12345' },
      onWrite(state, socket) {
        queueMicrotask(() => socket.reply({ status: 'ok', result: value }));
      } });
    const result = await g.runTool('run_command', { command: 'fixture', params: {} });
    assert.equal(result.isError, undefined);
    assert.deepEqual(JSON.parse(result.content[0].text), value);
    assert.deepEqual(copy(result._meta.editor_health), { verified: false, reason: 'explicit_standin' });
    assert.equal(g.state.sockets.length, 1);
    assert.equal(g.state.writes.length, 1);
    assert.equal(g.state.replies, 1);
    assert.equal(g.state.probes.length, 0);
    noUi(g);
  });
}

test('A stand-in label cannot bypass the real editor port recovery guard', async () => {
  const g = gateway({ inventory: recovery(), env: { UNREAL_BRIDGE_TARGET: 'standin' } });
  errorState(await g.runTool('unreal_status', {}), 'recovery_required');
  assert.equal(g.state.sockets.length, 0);
  noDispatch(g);
  persisted(g);
});

test('Failure diagnostics preserve screenshot, inventory, and a bounded configured log tail offline', async () => {
  const snapshot = modal();
  const png = Buffer.from('offline screenshot bytes');
  snapshot.windows[1].png = png.toString('base64');
  const disk = memoryFs();
  disk.files.set(LOG_FILE, Buffer.from('old'.repeat(7000) + '\nLATEST LOG EVIDENCE\n'));
  const g = gateway({ disk, inventory: snapshot, env: { UNREAL_PROJECT_LOG: LOG_FILE } });
  const result = await g.runTool('save', {});
  errorState(result, 'modal_blocked');
  assert.equal(result.content.some(item => item.type === 'image' && item.data === png.toString('base64')), true);
  const screenshot = [...disk.files.entries()].find(([name]) => name.endsWith('window-1003.png'));
  assert.ok(screenshot, 'Screenshot archive must be written to the fake filesystem');
  assert.deepEqual(screenshot[1], png);
  const archive = [...disk.files.entries()].find(([name]) => name.endsWith('health.json'));
  assert.ok(archive, 'Health archive must be written to the fake filesystem');
  assert.equal(JSON.parse(archive[1].toString('utf8')).current_health.state, 'modal_blocked');
  const tail = result.content.filter(item => item.type === 'text').map(item => {
    try { return JSON.parse(item.text); } catch (_) { return null; }
  }).find(item => item && item.project_log);
  assert.ok(tail);
  assert.equal(Buffer.byteLength(tail.tail), 16384);
  assert.match(tail.tail, /LATEST LOG EVIDENCE/);
  assert.equal(disk.descriptors.size, 0);
  assert.equal(g.state.probes.some(item => item.args.includes('-Diagnostics')), true);
  noDispatch(g);
});

const securityContextFixture = { command_id: 'fixture-build', artifact_path: 'C:\\project\\owned-test.exe', artifact_sha256: 'a'.repeat(64) };
test('Explicit stand-in security observation is unavailable without native process inspection', async () => {
  const g = gateway({ env: { UNREAL_BRIDGE_TARGET: 'standin', UNREAL_BRIDGE_PORT: '12345' } });
  const result = await g.runTool('security_alert_status', securityContextFixture);
  assert.equal(JSON.parse(result.content[0].text).reason, 'explicit_standin');
  assert.equal(g.state.securityProbes.length, 0);
  noDispatch(g); noUi(g);
});
test('Opt-in unavailable observer preserves bridge success and never forwards artifact metadata', async () => {
  const g = gateway();
  const result = await g.runTool('unreal_status', { security_context: securityContextFixture });
  assert.equal(result.isError, undefined);
  assert.equal(result._meta.security_observation.state, 'unavailable');
  assert.deepEqual(g.state.writes[0].params, { bridge_timeout: g.state.writes[0].params.bridge_timeout });
  assert.equal(g.state.securityProbes.length, 2);
  noUi(g);
});
test('Matching Norton block prevents dispatch, survives disappearance, and leaves unrelated work available', async () => {
  const g = gateway({ securitySnapshot: { available: true, windows: [{ pid: 303, processName: 'NortonUI', hwnd: 3003,
    visible: true, title: 'Norton security alert', text: 'File blocked: C:\\project\\owned-test.exe', text_available: true }] } });
  errorState(await g.runTool('unreal_status', { security_context: securityContextFixture }), 'security_alert_observed');
  noDispatch(g); noUi(g);
  const probes = g.state.securityProbes.length;
  errorState(await g.runTool('unreal_status', { security_context: securityContextFixture }), 'security_alert_observed');
  assert.equal(g.state.securityProbes.length, probes);
  const independent = await g.runTool('unreal_status', {});
  assert.equal(independent.isError, undefined);
  assert.equal(g.state.writes.length, 1);
  assert.equal(g.state.inputAttempts.length, 0);
});
test('Correlated informational sandbox notice records once and allows the authorized call', async () => {
  const g = gateway({ securitySnapshot: { available: true, windows: [{ pid: 303, processName: 'NortonUI', hwnd: 3003,
    visible: true, title: 'Norton', text: 'Analyzing in sandbox: C:\\project\\owned-test.exe', text_available: true }] } });
  const result = await g.runTool('unreal_status', { security_context: securityContextFixture });
  assert.equal(result.isError, undefined);
  assert.equal(g.state.writes.length, 1);
  assert.equal(result._meta.security_observation.state, 'security_alert_notice');
  assert.equal([...g.disk.files.keys()].filter(file => /alert-evidence-/.test(file)).length, 1);
  noUi(g);
});

(async () => {
  let passed = 0;
  let failed = 0;
  for (const { name, run } of tests) {
    try { await run(); passed++; process.stdout.write('ok - ' + name + '\n'); }
    catch (error) {
      failed++;
      process.stderr.write('not ok - ' + name + '\n' + (error.stack || error) + '\n');
    }
  }
  process.stdout.write(`${passed}/${tests.length} gateway integration tests passed (offline; no real sockets, UI, child processes, or filesystem writes).\n`);
  if (failed) process.exitCode = 1;
})().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
