// SPDX-License-Identifier: MIT
// rd-jukebox sound engine: a FiiO-style player chain plus a Casio-style keyboard, all in WebAudio.
// No DOM and no three.js here, so it runs (and is tested) under node with a fake AudioContext.
//
//   sources ─▶ input ─▶ 10-band EQ ─▶ tone filter ─▶ gain (low/med/high) ─▶ LIMITER ─▶ ceiling ─▶ analyser ─▶ speakers
//   (media element, line in, keyboard voices)                                  ▲ always on: there is no API to bypass it
//
// Ear safety: the limiter (a hard-knee 20:1 DynamicsCompressor at -10 dBFS, 1 ms attack) and a fixed 0.89 ceiling sit
// between every source and the speakers. Gain is clamped to 1. guard() re-asserts the limiter's settings, and
// checkChain() proves every node feeding the speakers passes through it; the panel calls guard() on every frame.

export const EQ_BANDS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
export const EQ_RANGE_DB = 12;

/** EQ presets, dB per band (31 Hz … 16 kHz). */
export const PRESETS = {
  flat:       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  bass:       [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
  vocal:      [-2, -2, -1, 1, 3, 4, 3, 1, 0, -1],
  rock:       [4, 3, 1, -1, -2, -1, 1, 3, 4, 4],
  jazz:       [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
  classical:  [4, 3, 2, 1, -1, -1, 0, 2, 3, 4],
  electronic: [5, 4, 1, 0, -2, 1, 0, 1, 4, 5],
  treble:     [0, 0, 0, 0, 0, 1, 2, 4, 5, 6],
};

/** Output gain steps (pre-limiter). Even "high" stays under unity, and the limiter still has the last word. */
export const GAIN_LEVELS = { low: 0.35, med: 0.6, high: 0.85 };

/** Tone / filter choices: none, or a biquad shape with its cutoff (Hz) and Q. */
export const FILTERS = {
  none:     null,
  warm:     { type: "lowpass", frequency: 6500, Q: 0.5 },
  radio:    { type: "bandpass", frequency: 1800, Q: 0.9 },
  thin:     { type: "highpass", frequency: 300, Q: 0.7 },
  lofi:     { type: "lowpass", frequency: 2800, Q: 0.9 },
};

/** The limiter's fixed settings. Not exported as mutable: guard() restores these if anything touches them. */
export const LIMITER = Object.freeze({ threshold: -10, knee: 0, ratio: 20, attack: 0.001, release: 0.12 });
export const CEILING = 0.89;   // about -1 dBFS after the limiter

const own = (o, k) => typeof k === "string" && Object.hasOwn(o, k);   // never "constructor" / "__proto__"
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, Number.isFinite(+v) ? +v : lo));

/**
 * Builds the player chain on {@code ctx} and returns its controls. {@code destination} defaults to ctx.destination.
 */
export function createChain(ctx, destination = ctx.destination) {
  const input = ctx.createGain();
  const eq = EQ_BANDS.map((f, i) => {
    const b = ctx.createBiquadFilter();
    b.type = i === 0 ? "lowshelf" : i === EQ_BANDS.length - 1 ? "highshelf" : "peaking";
    b.frequency.value = f;
    b.Q.value = 1.1;
    b.gain.value = 0;
    return b;
  });
  const tone = ctx.createBiquadFilter();
  const gain = ctx.createGain();
  const limiter = ctx.createDynamicsCompressor();
  const ceiling = ctx.createGain();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.8;

  // input → eq… → tone → gain → limiter → ceiling → analyser → speakers
  let prev = input;
  for (const b of eq) { prev.connect(b); prev = b; }
  prev.connect(tone);
  tone.connect(gain);
  gain.connect(limiter);
  limiter.connect(ceiling);
  ceiling.connect(analyser);
  analyser.connect(destination);

  const state = { preset: "flat", bands: PRESETS.flat.slice(), filter: "none", level: "med" };

  function guard() {
    for (const [k, v] of Object.entries(LIMITER)) if (limiter[k].value !== v) limiter[k].value = v;
    if (ceiling.gain.value !== CEILING) ceiling.gain.value = CEILING;
    if (!(gain.gain.value <= 1)) gain.gain.value = GAIN_LEVELS.med;
  }

  function setLevel(level) {
    if (!own(GAIN_LEVELS, level)) level = "med";
    state.level = level;
    gain.gain.setTargetAtTime(GAIN_LEVELS[level], ctx.currentTime, 0.03);
    guard();
  }

  function setBand(i, db) {
    if (!(i >= 0 && i < eq.length)) return;
    state.bands[i] = clamp(db, -EQ_RANGE_DB, EQ_RANGE_DB);
    state.preset = "custom";
    eq[i].gain.setTargetAtTime(state.bands[i], ctx.currentTime, 0.02);
  }

  function setPreset(name) {
    const p = own(PRESETS, name) ? PRESETS[name] : PRESETS.flat;
    state.preset = own(PRESETS, name) ? name : "flat";
    p.forEach((db, i) => { state.bands[i] = db; eq[i].gain.setTargetAtTime(db, ctx.currentTime, 0.02); });
  }

  function setFilter(name) {
    const f = own(FILTERS, name) ? FILTERS[name] : null;
    state.filter = f ? name : "none";
    if (!f) {                       // "none": an allpass at the top of the band is acoustically transparent
      tone.type = "allpass";
      tone.frequency.value = 20000;
      tone.Q.value = 0.0001;
    } else {
      tone.type = f.type;
      tone.frequency.setTargetAtTime(f.frequency, ctx.currentTime, 0.02);
      tone.Q.value = f.Q;
    }
  }

  /** Plugs a source node into the chain (never straight into the speakers). Returns a disconnect function. */
  function connectSource(node) {
    node.connect(input);
    return () => { try { node.disconnect(input); } catch (e) { /* already gone */ } };
  }

  setPreset("flat");
  setFilter("none");
  gain.gain.value = GAIN_LEVELS.med;
  guard();

  return {
    ctx, input, eq, tone, gain, limiter, ceiling, analyser, destination, state,
    setLevel, setBand, setPreset, setFilter, connectSource, guard,
    checkChain: () => checkChain({ input, limiter, ceiling, analyser, destination }),
  };
}

/**
 * Walks the recorded graph (nodes expose their outputs as {@code _outs}, or via the panel's own tracking) and returns
 * true only if: the limiter feeds the ceiling, the ceiling feeds the analyser, the analyser is the only node feeding
 * the speakers, and the input reaches the speakers only through the limiter.
 */
export function checkChain({ input, limiter, ceiling, analyser, destination }) {
  const outs = n => (n && n._outs) || [];
  if (!outs(limiter).includes(ceiling) || !outs(ceiling).includes(analyser) || !outs(analyser).includes(destination)) return false;
  // every path from input to destination must cross the limiter
  const seen = new Set(), stack = [input];
  while (stack.length) {
    const n = stack.pop();
    if (n === limiter) continue;            // paths through the limiter are fine
    if (n === destination) return false;    // reached the speakers without the limiter
    if (seen.has(n)) continue;
    seen.add(n);
    stack.push(...outs(n));
  }
  return true;
}

/** Wraps a real AudioContext so connect()/disconnect() are recorded as _outs (checkChain uses it in the browser too). */
export function trackGraph(ctx) {
  const proto = Object.getPrototypeOf(ctx.createGain());
  const base = Object.getPrototypeOf(proto);
  const AudioNodeProto = typeof AudioNode !== "undefined" ? AudioNode.prototype : base;
  if (AudioNodeProto.__jbTracked) return ctx;
  const connect = AudioNodeProto.connect, disconnect = AudioNodeProto.disconnect;
  AudioNodeProto.connect = function (dest, ...rest) {
    (this._outs ||= []).push(dest);
    return connect.call(this, dest, ...rest);
  };
  AudioNodeProto.disconnect = function (dest, ...rest) {
    if (this._outs) this._outs = dest === undefined ? [] : this._outs.filter(d => d !== dest);
    return disconnect.call(this, dest, ...rest);
  };
  AudioNodeProto.__jbTracked = true;
  return ctx;
}

// ---------------------------------------------------------------- the keyboard (Casio side)

export const WAVES = ["sine", "triangle", "square", "sawtooth"];

/** A voice's parameters, with defaults. Also the payload the render service will take (see voiceSpec). */
export function defaultVoice() {
  return { instrument: "synth", wave: "sawtooth", attack: 0.01, decay: 0.2, sustain: 0.6, release: 0.35, brightness: 0.6, blend: 0.3 };
}

/** Clamps a voice to safe ranges (times in seconds; brightness and blend 0..1). Unknown fields are dropped. */
export function sanitizeVoice(v = {}) {
  const d = defaultVoice();
  const inst = typeof v.instrument === "string" && /^(synth|sample:[a-z0-9][a-z0-9-]{0,80}|studio:[A-Za-z0-9 %&._()'-]{1,48})$/.test(v.instrument) ? v.instrument : d.instrument;
  return {
    instrument: inst,
    wave: WAVES.includes(v.wave) ? v.wave : d.wave,
    attack: clamp(v.attack ?? d.attack, 0.001, 2),
    decay: clamp(v.decay ?? d.decay, 0.001, 3),
    sustain: clamp(v.sustain ?? d.sustain, 0, 1),
    release: clamp(v.release ?? d.release, 0.005, 4),
    brightness: clamp(v.brightness ?? d.brightness, 0, 1),
    blend: clamp(v.blend ?? d.blend, 0, 1),
  };
}

/** Brightness 0..1 → a lowpass cutoff, exponentially from 250 Hz to 12 kHz. */
export const cutoff = b => 250 * Math.pow(48, clamp(b, 0, 1));

/** MIDI note → Hz (A4 = 69 = 440 Hz). */
export const hz = note => 440 * Math.pow(2, (note - 69) / 12);

/**
 * Plays one note through {@code chain} (so the limiter applies) and returns {stop()}. The voice is a blend of
 * the chosen wave and a sample (when one is loaded: {@code sample} is an AudioBuffer pitched from C4), or of the wave
 * and a detuned partner wave when there is no sample; brightness drives a lowpass; ADSR shapes the amplitude.
 */
export function noteOn(chain, voice, note, sample = null, velocity = 0.8) {
  const ctx = chain.ctx, v = sanitizeVoice(voice), t = ctx.currentTime;
  const amp = ctx.createGain();
  const lp = ctx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.value = cutoff(v.brightness);
  lp.Q.value = 0.8;
  const a = ctx.createGain(), b = ctx.createGain();
  a.gain.value = 1 - v.blend;
  b.gain.value = v.blend;
  const osc = ctx.createOscillator();
  osc.type = v.wave;
  osc.frequency.value = hz(note);
  osc.connect(a);
  let other;
  if (sample && v.instrument.startsWith("sample:")) {
    other = ctx.createBufferSource();
    other.buffer = sample;
    other.playbackRate.value = hz(note) / hz(60);
  } else {
    other = ctx.createOscillator();
    other.type = v.wave === "sine" ? "triangle" : "sine";
    other.frequency.value = hz(note);
    other.detune.value = 7;
  }
  other.connect(b);
  a.connect(lp); b.connect(lp);
  lp.connect(amp);
  const peak = clamp(velocity, 0, 1) * 0.5;      // headroom for chords; the limiter catches the rest
  amp.gain.setValueAtTime(0, t);
  amp.gain.linearRampToValueAtTime(peak, t + v.attack);
  amp.gain.linearRampToValueAtTime(peak * v.sustain, t + v.attack + v.decay);
  const off = chain.connectSource(amp);
  osc.start(t);
  other.start(t);
  let stopped = false;
  return {
    stop() {
      if (stopped) return;
      stopped = true;
      const now = ctx.currentTime;
      amp.gain.cancelScheduledValues(now);
      amp.gain.setValueAtTime(amp.gain.value, now);
      amp.gain.linearRampToValueAtTime(0, now + v.release);
      osc.stop(now + v.release + 0.02);
      other.stop(now + v.release + 0.02);
      osc.onended = () => off();
    },
  };
}

/**
 * The voice settings in the render service's shape. Prometheus's parameter schema (rd-studio
 * server/CHANGES_FOR_FLEX.md) has not landed, so this is our proposal and {@code VOICE_SCHEMA_READY} stays false:
 * the panel shows the controls, plays them live, and says the studio can't render them yet.
 */
export const VOICE_SCHEMA_READY = true;     // rd-studio r4 shipped rd-voice/1 (GET /voices, /voices/schema, /note)
export function voiceSpec(voices) {
  return { schema: "rd-jukebox.voice/0-proposed", voices: Object.fromEntries(Object.entries(voices).map(([k, v]) => [k, sanitizeVoice(v)])) };
}

// ---------------------------------------------------------------- rd-studio r4 render options (CHANGES_FOR_FLEX.md)
export const HEADPHONE_PRESETS = Object.freeze(["neutral", "harman", "crossfeed", "warm", "bass"]);
export const RENDER_DEFAULT = Object.freeze({ format: "mp3", preset: "neutral", vinyl: 0, noise: "off" });
/** Clamp anything (saved state, a tampered localStorage) to what rd-studio accepts; surface noise is off by default. */
export function sanitizeRender(r) {
  const o = r && typeof r === "object" ? r : {};
  const format = o.format === "flac" ? "flac" : "mp3";
  const preset = typeof o.preset === "string" && HEADPHONE_PRESETS.includes(o.preset) ? o.preset : "neutral";
  const v = Number(o.vinyl), vinyl = Number.isFinite(v) ? Math.min(100, Math.max(0, Math.round(v / 10) * 10)) : 0;
  const n = Number(o.noise), noise = o.noise !== "off" && o.noise != null && Number.isFinite(n) ? String(Math.min(-30, Math.max(-60, Math.round(n)))) : "off";
  return { format, preset, vinyl, noise };
}

// ---------------------------------------------------------------- rd-voice/1 (rd-studio GET /note)
/** rd-voice/1 note schema ranges (rd_studio/voices.py NOTE_SCHEMA). */
export const NOTE_SCHEMA = Object.freeze({
  midi: [21, 108], vel: [0.05, 1], dur: [0.05, 8], a: [0.001, 4], d: [0.001, 8], s: [0, 1], r: [0.005, 8], rr: [0, 15],
});
const clampTo = (v, [lo, hi], dflt) => { const n = Number(v); return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : dflt; };
const r4 = (n) => String(Math.round(n * 10000) / 10000);
/**
 * Query params for one studio note: an engine voice (a name from /voices) played with this panel voice's envelope.
 * Everything is clamped to the schema, so the studio never sees an out-of-range value; unknown keys are never sent.
 */
export function noteQuery(voiceName, voice, midi, { vel = 0.8, dur = 1, native = false, format = "mp3" } = {}) {
  if (typeof voiceName !== "string" || !/^[A-Za-z0-9 %&._()'-]{1,48}$/.test(voiceName)) throw new Error("not a studio voice");
  const v = sanitizeVoice(voice), q = new URLSearchParams();
  q.set("voice", voiceName);
  q.set("midi", String(Math.round(clampTo(midi, NOTE_SCHEMA.midi, 60))));
  q.set("vel", r4(clampTo(vel, NOTE_SCHEMA.vel, 0.8)));
  q.set("dur", r4(clampTo(dur, NOTE_SCHEMA.dur, 1)));
  if (!native) {                         // omit a/d/s/r to hear the instrument natively
    q.set("a", r4(clampTo(v.attack, NOTE_SCHEMA.a, 0.01)));
    q.set("d", r4(clampTo(v.decay, NOTE_SCHEMA.d, 0.2)));
    q.set("s", r4(clampTo(v.sustain, NOTE_SCHEMA.s, 0.7)));
    q.set("r", r4(clampTo(v.release, NOTE_SCHEMA.r, 0.3)));
  }
  q.set("format", format === "flac" ? "flac" : "mp3");
  return q;
}
