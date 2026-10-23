// SPDX-License-Identifier: MIT
// Bounded, DOM-free checks: node tools/rpg_demo/journey_save_test.js
// Uses the actual party catalog, writer, Continue handler and member factory. No browser,
// build output, real browser storage, art, audio or game loop is started.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Save = require("./journey-save.js");
const Ways = require("./waystones.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg/party.json"), "utf8")).party;
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production source section exists: " + start);
  return html.slice(a, b);
}
const source = [
  html.split(/\r?\n/).find(line => line.startsWith("const T =")),
  between("function buildParty()", "let party ="),
  between("function makeMember(", "const atkOf ="),
  between("function airUnlocked()", "/* Where a saved skiff"),
  between("function footReach()", "/* Sky caches"),
  between("function interiorMap(", "function worldMap()"),
  between("function goto(", "const find ="),
  html.split(/\r?\n/).find(line => line.startsWith("const find =")),
  between('let SAVE_KEY = "prism.save.v1";', "function beginJourney()"),
  "this.api = { makeMember, saveGame, loadSave, readSavedJourney, saveSummary, titleChoose, setKey: k => { SAVE_KEY = k; } };"
].join("\n");

function session(realm = "prism", productionSource = source) {
  const store = new Map(), notices = [], pending = [];
  const ways = [{ id: "home", bit: 0, x: 0, y: 0, name: "Home" }];
  const c = {
    D: { realm_key: realm, party: JSON.parse(JSON.stringify(catalog[realm])), gear: {},
      dungeons: [{ name: "Cinder Forge", boss_data: { name: "PyreWarden" } }],
      interiors: { Inn: { grid: [["Floor"]], npcs: [], spawn: { x: 0, y: 0 } } }, frames: {}, interior_tiles: {}, town_tiles: {},
      world: [["Town", "Grass", "AirshipPad"], ["Grass", "Grass", "Grass"]],
      world_tiles: { Town: { kind: "landmark", walkable: true, airship_lands: true }, Grass: { walkable: true, airship_lands: true }, AirshipPad: { kind: "landmark", walkable: true, airship_lands: true } },
      waystones: ways },
    PrismJourneySave: Save, PrismWaystones: Ways, START_LEVEL: 15, ACTIVE: 4,
    GEAR: {}, party: [], reserve: [], bag: { "Herb Tonic": 8 }, gold: 237,
    state: { beaten: new Set(), seen: {}, air: null, fish: {}, quests: {}, ways: new Set(["home"]), day: 3, minute: 421, returnTo: { old: true } },
    opened: new Set(["dungeon0/0:1,2"]), grids: { live: true }, footCache: null,
    mode: "title", map: { live: true }, P: { x: 9, y: 9 }, fade: 0, fadeCb: null, nameEntry: null,
    WAYS: () => ways, sfx() {}, unlockAudio() {}, cue() {}, openSettings() {}, say() {},
    setTimeout: fn => { pending.push(fn); }, toast: (title, message) => { notices.push(title + ": " + message); },
    localStorage: { getItem: key => { if (c.blockReads) throw new Error("storage unavailable"); return store.get(key) ?? null; },
      setItem: (key, text) => { c.writes++; store.set(key, text); } },
    writes: 0, blockReads: false
  };
  if (realm === "portal") c.D.realm_profile = { start_level: 1, save_key: "portal.save.v1" };
  vm.createContext(c);
  vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  c.api.setKey(realm + ".save.v1");
  return { c, store, notices, pending, key: realm + ".save.v1" };
}
function saveNow(s) { assert.equal(s.c.api.saveGame(), true); return s.store.get(s.key); }
function live(s) {
  const c = s.c;
  return { refs: [c.party, c.reserve, c.bag, c.state.beaten, c.state.seen, c.state.air, c.state.fish, c.state.quests, c.state.ways, c.opened, c.grids, c.map, c.P, c.fadeCb],
    text: JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold,
      state: Object.assign({}, c.state, { beaten: [...c.state.beaten], ways: [...c.state.ways] }),
      opened: [...c.opened], grids: c.grids, mode: c.mode, map: c.map, P: c.P, fade: c.fade }),
    raw: s.store.get(s.key), writes: c.writes };
}
function unchanged(s, before) {
  const after = live(s);
  after.refs.forEach((r, i) => assert.equal(r, before.refs[i], "live reference kept " + i));
  assert.equal(after.text, before.text, "current journey values kept");
  assert.equal(after.raw, before.raw, "raw saved record kept");
  assert.equal(after.writes, before.writes, "no write during refused read");
}

const writer = session(), text = saveNow(writer), fixture = JSON.parse(text);
check("current writer roundtrip retains every saved field", () => {
  const r = Save.read(text, "prism", catalog.prism.members);
  assert.equal(r.ok, true); assert.deepEqual(r.value, fixture);
});
check("legacy optional fields and bossBeaten still load", () => {
  const v = JSON.parse(text);
  for (const k of ["realm_key", "at", "reserve", "beaten", "seen", "air", "fish", "quests", "day", "minute", "ways"]) delete v[k];
  v.bossBeaten = true;
  const r = Save.read(JSON.stringify(v), "prism", catalog.prism.members);
  assert.equal(r.ok, true); assert.deepEqual(r.value.beaten, ["PyreWarden"]);
  assert.deepEqual(r.value.reserve, []); assert.equal(r.value.day, 1); assert.equal(r.value.minute, 420);
});
check("unknown inventory names/counts are preserved without catalog pruning", () => {
  const v = JSON.parse(text); v.bag["Earlier build keepsake"] = 1234567;
  const r = Save.read(JSON.stringify(v), "prism", catalog.prism.members);
  assert.equal(r.ok, true); assert.equal(r.value.bag["Earlier build keepsake"], 1234567);
});
check("same shared reader accepts the existing Portal writer", () => {
  const s = session("portal"), raw = saveNow(s);
  assert.equal(Save.read(raw, "portal", catalog.portal.members).ok, true);
  assert.equal(Save.read(raw, "prism", catalog.prism.members).ok, false);
});

const corrupt = [
  ["null party", v => { v.party = null; }], ["empty party", v => { v.party = []; }],
  ["bad member", v => { v.party[0] = 1; }], ["bad name", v => { v.party[0].name = {}; }],
  ["unknown job", v => { v.party[0].job = "MissingJob"; }], ["missing stats", v => { delete v.party[0].st; }],
  ["bad stat", v => { v.party[0].st.str = "strong"; }], ["bad equipment", v => { v.party[0].equip.weapon = {}; }],
  ["missing spell list", v => { delete v.party[0].spells; }], ["bad spell", v => { v.party[0].spells.push({}); }],
  ["bad weapon kinds", v => { v.party[0].kinds = "sword"; }], ["bad sprite", v => { v.party[0].sprite = null; }],
  ["bad HP", v => { v.party[0].hp = "full"; }], ["bad EXP threshold", v => { v.party[0].next = 0; }],
  ["bad status", v => { v.party[0].status = { poison: {} }; }], ["duplicate reserve", v => { v.reserve = [v.party[0]]; }],
  ["bad inventory", v => { v.bag = []; }], ["bad count", v => { v.bag["Herb Tonic"] = -1; }],
  ["bad gold", v => { v.gold = "lots"; }], ["bad chests", v => { v.opened = null; }],
  ["bad Warden list", v => { v.beaten = {}; }], ["bad bestiary", v => { v.seen = { foe: {} }; }],
  ["bad fish log", v => { v.fish = { fish: "one" }; }], ["bad request", v => { v.quests = { pond: [] }; }],
  ["bad day", v => { v.day = 0; }], ["bad minute", v => { v.minute = 1440; }],
  ["bad date", v => { v.at = "yesterday"; }], ["unknown version", v => { v.v = 2; }]
];
for (const [label, change] of corrupt) check(label + " refuses without mutation", () => {
  const s = session(), v = JSON.parse(text); change(v); s.store.set(s.key, JSON.stringify(v));
  const before = live(s); s.c.api.titleChoose(1); unchanged(s, before);
  assert.equal(s.c.api.loadSave(), null); assert.match(s.c.api.saveSummary(), /CONTINUE/);
  assert.match(s.notices.at(-1), /kept/); assert.equal(s.pending.length, 0);
});
check("preservation assertion detects the former reset-before-load defect", () => {
  const broken = source.replace("  let resume = null;", "  party = buildParty();\n  let resume = null;");
  assert.notEqual(broken, source, "the controlled broken variant was installed");
  const s = session("prism", broken), v = JSON.parse(text); v.party = null;
  s.store.set(s.key, JSON.stringify(v)); const before = live(s); s.c.api.titleChoose(1);
  assert.throws(() => unchanged(s, before), /live reference kept/, "regression has teeth without touching files");
});
for (const [label, raw] of [["truncated JSON", '{"v":1'], ["oversized JSON", " ".repeat(Save.MAX_TEXT + 1)], ["root array", "[]"]]) {
  check(label + " refuses safely", () => {
    const s = session(); s.store.set(s.key, raw); const before = live(s);
    s.c.api.titleChoose(1); unchanged(s, before); assert.match(s.notices.at(-1), /kept/);
  });
}
check("missing storage remains a quiet safe title state", () => {
  const s = session(), before = live(s); s.c.api.titleChoose(1); unchanged(s, before);
  assert.equal(s.c.api.saveSummary(), "No saved journey"); assert.match(s.notices.at(-1), /NEW GAME/);
});
check("storage access failure keeps current journey and record", () => {
  const s = session(); s.store.set(s.key, text); s.c.blockReads = true; const before = live(s);
  s.c.api.titleChoose(1); unchanged(s, before); assert.match(s.notices.at(-1), /storage/);
});
check("map preparation exception happens before any live reset", () => {
  const s = session(); s.store.set(s.key, text); s.c.D.interiors.Inn.grid = null; const before = live(s);
  s.c.api.titleChoose(1); unchanged(s, before); assert.match(s.notices.at(-1), /prepare/);
});
check("legacy recruitment prepares before commit and preserves saved bytes", () => {
  const s = session(), v = JSON.parse(text); delete v.reserve; delete v.beaten; v.bossBeaten = true;
  s.store.set(s.key, JSON.stringify(v)); const raw = s.store.get(s.key);
  s.c.api.titleChoose(1);
  assert.equal(s.c.reserve.filter(m => m.job === "Beastcaller").length, 1);
  assert.equal(s.c.state.beaten.has("PyreWarden"), true); assert.equal(s.store.get(s.key), raw);
  assert.equal(s.c.fade, 1); s.c.fadeCb(); assert.equal(s.c.mode, "field"); assert.equal(s.c.map.name, "Inn");
});
check("playing after Continue cannot mutate the cached saved summary", () => {
  const s = session(); s.store.set(s.key, text); const summary = s.c.api.saveSummary();
  s.c.api.titleChoose(1); s.c.party[0].name = "Unsaved"; s.c.bag["Herb Tonic"] = 99;
  assert.equal(s.c.api.saveSummary(), summary); assert.equal(s.store.get(s.key), text);
});
check("malformed optional skiff/WAY1 retains existing forgiving recovery", () => {
  const s = session(), v = JSON.parse(text); v.air = { x: "lost" }; v.ways = "WAY1.bad";
  s.store.set(s.key, JSON.stringify(v)); s.c.api.titleChoose(1);
  assert.equal(s.c.state.air.recalled, true); assert.equal(s.c.state.air.x, 2); assert.equal(s.c.state.ways.size, 0);
});
check("huge legacy recruit level cannot loop or partially replace live state", () => {
  const s = session(), v = JSON.parse(text); v.party.forEach(m => { m.lv = Number.MAX_SAFE_INTEGER; });
  v.beaten = ["PyreWarden"]; s.store.set(s.key, JSON.stringify(v)); const before = live(s);
  vm.runInContext("api.titleChoose(1)", s.c, { timeout: 1000 }); unchanged(s, before);
  assert.match(s.notices.at(-1), /kept/);
});
console.log("Prismheart journey saves: " + checks + " focused checks passed");
