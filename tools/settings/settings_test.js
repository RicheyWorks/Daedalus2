// SPDX-License-Identifier: MIT
// node tools/settings/settings_test.js  -- DaedalusSettings + DaedalusPad math against the shared schema (no browser).
"use strict";
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const store = {};
globalThis.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
let pads = [null, null, null, null];
Object.defineProperty(globalThis, "navigator", { value: { getGamepads: () => pads, userAgent: "Windows" }, configurable: true });

globalThis.addEventListener = () => {};
const STATIC = path.join(ROOT, "daedalus-server/src/main/resources/static");
require(path.join(STATIC, "controllers/daedalus-pad.js"));
require(path.join(STATIC, "settings/daedalus-settings.js"));
const schema = JSON.parse(fs.readFileSync(path.join(ROOT, "data/settings/settings-schema.json"), "utf8"));
let n = 0, bad = 0;
const check = (name, ok, info) => { n++; if (!ok) bad++; console.log((ok ? "ok   " : "FAIL ") + name + (info !== undefined ? "  " + JSON.stringify(info) : "")); };
const near = (a, b, e = 1e-3) => Math.abs(a - b) < e;

// settings store
const S = DaedalusSettings.create({ schema });
check("console tab order", JSON.stringify(S.tabs()) === JSON.stringify(["CONTROLLER", "KEYBOARD/MOUSE", "VIDEO", "AUDIO", "GAMEPLAY", "ACCESSIBILITY"]), S.tabs());
check("native defaults kept (LeftDeadzone 15, FOV 80, LookSensH 5)", S.get("LeftDeadzone") === 15 && S.get("FieldOfView") === 80 && S.get("LookSensH") === 5);
check("audio defaults reuse data/settings/defaults.json (Main 80, Music 60, Effects 80)", S.get("MainVolume") === 80 && S.get("MusicVolume") === 60 && S.get("EffectsVolume") === 80);
check("slider clamps and snaps", S.set("LeftDeadzone", 99) && S.get("LeftDeadzone") === 40 && S.set("LookSensH", 7.26) && near(S.get("LookSensH"), 7.5));
check("choice wraps", S.nudge("ButtonLayout", -1) && S.choice("ButtonLayout") === "RECON");
check("saved flat {Id: number}, native format", JSON.parse(store["daedalus.settings"]).ButtonLayout === 5);
let seen = []; S.on("MusicVolume", v => seen.push(v)); S.set("MusicVolume", 35);
check("on(id) fires with the current value then changes", seen.join(",") === "60,35", seen);
S.resetTab("CONTROLLER");
check("reset tab restores Controller defaults only", S.get("LeftDeadzone") === 15 && S.choice("ButtonLayout") === "DEFAULT" && S.get("MusicVolume") === 35);
const ex = S.export(); const S2 = DaedalusSettings.create({ schema, storageKey: "other" }); S2.import(ex);
check("export / import round trip", JSON.stringify(S2.export()) === JSON.stringify(ex));
check("format", S.format("FieldOfView") === "80°" && S.format("Vibration") === "ON" && S.format("NotificationDuration") === "5 s", [S.format("FieldOfView"), S.format("NotificationDuration")]);

// pad shaping with settings
const P = DaedalusPad.create({ settings: S, sampleMs: 0 });
const gp = (axes, buttons = []) => ({ index: 0, id: "Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)", mapping: "standard", connected: true,
  axes, buttons: Array.from({ length: 17 }, (_, i) => ({ pressed: (buttons[i] || 0) > 0.5, value: buttons[i] || 0 })) });
const at = (axes, buttons) => { pads[0] = gp(axes, buttons); P.poll(); return P.axes(0); };
let a = at([0.1, -0.6, 0, 0]);
check("radial dead zone keeps a slight diagonal (cross dead zone would drop x=0.10)", a.lx > 0.05 && a.ly < -0.5, a);
a = at([0.1, 0.05, 0, 0]);
check("inside the 15% center dead zone reads zero", a.lx === 0 && a.ly === 0);
a = at([1, 0, 0, 0]);
check("full deflection still reaches 1", near(a.lx, 1));
S.set("LeftMaxInput", 80); a = at([0.8, 0, 0, 0]);
check("max input threshold 80%: 0.8 reads as full", near(a.lx, 1), a.lx);
S.set("LeftMaxInput", 100); S.set("LeftAxialDeadzone", 10); a = at([0.05, 0.9, 0, 0]);
check("axial dead zone drops small sideways drift", a.lx === 0 && a.ly > 0.8, a);
S.set("LeftAxialDeadzone", 0);
a = at([0, 0, 0, 0], { 6: 0.04, 7: 0.95 });
check("triggers: inner 5% ignores a resting 0.04; outer 95% makes 0.95 full", a.lt === 0 && near(a.rt, 1), [a.lt, a.rt]);
S.set("TriggerOuterDeadzone", 60); a = at([0, 0, 0, 0], { 7: 0.6 });
check("short-throw trigger stops: outer 60% makes 0.6 full and pressed", near(a.rt, 1) && P.held("zr"));
S.resetTab("CONTROLLER");

// layouts from the native tables
at([0, 0, 0, 0], { 0: 1 });
check("Default: A jumps", P.heroHeld("Jump"));
S.set("ButtonLayout", 1); at([0, 0, 0, 0], { 4: 1 });
check("Bumper Jumper: LB jumps, A does not", P.heroHeld("Jump") && (at([0, 0, 0, 0], { 0: 1 }), !P.heroHeld("Jump")));
check("Bumper Jumper: A is Shoulder swap", P.heroHeld("Shoulder"));
S.set("ButtonLayout", 5); at([0, 0, 0, 0], { 3: 1 });
check("Recon: Y melees", P.heroHeld("Melee"));
S.set("ThumbstickLayout", 1); at([0, 0, 0.9, -0.9]);
const mv = P.move(0), lk = P.look(0);
check("Southpaw: the right stick moves", mv.x > 0.6 && mv.y > 0.6 && lk.x === 0, { mv, lk });
S.set("ThumbstickLayout", 2); at([0.9, -0.9, 0, 0]);
check("Legacy: left stick Y moves forward, left X turns", P.move(0).y > 0.6 && P.move(0).x === 0 && P.look(0).x > 0.6);
S.resetTab("CONTROLLER");

// confirm button row drives the pad
pads[0] = { index: 0, id: "Pro Controller (STANDARD GAMEPAD Vendor: 057e Product: 2009)", mapping: "standard", connected: true, axes: [0, 0, 0, 0],
  buttons: Array.from({ length: 18 }, (_, i) => ({ pressed: i === 1, value: i === 1 ? 1 : 0 })) };
P.poll();
check("By Label: Switch A (east) confirms", P.held("confirm"));
S.set("ConfirmButton", 1); P.poll();
check("Bottom: Switch east is now back", !P.held("confirm") && P.held("cancel"));
let rumbled = 0; pads[0].vibrationActuator = { playEffect: (t, o) => { rumbled = o.strongMagnitude; return Promise.resolve(); } };
S.set("VibrationStrength", 50); P.rumble(0.8, 100);
check("vibration strength scales rumble", near(rumbled, 0.4), rumbled);
S.set("Vibration", 0); rumbled = 0; P.rumble(0.8, 100);
check("vibration off: no rumble", rumbled === 0);
console.log("SETTINGS " + (n - bad) + "/" + n + (bad ? " FAIL" : " PASS"));
process.exit(bad ? 1 : 0);
