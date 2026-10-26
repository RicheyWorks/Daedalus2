// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/summon_book_test.js
// Actual field handlers/painters, summons.table/unlocked and canonical selected QUEST boss records.
// Atlas rectangles are explicit square/wide/tall peers, not measurements or acceptance of real artwork.
// No combat, quest traversal, browser/device/native storage/build/full-IIFE execution.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Summons = require("./summons.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n"), builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts, spells = data("spells").spells, bosses = data("prism-bosses").bosses;
function tuples(name) { const m = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(m, name); return [...m[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]); }
const quest = tuples("QUEST"), optional = tuples("OPTIONAL_QUEST"), final = builder.match(/^FINAL = "([^"]+)"$/m)[1], scale = JSON.parse(builder.match(/^FINAL_SCALE = (\{[^\r\n]+\})$/m)[1]);
const pyRound = n => { const floor = Math.floor(n), rest = n - floor; return rest < 0.5 ? floor : rest > 0.5 ? floor + 1 : floor + floor % 2; };
const routes = quest.concat(optional).map(([landmark, name]) => { const boss_data = clone(bosses.find(b => b.dungeon === name)); assert.ok(boss_data);
  if (name === final) { boss_data.hp = Math.trunc(boss_data.hp * scale.hp); boss_data.attack = pyRound(boss_data.attack * scale.attack); boss_data.demo_scale = clone(scale); }
  return { name, landmark, final: name === final, optional: optional.some(([, n]) => n === name), boss_data };
});
const table = Summons.table(routes.map(d => d.boss_data), "prism"); assert.equal(table.length, 3);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"), line("function cursor("),
  between("function spr(", "function win("), between("function gauge(", "/* ---------- party ---------- */"), between("const START_LEVEL =", "/* ---------- maps"),
  between("let menu = null;", "function drawEquip("), between("const STATUS =", "/* ---------- bestiary:"),
  between("function spellHint(", "function drawBattle("), between("function titlePrompt(", "function drawTitle("), line("const SUMMONS ="), line("const mySpirits ="), line("const ELEM ="),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,drawMenu,openSummonBook,summonBookTick,drawSummonBook,fieldSpells,mySpirits,SUMMONS,cleanup," +
  "menu:()=>menu,roster,party:()=>party,chars:CHARS," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D,B,summonRules:PrismSummons})," +
  "view:()=>({mode,menu,pressed,pressedAt,now,fade})};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism") {
  const paints = [], sounds = [], pressed = {}, pressedAt = {}, calls = { rng: 0, storage: 0, damage: 0, readiness: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  const math = Object.create(Math); math.random = () => { calls.rng++; throw new Error("summon reference cannot consume gameplay RNG"); };
  // Real module table/unlocked; combat-only APIs are sentinels because this screen must not forecast readiness/damage.
  const reference = { ...Summons, damage() { calls.damage++; throw new Error("reference cannot calculate damage"); }, refusal() { calls.readiness++; throw new Error("reference cannot judge battle readiness"); } };
  const rects = { "ui:Cursor": [0, 0, 16, 8] };
  table.forEach((spirit, i) => { const dimensions = [[112, 112], [224, 112], [112, 224]][i]; rects["Boss_" + spirit.warden] = [512 * (i + 1), 0, ...dimensions]; });
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, dungeons: clone(routes), menus: clone(menus[realm]), rects: { sprites: rects },
      spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, pressedAt, now: 0, cursorNow: 0, PAD: null, B: null, actx: null, fade: 0, mode: "field", map: { kind: "town", retained: true }, P: { x: 7, y: 9, dir: "left" },
    state: { beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, day: 1, minute: 600, air: null, returnTo: null, steps: 0, sinceBattle: 0 }, opened: new Set(["retained/chest"]),
    window: { PrismSummons: reference }, PrismSummons: reference, IM: { sprites: "sprite-atlas-peer" }, performance: { now: () => c.cursorNow },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), sfx: x => sounds.push(x), drawField: () => paints.push({ kind: "field" }), shardCount: () => 0, clockText: () => "D1 10:00", isNight: () => false,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    win: (x, y, w, h) => paints.push({ kind: "window", x, y, w, h }),
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); },
      drawImage(sheet, sx, sy, sw, sh, x, y, w, h) { assert.equal(sheet, "sprite-atlas-peer"); const name = Object.keys(c.D.rects.sprites).find(n => { const r = c.D.rects.sprites[n]; return sy === r[1] && sx >= r[0] && sx < r[0] + r[2]; }); assert.ok(name); paints.push({ kind: "image", name, x, y, w, h }); } },
    localStorage: { getItem() { calls.storage++; throw new Error("summon reference cannot read native saves"); }, setItem() { calls.storage++; throw new Error("summon reference cannot save"); }, removeItem() { calls.storage++; throw new Error("summon reference cannot erase saves"); } },
    saveGame() { calls.storage++; throw new Error("summon reference cannot autosave"); }
  };
  vm.createContext(c); vm.runInContext(source, c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, calls, resources,
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.menuTick(); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), effects = JSON.stringify({ sounds, calls }); c.api.drawMenu(); assert.equal(resources(), before); assert.equal(JSON.stringify(c.api.view()), view); assert.equal(JSON.stringify({ sounds, calls }), effects); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP", menu = "QRSTUVWX") { c.PAD = { devices: () => [{ index: 0 }], label: action => ({ confirm, cancel, menu })[action] }; }
  };
}
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
function setEarned(s, names) { s.c.state.beaten.clear(); names.forEach(n => s.c.state.beaten.add(n)); }
function context(s, stage = "magic-who") {
  s.api.openMenu(); s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "magic-who");
  if (stage === "magic") { s.tick("a"); s.tick("a"); assert.equal(s.api.menu().sub, "magic-target"); s.tick("b"); s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "magic"); assert.match(s.api.menu().msg, /FOR BATTLE/); }
  return s;
}
function open(s) { s.tick("start"); assert.equal(s.api.menu().sub, "summons"); assert.equal(s.api.menu().si, 0); return s; }
function select(s, index) { for (let n = 0; s.api.menu().si !== index && n < table.length; n++) s.tick("down"); assert.equal(s.api.menu().si, index); }
function edges(s) { for (const key of ["a", "b", "start", "left", "right", "up", "down"]) assert.equal(!!s.c.pressed[key], false, key); }
function bounds(s) { for (const p of s.paints.filter(p => ["text", "rect", "window", "image"].includes(p.kind))) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function visibleEarned(s, expected) {
  s.draw(); assert.equal(at(s, 10, 12)[0].label, "SHARD SUMMONS"); assert.ok(at(s, 10).some(p => p.label === "KNOWN " + expected.length));
  const rows = s.paints.filter(p => p.kind === "text" && p.x === 24 && [84, 112, 140].includes(p.y)); assert.equal(rows.length, expected.length);
  rows.forEach((row, i) => { const prefix = row.label.replace(/\.\.\.$/, ""); assert.ok(prefix.length && expected[i].name.toUpperCase().startsWith(prefix), "only earned records appear in canonical order"); assert.equal(at(s, row.y + 12, 24)[0].label, expected[i].mp + " MP"); });
  for (const spirit of table.filter(sp => !expected.some(e => e.name === sp.name))) { assert.ok(!s.paints.some(p => p.kind === "text" && p.label === spirit.name.toUpperCase())); assert.ok(!s.paints.some(p => p.kind === "image" && p.name === "Boss_" + spirit.warden)); }
  assert.equal(at(s, 184, 12)[0].label, "BATTLE ONLY / ONCE EACH PER BATTLE"); assert.ok(!s.paints.some(p => p.kind === "text" && /DAMAGE|READY|NOT ENOUGH|ALREADY ANSWERED|CAST NOW/.test(p.label)));
}
check("actual projected QUEST table contains only three shard spirits and optional/final bosses reveal none", () => {
  const s = context(session()); assert.deepEqual(s.api.SUMMONS().map(sp => sp.warden), table.map(sp => sp.warden)); assert.equal(table.length, 3);
  setEarned(s, routes.filter(d => d.optional || d.final).map(d => d.boss_data.name)); open(s); assert.deepEqual(s.api.mySpirits(), []); visibleEarned(s, []); assert.ok(at(s, 42, 12).some(p => p.label === "NO SPIRITS YET."));
});
check("all earned subsets and all three-Warden victory orders retain the module's canonical table order", () => {
  const s = context(session());
  for (let mask = 0; mask < 8; mask++) { const expected = table.filter((_, i) => mask & (1 << i)); setEarned(s, expected.map(sp => sp.warden).reverse()); open(s); assert.deepEqual(s.api.mySpirits().map(sp => sp.name), expected.map(sp => sp.name)); visibleEarned(s, expected); s.tick("b"); }
  const [a, b, c] = table.map(sp => sp.warden); for (const order of [[a, b, c], [a, c, b], [b, a, c], [b, c, a], [c, a, b], [c, b, a]]) { setEarned(s, order); open(s); visibleEarned(s, table); assert.deepEqual(s.api.mySpirits().map(sp => sp.warden), [a, b, c]); s.tick("start"); }
});
check("opening and every closing button preserve caster/book/spell/feedback while draining concurrent edges", () => {
  for (const stage of ["magic-who", "magic"]) for (const close of ["a", "b", "start"]) { const s = context(session(), stage), m = s.api.menu(), before = s.resources(), kept = { who: m.who, ii: m.ii, spell: m.spell, msg: m.msg };
    s.tick("start", "a", ...(close === "b" ? ["up", "left"] : ["down", "right"])); assert.equal(m.sub, "summons"); assert.equal(m.summonBack, stage); assert.equal(m.si, 0); edges(s); assert.equal(s.resources(), before);
    s.tick(close, "up", "down", "left", "right"); assert.equal(m.sub, stage); assert.equal(m.summonBack, undefined); assert.equal(m.who, kept.who); assert.equal(m.ii, kept.ii); assert.equal(m.spell, kept.spell); assert.equal(m.msg, kept.msg); edges(s); assert.equal(s.resources(), before);
    s.tick(); assert.equal(m.sub, stage); assert.equal(s.resources(), before);
    // Direct helper seams also prove the drain before normal end-of-frame direction cleanup.
    for (const key of ["a", "start", "up", "down", "left", "right"]) s.c.pressed[key] = true; s.api.openSummonBook(); edges(s); assert.equal(m.si, 0);
    for (const key of ["a", "b", "start", "up", "down", "left", "right"]) s.c.pressed[key] = true; s.api.summonBookTick(); edges(s); assert.equal(m.sub, stage); assert.equal(s.resources(), before);
  }
});
check("Back beats Start and Confirm in both original magic stages without a delayed reference opening", () => {
  for (const stage of ["magic-who", "magic"]) { const s = context(session(), stage), before = s.resources(); s.tick("b", "start", "a", "up", "down", "left", "right"); assert.equal(s.api.menu().sub, stage === "magic" ? "magic-who" : null); edges(s); assert.equal(s.resources(), before); s.tick(); assert.notEqual(s.api.menu().sub, "summons"); }
});
check("spirit cursor wraps independently and Left/Right leave selection/resources intact in the audio-free fixture", () => {
  const s = context(session(), "magic"); setEarned(s, table.map(sp => sp.warden)); open(s); const m = s.api.menu(), ii = m.ii, who = m.who, before = s.resources();
  s.tick("up"); assert.equal(m.si, 2); s.tick("down"); assert.equal(m.si, 0); s.tick("down"); assert.equal(m.si, 1); s.tick("left", "right"); assert.equal(m.si, 1); assert.equal(m.ii, ii); assert.equal(m.who, who); assert.equal(s.resources(), before);
  s.draw(); assert.equal(s.paints.filter(p => p.kind === "text" && p.x === 24 && [84, 112, 140].includes(p.y)).length, 3);
});
check("empty reference is useful from a downed zero-MP noncaster and is not a field cast/readiness screen", () => {
  const s = context(session()), m = s.api.menu(); s.tick("left"); assert.equal(m.who, 0); s.api.party()[0].hp = 0; s.api.party()[0].mp = 0;
  // Observer-only queue fixture; no battle is entered or executed.
  s.c.B = { phase: "act", queue: [{ kind: "sentinel" }], acts: [], summoned: table.map(sp => sp.name) }; const before = s.resources(); open(s); s.tick("up", "down", "left", "right"); assert.equal(m.si, 0); visibleEarned(s, []); assert.equal(s.resources(), before); s.tick("a"); assert.equal(m.sub, "magic-who"); assert.equal(s.resources(), before);
  setEarned(s, table.map(sp => sp.warden)); const earned = s.resources(); open(s); visibleEarned(s, table); assert.equal(s.resources(), earned, "zero MP/downed/used observers do not turn earned information into a field cast or readiness calculation"); s.tick("b"); assert.equal(s.resources(), earned); assert.deepEqual(s.calls, { rng: 0, storage: 0, damage: 0, readiness: 0 });
});
for (const width of [320, 256]) check("earned names/costs/elements, cursor frames, aspect-constrained boss art and shard ordering fit at " + width, () => {
  const s = context(session(width)); setEarned(s, table.map(sp => sp.warden)); s.labels(); open(s); const split = width < 320 ? 112 : 128;
  for (let index = 0; index < table.length; index++) { select(s, index); const spirit = table[index]; for (const blink of [0, 300]) { s.c.cursorNow = blink; visibleEarned(s, table); bounds(s);
      assert.equal(at(s, 42, 12)[0].label, spirit.name.toUpperCase()); assert.ok(at(s, 42).some(p => p.label === spirit.mp + " MP")); assert.equal(at(s, 162, split + 12)[0].label, spirit.element.toUpperCase() + " / ALL FOES");
      const arrow = s.paints.find(p => p.kind === "image" && p.name === "ui:Cursor"), name = at(s, 84 + index * 28, 24)[0]; assert.ok(arrow && arrow.x === 12 + (blink ? 1 : 0)); assert.ok(arrow.x + arrow.w < name.x);
      const image = s.paints.find(p => p.kind === "image" && p.name === "Boss_" + spirit.warden); assert.ok(image); const r = s.c.D.rects.sprites[image.name]; assert.ok(image.w <= 72 && image.h <= 72 && image.x > split + 6 && image.x + image.w < width - 6 && image.y >= 74 && image.y + image.h <= 146); assert.equal(image.w / image.h, r[2] / r[3]);
      const imageIndex = s.paints.indexOf(image), shardIndex = s.paints.findIndex(p => p.kind === "rect" && p.w === 76 && p.h === 8 && p.y === 106); assert.ok(shardIndex >= 0 && shardIndex < imageIndex, "code-painted shard stays beneath existing art");
      assert.equal(at(s, 212, 12)[0].label, "ABCDEFGH/IJKLMNOP/QRSTUVWX: BACK");
    }
  }
});
check("missing earned artwork and an empty table use bounded generic shards without unknown Warden art", () => {
  for (const width of [320, 256]) { const s = context(session(width)); setEarned(s, [table[1].warden]); delete s.c.D.rects.sprites["Boss_" + table[1].warden]; open(s); visibleEarned(s, [table[1]]); bounds(s); assert.ok(!s.paints.some(p => p.kind === "image" && p.name.startsWith("Boss_"))); assert.ok(s.paints.some(p => p.kind === "rect" && p.w === 76 && p.h === 8));
    s.tick("b"); setEarned(s, []); open(s); visibleEarned(s, []); bounds(s); assert.ok(!s.paints.some(p => p.kind === "image")); assert.ok(at(s, 76, 12).some(p => p.label === "WARDEN SHARDS AWAKEN SUMMONS.")); }
});
for (const width of [320, 256]) check("large aliases/MP and the original magic footer's mapped summons hint stay bounded at " + width, () => {
  const s = context(session(width), "magic"), m = s.api.menu(), caster = s.api.roster()[m.who]; caster.name = "ß".repeat(64); caster.mp = caster.mmax = Number.MAX_SAFE_INTEGER; s.labels();
  for (const stage of ["magic", "magic-who"]) { m.sub = stage; s.draw(); bounds(s); const back = at(s, 214, 12)[0], hint = at(s, 214).find(p => p.label === "QRSTUVWX: SUMMONS"); assert.ok(hint && back.x + back.w < hint.x && hint.x + hint.w <= width - 12); }
  setEarned(s, table.map(sp => sp.warden)); open(s); visibleEarned(s, table); bounds(s); assert.ok(at(s, 22, 12)[0].label.startsWith("SS")); assert.ok(at(s, 22).some(p => p.label === "MP 9999+/9999+")); const before = JSON.stringify(s.paints); s.draw(); assert.equal(JSON.stringify(s.paints), before); assert.equal(caster.name, "ß".repeat(64)); assert.equal(caster.mp, Number.MAX_SAFE_INTEGER);
});
check("keyboard fallbacks and invalid labels show the actual Start reference action without guessing devices", () => {
  const s = context(session(256)); s.draw(); bounds(s); assert.ok(at(s, 214).some(p => p.label === "ENTER: SUMMONS")); open(s); s.draw(); bounds(s); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE/X/ESC/ENTER: BACK"); s.labels("INVALID LABEL", "<BAD>", "TOO LONG LABEL"); s.draw(); assert.equal(at(s, 212, 12)[0].label, "Z/SPACE/X/ESC/ENTER: BACK"); assert.deepEqual(s.calls, { rng: 0, storage: 0, damage: 0, readiness: 0 });
});
check("Portal Start retains the old ignored/buffered input path and never advertises or opens SUMMONS", () => {
  const s = session(256, "portal"); s.api.openMenu(); s.tick("down"); s.tick("a");
  for (const stage of ["magic-who", "magic"]) { if (stage === "magic") s.tick("a"); assert.equal(s.api.menu().sub, stage); s.tick("start"); assert.equal(s.api.menu().sub, stage); assert.equal(s.c.pressed.start, true); s.draw(); assert.ok(!s.paints.some(p => p.kind === "text" && /SHARD SUMMONS|: SUMMONS/.test(p.label))); for (let i = 0; i < 11; i++) s.tick(); assert.equal(!!s.c.pressed.start, false); }
  assert.deepEqual(s.api.SUMMONS(), []);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("summon book: " + groups + " focused groups passed; actual pure table/unlocked and paint/atlas peers, no combat/runtime acceptance");
