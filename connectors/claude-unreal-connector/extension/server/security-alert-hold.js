// SPDX-License-Identifier: MIT
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const MAX_BYTES = 16 * 1024;
const LOG_SOURCE = 'Norton autosandbox.log';
const NORTON = /^(?:NortonUI|Norton|NortonSecurity|NortonSecurityUI|Norton360|Norton360UI)(?:\.exe)?$/i;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const fail = code => Object.assign(new Error(code), { code });
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function identifier(value, label) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(value)) {
    throw new TypeError(`${label} must be a bounded metadata identifier`);
  }
  return value;
}

function normalizedArtifactPath(value) {
  if (typeof value !== 'string' || !value || value.length > 1024 || /[\u0000-\u001f\u007f]/.test(value)) {
    throw new TypeError('Artifact path must be a bounded Windows absolute file path');
  }
  let candidate = value.replace(/\//g, '\\');
  if (/^\\\\\?\\UNC\\/i.test(candidate)) candidate = '\\\\' + candidate.slice(8);
  else if (/^\\\\\?\\[a-z]:\\/i.test(candidate)) candidate = candidate.slice(4);
  if (!(/^[a-z]:\\/i.test(candidate) || /^\\\\[^\\]+\\[^\\]+\\[^\\]/.test(candidate)) ||
      /[<>"|?*]/.test(candidate) || /:\\?/.test(candidate.slice(2)) || candidate.endsWith('\\')) {
    throw new TypeError('Artifact path must name an absolute Windows file, without device or stream syntax');
  }
  candidate = path.win32.normalize(candidate);
  const root = path.win32.parse(candidate).root;
  const parts = candidate.slice(root.length).split('\\').map(part => part.replace(/[ .]+$/, ''));
  if (!parts.length || parts.some(part => !part || /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part))) {
    throw new TypeError('Artifact path must name a regular Windows file path');
  }
  return (root + parts.join('\\')).toLowerCase();
}

function contextMetadata(context) {
  if (context === undefined) return null;
  if (!plain(context)) throw new TypeError('Security hold context must be an object');
  const structured = own(context, 'artifact');
  const flat = own(context, 'artifact_path') || own(context, 'artifact_sha256') || own(context, 'sha256');
  if (!structured && !flat) {
    for (const key of ['command_id', 'command']) if (own(context, key)) identifier(context[key], key);
    return null; // Absence of artifact context is unobserved, never verified safety.
  }
  if (structured && flat) throw new TypeError('Use either structured or flat artifact metadata');
  if (!structured && own(context, 'artifact_sha256') && own(context, 'sha256')) {
    throw new TypeError('Use only one flat artifact hash field');
  }
  const artifact = structured ? context.artifact : {
    path: context.artifact_path, sha256: own(context, 'artifact_sha256') ? context.artifact_sha256 : context.sha256,
  };
  if (!plain(artifact)) throw new TypeError('Explicit artifact metadata must be an object');
  const artifactPath = normalizedArtifactPath(artifact.path);
  let hash = null;
  if (artifact.sha256 !== undefined && artifact.sha256 !== null) {
    if (typeof artifact.sha256 !== 'string' || !/^[0-9a-f]{64}$/i.test(artifact.sha256)) {
      throw new TypeError('Caller artifact SHA256 must contain exactly 64 hexadecimal characters');
    }
    hash = artifact.sha256.toLowerCase();
  }
  return { command_id: identifier(context.command_id, 'command_id'), command: identifier(context.command, 'command'),
    artifact: { path: artifactPath, sha256: hash, sha256_status: hash ? 'caller_supplied_unverified' : 'unavailable' } };
}

function deepFreeze(value) {
  for (const item of Object.values(value)) if (item && typeof item === 'object') deepFreeze(item);
  return Object.freeze(value);
}
const keyOf = context => createHash('sha256').update(context.artifact.path, 'utf8').digest('hex');

function utcTimestamp(value) {
  return typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value) &&
    Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value;
}

function logBlockResult(value) {
  return ['blocked', 'quarantined', 'denied'].includes(value) ? value : null;
}

function alertMetadata(evidence, context, stored = false) {
  if (!plain(evidence)) return null;
  const alert = plain(evidence.alert) ? evidence.alert : evidence;
  const blocked = alert.blocked === true || alert.severity === 'blocked' || evidence.severity === 'blocked';
  if (!blocked) return null; // Informational sandbox notices and ordinary command errors never latch.
  if (alert.blocked === false || alert.severity === 'informational') {
    throw new TypeError('Conflicting security alert severity');
  }
  if (alert.process === 'Norton log' || alert.source === LOG_SOURCE || alert.pid === null && own(alert, 'source')) {
    const result = logBlockResult(alert.result);
    const matchKind = alert.artifact_correlation ?? alert.match_kind;
    if (alert.source !== LOG_SOURCE || alert.process !== 'Norton log' || alert.pid !== null ||
        alert.hwnd !== null || matchKind !== 'exact_path' || !utcTimestamp(alert.event_at) || !result) {
      throw new TypeError('A log block requires the fixed Norton source, exact artifact correlation, explicit denial and UTC event time');
    }
    if (own(alert, 'artifact_path') && (!context || normalizedArtifactPath(alert.artifact_path) !== context.artifact.path)) {
      throw new TypeError('Norton log artifact does not match the caller artifact');
    }
    if (stored && alert.result !== result) throw new TypeError('Stored log result must be canonical');
    return { vendor: 'Norton', source: LOG_SOURCE, pid: null, process: 'Norton log', hwnd: null,
      event_at: alert.event_at, match_kind: 'exact_path', blocked: true, reason: 'matching_artifact_blocked', result };
  }
  const pid = alert.pid ?? alert.window_pid;
  const process = alert.process ?? alert.process_name;
  const matchKind = alert.artifact_correlation ?? alert.match_kind;
  if (!Number.isSafeInteger(pid) || pid <= 0 || typeof process !== 'string' ||
      process.length > 64 || !NORTON.test(process) || !['exact_path', 'basename_inference'].includes(matchKind)) {
    throw new TypeError('A confirmed Norton artifact block requires bounded correlated window metadata');
  }
  let hwnd = null;
  if (alert.hwnd !== undefined && alert.hwnd !== null) {
    if (!(typeof alert.hwnd === 'string' || Number.isSafeInteger(alert.hwnd)) ||
        !/^(?:[1-9]\d{0,19}|0x[0-9a-f]{1,16})$/i.test(String(alert.hwnd))) {
      throw new TypeError('Invalid security alert window handle');
    }
    hwnd = String(alert.hwnd).toLowerCase();
  }
  return { vendor: 'Norton', pid, process, hwnd, match_kind: matchKind,
    blocked: true, reason: 'matching_artifact_blocked' };
}

function exactKeys(value, keys) {
  return plain(value) && Object.keys(value).length === keys.length && keys.every(key => own(value, key));
}

/** Persistent artifact pause only. No observer, security actions, background jobs,
 * filesystem creation outside the supplied existing directory, or runtime clear API.
 */
function createSecurityAlertHold({ directory, fsImpl = fs } = {}) {
  if (typeof directory !== 'string' || !directory || directory.length > 4096 ||
      /[\u0000-\u001f\u007f]/.test(directory) || !path.isAbsolute(directory)) {
    throw new TypeError('An existing absolute security hold directory is required');
  }
  const root = path.resolve(directory);
  const held = new Map();
  const flags = fsImpl.constants || fs.constants;
  const diagnostic = (reason, error) => ({ reason,
    code: typeof error?.code === 'string' && /^[A-Z0-9_]{1,64}$/.test(error.code) ? error.code : null });
  const make = (context, alert, state = 'security_alert_observed') => ({
    version: 1, state, scope: 'artifact', artifact_key: keyOf(context),
    observed_at: new Date().toISOString(), context, alert,
  });
  const ioHold = (context, reason, error) => deepFreeze({ ...make(context, null, 'security_alert_held'),
    diagnostics: [diagnostic(reason, error)] });
  const fileFor = context => path.join(root, keyOf(context) + '.json');

  function checkedDirectory(expected) {
    const parsed = path.parse(root);
    const names = [parsed.root];
    let current = parsed.root;
    for (const part of root.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
      current = path.join(current, part);
      names.push(current);
    }
    const identity = names.map(name => {
      const stat = fsImpl.lstatSync(name);
      if (!stat.isDirectory() || stat.isSymbolicLink()) throw fail('HOLD_DIRECTORY_UNSAFE');
      return { name, dev: stat.dev, ino: stat.ino };
    });
    if (expected && identity.some((stat, index) => stat.name !== expected[index]?.name ||
        (stat.dev !== undefined && expected[index]?.dev !== undefined && stat.dev !== expected[index].dev) ||
        (stat.ino !== undefined && expected[index]?.ino !== undefined && stat.ino !== expected[index].ino))) {
      throw fail('HOLD_DIRECTORY_CHANGED');
    }
    return identity;
  }

  function checkedOpenedFile(file, descriptor) {
    const actual = fsImpl.fstatSync(descriptor);
    const linked = fsImpl.lstatSync(file);
    if (!actual.isFile() || !linked.isFile() || linked.isSymbolicLink() || actual.nlink > 1) throw fail('HOLD_NOT_REGULAR');
    if ((linked.dev !== undefined && actual.dev !== undefined && linked.dev !== actual.dev) ||
        (linked.ino !== undefined && actual.ino !== undefined && linked.ino !== actual.ino)) throw fail('HOLD_FILE_CHANGED');
    return actual;
  }

  function readExisting(context) {
    let descriptor;
    let result;
    let establishedEntry = false;
    try {
      const directoryIdentity = checkedDirectory();
      const file = fileFor(context);
      let before;
      try { before = fsImpl.lstatSync(file); }
      catch (error) { if (error.code === 'ENOENT') return null; throw error; }
      establishedEntry = true;
      if (!before.isFile() || before.isSymbolicLink()) throw fail('HOLD_NOT_REGULAR');
      if (!Number.isSafeInteger(before.size) || before.size < 0 || before.size > MAX_BYTES) throw fail('HOLD_TOO_LARGE');
      descriptor = fsImpl.openSync(file, flags.O_RDONLY | (flags.O_NONBLOCK || 0) | (flags.O_NOFOLLOW || 0));
      checkedDirectory(directoryIdentity);
      const actual = checkedOpenedFile(file, descriptor);
      const after = fsImpl.lstatSync(file);
      if (!actual.isFile() || !after.isFile() || after.isSymbolicLink()) throw fail('HOLD_NOT_REGULAR');
      for (const stat of [before, after]) {
        if ((stat.dev !== undefined && actual.dev !== undefined && stat.dev !== actual.dev) ||
            (stat.ino !== undefined && actual.ino !== undefined && stat.ino !== actual.ino)) throw fail('HOLD_FILE_CHANGED');
      }
      if (!Number.isSafeInteger(actual.size) || actual.size < 0 || actual.size > MAX_BYTES) throw fail('HOLD_TOO_LARGE');
      const bytes = Buffer.alloc(MAX_BYTES + 1);
      const count = fsImpl.readSync(descriptor, bytes, 0, bytes.length, 0);
      if (!Number.isSafeInteger(count) || count < 0 || count > MAX_BYTES) throw fail('HOLD_TOO_LARGE');
      checkedDirectory(directoryIdentity);
      checkedOpenedFile(file, descriptor);
      const value = JSON.parse(bytes.subarray(0, count).toString('utf8'));
      if (!exactKeys(value, ['version', 'state', 'scope', 'artifact_key', 'observed_at', 'context', 'alert']) ||
          value.version !== 1 || value.state !== 'security_alert_observed' || value.scope !== 'artifact' ||
          value.artifact_key !== keyOf(context) || typeof value.observed_at !== 'string' ||
          !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value.observed_at) ||
          !utcTimestamp(value.observed_at) ||
          !exactKeys(value.context, ['command_id', 'command', 'artifact']) ||
          !exactKeys(value.context.artifact, ['path', 'sha256', 'sha256_status']) ||
          !(exactKeys(value.alert, ['vendor', 'pid', 'process', 'hwnd', 'match_kind', 'blocked', 'reason']) ||
            exactKeys(value.alert, ['vendor', 'source', 'pid', 'process', 'hwnd', 'event_at', 'match_kind', 'blocked', 'reason', 'result']))) {
        throw fail('HOLD_INVALID');
      }
      const recorded = contextMetadata(value.context);
      if (recorded.artifact.path !== context.artifact.path ||
          recorded.artifact.path !== value.context.artifact.path ||
          recorded.artifact.sha256 !== value.context.artifact.sha256 ||
          recorded.artifact.sha256_status !== value.context.artifact.sha256_status || value.alert.vendor !== 'Norton' ||
          value.alert.blocked !== true || value.alert.reason !== 'matching_artifact_blocked') throw fail('HOLD_INVALID');
      const alert = alertMetadata(value.alert, recorded, true);
      if (!alert || alert.hwnd !== value.alert.hwnd) throw fail('HOLD_INVALID');
      result = deepFreeze({ ...value, context: recorded, alert });
    } catch (error) {
      // An uninspectable directory/entry is unobserved, not a Norton block.
      // Only an established matching-key entry can fail closed as a stored hold.
      result = establishedEntry ? ioHold(context, 'hold_read_failed', error) : null;
    } finally {
      if (descriptor !== undefined) {
        try { fsImpl.closeSync(descriptor); }
        catch (error) { result = ioHold(context, 'hold_read_failed', error); }
      }
    }
    return result;
  }

  function check(suppliedContext) {
    const context = contextMetadata(suppliedContext);
    if (!context) return null;
    const key = keyOf(context);
    if (held.has(key)) return held.get(key);
    const existing = readExisting(context);
    if (existing) held.set(key, existing);
    return existing;
  }

  function record(suppliedContext, evidence) {
    const context = contextMetadata(suppliedContext);
    if (!context) return null;
    const key = keyOf(context);
    if (held.has(key)) return held.get(key);
    const alert = alertMetadata(evidence, context);
    if (!alert) return null;
    held.set(key, deepFreeze(make(context, alert))); // Latch BEFORE filesystem operations can fail.
    const existing = readExisting(context);
    if (existing) { held.set(key, existing); return existing; }
    let descriptor;
    try {
      const directoryIdentity = checkedDirectory();
      const bytes = JSON.stringify(held.get(key)) + '\n';
      if (Buffer.byteLength(bytes, 'utf8') > MAX_BYTES) throw fail('HOLD_TOO_LARGE');
      descriptor = fsImpl.openSync(fileFor(context), 'wx', 0o600);
      // Node does not expose a portable Windows openat directory handle. Check
      // every ancestor and file identity before writing any private metadata.
      checkedDirectory(directoryIdentity);
      checkedOpenedFile(fileFor(context), descriptor);
      fsImpl.writeFileSync(descriptor, bytes);
      fsImpl.fsyncSync(descriptor);
      checkedDirectory(directoryIdentity);
      checkedOpenedFile(fileFor(context), descriptor);
    } catch (error) {
      if (error.code === 'EEXIST') {
        const winner = readExisting(context);
        if (winner) held.set(key, winner);
        else held.set(key, deepFreeze({ ...held.get(key), diagnostics: [diagnostic('hold_persist_failed', error)] }));
      } else held.set(key, deepFreeze({ ...held.get(key), diagnostics: [diagnostic('hold_persist_failed', error)] }));
    } finally {
      if (descriptor !== undefined) {
        try { fsImpl.closeSync(descriptor); }
        catch (error) { held.set(key, deepFreeze({ ...held.get(key), diagnostics: [diagnostic('hold_persist_failed', error)] })); }
      }
    }
    return held.get(key);
  }

  return { check, record };
}

module.exports = { createSecurityAlertHold };
