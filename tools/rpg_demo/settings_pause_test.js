// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/settings_pause_test.js
// Actual frame, modal callbacks, input handlers, fishing/movement and battle drawing.
// No browser, game loop scheduling, storage, assets, builds or native runtime is launched.
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
  between("function fieldTick(", "function land()"),
  between("function fishTick(", "function drawFishLog()"),
  between("function drawBattle()", "/* ---------- title:"),
  between('cv.addEventListener("pointerdown", e => {                 /* tap or click a title item */', "/* ---------- name entry"),
  between('cv.addEventListener("pointerdown", e => {\n  if (mode !== "name"', "/* ---------- ending ---------- */"),
  between("function frame(", "/* ---------- harness hooks"),
  "this.api = { frame, setHeld, releaseSource, hit, panel: PANEL, inputs: () => ({ held, pressed, SRC, repeatAt }), " +
  "last: () => last, paused: () => settingsFramePaused };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(productionSource = source, settings = true) {
  const keys = {}, pointers = [], buttons = {}, stats = { raf: 0, polls: 0, audio: 0, draws: 0, focus: 0, interactions: 0, steps: 0, titleChoices: 0, nameChoices: 0, nameFinishes: 0, ticks: {} };
  let panelOpen = false, panelOptions, padOptions;
  const makeButton = key => {
    const callbacks = {}, classes = new Set();
    return buttons[key] = { dataset: { k: key }, callbacks, classes,
      classList: { add: value => classes.add(value), remove: value => classes.delete(value) },
      addEventListener: (event, fn) => { callbacks[event] = fn; } };
  };
  const tick = (mode, dt) => { stats.ticks[mode] = (stats.ticks[mode] || 0) + 1; c.elapsed += dt || 0; };
  const panel = { isOpen: () => panelOpen,
    open: () => { panelOpen = true; panelOptions.onOpen(); },
    close: () => { panelOpen = false; panelOptions.onClose(); } };
  const pad = { poll: () => { stats.polls++; if (c.onPoll) c.onPoll(); }, binding: () => false, releaseAll() {}, clearEdges() {} };
  const settingsModule = { create: () => ({ on() {} }), mountPanel: options => { panelOptions = options; return panel; } };
  const padModule = { create: options => { padOptions = options; return pad; } };
  const c = {
    now: 0, elapsed: 0, mode: "field", dlg: null, fade: 0, fadeCb: null, poisonFlash: 0.2,
    nameEntry: { name: "CORIN", t: 0 }, ending: { t: 0 }, goT: 0, titleIdx: 0, TITLE_ITEMS: ["NEW GAME", "CONTINUE", "OPTIONS"],
    W: 320, H: 224, T: 16, AIR_SPEED: 2,
    P: { x: 1, y: 1, fx: 16, fy: 16, dir: "right", moving: 0, step: 0 },
    DIRS: { right: [1, 0], left: [-1, 0], up: [0, -1], down: [0, 1] },
    map: { walk: () => true }, state: { fish: {} }, bag: {}, party: [],
    D: { fish: [], rects: { backdrops: {}, spells: {} }, title: {
      menu_geometry: { item_y: 10, item_step: 20, window: [0, 0, 200, 160] }, name_entry: { grid: [["A"]] } } },
    B: { phase: "exec", t: 0, wait: 0.4, queue: ["foe turn"], pops: [], msg: "Waiting", sub: null,
      foes: [{ key: "slime", hp: 10, size: 56, x: 20, y: 20 }], flash: { slime20: 0.2 } },
    fishing: { phase: "bite", t: 0.27, fish: { name: "Pond Carp", window_s: 0.3, rarity: "COMMON" }, msg: "!" },
    performance: { now: () => c.now }, requestAnimationFrame: () => { stats.raf++; },
    window: { DaedalusSettings: settings ? settingsModule : null, DaedalusPad: padModule,
      addEventListener: (event, fn) => { (keys[event] ||= []).push(fn); } },
    document: { hidden: false, hasFocus: () => true, addEventListener() {}, querySelectorAll: () => ["up", "a", "start", "opts"].map(makeButton) },
    touchEl: { querySelectorAll: () => Object.values(buttons).filter(b => b.classes.has("held")) },
    cv: { addEventListener: (event, fn) => { if (event === "pointerdown") pointers.push(fn); },
      focus: () => { stats.focus++; }, getBoundingClientRect: () => ({ left: 0, top: 0, width: 320, height: 224 }) },
    DaedalusSettings: settingsModule, DaedalusPad: padModule,
    unlockAudio() {}, openSettings: () => panel.open(), sfx() {}, toast() {}, applyAudio() {}, fit() {},
    flying: () => false, land() {}, at: () => "Floor", npcAt: () => null,
    interact: () => { stats.interactions++; }, stepDone: () => { stats.steps++; }, dialogTick() {},
    titleTick: dt => tick("title", dt), nameTick: dt => tick("name", dt), endingTick: dt => tick("ending", dt),
    menuTick: () => tick("menu", 0), shopTick: () => tick("shop", 0), gameOverTick: dt => tick("gameover", dt),
    battleTick: dt => { tick("battle", dt); c.B.wait -= dt; if (c.B.wait <= 0) c.B.queue.shift(); },
    openMenu: () => { c.mode = "menu"; }, endFish: () => { c.mode = "field"; }, pickFish: () => c.fishing.fish,
    titleChoose: () => { stats.titleChoices++; }, nameAt: () => [0, 0], neActivate: () => { stats.nameChoices++; },
    neType: () => { stats.nameChoices++; }, neFinish: () => { stats.nameFinishes++; }, neDelete: () => true, neBack() {},
    drawTitle: () => { stats.draws++; }, drawName: () => { stats.draws++; }, drawEnding: () => { stats.draws++; },
    drawField: () => { stats.draws++; }, drawMenu: () => { stats.draws++; }, drawShop: () => { stats.draws++; },
    drawFish: () => { stats.draws++; }, drawGameOver: () => { stats.draws++; }, drawDialog() {},
    jukeTick: () => { stats.audio++; }, g: { fillStyle: "", fillRect: () => { stats.draws++; }, drawImage() {} },
    IM: {}, tags: () => [], spr() {}, cursor() {}, gauge() {}, win() {}, wrap: s => [s], text() {}, tw: s => String(s).length * 6,
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  const event = extra => ({ preventDefault() {}, stopImmediatePropagation() {}, ctrlKey: false, metaKey: false, altKey: false, repeat: false, ...extra });
  return { c, stats, api: c.api, panel, buttons,
    step: ms => { c.now += ms; c.api.frame(c.now); },
    key: (code, key, up = false) => (keys[up ? "keyup" : "keydown"] || []).forEach(fn => fn(event({ code, key }))),
    touch: (key, up = false) => buttons[key].callbacks[up ? "pointerup" : "pointerdown"](event({})),
    pointer: () => pointers.forEach(fn => fn(event({ clientX: 10, clientY: 10 }))),
    pad: (action, type = "down") => padOptions.onChange({ type, action }),
  };
}
function frozenState(s) {
  return JSON.stringify({ P: s.c.P, fish: s.c.fishing, battle: s.c.B, fade: s.c.fade,
    poison: s.c.poisonFlash, elapsed: s.c.elapsed, name: s.c.nameEntry, ending: s.c.ending, goT: s.c.goT });
}
function allReleased(s) {
  const input = s.api.inputs();
  for (const key of ["up", "down", "left", "right", "a", "b", "start"]) {
    assert.equal(!!input.held[key], false, "no held " + key); assert.equal(!!input.pressed[key], false, "no buffered " + key);
  }
  assert.equal(Object.keys(input.SRC).length, 0);
}
function pausedFish(productionSource = source) {
  const s = session(productionSource); s.c.mode = "fish"; s.panel.open();
  const before = frozenState(s); s.step(1000); s.step(1000);
  assert.equal(frozenState(s), before, "an open panel cannot cost the live bite or advance simulation"); return s;
}
check("complete production inline script compiles without executing the game", () => {
  const script = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(script);
  new vm.Script(script[1], { filename: "index.html inline script" });
});
for (const mode of ["title", "name", "ending", "field", "menu", "shop", "fish", "battle", "gameover"]) {
  check(mode + ": all simulation freezes while rendering, audio and controller polling continue", () => {
    const s = session(); s.c.mode = mode; s.panel.open();
    const before = frozenState(s);
    s.step(1000); s.step(4000);
    assert.equal(frozenState(s), before); assert.equal(s.stats.ticks[mode] || 0, 0);
    assert.ok(s.stats.draws >= 2); assert.equal(s.stats.audio, 2); assert.equal(s.stats.polls, 2); assert.equal(s.stats.raf, 2);
    assert.equal(s.api.last(), s.c.now); assert.equal(s.api.paused(), true);
  });
}
check("fishing keeps its actual bite deadline and resumes from the same time after closing", () => {
  const s = pausedFish(); s.panel.close(); s.step(1000);
  assert.equal(s.c.fishing.t, 0.27, "closing choice frame is still paused");
  s.step(16); assert.equal(s.c.fishing.phase, "bite"); assert.ok(Math.abs(s.c.fishing.t - 0.286) < 1e-12);
  s.step(16); assert.equal(s.c.fishing.phase, "done", "ordinary bite timer resumes instead of resetting");
});
check("fades and their callbacks remain frozen until the modal has closed", () => {
  const s = session(); s.c.fade = 0.55; let called = 0; s.c.fadeCb = () => { called++; };
  s.panel.open(); s.step(5000); assert.equal(s.c.fade, 0.55); assert.equal(called, 0);
  s.panel.close(); s.step(5000); assert.equal(s.c.fade, 0.55); assert.equal(called, 0);
  s.step(50); assert.ok(s.c.fade < 0.5); assert.equal(called, 1); assert.equal(s.c.fadeCb, null);
});
check("queued battle turns and fixed-step drawing flashes remain frozen", () => {
  const s = session(); s.c.mode = "battle"; s.c.B.wait = 0.01; s.panel.open(); const before = frozenState(s);
  s.step(1000); assert.equal(frozenState(s), before); assert.equal(s.c.B.flash.slime20, 0.2);
  s.panel.close(); s.step(1000); assert.equal(frozenState(s), before);
  s.step(16); assert.equal(s.c.B.queue.length, 0); assert.equal(s.c.B.flash.slime20, 0.2 - 1 / 60);
});
check("both modal callbacks release all sources and flush every buffered logical button", () => {
  const s = session();
  for (const source of ["kb", "pad", "touch"]) for (const key of ["up", "down", "left", "right", "a", "b", "start"]) s.api.setHeld(source, key, true);
  s.panel.open(); allReleased(s);
  s.api.setHeld("touch", "a", true); s.api.setHeld("pad", "right", true); s.panel.close(); allReleased(s);
  assert.equal(s.stats.focus, 1);
});
check("touch, keyboard and pad gameplay input cannot enter while the modal is open", () => {
  const s = session(); s.panel.open(); s.touch("a"); s.touch("up"); s.key("KeyZ", "z"); s.key("ArrowUp", "ArrowUp"); s.pad("confirm"); s.pad("up");
  allReleased(s); assert.equal(s.buttons.a.classes.has("held"), false); assert.equal(s.buttons.up.classes.has("held"), false);
});
check("modal close choices do not bleed, while released fresh keyboard/touch/pad presses work", () => {
  const s = session(); s.panel.open(); s.step(1000); s.panel.close();
  s.key("KeyZ", "z"); s.touch("a"); s.pad("confirm"); allReleased(s);
  s.step(16); assert.equal(s.stats.interactions, 0);
  s.key("KeyZ", "z"); s.step(16); assert.equal(s.stats.interactions, 1); s.key("KeyZ", "z", true);
  s.touch("a"); s.step(16); assert.equal(s.stats.interactions, 2); s.touch("a", true);
  s.pad("confirm"); s.step(16); assert.equal(s.stats.interactions, 3); s.pad("confirm", "up");
});
check("closing the panel during controller polling cannot leak that closing confirm", () => {
  const s = session(); s.panel.open(); s.step(1000);
  s.c.onPoll = () => { s.panel.close(); s.pad("confirm"); s.c.onPoll = null; };
  s.step(16); assert.equal(s.stats.interactions, 0); assert.equal(s.api.paused(), true); allReleased(s);
  s.step(16); assert.equal(s.stats.interactions, 0); s.pad("confirm"); s.step(16); assert.equal(s.stats.interactions, 1);
});
check("direct title/name pointer and typing handlers also reject modal closing input", () => {
  const s = session(); s.c.mode = "title"; s.panel.open(); s.pointer(); assert.equal(s.stats.titleChoices, 0);
  s.panel.close(); s.pointer(); assert.equal(s.stats.titleChoices, 0); s.step(16); s.pointer(); assert.equal(s.stats.titleChoices, 1);
  s.c.mode = "name"; s.panel.open(); s.pointer(); s.key("Enter", "Enter"); assert.equal(s.stats.nameChoices, 0); assert.equal(s.stats.nameFinishes, 0);
  s.panel.close(); s.pointer(); s.key("Enter", "Enter"); assert.equal(s.stats.nameChoices, 0); assert.equal(s.stats.nameFinishes, 0);
  s.step(16); s.pointer(); s.key("Enter", "Enter"); assert.equal(s.stats.nameChoices, 1); assert.equal(s.stats.nameFinishes, 1);
});
check("closed settings preserve real held field movement, menu input and frame timing", () => {
  const s = session(); s.key("ArrowRight", "ArrowRight"); s.step(16); assert.equal(s.c.P.x, 2); assert.equal(s.c.P.moving, 1);
  s.step(16); assert.ok(s.c.P.moving < 1); s.key("ArrowRight", "ArrowRight", true);
  s.c.P.moving = 0; s.key("Enter", "Enter"); s.step(16); assert.equal(s.c.mode, "menu");
  s.step(16); assert.equal(s.stats.ticks.menu, 1); assert.equal(s.api.last(), 64);
});
check("without a Settings panel the normal game and rendering remain available", () => {
  const s = session(source, false); assert.equal(s.api.panel, null);
  s.key("KeyZ", "z"); s.step(16); assert.equal(s.stats.interactions, 1); assert.equal(s.stats.draws, 2); // field plus poison overlay
  assert.equal(s.stats.polls, 1); assert.equal(s.stats.audio, 1); assert.equal(s.api.paused(), false);
});
check("controlled pre-fix timer, modal-edge, touch and drawing behavior is detected", () => {
  const ungated = source.replace('const paused = settingsFramePaused = gameplayInputBlocked(); settingsTransition = false;',
    'const paused = settingsFramePaused = false; settingsTransition = false;');
  assert.notEqual(ungated, source); assert.throws(() => pausedFish(ungated), assert.AssertionError);
  const oldCallbacks = source.replace('onOpen: clearSettingsInput, onClose: () => { if (PAD && PAD.binding()) PAD.cancelBind(); clearSettingsInput(); cv.focus({ preventScroll: true }); }',
    'onOpen: () => { Object.keys(SRC).forEach(releaseSource); }, onClose: () => { cv.focus({ preventScroll: true }); }');
  assert.notEqual(oldCallbacks, source);
  assert.throws(() => { const s = session(oldCallbacks); s.api.setHeld("kb", "a", true); s.panel.open(); allReleased(s); }, assert.AssertionError);
  const unguardedTouch = source.replace('if (gameplayInputBlocked()) return; if (k === "opts")', 'if (k === "opts")');
  assert.notEqual(unguardedTouch, source);
  assert.throws(() => { const s = session(unguardedTouch); s.panel.open(); s.touch("a"); allReleased(s); }, assert.AssertionError);
  const tickingDraw = source.replace('if (fl > 0 && !settingsFramePaused)', 'if (fl > 0)');
  assert.notEqual(tickingDraw, source);
  assert.throws(() => { const s = session(tickingDraw); s.c.mode = "battle"; s.panel.open(); s.step(16); assert.equal(s.c.B.flash.slime20, 0.2); }, assert.AssertionError);
});
console.log("settings pause: " + checks + " focused groups passed");
