'use strict';

const fs = require('fs');
const MAX_BYTES = 16 * 1024;

// A hold has no runtime release. After resolving recovery and reconciling work,
// the owner removes the file manually and restarts the connector.
function createRecoveryHold({ file, fsImpl = fs }) {
  if (typeof file !== 'string' || !file) throw new TypeError('Recovery hold file is required');
  let held = null;

  function immutable(value) {
    Object.freeze(value.details);
    if (value.diagnostics) {
      value.diagnostics.forEach(Object.freeze);
      Object.freeze(value.diagnostics);
    }
    return Object.freeze(value);
  }

  function metadata(details) {
    const source = details && typeof details === 'object' ? details : {};
    const result = {};
    if (Number.isSafeInteger(source.pid) && source.pid > 0) result.pid = source.pid;
    for (const [key, value] of [
      ['session', source.session],
      ['windowtitle', source.windowtitle ?? source.windowTitle ?? source.title],
    ]) {
      if (typeof value === 'string') result[key] = value.slice(0, 1024);
    }
    return result;
  }

  function hold(details) {
    return immutable({ version: 1, state: 'recovery_required', observed_at: new Date().toISOString(), details: metadata(details) });
  }

  function diagnostic(reason, error) {
    // Do not persist arbitrary exception text, which may contain private data.
    return { reason, code: typeof error?.code === 'string' ? error.code.slice(0, 64) : null };
  }

  function readExisting() {
    let descriptor;
    try {
      let before;
      try { before = fsImpl.lstatSync(file); }
      catch (error) { if (error.code === 'ENOENT') return null; throw error; }
      if (!before.isFile()) throw Object.assign(new Error('Not a regular file'), { code: 'HOLD_NOT_REGULAR' });
      if (before.size > MAX_BYTES) throw Object.assign(new Error('Hold too large'), { code: 'HOLD_TOO_LARGE' });
      const flags = (fsImpl.constants || fs.constants);
      descriptor = fsImpl.openSync(file, flags.O_RDONLY | (flags.O_NONBLOCK || 0) | (flags.O_NOFOLLOW || 0));
      const actual = fsImpl.fstatSync(descriptor);
      if (!actual.isFile()) throw Object.assign(new Error('Not a regular file'), { code: 'HOLD_NOT_REGULAR' });
      if (actual.size > MAX_BYTES) throw Object.assign(new Error('Hold too large'), { code: 'HOLD_TOO_LARGE' });
      const bytes = Buffer.alloc(MAX_BYTES + 1);
      const count = fsImpl.readSync(descriptor, bytes, 0, bytes.length, 0);
      if (count > MAX_BYTES) throw Object.assign(new Error('Hold too large'), { code: 'HOLD_TOO_LARGE' });
      const value = JSON.parse(bytes.subarray(0, count).toString('utf8'));
      if (!value || value.version !== 1 || value.state !== 'recovery_required' ||
          typeof value.observed_at !== 'string' || !Number.isFinite(Date.parse(value.observed_at)) ||
          !value.details || typeof value.details !== 'object' || Array.isArray(value.details)) {
        throw Object.assign(new Error('Invalid hold'), { code: 'HOLD_INVALID' });
      }
      return immutable({ version: 1, state: 'recovery_required', observed_at: value.observed_at, details: metadata(value.details) });
    } catch (error) {
      return immutable({ ...hold({}), diagnostics: [diagnostic('hold_read_failed', error)] });
    } finally {
      if (descriptor !== undefined) {
        try { fsImpl.closeSync(descriptor); } catch (_) { /* The safety latch still holds. */ }
      }
    }
  }

  function check() {
    if (held) return held;
    const existing = readExisting();
    if (existing) held = existing;
    return held;
  }

  function record(details) {
    if (held) return held;
    held = hold(details); // Latch before any filesystem operation can fail.
    const existing = readExisting();
    if (existing) { held = existing; return held; }
    let descriptor;
    try {
      descriptor = fsImpl.openSync(file, 'wx', 0o600);
      fsImpl.writeFileSync(descriptor, JSON.stringify(held) + '\n');
      fsImpl.fsyncSync(descriptor);
    } catch (error) {
      if (error.code === 'EEXIST') {
        const raced = readExisting();
        if (raced) { held = raced; return held; }
      }
      held = immutable({ ...held, diagnostics: [diagnostic('hold_persist_failed', error)] });
    } finally {
      if (descriptor !== undefined) {
        try { fsImpl.closeSync(descriptor); } catch (error) {
          held = immutable({ ...held, diagnostics: [diagnostic('hold_persist_failed', error)] });
        }
      }
    }
    return held;
  }

  return { check, record };
}

module.exports = { createRecoveryHold };
