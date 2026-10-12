// SPDX-License-Identifier: MIT
// rd-press: the "pressing your record" state, shared by the Daedalus jukebox and the R/D/S web page.
// Pure ES module, no dependencies. rd-studio r4 (engine frozen): a cache miss answers 202 {status:"pressing", eta_s,
// retry_after} + Retry-After and renders at priority (15-20 s). We show the token's coat (or palette) being pressed into
// the label and a groove cut from the song's waveform, then play the render through an always-on limiter.
// The raw on-chain HTML audio is never a fallback: only an explicit opt-in, at RAW_VOLUME, through its own limiter.

export const LIMITER = Object.freeze({ threshold: -10, knee: 0, ratio: 20, attack: 0.001, release: 0.12 });
export const CEILING = 0.89;
export const RAW_VOLUME = 0.35;
export const PRESS_MAX_MS = 120_000;
const RPM = 100 / 3, TAU = Math.PI * 2;

/** Retry-After (header seconds) or body retry_after / retryAfterMs, clamped to 1-60 s; default 5 s. */
export function retryMs(header, body) {
  const h = Number(header);
  if (Number.isFinite(h) && h > 0) return Math.min(60_000, Math.max(1000, h * 1000));
  const b = body && typeof body === 'object' ? body : {};
  if (Number.isFinite(b.retryAfterMs) && b.retryAfterMs > 0) return Math.min(60_000, Math.max(1000, b.retryAfterMs));
  if (Number.isFinite(b.retry_after) && b.retry_after > 0) return Math.min(60_000, Math.max(1000, b.retry_after * 1000));
  return 5000;
}

/**
 * Ask for a render until it is ready. Understands rd-studio directly (200 {url} / 202 / 404 / 422 / 400 / 503) and the
 * jukebox's wrapper (200 {status: READY|RENDERING|ORIGINAL|DOWN}). Never falls back to anything by itself.
 * Resolves {kind: 'ready', url, data} | {kind: 'unknown'|'failed'|'bad'|'unreachable'|'timeout'|'aborted'|'none', ...}.
 */
export async function pollArrange(url, o = {}) {
  const f = o.fetch || globalThis.fetch, sleep = o.sleep || ((ms) => new Promise((r) => setTimeout(r, ms)));
  const now = o.now || Date.now, start = now(), maxMs = o.maxMs ?? PRESS_MAX_MS, signal = o.signal;
  for (let attempt = 1; ; attempt++) {
    if (signal?.aborted) return { kind: 'aborted' };
    let res, body = null;
    try {
      res = await f(url, { signal, cache: 'no-store', headers: { Accept: 'application/json' } });
      try { body = await res.json(); } catch { body = null; }
    } catch (e) {
      return { kind: signal?.aborted ? 'aborted' : 'unreachable', error: String(e && e.message || e) };
    }
    const st = res.status, b = body && typeof body === 'object' ? body : {};
    const ra = () => retryMs(res.headers?.get?.('Retry-After'), b);
    let wait = 0;
    if (st === 200 && typeof b.url === 'string' && b.url) return { kind: 'ready', url: b.url, data: b };
    if (st === 202 || (st === 200 && b.status === 'RENDERING')) {
      wait = ra();
      o.onPressing?.({ attempt, retryMs: wait, etaMs: Number.isFinite(b.eta_s) ? b.eta_s * 1000 : wait, job: b.job || b.jobId || null, elapsedMs: now() - start });
    } else if (st === 503) {
      wait = ra(); o.onBusy?.({ attempt, retryMs: wait });
    } else if (st === 200 && b.status === 'DOWN') return { kind: 'unreachable', note: b.note || '' };
    else if (st === 200) return { kind: 'none', note: b.note || '', data: b };
    else if (st === 404) return { kind: 'unknown' };
    else if (st === 422) return { kind: 'failed' };
    else if (st === 400) return { kind: 'bad', error: b.error || '' };
    else return { kind: 'unreachable', status: st };
    if (now() - start + wait > maxMs) return { kind: 'timeout' };
    await sleep(wait);
  }
}

/** Progress shown while pressing: eased toward the ETA, never claiming done (holds below 0.97) until the render is ready. */
export function pressProgress(elapsedMs, etaMs) {
  const eta = Math.max(1000, etaMs || 18_000), x = Math.max(0, elapsedMs) / eta;
  return Math.min(0.97, x < 1 ? 0.9 * (1 - Math.pow(1 - x, 2)) : 0.9 + 0.07 * (1 - Math.exp(-(x - 1) * 2)));
}

function bytesOf(seed) {
  const hex = String(seed || '').replace(/^0x/, '').replace(/[^0-9a-f]/gi, '');
  const out = [];
  for (let i = 0; i + 1 < hex.length && out.length < 32; i += 2) out.push(parseInt(hex.slice(i, i + 2), 16));
  if (!out.length) for (const c of String(seed || 'rd')) out.push(c.charCodeAt(0) & 255);
  while (out.length < 8) out.push((out[out.length - 1] * 31 + 7) & 255);
  return out;
}

/** A deterministic, song-like waveform (-1..1) from the token hash: the groove before the real audio exists. */
export function seededWave(seed, n = 512) {
  const b = bytesOf(seed), w = new Float32Array(n);
  const parts = [0, 1, 2, 3].map((k) => ({ f: 3 + (b[k] % 23), p: (b[k + 4] / 255) * TAU, a: 0.25 + (b[(k + 8) % b.length] / 255) * 0.5 }));
  const beat = 8 + (b[12 % b.length] % 9);
  for (let i = 0; i < n; i++) {
    const t = i / n; let v = 0;
    for (const p of parts) v += p.a * Math.sin(TAU * p.f * t + p.p);
    v *= 0.55 + 0.45 * Math.abs(Math.sin(Math.PI * beat * t));            // pulses like bars of music
    w[i] = Math.max(-1, Math.min(1, v / 1.6));
  }
  return w;
}

/** Up to 5 label colours from the hash (used when there is no coat image). */
export function paletteFrom(seed) {
  const b = bytesOf(seed), base = (b[0] / 255) * 360;
  return [0, 1, 2, 3, 4].map((i) => `hsl(${Math.round((base + i * (40 + b[1] % 60)) % 360)} ${55 + b[i + 2] % 35}% ${30 + (b[i + 3] % 40)}%)`);
}

/**
 * The groove as points: a spiral from the outer rim inward, cut up to `progress` (0..1), its radius modulated by the
 * waveform. Pure geometry so it can be tested.
 */
export function groovePoints(progress, wave, { rOuter = 1, rInner = 0.42, turns = 26, amp = 0.012, steps = 1400 } = {}) {
  const p = Math.max(0, Math.min(1, Number(progress) || 0)), m = Math.floor(steps * p), pts = [];
  for (let i = 0; i <= m; i++) {
    const t = i / steps, a = t * turns * TAU, r0 = rOuter - (rOuter - rInner) * t;
    const s = wave && wave.length ? wave[Math.floor(t * (wave.length - 1))] : 0;
    const r = r0 + amp * s;
    pts.push([r * Math.cos(a), r * Math.sin(a)]);
  }
  return pts;
}

export function prefersReducedMotion(win = globalThis) {
  try { return !!win.matchMedia?.('(prefers-reduced-motion: reduce)').matches; } catch { return false; }
}

/**
 * Draw the record on a canvas. phase: 'pressing' (label stamped in, groove forming with progress), 'playing' (spins at
 * 33 1/3 rpm, the live waveform rides the groove), 'idle'. With reduced motion: no stamping, no spin, no live wobble;
 * the groove still shows progress, redrawn only when something changes.
 */
export function createPress(canvas, opts = {}) {
  const g = canvas.getContext('2d');
  const reduced = opts.reducedMotion ?? prefersReducedMotion();
  const st = { phase: 'idle', progress: 0, analyser: null, label: opts.label || null, palette: opts.palette || paletteFrom(opts.seed),
    wave: seededWave(opts.seed), angle: 0, stampAt: null, last: 0, raf: 0, dead: false };
  const raf = globalThis.requestAnimationFrame || ((fn) => setTimeout(() => fn(Date.now()), 33));
  const caf = globalThis.cancelAnimationFrame || clearTimeout;
  let live = null;

  function drawLabel(cx, cy, r, t) {
    let k = 1;
    if (st.phase === 'pressing' && !reduced) {
      const s = Math.min(1, (t - (st.stampAt ?? t)) / 900);              // the stamp comes down once
      k = 1 + 0.35 * Math.pow(1 - s, 3);
    }
    g.save(); g.translate(cx, cy); g.scale(k, k);
    g.beginPath(); g.arc(0, 0, r, 0, TAU); g.clip();
    if (st.label && st.label.complete !== false && (st.label.naturalWidth ?? 1) > 0) {
      g.rotate(-st.angle * 0.0); g.drawImage(st.label, -r, -r, 2 * r, 2 * r);
    } else {
      const pal = st.palette;
      for (let i = 0; i < pal.length; i++) { g.fillStyle = pal[i]; g.beginPath(); g.arc(0, 0, r * (1 - i / pal.length), 0, TAU); g.fill(); }
    }
    g.restore();
    g.save(); g.translate(cx, cy);
    g.strokeStyle = 'rgba(0,0,0,.45)'; g.lineWidth = Math.max(1, r * 0.05); g.beginPath(); g.arc(0, 0, r * k, 0, TAU); g.stroke();
    g.fillStyle = '#111'; g.beginPath(); g.arc(0, 0, r * 0.08, 0, TAU); g.fill();       // spindle hole
    g.restore();
  }

  function draw(t) {
    const w = canvas.width, h = canvas.height, cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 2;
    g.clearRect(0, 0, w, h);
    g.save(); g.translate(cx, cy); g.rotate(st.angle);
    const disc = g.createRadialGradient(0, 0, R * 0.3, 0, 0, R);
    disc.addColorStop(0, '#1b1b1b'); disc.addColorStop(1, '#050505');
    g.fillStyle = disc; g.beginPath(); g.arc(0, 0, R, 0, TAU); g.fill();
    // the groove: cut so far (pressing) or whole (playing)
    const prog = st.phase === 'playing' ? 1 : st.progress;
    const pts = groovePoints(prog, st.wave, { rOuter: 0.97, rInner: 0.42, turns: 22, amp: 0.018, steps: reduced ? 700 : 1400 });
    g.strokeStyle = 'rgba(200,200,200,.28)'; g.lineWidth = Math.max(0.6, R / 260);
    g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x * R, y * R) : g.moveTo(x * R, y * R))); g.stroke();
    if (st.phase === 'pressing' && pts.length) {                           // the cutting head
      const [x, y] = pts[pts.length - 1]; g.fillStyle = 'rgba(255,214,120,.95)'; g.beginPath(); g.arc(x * R, y * R, Math.max(2, R / 70), 0, TAU); g.fill();
    }
    g.restore();
    // live waveform riding the outer groove while it plays
    if (st.phase === 'playing' && st.analyser && !reduced) {
      live ||= new Uint8Array(st.analyser.fftSize);
      st.analyser.getByteTimeDomainData(live);
      g.save(); g.translate(cx, cy); g.strokeStyle = 'rgba(255,214,120,.8)'; g.lineWidth = Math.max(1, R / 160); g.beginPath();
      for (let i = 0; i < live.length; i += 4) {
        const a = (i / live.length) * TAU, r = R * (0.88 + ((live[i] - 128) / 128) * 0.08);
        i ? g.lineTo(r * Math.cos(a), r * Math.sin(a)) : g.moveTo(r * Math.cos(a), r * Math.sin(a));
      }
      g.closePath(); g.stroke(); g.restore();
    }
    drawLabel(cx, cy, R * 0.36, t);
  }

  function loop(t) {
    if (st.dead) return;
    const dt = st.last ? Math.min(100, t - st.last) : 0; st.last = t;
    if (st.phase === 'playing' && !reduced) st.angle = (st.angle + (RPM / 60) * TAU * (dt / 1000)) % TAU;
    draw(t);
    if (!reduced) st.raf = raf(loop);
  }

  const api = {
    set(next = {}) {
      if (next.phase && next.phase !== st.phase) { st.phase = next.phase; if (next.phase === 'pressing') st.stampAt = null; }
      if (next.progress != null) st.progress = Math.max(0, Math.min(1, next.progress));
      if ('analyser' in next) { st.analyser = next.analyser; live = null; }
      if ('label' in next) st.label = next.label;
      if (st.phase === 'pressing' && st.stampAt == null) st.stampAt = (globalThis.performance?.now?.() ?? Date.now());
      if (reduced) draw(globalThis.performance?.now?.() ?? Date.now());
      return api;
    },
    get state() { return { phase: st.phase, progress: st.progress, reduced, spinning: st.phase === 'playing' && !reduced }; },
    destroy() { st.dead = true; caf(st.raf); },
  };
  if (st.label && st.label.complete === false) st.label.addEventListener?.('load', () => reduced && draw(0), { once: true });
  if (reduced) draw(0); else st.raf = raf(loop);
  return api;
}

/**
 * The always-on ear-safety chain for a page without the jukebox's full sound engine:
 * input -> gain (<= 1) -> limiter (fixed) -> ceiling -> analyser -> speakers. guard() restores any tampering and runs on a
 * timer (not frames, which stall in background tabs). check() proves the limiter is between input and the speakers.
 */
export function createSafeChain(ctx, { volume = 1, guardMs = 200 } = {}) {
  const input = ctx.createGain(), gain = ctx.createGain(), limiter = ctx.createDynamicsCompressor(), ceiling = ctx.createGain(), analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  const vol = Math.max(0, Math.min(1, volume));
  gain.gain.value = vol; ceiling.gain.value = CEILING;
  for (const [k, v] of Object.entries(LIMITER)) limiter[k].value = v;
  input.connect(gain); gain.connect(limiter); limiter.connect(ceiling); ceiling.connect(analyser); analyser.connect(ctx.destination);
  const graph = new Map([[input, [gain]], [gain, [limiter]], [limiter, [ceiling]], [ceiling, [analyser]], [analyser, [ctx.destination]]]);
  function guard() {
    for (const [k, v] of Object.entries(LIMITER)) if (Math.abs(limiter[k].value - v) > 1e-6) limiter[k].value = v;
    if (Math.abs(ceiling.gain.value - CEILING) > 1e-6) ceiling.gain.value = CEILING;
    if (!(gain.gain.value <= 1)) gain.gain.value = vol;
  }
  function check() {
    // every path from input to the destination passes the limiter (the graph is ours and append-only)
    const seen = new Set(); let ok = true;
    (function walk(n, viaLimiter) {
      if (n === ctx.destination) { if (!viaLimiter) ok = false; return; }
      if (seen.has(n)) return; seen.add(n);
      for (const m of graph.get(n) || []) walk(m, viaLimiter || n === limiter);
    })(input, false);
    return ok && limiter.threshold.value <= LIMITER.threshold + 1e-6 && limiter.ratio.value >= LIMITER.ratio - 1e-6;
  }
  const timer = guardMs ? setInterval(guard, guardMs) : null;
  return {
    ctx, input, gain, limiter, ceiling, analyser, guard, check,
    connect(node) { node.connect(input); return () => { try { node.disconnect(input); } catch { /* gone */ } }; },
    destroy() { if (timer) clearInterval(timer); },
  };
}
