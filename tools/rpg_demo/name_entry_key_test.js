// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/name_entry_key_test.js
// Actual capture/bubble listeners, title choice/fade, name functions and metadata; no browser/game loop/storage.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const party = data("party").party.prism, title = data("title").realms.prism;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [between("const LOGICAL =", "document.querySelectorAll"), line("const hit ="),
  line("let journeySerial ="),
  between("const START_LEVEL =", "/* Recruits:"), between("function titleChoose(", "function beginJourney("),
  between("function titleTick(", "function titlePrompt("), between("let nameEntry = null;", "/* ---------- ending ---------- */"),
  "function fadeStep(dt) {\n" + between("      fade -= dt * 3;", '    } else if (mode === "title")') + "\n}",
  "function frameCleanup(now) {\n" + between("  for (const k in pressed)", '  if (mode === "title") drawTitle();') + "\n}",
  "this.api = { titleTick, nameTick, fadeStep, frameCleanup, setHeld, entry: () => nameEntry, " +
  "party: () => party, input: () => ({ held, pressed, SRC }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function surface() {
  const handlers = {};
  return { handlers, addEventListener(type, fn, capture = false) { (handlers[type] ||= []).push({ fn, capture: !!capture }); } };
}
function session(productionSource = source) {
  const win = surface(), cv = surface(), sounds = [], c = {
    D: { title: clone(title), party: clone(party), gear: {} }, W: 320, H: 224,
    window: win, cv, mode: "title", titleT: 0, titleIdx: 0, TITLE_ITEMS: clone(title.menu),
    state: { beaten: new Set() }, opened: new Set(), grids: {}, fade: 0, fadeCb: null,
    dlg: null, shop: null, menu: null, B: null, ending: null,
    now: 0, started: 0, settingsTransition: false, modal: false,
    PANEL: { isOpen: () => c.modal }, PAD: { binding: () => null },
    performance: { now: () => c.now }, sfx: sound => sounds.push(sound), unlockAudio() {},
    beginJourney: () => { c.started++; } // Journey/navigation is the observed downstream seam, not executed here.
  };
  cv.getBoundingClientRect = () => ({ left: 0, top: 0, width: c.W, height: c.H });
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  function dispatch(target, type, fields) {
    const event = { repeat: false, ctrlKey: false, metaKey: false, altKey: false, prevented: false, stopped: false,
      preventDefault() { this.prevented = true; }, stopImmediatePropagation() { this.stopped = true; }, ...fields };
    const registered = target.handlers[type] || [];
    for (const handler of registered.filter(h => h.capture).concat(registered.filter(h => !h.capture))) {
      if (event.stopped) break; handler.fn(event);
    }
    return event;
  }
  return { c, sounds, api: c.api,
    key: (key, code, extra = {}) => dispatch(win, "keydown", { key, code, ...extra }),
    up: (key = "Enter", code = "Enter") => dispatch(win, "keyup", { key, code }),
    pointer: (x, y) => dispatch(cv, "pointerdown", { clientX: x, clientY: y }),
    fade: dt => { c.now += dt * 1000; c.api.fadeStep(dt); c.api.frameCleanup(c.now); } };
}
function naming(productionSource = source) {
  const s = session(productionSource); s.key("Enter", "Enter");
  assert.equal(s.api.input().held.start, true); s.api.titleTick(1 / 60);
  assert.equal(s.c.fade, 1); assert.equal(s.c.mode, "title");
  s.fade(0.2); assert.equal(s.c.mode, "name"); s.fade(0.2);
  assert.equal(s.c.fade, 0); assert.equal(s.api.entry().name, party.members[0].name.toUpperCase());
  assert.equal(s.api.input().held.start, true, "the original physical Enter remains held across the fade");
  assert.equal(s.api.input().pressed.start, false, "existing fade cleanup consumed the title edge"); return s;
}
function assertRepeatWaits(productionSource = source) {
  const s = naming(productionSource), original = s.api.entry().name;
  for (let i = 0; i < 3; i++) {
    const event = s.key("Enter", "Enter", { repeat: true });
    assert.ok(event.prevented && event.stopped, "repeat Enter remains consumed by the capture handler");
    assert.equal(s.c.started, 0, "held title Enter cannot accept the name");
    assert.ok(s.api.entry()); assert.equal(s.api.entry().name, original); s.api.nameTick(1 / 60);
  }
  assert.equal(s.c.mode, "name"); assert.equal(s.api.input().pressed.start, false); return s;
}
check("held title Enter and its repeated events retain the naming screen", () => assertRepeatWaits());
check("fresh Enter accepts the default name exactly once", () => {
  const s = assertRepeatWaits(); s.up(); s.key("Enter", "Enter");
  assert.equal(s.api.entry(), null); assert.equal(s.api.party()[0].name, party.members[0].name); assert.equal(s.c.started, 1);
  s.key("Enter", "Enter", { repeat: true }); assert.equal(s.c.started, 1);
});
check("fresh Enter accepts an ordinarily typed name", () => {
  const s = naming(); s.up(); const count = s.api.entry().name.length;
  for (let i = 0; i < count; i++) s.key("Backspace", "Backspace", { repeat: i > 0 });
  for (const letter of "Ada") s.key(letter, "Key" + letter.toUpperCase());
  assert.equal(s.api.entry().name, "ADA"); s.key("Enter", "Enter");
  assert.equal(s.api.party()[0].name, "Ada"); assert.equal(s.c.started, 1);
});
check("repeated letter events keep the existing typing behavior without logical movement", () => {
  const s = naming(), before = s.api.entry().name; s.up();
  s.key("a", "KeyA"); s.key("a", "KeyA", { repeat: true });
  assert.equal(s.api.entry().name, before + "AA"); assert.equal(s.api.input().held.left, undefined); assert.equal(s.c.started, 0);
});
check("Backspace repeats still delete one character each", () => {
  const s = naming(), before = s.api.entry().name; s.up();
  s.key("Backspace", "Backspace"); s.key("Backspace", "Backspace", { repeat: true });
  assert.equal(s.api.entry().name, before.slice(0, -2)); assert.equal(s.c.started, 0);
});
check("space typing is still handled by the existing name capture path", () => {
  const s = naming(), before = s.api.entry().name; s.up(); const event = s.key(" ", "Space", { repeat: true });
  assert.equal(s.api.entry().name, before + " "); assert.ok(event.stopped); assert.equal(s.api.input().pressed.a, undefined);
});
for (const modifier of ["ctrlKey", "metaKey", "altKey"]) check(modifier + " still prevents ordinary letter typing", () => {
  const s = naming(), before = s.api.entry().name; s.up(); s.key("q", "KeyQ", { [modifier]: true });
  assert.equal(s.api.entry().name, before); assert.equal(s.c.started, 0);
});
for (const gate of ["modal", "settingsTransition"]) check(gate + " still gates keyboard and pointer naming", () => {
  const s = naming(), before = s.api.entry().name; s.up(); s.c[gate] = true;
  s.key("Enter", "Enter"); s.key("a", "KeyA"); s.pointer(s.c.W - 50, s.c.H - 27);
  assert.equal(s.api.entry().name, before); assert.equal(s.c.started, 0); assert.equal(s.api.input().held.start, false);
});
check("controller Start still finishes through actual nameTick", () => {
  const s = naming(); s.up(); s.api.setHeld("pad", "start", true); s.api.nameTick(1 / 60);
  assert.equal(s.api.entry(), null); assert.equal(s.c.started, 1); assert.equal(s.api.input().pressed.start, false);
});
check("pointer letter selection and END still use actual name activation", () => {
  const s = naming(), before = s.api.entry().name; s.up(); s.pointer(26, 64);
  assert.equal(s.api.entry().name, before + title.name_entry.grid[0][0]);
  s.pointer(s.c.W - 50, s.c.H - 27); assert.equal(s.api.entry(), null); assert.equal(s.c.started, 1);
});
check("controlled unguarded Enter fails the same title-to-name regression", () => {
  const guarded = '  if (k === "Enter") { stop(); if (!e.repeat) neFinish(); return; }'; assert.ok(source.includes(guarded));
  const legacy = source.replace(guarded, '  if (k === "Enter") { stop(); neFinish(); return; }');
  assert.throws(() => assertRepeatWaits(legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or DOM work.
console.log("Prismheart name entry key checks: " + checks + " passed; full inline script compiles.");
