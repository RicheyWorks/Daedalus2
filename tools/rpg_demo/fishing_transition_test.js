// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/fishing_transition_test.js
// Actual village map, water interaction, fishing, field movement and logical input/expiry.
// No browser, scheduled game loop, assets, storage, builds or native runtime is launched.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const village = data("prism-village"), fishCatalog = data("prism-fish").fish;
const townTiles = Object.fromEntries(data("town-tiles").tiles.filter(t => t.realm === "prism").map(t => [t.tile, t]));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found;
}
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [between("const LOGICAL =", "const KEYMAP ="), between("const hit =", "/* ---------- controllers:"),
  line("const DIRS ="), line("const at ="), line("const npcAt ="), line("function openMenu()"),
  between("function villageMap()", "function interiorMap("), between("function interact()", "function innPrompt("),
  between("function fieldTick(", "function land()"), between("function castLine(", "function drawFishLog("),
  "function frameCleanup(now) {\n" + cleanup + "\n}",
  "this.api = { villageMap, fieldTick, fishTick, endFish, interact, castLine, setHeld, releaseSource, menuRepeat, frameCleanup, " +
  "inputs: () => ({ held, pressed, SRC, pressedAt }) };"
].join("\n");
const dirs = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
function shore() {
  const npc = (x, y) => village.npcs.some(n => n.x === x && n.y === y);
  const tile = (x, y) => village.grid[y] && village.grid[y][x];
  const walk = (x, y) => !!(townTiles[tile(x, y)] || {}).walkable && !npc(x, y);
  for (let y = 0; y < village.grid.length; y++) for (let x = 0; x < village.grid[y].length; x++) {
    if (!walk(x, y)) continue;
    for (const [dir, [dx, dy]] of Object.entries(dirs)) {
      if (tile(x + dx, y + dy) !== "Water" || npc(x + dx, y + dy)) continue;
      const move = Object.entries(dirs).find(([, [mx, my]]) => walk(x + mx, y + my));
      if (move) return { x, y, dir, move: move[0] };
    }
  }
  throw new Error("authored Windmere map must have a usable pond shore and adjacent walkable step");
}
const shoreline = shore();
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(productionSource = source) {
  const sounds = [], notices = [], fixedMath = Object.create(Math);
  const c = {
    D: { village: clone(village), town_tiles: clone(townTiles), fish: clone(fishCatalog) },
    now: 0, mode: "field", fishing: null, dlg: null, menu: null, fade: 0, bag: {}, state: { fish: {} },
    P: { x: shoreline.x, y: shoreline.y, fx: shoreline.x * 16, fy: shoreline.y * 16, dir: shoreline.dir, moving: 0, step: 0 },
    T: 16, AIR_SPEED: 2, performance: { now: () => c.now }, Math: fixedMath,
    sfx: sound => sounds.push(sound), toast: (...args) => notices.push(args), isNight: () => false,
    flying: () => false, land() {}, stepDone: () => { c.completedSteps++; }, completedSteps: 0,
    say: () => { throw new Error("pond-water fixture unexpectedly opened a dialog"); },
  };
  fixedMath.random = () => 0.25;
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.map = c.api.villageMap();
  return { c, sounds, notices, api: c.api,
    tick: (keys = [], dt = 0.016) => {
      c.now += dt * 1000;
      for (const key of keys) { c.api.inputs().pressed[key] = true; c.api.inputs().pressedAt[key] = c.now; }
      c.api.menuRepeat(c.now);
      if (c.mode === "field") c.api.fieldTick(dt);
      else if (c.mode === "fish") c.api.fishTick(dt);
      c.api.frameCleanup(c.now);
    } };
}
function cast(productionSource = source) {
  const s = session(productionSource); s.tick(["a"]);
  assert.equal(s.c.mode, "fish"); assert.equal(s.c.fishing.phase, "wait");
  const [dx, dy] = dirs[shoreline.dir];
  assert.equal(s.c.map.grid[s.c.P.y + dy][s.c.P.x + dx], "Water", "the actual interaction faces real village pond water");
  return s;
}
function phase(s, kind) {
  s.c.fishing.phase = kind; s.c.fishing.t = kind === "done" ? 0.4 : 0;
  if (kind === "bite") s.c.fishing.fish = clone(fishCatalog[0]);
}
const resources = s => JSON.stringify({ bag: s.c.bag, fish: s.c.state.fish });
function assertExited(kind, keys, productionSource = source) {
  const s = cast(productionSource); phase(s, kind); const before = resources(s), where = [s.c.P.x, s.c.P.y];
  s.tick(keys); assert.equal(s.c.mode, "field"); assert.equal(s.c.fishing, null);
  assert.equal(resources(s), before, "cancelling or dismissing a catch does not award another fish");
  s.tick(); assert.equal(s.c.mode, "field", "returning to the same water does not recast or open the field menu");
  assert.equal(s.c.fishing, null); assert.deepEqual([s.c.P.x, s.c.P.y], where); assert.equal(resources(s), before);
  for (const key of ["a", "b", "start"]) assert.equal(!!s.api.inputs().pressed[key], false, "no buffered " + key + " survives the fishing transition");
  return s;
}
for (const kind of ["wait", "bite"]) for (const keys of [["a", "b"], ["b", "start"], ["a", "b", "start"]])
  check(kind + " cancellation " + keys.join("+") + " returns to water without another action", () => assertExited(kind, keys));
for (const keys of [["a"], ["b"], ["a", "b"], ["a", "start"], ["b", "start"], ["a", "b", "start"]])
  check("done dismissal " + keys.join("+") + " drains transition buttons", () => assertExited("done", keys));
for (const kind of ["wait", "bite"]) check("normal " + kind + " Back cancellation still returns without a catch", () => {
  const s = assertExited(kind, ["b"]); assert.equal(resources(s), JSON.stringify({ bag: {}, fish: {} }));
});
function caught(productionSource = source) {
  const s = cast(productionSource); s.c.fishing.wait = 0; s.tick();
  assert.equal(s.c.fishing.phase, "bite"); const name = s.c.fishing.fish.name;
  assert.ok(fishCatalog.some(f => f.name === name), "actual pickFish selected an authored fish");
  s.tick(["a"]); assert.equal(s.c.fishing.phase, "done"); assert.equal(s.c.fishing.caught, name);
  assert.equal(s.c.bag[name], 1); assert.equal(s.c.state.fish[name], 1); return { s, name };
}
for (const keys of [["a"], ["b"], ["a", "b"], ["a", "start"], ["b", "start"]])
  check("a caught fish remains awarded exactly once after " + keys.join("+") + " dismissal", () => {
    const { s, name } = caught(); for (let i = 0; i < 7; i++) s.tick([], 0.05);
    const before = resources(s); s.tick(keys); assert.equal(s.c.mode, "field"); s.tick();
    assert.equal(s.c.mode, "field"); assert.equal(resources(s), before); assert.equal(s.c.bag[name], 1); assert.equal(s.c.state.fish[name], 1);
  });
check("normal too-early strike and missed bite remain unsuccessful", () => {
  const early = cast(); early.tick(["a"]); assert.equal(early.c.fishing.phase, "done"); assert.match(early.c.fishing.msg, /TOO SOON/);
  assert.equal(resources(early), JSON.stringify({ bag: {}, fish: {} }));
  const late = cast(); phase(late, "bite"); late.c.fishing.t = late.c.fishing.fish.window_s; late.tick();
  assert.equal(late.c.fishing.phase, "done"); assert.match(late.c.fishing.msg, /GOT AWAY/); assert.equal(resources(late), JSON.stringify({ bag: {}, fish: {} }));
});
check("done input still waits for its existing short dismissal delay", () => {
  const { s } = caught(); s.tick(["b"]); assert.equal(s.c.mode, "fish");
  for (let i = 0; i < 7; i++) s.tick([], 0.05); assert.equal(s.c.mode, "fish", "expired old Back does not end the catch dialog");
  s.tick(["b"]); assert.equal(s.c.mode, "field");
});
check("a released fresh Confirm can cast again after cancellation, without altering held sources", () => {
  const s = cast(); s.api.setHeld("kb", "a", true); s.api.setHeld("kb", "b", true); s.tick();
  assert.equal(s.c.mode, "field"); assert.equal(s.api.inputs().held.a, true); assert.equal(s.api.inputs().held.b, true);
  s.tick(); assert.equal(s.c.mode, "field", "held action buttons do not make fresh presses");
  s.api.setHeld("kb", "a", false); s.api.setHeld("kb", "b", false); s.api.setHeld("kb", "a", true); s.tick();
  assert.equal(s.c.mode, "fish"); assert.equal(s.c.fishing.phase, "wait");
});
check("a fresh Start still opens the field menu after a settled fishing exit", () => {
  const s = assertExited("wait", ["a", "b"]); s.tick(["start"]);
  assert.equal(s.c.mode, "menu"); assert.ok(s.c.menu); assert.equal(s.c.fishing, null);
});
check("held movement and last-source release survive fishing cancellation", () => {
  const s = cast(), dir = shoreline.move, [dx, dy] = dirs[dir], before = [s.c.P.x, s.c.P.y];
  s.api.setHeld("kb", dir, true); s.api.setHeld("pad", dir, true); s.tick(["a", "b"]);
  assert.equal(s.c.mode, "field"); assert.equal(s.api.inputs().held[dir], true);
  s.api.releaseSource("kb"); assert.equal(s.api.inputs().held[dir], true, "another source still holds the direction");
  s.tick(); assert.deepEqual([s.c.P.x, s.c.P.y], [before[0] + dx, before[1] + dy]); assert.equal(s.c.P.moving, 1);
  s.api.releaseSource("pad"); assert.equal(s.api.inputs().held[dir], false);
});
check("removing the actual exit drain reproduces ordinary recast and menu leaks", () => {
  const exit = line("function endFish()"); assert.ok(exit.includes("clearActionButtons();"), "fishing exit uses existing action-edge helper");
  const legacy = source.replace(exit, exit.replace("clearActionButtons(); ", "")); assert.notEqual(legacy, source);
  for (const kind of ["wait", "bite"]) for (const keys of [["a", "b"], ["b", "start"]])
    assert.throws(() => assertExited(kind, keys, legacy), assert.AssertionError);
  assert.throws(() => assertExited("done", ["b", "start"], legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or DOM work.
console.log("Prismheart fishing transition checks: " + checks + " passed; full inline script compiles.");
