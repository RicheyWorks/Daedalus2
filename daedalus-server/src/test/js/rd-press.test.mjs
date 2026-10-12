// node --test : rd-press (pressing state) + rd-audio-shim (raw on-chain audio opt-in at reduced volume)
import test from 'node:test';
import assert from 'node:assert/strict';
import * as P from '../../main/resources/static/rd-press.js';
import '../../main/resources/jukebox/rd-audio-shim.js';                       // classic script: defines globalThis.rdAudioShim (works as CJS or ESM)
const shim = globalThis.rdAudioShim;

const resp = (status, body, headers = {}) => ({ status, json: async () => body, headers: { get: (k) => headers[k] ?? null } });
function fakeFetch(seq) { const calls = []; let i = 0; const f = async (url) => { calls.push(url); const r = seq[Math.min(i++, seq.length - 1)]; if (r instanceof Error) throw r; return r; }; f.calls = calls; return f; }
const noSleep = () => { const s = []; const fn = async (ms) => { s.push(ms); }; fn.waits = s; return fn; };

test('202 pressing → polls on Retry-After → ready (rd-studio direct)', async () => {
  const f = fakeFetch([resp(202, { status: 'pressing', job: 'c4dc3728c92b5bfe', retry_after: 12, eta_s: 12 }, { 'Retry-After': '12' }),
    resp(202, { status: 'running', retry_after: 5 }, { 'Retry-After': '5' }), resp(200, { url: 'http://s/audio/t00007.mp3', key: 't00007' })]);
  const sleep = noSleep(), seen = [];
  const r = await P.pollArrange('/arrange?source=token:7', { fetch: f, sleep, onPressing: (e) => seen.push(e) });
  assert.equal(r.kind, 'ready'); assert.equal(r.url, 'http://s/audio/t00007.mp3');
  assert.deepEqual(sleep.waits, [12000, 5000]); assert.equal(seen[0].etaMs, 12000); assert.equal(seen[0].job, 'c4dc3728c92b5bfe');
  assert.equal(f.calls.length, 3);
});

test('jukebox wrapper: RENDERING with retryAfterMs, then READY', async () => {
  const f = fakeFetch([resp(200, { status: 'RENDERING', retryAfterMs: 3000, jobId: 'j1' }, { 'Retry-After': '3' }), resp(200, { status: 'READY', url: '/api/v1/jukebox/studio/audio/x.mp3' })]);
  const r = await P.pollArrange('/a', { fetch: f, sleep: noSleep() });
  assert.equal(r.kind, 'ready');
});

test('never falls back by itself: 404 unknown, 422 failed, 400 bad, network → unreachable, DOWN → unreachable', async () => {
  for (const [res, kind] of [[resp(404, { status: 'unknown_source' }), 'unknown'], [resp(422, { status: 'failed_qa' }), 'failed'],
    [resp(400, { error: 'x' }), 'bad'], [new TypeError('Failed to fetch'), 'unreachable'], [resp(200, { status: 'DOWN', note: 'down' }), 'unreachable'],
    [resp(200, { status: 'ORIGINAL', available: false, note: 'none' }), 'none'], [resp(500, {}), 'unreachable']]) {
    assert.equal((await P.pollArrange('/a', { fetch: fakeFetch([res]), sleep: noSleep() })).kind, kind);
  }
});

test('503 backs off on its Retry-After and keeps going; bounded by maxMs', async () => {
  const f = fakeFetch([resp(503, { status: 'queue_full' }, { 'Retry-After': '30' }), resp(200, { url: 'u' })]);
  const sleep = noSleep();
  assert.equal((await P.pollArrange('/a', { fetch: f, sleep })).kind, 'ready'); assert.deepEqual(sleep.waits, [30000]);
  let t = 0; const always = fakeFetch([resp(202, { retry_after: 10 }, { 'Retry-After': '10' })]);
  const r = await P.pollArrange('/a', { fetch: always, sleep: async (ms) => { t += ms; }, now: () => t, maxMs: 60000 });
  assert.equal(r.kind, 'timeout'); assert.ok(always.calls.length <= 7);
});

test('abort stops polling', async () => {
  const ac = new AbortController(); ac.abort();
  assert.equal((await P.pollArrange('/a', { fetch: fakeFetch([resp(200, { url: 'u' })]), signal: ac.signal })).kind, 'aborted');
});

test('retryMs clamps and defaults', () => {
  assert.equal(P.retryMs('12'), 12000); assert.equal(P.retryMs('0.1'), 1000); assert.equal(P.retryMs('999'), 60000);
  assert.equal(P.retryMs(null, { retry_after: 4 }), 4000); assert.equal(P.retryMs('abc', {}), 5000); assert.equal(P.retryMs(null, null), 5000);
});

test('progress eases toward the ETA and never claims done', () => {
  let prev = -1;
  for (let ms = 0; ms <= 120000; ms += 500) { const p = P.pressProgress(ms, 18000); assert.ok(p >= prev && p <= 0.97); prev = p; }
  assert.ok(P.pressProgress(18000, 18000) >= 0.89);
});

test('waveform + palette are deterministic per hash and bounded; groove is a shrinking spiral cut to progress', () => {
  const h = '0x' + 'ab12'.repeat(16);
  assert.deepEqual([...P.seededWave(h, 64)], [...P.seededWave(h, 64)]);
  assert.notDeepEqual([...P.seededWave(h, 64)], [...P.seededWave('0x' + 'cd34'.repeat(16), 64)]);
  assert.ok([...P.seededWave(h)].every((v) => v >= -1 && v <= 1));
  assert.deepEqual(P.paletteFrom(h), P.paletteFrom(h)); assert.equal(P.paletteFrom('nonsense').length, 5);
  assert.equal(P.groovePoints(0, null, { steps: 100 }).length, 1);
  const half = P.groovePoints(0.5, P.seededWave(h), { steps: 100 }), full = P.groovePoints(1, P.seededWave(h), { steps: 100 });
  assert.equal(half.length, 51); assert.equal(full.length, 101);
  const r = ([x, y]) => Math.hypot(x, y);
  assert.ok(r(full[0]) > r(full[100])); assert.ok(r(full[100]) > 0.39);
  assert.equal(P.groovePoints(7, null, { steps: 10 }).length, 11); assert.equal(P.groovePoints(NaN, null, { steps: 10 }).length, 1);
});

// ---------------------------------------------------------------- fake WebAudio
class Param { constructor(v = 0) { this.value = v; } }
class Node { constructor(ctx) { this.ctx = ctx; this.out = new Set(); } connect(n) { this.out.add(n); return n; } disconnect(n) { n ? this.out.delete(n) : this.out.clear(); } }
class Gain extends Node { constructor(c) { super(c); this.gain = new Param(1); } }
class Comp extends Node { constructor(c) { super(c); for (const k of ['threshold', 'knee', 'ratio', 'attack', 'release']) this[k] = new Param(0); } }
class Analyser extends Node { constructor(c) { super(c); this.fftSize = 2048; } getByteTimeDomainData(a) { a.fill(128); } }
class FakeBase { constructor() { this._dest = new Node(this); } createGain() { return new Gain(this); } createDynamicsCompressor() { return new Comp(this); } createAnalyser() { return new Analyser(this); } }
Object.defineProperty(FakeBase.prototype, 'destination', { configurable: true, get() { return this._dest; } });
class FakeAC extends FakeBase {}
class FakeOffline extends FakeBase {}
const reaches = (from, to, via) => { const seen = new Set(); let viaHit = false, ok = false; (function w(n, v) { if (n === to) { ok = true; if (v) viaHit = true; return; } if (seen.has(n)) return; seen.add(n); for (const m of n.out) w(m, v || via(n)); })(from, false); return ok && viaHit; };

test('safe chain: limiter fixed, always between input and speakers, guard restores tampering', () => {
  const ctx = new FakeAC(), c = P.createSafeChain(ctx, { guardMs: 0 });
  assert.equal(c.limiter.threshold.value, -10); assert.equal(c.limiter.ratio.value, 20); assert.equal(c.ceiling.gain.value, P.CEILING);
  assert.ok(c.check()); assert.ok(reaches(c.input, ctx.destination, (n) => n === c.limiter));
  c.limiter.threshold.value = 0; c.limiter.ratio.value = 1; c.gain.gain.value = 5; c.ceiling.gain.value = 3;
  assert.equal(c.check(), false); c.guard();
  assert.equal(c.limiter.threshold.value, -10); assert.equal(c.limiter.ratio.value, 20); assert.ok(c.gain.gain.value <= 1); assert.equal(c.ceiling.gain.value, P.CEILING);
  assert.ok(c.check());
  const src = new Node(ctx), off = c.connect(src); assert.ok(reaches(src, ctx.destination, (n) => n === c.limiter)); off(); assert.equal(src.out.size, 0);
  assert.ok(Object.isFrozen(P.LIMITER));
});

test('safe chain guard runs on a timer (not frames)', async () => {
  const c = P.createSafeChain(new FakeAC(), { guardMs: 20 });
  c.limiter.ratio.value = 1; await new Promise((r) => setTimeout(r, 60)); assert.equal(c.limiter.ratio.value, 20); c.destroy();
});

// ---------------------------------------------------------------- raw on-chain audio shim
function fakeWin() {
  class B extends FakeBase {} class AC extends B {} class Off extends B {}
  Object.defineProperty(B.prototype, 'destination', { configurable: true, get() { return this._dest; } });
  class Media { constructor() { this._v = 1; this.muted = false; } play() { return 'played'; } }
  Object.defineProperty(Media.prototype, 'volume', { configurable: true, get() { return this._v; }, set(v) { this._v = v; } });
  const timers = []; return { BaseAudioContext: B, AudioContext: AC, OfflineAudioContext: Off, HTMLMediaElement: Media, setInterval: (fn) => timers.push(fn), timers };
}

test('shim: raw on-chain WebAudio goes through gain(0.35) → limiter → ceiling; offline renders untouched', () => {
  const w = fakeWin(); shim(w, P.RAW_VOLUME);
  const ctx = new w.AudioContext(), d = ctx.destination;
  assert.notEqual(d, ctx._dest); assert.equal(d.gain.value, 0.35);
  const lim = [...d.out][0]; assert.equal(lim.threshold.value, -10); assert.equal(lim.ratio.value, 20);
  assert.ok(reaches(d, ctx._dest, (n) => n === lim));
  assert.equal(ctx.destination, d);                                         // one chain per context
  const off = new w.OfflineAudioContext(); assert.equal(off.destination, off._dest);
  d.gain.value = 1; lim.ratio.value = 1; w.timers.forEach((f) => f());       // the token turns itself up: put back
  assert.equal(d.gain.value, 0.35); assert.equal(lim.ratio.value, 20);
});

test('shim: media elements are held at or below the volume; 0 = silent until opt-in', () => {
  const w = fakeWin(); shim(w, 0);
  const a = new w.HTMLMediaElement(); a.volume = 1; assert.equal(a.volume, 0); a.play(); assert.equal(a.muted, true);
  assert.equal(new w.AudioContext().destination.gain.value, 0);
  const w2 = fakeWin(); shim(w2, P.RAW_VOLUME); const b = new w2.HTMLMediaElement(); b.volume = 0.9; assert.equal(b.volume, 0.35);
  assert.equal(shim(fakeWin(), 'loud'), 0); assert.equal(shim(fakeWin(), 9), 1);
});

test('press: draws with reduced motion (no spin, redraw on change only) and with motion', () => {
  const ops = []; const g = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (typeof k === 'string' && ['canvas'].includes(k) ? undefined : (...a) => { ops.push(k); return { addColorStop() {} }; })), set: (t, k, v) => { t[k] = v; return true; } });
  const canvas = { width: 200, height: 200, getContext: () => g };
  const p = P.createPress(canvas, { seed: '0x' + '11'.repeat(32), reducedMotion: true });
  const n0 = ops.length; p.set({ phase: 'pressing', progress: 0.5 }); assert.ok(ops.length > n0);
  assert.deepEqual(p.state, { phase: 'pressing', progress: 0.5, reduced: true, spinning: false });
  p.set({ phase: 'playing', analyser: new Analyser() }); assert.equal(p.state.spinning, false); p.destroy();
  const q = P.createPress(canvas, { seed: 'x', reducedMotion: false }); q.set({ phase: 'playing' }); assert.equal(q.state.spinning, true); q.destroy();
});
