// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/floor_sketch_test.js
// Production functions + the five projected canonical dungeon grids. Canvas command capture only;
// no game IIFE, browser, assets, builder execution, native runtime, travel or persistence acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x)), raw = data("dungeons"), bosses = data("prism-bosses").bosses;
const world = data("worldmap-tiles").demo_maps.prism;
function tuples(name) { const m = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(m, name);
  return Array.from(m[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), x => [x[1], x[2]]); }
const selected = tuples("QUEST").concat(tuples("OPTIONAL_QUEST"));
const dungeons = selected.map(([landmark, name], i) => { const d = raw.dungeons.prism.find(d => d.name === name), b = bosses.find(b => b.dungeon === name);
  assert.ok(d && b, name); return { ...clone(d), landmark, boss_data: clone(b), final: name === "The Shattered Heart", optional: i >= 4 }; });
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const s = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(s, prefix); return s; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"), line("const chestKey ="), line("const find ="), line("const at ="),
  line("const STEP_MIN ="), line("function menuMove("), between("function dungeonMap(", "function goto("),
  between("function openChest(", "/* ---------- shops"), between("function stepDone()", "function fieldTick("),
  between("function finishBattle()", "function bossGate()"), between("function journeyRoutes()", "function journeyAnchor()"),
  between("function drawFloorSketch()", "function formationPreview()"), between("function titlePrompt(", "function drawTitle("),
  "this.api={makeMap:dungeonMap,openChest,stepDone,finishBattle,drawFloorSketch,drawJourney,journeyTick,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, production = source) {
  const paints = [], sounds = [], dialogs = [], moves = [], pressed = {}, calls = { save: 0, rng: 0, lazy: 0, pinToast: 0 };
  const tiles = {}, fromRect = new Map(); let index = 0;
  for (const d of dungeons) for (const tile of new Set(d.floors.flatMap(f => f.grid.flat()).concat("ChestOpen"))) {
    const key = "dg:" + d.theme + ":" + tile; if (tiles[key + "#0"]) continue;
    for (const frame of [0, 1]) { const r = [index++ * 16, 0, 16, 16]; tiles[key + "#" + frame] = r; fromRect.set(r[0], { key, frame }); }
  }
  const fixedMath = Object.create(Math); fixedMath.random = () => { calls.rng++; throw new Error("drawing must not roll gameplay RNG"); };
  const lazy = () => { calls.lazy++; throw new Error("drawing must not construct a map or initialize travel state"); };
  const c = { D: { realm_key: "prism", dungeons: clone(dungeons), dungeon_walkable: clone(raw.walkable), world: clone(world), zones: {},
      rects: { tiles }, frames: Object.fromEntries(Object.keys(tiles).map(k => [k.replace(/#\d$/, ""), 2])) },
    W: width, H: 224, IM: { tiles: "atlas" }, Math: fixedMath, PAD: null, pressed, held: { left: true }, SRC: { kb: { left: true } },
    state: { beaten: new Set(), steps: 0, sinceBattle: 0, day: 1, minute: 480, ways: new Set(), air: null },
    opened: new Set(["unrelated/progress", "journey/pin/Ruins"]), grids: {}, map: null, P: { x: 0, y: 0 },
    menu: { sub: "journey", jp: 2, ii: 0, idx: 9, msg: "" }, party: [{ hp: 50, max: 50, mp: 10, status: { bind: 2 } }], reserve: [],
    bag: { Tonic: 2 }, gold: 100, B: null, fade: 0, fadeCb: null, ending: null, mode: "menu", goT: 0,
    clamp: (n, a, b) => Math.max(a, Math.min(b, n)), tw: x => String(x).length * 6, pretty: s => s.toUpperCase(),
    carriesShard: d => !!d.boss_data && d.boss_data.shard !== "-" && d.boss_data.shard !== "all", shardCount: () => 0,
    follyDungeon: () => null, follyCleared: () => false, worldMap: lazy, townMap: lazy, interiorMap: lazy, airship: lazy, recoverAir: lazy,
    saveGame() { calls.save++; throw new Error("floor view must not save"); }, toast() { calls.pinToast++; },
    sfx: name => sounds.push(name), say: pages => dialogs.push(pages), cue() {}, fieldPoison() {}, passTime() {}, flying: () => false,
    goto(map, x, y, dir) { moves.push({ map, x, y, dir }); c.map = map; c.P = { x, y }; },
    drawJourneyMap() { paints.push({ kind: "world-page" }); }, cursor() {}, win() {},
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); },
      drawImage(image, sx, sy, sw, sh, x, y, w, h) { paints.push({ kind: "image", image, sx, sy, sw, sh, x, y, w, h, ...fromRect.get(sx) }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  const snapshot = () => JSON.stringify({ D: c.D, map: c.map, P: c.P, grids: c.grids, bag: c.bag, gold: c.gold, party: c.party, reserve: c.reserve,
    state: { ...c.state, beaten: [...c.state.beaten], ways: [...c.state.ways] }, opened: [...c.opened], menu: c.menu, held: c.held, SRC: c.SRC });
  return { c, paints, pressed, sounds, dialogs, moves, calls, snapshot,
    setup(di = 0, fi = 0) { c.map = c.api.makeMap(di, fi); c.P = { ...c.map.info.stairs_up }; return this; },
    lock() { c.dungeonMap = lazy; return this; },
    draw(dispatch = false) { paints.length = 0; const before = snapshot(); c.api[dispatch ? "drawJourney" : "drawFloorSketch"](); assert.equal(snapshot(), before, "drawing changed state/cache/catalog"); return paints; },
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.journeyTick(); },
    texts() { return paints.filter(p => p.kind === "text").map(p => p.label); }
  };
}
const glyphColors = ["#ffcf70", "#f8a0d0", "#a0d8f8"], glyphBits = { StairsUp: 11, StairsDown: 10, Chest: 9, BossGate: 11 };
function geometry(s) {
  const c = s.c, grid = c.map.grid, images = s.paints.filter(p => p.kind === "image"), cell = 5, x0 = (c.W - 200) / 2, y0 = 48;
  assert.equal(grid.length, 28); assert.ok(grid.every(row => row.length === 40)); assert.equal(images.length, 1120);
  grid.forEach((row, y) => row.forEach((tile, x) => { const p = images[y * 40 + x];
    assert.equal(p.image, "atlas"); assert.equal(p.key, c.map.key(tile)); assert.equal(p.frame, 0); assert.deepEqual([p.x, p.y, p.w, p.h], [x0 + x * cell, y0 + y * cell, 5, 5]);
    if (glyphBits[tile]) { const bits = s.paints.filter(p => p.kind === "rect" && glyphColors.includes(p.color) && p.x >= x0 + x * cell && p.x < x0 + (x + 1) * cell && p.y >= y0 + y * cell && p.y < y0 + (y + 1) * cell);
      assert.equal(bits.length, glyphBits[tile], tile + " marker"); assert.ok(bits.every(p => p.w === 1 && p.h === 1));
      assert.equal(Math.max(...bits.map(p => p.x)) - Math.min(...bits.map(p => p.x)), 2); assert.equal(Math.max(...bits.map(p => p.y)) - Math.min(...bits.map(p => p.y)), 4); }
  }));
  const glyphs = s.paints.filter(p => p.kind === "rect" && glyphColors.includes(p.color));
  assert.ok(glyphs.every(p => s.paints.indexOf(p) > s.paints.indexOf(images.at(-1))), "markers must survive all terrain art");
  const player = s.paints.filter(p => p.kind === "rect" && p.color === "#ffdf83"); assert.equal(player.length, 2);
  assert.deepEqual(player.map(p => [p.x, p.y, p.w, p.h]), [[x0 + c.P.x * 5, y0 + c.P.y * 5 + 2, 5, 1], [x0 + c.P.x * 5 + 2, y0 + c.P.y * 5, 1, 5]]);
  assert.ok(player.every(p => s.paints.indexOf(p) > Math.max(...glyphs.map(p => s.paints.indexOf(p)))));
  for (const p of s.paints) { assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= c.W && p.y + p.h <= c.H, "paint outside canvas " + JSON.stringify(p));
    if (p.kind === "text") assert.ok([...p.label].every(ch => c.api.chars.includes(ch)), "unsupported font glyph"); }
  const closed = grid.flat().filter(t => t === "Chest").length, opened = grid.flat().filter(t => t === "ChestOpen").length;
  assert.ok(s.texts().includes("CHESTS " + opened + "/" + (closed + opened) + " OPEN"));
  assert.ok(s.texts().includes("F" + (c.map.floor + 1) + "/" + c.D.dungeons[c.map.dungeon].floors.length));
  assert.deepEqual(s.calls, { save: 0, rng: 0, lazy: 0, pinToast: 0 });
}
for (const width of [320, 256]) check("all 17 projected floors at " + width + ": atlas0, local cells, glyph geometry, player last and purity", () => {
  assert.equal(dungeons.length, 5); assert.equal(dungeons.reduce((n, d) => n + d.floors.length, 0), 17);
  for (let di = 0; di < dungeons.length; di++) for (let fi = 0; fi < dungeons[di].floors.length; fi++) {
    const s = session(width).setup(di, fi).lock(); s.draw(true); geometry(s);
    assert.ok(s.texts().some(t => t === "YOU+ U " + (fi === 0 ? "EXIT" : "UP") + " D DOWN C CHEST G GATE"));
    assert.ok(s.texts().includes(fi === 0 ? "EXIT HERE" : "UP STAIRS HERE"));
    if (fi === dungeons[di].floors.length - 1) assert.equal(s.c.map.grid.flat().includes("StairsDown"), false);
  }
});
function openedChest(production = source) {
  const s = session(256, production).setup().lock(), chest = s.c.map.info.chests[0], tileBefore = s.c.map.info.grid[chest.y][chest.x];
  s.c.api.openChest(chest.x, chest.y); assert.equal(s.c.map.grid[chest.y][chest.x], "ChestOpen"); assert.equal(tileBefore, "Chest");
  assert.equal(s.c.map.info.grid[chest.y][chest.x], "Chest", "authored metadata remains stale by design");
  assert.ok(s.c.opened.has("dungeon0/0:" + chest.x + "," + chest.y));
  s.draw(); const image = s.paints.filter(p => p.kind === "image")[chest.y * 40 + chest.x]; assert.equal(image.key, "dg:volcano:ChestOpen");
  const again = JSON.stringify({ bag: s.c.bag, gold: s.c.gold, opened: [...s.c.opened] }); s.c.api.openChest(chest.x, chest.y);
  assert.equal(JSON.stringify({ bag: s.c.bag, gold: s.c.gold, opened: [...s.c.opened] }), again); return s;
}
check("actual openChest changes live art/counts, preserves metadata and cannot award twice", () => { const s = openedChest(); assert.ok(s.texts().includes("CHESTS 1/2 OPEN")); });
check("saved opened flag is honored by legitimate map construction before pure rendering", () => {
  const s = session(), chest = dungeons[0].floors[0].chests[0]; s.c.opened.add("dungeon0/0:" + chest.x + "," + chest.y); s.setup().lock(); s.draw(); geometry(s);
  assert.equal(s.c.map.grid[chest.y][chest.x], "ChestOpen");
});
check("actual boss completion fade clears live gate without changing authored boss metadata", () => {
  const s = session(256).setup(0, 2).lock(), boss = s.c.D.dungeons[0].boss_data, gate = s.c.map.info.boss.gate;
  s.c.B = { result: "win", boss: true, prevCue: "CAVE", foes: [{ boss: true, bossName: boss.name, name: boss.name }], endLines: [] };
  s.c.api.finishBattle(); assert.equal(s.c.map.grid[gate.y][gate.x], "BossGate"); s.c.fadeCb();
  assert.ok(s.c.state.beaten.has(boss.name)); assert.equal(s.c.map.grid[gate.y][gate.x], "Floor"); assert.equal(s.c.map.info.grid[gate.y][gate.x], "BossGate");
  s.draw(); assert.equal(s.paints.filter(p => p.kind === "image")[gate.y * 40 + gate.x].key, "dg:volcano:Floor");
  assert.equal(s.paints.some(p => p.kind === "rect" && p.color === "#f8a0d0"), false); geometry(s);
});
check("already-beaten gate is removed by actual constructor and current-floor drawing reads no other floor", () => {
  const s = session().setup(4, 2), boss = s.c.D.dungeons[4].boss_data; s.c.state.beaten.add(boss.name); s.setup(4, 2).lock();
  const gate = s.c.map.info.boss.gate; assert.equal(s.c.map.grid[gate.y][gate.x], "Floor"); s.draw(); geometry(s);
  const floors = s.c.D.dungeons[4].floors; s.c.D.dungeons[4].floors = new Proxy(floors, { get(target, key) { if (key === "length") return target.length; throw new Error("floor sketch read another floor: " + String(key)); } });
  s.paints.length = 0; s.c.api.drawFloorSketch(); assert.equal(s.paints.filter(p => p.kind === "image").length, 1120);
});
check("player marker uses local floor coordinates, including tile-edge cells", () => {
  for (const [x, y] of [[0, 0], [39, 27], [19, 12]]) { const s = session(256).setup().lock(); s.c.P = { x, y }; s.c.state.returnTo = { x: 1, y: 1 }; s.draw(); geometry(s); }
});
check("missing tile rectangle paints one bounded fallback without initializing assets or maps", () => {
  const s = session(256).setup().lock(), tile = s.c.map.grid[0][0], key = s.c.map.key(tile); delete s.c.D.rects.tiles[key + "#0"]; s.draw();
  assert.ok(s.paints.some(p => p.kind === "rect" && p.color === "#243848" && p.x === 28 && p.y === 48 && p.w === 5 && p.h === 5));
  assert.equal(s.calls.lazy, 0); assert.equal(s.calls.save, 0); assert.equal(s.calls.rng, 0);
});
check("actual stair handler leaves floor0 for the world entrance, never local coordinates", () => {
  const s = session().setup(), entrance = s.c.D.world.flat().indexOf(s.c.D.dungeons[0].landmark); assert.ok(entrance >= 0);
  s.c.worldMap = () => ({ kind: "world", grid: s.c.D.world }); s.c.api.stepDone(); assert.equal(s.moves.length, 1);
  assert.deepEqual([s.moves[0].map.kind, s.moves[0].x, s.moves[0].y, s.moves[0].dir], ["world", entrance % 32, Math.floor(entrance / 32) + 1, "down"]);
});
check("actual deeper UP/DOWN handlers select adjacent floors; sketch never does", () => {
  const s = session().setup(0, 1); s.c.api.stepDone(); assert.equal(s.c.map.floor, 0); const prior = s.c.D.dungeons[0].floors[0].stairs_down;
  assert.deepEqual(s.c.P, { x: prior.x, y: prior.y });
  const down = s.c.map.info.stairs_down; s.c.P = { x: down.x, y: down.y }; s.c.api.stepDone(); assert.equal(s.c.map.floor, 1);
  const up = s.c.map.info.stairs_up; assert.deepEqual(s.c.P, { x: up.x, y: up.y }); s.c.menu.jp = 2; s.lock(); s.draw(); geometry(s);
  s.c.P = { x: up.x, y: up.y + 1 }; s.draw(); assert.equal(s.texts().includes("UP STAIRS HERE"), false);
});
check("standing on DOWN stairs receives contextual label, final floor exposes no down marker", () => {
  const s = session(256).setup(); s.c.P = { ...s.c.map.info.stairs_down }; s.lock(); s.draw(); assert.ok(s.texts().includes("DOWN STAIRS HERE")); geometry(s);
  s.setup(0, 2); s.draw(); assert.equal(s.c.map.grid.flat().filter(t => t === "StairsDown").length, 0); assert.equal(s.texts().includes("DOWN STAIRS HERE"), false);
});
check("dungeon pages cycle both directions; outside keeps exactly the original two pages", () => {
  const s = session().setup(); s.c.menu.jp = 0; for (const page of [1, 2, 0]) { s.tick("right"); assert.equal(s.c.menu.jp, page); }
  for (const page of [2, 1, 0]) { s.tick("left"); assert.equal(s.c.menu.jp, page); }
  s.c.map = { kind: "world" }; for (const page of [1, 0, 1, 0]) { s.tick("right"); assert.equal(s.c.menu.jp, page); }
  s.c.D.realm_key = "portal"; for (const page of [1, 0]) { s.tick("left"); assert.equal(s.c.menu.jp, page); }
});
function inputIsolation(production = source) {
  const s = session(256, production).setup().lock(), before = s.snapshot(); s.tick("up", "down", "a");
  assert.equal(s.snapshot(), before); assert.ok(["up", "down", "a"].every(k => !s.pressed[k])); assert.equal(s.calls.pinToast, 0);
  s.tick("left"); assert.equal(s.c.menu.jp, 1); s.tick(); assert.equal(s.c.menu.ii, 0); assert.equal(s.calls.pinToast, 0); return s;
}
check("floor page drains hidden route/Confirm edges across adjacent ticks", () => { inputIsolation(); });
check("entering or leaving floor with simultaneous page/Confirm consumes A without changing pin", () => {
  const s = session().setup(); s.c.menu.jp = 1; const opened = [...s.c.opened]; s.tick("right", "a", "down"); assert.equal(s.c.menu.jp, 2); assert.equal(s.c.menu.ii, 0);
  s.tick("left", "a"); assert.equal(s.c.menu.jp, 1); assert.equal(s.pressed.a, false); s.tick(); assert.deepEqual([...s.c.opened], opened);
  s.tick("left", "right", "a"); assert.equal(s.pressed.left, false); assert.equal(s.pressed.right, false); assert.equal(s.pressed.a, false); assert.equal(s.calls.pinToast, 0);
});
check("Back/Start wins over Confirm on floor and does not leak into the prior menu", () => {
  for (const key of ["b", "start"]) { const s = session().setup(), opened = [...s.c.opened]; s.tick(key, "a"); assert.equal(s.c.menu.sub, null); assert.equal(s.c.menu.idx, 9);
    assert.ok(["a", "b", "start"].every(k => !s.pressed[k])); s.tick(); assert.equal(s.c.menu.sub, null); assert.deepEqual([...s.c.opened], opened); }
});
check("notes/world route browsing and explicit pin still work; floor does not change their selection", () => {
  const s = session().setup(); s.c.menu.jp = 1; s.tick("down"); assert.equal(s.c.menu.ii, 1); s.tick("a"); assert.ok(s.c.opened.has("journey/pin/Tower"));
  const before = [...s.c.opened]; s.tick("right", "a"); assert.equal(s.c.menu.jp, 2); s.draw(true); s.tick("up", "down", "a"); assert.equal(s.c.menu.ii, 1); assert.deepEqual([...s.c.opened], before);
});
check("controlled stale metadata, animated-frame and missing edge-drain variants fail the same assertions", () => {
  const stale = source.replace("const grid = map.grid, height = grid.length", "const grid = map.info.grid, height = grid.length"); assert.notEqual(stale, source); assert.throws(() => openedChest(stale), assert.AssertionError);
  const animated = source.replace('D.rects.tiles[map.key(tile) + "#0"]', 'D.rects.tiles[map.key(tile) + "#1"]'); assert.notEqual(animated, source);
  assert.throws(() => { const s = session(256, animated).setup().lock(); s.draw(); geometry(s); }, assert.AssertionError);
  const leaked = source.replace('if (menu.jp === 2 && map.kind === "dungeon") { hit("up"); hit("down"); hit("a"); return; }', 'if (menu.jp === 2 && map.kind === "dungeon") { return; }'); assert.notEqual(leaked, source);
  assert.throws(() => inputIsolation(leaked), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("floor sketch: " + checks + " focused groups passed; actual source/canonical-grid canvas capture only, no assets/browser/native acceptance");
