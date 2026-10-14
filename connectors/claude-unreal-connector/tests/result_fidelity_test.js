// SPDX-License-Identifier: MIT
// Offline regression checks for the actual adapter runTool/callUnreal path.
// Run: node connectors/claude-unreal-connector/tests/result_fidelity_test.js
'use strict';
const assert = require('assert').strict;
const { EventEmitter } = require('events');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const adapterPath = path.join(__dirname, '..', 'extension', 'server', 'index.js');
const source = fs.readFileSync(adapterPath, 'utf8');
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=';
const canceled = [{ title: 'Test modal', did: 'escape', closed: true }];
const note = { type: 'text', text: 'Dialogs the watcher canceled during this call: ' + JSON.stringify(canceled) };
const text = (value) => ({ type: 'text', text: JSON.stringify(value, null, 2) });
const plain = (value) => JSON.parse(JSON.stringify(value));

async function runOffline(adapterSource, reply, withNote = false) {
  const timers = new Set();
  const requests = [];
  const windows = [];
  const sockets = [];
  const schedule = (callback, delay) => {
    const timer = { callback, delay };
    timers.add(timer);
    return timer;
  };
  const forbidden = (name) => () => { throw new Error('Offline test attempted ' + name); };

  // This is an EventEmitter, not a real socket. The production transport still
  // writes its JSON request and receives a newline-framed JSON bridge reply.
  class MemorySocket extends EventEmitter {
    constructor() {
      super();
      this.destroyed = false;
      queueMicrotask(() => this.emit('connect'));
    }
    write(data) {
      requests.push(JSON.parse(data));
      if (withNote) {
        const first = [...timers].find((timer) => timer.delay === 2500);
        assert.ok(first, 'production dialog watcher scheduled its first tick');
        first.callback();
      }
      // Let the watcher's resolved list/input promises complete before reply.
      // setImmediate only schedules this in-memory event; it opens no handles.
      setImmediate(() => this.emit('data', Buffer.from(JSON.stringify(reply) + '\n')));
    }
    destroy() {
      this.destroyed = true;
      this.emit('close');
    }
  }

  const deps = {
    net: { createConnection: (options) => {
      assert.deepEqual(plain(options), { host: '127.0.0.1', port: 9877 });
      const socket = new MemorySocket();
      sockets.push(socket);
      return socket;
    } },
    path,
    child_process: { execFile: (program, args, options, callback) => {
      assert.equal(program, 'powershell.exe');
      assert.equal(options.windowsHide, true);
      const op = args[args.indexOf('-Op') + 1];
      windows.push(op);
      if (op === 'list') {
        callback(null, JSON.stringify({ ok: true, windows: [{ hwnd: 42, title: 'Test modal', main: false }] }), '');
      } else {
        assert.equal(op, 'input');
        assert.equal(args[args.indexOf('-Hwnd') + 1], '42');
        assert.equal(args[args.indexOf('-Keys') + 1], 'escape');
        callback(null, JSON.stringify({ ok: true, window_still_open: false }), '');
      }
    } },
    readline: { createInterface: () => ({ on: () => {} }) },
  };
  const context = vm.createContext({
    require: (name) => {
      assert.ok(Object.hasOwn(deps, name), 'only stubbed/allowlisted dependencies: ' + name);
      return deps[name];
    },
    __dirname: path.dirname(adapterPath),
    Buffer,
    process: {
      env: {}, platform: withNote ? 'win32' : 'linux', stdin: {},
      stdout: { write: forbidden('stdio response') },
      stderr: { write: forbidden('stderr response') },
      on: () => {}, exit: forbidden('process exit'),
    },
    setTimeout: schedule, setInterval: schedule,
    clearTimeout: (timer) => timers.delete(timer),
    clearInterval: (timer) => timers.delete(timer),
  });
  vm.runInContext(adapterSource + '\nglobalThis.testRunTool = runTool;\n', context, { filename: adapterPath });
  const output = await context.testRunTool('run_command', { command: 'test.result_fidelity', params: { flag: false } });
  assert.deepEqual(requests, [{ id: 1, type: 'test.result_fidelity', params: { bridge_timeout: 1800, flag: false } }]);
  assert.equal(sockets.length, 1);
  assert.ok(sockets[0].destroyed, 'production transport closed the memory socket');
  assert.equal(timers.size, 0, 'production transport and watcher cleared their timers');
  assert.deepEqual(windows, withNote ? ['list', 'input'] : []);
  return plain(output);
}

const falsyCases = [
  ['false', false], ['zero', 0], ['empty string', ''], ['null', null],
];

async function assertFalsyResults(adapterSource) {
  const rejected = [];
  for (const [name, value] of falsyCases) {
    const output = await runOffline(adapterSource, { status: 'ok', result: value });
    try {
      assert.deepEqual(output, { content: [text(value)] }, name + ' remains its exact JSON value');
    } catch (error) {
      if (!(error instanceof assert.AssertionError)) throw error;
      rejected.push(name);
    }
  }
  return rejected;
}

let passed = 0;
async function check(name, test) {
  await test();
  passed++;
  console.log('PASS ' + name);
}

(async () => {
  for (const [name, value] of falsyCases) {
    await check('exact JSON ' + name, async () => {
      assert.deepEqual(await runOffline(source, { status: 'ok', result: value }), { content: [text(value)] });
    });
  }
  for (const [name, value] of [
    ['empty array', []],
    ['nested array', [false, 0, '', null, { nested: [0, false] }]],
    ['empty object', {}],
    ['nested object', { ok: false, count: 0, label: '', extra: null, items: [1, 'two'] }],
    ['ordinary string', 'bridge result'],
    ['non-string image field', { image_png_base64: 0, width: 640 }],
  ]) {
    await check(name + ' stays JSON text', async () => {
      assert.deepEqual(await runOffline(source, { status: 'ok', result: value }), { content: [text(value)] });
    });
  }
  await check('missing result retains the empty-object fallback', async () => {
    assert.deepEqual(await runOffline(source, { status: 'ok' }), { content: [text({})] });
  });
  await check('ordinary bridge error retains message and traceback', async () => {
    assert.deepEqual(await runOffline(source, { status: 'error', message: 'ValueError: boom', traceback: 'Traceback\n  test_frame', result: null }),
      { isError: true, content: [{ type: 'text', text: 'ValueError: boom\n\nTraceback\n  test_frame' }] });
  });
  await check('missing error message retains its fallback', async () => {
    assert.deepEqual(await runOffline(source, { status: 'error' }),
      { isError: true, content: [{ type: 'text', text: 'Unreal reported an error' }] });
  });
  await check('PNG keeps image data and separate metadata', async () => {
    const meta = { width: 640, height: 360, path: 'test.png', alpha: false };
    const reply = { status: 'ok', result: { image_png_base64: png, ...meta } };
    const before = JSON.stringify(reply);
    assert.deepEqual(await runOffline(source, reply), { content: [
      { type: 'image', data: png, mimeType: 'image/png' }, text(meta),
    ] });
    assert.equal(JSON.stringify(reply), before, 'input reply remains unchanged');
  });
  await check('PNG metadata and watcher note retain their order', async () => {
    assert.deepEqual(await runOffline(source, { status: 'ok', result: { image_png_base64: png, width: 1, height: 1 } }, true), { content: [
      { type: 'image', data: png, mimeType: 'image/png' }, text({ width: 1, height: 1 }), note,
    ] });
  });
  await check('falsy result still retains a watcher note', async () => {
    assert.deepEqual(await runOffline(source, { status: 'ok', result: null }, true), { content: [text(null), note] });
  });
  await check('ordinary error still retains a watcher note', async () => {
    assert.deepEqual(await runOffline(source, { status: 'error', message: 'boom', traceback: 'test_trace' }, true),
      { isError: true, content: [{ type: 'text', text: 'boom\n\ntest_trace' }, note] });
  });
  await check('all four falsy fixtures reject the legacy || {} mutation', async () => {
    assert.deepEqual(await assertFalsyResults(source), [], 'current adapter passes every falsy fixture');
    const mutant = source.replace(/const result\s*=\s*reply\.result\s*===\s*undefined\s*\?\s*\{\}\s*:\s*reply\.result\s*;/,
      'const result = reply.result || {};');
    assert.notEqual(mutant, source, 'legacy fallback mutation was applied in memory');
    assert.deepEqual(await assertFalsyResults(mutant), falsyCases.map(([name]) => name));
  });
  console.log(`${passed}/${passed}`);
})().catch((error) => {
  console.error('FAIL ' + (error.stack || error));
  process.exitCode = 1;
});
