// SPDX-License-Identifier: MIT
'use strict';

const { performance } = require('node:perf_hooks');
const { createHash } = require('node:crypto');
const path = require('node:path');
const METHODS = ['acquireLease', 'inspect', 'preserve', 'closeWithoutSending', 'resolveRestore',
  'launch', 'readback', 'reconcile', 'releaseLease'];
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const session = value => value && Number.isSafeInteger(value.pid) && value.pid > 0 && text(value.start_time);
const sameSession = (left, right) => session(left) && session(right) && left.pid === right.pid && left.start_time === right.start_time;
const copy = value => JSON.parse(JSON.stringify(value));

class RecoveryBlocked extends Error {
  constructor(reason, state = 'blocked') { super(reason); this.reason = reason; this.state = state; }
}
function requireEvidence(condition, reason) { if (!condition) throw new RecoveryBlocked(reason); }
function unique(values, key) { return new Set(values.map(value => value[key])).size === values.length; }

/** Pure orchestration seam. Adapters perform and verify real actions; no Windows adapter is supplied.
 * acquireLease must atomically hold other callers; releaseLease must be atomic after verified readiness.
 * Callback cancellation stops waiting, not effects already begun. No command is automatically replayed.
 */
async function runRecovery({ project, expectedMap, crashedSession, adapter, timeoutMs, maxLaunchAttempts = 1,
  recoveryDecision } = {}) {
  let stage = 'configuration';
  let held = false;
  let leaseId;
  let releaseStarted = false;
  let decisionContext;
  let attempts = 0;
  const result = (state, details = {}) => ({ ok: state === 'ready', state, stage, held, project, leaseId,
    launchAttempts: attempts, details });
  if (!text(project) || !text(expectedMap) || !/\.uproject$/i.test(project) ||
      !(path.win32.isAbsolute(project) || path.posix.isAbsolute(project)) || !session(crashedSession) ||
      !Number.isFinite(timeoutMs) || timeoutMs <= 0 || maxLaunchAttempts !== 1) {
    return result('blocked', { reason: 'invalid_configuration' });
  }
  const missing = METHODS.filter(name => typeof adapter?.[name] !== 'function');
  if (missing.length) return result('blocked', { reason: 'missing_adapters', missing });
  try {
    crashedSession = copy(crashedSession);
    recoveryDecision = recoveryDecision === undefined ? undefined : copy(recoveryDecision);
  } catch (_) { return result('blocked', { reason: 'invalid_configuration' }); }
  const deadline = performance.now() + timeoutMs;
  const controller = new AbortController();
  let rejectDeadline;
  const expired = new Promise((_, reject) => { rejectDeadline = reject; });
  expired.catch(() => {});
  const timeout = () => new RecoveryBlocked('overall_deadline', 'timeout');
  const timer = setTimeout(() => { const error = timeout(); controller.abort(error); rejectDeadline(error); }, timeoutMs);
  const remaining = () => Math.max(0, deadline - performance.now());
  async function invoke(name, args = {}) {
    stage = name;
    if (!remaining()) throw timeout();
    const value = await Promise.race([Promise.resolve().then(() => adapter[name]({
      ...args, project, expectedMap, crashedSession, leaseId, signal: controller.signal, remainingMs: remaining()
    })), expired]);
    if (!remaining()) throw timeout();
    return copy(value);
  }
  function inspectEvidence(value) {
    requireEvidence(value?.project === project && sameSession(value.crashedSession, crashedSession), 'inspection_identity');
    requireEvidence(value.inventoryComplete === true && value.files &&
      ['crash', 'autosaves', 'authoritative'].every(group => Array.isArray(value.files[group])), 'incomplete_preservation_inventory');
    requireEvidence(value.files.crash.length > 0, 'missing_crash_artifacts');
    for (const group of ['crash', 'autosaves', 'authoritative']) {
      requireEvidence(unique(value.files[group], 'id') && value.files[group].every(file => text(file?.id) && hash(file.sha256)), 'invalid_file_inventory');
    }
    requireEvidence(value.session === null || (session(value.session) && value.session.project === project && value.session.running === true), 'unrelated_or_invalid_session');
    requireEvidence(Array.isArray(value.uncertainCommandIds) && value.uncertainCommandIds.every(text) &&
      new Set(value.uncertainCommandIds).size === value.uncertainCommandIds.length, 'invalid_uncertain_commands');
    return value;
  }
  function reporterEvidence(reporter) {
    const name = path.win32.basename(project).replace(/\.uproject$/i, '');
    requireEvidence(session(reporter) && (text(reporter.hwnd) || (Number.isSafeInteger(reporter.hwnd) && reporter.hwnd > 0)) && reporter.project === project &&
      reporter.crashedPid === crashedSession.pid && reporter.crashedStartTime === crashedSession.start_time &&
      reporter.title === `${name} Crash Reporter` && hash(reporter.contentHash) &&
      reporter.closeAction === 'CloseWithoutSending' && reporter.sendAllowed === false, 'unrecognized_reporter');
  }
  function preservationEvidence(receipt, files) {
    requireEvidence(receipt?.project === project && receipt.complete === true && receipt.durable === true && receipt.files, 'preservation_unconfirmed');
    let count = 0;
    for (const group of ['crash', 'autosaves', 'authoritative']) {
      const actual = receipt.files[group];
      requireEvidence(Array.isArray(actual) && unique(actual, 'id') && actual.length === files[group].length, 'preservation_count');
      count += actual.length;
      for (const source of files[group]) {
        const backup = actual.find(file => file.id === source.id);
        requireEvidence(backup && backup.sourceHash === source.sha256 && backup.backupHash === source.sha256, 'preservation_hash');
      }
    }
    requireEvidence(receipt.count === count, 'preservation_count');
  }
  function unchangedFiles(current, preserved) {
    for (const group of ['crash', 'autosaves', 'authoritative']) {
      requireEvidence(current[group].length === preserved[group].length && current[group].every(file =>
        preserved[group].some(original => original.id === file.id && original.sha256 === file.sha256)), 'preserved_inventory_changed');
    }
  }
  function unchangedCommands(current, original) {
    requireEvidence(current.length === original.length && current.every(id => original.includes(id)), 'uncertain_command_inventory_changed');
  }
  function readinessEvidence(readback, running) {
    requireEvidence(readback?.project === project && readback.session?.project === project && sameSession(readback.session, running) &&
      sameSession(readback.process, running) && readback.process.alive === true &&
      sameSession(readback.connector, running) && readback.connector.project === project && readback.connector.ready === true &&
      sameSession(readback.map, running) && readback.map.project === project && readback.map.name === expectedMap &&
      readback.map.loaded === true && readback.map.saved === true && readback.map.noPIE === true &&
      readback.map.noModal === true && readback.map.confirmed === true, 'readiness_unconfirmed');
  }
  function decisionEvidence(restore, files) {
    stage = 'restore_decision';
    const decision = recoveryDecision;
    requireEvidence(restore?.project === project && text(restore.id) && hash(restore.contentHash) &&
      Array.isArray(restore.candidates) && restore.candidates.length > 0 && unique(restore.candidates, 'id'), 'invalid_restore_evidence');
    for (const candidate of restore.candidates) {
      requireEvidence(text(candidate.id) && hash(candidate.sha256) && text(candidate.targetId) && hash(candidate.targetHash), 'invalid_restore_evidence');
      requireEvidence(files.autosaves.some(file => file.id === candidate.id && file.sha256 === candidate.sha256) &&
        files.authoritative.some(file => file.id === candidate.targetId && file.sha256 === candidate.targetHash), 'restore_not_preserved');
    }
    decisionContext = { restoreId: restore.id, contentHash: restore.contentHash,
      candidates: restore.candidates.map(candidate => ({ candidateId: candidate.id, candidateHash: candidate.sha256,
        targetId: candidate.targetId, targetHash: candidate.targetHash })), allowedActions: ['restore', 'keep_authoritative'] };
    if (!decision || decision.ownerAgreed !== true) throw new RecoveryBlocked('owner_restore_decision_required', 'recovery_decision_required');
    requireEvidence(decision.project === project && decision.restoreId === restore.id && decision.contentHash === restore.contentHash &&
      Array.isArray(decision.plan) && unique(decision.plan, 'candidateId') && unique(decision.plan, 'targetId') && decision.plan.length === restore.candidates.length &&
      hash(decision.planHash) && decision.planHash === createHash('sha256').update(JSON.stringify(decision.plan)).digest('hex'), 'restore_plan_identity');
    for (const candidate of restore.candidates) {
      const choice = decision.plan.find(entry => entry.candidateId === candidate.id);
      requireEvidence(text(candidate.id) && hash(candidate.sha256) && text(candidate.targetId) && hash(candidate.targetHash) && choice &&
        choice.candidateHash === candidate.sha256 && choice.targetId === candidate.targetId && choice.targetHash === candidate.targetHash &&
        ['restore', 'keep_authoritative'].includes(choice.action), 'restore_plan_identity');
    }
    return decision;
  }
  try {
    held = 'unconfirmed';
    const lease = await invoke('acquireLease');
    requireEvidence(lease?.project === project && text(lease.leaseId) && lease.exclusive === true && lease.callersHeld === true, 'exclusive_hold_unconfirmed');
    leaseId = lease.leaseId;
    held = true;
    let current = inspectEvidence(await invoke('inspect'));
    const files = copy(current.files);
    const uncertainIds = [...current.uncertainCommandIds];
    if (current.reporter !== null) reporterEvidence(current.reporter);
    const preserved = await invoke('preserve', { files });
    preservationEvidence(preserved, files);
    if (current.reporter !== null) {
      const original = current.reporter;
      current = inspectEvidence(await invoke('inspect'));
      unchangedFiles(current.files, files);
      unchangedCommands(current.uncertainCommandIds, uncertainIds);
      reporterEvidence(current.reporter);
      requireEvidence(sameSession(original, current.reporter) && original.hwnd === current.reporter.hwnd &&
        original.contentHash === current.reporter.contentHash, 'reporter_changed');
      const closed = await invoke('closeWithoutSending', { reporter: current.reporter, action: 'CloseWithoutSending' });
      requireEvidence(closed?.project === project && closed.reporterId === original.hwnd && closed.contentHash === original.contentHash &&
        closed.action === 'CloseWithoutSending' && closed.closed === true && closed.sent === false, 'close_without_sending_unconfirmed');
    }
    current = inspectEvidence(await invoke('inspect'));
    unchangedFiles(current.files, files);
    unchangedCommands(current.uncertainCommandIds, uncertainIds);
    requireEvidence(current.reporter === null, 'reporter_still_present');
    let expectedFiles = files;
    if (current.restore !== null) {
      const decision = decisionEvidence(current.restore, files);
      const resolved = await invoke('resolveRestore', { restore: current.restore, decision });
      requireEvidence(resolved?.project === project && resolved.restoreId === decision.restoreId &&
        resolved.contentHash === decision.contentHash && resolved.planHash === decision.planHash && resolved.resolved === true, 'restore_unconfirmed');
      expectedFiles = copy(files);
      for (const choice of decision.plan) {
        if (choice.action === 'restore') {
          expectedFiles.authoritative.find(file => file.id === choice.targetId).sha256 = choice.candidateHash;
        }
      }
    }
    current = inspectEvidence(await invoke('inspect'));
    unchangedFiles(current.files, expectedFiles);
    unchangedCommands(current.uncertainCommandIds, uncertainIds);
    requireEvidence(current.reporter === null && current.restore === null, 'unresolved_dialog');
    let running = current.session;
    if (running === null) {
      requireEvidence(current.launcher?.project === project && text(current.launcher.id) && current.launcher.existing === true, 'existing_launcher_required');
      attempts++;
      const launched = await invoke('launch', { launcher: current.launcher, attempt: attempts });
      requireEvidence(launched?.project === project && launched.launcherId === current.launcher.id && launched.attempt === attempts &&
        session(launched.session) && launched.session.project === project && launched.session.running === true, 'launch_unconfirmed');
      running = launched.session;
    }
    let readback = await invoke('readback', { session: running });
    readinessEvidence(readback, running);
    const reconciled = await invoke('reconcile', { commandIds: uncertainIds, session: running });
    requireEvidence(reconciled?.project === project && reconciled.replayed === 0 && Array.isArray(reconciled.commands) &&
      unique(reconciled.commands, 'id') && reconciled.commands.length === uncertainIds.length &&
      uncertainIds.every(id => reconciled.commands.some(command => command.id === id && ['committed', 'not_committed'].includes(command.status))), 'uncertain_commands_unresolved');
    readback = await invoke('readback', { session: running });
    readinessEvidence(readback, running);
    releaseStarted = true;
    const released = await invoke('releaseLease', { session: running, readback, reconciled });
    requireEvidence(released?.project === project && released.leaseId === leaseId && released.released === true &&
      released.callersReleased === true, 'release_unconfirmed');
    held = false;
    stage = 'ready';
    return result('ready', { preserved, readback, reconciled });
  } catch (error) {
    controller.abort(error);
    if (releaseStarted) held = 'unconfirmed';
    return result(error instanceof RecoveryBlocked ? error.state : 'blocked', {
      reason: error instanceof RecoveryBlocked ? error.reason : 'adapter_failed', error: String(error?.message || error),
      ...(error?.state === 'recovery_decision_required' ? { decision: decisionContext } : {})
    });
  } finally { clearTimeout(timer); }
}

module.exports = { runRecovery };
