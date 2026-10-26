// SPDX-License-Identifier: MIT
// node tools/controllers/contract_web.js CONTRACT.json  -- run the controller contract's vectors against daedalus-pad.js.
"use strict";
const fs = require("fs"), path = require("path");
const contract = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let now = 1000;
Object.defineProperty(globalThis, "performance", { value: { now: () => now }, configurable: true });
let pads = [null, null, null, null];
Object.defineProperty(globalThis, "navigator", { value: { getGamepads: () => pads, userAgent: "Windows" }, configurable: true });
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const listeners = {};
globalThis.addEventListener = (t, f) => { (listeners[t] = listeners[t] || []).push(f); };
require(process.env.DAEDALUS_PAD || path.join(__dirname, "..", "..", "daedalus-server/src/main/resources/static/controllers/daedalus-pad.js"));   // DAEDALUS_PAD: run another copy (mutant checks)
const STD = { south: 0, east: 1, west: 2, north: 3, back: 8, start: 9, dpad_up: 12, dpad_down: 13, dpad_left: 14, dpad_right: 15 };
const ONE_BUTTON_BUNDLE = { families: { atari: { south: "Fire", confirm: "south" } }, models: [], devices: { "0e6a:4011": { n: "Atari CX Controller", f: "atari", k: -1, m: { W: "a:b0,leftx:a0,lefty:a1" } } } };
const results = [];
for (const v of contract.vectors.filter(x => x.scope.includes("web"))) {
  pads = [null, null, null, null]; now = 1000;
  const settings = { loaded: () => true, get: id => ({ ConfirmButton: 0, LeftDeadzone: 15, LeftMaxInput: 100, LeftAxialDeadzone: 0, RightDeadzone: 15, RightMaxInput: 100,
    RightAxialDeadzone: 0, TriggerInnerDeadzone: 5, TriggerOuterDeadzone: 95, Vibration: 1, VibrationStrength: 100 }[id]), layout: () => null, choice: () => null };
  const one = v.layout === "one-button";
  const P = DaedalusPad.create({ settings, sampleMs: 0, bundle: one ? ONE_BUTTON_BUNDLE : null });
  const id = one ? "Atari CX Controller (Vendor: 0e6a Product: 4011)" : v.layout === "east" ? "Pro Controller (STANDARD GAMEPAD Vendor: 057e Product: 2009)"
    : "Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)";
  const mk = i => ({ index: i, id, mapping: one ? "" : "standard", connected: true, axes: [0, 0, 0, 0], buttons: Array.from({ length: 17 }, () => ({ pressed: false, value: 0 })) });
  pads[0] = mk(0); pads[1] = mk(1);                       // "@2" = the second pad
  let ok = true; const fails = [];
  const pulses = [];
  for (const [si, st] of v.steps.entries()) {
    if (st.release_all) { (listeners.blur || []).forEach(f => f()); }
    for (const k of st.down || []) { const [name, src] = k.split("@"); const b = pads[src ? 1 : 0].buttons[STD[name]]; b.pressed = true; b.value = 1; }
    for (const k of st.up || []) { const [name, src] = k.split("@"); const b = pads[src ? 1 : 0].buttons[STD[name]]; b.pressed = false; b.value = 0; }
    if (st.axes) {
      const a = pads[0].axes;
      if ("lx" in st.axes) a[0] = st.axes.lx;
      if ("ly" in st.axes) a[1] = -st.axes.ly;                // contract y is up-positive; the browser's is down-positive
      if ("lt" in st.axes) { pads[0].buttons[6].value = st.axes.lt; pads[0].buttons[6].pressed = st.axes.lt > 0.5; }
      if ("rt" in st.axes) { pads[0].buttons[7].value = st.axes.rt; pads[0].buttons[7].pressed = st.axes.rt > 0.5; }
    }
    P.poll();
    if (st.wait_ms) { const end = now + st.wait_ms; while (now < end) { now += 4; P.poll(); } }
    if (st.pulse) { let seen = false; for (let t = 0; t < 30; t++) { if (P.held(st.pulse)) seen = true; now += 4; P.poll(); } if (!seen) { ok = false; fails.push(si + ": no " + st.pulse + " pulse"); } }
    if (st.held) {
      const got = contract.logical.filter(k => P.held(k));
      if (JSON.stringify(got.sort()) !== JSON.stringify(st.held.slice().sort())) { ok = false; fails.push(si + ": held " + JSON.stringify(got) + " expected " + JSON.stringify(st.held)); }
    }
    if (st.analog) {
      const a = P.axes(0);
      for (const k in st.analog) { const [lo, hi] = st.analog[k]; const val = k === "ly" ? -a.ly : a[k]; if (!(val >= lo - 1e-9 && val <= hi + 1e-9)) { ok = false; fails.push(si + ": " + k + "=" + val.toFixed(3) + " not in [" + lo + "," + hi + "]"); } }
    }
  }
  results.push({ id: v.id, ok, fails });
}
console.log(JSON.stringify(results));
