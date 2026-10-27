// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/input_lifecycle_test.js
// DOM-free consumer checks: production functions/callbacks, tiny DOM/device peers.
// The shared pad module, complete game IIFE, browser, assets and native runtime are not executed.
// The pad peer models only the inspected synchronous UP/cancel callbacks and neutral-after-reset contract.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const source = [
  between("const LOGICAL =", "/* ---------- controllers:"),
  between("const SETTINGS =", "/* A small notice"),
  between("function openSettings()", "/* This demo's own rows"),
  between("function fieldTick(", "function land()"),
  between("function fishTick(", "function drawFishLog()"),
  between("function battleTick(", "function advanceChooser()"),
  between("function statusPill(", "/* ---------- title:"),
  between('cv.addEventListener("pointerdown", e => {                 /* tap or click a title item */', "/* ---------- name entry"),
  between('cv.addEventListener("pointerdown", e => {\n  if (mode !== "name"', "/* ---------- ending ---------- */"),
  between("function endingTick(", "function drawEnding()"),
  between("function gameOverTick(", "function drawGameOver()"),
  between("function frame(now)", "/* ---------- harness hooks"),
  between('window.addEventListener("keydown", e => {\n  if (!PANEL', "\nboot();"),
  "this.api = { frame, setHeld, hit, resetGameplayInput, blocked: gameplayInputBlocked, " +
    "inputs: () => ({ held, pressed, pressedAt, SRC, repeatAt, codes: Array.from(keyboardCodes) }), " +
    "last: () => last, paused: () => settingsFramePaused };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(production = source, options = {}) {
  const events = {}, docEvents = {}, pointers = [], buttons = {}, devices = new Map();
  const stats = { raf: 0, polls: 0, audio: 0, draws: 0, focus: 0, resets: 0, edgeClears: 0, cancels: 0, up: 0,
    interactions: 0, steps: 0, actions: 0, titleChoices: 0, nameChoices: 0, nameFinishes: 0, saves: 0, ticks: {}, sfx: [], toasts: [] };
  let panelOpen = false, panelOptions, padOptions, teaching = null;
  const aggregate = {}, edges = {}, ups = {};
  function makeButton(key) {
    const callbacks = {}, classes = new Set();
    return buttons[key] = { dataset: { k: key }, callbacks, classes,
      classList: { add: k => classes.add(k), remove: k => classes.delete(k) },
      addEventListener: (type, fn) => { callbacks[type] = fn; } };
  }
  function add(target, type, fn, capture) { (target[type] ||= []).push({ fn, capture: !!capture }); }
  function fire(target, type, extra = {}) {
    let stopped = false;
    const e = { code: "", key: "", repeat: false, ctrlKey: false, metaKey: false, altKey: false,
      preventDefault() {}, stopImmediatePropagation() { stopped = true; }, ...extra };
    for (const entry of [...(target[type] || [])].sort((a, b) => Number(b.capture) - Number(a.capture))) {
      if (stopped) break; entry.fn(e);
    }
  }
  function emit(e) { padOptions.onChange(e); }
  function merge() {
    const desired = new Set();
    for (const device of devices.values()) {
      if (device.suppressed && !device.physical.size) device.suppressed = false;
      if (!device.suppressed) for (const action of device.physical) desired.add(action);
    }
    for (const action of ["up", "down", "left", "right", "confirm", "cancel", "menu", "select"]) {
      const down = desired.has(action);
      if (down !== !!aggregate[action]) {
        if (down) edges[action] = true; else { ups[action] = true; stats.up++; }
        emit({ type: down ? "down" : "up", action }); // shared merge emits before assigning held
        aggregate[action] = down;
      }
    }
  }
  const pad = {
    poll() { stats.polls++; if (c.onPoll) c.onPoll(); }, binding: () => teaching,
    releaseAll() { stats.resets++; for (const d of devices.values()) d.suppressed = true; merge(); },
    clearEdges() { stats.edgeClears++; for (const k of Object.keys(edges)) edges[k] = false; for (const k of Object.keys(ups)) ups[k] = false; },
    cancelBind() { if (!teaching) return; stats.cancels++; teaching = null; emit({ type: "bindcancel" }); }
  };
  const panel = { isOpen: () => panelOpen,
    open() { panelOpen = true; panelOptions.onOpen(); }, close() { panelOpen = false; panelOptions.onClose(); } };
  const settingsModule = { create: () => ({ on() {} }), mountPanel: opts => { panelOptions = opts; return panel; } };
  const padModule = { create: opts => { padOptions = opts; return pad; } };
  const tick = (mode, dt) => { stats.ticks[mode] = (stats.ticks[mode] || 0) + 1; c.elapsed += dt || 0; };
  const c = {
    now: 1000, elapsed: 0, mode: "field", dlg: null, fade: 0, fadeCb: null, poisonFlash: 0.2, titleT: 0,
    nameEntry: { name: "CORIN", t: 0 }, ending: { t: 0.5, saved: true }, goT: 0, goIdx: -1, titleIdx: 0,
    TITLE_ITEMS: ["NEW GAME", "CONTINUE", "OPTIONS"], W: 320, H: 224, T: 16, AIR_SPEED: 2,
    P: { x: 2, y: 1, fx: 16, fy: 16, dir: "right", moving: 0.4, step: 0 },
    DIRS: { right: [1, 0], left: [-1, 0], up: [0, -1], down: [0, 1] },
    map: { cue: "FIELD", walk: () => true }, state: { fish: {} }, bag: {}, party: [],
    D: { fish: [], rects: { backdrops: {}, spells: {} }, title: {
      menu_geometry: { item_y: 10, item_step: 20, window: [0, 0, 200, 160] }, name_entry: { grid: [["A"]] } } },
    B: { phase: "act", t: 0, wait: 0.01, queue: [{ kind: "foe" }], pops: [{ t: 0.1, x: 1, y: 1, txt: "1" }],
      msg: "Waiting", sub: null, foes: [{ key: "slime", hp: 10, size: 56, x: 20, y: 20 }], flash: { slime20: 0.2 } },
    fishing: { phase: "bite", t: 0.27, fish: { name: "Pond Carp", window_s: 0.3, rarity: "COMMON" }, msg: "!" },
    performance: { now: () => c.now }, requestAnimationFrame: () => { stats.raf++; },
    window: { DaedalusSettings: options.settings === false ? null : settingsModule,
      DaedalusPad: options.pad === false ? null : padModule,
      addEventListener: (type, fn, capture) => add(events, type, fn, capture) },
    document: { hidden: false, hasFocus: () => options.focus !== false,
      addEventListener: (type, fn, capture) => add(docEvents, type, fn, capture),
      querySelectorAll: () => ["up", "down", "left", "right", "a", "b", "start", "opts"].map(makeButton) },
    touchEl: { querySelectorAll: () => Object.values(buttons).filter(b => b.classes.has("held")) },
    cv: { addEventListener: (type, fn) => { if (type === "pointerdown") pointers.push(fn); },
      focus: () => { stats.focus++; }, getBoundingClientRect: () => ({ left: 0, top: 0, width: 320, height: 224 }) },
    DaedalusSettings: settingsModule, DaedalusPad: padModule,
    unlockAudio() {}, sfx: event => stats.sfx.push(event), toast: (...args) => stats.toasts.push(args), applyAudio() {},
    flying: () => false, land() {}, at: () => "Floor", npcAt: () => null,
    interact: () => { stats.interactions++; }, stepDone: () => { stats.steps++; }, dialogTick: dt => tick("dialog", dt),
    titleTick: dt => tick("title", dt), nameTick: dt => tick("name", dt),
    menuTick: () => tick("menu", 0), shopTick: () => tick("shop", 0),
    openMenu: () => { c.mode = "menu"; }, endFish: () => { c.mode = "field"; }, pickFish: () => c.fishing.fish,
    doAction: () => { stats.actions++; }, endRound: () => { stats.ticks.round = (stats.ticks.round || 0) + 1; },
    // This lifecycle fixture has no saved record; recovery/reader integration has its own focused check.
    readSavedJourney: () => ({ ok: false, kind: "missing" }),
    titleChoose: () => { stats.titleChoices++; }, nameAt: () => [0, 0], neActivate: () => { stats.nameChoices++; },
    neType: () => { stats.nameChoices++; }, neFinish: () => { stats.nameFinishes++; }, neDelete: () => true, neBack() {},
    saveGame: () => { stats.saves++; return true; }, cue() {}, say() {},
    drawTitle: () => { stats.draws++; }, drawName: () => { stats.draws++; }, drawEnding: () => { stats.draws++; },
    drawField: () => { stats.draws++; }, drawMenu: () => { stats.draws++; }, drawShop: () => { stats.draws++; },
    drawFish: () => { stats.draws++; }, drawGameOver: () => { stats.draws++; }, drawDialog() {},
    jukeTick: () => { stats.audio++; }, g: { fillStyle: "", fillRect: () => { stats.draws++; }, drawImage() {} },
    IM: {}, tags: () => [], spr() {}, cursor() {}, gauge() {}, win() {}, wrap: s => [s], text() {}, tw: s => String(s).length * 6
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  return { c, stats, api: c.api, panel, buttons, edges, ups,
    step(ms = 16) { c.now += ms; c.api.frame(c.now); },
    key(code, up = false, extra = {}) { const key = { KeyZ: "z", KeyX: "x", KeyA: "a", Space: " " }[code] || code; fire(events, up ? "keyup" : "keydown", { code, key, ...extra }); },
    touch(key, type = "pointerdown") { buttons[key].callbacks[type]({ preventDefault() {} }); },
    pointer() { for (const fn of pointers) fn({ clientX: 10, clientY: 10 }); },
    blur() { fire(events, "blur"); }, focus() { fire(events, "focus"); },
    hidden(value) { c.document.hidden = value; fire(docEvents, "visibilitychange"); },
    device(id, action, down = true) { if (!devices.has(id)) devices.set(id, { physical: new Set(), suppressed: false }); const d = devices.get(id); if (down) d.physical.add(action); else d.physical.delete(action); merge(); },
    disconnect(id) { devices.delete(id); emit({ type: "disconnect", pad: { name: id } }); merge(); },
    beginBind() { teaching = { step: 0 }; emit({ type: "bind", step: null }); },
    bindStep() { teaching.step++; emit({ type: "bind", step: "confirm" }); },
    completeBind() { teaching = null; emit({ type: "bound", pad: { name: "Test Pad" } }); },
    cancelBind() { pad.cancelBind(); }, binding: () => teaching,
    rawPad(action, type) { emit({ type, action }); }
  };
}
function cleared(s) {
  const input = s.api.inputs();
  for (const k of ["up", "down", "left", "right", "a", "b", "start"]) {
    assert.equal(!!input.held[k], false, "no held " + k); assert.equal(!!input.pressed[k], false, "no buffered " + k);
    assert.equal(input.pressedAt[k], undefined, "no timestamp " + k); assert.equal(input.repeatAt[k], undefined, "no repeat " + k);
    for (const src of Object.values(input.SRC)) assert.equal(!!src[k], false, "no source contribution " + k);
  }
  assert.equal(input.codes.length, 0); for (const b of Object.values(s.buttons)) assert.equal(b.classes.has("held"), false);
  assert.ok(Object.values(s.edges).every(v => !v)); assert.ok(Object.values(s.ups).every(v => !v));
}
function state(s) { return JSON.stringify({ mode: s.c.mode, P: s.c.P, fish: s.c.fishing, B: s.c.B, ending: s.c.ending,
  goT: s.c.goT, goIdx: s.c.goIdx, name: s.c.nameEntry, fade: s.c.fade, poison: s.c.poisonFlash, bag: s.c.bag, elapsed: s.c.elapsed }); }
const pauses = {
  blur: { stop: s => s.blur(), resume: s => s.focus() },
  hidden: { stop: s => s.hidden(true), resume: s => s.hidden(false) },
  binding: { stop: s => s.beginBind(), resume: s => s.cancelBind() },
  settings: { stop: s => s.panel.open(), resume: s => s.panel.close() }
};
function aliasInvariant(production = source) {
  for (const [first, second, logical] of [["KeyW", "ArrowUp", "up"], ["KeyZ", "Space", "a"], ["KeyX", "Escape", "b"]]) {
    for (const releaseFirst of [first, second]) {
      const s = session(production); s.key(first); s.api.hit(logical); s.key(second);
      assert.equal(s.api.hit(logical), false, "overlapping alias is no new press"); s.key(releaseFirst, true);
      assert.equal(s.api.inputs().held[logical], true, "one alias still holds");
      s.key(releaseFirst === first ? second : first, true); assert.equal(s.api.inputs().held[logical], false);
      s.key(first); assert.equal(s.api.hit(logical), true, "released/new key presses normally");
    }
  }
}
function hiddenFishInvariant(production = source) {
  const s = session(production); s.c.mode = "fish"; s.hidden(true); const before = state(s);
  s.step(5000); assert.equal(state(s), before, "hidden live bite remains frozen");
}
check("complete inline source compiles without running the game", () => {
  const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
});
check("physical keyboard aliases aggregate and release in either order", () => aliasInvariant());
check("keyboard, touch and two pads preserve independent contributions", () => {
  const s = session(); s.key("ArrowUp"); s.touch("up"); s.device("one", "up"); s.device("two", "up");
  s.key("ArrowUp", true); s.device("one", "up", false); assert.equal(s.api.inputs().held.up, true);
  s.touch("up", "pointerup"); assert.equal(s.api.inputs().held.up, true); s.device("two", "up", false);
  assert.equal(s.api.inputs().held.up, false);
});
check("repeat key events cannot manufacture a fresh physical press", () => {
  const s = session(); s.key("KeyZ"); assert.equal(s.api.hit("a"), true); s.key("KeyZ", false, { repeat: true }); assert.equal(s.api.hit("a"), false);
  s.blur(); s.focus(); s.step(); s.key("KeyZ", false, { repeat: true }); assert.equal(!!s.api.inputs().held.a, false);
  s.key("KeyZ"); assert.equal(s.api.hit("a"), true);
});
check("blur resets aliases, every edge/timestamp/repeat, touch paint and synchronous pad UP", () => {
  const s = session(); s.key("KeyW"); s.key("ArrowUp"); s.touch("a"); s.device("one", "confirm");
  for (const k of ["up", "down", "left", "right", "a", "b", "start"]) s.api.setHeld("test", k, true);
  s.blur(); cleared(s); assert.equal(s.stats.resets, 1); assert.equal(s.stats.edgeClears, 1); assert.ok(s.stats.up > 0);
});
check("blocked keyboard/touch/pad downs are ignored and all releases still flow", () => {
  for (const pause of Object.values(pauses)) {
    const s = session(); pause.stop(s); s.key("KeyZ"); s.touch("a"); s.rawPad("confirm", "down"); cleared(s);
  }
  const s = session(); s.key("ArrowUp"); s.touch("a"); s.device("one", "right");
  s.c.document.hidden = true; // release arrives before the visibility callback
  s.key("ArrowUp", true); s.touch("a", "pointercancel"); s.device("one", "right", false);
  assert.equal(s.api.inputs().held.up, false); assert.equal(s.api.inputs().held.a, false); assert.equal(s.api.inputs().held.right, false);
});
for (const [reason, pause] of Object.entries(pauses)) {
  check(reason + " freezes every existing mode while polling, rendering and audio dispatch continue", () => {
    for (const mode of ["title", "name", "ending", "field", "menu", "shop", "fish", "battle", "gameover"]) {
      const s = session(); s.c.mode = mode; pause.stop(s); const before = state(s);
      s.step(1000); s.step(5000); assert.equal(state(s), before, mode); assert.equal(Object.keys(s.stats.ticks).length, 0);
      assert.equal(s.stats.actions, 0); assert.equal(s.stats.polls, 2); assert.equal(s.stats.raf, 2); assert.equal(s.stats.audio, 2); assert.ok(s.stats.draws >= 2);
      assert.equal(s.api.last(), s.c.now); assert.equal(!!s.api.paused(), true);
    }
  });
  check(reason + " freezes fade callbacks and resumes without elapsed-time catch-up", () => {
    const s = session(); let calls = 0; s.c.fade = 0.55; s.c.fadeCb = () => { calls++; }; pause.stop(s);
    s.step(5000); assert.equal(s.c.fade, 0.55); assert.equal(calls, 0); pause.resume(s); s.step(5000);
    assert.equal(s.c.fade, 0.55); assert.equal(calls, 0); s.step(16); assert.ok(Math.abs(s.c.fade - 0.502) < 1e-12);
    s.step(16); assert.equal(calls, 1); assert.equal(s.c.fadeCb, null);
  });
}
check("real field movement and live fishing resume at their prior progress", () => {
  const s = session(); s.blur(); s.step(10000); s.focus(); s.step(10000); assert.equal(s.c.P.moving, 0.4);
  s.step(16); assert.ok(Math.abs(s.c.P.moving - 0.28) < 1e-12);
  const f = session(); f.c.mode = "fish"; f.hidden(true); f.step(10000); f.hidden(false); f.step(10000);
  assert.equal(f.c.fishing.t, 0.27); f.step(16); assert.equal(f.c.fishing.phase, "bite");
  assert.ok(Math.abs(f.c.fishing.t - 0.286) < 1e-12); f.step(16); assert.equal(f.c.fishing.phase, "done");
});
check("real battle queue, animation and render-side flashes resume only after the boundary frame", () => {
  const s = session(); s.c.mode = "battle"; s.beginBind(); s.step(10000); const before = state(s); s.cancelBind(); s.step(10000);
  assert.equal(state(s), before); s.step(16); assert.equal(s.stats.actions, 0); assert.equal(s.c.B.queue.length, 1);
  assert.equal(s.c.B.flash.slime20, 0.2 - 1 / 60); s.step(16); assert.equal(s.stats.actions, 1); assert.equal(s.c.B.queue.length, 0);
});
check("ending state stays live and stale confirm cannot return to title", () => {
  const s = session(); s.c.mode = "ending"; s.c.ending.t = 3.1; s.key("KeyZ"); s.blur(); s.step(5000); s.focus(); s.step(5000); s.step(16);
  assert.equal(s.c.mode, "ending"); assert.ok(s.c.ending.t < 3.12); s.key("KeyZ"); s.step(16); assert.equal(s.c.mode, "title"); assert.equal(s.stats.saves, 0);
});
check("binding starts/steps/completes without recursive cancellation and requires neutral before fresh pad play", () => {
  const s = session(); s.device("one", "confirm"); s.beginBind(); cleared(s); const resets = s.stats.resets;
  s.bindStep(); assert.equal(s.stats.resets, resets); assert.ok(s.stats.sfx.includes("TICK")); s.completeBind(); cleared(s);
  assert.equal(s.binding(), null); assert.equal(s.stats.cancels, 0); s.c.P.moving = 0; s.step(); s.device("one", "confirm"); s.step(); assert.equal(s.stats.interactions, 0);
  s.device("one", "confirm", false); s.device("one", "confirm"); s.step(); assert.equal(s.stats.interactions, 1);
});
check("Escape, blur, hidden and Settings close cancel unfinished teaching once and clear closing input", () => {
  for (const finish of [s => s.key("Escape"), s => s.blur(), s => s.hidden(true), s => s.panel.close()]) {
    const s = session(); s.panel.open(); s.beginBind(); s.rawPad("confirm", "down"); finish(s);
    assert.equal(s.binding(), null); assert.equal(s.stats.cancels, 1); cleared(s);
  }
});
check("teaching disconnect cancels while an ordinary disconnect preserves keyboard, touch and another pad", () => {
  const teaching = session(); teaching.beginBind(); teaching.disconnect("one"); assert.equal(teaching.stats.cancels, 1); cleared(teaching);
  const s = session(); s.key("ArrowUp"); s.touch("up"); s.device("one", "up"); s.device("two", "up"); const resets = s.stats.resets;
  s.disconnect("one"); assert.equal(s.stats.resets, resets); assert.equal(s.api.inputs().held.up, true); assert.equal(s.buttons.up.classes.has("held"), true);
  s.key("ArrowUp", true); s.touch("up", "pointerleave"); assert.equal(s.api.inputs().held.up, true); s.disconnect("two"); assert.equal(s.api.inputs().held.up, false);
});
check("Settings close during polling retains its one-frame guard and fresh subsequent input works", () => {
  const s = session(); s.c.P.moving = 0; s.panel.open(); s.step();
  s.c.onPoll = () => { s.panel.close(); s.rawPad("confirm", "down"); s.c.onPoll = null; };
  s.step(); assert.equal(s.stats.interactions, 0); assert.equal(!!s.api.paused(), true); cleared(s);
  s.step(); s.key("KeyZ"); s.step(); assert.equal(s.stats.interactions, 1);
});
check("title pointer and direct name typing reject hidden/inactive/binding inputs and accept fresh resumed choices", () => {
  for (const pause of Object.values(pauses)) {
    const s = session(); s.c.mode = "title"; pause.stop(s); s.pointer(); assert.equal(s.stats.titleChoices, 0);
    s.c.mode = "name"; s.pointer(); s.key("Enter"); s.key("KeyA"); assert.equal(s.stats.nameChoices, 0); assert.equal(s.stats.nameFinishes, 0);
    pause.resume(s); s.pointer(); s.key("Enter"); assert.equal(s.stats.nameChoices, 0); assert.equal(s.stats.nameFinishes, 0);
    s.step(); s.pointer(); s.key("Enter"); assert.equal(s.stats.nameChoices, 1); assert.equal(s.stats.nameFinishes, 1);
  }
});
check("initially unfocused pages pause, and absent optional panel/pad modules preserve keyboard gameplay", () => {
  const s = session(source, { focus: false }); const before = state(s); s.step(5000); assert.equal(state(s), before); s.focus(); s.step(); s.step(); assert.ok(s.c.P.moving < 0.4);
  const plain = session(source, { settings: false, pad: false }); plain.c.P.moving = 0; plain.key("KeyZ"); plain.step(); assert.equal(plain.stats.interactions, 1); assert.equal(plain.stats.polls, 0); assert.equal(plain.stats.audio, 1);
});
check("controlled old alias, hidden timer, reset and blocked-release behavior violate the same invariants", () => {
  const aliases = source.replace('if (KEYMAP[e.code]) keyboardHeld(e.code, false);', 'if (KEYMAP[e.code]) setHeld("kb", KEYMAP[e.code], false);');
  assert.notEqual(aliases, source); assert.throws(() => aliasInvariant(aliases), assert.AssertionError);
  const ticking = source.replace('const paused = settingsFramePaused = gameplayInputBlocked();', 'const paused = settingsFramePaused = false;');
  assert.notEqual(ticking, source); assert.throws(() => hiddenFishInvariant(ticking), assert.AssertionError);
  const stale = source.replace('delete pressedAt[k]; delete repeatAt[k];', '/* old timestamps remain */');
  assert.notEqual(stale, source); assert.throws(() => { const s = session(stale); s.key("KeyZ"); s.blur(); cleared(s); }, assert.AssertionError);
  const droppedUp = source.replace('if (e.type === "down" && gameplayInputBlocked())', 'if (gameplayInputBlocked())');
  assert.notEqual(droppedUp, source); assert.throws(() => { const s = session(droppedUp); s.device("one", "right"); s.c.document.hidden = true; s.device("one", "right", false); assert.equal(s.api.inputs().held.right, false); }, assert.AssertionError);
});
console.log("input lifecycle: " + checks + " focused groups passed (consumer callbacks with fake DOM/devices; no real-device/runtime acceptance)");
