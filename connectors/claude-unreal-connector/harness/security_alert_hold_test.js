// SPDX-License-Identifier: MIT
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { createSecurityAlertHold } = require('../extension/server/security-alert-hold');

const HASH_A = 'a'.repeat(64), HASH_B = 'b'.repeat(64);
const ARTIFACT = 'C:\\Fixture\\Build\\alpha.exe';
const NORMAL = 'c:\\fixture\\build\\alpha.exe';
const context = (artifactPath = ARTIFACT, hash = HASH_A, id = 'command-1') => ({
  command_id: id, command: 'fixture_command', artifact: { path: artifactPath, sha256: hash },
});
const blocked = overrides => ({ alert: {
  blocked: true, severity: 'blocked', pid: 123, process: 'NortonUI.exe', hwnd: '456',
  artifact_correlation: 'exact_path', ...overrides,
} });
const logBlock = overrides => ({ alert: {
  source: 'Norton autosandbox.log', process: 'Norton log', pid: null, hwnd: null,
  event_at: '2026-10-13T00:15:30.000Z', artifact_path: ARTIFACT,
  artifact_correlation: 'exact_path', blocked: true, severity: 'blocked', result: 'blocked', ...overrides,
} });
function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'security-alert-hold-test-'));
  t.after(() => {
    const resolved = path.resolve(directory);
    assert.ok(resolved.startsWith(path.resolve(os.tmpdir()) + path.sep));
    assert.ok(path.basename(resolved).startsWith('security-alert-hold-test-'));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  return directory;
}
const fileFor = (directory, normalized = NORMAL) => path.join(directory,
  createHash('sha256').update(normalized, 'utf8').digest('hex') + '.json');
const ioError = code => Object.assign(new Error('private exception payload'), { code });
function expectReadHold(value, code) {
  assert.equal(value.state, 'security_alert_held');
  assert.equal(value.scope, 'artifact');
  assert.equal(value.alert, null, 'Corrupt storage must not invent a Norton observation');
  assert.equal(value.diagnostics[0].reason, 'hold_read_failed');
  if (code) assert.equal(value.diagnostics[0].code, code);
}

test('missing artifact is unobserved and never touches files, with no clear API', t => {
  const directory = fixture(t);
  const gate = createSecurityAlertHold({ directory, fsImpl: { lstatSync() { assert.fail('no artifact means no I/O'); } } });
  assert.deepEqual(Object.keys(gate).sort(), ['check', 'record']);
  for (const supplied of [undefined, {}, { command_id: 'one', command: 'fixture_command' }]) {
    assert.equal(gate.check(supplied), null);
    assert.equal(gate.record(supplied, blocked()), null);
  }
});

test('absent matching hold does not certify safety or hold another artifact', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  assert.equal(gate.check(context()), null);
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('confirmed matching block persists minimal metadata and survives a new instance', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record({ ...context(), code: 'private code', args: ['private args'] }, {
    ...blocked(), observed_at: 'private', screenshot: 'private pixels',
    alert: { ...blocked().alert, title: 'private title', text: 'private unrelated window text' },
  });
  assert.equal(value.state, 'security_alert_observed');
  assert.match(value.observed_at, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/);
  assert.equal(value.context.artifact.path, NORMAL);
  assert.equal(value.context.artifact.sha256_status, 'caller_supplied_unverified');
  assert.deepEqual(value.alert, { vendor: 'Norton', pid: 123, process: 'NortonUI.exe', hwnd: '456',
    match_kind: 'exact_path', blocked: true, reason: 'matching_artifact_blocked' });
  assert.equal(JSON.stringify(value).includes('private'), false);
  assert.deepEqual(JSON.parse(fs.readFileSync(fileFor(directory), 'utf8')), value);
  assert.deepEqual(createSecurityAlertHold({ directory }).check(context()), value);
});

test('confirmed fixed-source log block persists without inventing a window identity', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context(), logBlock({ raw_text: 'private raw log entry', log_path: 'private log path' }));
  assert.deepEqual(value.alert, { vendor: 'Norton', source: 'Norton autosandbox.log', pid: null,
    process: 'Norton log', hwnd: null, event_at: '2026-10-13T00:15:30.000Z', match_kind: 'exact_path',
    blocked: true, reason: 'matching_artifact_blocked', result: 'blocked' });
  assert.equal(JSON.stringify(value).includes('private'), false);
  assert.equal(Object.hasOwn(value.alert, 'artifact_path'), false, 'Artifact path belongs only in context');
  assert.deepEqual(createSecurityAlertHold({ directory }).check(context(ARTIFACT, HASH_B)), value);
});

test('explicit quarantine and access/execution denial log results use canonical blocked metadata', t => {
  for (const [observed, expected] of [['quarantined', 'quarantined'], ['denied', 'denied']]) {
    const directory = fixture(t);
    const value = createSecurityAlertHold({ directory }).record(context(), logBlock({ result: observed }));
    assert.equal(value.alert.result, expected);
    assert.deepEqual(createSecurityAlertHold({ directory }).check(context()), value);
  }
});

test('informational autosandbox log notice never creates a persistent pause', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  assert.equal(gate.record(context(), logBlock({ blocked: false, severity: 'informational', result: 'Sandbox' })), null);
  assert.equal(gate.check(context()), null);
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('wrong-source, malformed, uncorrelated or non-denial log evidence cannot create a hold', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  for (const evidence of [logBlock({ source: 'Other security log' }), logBlock({ process: 'NortonUI.exe' }),
    logBlock({ pid: 123 }), logBlock({ hwnd: '456' }), logBlock({ event_at: 'bad' }),
    logBlock({ event_at: '2026-02-31T00:00:00.000Z' }), logBlock({ event_at: '2026-10-13T00:15:30+00:00' }),
    logBlock({ artifact_correlation: 'basename_inference' }), logBlock({ result: 'Sandbox' }),
    logBlock({ result: 'execution_denied' }), logBlock({ result: 'access denied' }), logBlock({ result: undefined, reason: 'blocked' }),
    logBlock({ result: 'allowed' }), logBlock({ result: 'private'.repeat(100) }),
    logBlock({ artifact_path: 'C:\\Fixture\\Other\\alpha.exe' })]) {
    assert.throws(() => gate.record(context(), evidence), TypeError);
    assert.equal(gate.check(context()), null);
  }
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('case, slash, dot-segment and extended-drive aliases retain the same path hold', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context(), blocked());
  for (const alias of ['c:/FIXTURE/build/ALPHA.EXE', 'C:\\Fixture\\Elsewhere\\..\\Build\\alpha.exe',
    '\\\\?\\C:\\Fixture\\Build\\alpha.exe', 'C:\\Fixture\\Build. \\alpha.exe. ']) {
    assert.strictEqual(gate.check(context(alias, HASH_B, 'command-new')), value, alias);
    assert.deepEqual(createSecurityAlertHold({ directory }).check(context(alias, HASH_B)), value, alias);
  }
  assert.equal(fs.readdirSync(directory).length, 1);
});

test('UNC and extended-UNC aliases have one independent artifact key', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context('\\\\Server\\Share\\Build\\alpha.exe'), blocked());
  assert.strictEqual(gate.check(context('//server/share/build/ALPHA.EXE', HASH_B)), value);
  assert.deepEqual(createSecurityAlertHold({ directory }).check(context('\\\\?\\UNC\\SERVER\\Share\\Build\\alpha.exe')), value);
  assert.equal(value.context.artifact.path, '\\\\server\\share\\build\\alpha.exe');
});

test('rebuilt artifact hash and changed command ID do not release or replace the first hold', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context(), blocked());
  const bytes = fs.readFileSync(fileFor(directory), 'utf8');
  assert.strictEqual(gate.record(context(ARTIFACT, HASH_B, 'new-command'), blocked({ pid: 999 })), value);
  assert.strictEqual(gate.check(context(ARTIFACT, HASH_B)), value);
  assert.deepEqual(createSecurityAlertHold({ directory }).check(context(ARTIFACT, HASH_B)), value);
  assert.equal(fs.readFileSync(fileFor(directory), 'utf8'), bytes);
  assert.equal(value.context.artifact.sha256, HASH_A);
});

test('distinct directories with the same basename remain independent', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const first = gate.record(context(), blocked());
  const other = context('C:\\Fixture\\Other\\alpha.exe', HASH_A);
  assert.equal(gate.check(other), null);
  const second = gate.record(other, blocked({ pid: 456 }));
  assert.notEqual(first.artifact_key, second.artifact_key);
  assert.strictEqual(gate.check(context()), first);
  assert.strictEqual(gate.check(other), second);
  assert.equal(fs.readdirSync(directory).length, 2);
});

test('informational sandbox notices and unrelated command failures never create holds', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  for (const evidence of [undefined, {}, { error: 'EACCES' }, { severity: 'informational' },
    blocked({ blocked: false, severity: 'informational' }), { state: 'security_alert_notice',
      alert: { pid: 123, process: 'NortonUI.exe', artifact_correlation: 'exact_path', blocked: false } }]) {
    assert.equal(gate.record(context(), evidence), null);
  }
  assert.equal(gate.check(context()), null);
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('a previous hold stays immutable after informational notices, success and file deletion', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context(), blocked());
  fs.unlinkSync(fileFor(directory));
  assert.strictEqual(gate.record(context(), blocked({ blocked: false, severity: 'informational' })), value);
  assert.strictEqual(gate.check({ ...context(), success: true, window_disappeared: true }), value);
  assert.equal(fs.existsSync(fileFor(directory)), false);
});

test('reading an existing hold latches it even if its file later disappears', t => {
  const directory = fixture(t);
  createSecurityAlertHold({ directory }).record(context(), blocked());
  const gate = createSecurityAlertHold({ directory }), value = gate.check(context());
  fs.unlinkSync(fileFor(directory));
  assert.strictEqual(gate.check(context()), value);
});

test('severity-only confirmed block and basename correlation use the bounded schema', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record(context(), blocked({ blocked: undefined, severity: 'blocked',
    artifact_correlation: 'basename_inference', hwnd: '0xABC' }));
  assert.equal(value.alert.match_kind, 'basename_inference');
  assert.equal(value.alert.hwnd, '0xabc');
  assert.deepEqual(createSecurityAlertHold({ directory }).check(context()), value);
});

test('flat artifact context and unavailable hash are explicit and bounded', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  const value = gate.record({ command_id: 'flat', command: 'fixture_command', artifact_path: ARTIFACT,
    artifact_sha256: HASH_A.toUpperCase() }, blocked());
  assert.equal(value.context.artifact.sha256, HASH_A);
  assert.deepEqual(createSecurityAlertHold({ directory }).check({ command_id: 'flat-new', command: 'fixture_command',
    artifact_path: ARTIFACT, sha256: HASH_B }), value);
  const other = gate.record(context('C:\\Fixture\\Other\\unknown.exe', null), blocked());
  assert.equal(other.context.artifact.sha256, null);
  assert.equal(other.context.artifact.sha256_status, 'unavailable');
});

test('malformed explicit context is rejected without recording metadata', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  for (const invalid of [null, [], 'private', { artifact: null }, { artifact_path: ARTIFACT },
    { ...context(), command_id: 'private args or code' }, { ...context(), command: '' },
    { ...context(), command_id: 'a'.repeat(129) }, { ...context(), command: 'x'.repeat(129) },
    { ...context(), artifact_path: ARTIFACT }, context(ARTIFACT, 'invalid hash'),
    { command_id: 'flat', command: 'fixture_command', artifact_path: ARTIFACT, artifact_sha256: HASH_A, sha256: HASH_B },
    context(ARTIFACT, 'a'.repeat(65)), context(ARTIFACT, 123)]) {
    assert.throws(() => gate.check(invalid), TypeError);
    assert.throws(() => gate.record(invalid, blocked()), TypeError);
  }
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('relative, device, stream, directory and oversized artifact paths are rejected', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  for (const invalid of ['alpha.exe', 'C:alpha.exe', '\\alpha.exe', '/tmp/alpha.exe',
    '\\\\.\\PhysicalDrive0', 'C:\\Fixture\\alpha.exe:stream', 'C:\\Fixture\\', 'C:\\NUL.exe',
    'C:\\Fixture\\bad\u0000.exe', 'C:\\Fixture\\wild*.exe', 'C:\\' + 'x'.repeat(1024)]) {
    assert.throws(() => gate.check(context(invalid)), TypeError, invalid);
  }
});

test('malformed or unrelated confirmed window evidence is rejected without a hold', t => {
  const directory = fixture(t), gate = createSecurityAlertHold({ directory });
  for (const evidence of [blocked({ pid: 0 }), blocked({ pid: 1.5 }), blocked({ process: 'NotNorton.exe' }),
    blocked({ process: 'NortonUI.exe private text' }), blocked({ hwnd: '0' }), blocked({ hwnd: 'private' }),
    blocked({ artifact_correlation: 'no_match' }), blocked({ artifact_correlation: undefined }),
    blocked({ blocked: false, severity: 'blocked' }), blocked({ blocked: true, severity: 'informational' })]) {
    assert.throws(() => gate.record(context(), evidence), TypeError);
    assert.equal(gate.check(context()), null);
  }
});

test('all returned metadata is recursively immutable', t => {
  const value = createSecurityAlertHold({ directory: fixture(t) }).record(context(), blocked());
  for (const obj of [value, value.context, value.context.artifact, value.alert]) assert.equal(Object.isFrozen(obj), true);
  assert.throws(() => { value.context.artifact.sha256 = HASH_B; }, TypeError);
  assert.throws(() => { value.alert.pid = 999; }, TypeError);
});

test('corrupt or mismatched holds fail closed only for their artifact and preserve bytes', t => {
  for (const malformed of ['{', 'null', '{}']) {
    const directory = fixture(t), target = fileFor(directory);
    fs.writeFileSync(target, malformed);
    const gate = createSecurityAlertHold({ directory }), value = gate.check(context());
    expectReadHold(value);
    assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
    assert.equal(fs.readFileSync(target, 'utf8'), malformed);
  }
});

test('wrong schema, artifact key/path, timestamps and unexpected raw fields are not accepted', t => {
  const originalDirectory = fixture(t);
  const original = createSecurityAlertHold({ directory: originalDirectory }).record(context(), blocked());
  for (const mutate of [value => { value.version = 2; }, value => { value.state = 'ready'; },
    value => { value.artifact_key = '0'.repeat(64); }, value => { value.context.artifact.path = 'c:\\other\\alpha.exe'; },
    value => { value.observed_at = 'bad'; }, value => { value.observed_at = '2026-02-31T00:00:00.000Z'; },
    value => { value.context.args = 'private'; }, value => { value.alert.text = 'private'; },
    value => { value.alert.blocked = false; }]) {
    const directory = fixture(t), value = JSON.parse(JSON.stringify(original));
    mutate(value);
    const bytes = JSON.stringify(value);
    fs.writeFileSync(fileFor(directory), bytes);
    const returned = createSecurityAlertHold({ directory }).check(context());
    expectReadHold(returned);
    assert.equal(JSON.stringify(returned).includes('private'), false);
    assert.equal(fs.readFileSync(fileFor(directory), 'utf8'), bytes);
  }
});

test('valid metadata key order does not change semantics or rewrite an existing hold', t => {
  const directory = fixture(t);
  const value = createSecurityAlertHold({ directory }).record(context(), blocked());
  const reordered = { ...value, context: { artifact: { sha256_status: value.context.artifact.sha256_status,
    sha256: HASH_A, path: NORMAL }, command: value.context.command, command_id: value.context.command_id },
  alert: Object.fromEntries(Object.entries(value.alert).reverse()) };
  const bytes = JSON.stringify(reordered, null, 2);
  fs.writeFileSync(fileFor(directory), bytes);
  const gate = createSecurityAlertHold({ directory });
  assert.deepEqual(gate.record(context(ARTIFACT, HASH_B), blocked({ pid: 999 })), value);
  assert.equal(fs.readFileSync(fileFor(directory), 'utf8'), bytes);
});

test('oversized hold is rejected before any open, within the 16 KiB bound', t => {
  const directory = fixture(t);
  fs.writeFileSync(fileFor(directory), Buffer.alloc(16385, 32));
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs,
    openSync() { assert.fail('oversized file must not be opened'); } } });
  expectReadHold(gate.check(context()), 'HOLD_TOO_LARGE');
});

test('directory and symbolic-link hold entries fail closed before opening', t => {
  const directory = fixture(t), target = fileFor(directory);
  fs.mkdirSync(target);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs,
    openSync() { assert.fail('nonregular file must not be opened'); } } });
  expectReadHold(gate.check(context()), 'HOLD_NOT_REGULAR');
  const second = fixture(t);
  fs.writeFileSync(fileFor(second), '{}');
  const links = createSecurityAlertHold({ directory: second, fsImpl: { ...fs, lstatSync(name) {
    const stat = fs.lstatSync(name);
    if (name === fileFor(second)) return { ...stat, isFile: () => true, isSymbolicLink: () => true };
    return stat;
  }, openSync() { assert.fail('symlink must not be followed'); } } });
  expectReadHold(links.check(context()), 'HOLD_NOT_REGULAR');
});

test('redirected hold directory is not followed or written', t => {
  const directory = fixture(t);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, lstatSync(name) {
    if (name === directory) return { isDirectory: () => true, isSymbolicLink: () => true };
    return fs.lstatSync(name);
  }, openSync() { assert.fail('redirected directory must not be opened'); } } });
  assert.equal(gate.check(context()), null, 'Unsafe storage alone must not create a Norton pause');
  const value = gate.record(context(), blocked());
  assert.equal(value.state, 'security_alert_observed');
  assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'HOLD_DIRECTORY_UNSAFE' }]);
});

test('unreadable existing hold stays path-scoped without leaking exception text', t => {
  const directory = fixture(t), target = fileFor(directory);
  fs.writeFileSync(target, '{}');
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, openSync(name, flags, mode) {
    if (name === target) throw ioError('EACCES');
    return fs.openSync(name, flags, mode);
  } } });
  const value = gate.check(context());
  expectReadHold(value, 'EACCES');
  assert.equal(JSON.stringify(value).includes('private'), false);
  assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
});

test('directory access errors without a matching entry never pause arbitrary artifacts', t => {
  const directory = fixture(t);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, lstatSync(name) {
    if (name === directory) throw ioError('EACCES');
    return fs.lstatSync(name);
  } } });
  assert.equal(gate.check(context()), null);
  assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
  assert.equal(gate.record(context(), blocked({ blocked: false, severity: 'informational' })), null);
  const observed = gate.record(context(), blocked());
  assert.equal(observed.state, 'security_alert_observed');
  assert.deepEqual(observed.diagnostics, [{ reason: 'hold_persist_failed', code: 'EACCES' }]);
  assert.strictEqual(gate.check(context()), observed);
  assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
});

test('uninspectable matching filename alone is not treated as an established hold', t => {
  const directory = fixture(t), target = fileFor(directory);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, lstatSync(name) {
    if (name === target) throw ioError('EACCES');
    return fs.lstatSync(name);
  } } });
  assert.equal(gate.check(context()), null);
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('an ancestor junction or symlink prevents persistence without a global hold', t => {
  const directory = fixture(t), ancestor = path.dirname(directory);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, lstatSync(name) {
    if (name === ancestor) return { isDirectory: () => true, isSymbolicLink: () => true };
    return fs.lstatSync(name);
  }, openSync() { assert.fail('Ancestor redirect must not be followed'); } } });
  assert.equal(gate.check(context()), null);
  const value = gate.record(context(), blocked());
  assert.equal(value.state, 'security_alert_observed');
  assert.equal(value.diagnostics[0].code, 'HOLD_DIRECTORY_UNSAFE');
  assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
});

test('directory replacement after exclusive open stops before private metadata is written', t => {
  const directory = fixture(t);
  let changed = false;
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, openSync(name, flags, mode) {
    const fd = fs.openSync(name, flags, mode);
    if (flags === 'wx') changed = true;
    return fd;
  }, lstatSync(name) {
    const stat = fs.lstatSync(name);
    return changed && name === directory ? { ...stat, ino: stat.ino === 0 ? 1 : 0,
      isDirectory: () => true, isSymbolicLink: () => false } : stat;
  }, writeFileSync() { assert.fail('Must not write private metadata after a detected directory swap'); } } });
  const value = gate.record(context(), blocked());
  assert.equal(value.diagnostics[0].code, 'HOLD_DIRECTORY_CHANGED');
  assert.strictEqual(gate.check(context()), value);
  assert.equal(fs.statSync(fileFor(directory)).size, 0);
});

test('read bounds cover growth races and descriptors are closed', t => {
  const directory = fixture(t);
  createSecurityAlertHold({ directory }).record(context(), blocked());
  let closed = 0;
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs,
    readSync(fd, buffer, offset, length, position) {
      assert.equal(buffer.length, 16385); assert.equal(length, 16385); assert.equal(position, 0);
      return 16385;
    }, closeSync(fd) { closed++; fs.closeSync(fd); } } });
  expectReadHold(gate.check(context()), 'HOLD_TOO_LARGE');
  assert.equal(closed, 1);
});

test('opened replacement device and changed inode fail closed without reading', t => {
  for (const changed of [false, true]) {
    const directory = fixture(t);
    createSecurityAlertHold({ directory }).record(context(), blocked());
    let closed = 0;
    const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs,
      fstatSync(fd) {
        const stat = fs.fstatSync(fd);
        return changed ? { ...stat, ino: stat.ino === 0 ? 1 : 0, isFile: () => true }
          : { size: 1, isFile: () => false };
      }, readSync() { assert.fail('replacement must not be read'); },
      closeSync(fd) { closed++; fs.closeSync(fd); } } });
    expectReadHold(gate.check(context()), changed ? 'HOLD_FILE_CHANGED' : 'HOLD_NOT_REGULAR');
    assert.equal(closed, 1);
  }
});

test('failed write latches first, retains memory hold, and does not affect other artifacts', t => {
  const directory = fixture(t);
  let gate;
  gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, writeFileSync() {
    assert.equal(gate.check(context()).state, 'security_alert_observed');
    throw ioError('ENOSPC');
  } } });
  const value = gate.record(context(), blocked());
  assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'ENOSPC' }]);
  assert.strictEqual(gate.check(context(ARTIFACT, HASH_B)), value);
  assert.equal(gate.check(context('C:\\Fixture\\Other\\alpha.exe')), null);
  assert.equal(JSON.stringify(value).includes('private'), false);
  expectReadHold(createSecurityAlertHold({ directory }).check(context()));
});

test('exclusive creation uses private mode and fsync, preserving a race winner', t => {
  const directory = fixture(t);
  let winner, synced = 0;
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, openSync(name, flags, mode) {
    if (flags === 'wx') {
      assert.equal(mode, 0o600);
      winner = createSecurityAlertHold({ directory }).record(context(ARTIFACT, HASH_B, 'winner'), blocked({ pid: 789 }));
      throw ioError('EEXIST');
    }
    return fs.openSync(name, flags, mode);
  }, fsyncSync(fd) { synced++; fs.fsyncSync(fd); } } });
  assert.deepEqual(gate.record(context(), blocked()), winner);
  assert.deepEqual(JSON.parse(fs.readFileSync(fileFor(directory), 'utf8')), winner);
  assert.equal(synced, 0, 'Loser must not overwrite/fsync winner');
  const otherDirectory = fixture(t);
  let normalSync = 0;
  createSecurityAlertHold({ directory: otherDirectory, fsImpl: { ...fs,
    fsyncSync(fd) { normalSync++; fs.fsyncSync(fd); } } }).record(context(), blocked());
  assert.equal(normalSync, 1);
});

test('fsync or close failure preserves the latched hold with bounded diagnostics', t => {
  for (const action of ['fsync', 'close']) {
    const directory = fixture(t);
    const impl = { ...fs };
    if (action === 'fsync') impl.fsyncSync = () => { throw ioError('EIO'); };
    else impl.closeSync = fd => { fs.closeSync(fd); throw ioError('EIO'); };
    const gate = createSecurityAlertHold({ directory, fsImpl: impl });
    const value = gate.record(context(), blocked());
    assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'EIO' }]);
    assert.strictEqual(gate.check(context()), value);
    assert.equal(JSON.stringify(value).includes('private'), false);
  }
});

test('an exclusive-create race with a vanished winner retains a diagnosed memory latch', t => {
  const directory = fixture(t);
  const gate = createSecurityAlertHold({ directory, fsImpl: { ...fs, openSync(name, flags, mode) {
    if (flags === 'wx') throw ioError('EEXIST');
    return fs.openSync(name, flags, mode);
  } } });
  const value = gate.record(context(), blocked());
  assert.equal(value.state, 'security_alert_observed');
  assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'EEXIST' }]);
  assert.strictEqual(gate.check(context()), value);
  assert.equal(fs.readdirSync(directory).length, 0);
});

test('maximum accepted metadata remains below 16 KiB; relative directories are rejected', t => {
  const directory = fixture(t);
  const supplied = context('C:\\' + '\u4e2d'.repeat(990) + '.exe');
  supplied.command_id = 'a'.repeat(128); supplied.command = 'b'.repeat(128);
  const value = createSecurityAlertHold({ directory }).record(supplied, blocked());
  assert.ok(Buffer.byteLength(JSON.stringify(value), 'utf8') <= 16384);
  for (const invalid of [undefined, '', '.', 'relative', 123, '\u0000']) {
    assert.throws(() => createSecurityAlertHold({ directory: invalid }), TypeError);
  }
});
