// SPDX-License-Identifier: MIT
'use strict';

const { createHash } = require('node:crypto');
const { performance } = require('node:perf_hooks');

const NORTON = /^(?:NortonUI|Norton|NortonSecurity|NortonSecurityUI|Norton360|Norton360UI)(?:\.exe)?$/i;
const ALERT = /\b(?:security (?:alert|risk)|threat(?:s)? (?:detected|found|blocked|removed)|(?:malware|virus|suspicious|unsafe|untrusted)\b|quarantin(?:e|ed)|(?:file|application|program|execution) (?:was |has been |is )?(?:blocked|removed|stopped)|we (?:have )?(?:blocked|removed|stopped)|auto[- ]?sandbox|sandbox(?:ed|ing)?|analy[sz](?:ing|ed)|scanning|(?:auto[- ]?protect|SONAR) (?:blocked|detected|removed))\b/i;
const BLOCKED = /\b(?:(?:file|application|program|execution) (?:was |has been |is )?(?:blocked|removed|stopped|denied)|we (?:have )?(?:blocked|removed|stopped) (?:this |the |your |a |an )?(?:file|application|program|threat|malware|virus|execution)|(?:execution|access) (?:was |is )?denied|(?:threat|malware|virus) (?:was |has been |is )?(?:blocked|removed)|(?:auto[- ]?protect|SONAR) (?:blocked|removed))\b/i;
const MAX_TEXT = 4096;
const MAX_WINDOWS = 64;
const HISTORY_SOURCE = 'Norton autosandbox.log';
const clean = (value, size) => typeof value === 'string'
  ? value.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').slice(0, size) : '';
const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const normalizePath = value => value.replace(/\\/g, '/').toLowerCase();
const positive = value => Number.isSafeInteger(value) && value > 0;

function contextMetadata(value = {}) {
  const result = {};
  for (const key of ['command_id', 'command']) {
    if (typeof value[key] === 'string' && /^[\w.:-]{1,128}$/.test(value[key])) result[key] = value[key];
  }
  const artifact = value.artifact || { path: value.artifact_path, sha256: value.artifact_sha256 };
  if (artifact && typeof artifact.path === 'string' && artifact.path.length <= 1024 &&
      !/[\u0000-\u001f\u007f]/.test(artifact.path) &&
      (/^[a-z]:[\\/]/i.test(artifact.path) || /^\/(?!\/)/.test(artifact.path))) {
    result.artifact = { path: artifact.path, sha256: null, sha256_status: 'unavailable' };
    if (typeof artifact.sha256 === 'string' && /^[0-9a-f]{64}$/i.test(artifact.sha256)) {
      result.artifact.sha256 = artifact.sha256.toLowerCase();
      result.artifact.sha256_status = 'caller_supplied';
    }
  }
  return result;
}

function correlation(text, artifact) {
  if (!artifact) return null;
  const normalized = normalizePath(text);
  const full = normalizePath(artifact.path);
  const boundary = '(?=$|[^a-z0-9_.-]|\\.(?:\\s|$))';
  if (new RegExp(`${escape(full)}${boundary}`, 'i').test(normalized)) return 'exact_path';
  const basename = full.slice(full.lastIndexOf('/') + 1);
  // An explicit different directory is stronger evidence than a shared basename.
  // Quoted paths can contain spaces; unquoted paths stop at whitespace.
  const paths = [...normalized.matchAll(/(?:["']((?:[a-z]:\/|\/)[^"'\r\n]+)["']|((?:[a-z]:\/|\/)[^\s"'<>]+))/gi)]
    .map(match => (match[1] || match[2]).replace(/[.,;:]+$/, ''));
  if (paths.some(path => path.endsWith('/' + basename) && path !== full)) return null;
  if (basename.length >= 5 && new RegExp(`(?:^|[^a-z0-9_.-])${escape(basename)}${boundary}`, 'i').test(text)) {
    return 'basename_inference';
  }
  return null;
}

function redact(value, artifact) {
  return value
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[email redacted]')
    .replace(/\bhttps?:\/\/[^\s<>"']+/gi, '[URL redacted]')
    .replace(/[a-z]:[\\/][^\s"'<>]+/gi, path =>
      artifact && normalizePath(path.replace(/[.,;:]+$/, '')) === normalizePath(artifact.path) ? path : '[path redacted]')
    .replace(/(^|[\s"'(])(\/(?!\/)[^\s"'<>]+)/g, (match, prefix, path) =>
      prefix + (artifact && normalizePath(path.replace(/[.,;:]+$/, '')) === normalizePath(artifact.path) ? path : '[path redacted]'))
    .replace(/\b[a-z]:[\\/]Users[\\/][^\\/\s"']+/gi, 'C:\\Users\\[redacted]')
    .replace(/\b(?:account(?:id)?|login(?:id)?|machineid|user(?:name)?)\s*[:=]\s*[^\s,;]+/gi, '[identity redacted]');
}

function relevantText(value, artifact) {
  return redact(clean(value, MAX_TEXT).split(/\r?\n/)
    .filter(line => correlation(line, artifact) || (ALERT.test(line) &&
      !/\b[^\s"'<>]+\.(?:exe|dll|com|bat|cmd|ps1|msi)\b|[a-z]:[\\/]|\[.*path.*redacted.*\]/i.test(line)))
    .slice(0, 8).join('\n'), artifact).slice(0, 1024);
}

function reportsArtifactBlock(combined, artifact) {
  const blocked = line => BLOCKED.test(line) || /\bquarantined\b/i.test(line.replace(/\b(?:not|never)(?: been)? quarantined\b/gi, ''));
  const lines = combined.split(/\r?\n/);
  const related = lines.filter(line => correlation(line, artifact));
  if (related.some(blocked)) return true;
  // Accessible labels are often separate nodes ("Program blocked" then a filename).
  // Accept a generic block label only with a single-artifact notice. Never associate
  // an unrelated named file/history entry with the current artifact's sandbox notice.
  if (related.some(line => /\b(?:auto[- ]?sandbox|sandboxed|analy[sz](?:ing|ed)|scanning)\b/i.test(line))) return false;
  return lines.some(line => blocked(line) && !/\b[^\s"'<>]+\.(?:exe|dll|com|bat|cmd|ps1|msi)\b|[a-z]:[\\/]|\[.*path.*redacted.*\]/i.test(line));
}

function classifyHistory(snapshot, context, { sinceUtc, observedUtc } = {}) {
  if (!snapshot || snapshot.history === undefined) return null;
  if (snapshot.history_source !== HISTORY_SOURCE || !Array.isArray(snapshot.history) || snapshot.history.length > 64) {
    return { state: 'unavailable', reason: 'log_history_invalid' };
  }
  const utc = value => typeof value === 'string' && /Z$/.test(value) && Number.isFinite(Date.parse(value));
  if (!utc(sinceUtc) || !utc(observedUtc) || Date.parse(sinceUtc) > Date.parse(observedUtc)) {
    return { state: 'unavailable', reason: 'log_history_scope_unavailable' };
  }
  let notice;
  for (const event of snapshot.history) {
    if (!event || event.source !== HISTORY_SOURCE || !utc(event.event_at) ||
        Date.parse(event.event_at) < Date.parse(sinceUtc) - 1000 || Date.parse(event.event_at) > Date.parse(observedUtc) ||
        typeof event.artifact_path !== 'string' || normalizePath(event.artifact_path) !== normalizePath(context.artifact.path) ||
        !['notice', 'block'].includes(event.kind) || typeof event.result !== 'string' || event.result.length > 256) continue;
    const result = clean(event.result, 256);
    if (!ALERT.test(result) && !/\b(?:blocked|quarantined|denied)\b/i.test(result)) continue;
    const blocked = event.kind === 'block' && (/\b(?:blocked|denied)\b/i.test(result.replace(/\b(?:not|never)(?: been)? (?:blocked|denied)\b/gi, '')) ||
      /\bquarantined\b/i.test(result.replace(/\b(?:not|never)(?: been)? quarantined\b/gi, '')));
    const safeResult = blocked ? (/\bquarantined\b/i.test(result) ? 'quarantined' : /\bdenied\b/i.test(result) ? 'denied' : 'blocked')
      : redact(result, context.artifact);
    const record = {
      vendor: 'Norton', source: HISTORY_SOURCE, process: 'Norton log', pid: null, hwnd: null,
      event_at: new Date(event.event_at).toISOString(), artifact_path: context.artifact.path,
      title: '', text: redact(result, context.artifact), result: safeResult, kind: blocked ? 'block' : 'notice', text_available: true,
      timestamp_resolution_ms: 1000,
      artifact_correlation: 'exact_path', causality: 'unconfirmed', detection_verdict: 'not_assessed',
      blocked, severity: blocked ? 'blocked' : 'informational',
    };
    record.alert_id = createHash('sha256').update(JSON.stringify({ source: record.source,
      event_at: record.event_at, artifact: normalizePath(record.artifact_path), text: record.text,
      blocked: record.blocked })).digest('hex');
    if (blocked) return { state: 'alert', alert: record };
    if (!notice || record.event_at > notice.alert.event_at) notice = { state: 'alert', alert: record };
  }
  return notice || null;
}

/** Only a provider-filtered Norton window with actionable language AND an explicit
 * artifact match is an alert. A name/path match is correlation, not a malware verdict.
 * Unavailable inspection/text must never be represented as verified absence.
 */
function classifySecurityAlerts(snapshot, suppliedContext, historyScope) {
  const context = contextMetadata(suppliedContext);
  if (!context.artifact) return { state: 'unavailable', reason: 'artifact_context_unavailable' };
  const available = snapshot && (snapshot.ok === true || snapshot.available === true) && Array.isArray(snapshot.windows);
  const tooManyWindows = available && snapshot.windows.length > MAX_WINDOWS;
  let unreadable = false;
  let notice;
  for (const window of available && !tooManyWindows ? snapshot.windows : []) {
    if (!window || window.visible !== true || !positive(window.pid)) continue;
    const processName = window.process ?? window.processName;
    if (typeof processName !== 'string' || !NORTON.test(processName)) continue;
    const title = clean(window.title, 512);
    const text = clean(window.text, MAX_TEXT);
    if (window.text_available === false || typeof window.text !== 'string') unreadable = true;
    const combined = title + '\n' + text;
    if (!ALERT.test(combined)) continue;
    const association = correlation(combined, context.artifact);
    if (!association) continue;
    if (window.matched_path !== undefined && window.matched_path !== null &&
        (typeof window.matched_path !== 'string' || normalizePath(window.matched_path) !== normalizePath(context.artifact.path))) continue;
    const blocked = reportsArtifactBlock(combined, context.artifact);
    const record = {
      vendor: 'Norton', pid: window.pid, process: processName,
      hwnd: /^(?:\d{1,20}|0x[0-9a-f]{1,16})$/i.test(String(window.hwnd)) ? String(window.hwnd) : null,
      title: relevantText(title, context.artifact), text: relevantText(text, context.artifact),
      text_available: window.text_available !== false && typeof window.text === 'string',
      artifact_correlation: association, causality: 'unconfirmed', detection_verdict: 'not_assessed',
      blocked, severity: blocked ? 'blocked' : 'informational',
    };
    if (typeof window.start_time === 'string' && Number.isFinite(Date.parse(window.start_time))) {
      record.process_start_time = new Date(window.start_time).toISOString();
    }
    // The identity is content/session based, so an OS-reused handle cannot merge a new alert.
    record.alert_id = createHash('sha256').update(JSON.stringify({
      ...record, artifact: normalizePath(context.artifact.path),
    })).digest('hex');
    if (blocked) return { state: 'alert', alert: record };
    if (!notice) notice = { state: 'alert', alert: record };
  }
  const history = classifyHistory(snapshot, context, historyScope);
  if (history?.alert?.blocked) return history;
  if (notice) return notice;
  if (history) return history;
  if (!available) return { state: 'unavailable', reason: 'inspection_unavailable' };
  if (tooManyWindows) return { state: 'unavailable', reason: 'provider_window_limit' };
  return unreadable ? { state: 'unavailable', reason: 'alert_text_unavailable' }
    : { state: 'not_observed', reason: 'no_matching_alert_in_snapshot' };
}

class SecurityAlertError extends Error {
  constructor(evidence, dispatched = false) {
    super(evidence?.state === 'security_alert_held'
      ? 'This artifact has unreadable existing pause metadata; owner review is required. No new alert is claimed.'
      : 'Matching security alert observed; this artifact task is paused. Started work may still finish.');
    this.name = 'SecurityAlertError';
    this.code = evidence?.state === 'security_alert_held' ? 'SECURITY_ALERT_HELD' : 'SECURITY_ALERT_OBSERVED';
    this.state = evidence?.state === 'security_alert_held' ? 'security_alert_held' : 'security_alert_observed';
    this.details = evidence;
    this.dispatched = dispatched;
    this.outcome_uncertain = dispatched;
  }
}

function createSecurityAlertObserver({ inspect, capture, requestScreenshot = false,
  onEvidence, onPause, pollMs = 250, probeTimeoutMs = 1000, hookTimeoutMs = 1000,
  nowUtc = () => new Date().toISOString() } = {}) {
  if (typeof inspect !== 'function') throw new TypeError('A read-only inspect adapter is required');
  for (const [key, value] of Object.entries({ pollMs, probeTimeoutMs, hookTimeoutMs })) {
    if (!Number.isFinite(value) || value <= 0) throw new TypeError(`${key} must be positive and finite`);
  }
  for (const hook of [capture, onEvidence, onPause]) {
    if (hook !== undefined && typeof hook !== 'function') throw new TypeError('Optional hooks must be functions');
  }
  if (typeof requestScreenshot !== 'boolean' || typeof nowUtc !== 'function') throw new TypeError('Invalid observer options');
  const holds = new Map();
  const notices = new Map();
  const lastNotices = new Map();
  const observations = new Map();
  let latest = { state: 'inactive', reason: 'no_authorized_command' };
  const keyOf = context => context.artifact ? normalizePath(context.artifact.path) : `command:${context.command_id || ''}`;
  const timestamp = () => {
    const value = nowUtc();
    if (!Number.isFinite(Date.parse(value))) throw new TypeError('nowUtc must return a UTC-compatible timestamp');
    return new Date(value).toISOString();
  };

  async function bounded(adapter, args, budget, reason, externalSignal) {
    const controller = new AbortController();
    let timer, abort;
    try {
      const timeout = new Promise(resolve => {
        timer = setTimeout(() => { controller.abort(); resolve({ unavailable: true, reason }); }, budget);
      });
      const cancelled = new Promise(resolve => {
        if (!externalSignal) return;
        abort = () => { controller.abort(); resolve({ unavailable: true, reason: 'operation_aborted' }); };
        externalSignal.addEventListener('abort', abort, { once: true });
        if (externalSignal.aborted) abort();
      });
      return await Promise.race([
        Promise.resolve().then(() => adapter({ ...args, signal: controller.signal }))
          .catch(() => ({ unavailable: true, reason: 'adapter_unavailable' })), timeout, cancelled,
      ]);
    } finally {
      clearTimeout(timer);
      if (abort) externalSignal.removeEventListener('abort', abort);
      controller.abort();
    }
  }

  async function check({ context: suppliedContext, signal, timeoutMs = probeTimeoutMs,
    dispatched = false, onLatch, sinceUtc } = {}) {
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new TypeError('check timeoutMs must be positive and finite');
    const context = contextMetadata(suppliedContext);
    const startedUtc = sinceUtc ?? timestamp();
    const key = keyOf(context);
    if (holds.has(key)) throw new SecurityAlertError(holds.get(key), dispatched);
    if (signal?.aborted) return { state: 'unavailable', reason: 'operation_aborted' };
    let observation;
    if (!context.artifact) observation = { state: 'unavailable', reason: 'artifact_context_unavailable' };
    else {
      const snapshot = await bounded(inspect, { screenshot: false, context, sinceUtc: startedUtc }, Math.min(timeoutMs, probeTimeoutMs), 'inspection_timeout', signal);
      observation = snapshot?.unavailable ? { state: 'unavailable', reason: snapshot.reason }
        : classifySecurityAlerts(snapshot, context, { sinceUtc: startedUtc, observedUtc: timestamp() });
    }
    if (signal?.aborted) return { state: 'unavailable', reason: 'operation_aborted' };
    if (observation.state !== 'alert') {
      latest = { ...observation, observed_at: timestamp() };
      if (lastNotices.has(key)) latest.last_notice = lastNotices.get(key);
      const previous = observations.get(key);
      observations.set(key, latest);
      if (onEvidence && latest.state === 'unavailable' && previous?.reason !== latest.reason) {
        await bounded(onEvidence, { evidence: { ...latest, context } }, hookTimeoutMs, 'evidence_hook_timeout');
      }
      return latest;
    }

    // Concurrent observations of the same artifact cannot duplicate the pause/evidence hooks.
    if (holds.has(key)) throw new SecurityAlertError(holds.get(key), dispatched);

    if (!observation.alert.blocked) {
      const noticeKey = key + ':' + observation.alert.alert_id;
      let evidence = notices.get(noticeKey);
      if (!evidence) {
        evidence = { version: 1, state: 'security_alert_notice', observed_at: timestamp(), context,
          alert: observation.alert, screenshot: { status: 'not_requested' },
          pause: { state: 'not_required', scope: 'artifact' } };
        notices.set(noticeKey, evidence); // Deduplicate informational popups without holding the task.
        if (onEvidence) {
          const result = await bounded(onEvidence, { evidence }, hookTimeoutMs, 'evidence_hook_timeout');
          if (result?.unavailable) evidence.evidence_storage = { status: 'unavailable', reason: result.reason };
        }
      }
      latest = evidence;
      lastNotices.set(key, evidence);
      observations.set(key, evidence);
      return evidence;
    }

    const evidence = {
      version: 1, state: 'security_alert_observed', observed_at: timestamp(), context,
      alert: observation.alert, screenshot: { status: requestScreenshot ? 'unavailable' : 'not_requested' },
      pause: { state: 'latched', scope: 'artifact', hook: onPause ? 'pending' : 'not_configured' },
    };
    holds.set(key, evidence); // Latch before optional evidence, capture or pause I/O can fail.
    latest = evidence;
    observations.set(key, evidence);
    if (typeof onLatch === 'function') onLatch(new SecurityAlertError(evidence, dispatched));
    if (onPause) {
      const result = await bounded(onPause, { evidence }, hookTimeoutMs, 'pause_hook_timeout');
      evidence.pause.hook = result?.unavailable ? 'unavailable' : 'completed';
      if (result?.unavailable) evidence.pause.reason = result.reason;
    }
    if (requestScreenshot) {
      if (evidence.alert.source === HISTORY_SOURCE) {
        evidence.screenshot = { status: 'unavailable', reason: 'window_unavailable_for_log_event' };
      } else if (capture) {
        const result = await bounded(capture, {
          window: { pid: evidence.alert.pid, process: evidence.alert.process, hwnd: evidence.alert.hwnd }, context,
        }, hookTimeoutMs, 'screenshot_timeout');
        // Never attach pixels or an arbitrary path/URL to a tool response. A local writer owns the file.
        evidence.screenshot = result?.status === 'captured'
          ? { status: 'captured_locally' } : { status: 'unavailable' };
      } else evidence.screenshot.reason = 'capture_adapter_unavailable';
    }
    if (onEvidence) {
      const result = await bounded(onEvidence, { evidence }, hookTimeoutMs, 'evidence_hook_timeout');
      if (result?.unavailable) evidence.evidence_storage = { status: 'unavailable', reason: result.reason };
    }
    throw new SecurityAlertError(evidence, dispatched);
  }

  async function run({ context, call, timeoutMs, signal } = {}) {
    if (typeof call !== 'function' || !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
      throw new TypeError('call and a positive finite timeoutMs are required');
    }
    const controller = new AbortController();
    const startedUtc = timestamp();
    const deadline = performance.now() + timeoutMs;
    let dispatched = false, timer, tickTimer, error, rejectStop, abort;
    const remaining = () => Math.max(0, deadline - performance.now());
    const stopped = new Promise((_, reject) => { rejectStop = reject; });
    stopped.catch(() => {});
    function stop(reason) {
      if (!error) error = reason;
      controller.abort(error);
      rejectStop(error);
    }
    const timeoutError = () => Object.assign(new Error('Authorized command observation deadline expired; started work may still finish.'), {
      code: 'SECURITY_OBSERVATION_TIMEOUT', dispatched, outcome_uncertain: dispatched,
    });
    timer = setTimeout(() => stop(timeoutError()), timeoutMs);
    if (signal) {
      abort = () => stop(signal.reason instanceof Error ? signal.reason : new Error('Authorized command aborted'));
      signal.addEventListener('abort', abort, { once: true });
      if (signal.aborted) abort();
    }
    async function probe() {
      if (error) throw error;
      if (!remaining()) throw timeoutError();
      const result = await Promise.race([check({ context, signal: controller.signal, sinceUtc: startedUtc,
        timeoutMs: Math.min(probeTimeoutMs, remaining()), dispatched,
        onLatch: reason => { if (!error) error = reason; controller.abort(reason); },
      }), stopped]);
      if (error) throw error;
      if (controller.signal.aborted) throw controller.signal.reason;
      if (!remaining()) throw timeoutError();
      return result;
    }
    try {
      await probe();
      if (error) throw error;
      const outcome = Promise.resolve().then(() => {
        if (error || controller.signal.aborted) throw error || controller.signal.reason;
        if (!remaining()) throw timeoutError();
        dispatched = true;
        return call({ signal: controller.signal, remainingMs: remaining() });
      })
        .then(value => ({ value }), failure => ({ failure }));
      for (;;) {
        const event = await Promise.race([outcome, stopped, new Promise(resolve => {
          tickTimer = setTimeout(() => resolve({ tick: true }), Math.min(pollMs, remaining()));
        })]);
        clearTimeout(tickTimer);
        if (event.tick) { await probe(); continue; }
        await probe(); // A successful reply cannot hide an alert seen at completion.
        if (error || controller.signal.aborted) throw error || controller.signal.reason;
        if (Object.hasOwn(event, 'failure')) throw event.failure;
        return event.value;
      }
    } finally {
      clearTimeout(timer);
      clearTimeout(tickTimer);
      controller.abort();
      if (abort) signal.removeEventListener('abort', abort);
    }
  }

  return {
    check, run,
    status(context) { return context ? observations.get(keyOf(contextMetadata(context))) || { state: 'inactive' } : latest; },
  };
}

module.exports = { classifySecurityAlerts, createSecurityAlertObserver, SecurityAlertError, contextMetadata };
