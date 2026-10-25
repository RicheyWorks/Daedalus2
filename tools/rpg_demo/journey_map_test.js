// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/journey_map_test.js
// Actual notebook map/anchor/page/menu functions; canonical world/route/interior metadata.
// Atlas rectangles are canvas peers, not asset inspection. Waystone IDs are canonical; runtime display
// coordinates are explicitly assigned fixture positions on canonical walkable cells, not packer-parity evidence.
// No DOM, game IIFE, browser, Python/builder/shared-module execution, assets or native runtime.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8"), portal = fs.readFileSync(path.join(__dirname, "portal_realm.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const worldData = data("worldmap-tiles"), parties = data("party").party, layouts = data("menus").layouts, interiors = data("interiors").interiors;
const dungeonData = data("dungeons").dungeons, bosses = data("prism-bosses").bosses, spells = data("spells").spells;
const village = data("prism-village"), waystoneData = data("prism-waystones").waystones;
function tuples(text, name) { const found = text.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(found, name);
  return Array.from(found[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), m => [m[1], m[2]]); }
const main = tuples(builder, "QUEST"), extra = tuples(builder, "OPTIONAL_QUEST"), finalName = builder.match(/^FINAL = "([^"]+)"$/m)[1];
function routes(realm) { return (realm === "prism" ? main.concat(extra) : tuples(portal, "QUEST")).map(([landmark, name], i) => {
  const d = dungeonData[realm].find(d => d.name === name), boss = realm === "prism" ? bosses.find(b => b.dungeon === name) : null;
  assert.ok(d && (realm !== "prism" || boss)); return { ...clone(d), landmark, optional: realm === "prism" && i >= main.length,
    final: realm === "prism" && name === finalName, boss_data: boss ? clone(boss) : null }; }); }
function findCell(grid, name) { for (let y = 0; y < grid.length; y++) { const x = grid[y].indexOf(name); if (x >= 0) return { x, y }; } return null; }
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"), line("const find ="), line("function airUnlocked()"),
  between("const START_LEVEL =", "/* Recruits:"), line("const spellOf ="), between("const carriesShard =", "const chestKey ="),
  between("let menu = null;", "/* Four rows"), between("function drawMenu()", "function drawStatus()"), between("function titlePrompt(", "function drawTitle("),
  "this.api={ start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,drawJourney,drawJourneyMap,journeyAnchor,journeyStatus,journeyRoutes,airUnlocked," +
  "menu:()=>menu,chars:CHARS,resources:()=>({D,party,reserve,bag,gold,map,P,beaten:Array.from(state.beaten),ways:Array.from(state.ways),air:state.air," +
  "seen:state.seen,quests:state.quests,fish:state.fish,day:state.day,minute:state.minute,returnTo:state.returnTo,opened:Array.from(opened),held,SRC}),view:()=>({mode,menu,pressed})};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], pressed = {}, sounds = [], calls = { lazy: 0, save: 0, travel: 0 }, gear = {}, tiles = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const item of shop.stock || [])
    if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
  const world = clone(worldData.demo_maps[realm]), tileInfo = Object.fromEntries(worldData.tiles.filter(t => t.realm === realm).map(t => [t.tile, clone(t)]));
  const tileNames = [...new Set(world.flat())]; tileNames.forEach((name, i) => { tiles["wm:" + name + "#0"] = [i * 32, 0, 16, 16]; tiles["wm:" + name + "#1"] = [i * 32 + 16, 0, 16, 16]; });
  const spots = []; world.forEach((row, y) => row.forEach((name, x) => { if (tileInfo[name] && tileInfo[name].walkable && tileInfo[name].kind !== "landmark") spots.push({ x, y }); }));
  assert.ok(spots.length >= waystoneData.length);
  const runtimeWays = realm === "prism" ? waystoneData.map((w, i) => ({ ...clone(w), ...spots[i] })) : [];
  const town = findCell(world, "Town"); assert.ok(town);
  const fixedMath = Object.create(Math); fixedMath.random = () => { throw new Error("map cannot consume gameplay randomness"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(layouts[realm]), dungeons: routes(realm), world,
      world_tiles: tileInfo, interiors: clone(interiors[realm]), village: clone(village), waystones: runtimeWays,
      spells: clone(spells.filter(s => s.realm === realm)), rects: { sprites: {}, tiles }, frames: Object.fromEntries(tileNames.map(n => [n, 2])),
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: fixedMath, IM: { tiles: "world-atlas" }, B: null, mode: "field", map: { kind: "world" },
    P: { x: town.x, y: town.y + 1 }, pressed, held: { right: true }, SRC: { kb: { right: true } }, opened: new Set(["existing/chest"]),
    state: { beaten: new Set(), ways: new Set(), air: null, seen: {}, quests: {}, fish: {}, returnTo: null, day: 1, minute: 480 },
    PAD: null, sfx: k => sounds.push(k), toast() {}, drawField() {}, drawPartyRows() {}, clockText: () => "D1 08:00", isNight: () => false,
    airship() { calls.lazy++; throw new Error("map cannot initialize airship state"); },
    saveGame() { calls.save++; throw new Error("map cannot save"); }, goto() { calls.travel++; throw new Error("map cannot travel"); },
    enterDungeon() { calls.travel++; throw new Error("map cannot enter a route"); }, openSettings() {},
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: value => String(value).length * 6,
    text: (value, x, y, color = "#ffffff", shadow = "#202040") => paints.push({ kind: "text", label: String(value).toUpperCase(), x, y, w: String(value).length * 6, h: 8, color, shadow }),
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }), cursor: (x, y) => paints.push({ kind: "cursor", x, y }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); },
      drawImage(image, sx, sy, sw, sh, x, y, w, h) { paints.push({ kind: "image", image, sx, sy, sw, sh, x, y, w, h }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, pressed, calls, sounds, resources,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), callBefore = JSON.stringify(calls), soundCount = sounds.length;
      c.api.drawMenu(); assert.equal(resources(), before, "map drawing cannot mutate progress, resources, world, roster, air or held sources");
      assert.equal(JSON.stringify(c.api.view()), view, "drawing preserves menu selection and buffered inputs");
      assert.equal(JSON.stringify(calls), callBefore); assert.equal(sounds.length, soundCount); return paints; }
  };
}
function openMap(s) { s.api.openMenu(); for (let i = 0; i < 9; i++) s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "journey"); assert.equal(s.api.menu().jp, 0);
  s.tick("right"); assert.equal(s.api.menu().jp, 1); return s; }
function geometry(s) { const h = s.c.D.world.length, w = s.c.D.world[0].length, cell = Math.max(1, Math.min(8, Math.floor((s.c.W - 32) / w), Math.floor(140 / h)));
  return { h, w, cell, x0: Math.floor((s.c.W - w * cell) / 2), y0: 48 + Math.floor((140 - h * cell) / 2) }; }
function glyph(s, p, text) { const a = geometry(s); return s.paints.find(d => d.kind === "text" && d.label === text && d.x === a.x0 + p.x * a.cell + Math.floor(a.cell / 2) - 2 && d.y === a.y0 + p.y * a.cell + Math.floor(a.cell / 2) - 3); }
function cross(s, p) { const a = geometry(s), x = a.x0 + p.x * a.cell + Math.floor(a.cell / 2), y = a.y0 + p.y * a.cell + Math.floor(a.cell / 2);
  const marks = s.paints.filter(d => d.kind === "rect" && d.color === "#ffdf83");
  assert.deepEqual(marks.map(d => [d.x, d.y, d.w, d.h]), [[x - 2, y, 5, 1], [x, y - 2, 1, 5]]); return marks; }
function assertCells(s) {
  const a = geometry(s), images = s.paints.filter(d => d.kind === "image"); assert.equal(images.length, a.w * a.h);
  images.forEach((d, i) => { const x = i % a.w, y = Math.floor(i / a.w), rect = s.c.D.rects.tiles["wm:" + s.c.D.world[y][x] + "#0"];
    assert.deepEqual([d.image, d.sx, d.sy, d.sw, d.sh], ["world-atlas", rect[0], rect[1], 16, 16], "map reads frame zero directly");
    assert.deepEqual([d.x, d.y, d.w, d.h], [a.x0 + x * a.cell, a.y0 + y * a.cell, a.cell, a.cell]);
    assert.ok(d.x >= 0 && d.x + d.w <= s.c.W && d.y >= 48 && d.y + d.h <= 188);
  });
  for (const d of s.paints) if (d.kind === "text") { assert.ok(d.x >= 0 && d.x + d.w <= s.c.W && d.y >= 0 && d.y + d.h <= 224); assert.ok([...d.label].every(k => s.api.chars.includes(k))); }
}
function castleAnchor(s) {
  s.c.map = { kind: "interior", name: "Castle" }; s.c.P = { x: 7, y: 6 };
  const expected = findCell(s.c.D.world, "Castle"); assert.ok(expected); const got = s.api.journeyAnchor();
  assert.deepEqual(clone(got), { ...expected, label: "INSIDE CASTLE" }); return got;
}
for (const width of [320, 256]) check("canonical world cells, atlas frame zero, text and markers fit at " + width, () => {
  const s = openMap(session(width)); s.draw(); assertCells(s); cross(s, s.c.P);
  assert.ok(s.paints.some(p => p.kind === "text" && p.y === 34 && p.label.startsWith("YOU +")));
});
check("world and aboard anchors use actual world coordinates without lazy skiff initialization", () => {
  const s = openMap(session()), town = findCell(s.c.D.world, "Town"); s.c.P = { x: town.x, y: town.y + 1 };
  assert.deepEqual(clone(s.api.journeyAnchor()), { ...s.c.P, label: "ON THE WORLD MAP." }); s.draw(); assert.equal(s.c.state.air, null);
  s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x: s.c.P.x, y: s.c.P.y, aboard: true };
  assert.deepEqual(clone(s.api.journeyAnchor()), { ...s.c.P, label: "ABOARD THE PRISM SKIFF." }); s.draw(); cross(s, s.c.P);
  assert.equal(s.paints.filter(p => p.kind === "text" && p.label === "S").length, 0); assert.equal(s.calls.lazy, 0);
});
for (const width of [320, 256]) check("town, village, every interior and all dungeon floors use world entrances at " + width, () => {
  const s = openMap(session(width)), cases = [{ map: { kind: "town" }, pos: { x: 11, y: 16 }, landmark: "Town", label: "INSIDE TOWN" },
    { map: { kind: "village" }, pos: { x: village.spawn.x, y: village.spawn.y }, landmark: village.landmark, label: "INSIDE " + village.name.toUpperCase() }];
  for (const [name, room] of Object.entries(s.c.D.interiors)) cases.push({ map: { kind: "interior", name }, pos: { x: room.spawn.x, y: room.spawn.y },
    landmark: room.opened_by && room.opened_by.map === "overworld" ? room.opened_by.landmark : "Town", label: "INSIDE " + name.toUpperCase() });
  s.c.D.dungeons.forEach((d, di) => d.floors.forEach((fl, floor) => cases.push({ map: { kind: "dungeon", dungeon: di, floor },
    pos: { x: fl.stairs_up.x, y: fl.stairs_up.y }, landmark: d.landmark, label: "INSIDE " + d.name.toUpperCase() })));
  for (const item of cases) { s.c.map = item.map; s.c.P = item.pos; const at = findCell(s.c.D.world, item.landmark); assert.ok(at);
    assert.deepEqual(clone(s.api.journeyAnchor()), { ...at, label: item.label }); s.draw(); cross(s, at);
    assert.ok(s.paints.some(p => p.kind === "text" && p.y === 34 && p.label.startsWith("ENTRANCE +")));
  }
  castleAnchor(s);
});
for (const width of [320, 256]) check("selected canonical route border and live completion status agree at " + width, () => {
  const s = openMap(session(width)), a = geometry(s), ds = s.api.journeyRoutes();
  for (const beaten of [[], [ds[0].boss_data.name], ds.slice(0, 3).map(d => d.boss_data.name), ds.map(d => d.boss_data.name)]) {
    s.c.state.beaten = new Set(beaten);
    for (let i = 0; i < ds.length; i++) { s.api.menu().ii = i; s.draw(); const d = ds[i], dest = findCell(s.c.D.world, d.landmark), x = a.x0 + dest.x * a.cell, y = a.y0 + dest.y * a.cell;
      const border = s.paints.filter(p => p.kind === "rect" && p.color === "#ffffff");
      assert.deepEqual(border.map(p => [p.x, p.y, p.w, p.h]), [[x, y, a.cell, 1], [x, y + a.cell - 1, a.cell, 1], [x, y, 1, a.cell], [x + a.cell - 1, y, 1, a.cell]]);
      assert.ok(s.paints.some(p => p.kind === "text" && p.y === 198 && p.label === (d.name + " - " + s.api.journeyStatus(d).word).toUpperCase().slice(0, Math.floor((width - 24) / 6))));
    }
  }
});
check("only awake canonical waystone IDs get O markers (assigned runtime display positions, not packer parity)", () => {
  const s = openMap(session()), ws = s.c.D.waystones; s.c.state.ways = new Set([ws[1].id, ws[3].id]); s.draw();
  assert.equal(s.paints.filter(p => p.kind === "text" && p.label === "O").length, 2);
  ws.forEach((w, i) => assert.equal(!!glyph(s, w, "O"), i === 1 || i === 3));
});
check("locked skiff stays hidden; unlocked null air shows its dock without creating state", () => {
  const s = openMap(session()), dock = findCell(s.c.D.world, "AirshipPad"); assert.ok(dock); s.draw();
  assert.equal(s.paints.some(p => p.kind === "text" && p.label === "S"), false); assert.equal(s.c.state.air, null);
  s.c.state.beaten.add(s.c.D.dungeons[1].boss_data.name); s.draw(); assert.equal(s.paints.some(p => p.kind === "text" && p.label === "S"), false, "the existing unlock condition is retained");
  s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.draw(); assert.ok(glyph(s, dock, "S")); assert.equal(s.c.state.air, null); assert.equal(s.calls.lazy, 0);
});
check("a parked skiff is drawn at its saved world position rather than reset to the dock", () => {
  for (const width of [320, 256]) {
    const s = openMap(session(width)), dock = findCell(s.c.D.world, "AirshipPad"), parked = s.c.D.waystones[2];
    s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x: parked.x, y: parked.y, aboard: false }; s.draw();
    assert.ok(glyph(s, parked, "S")); assert.equal(s.paints.filter(p => p.kind === "text" && p.label === "S").length, 1);
    assert.equal(!!glyph(s, dock, "S"), parked.x === dock.x && parked.y === dock.y); assert.equal(s.calls.lazy, 0);
  }
});
check("parked and aboard skiff markers preserve actual air state and YOU is painted above co-located markers", () => {
  for (const width of [320, 256]) {
    const s = openMap(session(width)), dock = findCell(s.c.D.world, "AirshipPad"); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name);
    s.c.state.air = { x: dock.x, y: dock.y, aboard: false }; s.c.P = { ...dock }; s.api.menu().ii = 4;
    s.c.D.waystones[0] = { ...s.c.D.waystones[0], ...dock }; s.c.state.ways.add(s.c.D.waystones[0].id); s.draw();
    const o = glyph(s, dock, "O"), ship = glyph(s, dock, "S"), plus = cross(s, dock), border = s.paints.filter(p => p.kind === "rect" && p.color === "#ffffff");
    assert.ok(o && ship); assert.ok(s.paints.indexOf(o) < s.paints.indexOf(ship)); assert.ok(s.paints.indexOf(ship) < s.paints.indexOf(border[0]));
    assert.ok(s.paints.indexOf(border.at(-1)) < s.paints.indexOf(plus[0])); assert.ok(s.paints.some(p => p.kind === "text" && p.y === 22 && p.label.includes("SKIFF HERE.")));
    s.c.state.air.aboard = true; s.draw(); assert.equal(s.paints.some(p => p.kind === "text" && p.label === "S"), false); cross(s, dock);
  }
});
check("missing dock and missing entrance are display-only refusals, not lazy world edits", () => {
  const s = openMap(session()), dock = findCell(s.c.D.world, "AirshipPad"); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name);
  const replacement = s.c.D.world[s.c.D.waystones[0].y][s.c.D.waystones[0].x]; s.c.D.world[dock.y][dock.x] = replacement;
  s.draw(); assert.equal(s.paints.some(p => p.kind === "text" && p.label === "S"), false); assert.equal(s.c.state.air, null);
  s.c.map = { kind: "dungeon", dungeon: 4, floor: 0 }; assert.equal(s.api.journeyAnchor(), null); s.draw();
  assert.ok(s.paints.some(p => p.kind === "text" && p.y === 22 && p.label === "WORLD ENTRANCE UNKNOWN."));
  assert.equal(s.paints.filter(p => p.kind === "rect" && p.color === "#ffdf83").length, 0); assert.equal(s.calls.lazy, 0);
});
check("missing atlas entries use bounded cell fills without changing canonical world tiles", () => {
  const s = openMap(session()), name = s.c.D.world[0][0]; delete s.c.D.rects.tiles["wm:" + name + "#0"]; s.draw();
  const expected = s.c.D.world.flat().filter(n => n === name).length, fills = s.paints.filter(p => p.kind === "rect" && p.color === "#243848"), a = geometry(s);
  assert.equal(fills.length, expected); assert.ok(fills.every(p => p.w === a.cell && p.h === a.cell && p.y >= 48 && p.y + p.h <= 188));
});
function bothPageEdges(production = source) {
  const s = openMap(session(320, "prism", production)); s.tick("left"); assert.equal(s.api.menu().jp, 0); const selected = s.api.menu().ii;
  s.tick("left", "right", "a"); assert.equal(s.api.menu().jp, 1); assert.equal(s.api.menu().ii, selected);
  assert.ok(!s.pressed.left && !s.pressed.right && !s.pressed.a); s.tick(); assert.equal(s.api.menu().jp, 1, "second page edge cannot leak into the next tick"); return s;
}
check("both page directions are consumed once and route selection/Confirm never initiates travel", () => {
  const s = bothPageEdges(), before = s.resources(); s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.label === "MAP"));
  s.tick("left"); s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.label === "JOURNEY"));
  s.tick("up"); assert.equal(s.api.menu().ii, 4); s.tick("down"); assert.equal(s.api.menu().ii, 0); s.tick("right", "a"); s.tick("a");
  assert.equal(s.resources(), before); assert.equal(s.calls.travel, 0); assert.equal(s.calls.save, 0); assert.equal(s.calls.lazy, 0);
});
for (const key of ["b", "start"]) check(key + " exits either page before simultaneous Confirm and preserves the menu destination", () => {
  for (const page of [0, 1]) { const s = openMap(session()); if (!page) s.tick("left"); const before = s.resources(); s.tick(key, "a");
    assert.equal(s.api.menu().sub, null); assert.equal(s.api.menu().idx, 9); assert.ok(["a", "b", "start"].every(k => !s.pressed[k])); s.tick(); assert.equal(s.api.menu().sub, null);
    assert.equal(s.resources(), before); s.tick("a"); assert.equal(s.api.menu().jp, 0, "fresh notebook entry starts on notes"); }
});
check("Portal retains its real nine-entry menu and cannot accidentally select a map page", () => {
  const s = session(256, "portal"); s.api.openMenu(); s.tick("up"); assert.equal(s.api.menu().idx, 8); s.tick("down"); assert.equal(s.api.menu().idx, 0);
  for (let i = 0; i < 9; i++) { s.draw(); assert.equal(s.paints.some(p => p.kind === "text" && p.label === "JOURNEY"), false); s.tick("down"); }
  assert.equal(s.api.menu().idx, 0); assert.equal(s.api.menu().sub, null); assert.equal(s.calls.save, 0);
});
check("controlled local-coordinate anchor, short-circuit page edge and animated atlas variants fail the same invariants", () => {
  const wrongCastle = source.replace(/opening\.map === ["']overworld["'] \? opening\.landmark : ["']Town["']/, '"Town"'); assert.notEqual(wrongCastle, source);
  assert.throws(() => castleAnchor(openMap(session(320, "prism", wrongCastle))), assert.AssertionError);
  const stale = source.replace('const left = hit("left"), right = hit("right");', 'const left = hit("left"), right = left || hit("right");'); assert.notEqual(stale, source);
  assert.throws(() => bothPageEdges(stale), assert.AssertionError);
  const animated = source.replace('D.rects.tiles["wm:" + D.world[y][x] + "#0"]', 'D.rects.tiles["wm:" + D.world[y][x] + "#1"]'); assert.notEqual(animated, source);
  assert.throws(() => { const s = openMap(session(320, "prism", animated)); s.draw(); assertCells(s); }, assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("journey map: " + checks + " focused groups passed; command capture/runtime fixtures only, no packer/asset/browser acceptance");
