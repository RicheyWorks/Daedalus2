// SPDX-License-Identifier: MIT
// Drives the Unreal connector (server/index.js) over stdio, as Claude does, against host.py's bridge.
// Each check must be able to fail; prints n/m last and exits 1 on any failure.
'use strict';
const { spawn } = require('child_process');
const path = require('path');
const port = process.argv[2];
const srv = spawn(process.execPath, [path.join(__dirname, '..', 'extension', 'server', 'index.js')], { env: Object.assign({}, process.env, { UNREAL_BRIDGE_PORT: port }) });
let buf = '', next = 1; const waiting = {};
srv.stdout.on('data', (d) => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const m = JSON.parse(buf.slice(0, i)); buf = buf.slice(i + 1); if (waiting[m.id]) { waiting[m.id](m); delete waiting[m.id]; } } });
const rpc = (method, params) => new Promise((res) => { const id = next++; waiting[id] = res; srv.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); });
const call = async (name, args) => (await rpc('tools/call', { name, arguments: args || {} })).result;
const text = (r) => r.content.filter((c) => c.type === 'text').map((c) => c.text).join('\n');
let pass = 0, total = 0;
const check = (label, ok, detail) => { total++; if (ok) pass++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok ? '' : '  ' + (detail || ''))); };

(async () => {
  const init = await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' } });
  check('initialize names the server and offers tools', init.result.serverInfo.name === 'unreal' && init.result.capabilities.tools);
  const list = (await rpc('tools/list', {})).result.tools.map((t) => t.name);
  check('13 tools listed, none of them project-specific', list.length === 13 && list.includes('run_command') && list.includes('window_input') && !list.some((n) => /daedalus/.test(n)), list.join(','));

  let r = await call('unreal_status');
  let j = JSON.parse(text(r));
  check('unreal_status reports engine, project, level, actors', !r.isError && j.engine === '5.8.3-fake' && j.actors === 3 && j.level.includes('DaedalusWorld') && j.bridge_port === +port, text(r));

  r = await call('get_level_info', { folder: 'Daedalus/world-zero' });
  j = JSON.parse(text(r));
  check('get_level_info filters by Outliner folder', j.actors_total === 2 && j.actors[0].location[2] === 3000 && j.selected[0] === 'chunk_0_2_-6', text(r));

  r = await call('get_actor_info', { name: 'chunk_0_2_-6' });
  j = JSON.parse(text(r));
  check('get_actor_info returns transform, bounds and components', j.bounds.extent[0] === 100 && j.components.length === 1, text(r));
  r = await call('get_actor_info', { name: 'nobody' });
  check('get_actor_info on a missing actor is an error that says so', r.isError && /no actor/.test(text(r)), text(r));

  r = await call('execute_python', { code: 'print("hello from", unreal.SystemLibrary.get_engine_version())\nresult = {"n": len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())}' });
  j = JSON.parse(text(r));
  check('execute_python returns stdout and `result`', j.stdout.includes('hello from 5.8.3-fake') && j.result.n === 3, text(r));
  check('execute_python goes through Remote Execution, unattended (dialogs are canceled, not waited on)', j.unattended === true, text(r));
  r = await call('run_command', { command: 'test.remote_calls' });
  check('the Remote Execution call asked for unattended mode', JSON.parse(text(r)).calls.some((c) => c[0] === 'run' && c[1] === true), text(r));
  r = await call('execute_python', { code: 'raise ValueError("boom")' });
  check('execute_python errors come back with the message', r.isError && /ValueError: boom/.test(text(r)), text(r));
  r = await call('run_command', { command: 'test.remote_off' });
  r = await call('execute_python', { code: 'result = 7' });
  j = JSON.parse(text(r));
  check('with Remote Execution off it still runs, directly, and says dialogs would block', j.result === 7 && j.unattended === false && /Remote Execution is off/.test(j.note || ''), text(r));
  r = await call('execute_python', { code: 'raise ValueError("boom")' });
  check('direct errors come back with the traceback', r.isError && /ValueError: boom/.test(text(r)) && /Traceback/.test(text(r)), text(r));

  r = await call('viewport_screenshot', { width: 640, height: 360 });
  const img = r.content.find((c) => c.type === 'image');
  check('viewport_screenshot waits for the file over frames and returns a PNG', img && Buffer.from(img.data, 'base64').slice(1, 4).toString() === 'PNG', text(r));

  r = await call('play');
  check('play waits until Play In Editor is running', !r.isError && JSON.parse(text(r)).playing === true, text(r));
  r = await call('unreal_status');
  check('status then says playing', JSON.parse(text(r)).playing === true);
  r = await call('stop');
  check('stop ends it', JSON.parse(text(r)).playing === false, text(r));

  r = await call('list_commands');
  j = JSON.parse(text(r));
  const addon = j.commands.find((c) => c.name === 'test.countdown');
  check('list_commands shows built-ins and a project add-on with its params', addon && addon.params.from === 'int' && j.commands.some((c) => c.name === 'execute_python'), text(r));
  r = await call('run_command', { command: 'test.countdown', params: { from: 4, who: 'grok' } });
  j = JSON.parse(text(r));
  check('run_command runs the add-on across editor ticks', JSON.stringify(j.counted) === '[4,3,2,1]' && j.by === 'grok', text(r));
  r = await call('run_command', { command: 'nope.missing' });
  check('an unknown command is an error that lists the known ones', r.isError && /test\.countdown/.test(text(r)), text(r));
  r = await call('editor_windows');
  check('the window harness says plainly when it cannot run (not Windows)', process.platform === 'win32' || (r.isError && /Windows only/.test(text(r))), text(r));

  r = await call('save');
  check('save saves the level and the changed packages', JSON.parse(text(r)).level_saved === true, text(r));

  r = await call('output_log', { filter: 'error', lines: 10 });
  j = JSON.parse(text(r));
  check('output_log filters the editor log', j.lines.length === 1 && j.lines[0].includes('something broke'), text(r));

  // Canary: once the "editor" stops ticking (a modal dialog), a call must time out with a reason, not hang.
  await call('run_command', { command: 'test.freeze' });
  r = await call('unreal_status');
  check('a frozen editor gives a clear timeout, not a hang', r.isError && /did not answer|in time/.test(text(r)), text(r));

  console.log(`${pass}/${total}`);
  srv.kill();
  process.exit(pass === total ? 0 : 1);
})();
