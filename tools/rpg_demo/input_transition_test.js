// SPDX-License-Identifier: MIT
// Focused DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/input_transition_test.js
// Production input/field/menu/title/game-over handlers and frame-tail expiry; no game loop or browser.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [
  between("const LOGICAL =", "const KEYMAP ="),
  between("const hit =", "/* ---------- controllers:"),
  between("function fieldTick(", "function land()"),
  between("const MENU_CMDS =", "function equipCandidates("),
  between("function titleTick(", "function titlePrompt("),
  between("function gameOverTick(", "function drawGameOver("),
  "function frameCleanup(now) {\n" + cleanup + "\n}",
  "this.api = { setHeld, releaseSource, clearActionButtons, menuRepeat, fieldTick, menuTick, titleTick, gameOverTick, frameCleanup, inputs: () => ({ held, pressed, pressedAt, SRC, repeatAt }) };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(productionSource = source) {
  const choices = [], c = {
    mode: "field", menu: null, dlg: null, fade: 0, goT: 2, titleT: 0, titleIdx: 0,
    TITLE_ITEMS: ["NEW GAME", "CONTINUE", "OPTIONS"], now: 0, interactions: 0, completedSteps: 0,
    P: { moving: 0, dir: "right", x: 1, y: 1, fx: 16, fy: 16, step: 0 }, T: 16, AIR_SPEED: 2,
    DIRS: { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] },
    map: { walk: () => true }, GEAR: { Tonic: { effect: "heal 1" } }, bag: { Tonic: 1 }, D: {},
    performance: { now: () => c.now }, sfx() {}, cue() {}, flying: () => false,
    interact: () => { c.interactions++; }, land() {}, stepDone: () => { c.completedSteps++; },
    at: () => "Floor", npcAt: () => null,
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)),
    titleChoose: i => { choices.push(c.TITLE_ITEMS[i]); },
    fieldItems: () => ["Tonic"], roster: () => [],
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  return { c, choices, down: (...keys) => keys.forEach(k => c.api.setHeld("kb", k, true)),
    up: (...keys) => keys.forEach(k => c.api.setHeld("kb", k, false)),
    step: (dt = 1 / 60) => {
      c.now += dt * 1000; c.api.menuRepeat(c.now);
      if (c.mode === "field") c.api.fieldTick(dt);
      else if (c.mode === "menu") c.api.menuTick();
      else if (c.mode === "title") c.api.titleTick(dt);
      else if (c.mode === "gameover") c.api.gameOverTick(dt);
      c.api.frameCleanup(c.now);
    } };
}
function assertTitleWaits(productionSource = source, index = 0) {
  const s = session(productionSource); s.c.mode = "gameover"; s.c.titleIdx = index;
  s.down("start", "a"); s.step(); assert.equal(s.c.mode, "title"); s.step();
  assert.deepEqual(s.choices, [], "Game Over dismissal cannot choose a title item next frame");
  return s;
}
function assertMenuWaits(productionSource = source) {
  const s = session(productionSource); s.down("start", "a"); s.step();
  assert.equal(s.c.mode, "menu"); s.step();
  assert.equal(s.c.menu.sub, null, "opening menu cannot automatically choose ITEM"); return s;
}
function assertMenuCloses(productionSource = source) {
  const s = session(productionSource); s.down("start"); s.step(); s.up("start");
  s.down("b", "start", "a"); s.step(); assert.equal(s.c.mode, "field"); s.step();
  assert.equal(s.c.mode, "field", "menu-close buttons cannot reopen the menu");
  assert.equal(s.c.interactions, 0, "menu-close buttons cannot interact on the field"); return s;
}
for (const index of [0, 1]) check("Game Over does not auto choose " + ["NEW GAME", "CONTINUE"][index], () => assertTitleWaits(source, index));
check("Start plus confirm opens the menu without choosing ITEM", () => assertMenuWaits());
check("cancel plus Start closes the menu without reopening or interacting", () => assertMenuCloses());
check("a fresh confirm still chooses the selected title item", () => {
  const s = assertTitleWaits(source, 1); s.up("a", "start"); s.down("a"); s.step();
  assert.deepEqual(s.choices, ["CONTINUE"]);
});
for (const key of ["a", "start"]) check("single " + key + " still dismisses Game Over after its delay", () => {
  const s = session(); s.c.mode = "gameover"; s.c.goT = 1; s.down(key); s.c.api.gameOverTick(0);
  assert.equal(s.c.mode, "gameover"); s.step();
  assert.equal(s.c.mode, "title"); s.step(); assert.deepEqual(s.choices, []);
});
check("fresh Start can close and reopen the menu", () => {
  const s = assertMenuWaits(); s.up("a", "start"); s.down("start"); s.step();
  assert.equal(s.c.mode, "field"); s.up("start"); s.down("start"); s.step(); assert.equal(s.c.mode, "menu");
});
check("held action buttons do not create synthetic repeat edges", () => {
  const s = assertMenuWaits(), before = JSON.stringify(s.c.api.inputs().SRC);
  s.down("start", "a"); s.step(0.5); s.step();
  assert.equal(s.c.menu.sub, null); assert.equal(JSON.stringify(s.c.api.inputs().SRC), before);
  assert.equal(s.c.api.inputs().held.start, true); assert.equal(s.c.api.inputs().held.a, true);
});
check("clearing action edges preserves source holds, timestamps and directions", () => {
  const s = session(); s.down("a", "b", "start", "right"); const i = s.c.api.inputs();
  const before = JSON.stringify({ held: i.held, SRC: i.SRC, pressedAt: i.pressedAt, repeatAt: i.repeatAt });
  s.c.api.clearActionButtons();
  assert.equal(JSON.stringify({ held: i.held, SRC: i.SRC, pressedAt: i.pressedAt, repeatAt: i.repeatAt }), before);
  assert.equal(i.pressed.right, true); assert.ok(["a", "b", "start"].every(k => i.pressed[k] === false));
});
check("fresh confirm still opens ITEM after a menu transition", () => {
  const s = assertMenuWaits(); s.up("a"); s.down("a"); s.step(); assert.equal(s.c.menu.sub, "item");
});
check("a buffered mid-step interaction remains available when movement finishes", () => {
  const s = session(); s.c.P.moving = 0.2; s.down("a"); s.step(0.01); s.step(0.02);
  assert.equal(s.c.completedSteps, 1); assert.equal(s.c.interactions, 0);
  s.step(); assert.equal(s.c.interactions, 1); s.step(); assert.equal(s.c.interactions, 1);
});
check("actual frame-tail expiry still keeps 150ms and discards older action edges", () => {
  const s = session(); s.down("a"); s.c.api.frameCleanup(150); assert.equal(s.c.api.inputs().pressed.a, true);
  s.c.api.frameCleanup(151); assert.equal(s.c.api.inputs().pressed.a, false);
});
check("held field directions still move and menu directions keep their repeat timing", () => {
  const s = session(); s.down("right"); s.step(); assert.equal(s.c.P.x, 2);
  assert.equal(s.c.api.inputs().pressed.right, false); assert.equal(s.c.api.inputs().held.right, true);
  s.c.P.moving = 0; s.c.api.setHeld("kb", "right", false); s.down("start"); s.step(); s.down("down"); s.step();
  assert.equal(s.c.menu.idx, 1); s.c.now = 500; s.step(); assert.equal(s.c.menu.idx, 2);
});
check("controlled old transitions fail the same adjacent-frame regressions", () => {
  // Remove only the new boundary calls; retain the actual former short-circuit handlers.
  const legacy = source.replaceAll("{ clearActionButtons(); sfx(", "{ sfx(")
    .replace("{ clearActionButtons(); mode = \"title\"", "{ mode = \"title\"");
  assert.notEqual(legacy, source);
  for (const regression of [assertTitleWaits, assertMenuWaits, assertMenuCloses])
    assert.throws(() => regression(legacy), assert.AssertionError);
});
// Compile the complete inline production script without executing boot, DOM handlers or the game loop.
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/);
assert.ok(inline); new vm.Script(inline[1], { filename: "index.html:inline" });
console.log("Prismheart input transition checks: " + checks + " passed; full inline script compiles.");
