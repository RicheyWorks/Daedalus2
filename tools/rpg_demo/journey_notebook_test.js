// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/journey_notebook_test.js
// Actual notebook/menu handlers and painters with canonical RPG metadata.
// Canvas-command capture and tiny storage/pad peers only; no DOM, game IIFE, browser, assets or builds.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const portal = fs.readFileSync(path.join(__dirname, "portal_realm.py"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, layouts = data("menus").layouts, catalogs = data("dungeons").dungeons;
const bosses = data("prism-bosses").bosses, spells = data("spells").spells, interiors = data("interiors").interiors;
const originalCommands = ["ITEM", "MAGIC", "EQUIP", "STATUS", "ORDER", "BESTIARY", "FISH", "SAVE", "OPTIONS"];
function tuples(text, name) {
  const found = text.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(found, name);
  return Array.from(found[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), m => [m[1], m[2]]);
}
const main = tuples(builder, "QUEST"), optional = tuples(builder, "OPTIONAL_QUEST"), finalName = builder.match(/^FINAL = "([^"]+)"$/m)[1];
function routes(realm) {
  return (realm === "prism" ? main.concat(optional) : tuples(portal, "QUEST")).map(([landmark, name], i) => {
    const d = catalogs[realm].find(d => d.name === name); assert.ok(d, "projected route has canonical metadata: " + name);
    const boss = realm === "prism" ? bosses.find(b => b.dungeon === name) : null;
    if (realm === "prism") assert.ok(boss, "Prism route has canonical boss metadata");
    return { ...clone(d), landmark, optional: realm === "prism" && i >= main.length,
      final: realm === "prism" && name === finalName, boss_data: boss ? clone(boss) : null };
  });
}
const prismRoutes = routes("prism"), shardRoutes = prismRoutes.filter(d => !d.final && !d.optional), finalRoute = prismRoutes.find(d => d.final), folly = prismRoutes.find(d => d.optional);
assert.equal(shardRoutes.length, 3); assert.equal(prismRoutes.length, 5); assert.ok(finalRoute && folly && folly.boss_data.shard === "-");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), line("const spellOf ="),
  between("const carriesShard =", "const chestKey ="),
  between("let menu = null;", "/* Four rows"),
  between("function drawMenu()", "function drawStatus()"),
  between("function titlePrompt(", "function drawTitle("),
  "this.api = { start: () => { party = buildParty(); }, openMenu, menuTick, drawMenu, journeyRoutes, journeyObjective, journeyStatus, journeyTick, drawJourney, " +
    "menu: () => menu, commands: () => MENU_CMDS.slice(), shardCount, chars: CHARS, " +
    "resources: () => ({ data: D, party, reserve, bag, gold, beaten: Array.from(state.beaten), seen: state.seen, quests: state.quests, fish: state.fish, " +
    "opened: Array.from(opened), ways: Array.from(state.ways), air: state.air, returnTo: state.returnTo, day: state.day, minute: state.minute, map }), " +
    "view: () => ({ mode, menu, pressed }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(realm = "prism", production = source) {
  const pressed = {}, paints = [], sounds = [], storage = { reads: 0, writes: 0, record: "preserved journey" }, calls = { settings: 0, field: 0 }, labels = [];
  const gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r]))
    for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), menus: clone(layouts[realm]), dungeons: routes(realm),
      spells: clone(spells.filter(s => s.realm === realm)), rects: { sprites: {} }, ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: realm === "portal" ? 256 : 320, H: 224, GEAR: gear, B: null, mode: "field", pressed, map: { kind: "world" },
    state: { beaten: new Set(), seen: {}, quests: {}, fish: {}, ways: new Set(), air: null, returnTo: null, day: 1, minute: 480 },
    opened: new Set(["preserved/chest"]), clockText: () => "D1 08:00", isNight: () => false,
    sfx: k => sounds.push(k), toast() {}, saveSummary: () => "saved fixture", saveGame: () => { storage.writes++; return true; },
    openSettings: () => { calls.settings++; }, drawField: () => { calls.field++; }, drawPartyRows() {},
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), tw: text => String(text).length * 6,
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }), cursor: (x, y) => paints.push({ kind: "cursor", x, y }),
    text: (text, x, y, color = "#ffffff") => paints.push({ kind: "text", label: String(text).toUpperCase(), x, y, color, w: String(text).length * 6, h: 8 }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); } },
    PAD: null, localStorage: { getItem() { storage.reads++; return storage.record; }, setItem() { storage.writes++; throw new Error("notebook cannot save"); }, removeItem() { throw new Error("notebook cannot erase"); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  const draw = (notebookOnly = false) => {
    paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), saved = JSON.stringify(storage), soundCount = sounds.length;
    notebookOnly ? c.api.drawJourney() : c.api.drawMenu();
    assert.equal(resources(), before, "looking cannot change inventory, HP/MP, roster, progress, maps or catalog data");
    assert.equal(JSON.stringify(c.api.view()), view, "drawing cannot consume inputs or alter selection");
    assert.equal(JSON.stringify(storage), saved, "drawing cannot access or rewrite saved state"); assert.equal(sounds.length, soundCount);
    return paints;
  };
  return { c, api: c.api, paints, pressed, sounds, storage, calls, labels, resources, draw,
    tick(...keys) { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); },
    controller(cancelLabel = "B", confirmLabel = "A") { c.PAD = { devices: () => [{ index: 0 }], label(action, index) { labels.push({ action, index }); assert.ok(["cancel", "confirm"].includes(action), "notebook uses existing shared pad actions"); return action === "cancel" ? cancelLabel : confirmLabel; } }; }
  };
}
function openBook(s) {
  s.api.openMenu(); for (let i = 0; i < 9; i++) s.tick("down"); assert.equal(s.api.menu().idx, 9);
  s.tick("a"); assert.equal(s.api.menu().sub, "journey", "the tenth Prism command opens the notebook"); return s;
}
function assertProgress(s, beaten) {
  s.c.state.beaten = new Set(beaten); const before = s.resources(), count = shardRoutes.filter(d => beaten.includes(d.boss_data.name)).length;
  assert.equal(s.api.shardCount(), count); assert.deepEqual(Array.from(s.api.journeyRoutes(), d => d.name), prismRoutes.map(d => d.name));
  for (let i = 0; i < prismRoutes.length; i++) {
    const d = s.api.journeyRoutes()[i], done = beaten.includes(d.boss_data.name), info = s.api.journeyStatus(d);
    assert.equal(info.word, done ? i < 3 ? "SHARD" : "CLEARED" : i >= 3 && count < 3 ? "SEALED" : "OPEN");
    if (d.optional) assert.equal(info.hint, done ? "BRANNOC'S CALIBRATION IS AT THE INN." : count < 3 ? "GATHER ALL THREE WARDEN SHARDS." : "ON FOOT: FACE THE AIRSHIP PAD.");
  }
  const finalDone = beaten.includes(finalRoute.boss_data.name), follyDone = beaten.includes(folly.boss_data.name);
  const objective = finalDone ? ["THE HEART IS WHOLE AGAIN.", follyDone ? "EXPLORE THE ISLES AT YOUR OWN PACE." : "THE WORKS WAIT AT THE AIRSHIP PAD."]
    : count >= 3 ? ["THE CRYSTAL SHRINE IS OPEN.", "THE SHATTERED HEART AWAITS."] : [count === 2 ? "ONE WARDEN STILL HOLDS A SHARD." : (3 - count) + " WARDENS STILL HOLD SHARDS.", "CHOOSE ANY UNFINISHED SHARD ROUTE."];
  assert.deepEqual(Array.from(s.api.journeyObjective()), objective); assert.equal(s.resources(), before); assert.equal(s.storage.writes, 0);
}
for (let mask = 0; mask < 8; mask++) check("actual shard subset " + mask + " has truthful statuses and objective", () => {
  const s = session(), beaten = shardRoutes.filter((_, i) => mask & (1 << i)).map(d => d.boss_data.name); assertProgress(s, beaten);
});
for (const order of [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]])
  check("arbitrary authored shard order " + order.join("/") + " selects the first unfinished open route", () => {
    const s = session(), beaten = [];
    for (const index of order) {
      beaten.push(shardRoutes[index].boss_data.name); assertProgress(s, beaten); openBook(s);
      const expected = prismRoutes.findIndex(d => !beaten.includes(d.boss_data.name) && (!(d.final || d.optional) || beaten.length >= 3));
      assert.equal(s.api.menu().ii, expected); s.tick("b"); s.tick("b");
    }
  });
check("final and optional victories do not fabricate more shards", () => {
  const s = session(), all = shardRoutes.map(d => d.boss_data.name);
  assertProgress(s, all.concat(folly.boss_data.name)); assertProgress(s, all.concat(finalRoute.boss_data.name));
  assertProgress(s, all.concat(finalRoute.boss_data.name, folly.boss_data.name));
});
check("the original nine command indices and actions remain stable, with Prism JOURNEY appended", () => {
  const s = session(); assert.deepEqual(Array.from(s.api.commands()), originalCommands);
  const expected = ["item", "magic-who", "equip", "status", "order", "bestiary", "fish", null, null];
  for (let i = 0; i < originalCommands.length; i++) {
    s.api.openMenu(); for (let j = 0; j < i; j++) s.tick("down"); assert.equal(s.api.menu().idx, i); s.tick("a");
    if (i === 8) { assert.equal(s.c.mode, "field"); assert.equal(s.calls.settings, 1); }
    else assert.equal(s.api.menu().sub, expected[i], originalCommands[i]);
  }
  assert.equal(s.storage.writes, 1, "only intentionally choosing the existing SAVE command saves");
  openBook(s); s.tick("b"); s.tick("down"); assert.equal(s.api.menu().idx, 0); s.tick("up"); assert.equal(s.api.menu().idx, 9);
});
check("Portal keeps its actual nine-entry menu and wrap without a JOURNEY command", () => {
  const s = session("portal"); assert.deepEqual(Array.from(s.api.commands()), originalCommands); assert.equal(s.api.journeyRoutes().length, 0);
  s.api.openMenu(); s.tick("up"); assert.equal(s.api.menu().idx, 8); s.tick("down"); assert.equal(s.api.menu().idx, 0);
  for (let i = 0; i < 9; i++) { assert.equal(s.api.menu().idx, i); const drawn = s.draw().filter(p => p.kind === "text"); assert.equal(drawn.some(p => p.label === "JOURNEY"), false); s.tick("down"); }
  assert.equal(s.api.menu().idx, 0); assert.equal(s.storage.writes, 0);
});
function assertRail(s) {
  const cw = s.c.D.menus.screens.Menu.windows.find(w => w.name === "commands"), paints = s.draw(), commands = originalCommands.concat(s.c.D.realm_key === "prism" ? ["JOURNEY"] : []);
  const rows = paints.filter(p => p.kind === "text" && p.x === cw.x + 18 && commands.includes(p.label)), cursor = paints.find(p => p.kind === "cursor" && p.x === cw.x + 6);
  assert.ok(rows.length > 0 && cursor); const selected = rows.find(p => p.y === cursor.y); assert.ok(selected); assert.equal(selected.label, commands[s.api.menu().idx]);
  for (const p of rows) assert.ok(p.x >= cw.x && p.x + p.w <= cw.x + cw.w - 4 && p.y >= cw.y + 8 && p.y + p.h <= cw.y + cw.h - 8, "selected rail entries fit the actual authored command window");
  const cue = paints.find(p => p.kind === "text" && p.x === cw.x + 8 && p.y === cw.y + cw.h - 10);
  if (commands.length > Math.floor((cw.h - 16) / 16)) { assert.ok(cue); assert.equal(cue.label, (s.api.menu().idx + 1) + "/" + commands.length); assert.ok(rows.every(p => p.y + p.h <= cue.y)); }
  else assert.equal(cue, undefined);
}
for (const realm of ["prism", "portal"]) check("command rail stays visible in the real " + realm + " window", () => {
  const s = session(realm); s.api.openMenu(); for (let i = 0; i < (realm === "prism" ? 10 : 9); i++) { assertRail(s); s.tick("down"); }
});
for (const width of [320, 256]) check("notebook metadata, text, glyphs and panes fit at " + width + " without changing the journey", () => {
  const s = openBook(session()); s.c.W = width; s.controller();
  const beatenSets = [[], [shardRoutes[1].boss_data.name], shardRoutes.map(d => d.boss_data.name), shardRoutes.map(d => d.boss_data.name).concat(finalRoute.boss_data.name), prismRoutes.map(d => d.boss_data.name)];
  for (const beaten of beatenSets) { s.c.state.beaten = new Set(beaten);
    for (let i = 0; i < prismRoutes.length; i++) { s.api.menu().ii = i; const paints = s.draw();
      for (const p of paints) {
        if (p.kind === "text") { assert.ok(p.x >= 0 && p.x + p.w <= width - 6 && p.y >= 0 && p.y + p.h <= 224); assert.ok(Array.from(p.label).every(k => s.api.chars.includes(k))); }
        if (p.kind === "window") assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= width && p.y + p.h <= 224);
      }
      const row = paints.find(p => p.kind === "cursor"), name = paints.find(p => p.kind === "text" && p.x === 24 && p.y === row.y), status = paints.find(p => p.kind === "text" && p.x + p.w === width - 12 && p.y === row.y);
      assert.ok(row && name && status); assert.ok(name.x + name.w < status.x); assert.equal(name.label, prismRoutes[i].name.toUpperCase().slice(0, Math.floor((width - 120) / 6)));
      assert.equal(status.label, s.api.journeyStatus(s.api.journeyRoutes()[i]).word);
      assert.ok(paints.some(p => p.kind === "text" && p.label === ("MAP: " + prismRoutes[i].landmark.replace(/([a-z])([A-Z])/g, "$1 $2")).toUpperCase()));
      assert.ok(paints.some(p => p.kind === "text" && p.y === 210 && p.label === "UP/DOWN: ROUTE  B: BACK"));
      const confirm = paints.find(p => p.kind === "text" && p.y === 196);
      assert.equal(confirm.label, "PIN: PRESS A");
      if (prismRoutes[i].optional && status.label === "OPEN") assert.ok(paints.some(p => p.kind === "text" && p.y === 184 && p.label === "ON FOOT: FACE PAD. PRESS A."));
    }
  }
  assert.ok(s.labels.some(p => p.action === "cancel") && s.labels.some(p => p.action === "confirm")); assert.equal(s.storage.writes, 0);
});
check("keyboard/touch fallback and sanitized controller prompts stay complete in the compact notebook", () => {
  const s = openBook(session()); s.c.W = 256; s.api.menu().ii = 4;
  shardRoutes.forEach(d => s.c.state.beaten.add(d.boss_data.name));
  const plain = s.draw(); assert.ok(plain.some(p => p.kind === "text" && p.y === 210 && p.label === "UP/DOWN: ROUTE  X/ESC OR TAP B: BACK"));
  assert.ok(plain.some(p => p.kind === "text" && p.y === 196 && p.label === "PIN: PRESS Z/SPACE OR TAP A"));
  s.controller("ABCD1234", "<UNSAFE>"); const labelled = s.draw();
  assert.ok(labelled.some(p => p.kind === "text" && p.y === 210 && p.label === "UP/DOWN: ROUTE  ABCD1234: BACK"));
  assert.ok(labelled.some(p => p.kind === "text" && p.y === 196 && p.label === "PIN: PRESS Z/SPACE OR TAP A"));
  assert.ok(labelled.filter(p => p.kind === "text").every(p => p.x + p.w <= 250));
});
check("looking, route movement and repeated rendering do not travel, spend or save", () => {
  const s = openBook(session()), before = s.resources();
  for (let i = 0; i < 20; i++) { s.tick("down"); s.draw(); assert.equal(s.api.menu().sub, "journey"); }
  assert.equal(s.resources(), before); assert.equal(s.storage.writes, 0); assert.equal(s.storage.reads, 0);
  s.tick("up"); const last = s.api.menu().ii; assert.equal(last, 4); s.tick("down"); assert.equal(s.api.menu().ii, 0);
});
function cancelled(production = source, key = "b") {
  const s = openBook(session("prism", production)), before = s.resources(); s.api.menu().msg = "old feedback";
  s.tick(key, "a"); assert.equal(s.api.menu().sub, null); assert.equal(s.api.menu().idx, 9); assert.equal(s.api.menu().msg, "");
  for (const k of ["a", "b", "start"]) assert.equal(!!s.pressed[k], false, "dismissal consumes concurrent " + k);
  s.tick(); assert.equal(s.api.menu().sub, null, "old Confirm cannot reopen the notebook next tick"); assert.equal(s.resources(), before); assert.equal(s.storage.writes, 0);
  s.tick("a"); assert.equal(s.api.menu().sub, "journey", "fresh Confirm still works"); return s;
}
for (const key of ["b", "start"]) check(key + " closes the notebook before concurrent Confirm and keeps its menu destination", () => cancelled(source, key));
check("single Back preserves selection, while simultaneous Back/Start/Confirm drains all actions", () => {
  const s = openBook(session()); s.tick("down"); s.tick("b"); assert.equal(s.api.menu().idx, 9); assert.equal(s.api.menu().sub, null);
  s.tick("a"); s.tick("b", "start", "a"); assert.equal(s.api.menu().sub, null); assert.ok(["a", "b", "start"].every(k => !s.pressed[k])); s.tick(); assert.equal(s.api.menu().sub, null);
});
check("controlled legacy entry, rail overflow, stale Confirm and inflated shard counts fail the same invariants", () => {
  const noBook = source.replaceAll('MENU_CMDS.concat((D.realm_key || "prism") === "prism" ? ["JOURNEY"] : [])', "MENU_CMDS"); assert.notEqual(noBook, source);
  assert.throws(() => openBook(session("prism", noBook)), assert.AssertionError);
  const unbounded = source.replace('const rows = Math.max(1, Math.floor((cw[3] - 16) / 16));', "const rows = commands.length;"); assert.notEqual(unbounded, source);
  assert.throws(() => { const s = session("prism", unbounded); s.api.openMenu(); for (let i = 0; i < 9; i++) s.tick("down"); assertRail(s); }, assert.AssertionError);
  const stale = source.replace('if (hit("b") || hit("start")) { clearActionButtons(); menu.sub = null;', 'if (hit("b") || hit("start")) { menu.sub = null;'); assert.notEqual(stale, source);
  assert.throws(() => cancelled(stale), assert.AssertionError);
  const inflated = source.replace('const shardCount = () => shardBosses().filter(n => state.beaten.has(n)).length;', 'const shardCount = () => state.beaten.size;'); assert.notEqual(inflated, source);
  assert.throws(() => assertProgress(session("prism", inflated), prismRoutes.map(d => d.boss_data.name)), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("journey notebook: " + checks + " focused groups passed; DOM-free source checks only, no runtime acceptance");
