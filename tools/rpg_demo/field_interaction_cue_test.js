// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/field_interaction_cue_test.js
// Actual cue/fieldTick/interact/board/land/BossGate queries against canonical grids.
// Placements, branch-dispatch, sprites/tiles/glow and storage peers are explicit; no quests/fights/assets/runtime.
// Only direct cue query/chip painting is claimed pure. Whole drawField inherits its existing airship behavior.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n"), build = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const wm = data("worldmap-tiles"), towns = data("town-tiles"), village = data("prism-village"), interiors = data("interiors"), rawDungeons = data("dungeons"), bosses = data("prism-bosses").bosses;
const world = wm.demo_maps.prism, wt = Object.fromEntries(wm.tiles.filter(t => t.realm === "prism").map(t => [t.tile, t])), tt = Object.fromEntries(towns.tiles.filter(t => t.realm === "prism").map(t => [t.tile, t]));
const it = Object.fromEntries(interiors.tiles.filter(t => t.realm === "prism").map(t => [t.tile, t])), fish = data("prism-fish").fish, ways = data("prism-waystones").waystones;
const skyLoot = JSON.parse(build.match(/^SKY_LOOT = (\[[^\r\n]+\])$/m)[1]);
const specs = ["QUEST", "OPTIONAL_QUEST"].flatMap(name => [...build.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m"))[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]));
const dungeons = specs.map(([landmark, name], index) => ({ ...clone(rawDungeons.dungeons.prism.find(d => d.name === name)), landmark, optional: index >= 4, final: index === 3, boss_data: clone(bosses.find(b => b.dungeon === name)) }));
const dirs = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const source = [line("const CHARS ="), line("const tw ="), line("const T ="), line("const hit ="), line("const DIRS ="), line("const DIR_ROW ="), line("const find ="), line("const at ="), line("const npcAt ="), line("const pretty ="),
  line("function airUnlocked()"), line("const flying ="), line("const follyDungeon ="), line("const AIR_SPEED ="),
  between("function boardAirship()", "const flying ="), between("const LINES =", "function innPrompt("),
  between("function fieldTick(", "function land()"), between("function land()", "function drawAirship("),
  between("function fieldInteractionCue()", "/* ---------- fishing"), between("function dark()", "/* ---------- the airship"),
  between("function bossGate()", "function spellHint("), between("function titlePrompt(", "function drawTitle("),
  // Dispatch probes wrap the real functions without replacing their bodies; pure query/chip calls must not enter them.
  "const cueRealInteract=interact,cueRealLand=land,cueRealBoard=boardAirship,cueRealBoss=bossGate;" +
  "interact=(...args)=>{probe('interact',args);return cueRealInteract(...args);};land=(...args)=>{probe('land',args);return cueRealLand(...args);};" +
  "boardAirship=(...args)=>{probe('boardAirship',args);return cueRealBoard(...args);};bossGate=(...args)=>{probe('bossGate',args);return cueRealBoss(...args);};",
  "this.api={fieldInteractionCue,drawFieldInteractionCue,drawField,fieldTick,interact,boardAirship,land,bossGate,find," +
  "chars:CHARS,snapshot:()=>({D,map,P,mode,dlg,fade,settingsFramePaused,party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),pressed,held})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320) {
  let phase = "pure"; const paints = [], events = [], counters = { rng: 0, storage: 0 }, math = Object.create(Math);
  math.random = () => { counters.rng++; throw new Error("cue must not use RNG"); };
  const paintAccess = new Set(["airship", "drawAirship", "WAYS"]);
  function probe(name, args = []) { if (phase !== "action" && !(phase === "paint" && paintAccess.has(name))) throw new Error("pure cue entered action/accessor: " + name); events.push({ name, args: args.map(x => typeof x === "function" ? "callback" : x) }); }
  const c = { D: { realm_key: "prism", world: clone(world), world_tiles: clone(wt), town_tiles: clone(tt), interior_tiles: clone(it), interiors: clone(interiors.interiors.prism),
      dungeons: clone(dungeons), fish: clone(fish), sky_caches: [], waystones: [], frames: {}, village: clone(village) },
    W: width, H: 224, Math: math, pressed: {}, held: {}, mode: "field", dlg: null, fade: 0, settingsFramePaused: false, map: null,
    P: { x: 0, y: 0, fx: 0, fy: 0, dir: "down", moving: 0, step: 0 }, party: [{ name: "Corin", hp: 1, max: 84, mp: 0, mmax: 0, status: { poison: true } }], reserve: [], bag: {}, gold: 321,
    state: { air: null, beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, steps: 0, sinceBattle: 0, day: 1, minute: 600 }, opened: new Set(), PAD: null,
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), performance: { now: () => 0 }, probe,
    roster: () => c.party.concat(c.reserve), sfx: (...a) => probe("sfx", a), toast: (...a) => probe("toast", a),
    say(lines, then, voice) { probe("say", [lines, then, voice]); c.dlg = { pages: [].concat(lines), then, voice }; }, ask(question, options, then) { probe("ask", [question, options, then]); c.dlg = { question, options, then }; },
    airship() { probe("airship"); if (!c.state.air) { assert.notEqual(phase, "paint", "whole-field paint fixture must preseed the ship"); const p = c.api.find(c.D.world, "AirshipPad"); c.state.air = p ? { x: p[0], y: p[1], aboard: false } : null; } return c.state.air; },
    cacheAt: (...a) => { probe("cacheAt", a); return null; }, openCache: (...a) => probe("openCache", a), recoverAir: (...a) => probe("recoverAir", a),
    enterDungeon: (...a) => probe("enterDungeon", a), startBattle: (...a) => probe("startBattle", a), castLine: (...a) => probe("castLine", a), openChest: (...a) => probe("openChest", a),
    openShop: (...a) => probe("openShop", a), innPrompt: (...a) => probe("innPrompt", a), workshopPrompt: (...a) => probe("workshopPrompt", a), villageRequest: (...a) => probe("villageRequest", a),
    openMenu: (...a) => probe("openMenu", a), dialogTick: (...a) => probe("dialogTick", a), stepDone: (...a) => probe("stepDone", a),
    clearAll(list) { probe("clearAll"); list.forEach(m => { if (m.status) delete m.status.poison; }); },
    worldMap: (...a) => probe("worldMap", a), townMap: (...a) => probe("townMap", a), villageMap: (...a) => probe("villageMap", a), interiorMap: (...a) => probe("interiorMap", a), dungeonMap: (...a) => probe("dungeonMap", a),
    WAYS: () => { probe("WAYS"); return c.D.waystones; }, drawAirship: (...a) => { probe("drawAirship", a); paints.push({ kind: "ship", x: a[0], y: a[1] }); }, skyKey: p => "sky:" + p.x + "," + p.y,
    tileImg: (key, x, y) => { paints.push({ kind: "tile", key, x, y }); return true; }, spr: (sheet, name, x, y, sx, w = 16, h = 16) => paints.push({ kind: "sprite", name, x, y, w, h }),
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); }, createRadialGradient() { const gradient = { kind: "gradient", stops: [], addColorStop(...args) { this.stops.push(args); } }; return gradient; } },
    localStorage: { getItem() { counters.storage++; throw new Error("no native storage"); }, setItem() { counters.storage++; throw new Error("no native storage"); }, removeItem() { counters.storage++; throw new Error("no native storage"); } }
  };
  vm.createContext(c); vm.runInContext(source, c, { timeout: 1000 });
  function snapshot() { return JSON.stringify({ game: c.api.snapshot(), events, counters }); }
  function pure(fn) { const before = snapshot(); const result = fn(); assert.equal(snapshot(), before, "query/chip changes neither state, NPC facing, resources, input, progress nor action counters"); return result; }
  function action(fn) { phase = "action"; try { return fn(); } finally { phase = "pure"; } }
  return { c, api: c.api, paints, events, counters, snapshot, action,
    query: () => pure(() => c.api.fieldInteractionCue()),
    chip(oy = 0) { paints.length = 0; pure(() => c.api.drawFieldInteractionCue(oy)); return paints; },
    press() { Object.keys(c.pressed).forEach(k => { c.pressed[k] = false; }); c.pressed.a = true; action(() => c.api.fieldTick(0)); },
    paintField() { paints.length = 0; phase = "paint"; try { c.api.drawField(); } finally { phase = "pure"; } return paints; },
    labels(label = "ABCDEFGH") { c.PAD = { devices: () => [{ index: 0 }], label: action => { assert.equal(action, "confirm"); return label; } }; }
  };
}
function fixture(s, kind = "town", name) {
  let info, grid, npcs, key, walk;
  if (kind === "world") { grid = clone(s.c.D.world); npcs = []; key = tile => "wm:" + tile; walk = tile => !!((wt[tile] || {}).walkable || (wt[tile] || {}).kind === "landmark"); }
  else if (kind === "town" || kind === "village") { info = kind === "town" ? towns.demo_towns.prism : village; grid = clone(info.grid); npcs = info.npcs.map(n => ({ ...clone(n), dir: n.facing })); key = tile => "town:" + tile; walk = tile => !!(tt[tile] || {}).walkable; }
  else if (kind === "interior") { info = s.c.D.interiors[name]; grid = clone(info.grid); npcs = info.npcs.map(n => ({ ...clone(n), dir: n.facing })); key = tile => (s.c.D.frames["int:" + tile] ? "int:" : "town:") + tile; walk = tile => !!(it[tile] || tt[tile] || {}).walkable; }
  else { const di = name === undefined ? 0 : name, dungeon = s.c.D.dungeons[di], floor = dungeon.floors.length - 1; info = dungeon.floors[floor]; grid = clone(info.grid); npcs = []; key = tile => "dg:" + dungeon.theme + ":" + tile; walk = tile => rawDungeons.walkable.concat(["Hazard", "StairsUp", "StairsDown"]).includes(tile); s.c.map = { kind, dungeon: di, floor, info, grid, npcs, key, walk }; return s.c.map; }
  s.c.map = { kind, name, info, grid, npcs, key, walk }; return s.c.map;
}
function place(s, x, y, dir) { Object.assign(s.c.P, { x, y, fx: x * 16, fy: y * 16, dir, moving: 0 }); }
function faceTile(s, tile) {
  const map = s.c.map;
  for (let y = 0; y < map.grid.length; y++) for (let x = 0; x < map.grid[y].length; x++) if (map.grid[y][x] === tile) {
    for (const [dir, [dx, dy]] of Object.entries(dirs)) { const px = x - dx, py = y - dy, cell = map.grid[py] && map.grid[py][px];
      if (cell === undefined || !map.walk(cell) || map.npcs.some(n => n.x === px && n.y === py)) continue;
      if (map.npcs.some(n => n.x === x && n.y === y)) continue;
      place(s, px, py, dir); return { x, y };
    }
  }
  throw new Error("no faceable canonical tile: " + tile);
}
function ground(s, predicate) { for (let y = 1; y < s.c.D.world.length - 1; y++) for (let x = 1; x < s.c.D.world[y].length - 1; x++) if (predicate(wt[s.c.D.world[y][x]] || {}, s.c.D.world[y][x])) { place(s, x, y, "up"); return [x, y]; } throw new Error("canonical ground fixture missing"); }
const text = s => s.paints.find(p => p.kind === "text"), panel = s => s.paints.find(p => p.kind === "rect" && p.h === 16 && p.color === "#080c20");
function chipBounds(s) { const p = panel(s), t = text(s); assert.ok(p && t); assert.ok(p.x >= 0 && p.x + p.w <= s.c.W && p.y >= 0 && p.y + p.h <= 224); assert.ok(t.x >= p.x + 8 && t.x + t.w <= p.x + p.w - 8 && t.y >= p.y && t.y + t.h <= p.y + p.h); assert.ok([...t.label].every(ch => s.api.chars.includes(ch))); }
const hasEvent = (s, name) => s.events.some(e => e.name === name);
check("query/chip stay observational and are suppressed by nonfield modes, movement, dialog, fade, pause or Portal", () => {
  const s = session(); fixture(s, "interior", "Magic"); faceTile(s, "Bookcase"); s.c.pressed = { a: true, b: true, start: true, down: true }; s.c.held = { right: true }; assert.equal(s.query(), "READ"); s.chip(); chipBounds(s);
  for (const mode of ["menu", "battle", "name", "ending", "gameover"]) { s.c.mode = mode; assert.equal(s.query(), ""); s.chip(); assert.equal(s.paints.length, 0); } s.c.mode = "field";
  for (const [key, value] of [["dlg", { pages: ["PENDING"] }], ["fade", 1], ["settingsFramePaused", true]]) { const previous = s.c[key]; s.c[key] = value; assert.equal(s.query(), ""); s.chip(); assert.equal(s.paints.length, 0); s.c[key] = previous; }
  s.c.P.moving = 0.5; assert.equal(s.query(), ""); s.chip(); assert.equal(s.paints.length, 0); s.c.P.moving = 0; s.c.D.realm_key = "portal"; assert.equal(s.query(), ""); s.chip(); assert.equal(s.paints.length, 0); assert.equal(s.events.length, 0);
});
check("canonical counter NPCs beat objects, query never turns them, and Confirm reaches actual talk/service dispatch", () => {
  const s = session(), map = fixture(s, "interior", "Item"), merchant = map.npcs[0]; place(s, merchant.x, merchant.y + 2, "up"); assert.equal(map.grid[merchant.y + 1][merchant.x], "Counter");
  merchant.dir = "left"; const facing = merchant.dir; assert.equal(s.query(), "TALK"); s.chip(); assert.equal(merchant.dir, facing); s.press(); assert.ok(hasEvent(s, "interact") && hasEvent(s, "say")); assert.equal(merchant.dir, "down"); assert.equal(typeof s.c.dlg.then, "function"); s.action(() => s.c.dlg.then()); assert.ok(hasEvent(s, "openShop"));
  s.c.dlg = null; map.grid[s.c.P.y - 1][s.c.P.x] = "Chest"; map.npcs.push({ type: "Guard", x: s.c.P.x, y: s.c.P.y - 1, dir: "left" }); assert.equal(s.query(), "TALK", "direct NPC precedes chest");
});
check("all coded object labels follow live tiles and existing container-open keys without awarding while read", () => {
  for (const [room, tile, cue] of [["Castle", "Chest", "OPEN"], ["Item", "Barrel", "SEARCH"], ["Item", "Crate", "SEARCH"], ["Magic", "Pot", "SEARCH"], ["Magic", "Bookcase", "READ"], ["Castle", "Throne", "EXAMINE"]]) {
    const s = session(); fixture(s, "interior", room);
    // The Ruler occupies the canonical throne's only walkable neighbor. Clear NPCs in this
    // explicit branch-isolation fixture; do not claim ordinary unmodified throne reachability.
    if (tile === "Throne") s.c.map.npcs = [];
    const at = faceTile(s, tile); assert.equal(s.query(), cue); s.chip(); chipBounds(s);
    if (["Barrel", "Crate", "Pot"].includes(tile)) { s.c.opened.add("wrong:" + at.x + "," + at.y); assert.equal(s.query(), "SEARCH"); s.c.opened.add("interior" + at.x + "," + at.y); assert.equal(s.query(), "CHECK"); }
    if (tile === "Chest") { s.c.map.grid[at.y][at.x] = "ChestOpen"; assert.equal(s.query(), "CHECK"); s.press(); assert.ok(hasEvent(s, "openChest")); }
    if (["Bookcase", "Throne"].includes(tile)) { s.press(); assert.ok(hasEvent(s, "say")); }
  }
  const fountain = session(); fixture(fountain); faceTile(fountain, "Fountain"); assert.equal(fountain.query(), "DRINK"); fountain.press(); assert.ok(hasEvent(fountain, "clearAll") && hasEvent(fountain, "say"));
});
check("fishing is offered only at faced town/village water with fish metadata, then uses actual interaction dispatch", () => {
  for (const kind of ["town", "village"]) { const s = session(); fixture(s, kind); let target;
    if (kind === "village") target = faceTile(s, "Water"); else { // Explicit town shoreline placement: same canonical Water/Grass tiles, not a route claim.
      place(s, 1, 1, "right"); s.c.map.grid[1][2] = "Water"; s.c.map.npcs = []; target = { x: 2, y: 1 }; }
    assert.equal(s.query(), "FISH"); s.press(); assert.deepEqual(s.events.find(e => e.name === "castLine").args, [target.x, target.y]); s.c.D.fish = []; assert.equal(s.query(), ""); s.c.D.fish = clone(fish); s.c.map.kind = "interior"; assert.equal(s.query(), "");
  }
});
check("an undefeated live BossGate offers CHALLENGE and Confirm opens the real confirmation before the battle peer", () => {
  const s = session(); fixture(s, "dungeon", 0); faceTile(s, "BossGate"); assert.equal(s.query(), "CHALLENGE"); s.chip(); chipBounds(s); s.press(); assert.ok(hasEvent(s, "bossGate") && hasEvent(s, "ask")); assert.deepEqual(Array.from(s.c.dlg.options), ["YES", "NO"]); assert.ok(!hasEvent(s, "startBattle")); s.action(() => s.c.dlg.then(0)); assert.ok(hasEvent(s, "startBattle"));
  s.c.dlg = null; s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); assert.equal(s.query(), ""); s.c.D.dungeons[0].boss_data = null; assert.equal(s.query(), "");
});
check("default parked skiff query uses pure dock find, while actual Confirm alone initializes/boards it", () => {
  const s = session(); fixture(s, "world"); const dock = s.api.find(s.c.D.world, "AirshipPad"); place(s, dock[0], dock[1], "down"); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name);
  assert.equal(s.c.state.air, null); assert.equal(s.query(), "BOARD"); s.chip(); assert.equal(s.c.state.air, null); assert.equal(s.events.length, 0); s.press(); assert.ok(hasEvent(s, "boardAirship") && hasEvent(s, "airship")); assert.equal(s.c.state.air.aboard, true);
  const locked = session(); fixture(locked, "world"); place(locked, dock[0], dock[1], "down"); assert.notEqual(locked.query(), "BOARD"); assert.equal(locked.c.state.air, null);
});
check("parked-underfoot boarding outranks facing Folly, while adjacent dock examination preserves its real entry dispatch", () => {
  const s = session(); fixture(s, "world"); const dock = s.api.find(s.c.D.world, "AirshipPad"); place(s, dock[0], dock[1] + 1, "up"); assert.equal(s.query(), "EXAMINE"); s.press(); assert.equal(s.events.find(e => e.name === "enterDungeon").args[0], 4);
  s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x: s.c.P.x, y: s.c.P.y, aboard: false }; assert.equal(s.query(), "BOARD"); s.events.length = 0; s.press(); assert.equal(s.c.state.air.aboard, true); assert.ok(!hasEvent(s, "enterDungeon"));
  s.c.state.air = { x: dock[0], y: dock[1], aboard: false }; assert.equal(s.query(), "EXAMINE"); s.c.D.dungeons = s.c.D.dungeons.filter(d => !d.optional); assert.equal(s.query(), "");
});
check("aboard hints and actual Confirm use current-tile landing/refusal, never forward actions", () => {
  for (const allowed of [true, false]) { const s = session(); fixture(s, "world"); const [x, y] = ground(s, t => !!t.airship_lands === allowed); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x, y, aboard: true };
    // Explicit front-object placement isolates priority; it does not assert a new authored world location.
    s.c.map.grid[y - 1][x] = "Chest"; assert.equal(s.query(), allowed ? "LAND" : "NO LANDING HERE"); s.chip(); chipBounds(s); s.press(); assert.ok(hasEvent(s, "land") && !hasEvent(s, "interact") && !hasEvent(s, "openChest")); assert.equal(s.c.state.air.aboard, !allowed); assert.equal(hasEvent(s, "openCache"), allowed);
  }
});
check("step-only stairs/landmarks/waystone/cache overlays do not invent a Confirm action", () => {
  const s = session(); fixture(s, "dungeon", 0); faceTile(s, "StairsUp"); assert.equal(s.query(), "");
  for (const landmark of ["Town", "Cave", "Tower", "CrystalShrine"]) { fixture(s, "world"); faceTile(s, landmark); assert.equal(s.query(), ""); }
  fixture(s, "world"); const p = ground(s, t => t.airship_lands);
  // Canonical IDs/loot with explicit runtime positions; no waystone/cache packer-placement parity claim.
  s.c.D.waystones = [{ ...clone(ways[0]), x: p[0], y: p[1] }]; s.c.state.ways.add(ways[0].id); s.c.D.sky_caches = [{ x: p[0], y: p[1], item: skyLoot[0] }]; s.c.map.grid[s.c.P.y - 1][s.c.P.x] = s.c.D.world[p[1]][p[0]]; assert.equal(s.query(), ""); assert.equal(s.events.length, 0);
});
check("fieldTick preserves Start/dialog/moving priorities rather than turning cue rendering into input", () => {
  const s = session(); fixture(s, "interior", "Magic"); faceTile(s, "Bookcase"); s.c.pressed = { start: true, a: true }; s.action(() => s.api.fieldTick(0)); assert.ok(hasEvent(s, "openMenu")); assert.ok(!hasEvent(s, "interact"));
  s.events.length = 0; s.c.dlg = { pages: ["PENDING"] }; s.action(() => s.api.fieldTick(0)); assert.ok(hasEvent(s, "dialogTick")); assert.ok(!hasEvent(s, "interact"));
  s.c.dlg = null; s.events.length = 0; s.c.P.moving = 1; s.c.pressed = { a: true }; s.action(() => s.api.fieldTick(0.01)); assert.ok(s.c.P.moving < 1); assert.ok(!hasEvent(s, "interact")); assert.equal(s.c.pressed.a, true);
});
for (const width of [320, 256]) check("all cue chips/font/max labels/fallback/blocked text fit and avoid player plus faced tile at screen edges " + width, () => {
  const s = session(width); s.labels(); fixture(s, "dungeon", 0); faceTile(s, "BossGate"); s.chip(); chipBounds(s); assert.equal(text(s).label, "ABCDEFGH: CHALLENGE");
  s.labels("INVALID LABEL"); s.chip(); assert.equal(text(s).label, "Z/SPACE: CHALLENGE");
  // Explicit actionable/NPC placements on canonical town dimensions test viewport edges, not walking routes.
  for (const bottom of [false, true]) for (const right of [false, true]) { const m = fixture(s), x = right ? m.grid[0].length - 2 : 1, y = bottom ? m.grid.length - 3 : 1, dir = bottom ? "down" : "up", [dx, dy] = dirs[dir]; place(s, x, y, dir); m.npcs = [{ type: "Guard", x: x + dx, y: y + dy, dir: "left" }];
    const oy = bottom ? 224 - m.grid.length * 16 : 0; s.chip(oy); chipBounds(s); const chip = panel(s); assert.equal(chip.y, bottom ? 6 : 202); const player = { y: oy + s.c.P.fy, h: 16 }, facing = { y: oy + (y + dy) * 16, h: 16 };
    for (const object of [player, facing]) assert.ok(chip.y + chip.h <= object.y || chip.y >= object.y + object.h, "chip cannot cover player or facing tile"); }
  fixture(s, "world"); const [x, y] = ground(s, t => !t.airship_lands); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x, y, aboard: true }; s.c.PAD = { devices() { throw new Error("blocked cue must not ask for Confirm"); } }; s.chip(); chipBounds(s); assert.equal(text(s).label, "NO LANDING HERE"); assert.equal(text(s).color, "#f87878");
});
check("actual field painter sends current camera anchoring and paints the cue after night overlays/glows", () => {
  for (const width of [320, 256]) { const s = session(width), m = fixture(s); const x = 2, y = m.grid.length - 5; place(s, x, y, "down"); m.npcs = [{ type: "Merchant", x, y: y + 1, dir: "up" }]; m.grid[y][x + 1] = "Lamp"; s.c.state.minute = 1320;
    s.paintField(); const actor = s.paints.find(p => p.kind === "sprite" && p.name === "NPC_Guard"), chip = panel(s); assert.ok(actor && chip); const oy = actor.y - s.c.P.fy, focus = oy + Math.max(s.c.P.fy, (y + 1) * 16) + 16; assert.equal(chip.y, focus >= 198 ? 6 : 202); assert.equal(chip.y, 202, "uses camera Y rather than raw world Y");
    const night = s.paints.findIndex(p => p.kind === "rect" && String(p.color).startsWith("rgba(10,14,48,")), glow = s.paints.findIndex(p => p.kind === "rect" && p.color && p.color.kind === "gradient"), lastText = s.paints.findLastIndex(p => p.kind === "text"); assert.ok(night >= 0 && glow > night && s.paints.indexOf(chip) > glow); assert.equal(lastText, s.paints.length - 1); chipBounds(s);
  }
});
check("whole-field world integration uses a preseeded skiff; no purity claim masks inherited airship access", () => {
  const s = session(); fixture(s, "world"); const p = ground(s, t => t.airship_lands); s.c.state.beaten.add(s.c.D.dungeons[0].boss_data.name); s.c.state.air = { x: p[0], y: p[1], aboard: false }; const air = s.c.state.air; s.paintField(); assert.ok(hasEvent(s, "airship")); assert.equal(s.c.state.air, air); assert.equal(text(s).label, "Z/SPACE: BOARD"); chipBounds(s);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("field interaction cue: " + groups + " focused groups passed; canonical grids/explicit placements/branch peers, runtime acceptance pending");
