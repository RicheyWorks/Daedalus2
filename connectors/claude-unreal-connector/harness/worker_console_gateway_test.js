// SPDX-License-Identifier: MIT
// Run the actual MCP gateway in a VM with a fake Windows provider. No processes or desktop actions.
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { EventEmitter } = require('events');
const sourcePath = process.argv[2] || path.join(__dirname, '..', 'extension', 'server', 'index.js');
const source = fs.readFileSync(sourcePath, 'utf8');

function gateway(platform = 'win32') {
  const requests = [], timers = [], responses = [], hooks = {};
  const worker = { pid: 42, hwnd: 123, status: 'minimized', reason: '' };
  const execFile = (exe, args, options, done) => {
    requests.push({ exe, args, options });
    const op = args[args.indexOf('-Op') + 1];
    const result = { ok: true, worker_consoles: { status: 'ok', workers: [worker] } };
    if (op === 'list') result.windows = [];
    if (op === 'input') throw new Error('worker must never enter the editor input path');
    done(null, JSON.stringify(result), '');
  };
  const context = vm.createContext({
    require: (name) => ({ net: { createConnection: () => new EventEmitter() }, path,
      child_process: { execFile }, readline: { createInterface: () => ({ on: (name, cb) => { hooks[name] = cb; } }) } })[name],
    __dirname: path.dirname(sourcePath), Buffer, console,
    setTimeout: (fn) => { timers.push(fn); return fn; }, clearTimeout: () => {},
    setInterval: (fn) => { timers.push(fn); return fn; }, clearInterval: () => {},
    process: { platform, env: {}, stdin: {}, stdout: { write: (line) => responses.push(JSON.parse(line)) },
      stderr: { write: () => {} }, on: () => {}, exit: () => {} },
  });
  vm.runInContext(source, context, { filename: sourcePath });
  return { context, requests, timers, responses, hooks, worker };
}

(async () => {
  const g = gateway();
  const tools = vm.runInContext('TOOLS', g.context);
  const workerTool = tools.find(t => t.name === 'background_worker_windows');
  assert(workerTool && workerTool.local === 'workers', 'worker console tool must exist independently of editor/bridge');
  const result = await vm.runInContext("runTool('background_worker_windows', {})", g.context);
  const payload = JSON.parse(result.content[0].text);
  assert.strictEqual(payload.worker_consoles.workers[0].status, 'minimized');
  assert.strictEqual(g.requests.length, 1);
  assert.strictEqual(g.requests[0].args[g.requests[0].args.indexOf('-Op') + 1], 'workers');
  assert(!g.requests[0].args.includes('-Hwnd'), 'worker tool does not accept arbitrary window actions');
  assert(!g.requests[0].args.includes('-ExecutionPolicy'), 'window capability obeys the existing execution policy');

  await vm.runInContext("runTool('editor_windows', {max_images: 0})", g.context);
  assert.strictEqual(g.requests[1].args[g.requests[1].args.indexOf('-Op') + 1], 'list');
  const answered = [];
  g.context.answeredFixture = answered;
  const stop = vm.runInContext('startDialogWatcher(answeredFixture)', g.context);
  for (const tick of g.timers) await tick();
  assert(g.requests.slice(2).every(r => r.args[r.args.indexOf('-Op') + 1] === 'list'));
  assert.strictEqual(answered.length, 0, 'worker records are separate from editor dialogs and never receive Escape');
  stop();

  g.worker.status = 'already_minimized';
  const again = await vm.runInContext("runTool('background_worker_windows', {})", g.context);
  assert.strictEqual(JSON.parse(again.content[0].text).worker_consoles.workers[0].status, 'already_minimized');
  g.worker.status = 'minimized';
  const restored = await vm.runInContext("runTool('background_worker_windows', {})", g.context);
  assert.strictEqual(JSON.parse(restored.content[0].text).worker_consoles.workers[0].status, 'minimized');

  const unix = gateway('linux');
  const unavailable = await vm.runInContext("runTool('background_worker_windows', {})", unix.context);
  assert(unavailable.isError && /Windows only/.test(unavailable.content[0].text));
  assert.strictEqual(unix.requests.length, 0);
  console.log('worker console gateway fixtures passed (mock Windows provider; no live actions)');
})().catch(e => { console.error(e); process.exitCode = 1; });
