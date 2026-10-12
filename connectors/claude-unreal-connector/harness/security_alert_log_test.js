// SPDX-License-Identifier: MIT
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createNortonLogReader, parseAutosandboxTail, parseNortonLocalTimestamp } = require('../extension/server/security-alert-log');

const FILE = 'C:\\ProgramData\\Norton\\Antivirus\\log\\autosandbox.log';
const ARTIFACT = 'C:\\Project\\Build\\fixture-task.exe';
const CONTEXT = { artifact: { path: ARTIFACT } };
const SINCE = '2026-10-12T22:56:10.900Z';
const NOW = '2026-10-12T22:56:15.000Z';
const localParser = (text, parts) => Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour + 7, parts.minute, parts.second);
const options = { context: CONTEXT, sinceUtc: SINCE, nowUtc: NOW, parseLocalTimestamp: localParser };
function entry({ timestamp = '10/12/2026 3:56:11 PM', artifact = ARTIFACT, result = 'Sandboxing (no custody)' } = {}) {
  return `${timestamp}\tAutosandbox candidate: ${artifact}\n\t[Source: C:\\Private\\Compiler.exe PID 3672]\n\t[Opened by: ${artifact}]\n\t[Reason: 0x00020000]\n\t --> Result: ${result}\n\t --> Instrumentation: Instrumentation inside sandbox requested\n\n`;
}
function fakeFs(text, overrides = {}) {
  const bytes = Buffer.from(text);
  const calls = [];
  const impl = { calls,
    lstatSync(file) { calls.push(['lstat', file]); assert.equal(file, FILE); return { isFile: () => true }; },
    openSync(file, flags) { calls.push(['open', file, flags]); assert.equal(file, FILE); return 77; },
    fstatSync(fd) { assert.equal(fd, 77); return { size: bytes.length, isFile: () => true }; },
    readSync(fd, output, start, length, offset) { calls.push(['read', length, offset]); assert.equal(fd, 77); return bytes.copy(output, start, offset, offset + length); },
    closeSync(fd) { calls.push(['close', fd]); }, ...overrides };
  return impl;
}
function reader(impl) { return createNortonLogReader({ fsImpl: impl, parseLocalTimestamp: localParser, clock: () => NOW }); }

test('exact existing entry yields an informational log notice, not a UI alert', () => {
  const [event] = parseAutosandboxTail(entry(), options);
  assert.equal(event.source, 'Norton autosandbox.log');
  assert.equal(event.event_at, '2026-10-12T22:56:11.000Z');
  assert.equal(event.kind, 'notice');
  assert.equal(event.result, 'Sandboxing (no custody)');
  assert.equal(event.artifact_path, ARTIFACT);
  assert.equal(event.process, 'Norton log');
  assert.equal(event.pid, null); assert.equal(event.hwnd, null);
  assert.equal(event.reason_code, '0x00020000');
  assert.equal(JSON.stringify(event).includes('Private'), false);
  assert.deepEqual(parseAutosandboxTail(entry().replace('Compiler.exe PID 3672', 'OtherCompiler.exe PID 9000'), options), [event]);
});

test('only explicit blocked/quarantined/denied results are blocks', () => {
  for (const result of ['Blocked', 'Quarantined', 'Execution denied', 'Access denied', 'File was blocked']) {
    const event = parseAutosandboxTail(entry({ result }), options)[0];
    assert.equal(event.kind, 'block');
    assert.ok(['blocked', 'quarantined', 'denied'].includes(event.result));
  }
  for (const result of ['Sandboxing (no custody)', 'Not blocked', 'Not quarantined', 'Allowed', 'Analysis complete']) {
    assert.equal(parseAutosandboxTail(entry({ result }), options)[0].kind, 'notice');
  }
});

test('strict timestamps reject malformed and impossible dates before invoking injected parser', () => {
  let invoked = 0;
  for (const timestamp of ['02/30/2026 3:56:11 PM', '13/12/2026 3:56:11 PM', '10/12/2026 0:56:11 PM',
    '10/12/2026 13:56:11 PM', '10/12/2026 3:60:11 PM', '10/12/2026 3:56:60 PM',
    '1/12/2026 3:56:11 PM', '10/12/2026 3:56:11 pm']) {
    assert.deepEqual(parseAutosandboxTail(entry({ timestamp }), { ...options, parseLocalTimestamp() { invoked++; return Date.parse(NOW); } }), []);
  }
  assert.equal(invoked, 0);
  assert.equal(parseNortonLocalTimestamp('02/30/2026 3:56:11 PM'), null);
  const local = new Date(2026, 9, 12, 15, 56, 11);
  assert.equal(parseNortonLocalTimestamp('10/12/2026 3:56:11 PM'), +local);
});

test('events outside current command are ignored; one second rounding is permitted', () => {
  assert.equal(parseAutosandboxTail(entry({ timestamp: '10/12/2026 3:56:10 PM' }), options).length, 1);
  for (const timestamp of ['10/12/2026 3:56:09 PM', '10/12/2026 3:56:16 PM', '10/11/2026 3:56:11 PM']) {
    assert.deepEqual(parseAutosandboxTail(entry({ timestamp }), options), []);
  }
});

test('exact Windows path required, including rejection of same basename elsewhere', () => {
  for (const artifact of ['C:\\Other\\fixture-task.exe', ARTIFACT + '.old', 'fixture-task.exe']) {
    assert.deepEqual(parseAutosandboxTail(entry({ artifact }), options), []);
  }
  assert.equal(parseAutosandboxTail(entry({ artifact: 'c:/project/build/FIXTURE-TASK.exe' }), options).length, 1);
});

test('duplicate polls and repeated entries derive stable content identities', () => {
  const first = parseAutosandboxTail(entry(), options);
  const second = parseAutosandboxTail(entry() + entry(), options);
  assert.deepEqual(second, first);
  assert.match(first[0].event_id, /^[a-f0-9]{64}$/);
  assert.notEqual(parseAutosandboxTail(entry({ result: 'Blocked' }), options)[0].event_id, first[0].event_id);
});

test('result/reason cannot bleed from previous or next candidate entries', () => {
  const candidate = `10/12/2026 3:56:11 PM\tAutosandbox candidate: ${ARTIFACT}\n\t[Reason: 0x1]\n`;
  assert.deepEqual(parseAutosandboxTail('\t --> Result: Blocked\n' + candidate + entry({ artifact: 'C:\\Other\\other.exe', result: 'Blocked' }), options), []);
  assert.deepEqual(parseAutosandboxTail(candidate + entry({ timestamp: 'invalid timestamp', artifact: 'C:\\Other\\other.exe', result: 'Blocked' }), options), []);
  assert.deepEqual(parseAutosandboxTail(candidate + '\tnoise\n'.repeat(5) + '\t --> Result: Blocked\n', options), []);
  assert.deepEqual(parseAutosandboxTail(entry({ result: 'Blocked C:\\Private\\other.exe' }), options), []);
});

test('reader requests only final 64 KiB at a fixed ordinary regular file', () => {
  const impl = fakeFs('unrelated private history\n'.repeat(6000) + entry());
  const result = reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE });
  assert.equal(result.available, true);
  assert.equal(result.history.length, 1);
  const read = impl.calls.find(call => call[0] === 'read');
  assert.equal(read[1], 65536); assert.ok(read[2] > 0);
  assert.equal(impl.calls.filter(call => call[0] === 'read').length, 1);
  assert.equal(impl.calls.at(-1)[0], 'close');
});

test('access denial reports unavailable without raw errors, retries or alternate paths', () => {
  let attempts = 0;
  const impl = fakeFs('', { openSync() { attempts++; throw Object.assign(new Error('private credentials path'), { code: 'EACCES' }); } });
  const result = reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE });
  assert.deepEqual(result, { available: false, reason: 'history_unavailable', history_source: 'Norton autosandbox.log', history: [] });
  assert.equal(impl.calls.length, 1);
  assert.equal(attempts, 1);
});

test('nonregular file and descriptor replacement are refused without reading', () => {
  for (const field of ['lstatSync', 'fstatSync']) {
    const impl = fakeFs(entry(), { [field]() { return { size: 1, isFile: () => false }; } });
    assert.equal(reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE }).available, false);
    assert.equal(impl.calls.some(call => call[0] === 'read'), false);
  }
});

test('missing context/time and aborted observation perform no file access', () => {
  const impl = fakeFs(entry());
  const gate = reader(impl);
  assert.equal(gate.inspect({ sinceUtc: SINCE }).available, false);
  assert.equal(gate.inspect({ context: CONTEXT }).available, false);
  assert.equal(gate.inspect({ context: CONTEXT, sinceUtc: 'bad' }).available, false);
  assert.equal(gate.inspect({ context: CONTEXT, sinceUtc: SINCE, signal: { aborted: true } }).reason, 'inspection_aborted');
  assert.equal(impl.calls.length, 0);
});

test('truncated leading candidate and trailing partial entry cannot establish an event', () => {
  assert.deepEqual(parseAutosandboxTail(entry(), { ...options, leadingTruncated: true }), []);
  assert.deepEqual(parseAutosandboxTail(entry().split('\n').slice(0, 5).join('\n'), { ...options, trailingTruncated: true }), []);
  const impl = fakeFs(entry().split('\n').slice(0, 5).join('\n'));
  assert.deepEqual(reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE }).history, []);
});

test('short reads and timestamp-provider failure never produce alert evidence', () => {
  const impl = fakeFs(entry(), { readSync() { return 0; } });
  assert.equal(reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE }).available, false);
  for (const parseLocalTimestamp of [() => 'bad', () => { throw new Error('private'); }]) {
    assert.deepEqual(parseAutosandboxTail(entry(), { ...options, parseLocalTimestamp }), []);
  }
});

test('abort during the bounded read discards all evidence and closes descriptor', () => {
  const signal = { aborted: false };
  const impl = fakeFs(entry());
  const originalRead = impl.readSync;
  impl.readSync = (...args) => { const count = originalRead(...args); signal.aborted = true; return count; };
  const result = reader(impl).inspect({ context: CONTEXT, sinceUtc: SINCE, signal });
  assert.equal(result.reason, 'inspection_aborted');
  assert.deepEqual(result.history, []);
  assert.equal(impl.calls.at(-1)[0], 'close');
});

test('history output remains capped independently of tail size', () => {
  let text = '';
  for (let second = 0; second < 70; second++) {
    text += entry({ timestamp: `10/12/2026 3:${second < 60 ? '55' : '56'}:${String(second % 60).padStart(2, '0')} PM` });
  }
  const history = parseAutosandboxTail(text, { ...options, sinceUtc: '2026-10-12T22:55:00Z' });
  assert.equal(history.length, 64);
});
