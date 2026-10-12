/* SPDX-License-Identifier: MIT
 * rd-audio-shim: run BEFORE a token's raw on-chain HTML. Every AudioContext's `destination` becomes
 * gain(volume) -> fixed limiter (-10 dB, 20:1) -> ceiling 0.89 -> the real speakers, and media elements are held at
 * or below `volume`. volume 0 = silent (watch only); RAW_VOLUME 0.35 = the explicit opt-in. Classic script, no module. */
(function (root) {
  function rdAudioShim(win, volume) {
    var vol = Math.max(0, Math.min(1, Number(volume) || 0));
    var Base = win.BaseAudioContext || win.AudioContext || win.webkitAudioContext;
    var Live = win.AudioContext || win.webkitAudioContext;
    if (Base && Live && !Base.prototype.__rdShim) {
      var desc = Object.getOwnPropertyDescriptor(Base.prototype, 'destination');
      if (desc && desc.get) {
        var real = desc.get, safe = new WeakMap();
        Object.defineProperty(Base.prototype, 'destination', { configurable: false, get: function () {
          var out = real.call(this);
          if (!(this instanceof Live)) return out;                       // offline renders stay untouched
          var s = safe.get(this);
          if (!s) {
            var g = this.createGain(), l = this.createDynamicsCompressor(), c = this.createGain();
            g.gain.value = vol; c.gain.value = 0.89;
            l.threshold.value = -10; l.knee.value = 0; l.ratio.value = 20; l.attack.value = 0.001; l.release.value = 0.12;
            g.connect(l); l.connect(c); c.connect(out);
            s = { g: g, l: l, c: c }; safe.set(this, s);
            win.setInterval(function () {                                   // nobody turns it back up
              if (s.g.gain.value !== vol) s.g.gain.value = vol;
              if (s.l.threshold.value > -10) s.l.threshold.value = -10;
              if (s.l.ratio.value < 20) s.l.ratio.value = 20;
              if (s.c.gain.value !== 0.89) s.c.gain.value = 0.89;
            }, 200);
          }
          return s.g;
        } });
      }
      Object.defineProperty(Base.prototype, '__rdShim', { value: vol });
    }
    var M = win.HTMLMediaElement;
    if (M && !M.prototype.__rdShim) {
      var vd = Object.getOwnPropertyDescriptor(M.prototype, 'volume');
      if (vd && vd.set) {
        Object.defineProperty(M.prototype, 'volume', { configurable: false, get: vd.get, set: function (v) { vd.set.call(this, Math.min(vol, Math.max(0, +v || 0))); } });
        var play = M.prototype.play;
        M.prototype.play = function () { vd.set.call(this, Math.min(vol, vd.get.call(this))); if (vol === 0) this.muted = true; return play.apply(this, arguments); };
      }
      Object.defineProperty(M.prototype, '__rdShim', { value: vol });
    }
    return vol;
  }
  root.rdAudioShim = rdAudioShim;
  if (typeof module !== 'undefined' && module.exports) module.exports = rdAudioShim;
})(typeof window !== 'undefined' ? window : globalThis);
