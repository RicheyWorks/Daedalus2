// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/journey_pin_test.js
// Actual pin/menu/drawing/save/Continue/New handlers, canonical catalogs and existing v1 reader.
// DOM-free canvas/storage peers. No browser, full game IIFE, assets, builder or native runtime.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Save = require("./journey-save.js"), Ways = require("./waystones.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n"), builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8"), portal = fs.readFileSync(path.join(__dirname, "portal_realm.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, layouts = data("menus").layouts, dungeonData = data("dungeons").dungeons, bosses = data("prism-bosses").bosses;
const interiors = data("interiors"), worldData = data("worldmap-tiles"), village = data("prism-village"), allSpells = data("spells").spells, ways = data("prism-waystones").waystones;
function tuples(text, name) { const found = text.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(found, name); return [...found[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]); }
const main = tuples(builder, "QUEST"), extra = tuples(builder, "OPTIONAL_QUEST"), finalName = builder.match(/^FINAL = "([^"]+)"$/m)[1];
function routes(realm) { return (realm === "prism" ? main.concat(extra) : tuples(portal, "QUEST")).map(([landmark, name], i) => {
  const d = dungeonData[realm].find(d => d.name === name), b = realm === "prism" ? bosses.find(b => b.dungeon === name) : null; assert.ok(d && (realm !== "prism" || b));
  return { ...clone(d), landmark, optional: realm === "prism" && i >= main.length, final: realm === "prism" && name === finalName, boss_data: b ? clone(b) : null }; }); }
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"), line("const T ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("let journeySerial ="), line("const find ="), line("function airUnlocked()"),
  between("function buildParty()", "let party ="), between("function makeMember(", "const atkOf ="), line("const spellOf ="), between("const carriesShard =", "const chestKey ="),
  between("function interiorMap(", "function worldMap()"), between("function goto(", "const find ="), between("let menu = null;", "/* Four rows"), between("function drawMenu()", "function drawStatus()"),
  between('let SAVE_KEY = "prism.save.v1";', "function beginJourney()"), between("function titlePrompt(", "function drawTitle("),
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,journeyPinned,toggleJourneyPin,journeyObjective,journeyStatus,journeyRoutes,saveGame,titleChoose,loadSave,menu:()=>menu,prefix:JOURNEY_PIN,chars:CHARS," +
  "applyFade:()=>{if(fadeCb){const cb=fadeCb;fadeCb=null;cb();}fade=0;},key:()=>SAVE_KEY,setKey:k=>{SAVE_KEY=k;}," +
  "progress:()=>({party,reserve,bag,gold,beaten:Array.from(state.beaten),seen:state.seen,quests:state.quests,fish:state.fish,ways:Array.from(state.ways),air:state.air,day:state.day,minute:state.minute,map,P,D,held,SRC}),view:()=>({mode,menu,pressed,opened:Array.from(opened)})};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], pressed = {}, notices = [], sounds = [], pending = [], store = new Map(), counts = { reads: 0, writes: 0, erases: 0, lazy: 0 }, gear = {}, tiles = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors.interiors[r])) for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
  const world = clone(worldData.demo_maps[realm]); [...new Set(world.flat())].forEach((n, i) => { tiles["wm:" + n + "#0"] = [i * 16, 0, 16, 16]; });
  const fixedMath = Object.create(Math); fixedMath.random = () => { throw new Error("pins cannot consume gameplay randomness"); };
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, menus: clone(layouts[realm]), dungeons: routes(realm), world,
      interiors: clone(interiors.interiors[realm]), interior_tiles: Object.fromEntries(interiors.tiles.map(t => [t.tile, clone(t)])), town_tiles: {}, frames: {},
      village: clone(village), waystones: clone(ways), spells: clone(allSpells.filter(s => s.realm === realm)), rects: { sprites: {}, tiles }, ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    Math: fixedMath, PrismJourneySave: Save, PrismWaystones: Ways, W: width, H: 224, IM: { tiles: "atlas" }, GEAR: {}, party: [], reserve: [], bag: {}, gold: 0,
    state: { beaten: new Set(), seen: {}, quests: {}, fish: {}, ways: new Set(), air: null, returnTo: null, day: 1, minute: 480, steps: 0, sinceBattle: 0 },
    opened: new Set(["dungeon0/0:1,2", "story/folly/discovered"]), grids: {}, map: { kind: "world" }, P: { x: 1, y: 1 }, mode: "field", fade: 0, fadeCb: null,
    dlg: null, shop: null, B: null, ending: null, nameEntry: null, PAD: null, pressed, held: { right: true }, SRC: { kb: { right: true } },
    WAYS: () => c.D.waystones, recoverAir() { throw new Error("round-trip fixture has no saved air state"); },
    sfx: k => sounds.push(k), toast: (...text) => notices.push(text), unlockAudio() {}, cue() {}, say() {}, setTimeout: fn => pending.push(fn),
    openSettings() {}, drawField() {}, drawPartyRows() {}, clockText: () => "D1 08:00", isNight: () => false,
    airship() { counts.lazy++; throw new Error("looking cannot initialize air state"); },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: v => String(v).length * 6,
    text: (value, x, y, color = "#ffffff") => paints.push({ kind: "text", label: String(value).toUpperCase(), x, y, w: String(value).length * 6, h: 8, color }),
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }), cursor: (x, y) => paints.push({ kind: "cursor", x, y }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); }, drawImage(image, sx, sy, sw, sh, x, y, w, h) { paints.push({ kind: "image", image, sx, sy, sw, sh, x, y, w, h }); } },
    localStorage: { getItem(key) { counts.reads++; return store.get(key) ?? null; }, setItem(key, raw) { counts.writes++; store.set(key, raw); }, removeItem(key) { counts.erases++; store.delete(key); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start(); c.api.setKey(realm + ".save.v1");
  const progress = () => JSON.stringify(c.api.progress());
  return { c, api: c.api, paints, pressed, notices, sounds, counts, store, pending, progress,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    draw() { paints.length = 0; const before = progress(), view = JSON.stringify(c.api.view()), calls = JSON.stringify(counts), soundCount = sounds.length, noticeCount = notices.length;
      c.api.drawMenu(); assert.equal(progress(), before); assert.equal(JSON.stringify(c.api.view()), view); assert.equal(JSON.stringify(counts), calls); assert.equal(sounds.length, soundCount); assert.equal(notices.length, noticeCount); return paints; },
    pad(confirm = "A", cancel = "B") { c.PAD = { devices: () => [{ index: 0 }], label(action) { assert.ok(["confirm", "cancel"].includes(action)); return action === "confirm" ? confirm : cancel; } }; }
  };
}
function openBook(s) { s.api.openMenu(); for (let i = 0; i < 9; i++) s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "journey"); return s; }
function known(s) { return [...s.c.opened].filter(k => s.api.journeyRoutes().some(d => k === s.api.prefix + d.landmark)); }
function pin(s, i) { s.api.menu().ii = i; const before = s.progress(), objective = JSON.stringify(s.api.journeyObjective()), statuses = Array.from(s.api.journeyRoutes(), d => s.api.journeyStatus(d).word); s.tick("a");
  assert.equal(s.progress(), before, "pinning cannot change resources, progression, location or catalogs"); assert.equal(JSON.stringify(s.api.journeyObjective()), objective);
  assert.deepEqual(Array.from(s.api.journeyRoutes(), d => s.api.journeyStatus(d).word), statuses); assert.equal(s.counts.writes, 0, "pin choices do not autosave"); assert.equal(s.counts.lazy, 0); }
check("pin, move and remove any canonical route, including sealed and completed destinations", () => {
  const s = openBook(session()), ds = s.api.journeyRoutes(), preserved = [...s.c.opened];
  for (const completed of [false, true]) {
    if (completed) ds.forEach(d => s.c.state.beaten.add(d.boss_data.name));
    for (let i = 0; i < ds.length; i++) { pin(s, i); assert.equal(s.api.journeyPinned(), ds[i]); assert.deepEqual(known(s), [s.api.prefix + ds[i].landmark]);
      preserved.forEach(k => assert.ok(s.c.opened.has(k))); assert.match(s.notices.at(-1)[1], /SAVE.*inn/); }
    pin(s, ds.length - 1); assert.equal(s.api.journeyPinned(), null); assert.equal(known(s).length, 0);
  }
});
check("recognized pins are consolidated without dropping chest, story or unknown future flags", () => {
  const s = openBook(session()), ds = s.api.journeyRoutes(), unknown = s.api.prefix + "FutureRoad", other = "another-system/keepsake";
  s.c.opened.add(unknown); s.c.opened.add(other); s.c.opened.add(s.api.prefix + ds[3].landmark); s.c.opened.add(s.api.prefix + ds[1].landmark);
  const preserved = [...s.c.opened].filter(k => !known(s).includes(k)); pin(s, 4);
  assert.deepEqual(known(s), [s.api.prefix + ds[4].landmark]); preserved.forEach(k => assert.ok(s.c.opened.has(k)));
  pin(s, 4); assert.equal(known(s).length, 0); assert.ok(s.c.opened.has(unknown) && s.c.opened.has(other));
});
check("re-entering prefers the player pin while unpinned entry keeps normal objective selection", () => {
  const s = openBook(session()), ds = s.api.journeyRoutes(); pin(s, 3); s.tick("b"); s.tick("b"); openBook(s); assert.equal(s.api.menu().ii, 3); assert.equal(s.api.journeyStatus(ds[3]).word, "SEALED");
  pin(s, 3); s.tick("b"); s.tick("b"); openBook(s); assert.equal(s.api.menu().ii, 0);
  s.c.state.beaten.add(ds[0].boss_data.name); s.tick("b"); s.tick("b"); openBook(s); assert.equal(s.api.menu().ii, 1);
});
function fullFlags(s, pinIndex = null) { s.c.opened.clear(); const count = pinIndex === null ? 4096 : 4095;
  for (let i = 0; i < count; i++) s.c.opened.add("progress/chest/" + i); if (pinIndex !== null) s.c.opened.add(s.api.prefix + s.api.journeyRoutes()[pinIndex].landmark); }
function capacityRefusal(production = source) { const s = openBook(session(320, "prism", production)); fullFlags(s); const before = [...s.c.opened]; pin(s, 4);
  assert.deepEqual([...s.c.opened], before, "a full existing record must not drop any progress to make room"); assert.equal(s.api.journeyPinned(), null); assert.equal(s.sounds.at(-1), "LOCKED"); return s; }
check("the existing 4096-flag bound refuses an extra pin without discarding progress", () => {
  const s = capacityRefusal(); assert.equal(s.api.saveGame(), true); assert.equal(Save.read(s.store.get(s.api.key()), "prism", parties.prism.members).ok, true);
});
check("a full record may replace or remove its recognized pin without dropping unrelated flags", () => {
  const s = openBook(session()); fullFlags(s, 0); const preserved = [...s.c.opened].filter(k => !known(s).includes(k)); pin(s, 4);
  assert.equal(s.c.opened.size, 4096); assert.deepEqual(known(s), [s.api.prefix + s.api.journeyRoutes()[4].landmark]); preserved.forEach(k => assert.ok(s.c.opened.has(k)));
  pin(s, 4); assert.equal(s.c.opened.size, 4095); assert.equal(s.api.journeyPinned(), null); preserved.forEach(k => assert.ok(s.c.opened.has(k)));
});
function fieldSave(s) { s.api.openMenu(); for (let i = 0; i < 7; i++) s.tick("down"); s.tick("a"); assert.equal(s.api.menu().idx, 7); assert.equal(s.counts.writes, 1);
  const raw = s.store.get(s.api.key()), decoded = Save.read(raw, s.c.D.realm_key, parties[s.c.D.realm_key].members); assert.equal(decoded.ok, true); return { raw, decoded: decoded.value }; }
check("normal field SAVE and accepted Continue retain the pin through the existing v1 reader", () => {
  const s = openBook(session()), key = s.api.prefix + s.api.journeyRoutes()[3].landmark; pin(s, 3); const { raw, decoded } = fieldSave(s);
  assert.ok(decoded.opened.includes(key)); assert.equal(decoded.v, 1); s.c.opened.clear(); s.api.titleChoose(1); s.api.applyFade();
  assert.equal(s.c.mode, "field"); assert.equal(s.c.map.kind, "interior"); assert.equal(s.c.map.name, "Inn"); assert.ok(s.c.opened.has(key));
  assert.equal(s.api.journeyPinned().landmark, s.api.journeyRoutes()[3].landmark); assert.equal(s.store.get(s.api.key()), raw); assert.equal(s.counts.writes, 1);
  openBook(s); assert.equal(s.api.menu().ii, 3);
});
check("legacy v1 records without a pin remain unpinned and NEW clears live pins without erasing saves", () => {
  const s = openBook(session()); pin(s, 2); const { decoded } = fieldSave(s);
  decoded.opened = decoded.opened.filter(k => !k.startsWith(s.api.prefix)); const legacy = JSON.stringify(decoded); s.store.set(s.api.key(), legacy);
  s.api.titleChoose(1); s.api.applyFade(); assert.equal(s.api.journeyPinned(), null); assert.equal(s.store.get(s.api.key()), legacy);
  openBook(s); assert.equal(s.api.menu().ii, 0); s.api.menu().ii = 4; s.tick("a"); assert.ok(s.api.journeyPinned()); const writes = s.counts.writes;
  s.api.titleChoose(0); assert.equal(s.api.journeyPinned(), null); assert.equal(s.c.opened.size, 0); assert.equal(s.counts.writes, writes); assert.equal(s.store.get(s.api.key()), legacy);
  s.api.applyFade(); assert.equal(s.c.mode, "name");
});
check("Portal treats generic opened pin-like strings as preserved data and offers no pin operation", () => {
  const s = session(256, "portal"), routeId = "journey/pin/Cave"; s.c.opened.add(routeId); s.api.openMenu(); const before = [...s.c.opened];
  s.api.toggleJourneyPin(); assert.equal(s.api.journeyPinned(), null); assert.deepEqual([...s.c.opened], before); assert.equal(s.notices.length, 0); assert.equal(s.counts.writes, 0);
  s.tick("up"); assert.equal(s.api.menu().idx, 8); s.tick("down"); assert.equal(s.api.menu().idx, 0);
});
function pageConfirm(production = source) { const s = openBook(session(320, "prism", production)), before = [...s.c.opened]; s.tick("left", "right", "a");
  assert.equal(s.api.menu().jp, 1); assert.deepEqual([...s.c.opened], before, "page-switch Confirm cannot create a pin"); assert.ok(!s.pressed.left && !s.pressed.right && !s.pressed.a); s.tick(); assert.equal(s.api.menu().jp, 1); return s; }
check("page changes suppress same-frame Confirm but fresh Confirm pins from either page", () => {
  const s = pageConfirm(); s.tick("a"); assert.ok(s.api.journeyPinned()); s.tick("left", "a"); assert.equal(s.api.menu().jp, 0); assert.ok(s.api.journeyPinned()); s.tick("a"); assert.equal(s.api.journeyPinned(), null);
});
for (const key of ["b", "start"]) check(key + " dismisses before Confirm without changing a pin or leaking next-tick action", () => {
  const s = openBook(session()); pin(s, 4); const before = [...s.c.opened]; s.tick(key, "a"); assert.equal(s.api.menu().sub, null); assert.deepEqual([...s.c.opened], before);
  assert.ok(["a", "b", "start"].every(k => !s.pressed[k])); s.tick(); assert.equal(s.api.menu().sub, null);
});
for (const width of [320, 256]) check("X markers, PIN/UNPIN controls and glyph bounds stay readable at " + width, () => {
  const s = openBook(session(width)); s.pad("ABCD1234", "B"); const ds = s.api.journeyRoutes();
  for (let i = 0; i < ds.length; i++) { pin(s, i); for (const page of [0, 1]) { s.api.menu().jp = page; const paints = s.draw();
      for (const p of paints.filter(p => p.kind === "text")) { assert.ok(p.x >= 0 && p.x + p.w <= width && p.y >= 0 && p.y + p.h <= 224); assert.ok([...p.label].every(k => s.api.chars.includes(k))); }
      if (!page) { assert.ok(paints.some(p => p.kind === "text" && p.x === 24 && p.label.startsWith("X " + ds[i].name.toUpperCase())));
        assert.ok(paints.some(p => p.kind === "text" && p.y === 196 && p.label === "UNPIN: PRESS ABCD1234")); }
      else { const marks = paints.filter(p => p.kind === "text" && p.label === "X"); assert.equal(marks.length, 1); assert.ok(paints.some(p => p.kind === "text" && p.y === 34 && p.label.includes(": UNPIN X ")));
        const y = s.c.D.world.findIndex(row => row.includes(ds[i].landmark)), x = s.c.D.world[y].indexOf(ds[i].landmark);
        const tile = paints.filter(p => p.kind === "image")[y * s.c.D.world[0].length + x];
        assert.deepEqual([marks[0].x, marks[0].y], [tile.x + Math.floor(tile.w / 2) - 2, tile.y + Math.floor(tile.h / 2) - 3], "pin marker belongs to its canonical landmark cell");
        assert.ok(paints.some(p => p.kind === "text" && p.y === 198 && p.label.startsWith("X "))); }
    }
  }
  s.api.menu().jp = 0; s.api.menu().ii = 0; s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.y === 196 && p.label === "PIN: PRESS ABCD1234"));
  s.api.menu().jp = 1; s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.y === 34 && p.label.includes(": PIN X ")));
});
check("ordinary unlocked null-air Folly pin keeps skiff context and marker paint order", () => {
  for (const width of [320, 256]) { const s = openBook(session(width)), ds = s.api.journeyRoutes(); s.c.state.beaten.add(ds[0].boss_data.name); pin(s, 4); s.api.menu().jp = 1;
    const paints = s.draw(), ship = paints.findIndex(p => p.kind === "text" && p.label === "S"), mark = paints.findIndex(p => p.kind === "text" && p.label === "X"), border = paints.findIndex(p => p.kind === "rect" && p.color === "#ffffff"), plus = paints.findIndex(p => p.kind === "rect" && p.color === "#ffdf83");
    assert.ok(ship >= 0 && ship < mark && mark < border && border < plus); assert.ok(paints.some(p => p.kind === "text" && p.y === 22 && p.label.includes("SKIFF AT X."))); assert.equal(s.c.state.air, null); assert.equal(s.counts.lazy, 0);
  }
});
check("looking does not autosave or change accepted flags, and Folly keeps separate physical entry guidance", () => {
  const s = openBook(session()); s.c.state.beaten = new Set(s.api.journeyRoutes().slice(0, 3).map(d => d.boss_data.name)); pin(s, 4);
  for (let i = 0; i < 10; i++) { s.api.menu().jp = i % 2; s.draw(); }
  s.api.menu().jp = 0; s.draw(); assert.ok(s.paints.some(p => p.kind === "text" && p.y === 184 && p.label === "ON FOOT: FACE PAD. PRESS Z OR TAP A.")); assert.equal(s.counts.writes, 0);
});
check("controlled broad deletion, overflow, page Confirm and autosave regressions violate behavioral invariants", () => {
  const broad = source.replace('const previous = routes.map(r => JOURNEY_PIN + r.landmark).filter(k => opened.has(k));', 'const previous = Array.from(opened).filter(k => k.startsWith(JOURNEY_PIN));'); assert.notEqual(broad, source);
  assert.throws(() => { const s = openBook(session(320, "prism", broad)), unknown = s.api.prefix + "FutureRoad"; s.c.opened.add(unknown); pin(s, 0); assert.ok(s.c.opened.has(unknown)); }, assert.AssertionError);
  const overflow = source.replace(/\n  if \(!remove && opened\.size - previous\.length >= 4096\) \{[^\n]*\}\n/, "\n"); assert.notEqual(overflow, source); assert.throws(() => capacityRefusal(overflow), assert.AssertionError);
  const page = source.replace('if (hit("a") && !left && !right)', 'if (hit("a"))'); assert.notEqual(page, source); assert.throws(() => pageConfirm(page), assert.AssertionError);
  const auto = source.replace('sfx("PICK"); toast(remove ?', 'sfx("PICK"); saveGame(); toast(remove ?'); assert.notEqual(auto, source); assert.throws(() => pin(openBook(session(320, "prism", auto)), 0), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("journey pin: " + checks + " focused groups passed; source/VM only, no browser or runtime acceptance");
