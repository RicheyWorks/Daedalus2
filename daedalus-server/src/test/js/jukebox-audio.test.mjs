// SPDX-License-Identifier: MIT
// node --test src/test/js/  (also run by JukeboxAudioJsTest under mvn verify)
import test from "node:test";
import assert from "node:assert/strict";
import * as SND from "../../main/resources/static/jukebox-audio.js";
import {
  createChain, checkChain, PRESETS, GAIN_LEVELS, FILTERS, LIMITER, CEILING, EQ_BANDS,
  sanitizeVoice, defaultVoice, noteOn, cutoff, hz, voiceSpec, VOICE_SCHEMA_READY,
} from "../../main/resources/static/jukebox-audio.js";

// ---- a fake AudioContext that records the graph -------------------------------------------------------------
class Param {
  constructor(v = 0) { this.value = v; this.events = []; }
  setTargetAtTime(v) { this.value = v; this.events.push(["target", v]); }
  setValueAtTime(v) { this.value = v; this.events.push(["set", v]); }
  linearRampToValueAtTime(v) { this.value = v; this.events.push(["ramp", v]); }
  cancelScheduledValues() { this.events.push(["cancel"]); }
}
class Node {
  constructor(kind) { this.kind = kind; this._outs = []; }
  connect(d) { this._outs.push(d); return d; }
  disconnect(d) { this._outs = d === undefined ? [] : this._outs.filter(x => x !== d); }
}
class FakeCtx {
  constructor() { this.currentTime = 0; this.destination = new Node("destination"); this.made = []; }
  mk(kind, params) { const n = new Node(kind); for (const [k, v] of Object.entries(params)) n[k] = new Param(v); this.made.push(n); return n; }
  createGain() { return this.mk("gain", { gain: 1 }); }
  createBiquadFilter() { const n = this.mk("biquad", { frequency: 350, Q: 1, gain: 0, detune: 0 }); n.type = "lowpass"; return n; }
  createDynamicsCompressor() { return this.mk("compressor", { threshold: -24, knee: 30, ratio: 12, attack: 0.003, release: 0.25 }); }
  createAnalyser() { const n = this.mk("analyser", {}); n.fftSize = 2048; return n; }
  createOscillator() { const n = this.mk("osc", { frequency: 440, detune: 0 }); n.type = "sine"; n.start = () => { n.started = true; }; n.stop = () => { n.stopped = true; }; return n; }
  createBufferSource() { const n = this.mk("buffer", { playbackRate: 1 }); n.start = () => {}; n.stop = () => {}; return n; }
}

const reachable = (from, to) => {
  const seen = new Set(), stack = [from];
  while (stack.length) { const n = stack.pop(); if (n === to) return true; if (seen.has(n)) continue; seen.add(n); stack.push(...n._outs); }
  return false;
};

// ---- the limiter is always there ---------------------------------------------------------------------------
test("the chain ends limiter → ceiling → analyser → speakers, with the fixed ear-safety settings", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  assert.equal(c.limiter.kind, "compressor");
  assert.deepEqual(c.limiter._outs, [c.ceiling]);
  assert.deepEqual(c.ceiling._outs, [c.analyser]);
  assert.deepEqual(c.analyser._outs, [ctx.destination]);
  for (const [k, v] of Object.entries(LIMITER)) assert.equal(c.limiter[k].value, v, k);
  assert.equal(c.ceiling.gain.value, CEILING);
  assert.ok(c.checkChain());
  // only the analyser feeds the speakers
  assert.deepEqual(ctx.made.filter(n => n._outs.includes(ctx.destination)), [c.analyser]);
});

test("no control can remove, bypass or loosen the limiter", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  for (const p of Object.keys(PRESETS)) c.setPreset(p);
  for (const f of Object.keys(FILTERS)) c.setFilter(f);
  for (const l of [...Object.keys(GAIN_LEVELS), "ludicrous", undefined]) c.setLevel(l);
  for (let i = 0; i < EQ_BANDS.length; i++) c.setBand(i, 99);
  assert.ok(c.checkChain());
  for (const [k, v] of Object.entries(LIMITER)) assert.equal(c.limiter[k].value, v, k);
  assert.ok(!("bypass" in c) && !("setLimiter" in c) && !("disableLimiter" in c));
  assert.ok(Object.isFrozen(LIMITER));
});

test("guard() restores a tampered limiter, ceiling or runaway gain", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  c.limiter.threshold.value = 0; c.limiter.ratio.value = 1; c.ceiling.gain.value = 4; c.gain.gain.value = 10;
  c.guard();
  for (const [k, v] of Object.entries(LIMITER)) assert.equal(c.limiter[k].value, v, k);
  assert.equal(c.ceiling.gain.value, CEILING);
  assert.ok(c.gain.gain.value <= 1);
});

test("checkChain catches a source wired straight to the speakers or a missing limiter", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  c.eq[3].connect(ctx.destination);                  // a sneaky bypass
  assert.equal(c.checkChain(), false);
  const ctx2 = new FakeCtx(), c2 = createChain(ctx2);
  c2.limiter.disconnect(c2.ceiling);
  assert.equal(c2.checkChain(), false);
});

test("sources plug into the chain input, never the destination", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  const media = new Node("media");
  const off = c.connectSource(media);
  assert.deepEqual(media._outs, [c.input]);
  assert.ok(reachable(media, c.limiter));
  off();
  assert.deepEqual(media._outs, []);
});

// ---- the player controls -----------------------------------------------------------------------------------
test("gain levels are low < med < high, all under unity", () => {
  assert.ok(GAIN_LEVELS.low < GAIN_LEVELS.med && GAIN_LEVELS.med < GAIN_LEVELS.high && GAIN_LEVELS.high < 1);
  const c = createChain(new FakeCtx());
  c.setLevel("high"); assert.equal(c.gain.gain.value, GAIN_LEVELS.high);
  c.setLevel("nope"); assert.equal(c.state.level, "med");
});

test("EQ presets set all ten bands; a band is clamped to ±12 dB and makes the preset custom", () => {
  const c = createChain(new FakeCtx());
  assert.equal(c.eq.length, 10);
  assert.equal(c.eq[0].type, "lowshelf"); assert.equal(c.eq[9].type, "highshelf"); assert.equal(c.eq[5].type, "peaking");
  c.setPreset("rock");
  assert.deepEqual(c.eq.map(b => b.gain.value), PRESETS.rock);
  c.setBand(2, 40); assert.equal(c.eq[2].gain.value, 12); assert.equal(c.state.preset, "custom");
  c.setBand(2, "junk"); assert.equal(c.eq[2].gain.value, -12);
  c.setPreset("doesnotexist"); assert.deepEqual(c.eq.map(b => b.gain.value), PRESETS.flat);
  for (const p of Object.values(PRESETS)) assert.equal(p.length, 10);
});

test("filters switch shape and 'none' is transparent", () => {
  const c = createChain(new FakeCtx());
  c.setFilter("radio"); assert.equal(c.tone.type, "bandpass");
  c.setFilter("thin"); assert.equal(c.tone.type, "highpass");
  c.setFilter("none"); assert.equal(c.tone.type, "allpass");
  c.setFilter("<script>"); assert.equal(c.state.filter, "none");
});

// ---- the keyboard ------------------------------------------------------------------------------------------
test("voices are sanitized: ranges clamped, unknown instruments and waves refused", () => {
  const v = sanitizeVoice({ instrument: "sample:../../etc", wave: "noise", attack: -5, decay: 1e9, sustain: 3, release: "x", brightness: 2, blend: -1, evil: 1 });
  assert.deepEqual(Object.keys(v).sort(), Object.keys(defaultVoice()).sort());
  assert.equal(v.instrument, "synth"); assert.equal(v.wave, "sawtooth");
  assert.equal(v.attack, 0.001); assert.equal(v.decay, 3); assert.equal(v.sustain, 1); assert.equal(v.release, 0.005);
  assert.equal(v.brightness, 1); assert.equal(v.blend, 0);
  assert.equal(sanitizeVoice({ instrument: "sample:celtic-pipes" }).instrument, "sample:celtic-pipes");
});

test("a note runs through the chain (so the limiter applies) and releases cleanly", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  const n = noteOn(c, { wave: "square", brightness: 0, blend: 0.25 }, 69);
  const osc = ctx.made.find(x => x.kind === "osc");
  assert.equal(osc.frequency.value, 440); assert.equal(osc.type, "square");
  assert.ok(reachable(osc, c.limiter));
  assert.ok(!osc._outs.includes(ctx.destination));
  assert.ok(c.checkChain());
  n.stop(); n.stop();
  assert.ok(osc.stopped);
});

test("brightness and pitch maps", () => {
  assert.equal(Math.round(cutoff(0)), 250);
  assert.equal(Math.round(cutoff(1)), 12000);
  assert.equal(hz(69), 440);
  assert.equal(Math.round(hz(60)), 262);
});

test("voice specs are clean, and the studio schema is honestly marked not ready", () => {
  const s = voiceSpec({ lead: { wave: "sine", attack: 99 }, bass: {} });
  assert.equal(s.voices.lead.attack, 2);
  assert.equal(VOICE_SCHEMA_READY, true);
});

// ---- fuzz --------------------------------------------------------------------------------------------------
test("fuzzed control input never breaks the chain or the limiter", () => {
  const ctx = new FakeCtx(), c = createChain(ctx);
  const junk = [NaN, Infinity, -Infinity, null, undefined, "", "1e400", {}, [], -1, 1e9, "flat", "rock", "__proto__", "constructor"];
  let seed = 46630; const r = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
  for (let i = 0; i < 3000; i++) {
    const v = junk[Math.floor(r() * junk.length)];
    [() => c.setLevel(v), () => c.setPreset(v), () => c.setFilter(v), () => c.setBand(Math.floor(r() * 14) - 2, v),
      () => noteOn(c, { wave: v, attack: v, blend: v, brightness: v, instrument: v }, 20 + Math.floor(r() * 90)).stop()][i % 5]();
  }
  assert.ok(c.checkChain());
  for (const [k, val] of Object.entries(LIMITER)) assert.equal(c.limiter[k].value, val);
  for (const b of c.eq) assert.ok(Math.abs(b.gain.value) <= 12 && Number.isFinite(b.gain.value));
  assert.ok(c.gain.gain.value <= 1);
});

test("r4 render options: defaults, clamping, and surface noise off by default", () => {
  assert.deepEqual(SND.sanitizeRender(undefined), { format: "mp3", preset: "neutral", vinyl: 0, noise: "off" });
  assert.deepEqual(SND.sanitizeRender({ format: "flac", preset: "harman", vinyl: 57, noise: -45 }), { format: "flac", preset: "harman", vinyl: 60, noise: "-45" });
  assert.deepEqual(SND.sanitizeRender({ format: "wav", preset: "constructor", vinyl: 999, noise: -5 }), { format: "mp3", preset: "neutral", vinyl: 100, noise: "-30" });
  assert.equal(SND.sanitizeRender({ vinyl: "x", noise: "on" }).noise, "off");
  assert.deepEqual([...SND.HEADPHONE_PRESETS], ["neutral", "harman", "crossfeed", "warm", "bass"]);
  for (let i = 0; i < 500; i++) {
    const r = SND.sanitizeRender({ format: Math.random(), preset: String(Math.random()), vinyl: (Math.random() - .5) * 1e4, noise: (Math.random() - .5) * 200 });
    assert.ok(r.vinyl % 10 === 0 && r.vinyl >= 0 && r.vinyl <= 100);
    assert.ok(r.noise === "off" || (+r.noise >= -60 && +r.noise <= -30));
  }
});

test("rd-voice/1: studio note queries are clamped to the schema and never carry unknown keys", () => {
  const q = SND.noteQuery("Celesta", { attack: 99, decay: -1, sustain: 2, release: 0 }, 300, { vel: 9, dur: 0 });
  assert.deepEqual(Object.fromEntries(q), { voice: "Celesta", midi: "108", vel: "1", dur: "0.05", a: "2", d: "0.001", s: "1", r: "0.005", format: "mp3" });
  assert.deepEqual([...SND.noteQuery("Saw Lead", SND.defaultVoice(), 60, { native: true }).keys()], ["voice", "midi", "vel", "dur", "format"]);
  for (const bad of ["", "../x", "a".repeat(49), "<script>", null]) assert.throws(() => SND.noteQuery(bad, {}, 60));
  for (let i = 0; i < 300; i++) {
    const q2 = SND.noteQuery("Celesta", { attack: Math.random() * 1e3 - 500, decay: NaN, sustain: "x", release: Infinity }, Math.random() * 400 - 100);
    const m = +q2.get("midi"); assert.ok(Number.isInteger(m) && m >= 21 && m <= 108);
    for (const k of ["a", "d", "s", "r"]) { const [lo, hi] = SND.NOTE_SCHEMA[k]; assert.ok(+q2.get(k) >= lo && +q2.get(k) <= hi, k); }
  }
});

test("a studio engine voice is a valid instrument; junk is not", () => {
  assert.equal(SND.sanitizeVoice({ instrument: "studio:Saw Lead" }).instrument, "studio:Saw Lead");
  assert.equal(SND.sanitizeVoice({ instrument: "studio:<img>" }).instrument, "synth");
});
