// SPDX-License-Identifier: MIT
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { runRecovery } = require('../extension/server/editor-recovery.js');

const PROJECT = 'C:\\Projects\\DaedalusRealm\\DaedalusRealm.uproject';
const CRASHED = { pid: 123, start_time: 'old' };
const SESSION = { pid: 124, start_time: 'new', project: PROJECT, running: true };
const HASH = character => character.repeat(64);
const copy = value => JSON.parse(JSON.stringify(value));
const never = () => new Promise(() => {});

function fixture({ healthy = false, restore = false, uncertain = [] } = {}) {
  const calls = [];
  const requests = [];
  const scene = {
    project: PROJECT, crashedSession: copy(CRASHED), inventoryComplete: true,
    files: {
      crash: [{ id: 'crash.log', sha256: HASH('a') }],
      autosaves: [{ id: 'autosave-main', sha256: HASH('b') }],
      authoritative: [{ id: 'main-map', sha256: HASH('c') }],
    },
    session: healthy ? copy(SESSION) : null,
    reporter: healthy ? null : {
      pid: 900, start_time: 'reporter-start', hwnd: '900-window', project: PROJECT,
      crashedPid: CRASHED.pid, crashedStartTime: CRASHED.start_time,
      title: 'DaedalusRealm Crash Reporter', contentHash: HASH('d'),
      closeAction: 'CloseWithoutSending', sendAllowed: false,
    },
    restore: restore ? {
      id: 'restore-main', project: PROJECT, contentHash: HASH('e'),
      candidates: [{ id: 'autosave-main', sha256: HASH('b'), targetId: 'main-map', targetHash: HASH('c') }],
    } : null,
    launcher: { id: 'existing-launcher', project: PROJECT, existing: true },
    uncertainCommandIds: [...uncertain],
  };
  const plan = [{ candidateId: 'autosave-main', candidateHash: HASH('b'), targetId: 'main-map', targetHash: HASH('c'), action: 'restore' }];
  const decision = {
    project: PROJECT, restoreId: 'restore-main', contentHash: HASH('e'),
    ownerAgreed: true, plan,
    planHash: createHash('sha256').update(JSON.stringify(plan)).digest('hex'),
  };
  const handlers = {
    acquireLease: () => ({ leaseId: 'owner', project: PROJECT, exclusive: true, callersHeld: true }),
    inspect: () => copy(scene),
    preserve: () => ({
      project: PROJECT, complete: true, durable: true, count: 3,
      files: Object.fromEntries(Object.entries(scene.files).map(([kind, files]) => [kind,
        files.map(file => ({ id: file.id, sourceHash: file.sha256, backupHash: file.sha256 })),
      ])),
    }),
    closeWithoutSending: () => {
      const reporter = scene.reporter;
      scene.reporter = null;
      return { project: PROJECT, reporterId: reporter.hwnd, contentHash: reporter.contentHash, action: 'CloseWithoutSending', closed: true, sent: false };
    },
    resolveRestore: () => {
      const dialog = scene.restore;
      for (const choice of decision.plan) {
        if (choice.action === 'restore') {
          scene.files.authoritative.find(file => file.id === choice.targetId).sha256 = choice.candidateHash;
        }
      }
      scene.restore = null;
      return { project: PROJECT, restoreId: dialog.id, contentHash: dialog.contentHash, resolved: true, planHash: decision.planHash };
    },
    launch: () => {
      scene.session = copy(SESSION);
      return { project: PROJECT, launcherId: 'existing-launcher', attempt: 1, session: copy(SESSION) };
    },
    readback: () => ({
      project: PROJECT, session: copy(SESSION),
      process: { pid: SESSION.pid, start_time: SESSION.start_time, alive: true },
      connector: { pid: SESSION.pid, start_time: SESSION.start_time, project: PROJECT, ready: true },
      map: { pid: SESSION.pid, start_time: SESSION.start_time, project: PROJECT, name: '/Game/Maps/Main', loaded: true, saved: true, noPIE: true, noModal: true, confirmed: true },
    }),
    reconcile: () => ({ project: PROJECT, replayed: 0, commands: uncertain.map(id => ({ id, status: 'not_committed' })) }),
    releaseLease: () => ({ project: PROJECT, leaseId: 'owner', released: true, callersReleased: true }),
  };
  const adapter = Object.fromEntries(Object.keys(handlers).map(name => [name, async request => {
    calls.push(name);
    requests.push({ name, request });
    return handlers[name](request);
  }]));
  return {
    calls, requests, scene, handlers, adapter, decision,
    run: extra => runRecovery({ project: PROJECT, expectedMap: '/Game/Maps/Main', crashedSession: copy(CRASHED), adapter, timeoutMs: 1000, maxLaunchAttempts: 1, ...(restore ? { recoveryDecision: decision } : {}), ...extra }),
  };
}

function heldFailure(result, fixture) {
  assert.equal(result.ok, false);
  assert.equal(result.held, true);
  assert.equal(fixture.calls.includes('releaseLease'), false);
}

test('preserves evidence before closing without sending and releases only after readback and reconciliation', async () => {
  const f = fixture();
  const result = await f.run();
  assert.equal(result.ok, true);
  assert.equal(result.state, 'ready');
  assert.equal(result.stage, 'ready');
  assert.equal(result.held, false);
  assert.deepEqual(f.calls, ['acquireLease', 'inspect', 'preserve', 'inspect', 'closeWithoutSending', 'inspect', 'inspect', 'launch', 'readback', 'reconcile', 'readback', 'releaseLease']);
  for (const { name, request } of f.requests) {
    assert.equal(request.project, PROJECT);
    assert.deepEqual(request.crashedSession, CRASHED);
    assert.ok(request.signal instanceof AbortSignal);
    assert.ok(request.remainingMs > 0 && request.remainingMs <= 1000);
    if (name !== 'acquireLease') assert.equal(request.leaseId, 'owner');
  }
});

test('healthy existing session skips reporter closure, restoration and launch', async () => {
  const f = fixture({ healthy: true });
  assert.equal((await f.run()).ok, true);
  assert.deepEqual(f.calls, ['acquireLease', 'inspect', 'preserve', 'inspect', 'inspect', 'readback', 'reconcile', 'readback', 'releaseLease']);
});

test('a complete owner-approved restore plan is bound to preserved targets and refreshed dialog evidence', async () => {
  const f = fixture({ restore: true });
  assert.equal((await f.run()).ok, true);
  assert.equal(f.scene.files.authoritative[0].sha256, HASH('b'));
  assert.deepEqual(f.calls, ['acquireLease', 'inspect', 'preserve', 'inspect', 'closeWithoutSending', 'inspect', 'resolveRestore', 'inspect', 'launch', 'readback', 'reconcile', 'readback', 'releaseLease']);
});

test('keep_authoritative preserves the prior authoritative hash when resolving restoration', async () => {
  const f = fixture({ restore: true });
  f.decision.plan[0].action = 'keep_authoritative';
  f.decision.planHash = createHash('sha256').update(JSON.stringify(f.decision.plan)).digest('hex');
  assert.equal((await f.run()).ok, true);
  assert.equal(f.scene.files.authoritative[0].sha256, HASH('c'));
});

test('an unapproved post-restore target hash blocks launch and release', async () => {
  const f = fixture({ restore: true });
  const original = f.handlers.resolveRestore;
  f.handlers.resolveRestore = () => {
    const receipt = original();
    f.scene.files.authoritative[0].sha256 = HASH('0');
    return receipt;
  };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('launch'), false);
});

test('missing required adapter blocks before a lease or side effects', async () => {
  const f = fixture();
  delete f.adapter.preserve;
  const result = await f.run();
  assert.equal(result.ok, false);
  assert.equal(result.state, 'blocked');
  assert.equal(result.details.reason, 'missing_adapters');
  assert.equal(result.held, false);
  assert.deepEqual(f.calls, []);
});

test('missing or blank expected map blocks before acquiring a lease', async () => {
  for (const expectedMap of [undefined, '', '  ', 42]) {
    const f = fixture();
    const result = await f.run({ expectedMap });
    assert.equal(result.ok, false);
    assert.equal(result.state, 'blocked');
    assert.equal(result.held, false);
    assert.deepEqual(f.calls, []);
  }
});

test('incomplete or changed backup receipts prevent closure and launch', async () => {
  for (const mutate of [receipt => { receipt.files.authoritative = []; }, receipt => { receipt.files.autosaves[0].backupHash = HASH('0'); }, receipt => { receipt.durable = false; }]) {
    const f = fixture();
    const original = f.handlers.preserve;
    f.handlers.preserve = () => { const receipt = original(); mutate(receipt); return receipt; };
    heldFailure(await f.run(), f);
    assert.equal(f.calls.includes('closeWithoutSending'), false);
    assert.equal(f.calls.includes('launch'), false);
  }
});

test('incomplete inventory or evidence associated with another project or crash cannot cause closure', async () => {
  for (const mutate of [scene => { scene.inventoryComplete = false; }, scene => { scene.project = 'C:\\Other\\Other.uproject'; }, scene => { scene.reporter.crashedStartTime = 'another-crash'; }, scene => { scene.reporter.sendAllowed = true; }]) {
    const f = fixture();
    mutate(f.scene);
    heldFailure(await f.run(), f);
    assert.equal(f.calls.includes('preserve'), false);
    assert.equal(f.calls.includes('closeWithoutSending'), false);
    assert.equal(f.calls.includes('launch'), false);
  }
});

test('invalid numeric or object reporter window handles block before preservation or closure', async () => {
  for (const hwnd of [-1, 0, 1.5, {}]) {
    const f = fixture();
    f.scene.reporter.hwnd = hwnd;
    heldFailure(await f.run(), f);
    assert.equal(f.calls.includes('preserve'), false);
    assert.equal(f.calls.includes('closeWithoutSending'), false);
    assert.equal(f.calls.includes('launch'), false);
  }
});

test('an adapter throwing null after acquisition returns a blocked result with callers held', async () => {
  const f = fixture();
  f.handlers.preserve = () => { throw null; };
  const result = await f.run();
  heldFailure(result, f);
  assert.equal(result.state, 'blocked');
  assert.equal(f.calls.includes('closeWithoutSending'), false);
  assert.equal(f.calls.includes('launch'), false);
});

test('reporter identity changing after preservation blocks closure', async () => {
  const f = fixture();
  let inspections = 0;
  f.handlers.inspect = () => {
    const scene = copy(f.scene);
    if (++inspections === 2) scene.reporter.start_time = 'replacement-reporter';
    return scene;
  };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('closeWithoutSending'), false);
  assert.equal(f.calls.includes('launch'), false);
});

test('a close receipt claiming it sent a report keeps callers held', async () => {
  const f = fixture();
  const original = f.handlers.closeWithoutSending;
  f.handlers.closeWithoutSending = () => ({ ...original(), sent: true });
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('launch'), false);
});

test('ambiguous restoration requires a decision and never launches', async () => {
  const f = fixture({ restore: true });
  const result = await f.run({ recoveryDecision: undefined });
  heldFailure(result, f);
  assert.equal(result.state, 'recovery_decision_required');
  assert.equal(result.stage, 'restore_decision');
  assert.deepEqual(result.details.decision, {
    restoreId: 'restore-main', contentHash: HASH('e'),
    candidates: [{ candidateId: 'autosave-main', candidateHash: HASH('b'), targetId: 'main-map', targetHash: HASH('c') }],
    allowedActions: ['restore', 'keep_authoritative'],
  });
  assert.equal(f.calls.includes('resolveRestore'), false);
  assert.equal(f.calls.includes('launch'), false);
  assert.equal(f.scene.files.authoritative[0].sha256, HASH('c'));
  assert.equal(f.scene.files.autosaves[0].sha256, HASH('b'));
});

test('a plan with an invalid hash or an unpreserved target is blocked', async () => {
  for (const mutate of [decision => { decision.planHash = HASH('f'); }, decision => {
    decision.plan[0].targetHash = HASH('0');
    decision.planHash = createHash('sha256').update(JSON.stringify(decision.plan)).digest('hex');
  }, decision => { decision.ownerAgreed = false; }]) {
    const f = fixture({ restore: true });
    mutate(f.decision);
    heldFailure(await f.run(), f);
    assert.equal(f.calls.includes('resolveRestore'), false);
    assert.equal(f.calls.includes('launch'), false);
  }
});

test('a changed restore dialog hash blocks applying the approved plan', async () => {
  const f = fixture({ restore: true });
  let inspections = 0;
  f.handlers.inspect = () => {
    const scene = copy(f.scene);
    if (++inspections === 3) scene.restore.contentHash = HASH('0');
    return scene;
  };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('resolveRestore'), false);
  assert.equal(f.calls.includes('launch'), false);
});

test('fresh authoritative inventory drift cannot apply a plan against the older preserved target', async () => {
  const f = fixture({ restore: true });
  let inspections = 0;
  f.handlers.inspect = () => {
    const scene = copy(f.scene);
    if (++inspections > 1) scene.files.authoritative[0].sha256 = HASH('0');
    return scene;
  };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('resolveRestore'), false);
  assert.equal(f.calls.includes('launch'), false);
});

test('new uncertain command evidence cannot be silently omitted from reconciliation', async () => {
  const f = fixture({ uncertain: ['command-a'] });
  let inspections = 0;
  f.handlers.inspect = () => {
    const scene = copy(f.scene);
    if (++inspections > 1) scene.uncertainCommandIds.push('command-b');
    return scene;
  };
  heldFailure(await f.run(), f);
});

test('a hung adapter times out, aborts its signal and retains the lease', async () => {
  const f = fixture();
  f.handlers.preserve = never;
  const started = Date.now();
  const result = await f.run({ timeoutMs: 30 });
  heldFailure(result, f);
  assert.equal(result.state, 'timeout');
  assert.ok(Date.now() - started < 1000);
  assert.equal(f.requests.find(row => row.name === 'preserve').request.signal.aborted, true);
  assert.equal(f.calls.includes('closeWithoutSending'), false);
});

test('a hung acquisition reports an unconfirmed hold and never proceeds to inspection', async () => {
  const f = fixture();
  f.handlers.acquireLease = never;
  const result = await f.run({ timeoutMs: 30 });
  assert.equal(result.ok, false);
  assert.equal(result.state, 'timeout');
  assert.equal(result.held, 'unconfirmed');
  assert.deepEqual(f.calls, ['acquireLease']);
  assert.equal(f.requests[0].request.signal.aborted, true);
});

test('invalid lease receipts cannot claim no hold or proceed to side effects', async () => {
  for (const mutate of [receipt => { receipt.exclusive = false; }, receipt => { receipt.project = 'C:\\Other\\Other.uproject'; }, receipt => { receipt.leaseId = ''; }]) {
    const f = fixture();
    const original = f.handlers.acquireLease;
    f.handlers.acquireLease = () => { const receipt = original(); mutate(receipt); return receipt; };
    const result = await f.run();
    assert.equal(result.ok, false);
    assert.equal(result.held, 'unconfirmed');
    assert.deepEqual(f.calls, ['acquireLease']);
  }
});

test('failed launch has exactly one attempt and no uncertain retry', async () => {
  const f = fixture();
  f.handlers.launch = () => { throw new Error('launch acknowledgement lost'); };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.filter(name => name === 'launch').length, 1);
  assert.equal(f.calls.includes('readback'), false);
});

test('a readback from a different process generation cannot release callers', async () => {
  const f = fixture();
  const original = f.handlers.readback;
  f.handlers.readback = () => { const receipt = original(); receipt.connector.start_time = 'stale'; return receipt; };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('reconcile'), false);
});

test('a different loaded map cannot satisfy the expected map readiness gate', async () => {
  const f = fixture();
  const original = f.handlers.readback;
  f.handlers.readback = () => { const receipt = original(); receipt.map.name = '/Game/Maps/Other'; return receipt; };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.includes('reconcile'), false);
});

test('map readiness requires confirmed saved map with no PIE or modal', async () => {
  for (const field of ['loaded', 'saved', 'noPIE', 'noModal', 'confirmed']) {
    const f = fixture();
    const original = f.handlers.readback;
    f.handlers.readback = () => { const receipt = original(); receipt.map[field] = false; return receipt; };
    heldFailure(await f.run(), f);
    assert.equal(f.calls.includes('reconcile'), false);
  }
});

test('late editor failure after reconciliation prevents releasing held callers', async () => {
  const f = fixture();
  const original = f.handlers.readback;
  let readbacks = 0;
  f.handlers.readback = () => {
    const receipt = original();
    if (++readbacks === 2) receipt.process.alive = false;
    return receipt;
  };
  heldFailure(await f.run(), f);
  assert.equal(f.calls.filter(name => name === 'readback').length, 2);
  assert.equal(f.calls.filter(name => name === 'reconcile').length, 1);
});

test('uncertain command outcomes are reconciled without executing them again', async () => {
  const f = fixture({ uncertain: ['command-a', 'command-b'] });
  f.adapter.replay = () => { throw new Error('commands must not be replayed'); };
  assert.equal((await f.run()).ok, true);
  assert.equal(f.calls.filter(name => name === 'reconcile').length, 1);
});

test('missing command outcome or any replay claim prevents lease release', async () => {
  for (const mutate of [receipt => { receipt.commands.pop(); }, receipt => { receipt.replayed = 1; }, receipt => { receipt.commands[0].status = 'unknown'; }]) {
    const f = fixture({ uncertain: ['command-a', 'command-b'] });
    const original = f.handlers.reconcile;
    f.handlers.reconcile = () => { const receipt = original(); mutate(receipt); return receipt; };
    heldFailure(await f.run(), f);
  }
});

test('uncertain release acknowledgement is reported without claiming callers were released', async () => {
  const f = fixture();
  f.handlers.releaseLease = () => { throw new Error('release acknowledgement lost'); };
  const result = await f.run();
  assert.equal(result.ok, false);
  assert.equal(result.held, 'unconfirmed');
  assert.equal(f.calls.filter(name => name === 'releaseLease').length, 1);
});
