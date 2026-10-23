// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/skiff_reboard_test.js
// Actual Prism world/catalogs, field/input, boarding/landing, cache and parked-save recovery handlers.
// No browser, assets, storage, scheduled game loop, builds or native runtime is launched.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const build = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const worldCatalog = data("worldmap-tiles"), world = worldCatalog.demo_maps.prism;
const worldTiles = Object.fromEntries(worldCatalog.tiles.filter(t => t.realm === "prism").map(t => [t.tile, t]));
const village = data("prism-village"), townTiles = Object.fromEntries(data("town-tiles").tiles.filter(t => t.realm === "prism").map(t => [t.tile, t]));
const quest = JSON.parse(build.match(/^QUEST = (\[.*\])/m)[1].replace(/\(/g, "[").replace(/\)/g, "]"));
const bosses = data("prism-bosses").bosses;
const dungeons = quest.map(([landmark, name]) => ({ landmark, name, boss_data: bosses.find(b => b.dungeon === name) }));
const skyLoot = JSON.parse(build.match(/^SKY_LOOT = (\[.*\])/m)[1]);
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found;
}
const source = [between("const LOGICAL =", "const KEYMAP ="), between("const KEYMAP =", 'window.addEventListener("keydown"'),
  between("const hit =", "/* ---------- controllers:"), line("const DIRS ="), line("const find ="), line("const at ="), line("const npcAt ="),
  between("const STEP_MIN =", "function wakeAt("), between("const AIR_SPEED =", "/* The shard quest:"),
  between("function worldMap()", "function dungeonMap("), between("function villageMap()", "function interiorMap("),
  between("let dlg = null;", "function wrap("), between("function interact()", "function innPrompt("),
  between("function stepDone()", "function drawAirship("), between("function titlePrompt(", "function drawTitle("),
  "this.api = { fieldTick, interact, boardAirship, land, stepDone, airship, flying, recoverAir, footReach, worldMap, villageMap, " +
  "setHeld, releaseSource, inputs: () => ({ held, pressed }), dialog: () => dlg, keys: KEYMAP };"
].join("\n");
const dirs = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const tile = (x, y) => world[y] && world[y][x];
const pad = (() => { for (let y = 0; y < world.length; y++) { const x = world[y].indexOf("AirshipPad"); if (x >= 0) return [x, y]; } throw new Error("authored dock missing"); })();
const traps = [[7, 3], [19, 11]];
// Project only the authored sky-cache metadata using build_demo.py's existing pocket/loot ordering.
// This reads the real map; it does not invoke the asset builder or invent a test map.
function caches(foot) {
  const done = new Set(), pockets = [], compare = (a, b) => a[0] - b[0] || a[1] - b[1];
  for (let y = 0; y < world.length; y++) for (let x = 0; x < world[y].length; x++) {
    const key = x + "," + y;
    if (!worldTiles[tile(x, y)].airship_lands || foot.has(key) || done.has(key)) continue;
    const pocket = [], q = [[x, y]]; done.add(key);
    while (q.length) {
      const [cx, cy] = q.shift(); pocket.push([cx, cy]);
      for (const [dx, dy] of Object.values(dirs)) {
        const nx = cx + dx, ny = cy + dy, k = nx + "," + ny;
        if (!(worldTiles[tile(nx, ny)] || {}).airship_lands || foot.has(k) || done.has(k)) continue;
        done.add(k); q.push([nx, ny]);
      }
    }
    pockets.push(pocket.sort(compare));
  }
  return pockets.sort((a, b) => b.length - a.length || compare(a[0], b[0])).slice(0, skyLoot.length)
    .map((p, i) => ({ x: p[Math.floor(p.length / 2)][0], y: p[Math.floor(p.length / 2)][1], item: skyLoot[i], pocket: p.length }));
}
function session(productionSource = source, options = {}) {
  const sounds = [], notices = [], visits = [], c = {
    D: { world: clone(world), world_tiles: clone(worldTiles), village: clone(village), town_tiles: clone(townTiles),
      dungeons: clone(dungeons), sky_caches: [], zones: {}, fish: [{}] },
    state: { air: null, beaten: new Set(options.locked ? [] : [bosses[0].name]), steps: 0, sinceBattle: 0, day: 1, minute: 480 },
    opened: new Set(), bag: {}, party: [], mode: "field", T: 16, now: 0,
    P: { x: pad[0], y: pad[1] + 1, fx: pad[0] * 16, fy: (pad[1] + 1) * 16, dir: "up", moving: 0, step: 0 },
    performance: { now: () => c.now }, sfx: sound => sounds.push(sound), toast: (...args) => notices.push(args),
    PAD: options.label ? { devices: () => [{ index: 4 }], label: (action, index) => { assert.equal(action, "confirm"); assert.equal(index, 4); return options.label; } } : null,
    fieldPoison() {}, waystoneStep: () => false, goto: (...args) => visits.push(args), openMenu: () => { c.mode = "menu"; },
    startBattle: () => { throw new Error("this field traversal must not start a battle"); },
    castLine: (x, y) => { c.castAt = [x, y]; },
    localStorage: { getItem() { throw new Error("no storage access allowed"); }, setItem() { throw new Error("no storage access allowed"); } }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.map = c.api.worldMap(); c.D.sky_caches = caches(c.api.footReach());
  const s = { c, api: c.api, sounds, notices, visits,
    tick(dt = 0.016) { c.now += dt * 1000; assert.equal(c.mode, "field"); c.api.fieldTick(dt); },
    press(key = "a") { c.api.setHeld("kb", key, true); this.tick(); c.api.setHeld("kb", key, false); },
    move(dir) { c.api.setHeld("kb", dir, true); this.tick(); c.api.setHeld("kb", dir, false); if (c.P.moving) this.tick(0.2); },
    dialog() { for (let i = 0; c.api.dialog() && i < 10; i++) this.press(); assert.equal(c.api.dialog(), null); },
  };
  return s;
}
function board(s) {
  assert.equal(tile(s.c.P.x, s.c.P.y + dirs.up[1]), "AirshipPad");
  s.move("up"); assert.equal(s.api.flying(), true, "ordinary walk onto the unlocked dock boards"); return s;
}
function flyTo(s, x, y) {
  assert.equal(s.api.flying(), true);
  while (s.c.P.x !== x) s.move(s.c.P.x < x ? "right" : "left");
  while (s.c.P.y !== y) s.move(s.c.P.y < y ? "down" : "up");
  assert.equal(s.c.map.kind, "world"); assert.equal(s.api.flying(), true);
}
function landAt(s, x, y) {
  flyTo(s, x, y); s.press(); assert.equal(s.api.flying(), false);
  assert.deepEqual([s.c.state.air.x, s.c.state.air.y], [x, y]); return s;
}
function escape(s, x, y) {
  landAt(s, x, y); s.dialog();
  const loot = JSON.stringify(s.c.bag), opened = [...s.c.opened].sort(), clock = [s.c.state.day, s.c.state.minute, s.c.state.steps];
  const enter = s.sounds.filter(k => k === "ENTER").length;
  s.press(); assert.equal(s.api.flying(), true, "fresh grounded Confirm reboards on this same isolated tile");
  assert.equal(s.sounds.filter(k => k === "ENTER").length, enter + 1, "exactly one boarding effect");
  assert.equal(JSON.stringify(s.c.bag), loot); assert.deepEqual([...s.c.opened].sort(), opened);
  assert.deepEqual([s.c.state.day, s.c.state.minute, s.c.state.steps], clock, "boarding is not an extra step or clock tick");
  s.move("right"); assert.deepEqual([s.c.P.x, s.c.P.y], [x + 1, y]); assert.equal(s.api.flying(), true);
  assert.equal(JSON.stringify(s.c.bag), loot); return s;
}
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
for (const [x, y] of traps) {
  check("authored isolated landing tile " + x + "," + y + " has four blocked neighbors", () => {
    const s = session(); assert.ok(worldTiles[tile(x, y)].airship_lands); assert.ok(!s.api.footReach().has(x + "," + y));
    for (const [dx, dy] of Object.values(dirs)) { const t = tile(x + dx, y + dy); assert.ok(t); assert.equal(s.c.map.walk(t), false, t); }
    assert.ok(s.c.D.sky_caches.some(cache => cache.x === x && cache.y === y), "the authored sky-cache projection includes this singleton");
  });
  check("fly, land and escape " + x + "," + y + " through ordinary controls without storage", () => escape(board(session()), x, y));
  check("ground movement really is blocked in all directions after landing " + x + "," + y, () => {
    const s = landAt(board(session()), x, y); s.dialog();
    for (const dir of Object.keys(dirs)) { s.move(dir); assert.deepEqual([s.c.P.x, s.c.P.y], [x, y]); assert.equal(s.c.P.moving, 0); }
    s.press(); assert.equal(s.api.flying(), true);
  });
  check("Continue still recalls a parked skiff from " + x + "," + y, () => {
    const s = landAt(board(session()), x, y), saved = { x: s.c.state.air.x, y: s.c.state.air.y };
    const recalled = s.api.recoverAir(saved); assert.deepEqual([recalled.x, recalled.y], pad); assert.equal(recalled.aboard, false); assert.equal(recalled.recalled, true);
    assert.deepEqual([s.c.state.air.x, s.c.state.air.y], [x, y], "checking recovery does not alter the live parked craft");
  });
}
check("walk-on boarding remains available after landing on ordinary connected ground", () => {
  const s = landAt(board(session()), pad[0] + 1, pad[1]); s.dialog();
  assert.ok(s.c.map.walk(tile(pad[0] + 2, pad[1]))); s.move("right"); assert.equal(s.api.flying(), false);
  s.move("left"); assert.equal(s.api.flying(), true); assert.equal(s.sounds.filter(k => k === "ENTER").length, 2);
});
check("a fresh Confirm in flight still lands, and a fresh grounded Confirm boards once", () => {
  const s = landAt(board(session()), pad[0] + 1, pad[1]);
  s.api.setHeld("kb", "a", true); s.tick(); assert.equal(s.api.flying(), true);
  s.tick(); assert.equal(s.api.flying(), true, "held Confirm does not turn into another land command");
  s.api.setHeld("kb", "a", false); s.press(); assert.equal(s.api.flying(), false);
  s.tick(); assert.equal(s.api.flying(), false);
});
check("Confirm away from the parked skiff does not board remotely", () => {
  const s = landAt(board(session()), pad[0] + 1, pad[1]); s.move("right");
  const before = s.sounds.filter(k => k === "ENTER").length; s.press(); assert.equal(s.api.flying(), false);
  assert.equal(s.sounds.filter(k => k === "ENTER").length, before); assert.deepEqual([s.c.state.air.x, s.c.state.air.y], [pad[0] + 1, pad[1]]);
});
check("the locked dock refuses walk-on and Confirm without lazily creating a skiff", () => {
  const s = session(source, { locked: true }); s.move("up"); assert.equal(s.api.flying(), false); assert.equal(s.c.state.air, null);
  assert.match(s.api.dialog().pages.join(" "), /WARDEN'S SHARD/); s.dialog(); s.press();
  assert.equal(s.c.state.air, null); assert.equal(s.api.flying(), false); assert.equal(s.sounds.includes("ENTER"), false);
});
check("non-world Confirm retains the real village water interaction and does not create a skiff", () => {
  const s = session(); s.c.map = s.api.villageMap();
  const vtile = (x, y) => s.c.map.grid[y] && s.c.map.grid[y][x]; let shore;
  for (let y = 0; y < village.grid.length && !shore; y++) for (let x = 0; x < village.grid[y].length && !shore; x++) {
    if (!s.c.map.walk(vtile(x, y)) || s.c.map.npcs.some(n => n.x === x && n.y === y)) continue;
    for (const [dir, [dx, dy]] of Object.entries(dirs)) if (vtile(x + dx, y + dy) === "Water" && !s.c.map.npcs.some(n => n.x === x + dx && n.y === y + dy)) { shore = { x, y, dir, water: [x + dx, y + dy] }; break; }
  }
  assert.ok(shore); Object.assign(s.c.P, { x: shore.x, y: shore.y, dir: shore.dir }); s.press();
  assert.deepEqual(s.c.castAt, shore.water); assert.equal(s.c.state.air, null); assert.equal(s.sounds.includes("ENTER"), false);
});
check("grounded Confirm boards before held movement and preserves the held direction for flight", () => {
  const s = landAt(board(session()), ...traps[0]); s.dialog();
  s.api.setHeld("kb", "right", true); s.press(); assert.equal(s.api.flying(), true);
  assert.deepEqual([s.c.P.x, s.c.P.y], traps[0]); assert.equal(s.api.inputs().held.right, true);
  s.tick(); assert.deepEqual([s.c.P.x, s.c.P.y], [traps[0][0] + 1, traps[0][1]]);
  s.api.releaseSource("kb"); assert.equal(s.api.inputs().held.right, false); s.tick(0.2); assert.equal(s.api.flying(), true);
});
check("failed landings over authored Mountain and DeepSea keep flight and the last parked spot", () => {
  for (const terrain of ["Mountain", "DeepSea"]) {
    const s = board(session()), parked = [s.c.state.air.x, s.c.state.air.y];
    let point; for (let y = 0; y < world.length && !point; y++) { const x = world[y].indexOf(terrain); if (x >= 0) point = [x, y]; }
    flyTo(s, ...point); s.press(); assert.equal(s.api.flying(), true); assert.deepEqual([s.c.state.air.x, s.c.state.air.y], parked);
    assert.equal(s.notices.at(-1)[0], "NO PLACE TO LAND");
  }
});
check("each real cache awards once, its dialog consumes Confirm, and boarding never reopens it", () => {
  const metadata = session().c.D.sky_caches; assert.ok(metadata.length >= 2);
  for (const cache of metadata) {
    const s = landAt(board(session()), cache.x, cache.y); assert.equal(s.c.bag[cache.item], 1);
    assert.ok(s.c.opened.has("sky:" + cache.x + "," + cache.y)); assert.ok(s.api.dialog());
    s.press(); assert.equal(s.api.flying(), false, "Confirm reveals the cache dialog before it can board");
    s.dialog(); s.tick(); assert.equal(s.api.flying(), false, "the dialog's dismissal is not a new boarding edge");
    s.press(); assert.equal(s.api.flying(), true); s.press(); s.dialog();
    assert.equal(s.api.flying(), false); assert.equal(s.c.bag[cache.item], 1); assert.equal(s.c.opened.size, 1);
    s.press(); assert.equal(s.api.flying(), true); assert.equal(s.c.bag[cache.item], 1);
  }
});
check("Continue retains a reachable parked tile and defaults the skiff to its dock", () => {
  const s = session(), x = pad[0] + 1, y = pad[1]; assert.ok(s.api.footReach().has(x + "," + y));
  const kept = s.api.recoverAir({ x, y }); assert.deepEqual([kept.x, kept.y], [x, y]); assert.equal(kept.recalled, false); assert.equal(kept.aboard, false);
  const home = s.api.recoverAir(null); assert.deepEqual([home.x, home.y], pad); assert.equal(home.recalled, false);
});
for (const label of [null, "X", "TRIANGLE", "unsafe controller label <A>"]) check("boarding and landing hints use physical Confirm label " + label, () => {
  const s = session(source, { label }); board(s);
  const expected = label === "X" || label === "TRIANGLE" ? "PRESS " + label : "PRESS Z/SPACE OR TAP A";
  assert.equal(s.notices.at(-1)[1], expected + " TO LAND ON OPEN GROUND");
  landAt(s, pad[0] + 1, pad[1]); assert.equal(s.notices.at(-1)[1], expected + " TO BOARD AGAIN HERE");
  assert.equal(s.api.keys.KeyZ, "a"); assert.equal(s.api.keys.Space, "a"); assert.equal(s.api.keys.KeyA, "left");
  assert.match(html, /<button data-k="a"[^>]*>A<\/button>/);
});
check("removing only the new current-tile boarding hook reproduces both ordinary traps", () => {
  const hook = '  if (map.kind === "world" && boardAirship()) return;'; assert.ok(source.includes(hook));
  const legacy = source.replace(hook, ""); assert.notEqual(legacy, source);
  for (const [x, y] of traps) assert.throws(() => escape(board(session(legacy)), x, y), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute DOM/boot work.
console.log("Prismheart skiff reboarding checks: " + checks + " passed; full inline script compiles.");
