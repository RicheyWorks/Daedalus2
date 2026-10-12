#!/usr/bin/env node
// Unreal connector for Claude: a dependency-free MCP server (stdio, JSON-RPC 2.0) that forwards tool calls to the
// Claude Unreal Bridge running inside the Unreal Editor (DaedalusLink's claude_unreal_bridge.py).
'use strict';
const net = require('net');
const readline = require('readline');

const HOST = process.env.UNREAL_BRIDGE_HOST || '127.0.0.1';
const PORT = parseInt(process.env.UNREAL_BRIDGE_PORT || '9877', 10) || 9877;
const SERVER_INFO = { name: 'unreal', version: '1.0.0' };
const SUPPORTED = ['2025-06-18', '2025-03-26', '2024-11-05'];
const none = { type: 'object', properties: {}, additionalProperties: false };

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
  { name: 'import_daedalus_world', command: 'import_world', timeout: 1800000,
    description: 'Download a Daedalus World Package from its server, import it into the open project (chunk meshes, materials, ark, live actor, a view PlayerStart), verify the result against the manifest, and frame the viewport on it. Returns every PASS/FAIL check.',
    inputSchema: { type: 'object', properties: {
      server: { type: 'string', description: 'Daedalus server (default http://localhost:8088)' },
      world: { type: 'string', description: 'World id (default world-zero)' },
      live: { type: 'boolean', description: 'Only the live actor, no baked chunks' } }, additionalProperties: false } },
  { name: 'frame_daedalus_world', command: 'frame_world', timeout: 30000,
    description: 'Point the editor viewport at a Daedalus world in the open level (the first one if no id).',
    inputSchema: { type: 'object', properties: { world: { type: 'string' } }, additionalProperties: false } },
  { name: 'output_log', command: 'output_log', timeout: 30000,
    description: 'The last lines of the editor log, optionally filtered (e.g. "Error", "Daedalus", "LogPython").',
    inputSchema: { type: 'object', properties: {
      lines: { type: 'integer', minimum: 1, maximum: 5000, description: 'How many lines (default 200)' },
      filter: { type: 'string', description: 'Only lines containing this text (case-insensitive)' } }, additionalProperties: false } },
];

function callUnreal(type, params, timeoutMs) {
  return new Promise((resolve, reject) => {
    const sock = net.createConnection({ host: HOST, port: PORT });
    const chunks = [];
    let settled = false;
    const finish = (err, val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      sock.destroy();
      err ? reject(err) : resolve(val);
    };
    const timer = setTimeout(() => finish(new Error(`Unreal did not answer within ${Math.round(timeoutMs / 1000)}s. It may be compiling shaders, loading, or showing a dialog.`)), timeoutMs);
    sock.on('connect', () => sock.write(JSON.stringify({ id: 1, type, params: Object.assign({ bridge_timeout: timeoutMs / 1000 }, params || {}) }) + '\n'));
    sock.on('data', (d) => {
      chunks.push(d);
      if (d.includes(10)) {
        const text = Buffer.concat(chunks).toString('utf8');
        try { finish(null, JSON.parse(text.slice(0, text.indexOf('\n')))); } catch (e) { finish(new Error('Bad reply from Unreal: ' + e.message)); }
      }
    });
    sock.on('error', (e) => {
      if (e.code === 'ECONNREFUSED' || e.code === 'ETIMEDOUT' || e.code === 'EHOSTUNREACH') {
        finish(new Error(`Could not reach the Unreal Editor on ${HOST}:${PORT}. Open the project (the DaedalusLink plugin starts the Claude Unreal Bridge with the editor): setup-unreal.ps1 -Open does it in one line.`));
      } else finish(e);
    });
    sock.on('close', () => finish(new Error('Unreal closed the connection before answering.')));
  });
}

async function runTool(name, args) {
  const tool = TOOLS.find((t) => t.name === name);
  if (!tool) return { isError: true, content: [{ type: 'text', text: `Unknown tool: ${name}` }] };
  let reply;
  try { reply = await callUnreal(tool.command, args || {}, tool.timeout); } catch (e) {
    return { isError: true, content: [{ type: 'text', text: e.message }] };
  }
  if (!reply || reply.status !== 'ok') {
    const tb = reply && reply.traceback ? '\n\n' + reply.traceback : '';
    return { isError: true, content: [{ type: 'text', text: ((reply && reply.message) || 'Unreal reported an error') + tb }] };
  }
  const result = reply.result || {};
  if (typeof result.image_png_base64 === 'string') {
    const { image_png_base64, ...meta } = result;
    return { content: [{ type: 'image', data: image_png_base64, mimeType: 'image/png' }, { type: 'text', text: JSON.stringify(meta, null, 2) }] };
  }
  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
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
          instructions: 'Operates the user\'s open Unreal Editor. Call unreal_status first; inspect with get_level_info / get_actor_info; do anything with execute_python (the full unreal API); check work with viewport_screenshot; play/stop for Play In Editor; save to keep changes. import_daedalus_world brings a Daedalus world in from its server and verifies it.',
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
