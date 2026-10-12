#!/usr/bin/env node
// claude-unreal-connector: a dependency-free MCP server (stdio, JSON-RPC 2.0) that forwards tool calls to the
// Claude Unreal Bridge plugin running inside the Unreal Editor, plus a window harness (win.ps1) that answers
// dialogs from outside the editor. MIT. See PROTOCOL.md to drive the bridge without MCP.
'use strict';
const net = require('net');
const path = require('path');
const { execFile } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const os = require('os');
const { randomUUID } = require('crypto');
const { classify, guardedCall, EditorHealthError } = require('./editor-health');
const { createRecoveryHold } = require('./recovery-hold');

const HOST = process.env.UNREAL_BRIDGE_HOST || '127.0.0.1';
const PORT = parseInt(process.env.UNREAL_BRIDGE_PORT || '9877', 10) || 9877;
const SERVER_INFO = { name: 'unreal', version: '1.1.0' };
const SUPPORTED = ['2025-06-18', '2025-03-26', '2024-11-05'];
const none = { type: 'object', properties: {}, additionalProperties: false };
const recoveryHold = createRecoveryHold({
  file: process.env.UNREAL_RECOVERY_HOLD_FILE || path.join(os.tmpdir(), 'claude-unreal-recovery-hold.json'), fsImpl: fs,
});
function checkRecoveryHold() {
  const hold = recoveryHold.check();
  if (hold) throw new EditorHealthError('recovery_required', { reason: 'recovery_hold', hold });
}
function recordRecovery(health, snapshot) {
  recoveryHold.record({ pid: health.pid,
    session: health.start_time || snapshot?.processes?.find(p => p.pid === health.pid)?.start_time,
    windowtitle: health.details?.windows?.[0]?.title,
  });
}
const requiresHold = state => ['recovery_required', 'crashed', 'crash_reporter_present'].includes(state);

const TOOLS = [
  { name: 'unreal_status', command: 'ping', timeout: 10000, inputSchema: none,
    description: 'Check that the Unreal Editor is open and the Claude Unreal Bridge is listening. Returns the engine version, project, open level, actor count and whether Play is running. Call this first.' },
  { name: 'get_level_info', command: 'get_level_info', timeout: 30000,
    description: 'List actors in the open level: label, class, World Outliner folder and location (Unreal units, cm, Z up). Also the selection.',
    inputSchema: { type: 'object', properties: {
      limit: { type: 'integer', minimum: 1, maximum: 5000, description: 'Maximum actors to list (default 300)' },
      folder: { type: 'string', description: 'Only actors whose Outliner folder starts with this, e.g. "Daedalus/world-zero"' } }, additionalProperties: false } },
  { name: 'get_actor_info', command: 'get_actor_info', timeout: 30000,
    description: 'Details for one actor by label or name: transform, bounds, components, meshes and materials.',
    inputSchema: { type: 'object', properties: { name: { type: 'string', description: 'Actor label (as in the Outliner) or object name' } }, required: ['name'], additionalProperties: false } },
  { name: 'execute_python', command: 'execute_python', timeout: 600000,
    description: 'Run Python inside the open Unreal Editor on its game thread, with `unreal` imported: the full editor API (unreal.EditorActorSubsystem, EditorAssetLibrary, LevelEditorSubsystem, MaterialEditingLibrary, AssetTools, ...). This is how to do anything the other tools do not: spawn and edit actors, make materials and Blueprints, change project settings, run console commands. stdout is returned; assign a JSON-serializable value to `result` to return data. Changes are live and unsaved until `save` (or code that saves).',
    inputSchema: { type: 'object', properties: { code: { type: 'string', description: 'Python source to execute' } }, required: ['code'], additionalProperties: false } },
  { name: 'viewport_screenshot', command: 'viewport_screenshot', timeout: 90000,
    description: 'Capture the active level viewport (a high-res screenshot written by the editor) and return it as an image. Use it to check work.',
    inputSchema: { type: 'object', properties: {
      width: { type: 'integer', minimum: 128, maximum: 3840, description: 'Width in pixels (default 1280)' },
      height: { type: 'integer', minimum: 128, maximum: 2160, description: 'Height in pixels (default 720)' } }, additionalProperties: false } },
  { name: 'play', command: 'play', timeout: 60000,
    description: 'Start Play In Editor (or Simulate) and wait until it is running.',
    inputSchema: { type: 'object', properties: { simulate: { type: 'boolean', description: 'Simulate instead of possessing a player' } }, additionalProperties: false } },
  { name: 'stop', command: 'stop', timeout: 60000, inputSchema: none, description: 'Stop Play In Editor and wait until it has ended.' },
  { name: 'save', command: 'save', timeout: 300000, inputSchema: none, description: 'Save the current level and every changed asset.' },
  { name: 'list_commands', command: 'list_commands', timeout: 15000, inputSchema: none,
    description: 'Every command the bridge answers, including ones a project added (for example daedalus.import_world), with descriptions and parameters. Call run_command to use an add-on command.' },
  { name: 'run_command', timeout: 1800000,
    description: 'Run any bridge command by name with its params, usually a project add-on found with list_commands (e.g. {"command": "daedalus.import_world", "params": {"server": "http://localhost:8088"}}).',
    inputSchema: { type: 'object', properties: {
      command: { type: 'string', description: 'Command name from list_commands' },
      params: { type: 'object', description: 'Its parameters' } }, required: ['command'], additionalProperties: false } },
  { name: 'editor_windows', local: 'list', timeout: 60000,
    description: 'Read-only inventory of Unreal Editor and CrashReportClient processes/windows, with pictures. Includes ownership and enabled state; main is a display hint, not readiness proof. Restore Packages requires preserving/comparing autosaves and owner recovery; unidentified dialogs require review. This tool never answers dialogs. Windows only.',
    inputSchema: { type: 'object', properties: { max_images: { type: 'integer', minimum: 0, maximum: 12, description: 'Pictures for at most this many windows (default 6)' } }, additionalProperties: false } },
  { name: 'window_input', local: 'input', timeout: 30000,
    description: 'Answer an Unreal dialog, or drive any editor window, from outside the editor: brings the window (hwnd from editor_windows) to the front, optionally clicks at (x, y) in that window\'s own pixels as seen in its editor_windows picture (divide by image_scale if the picture was scaled), then presses keys. Keys: enter, escape, tab, space, left, right, up, down, y, n, alt+f4, separated by spaces (e.g. "tab enter"). Or pass action to close, minimize, restore, maximize or move a window without guessing where its buttons are. Reports whether the window closed. Windows only.',
    inputSchema: { type: 'object', properties: {
      hwnd: { type: 'integer', description: 'Window handle from editor_windows' },
      keys: { type: 'string', description: 'Keys to press, e.g. "enter" for a default OK, "escape" to cancel' },
      x: { type: 'integer', minimum: 0, description: 'Click x inside the window (window pixels)' },
      y: { type: 'integer', minimum: 0, description: 'Click y inside the window (window pixels); with action move, the screen y' },
      action: { type: 'string', enum: ['close', 'minimize', 'restore', 'maximize', 'move'], description: 'Instead of clicking: close the window (like its X), minimize/restore/maximize it, or move it to screen (x, y)' },
      width: { type: 'integer', minimum: 100, description: 'With action move: new width' },
      height: { type: 'integer', minimum: 100, description: 'With action move: new height' } }, required: ['hwnd'], additionalProperties: false } },
  { name: 'output_log', command: 'output_log', timeout: 30000,
    description: 'The last lines of the editor log, optionally filtered (e.g. "Error", "Daedalus", "LogPython").',
    inputSchema: { type: 'object', properties: {
      lines: { type: 'integer', minimum: 1, maximum: 5000, description: 'How many lines (default 200)' },
      filter: { type: 'string', description: 'Only lines containing this text (case-insensitive)' } }, additionalProperties: false } },
];

function callUnreal(type, params, timeoutMs, signal, expectedPid, expectedStartTime) {
  return new Promise((resolve, reject) => {
    const sock = net.createConnection({ host: HOST, port: PORT });
    const chunks = [];
    let settled = false;
    const finish = (err, val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (signal) signal.removeEventListener('abort', abort);
      sock.destroy();
      err ? reject(err) : resolve(val);
    };
    const abort = () => finish(signal.reason instanceof Error ? signal.reason : new Error('Editor health stopped the call; started work may still finish.'));
    const timer = setTimeout(() => finish(new Error(`Unreal did not answer within ${Math.round(timeoutMs / 1000)}s. It may be compiling shaders or loading, or a dialog is waiting: call editor_windows to see it and window_input to answer it.`)), timeoutMs);
    if (signal) {
      signal.addEventListener('abort', abort, { once: true });
      if (signal.aborted) { abort(); return; }
    }
    sock.on('connect', async () => {
      try {
        if (process.platform === 'win32' && LOCAL_TARGET && !STANDIN) {
          checkRecoveryHold();
          const snapshot = await runWindows('list', { max_images: 0 }, Math.min(5000, timeoutMs), signal);
          if (signal && signal.aborted) { abort(); return; }
          const health = classify(snapshot, expectedPid, expectedStartTime);
          if (requiresHold(health.state)) recordRecovery(health, snapshot);
          if (health.state !== 'available') throw new EditorHealthError(health.state, health.details);
          checkRecoveryHold();
        }
        if (settled) return;
        sock.write(JSON.stringify({ id: 1, type, params: Object.assign({ bridge_timeout: timeoutMs / 1000 }, params || {}) }) + '\n');
      } catch (e) { finish(e); }
    });
    sock.on('data', (d) => {
      chunks.push(d);
      if (d.includes(10)) {
        const text = Buffer.concat(chunks).toString('utf8');
        try { finish(null, JSON.parse(text.slice(0, text.indexOf('\n')))); } catch (e) { finish(new Error('Bad reply from Unreal: ' + e.message)); }
      }
    });
    sock.on('error', (e) => {
      if (e.code === 'ECONNREFUSED' || e.code === 'ETIMEDOUT' || e.code === 'EHOSTUNREACH') {
        finish(new Error(`Could not reach the Unreal Editor on ${HOST}:${PORT}. Open the project in the Unreal Editor with the Claude Unreal Bridge plugin enabled (install.ps1 sets that up).`));
      } else finish(e);
    });
    sock.on('close', () => finish(new Error('Unreal closed the connection before answering.')));
  });
}

// The window harness: win.ps1 run by Windows PowerShell, outside the editor.
function runWindows(op, args, timeoutMs, signal) {
  return new Promise((resolve) => {
    if (process.platform !== 'win32') return resolve({ ok: false, message: 'editor_windows and window_input work on Windows only' });
    const a = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(__dirname, 'win.ps1'), '-Op', op];
    if (op === 'list' && args.max_images !== undefined) a.push('-MaxImages', String(args.max_images));
    if (op === 'list' && args.diagnostics) a.push('-Diagnostics');
    if (op === 'input') {
      a.push('-Hwnd', String(args.hwnd));
      if (args.keys) a.push('-Keys', String(args.keys));
      if (args.x !== undefined && args.y !== undefined) a.push('-X', String(args.x), '-Y', String(args.y));
      if (args.action) a.push('-Action', String(args.action));
      if (args.width) a.push('-W', String(args.width));
      if (args.height) a.push('-H', String(args.height));
    }
    execFile('powershell.exe', a, { timeout: timeoutMs, signal, maxBuffer: 64 * 1024 * 1024, windowsHide: true }, (err, stdout, stderr) => {
      const line = String(stdout || '').trim().split(/\r?\n/).pop();
      try { resolve(JSON.parse(line)); } catch (e) {
        resolve({ ok: false, message: 'window harness failed: ' + ((err && err.message) || '') + ' ' + String(stderr || '').slice(0, 2000) });
      }
    });
  });
}

// Observe outside the game thread. No Escape, WM_CLOSE, recovery, or automatic retry.
const LOCAL_TARGET = /^(127\.0\.0\.1|localhost|::1)$/i.test(HOST);
const STANDIN = process.env.UNREAL_BRIDGE_TARGET === 'standin' && LOCAL_TARGET && PORT !== 9877;
async function failureEvidence(error) {
  let evidenceFolder;
  const content = [{ type: 'text', text: JSON.stringify({
    state: error.state || 'call_failed', code: error.code, message: error.message,
    dispatched: !!error.dispatched, outcome_uncertain: !!error.outcome_uncertain,
    retry_safe: false, details: error.details,
    next: error.state === 'recovery_required'
      ? 'Preserve autosaves and compare authoritative package versions with the asset owner. Resolve recovery and obtain a saved editor slot before a new operation.'
      : 'Inspect diagnostics with the editor owner. Reconcile any dispatched operation before a new attempt; this harness does not restart or answer dialogs.'
  }, null, 2) }];
  if (process.platform === 'win32' && LOCAL_TARGET && !STANDIN) {
    const snapshot = await runWindows('list', { max_images: 2, diagnostics: true }, 3000);
    const currentHealth = classify(snapshot);
    if (requiresHold(currentHealth.state)) recordRecovery(currentHealth, snapshot);
    const record = { observed_at: new Date().toISOString(), state: error.state, code: error.code,
      dispatched: !!error.dispatched, outcome_uncertain: !!error.outcome_uncertain,
      details: error.details, current_health: currentHealth, snapshot };
    let folder;
    try {
      folder = path.join(process.env.UNREAL_DIAGNOSTICS_DIR || path.join(os.tmpdir(), 'claude-unreal-evidence'), randomUUID());
      fs.mkdirSync(folder, { recursive: true });
      evidenceFolder = folder;
    } catch (e) { content.push({ type: 'text', text: 'Evidence directory unavailable: ' + e.message }); }
    for (const window of snapshot.windows || []) {
      if (window.png) {
        if (folder) {
          try {
            const bytes = Buffer.from(window.png, 'base64');
            if (bytes.length <= 8 * 1024 * 1024) fs.writeFileSync(path.join(folder, `window-${window.hwnd}.png`), bytes);
          } catch (e) { content.push({ type: 'text', text: 'Screenshot archive unavailable: ' + e.message }); }
        }
        content.push({ type: 'text', text: `Diagnostic window ${window.hwnd}: ${window.title}` });
        // Crash-report images can contain account identifiers: preserve locally, never forward automatically.
        if (!/CrashReportClient|Crash Reporter/i.test(`${window.process} ${window.title}`)) {
          content.push({ type: 'image', data: window.png, mimeType: 'image/png' });
        }
        delete window.png;
      }
    }
    if (folder) {
      try {
        fs.writeFileSync(path.join(folder, 'health.json'), JSON.stringify(record, null, 2));
        content.push({ type: 'text', text: 'Diagnostics preserved: ' + folder });
      } catch (e) { content.push({ type: 'text', text: 'Health archive unavailable: ' + e.message }); }
    }
    content.push({ type: 'text', text: JSON.stringify({ diagnostic_snapshot: snapshot }) });
  }
  // Optional, explicitly configured project log; read only its final 16 KiB.
  if (process.env.UNREAL_PROJECT_LOG) {
    let fd;
    try {
      fd = fs.openSync(process.env.UNREAL_PROJECT_LOG, 'r');
      const size = fs.fstatSync(fd).size, bytes = Math.min(size, 16384), buffer = Buffer.alloc(bytes);
      fs.readSync(fd, buffer, 0, bytes, Math.max(0, size - bytes));
      if (evidenceFolder) fs.writeFileSync(path.join(evidenceFolder, 'project-log.txt'), buffer);
      const tail = buffer.toString('utf8').replace(/((?:Epic)?AccountId|LoginId|MachineId)(\s*[:=]\s*)[^\s<>]+/gi, '$1$2[redacted]');
      content.push({ type: 'text', text: JSON.stringify({ project_log: process.env.UNREAL_PROJECT_LOG, tail }) });
    } catch (e) { content.push({ type: 'text', text: 'Project log unavailable: ' + e.message }); }
    finally { if (fd !== undefined) fs.closeSync(fd); }
  }
  return content;
}

async function runLocal(tool, args) {
  if (STANDIN) return { isError: true, content: [{ type: 'text', text: 'Native windows are unavailable for the explicit stand-in target.' }] };
  if (tool.local === 'input') {
    try {
      checkRecoveryHold();
      const snapshot = await runWindows('list', { max_images: 0 }, 5000);
      const selectedPid = process.env.UNREAL_EDITOR_PID ? Number(process.env.UNREAL_EDITOR_PID) : undefined;
      const health = classify(snapshot, selectedPid);
      if (requiresHold(health.state)) recordRecovery(health, snapshot);
      if (health.state !== 'available') throw new EditorHealthError(health.state, health.details);
      checkRecoveryHold();
    }
    catch (e) { return { isError: true, content: await failureEvidence(e) }; }
  }
  const r = await runWindows(tool.local, args || {}, tool.timeout);
  if (!r || r.ok === false) return { isError: true, content: [{ type: 'text', text: (r && r.message) || 'window harness failed' }] };
  const content = [];
  for (const w of r.windows || []) {
    if (w.png) {
      content.push({ type: 'text', text: `window ${w.hwnd} "${w.title}"${w.main ? ' (main editor)' : ''} ${w.width}x${w.height}, image_scale ${w.image_scale}` });
      content.push({ type: 'image', data: w.png, mimeType: 'image/png' });
      delete w.png;
    }
  }
  content.push({ type: 'text', text: JSON.stringify(r, null, 2) });
  return { content };
}

async function runTool(name, args) {
  const tool = TOOLS.find((t) => t.name === name);
  if (!tool) return { isError: true, content: [{ type: 'text', text: `Unknown tool: ${name}` }] };
  if (tool.local) return runLocal(tool, args);
  const command = tool.command || (args && args.command);
  const params = tool.command ? (args || {}) : ((args && args.params) || {});
  let reply;
  const healthChecked = process.platform === 'win32' && LOCAL_TARGET && !STANDIN;
  const note = () => [];
  try {
    if (healthChecked) {
      const selectedPid = process.env.UNREAL_EDITOR_PID ? Number(process.env.UNREAL_EDITOR_PID) : undefined;
      if (selectedPid !== undefined && (!Number.isInteger(selectedPid) || selectedPid <= 0)) throw new EditorHealthError('probe_failed', { reason: 'UNREAL_EDITOR_PID must be a positive integer' });
      checkRecoveryHold();
      reply = await guardedCall({
        timeoutMs: tool.timeout, expectedPid: selectedPid,
        beforeDispatch: checkRecoveryHold,
        onEvidence: (health) => {
          if (requiresHold(health.state)) recordRecovery(health);
        },
        probe: ({ signal }) => runWindows('list', { max_images: 0 }, 5000, signal),
        call: ({ signal, remainingMs, expectedPid, expectedStartTime }) => callUnreal(command, params, remainingMs, signal, expectedPid, expectedStartTime),
      });
    } else reply = await callUnreal(command, params, tool.timeout);
  } catch (e) {
    if (requiresHold(e.state)) recordRecovery(e);
    return { isError: true, content: await failureEvidence(e) };
  }
  if (!reply || reply.status !== 'ok') {
    const tb = reply && reply.traceback ? '\n\n' + reply.traceback : '';
    return { isError: true, content: [{ type: 'text', text: ((reply && reply.message) || 'Unreal reported an error') + tb }, ...note()] };
  }
  const result = reply.result === undefined ? {} : reply.result;
  const healthMeta = !healthChecked ? { editor_health: { verified: false, reason: STANDIN ? 'explicit_standin' : 'unsupported_target' } } : {};
  if (result && typeof result.image_png_base64 === 'string') {
    const { image_png_base64, ...meta } = result;
    return { content: [{ type: 'image', data: image_png_base64, mimeType: 'image/png' }, { type: 'text', text: JSON.stringify(meta, null, 2) }, ...note()], _meta: healthMeta };
  }
  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }, ...note()], _meta: healthMeta };
}

function send(msg) { process.stdout.write(JSON.stringify(msg) + '\n'); }

async function handle(msg) {
  const { id, method, params } = msg;
  const isRequest = id !== undefined && id !== null;
  try {
    switch (method) {
      case 'initialize': {
        const asked = params && params.protocolVersion;
        return send({ jsonrpc: '2.0', id, result: {
          protocolVersion: SUPPORTED.includes(asked) ? asked : SUPPORTED[0],
          capabilities: { tools: {} },
          serverInfo: SERVER_INFO,
          instructions: 'Operates the user\'s open Unreal Editor. Local Windows calls check process/modal health before dispatch and while waiting. Restore Packages blocks work pending owner recovery; unknown dialogs and crashes stop with diagnostics. No automatic clicks, restart, or retry. Started work can still finish after the transport stops: reconcile it before another attempt. Call unreal_status first; editor_windows provides read-only diagnostics. Obtain the editor owner\'s saved exclusive slot before mutations.',
        } });
      }
      case 'ping': return send({ jsonrpc: '2.0', id, result: {} });
      case 'tools/list':
        return send({ jsonrpc: '2.0', id, result: { tools: TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })) } });
      case 'tools/call':
        return send({ jsonrpc: '2.0', id, result: await runTool(params && params.name, params && params.arguments) });
      case 'resources/list': return send({ jsonrpc: '2.0', id, result: { resources: [] } });
      case 'prompts/list': return send({ jsonrpc: '2.0', id, result: { prompts: [] } });
      default:
        if (isRequest) send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
    }
  } catch (e) {
    if (isRequest) send({ jsonrpc: '2.0', id, error: { code: -32603, message: String((e && e.message) || e) } });
  }
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
let pending = 0, closing = false;
rl.on('line', (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try { msg = JSON.parse(line); } catch (e) { return send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }); }
  for (const m of Array.isArray(msg) ? msg : [msg]) {
    pending++;
    handle(m).finally(() => { pending--; if (closing && pending === 0) process.exit(0); });
  }
});
rl.on('close', () => { closing = true; if (pending === 0) process.exit(0); });
process.on('uncaughtException', (e) => { process.stderr.write('[unreal-connector] ' + (e && e.stack || e) + '\n'); });
