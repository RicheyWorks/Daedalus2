'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createRecoveryHold } = require('../extension/server/recovery-hold');

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-hold-test-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return path.join(directory, 'hold.json');
}
function error(code) { return Object.assign(new Error('private error text'), { code }); }
function stored(details = {}) {
  return { version: 1, state: 'recovery_required', observed_at: '2026-10-12T00:00:00.000Z', details };
}

test('absent file is clear, with no clear API', t => {
  const gate = createRecoveryHold({ file: fixture(t) });
  assert.equal(gate.check(), null);
  assert.deepEqual(Object.keys(gate).sort(), ['check', 'record']);
});

test('record persists metadata and survives connector restart', t => {
  const file = fixture(t);
  const gate = createRecoveryHold({ file });
  const value = gate.record({ pid: 123, session: 'editor-123', windowTitle: 'Restore Packages', png: 'private', conversation: 'private' });
  assert.equal(value.state, 'recovery_required');
  assert.equal(value.version, 1);
  assert.match(value.observed_at, /^\d{4}-\d\d-\d\dT.*Z$/);
  assert.deepEqual(value.details, { pid: 123, session: 'editor-123', windowtitle: 'Restore Packages' });
  assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')), value);
  assert.deepEqual(createRecoveryHold({ file }).check(), value);
  assert.equal(fs.readFileSync(file, 'utf8').includes('private'), false);
});

test('file disappearance and healthy checks never release an observed hold', t => {
  const file = fixture(t);
  const gate = createRecoveryHold({ file });
  const value = gate.record({ title: 'Restore Packages' });
  fs.unlinkSync(file);
  assert.strictEqual(gate.check({ state: 'ready', ping: { healthy: true } }), value);
  assert.strictEqual(gate.record({ state: 'ready' }), value);
  assert.equal(fs.existsSync(file), false);
  assert.equal(createRecoveryHold({ file }).check(), null); // Only a new instance can see owner removal.
});

test('reading an existing hold also latches after deletion', t => {
  const file = fixture(t);
  fs.writeFileSync(file, JSON.stringify(stored({ pid: 321 })));
  const gate = createRecoveryHold({ file });
  const value = gate.check();
  fs.unlinkSync(file);
  assert.strictEqual(gate.check(), value);
});

test('existing file is never overwritten by a later observation', t => {
  const file = fixture(t);
  const bytes = JSON.stringify(stored({ pid: 5, windowtitle: 'Restore Packages' }), null, 2);
  fs.writeFileSync(file, bytes);
  const gate = createRecoveryHold({ file });
  assert.deepEqual(gate.record({ pid: 9 }), stored({ pid: 5, windowtitle: 'Restore Packages' }));
  assert.equal(fs.readFileSync(file, 'utf8'), bytes);
});

test('malformed or non-hold JSON fails closed and is preserved', t => {
  for (const text of ['{', 'null', '{}', JSON.stringify({ ...stored(), state: 'ready' }), JSON.stringify({ ...stored(), observed_at: 'bad' })]) {
    const file = fixture(t);
    fs.writeFileSync(file, text);
    const gate = createRecoveryHold({ file });
    const value = gate.record({ pid: 8 });
    assert.equal(value.state, 'recovery_required');
    assert.equal(value.diagnostics[0].reason, 'hold_read_failed');
    assert.equal(fs.readFileSync(file, 'utf8'), text);
    fs.unlinkSync(file);
    assert.strictEqual(gate.check(), value);
  }
});

test('unreadable file fails closed without leaking exception text', t => {
  const file = fixture(t);
  const impl = { ...fs, lstatSync() { throw error('EACCES'); } };
  const gate = createRecoveryHold({ file, fsImpl: impl });
  const value = gate.check();
  assert.equal(value.state, 'recovery_required');
  assert.deepEqual(value.diagnostics, [{ reason: 'hold_read_failed', code: 'EACCES' }]);
  assert.equal(JSON.stringify(value).includes('private'), false);
});

test('persistence failure keeps synchronous in-memory hold', t => {
  const file = fixture(t);
  let gate;
  const impl = { ...fs, writeFileSync() {
    assert.equal(gate.check().state, 'recovery_required');
    throw error('ENOSPC');
  } };
  gate = createRecoveryHold({ file, fsImpl: impl });
  const value = gate.record({ pid: 3 });
  assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'ENOSPC' }]);
  assert.strictEqual(gate.check(), value);
  assert.equal(fs.statSync(file).size, 0);
  assert.equal(createRecoveryHold({ file }).check().state, 'recovery_required');
});

test('exclusive-create race preserves the winner', t => {
  const file = fixture(t);
  const winner = stored({ pid: 77 });
  const impl = { ...fs, openSync(target, flags, mode) {
    if (flags === 'wx') {
      assert.equal(mode, 0o600);
      fs.writeFileSync(target, JSON.stringify(winner));
      throw error('EEXIST');
    }
    return fs.openSync(target, flags, mode);
  } };
  assert.deepEqual(createRecoveryHold({ file, fsImpl: impl }).record({ pid: 2 }), winner);
  assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')), winner);
});

test('directories and oversized files fail closed without opening them', t => {
  for (const kind of ['directory', 'large']) {
    const file = fixture(t);
    if (kind === 'directory') fs.mkdirSync(file);
    else fs.writeFileSync(file, Buffer.alloc(16385, 32));
    const impl = { ...fs, openSync() { assert.fail('must reject before opening'); } };
    const value = createRecoveryHold({ file, fsImpl: impl }).check();
    assert.equal(value.state, 'recovery_required');
    assert.equal(value.diagnostics[0].code, kind === 'directory' ? 'HOLD_NOT_REGULAR' : 'HOLD_TOO_LARGE');
  }
});

test('file replacement after open is checked as a regular file before reading', t => {
  const file = fixture(t);
  fs.writeFileSync(file, JSON.stringify(stored()));
  let closed = false;
  const impl = { ...fs, fstatSync() { return { size: 1, isFile: () => false }; },
    readSync() { assert.fail('must not read a pipe/device'); },
    closeSync(fd) { closed = true; fs.closeSync(fd); } };
  const value = createRecoveryHold({ file, fsImpl: impl }).check();
  assert.equal(value.diagnostics[0].code, 'HOLD_NOT_REGULAR');
  assert.equal(closed, true);
});

test('reads have an explicit 16 KiB bound, including growth races', t => {
  const file = fixture(t);
  fs.writeFileSync(file, JSON.stringify(stored()));
  const impl = { ...fs, readSync(fd, buffer, offset, length, position) {
    assert.equal(length, 16385);
    assert.equal(position, 0);
    return 16385;
  } };
  const value = createRecoveryHold({ file, fsImpl: impl }).check();
  assert.equal(value.state, 'recovery_required');
  assert.equal(value.diagnostics[0].code, 'HOLD_TOO_LARGE');
});

test('metadata is bounded and arbitrary payloads are discarded', t => {
  const file = fixture(t);
  const value = createRecoveryHold({ file }).record({ pid: -1, session: 'x'.repeat(100000), title: 'y'.repeat(100000), png: 'z'.repeat(100000) });
  assert.deepEqual(Object.keys(value.details).sort(), ['session', 'windowtitle']);
  assert.equal(value.details.session.length, 1024);
  assert.equal(value.details.windowtitle.length, 1024);
  assert.ok(fs.statSync(file).size < 16384);
});

test('returned holds cannot be mutated into healthy states', t => {
  const gate = createRecoveryHold({ file: fixture(t) });
  const value = gate.record({ title: 'Restore Packages' });
  assert.throws(() => { value.state = 'ready'; }, TypeError);
  assert.throws(() => { value.details.windowtitle = 'healthy'; }, TypeError);
  assert.equal(gate.check().state, 'recovery_required');
});

test('new hold is flushed before record returns, and flush failures stay held', t => {
  for (const failing of [false, true]) {
    const file = fixture(t);
    let flushed = false;
    const impl = { ...fs, fsyncSync(fd) {
      flushed = true;
      if (failing) throw error('EIO');
      fs.fsyncSync(fd);
    } };
    const gate = createRecoveryHold({ file, fsImpl: impl });
    const value = gate.record({ pid: 1 });
    assert.equal(flushed, true);
    assert.equal(value.state, 'recovery_required');
    if (failing) assert.deepEqual(value.diagnostics, [{ reason: 'hold_persist_failed', code: 'EIO' }]);
    assert.strictEqual(gate.check(), value);
  }
});
