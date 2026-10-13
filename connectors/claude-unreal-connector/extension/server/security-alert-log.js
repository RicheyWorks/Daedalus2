// SPDX-License-Identifier: MIT
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

const LOG_PATH = 'C:\\ProgramData\\Norton\\Antivirus\\log\\autosandbox.log';
const SOURCE = 'Norton autosandbox.log';
const MAX_BYTES = 64 * 1024;
const MAX_EVENTS = 64;
const HEADER = /^(\d{2}\/\d{2}\/\d{4} \d{1,2}:\d{2}:\d{2} (?:AM|PM))\tAutosandbox candidate: (.+)$/;

function timestampParts(text) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{1,2}):(\d{2}):(\d{2}) (AM|PM)$/.exec(text);
  if (!match) return null;
  const [, month, day, year, hour, minute, second, period] = match;
  const parts = { year: +year, month: +month, day: +day,
    hour: (+hour % 12) + (period === 'PM' ? 12 : 0), minute: +minute, second: +second };
  if (+hour < 1 || +hour > 12 || parts.year < 1970 || parts.year > 9999 ||
      parts.month < 1 || parts.month > 12 || parts.day < 1 || parts.minute > 59 || parts.second > 59) return null;
  const calendar = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  if (calendar.getUTCFullYear() !== parts.year || calendar.getUTCMonth() !== parts.month - 1 ||
      calendar.getUTCDate() !== parts.day) return null;
  return parts;
}

function parseNortonLocalTimestamp(text, parts = timestampParts(text)) {
  if (!parts) return null;
  const sameLocal = date => date.getFullYear() === parts.year && date.getMonth() === parts.month - 1 &&
    date.getDate() === parts.day && date.getHours() === parts.hour &&
    date.getMinutes() === parts.minute && date.getSeconds() === parts.second;
  const local = new Date(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
  if (!sameLocal(local)) return null; // Nonexistent local time during a DST jump.
  const offsets = new Set([-86400000, 0, 86400000].map(delta => new Date(+local + delta).getTimezoneOffset()));
  const naive = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
  const possibilities = [...offsets].map(offset => new Date(naive + offset * 60000)).filter(sameLocal);
  if (possibilities.length !== 1) return null; // Ambiguous local time is not fresh-command evidence.
  return +possibilities[0];
}

function epoch(value) {
  if (value instanceof Date) return +value;
  if (typeof value === 'number') return value;
  return typeof value === 'string' ? Date.parse(value) : NaN;
}
function normalizeArtifact(value) {
  if (typeof value !== 'string' || !value || value.length > 1024 || /[\u0000-\u001f\u007f]/.test(value) ||
      !(/^[a-z]:[\\/]/i.test(value) || /^\\\\[^\\/]+[\\/][^\\/]+[\\/]/.test(value))) return null;
  return path.win32.normalize(value).toLowerCase();
}
function contextArtifact(context) { return context?.artifact?.path ?? context?.artifact_path; }
function resultKind(result) {
  return /^(?:blocked|quarantined|denied)\b|^(?:access|execution|file|application|process)\s+(?:was\s+)?(?:blocked|quarantined|denied)\b/i.test(result)
    ? 'block' : 'notice';
}
function canonicalResult(result, kind) {
  if (kind !== 'block') return result;
  if (/\bquarantined\b/i.test(result)) return 'quarantined';
  if (/\bdenied\b/i.test(result)) return 'denied';
  return 'blocked';
}

/** Pure parser. Only complete candidate entries and their own following fields are considered. */
function parseAutosandboxTail(text, { context, sinceUtc, nowUtc, parseLocalTimestamp = parseNortonLocalTimestamp,
  leadingTruncated = false, trailingTruncated = false } = {}) {
  const artifactPath = contextArtifact(context);
  const normalized = normalizeArtifact(artifactPath);
  const since = epoch(sinceUtc), now = epoch(nowUtc);
  if (!normalized || !Number.isFinite(since) || !Number.isFinite(now) || since > now || typeof text !== 'string') return [];
  const lines = text.split(/\r?\n/);
  if (leadingTruncated) lines.shift();
  if (trailingTruncated) lines.pop();
  const events = new Map();
  for (let index = 0; index < lines.length; index++) {
    const header = HEADER.exec(lines[index]);
    if (!header || normalizeArtifact(header[2]) !== normalized) continue;
    const parts = timestampParts(header[1]);
    if (!parts) continue;
    let at;
    try { at = epoch(parseLocalTimestamp(header[1], Object.freeze({ ...parts }))); }
    catch (_) { continue; }
    if (!Number.isFinite(at) || at < since - 1000 || at > now) continue;
    let result = null, reasonCode = null, incomplete = false;
    for (let offset = 1; offset <= 5; offset++) {
      const line = lines[index + offset];
      if (line === undefined) { incomplete = trailingTruncated; break; }
      if (line.includes('\tAutosandbox candidate:') || line.trim() === '') break;
      const outcome = /^\s*--> Result:\s*([^\r\n]{1,160})$/.exec(line);
      if (outcome) {
        if (result !== null) { incomplete = true; break; }
        // Result labels must not expose arbitrary identity/path/compiler text.
        if (/[:\\/@\u0000-\u001f\u007f]/.test(outcome[1])) { incomplete = true; break; }
        result = outcome[1].trim();
      }
      const reason = /^\s*\[Reason:\s*(0x[0-9a-f]{1,8})\]\s*$/i.exec(line);
      if (reason) reasonCode = reason[1].toLowerCase();
    }
    if (!result || incomplete) continue;
    const kind = resultKind(result);
    result = canonicalResult(result, kind);
    const event = { source: SOURCE, event_at: new Date(at).toISOString(), artifact_path: artifactPath,
      kind, result, process: 'Norton log', pid: null, hwnd: null };
    if (reasonCode) event.reason_code = reasonCode;
    event.event_id = createHash('sha256').update(JSON.stringify({ source: SOURCE, at,
      artifact: normalized, result, reasonCode })).digest('hex');
    events.set(event.event_id, event);
  }
  return [...events.values()].sort((left, right) => left.event_at.localeCompare(right.event_at)).slice(-MAX_EVENTS);
}

function createNortonLogReader({ fsImpl = fs, parseLocalTimestamp = parseNortonLocalTimestamp,
  clock = Date.now } = {}) {
  if (typeof parseLocalTimestamp !== 'function' || typeof clock !== 'function') throw new TypeError('Timestamp parser and clock must be functions');
  const unavailable = reason => ({ available: false, reason, history_source: SOURCE, history: [] });
  function inspect({ context, sinceUtc, signal } = {}) {
    if (signal?.aborted) return unavailable('inspection_aborted');
    if (!normalizeArtifact(contextArtifact(context))) return unavailable('artifact_context_unavailable');
    let now;
    try { now = epoch(clock()); } catch (_) { return unavailable('time_context_unavailable'); }
    const since = epoch(sinceUtc);
    if (!Number.isFinite(since) || !Number.isFinite(now) || since > now) return unavailable('time_context_unavailable');
    let descriptor;
    try {
      if (!fsImpl.lstatSync(LOG_PATH).isFile()) return unavailable('history_unavailable');
      const constants = fsImpl.constants || fs.constants;
      descriptor = fsImpl.openSync(LOG_PATH, constants.O_RDONLY | (constants.O_NONBLOCK || 0) | (constants.O_NOFOLLOW || 0));
      const stat = fsImpl.fstatSync(descriptor);
      if (!stat.isFile() || !Number.isSafeInteger(stat.size) || stat.size < 0) return unavailable('history_unavailable');
      const count = Math.min(stat.size, MAX_BYTES), offset = stat.size - count;
      const bytes = Buffer.alloc(count);
      const read = count ? fsImpl.readSync(descriptor, bytes, 0, count, offset) : 0;
      if (signal?.aborted) return unavailable('inspection_aborted');
      if (read !== count) return unavailable('history_unavailable');
      const text = bytes.toString('utf8');
      const history = parseAutosandboxTail(text, { context, sinceUtc: since, nowUtc: now, parseLocalTimestamp,
        leadingTruncated: offset > 0, trailingTruncated: text.length > 0 && !text.endsWith('\n') });
      return { available: true, reason: history.length ? 'matching_recent_history' : 'no_matching_complete_recent_history',
        history_source: SOURCE, history };
    } catch (_) { return unavailable('history_unavailable'); }
    finally { if (descriptor !== undefined) { try { fsImpl.closeSync(descriptor); } catch (_) { /* No retry. */ } } }
  }
  return { inspect };
}

module.exports = { createNortonLogReader, parseAutosandboxTail, parseNortonLocalTimestamp };
