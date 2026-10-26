// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/battle_charge_cue_test.js
// Actual AI/action guards, choice/undo, status helpers and battle paint; no complete fight or traversal.
// Canonical Windcut floor-zone/formation membership is evidence, not a played dungeon route.
// Controlled RNG streams and explicit 112px atlas rectangles are finite VM/paint peers, not runtime acceptance.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x)), parties = data("party").party, catalog = data("spells").spells;
const types = data("prism-bestiary").types, zones = data("prism-encounters").zones;
const windcut = data("dungeons").dungeons.prism.find(d => d.name === "Windcut Aerie"); assert.ok(windcut);
const windZones = [...new Set(windcut.floors.map(f => f.encounters.zone))];
assert.ok(windZones.includes("mountain") && windZones.includes("mountain_deep"));
const byKey = Object.fromEntries(types.map(f => [f.key, f]));
const layouts = windZones.flatMap(zone => zones[zone].formations.filter(f => f.enemies.some(k => byKey[k].behaviour === "charge")).map(f => ({ zone, enemies: f.enemies })));
assert.ok(layouts.length); const first = layouts.find(f => f.enemies.length === 4 && f.enemies.every(k => k === "prism_best_thunder_ram")); assert.ok(first);
const deep = layouts.find(f => f.zone === "mountain_deep" && f.enemies.includes("prism_best_ember_ram")); assert.ok(deep);
const gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("const hit ="), line("const rnd ="), line("const ri ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "const fieldSpells ="), between("const STATUS =", "/* ---------- bestiary:"),
  between("function passTime(", "function wakeAt("), between("function startBattle(", "const ELEM ="), line("const ELEM ="), line("const CMDS ="), line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="),
  between("function nextChooser(", "function endRound()"), line("function wrap("), between("function spellHint(", "/* ---------- title:"), between("function titlePrompt(", "function drawTitle("),
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={makeMember,startBattle,battleTick,advanceChooser,doAction,foeTurn,foeHit,drawBattle,drawBattleTarget,drawChargeBadge,statusPill,tags,has,inflict,cure,roundStatuses,landHit,cleanup,battleItems,battleItemStock,battleCmds,spellOf,chars:CHARS,statuses:STATUS};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], pressed = {}, pressedAt = {}, rolls = [], calls = { rng: 0, storage: 0, meet: 0 };
  const math = Object.create(Math); math.random = () => { calls.rng++; assert.ok(rolls.length, "unexpected RNG: never run AI while drawing"); return rolls.shift(); };
  const known = new Set(parties[realm].members.flatMap(m => m.spells)), rects = {};
  types.forEach((f, i) => { rects["Foe_" + f.key] = [i * 128, 0, 112, 112]; });
  parties[realm].members.forEach((m, i) => { rects["Party_" + m.job] = [i * 128, 128, 112, 112]; });
  const c = { W: width, H: 224, D: { realm_key: realm, realm_profile: realm === "portal" ? { start_level: 1 } : null, party: clone(parties[realm]),
      spells: clone(catalog.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), foes: clone(byKey), zones: clone(zones), dungeons: [],
      backdrop_for_zone: { mountain: "mountain-peer", mountain_deep: "mountain-peer" }, rects: { sprites: rects, spells: {}, backdrops: { "mountain-peer": [0, 0, 320, 180] } } },
    GEAR: clone(gear), party: [], reserve: [], bag: { "Herb Tonic": 2, "Feather of Waking": 1 }, gold: 237,
    state: { beaten: new Set(), seen: {}, sinceBattle: 11, day: 1, minute: 480 }, map: { kind: "dungeon", dungeon: 1, floor: 0, cue: "TOWER" },
    B: null, mode: "field", fade: 0, fadeCb: null, settingsFramePaused: true, now: 0, pressed, pressedAt,
    window: {}, PAD: null, Math: math, IM: { backdrops: "backdrop-peer", spells: "spell-atlas-peer" }, performance: { now: () => 0 },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), meet() { calls.meet++; }, cue() {}, sfx: s => sounds.push(s), toast() {},
    saveGame() { calls.storage++; throw new Error("charge cue cannot save"); },
    localStorage: Object.fromEntries(["getItem", "setItem", "removeItem"].map(k => [k, () => { calls.storage++; throw new Error("charge cue cannot use native storage"); }])),
    spr(sheet, name, x, y, sx, sw, sh, scale = 1) { const r = c.D.rects.sprites[name]; assert.ok(r, name); paints.push({ kind: "sprite", name, x, y, w: (sw || r[2]) * scale, h: (sh || r[3]) * scale }); },
    cursor(x, y) { paints.push({ kind: "cursor", x, y, w: 8, h: 8 }); },
    gauge(x, y, w, fraction, color) { paints.push({ kind: "gauge", x, y, w, h: 5, fraction, color }); },
    win(x, y, w, h) { paints.push({ kind: "window", x, y, w, h }); }, tw: value => String(value).length * 6,
    text(value, x, y, color = "#ffffff", shadow = "#202040") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color, shadow }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); },
      drawImage(image, sx, sy, sw, sh, x, y, w, h) { paints.push({ kind: "image", image, x, y, w, h }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  const resources = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold, state: { ...c.state, beaten: [...c.state.beaten] } });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, map: c.map, B: c.B, mode: c.mode, fade: c.fade, pressed, pressedAt, now: c.now, calls, sounds, rolls });
  const s = { c, api: c.api, paints, sounds, pressed, calls, resources,
    rolls(...values) { assert.equal(rolls.length, 0, "previous controlled stream was not consumed"); rolls.push(...values); },
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.battleTick(0); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = snapshot(); c.api.drawBattle(); assert.equal(snapshot(), before, "painting changed AI/state/resources/queue/input/RNG/storage"); return paints; },
    start(layout = first) { c.api.startBattle(layout.zone, null, layout.enemies); c.fadeCb(); s.tick("a"); assert.equal(c.B.phase, "cmd"); c.fade = 0; return s; },
    labels() { c.PAD = { devices: () => [{ index: 0 }], label: a => ({ confirm: "ABCDEFGH", cancel: "IJKLMNOP" })[a] }; }
  };
  return s.start();
}
const textAt = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
const badges = s => s.paints.filter(p => p.kind === "rect" && p.color === "#101526" && p.w === 48 && p.h === 9 && p.y < 144);
const pills = s => s.paints.filter(p => p.kind === "rect" && p.color === "#101526" && p.w === 24 && p.h === 9 && p.y < 144);
const intersects = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
function gather(s, f = s.c.B.foes[0]) { const rng = s.calls.rng; s.api.doAction({ kind: "foe", who: f }); assert.equal(f.charged, true); assert.equal(s.calls.rng, rng); assert.match(s.c.B.msg, /GATHERING ITSELF/); return f; }
function command(s, name) { assert.equal(s.c.B.sub, null); const commands = Array.from(s.api.battleCmds()), index = commands.indexOf(name); assert.ok(index >= 0, name); for (let i = 0; s.c.B.cmd !== index && i < commands.length; i++) s.tick("down"); assert.equal(s.c.B.cmd, index); s.tick("a"); }
function chooseSpell(s, name) { command(s, "MAGIC"); const list = s.c.party[s.c.B.who].spells.map(s.api.spellOf).filter(Boolean), index = list.findIndex(sp => sp.name === name); assert.ok(index >= 0, name); for (let i = 0; i < index; i++) s.tick("down"); s.tick("a"); }
function assertBadge(s, f) {
  const stacked = s.api.tags(f).length > 0, x = Math.round(Math.max(0, Math.min(s.c.W - 48, f.x + f.size / 2 - 24))), y = Math.round(f.y + f.size - (stacked ? 18 : 7));
  const badge = badges(s).find(p => p.x === x && p.y === y); assert.ok(badge, f.name + " at " + x + "," + y);
  const word = s.paints.find(p => p.kind === "text" && p.label === "CHARGED" && p.x === x + 3 && p.y === y + 1); assert.ok(word); assert.equal(word.shadow, null); assert.equal(word.color, "#f8d878"); assert.ok(word.x + word.w <= x + 48);
  assert.ok(badge.y >= 0 && badge.y + badge.h <= 144 && badge.x >= 0 && badge.x + badge.w <= s.c.W);
  if (stacked) { const pill = pills(s).find(p => p.x === Math.round(f.x + f.size / 2 - 12) && p.y === Math.round(f.y + f.size - 7)); assert.ok(pill); assert.equal(pill.y - badge.y, 11); assert.ok(!intersects(badge, pill)); }
  const lastArt = Math.max(...s.paints.map((p, i) => p.kind === "sprite" || p.kind === "image" ? i : -1)); assert.ok(s.paints.indexOf(badge) > lastArt, "charge word survives all overlapping art/effects");
  return badge;
}
function assertBounds(s) { for (const p of s.paints) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function assertCard(s, expected) { const row = textAt(s, 174, 6)[0], split = s.c.W < 320 ? 120 : 150; assert.equal(row.label, expected); assert.ok(row.x + row.w <= split - 6); return s.paints.filter(p => p.kind === "text" && p.x === 6 && p.y >= 152); }
check("canonical Windcut floor zones contain Thunder/Ember charger formations and exact startBattle placement", () => {
  assert.ok(layouts.some(f => f.enemies.includes("prism_best_thunder_ram"))); assert.ok(layouts.some(f => f.zone === "mountain_deep" && f.enemies.includes("prism_best_ember_ram")));
  const s = session(); first.enemies.forEach((key, i) => { const f = s.c.B.foes[i]; assert.equal(f.key, key); assert.equal(f.beh, byKey[key].behaviour); assert.equal(f.atk, byKey[key].attack); assert.equal(f.x, 24 + i % 2 * 70 + (i > 1 ? 18 : 0)); assert.equal(f.y, 26 + Math.floor(i / 2) * 52 + i % 2 * 8); }); assert.equal(s.calls.rng, 0);
});
check("actual gathering sets the persistent flag without damage/RNG and the next command view exposes it", () => {
  const s = session(), before = s.resources(), f = gather(s); assert.equal(s.resources(), before); assert.equal(f.turns, 1); assert.equal(s.c.B.turn, 1); assert.ok(s.c.B.pops.some(p => p.txt === "!!"));
  s.c.B.pops = []; s.draw(); assertBadge(s, f); assert.equal(s.c.B.phase, "cmd"); assert.equal(s.c.B.acts.length, 0);
});
check("sleep skips preserve charge until the next eligible hit and a charged miss also consumes it", () => {
  for (const hit of [true, false]) { const s = session(), f = gather(s), beforeHP = s.c.party.map(m => m.hp); s.api.inflict(f, "sleep"); const before = s.resources(), turns = f.turns, rng = s.calls.rng;
    s.api.doAction({ kind: "foe", who: f }); assert.equal(f.charged, true); assert.equal(f.turns, turns); assert.equal(s.calls.rng, rng); assert.equal(s.c.B.wait, 0.45); assert.match(s.c.B.msg, /ASLEEP/); assert.equal(s.resources(), before);
    s.api.cure(f, "sleep"); s.rolls(...(hit ? [0, 0.5, 0.5] : [0, 0])); s.api.doAction({ kind: "foe", who: f }); assert.equal(f.charged, false); assert.equal(f.turns, turns + 1); assert.equal(s.calls.rng - rng, hit ? 3 : 2);
    if (hit) { assert.ok(s.c.party[0].hp < beforeHP[0]); assert.match(s.c.B.msg, /UNLEASHES ITSELF/); } else { assert.deepEqual(s.c.party.map(m => m.hp), beforeHP); assert.match(s.c.B.msg, /MISSES/); }
    s.c.B.pops = []; s.draw(); assert.equal(badges(s).length, 0); }
});
check("actual Defend halves charged foeHit with the identical controlled miss/damage rolls", () => {
  const plain = session().start(deep), guarded = session().start(deep); const a = plain.c.party[0], b = guarded.c.party[0];
  guarded.api.doAction({ kind: "defend", who: b }); assert.equal(b.defend, true); assert.equal(guarded.calls.rng, 0);
  plain.rolls(0.5, 0.5); guarded.rolls(0.5, 0.5); const damage = plain.api.foeHit(plain.c.B.foes[0], a, 2.2, 0.06), protectedDamage = guarded.api.foeHit(guarded.c.B.foes[0], b, 2.2, 0.06);
  assert.ok(damage > 1 && protectedDamage < damage); assert.ok(Math.abs(2 * protectedDamage - damage) <= 1); assert.equal(plain.calls.rng, 2); assert.equal(guarded.calls.rng, 2); assert.equal(a.max - a.hp, damage); assert.equal(b.max - b.hp, protectedDamage);
});
check("charge remains separate from the unchanged canonical status/cure system", () => {
  const s = session(), f = gather(s); assert.deepEqual(Object.keys(s.api.statuses), ["poison", "sleep", "protect", "haste", "slow", "confuse", "bind", "paralyze", "blind", "burn"]); assert.equal(s.api.statuses.charged, undefined);
  s.api.inflict(f, "poison"); assert.deepEqual(Array.from(s.api.tags(f)), ["poison"]); assert.equal(s.api.cure(f, "poison"), true); assert.equal(s.api.cure(f, "poison"), false); assert.equal(f.charged, true); assert.deepEqual(Array.from(s.api.tags(f)), []);
  assert.ok(Object.values(gear).some(it => /cure poison/.test(it.effect || ""))); s.c.B.pops = []; s.draw(); assertBadge(s, f);
});
for (const width of [320, 256]) check("all authored charger-bearing Windcut layouts keep badges above status/after art and outside HUD at " + width, () => {
  const s = session(width);
  for (const layout of layouts) { s.start(layout); s.c.B.foes.forEach((f, i) => { if (f.beh === "charge") gather(s, f); if (i % 3 === 1) f.status = { poison: true }; if (i % 3 === 2) f.status = { sleep: 3, burn: 3, slow: 4 }; });
    s.c.B.pops = []; const sp = s.api.spellOf("Ember"); assert.ok(sp); s.c.D.rects.spells["fx:" + sp.name] = [0, 0, 480, 48]; s.c.B.fx = { name: sp.name, t: 0.2, targets: [s.c.B.foes.at(-1)] };
    s.draw(); assertBounds(s); const expected = s.c.B.foes.filter(f => f.charged); assert.equal(badges(s).length, expected.length); expected.forEach(f => assertBadge(s, f));
    const marked = badges(s); for (let i = 0; i < marked.length; i++) for (let j = i + 1; j < marked.length; j++) assert.ok(!intersects(marked[i], marked[j]), "separate foes' charge labels overlap");
    const firstWindow = s.paints.findIndex(p => p.kind === "window"); marked.forEach(p => assert.ok(s.paints.indexOf(p) < firstWindow)); assert.deepEqual(textAt(s, 147).map(p => p.label), ["PARTY", "HP", "MP"]); }
});
check("every canonical status and multi-status rotation leave CHARGED stable and independently stacked", () => {
  const s = session(256), f = gather(s); s.c.B.pops = [];
  for (const key of Object.keys(s.api.statuses)) { f.status = { [key]: key === "poison" ? true : 3 }; s.draw(); const badge = assertBadge(s, f), pill = pills(s)[0], label = s.paints.find(p => p.kind === "text" && p.x === pill.x + 3 && p.y === pill.y + 1); assert.equal(label.label, s.api.statuses[key].tag); assert.equal(pill.y - badge.y, 11); }
  f.status = { poison: true, sleep: 3, blind: 4 }; const seen = [];
  for (const time of [0, 1.2, 2.4]) { s.c.B.t = time; s.draw(); assertBadge(s, f); const p = pills(s)[0]; seen.push(s.paints.find(t => t.kind === "text" && t.x === p.x + 3 && t.y === p.y + 1).label); }
  assert.deepEqual(seen, ["PSN", "SLP", "BLN"]); assert.equal(f.charged, true);
});
check("uncharged, dead-with-flash and Portal foes have no charge cue while inherited art may remain", () => {
  const clean = session(); clean.draw(); assert.equal(badges(clean).length, 0);
  const s = session(), f = gather(s); f.hp = 0; s.c.B.flash[f.key + f.x] = 0.2; s.c.B.pops = []; s.draw(); assert.ok(s.paints.some(p => p.kind === "sprite" && p.name === f.img && p.x === f.x)); assert.equal(badges(s).length, 0); assert.equal(f.charged, true, "renderer does not rewrite inherited dead state");
  // Supply the known Prism formation solely as a Portal renderer-guard witness;
  // this is not an authored Portal encounter projection or balance claim.
  const p = session(256, "portal"), foe = gather(p); p.c.B.pops = []; p.draw(); assert.equal(badges(p).length, 0); p.c.B.sub = "target"; p.c.B.pending = { kind: "attack", who: p.c.party[0] }; p.c.B.list = p.c.B.foes; p.c.B.target = 0; p.draw(); assert.equal(textAt(p, 174, 6).length, 0); assert.ok(!p.paints.some(t => t.kind === "text" && t.label === "CHARGED")); assert.equal(foe.charged, true);
});
for (const width of [320, 256]) check("duplicate targets show only the selected living foe's CHARGED suffix and keep choose/undo at " + width, () => {
  const s = session(width); const charged = gather(s, s.c.B.foes[1]); s.c.B.pops = []; s.labels(); const before = s.resources(); command(s, "ATTACK"); s.draw(); assertCard(s, "TARGET 1/4");
  s.tick("right"); assert.equal(s.c.B.list[s.c.B.target], charged); assert.equal(charged.name, s.c.B.foes[0].name); s.draw(); const card = assertCard(s, "TARGET 2/4 CHARGED"); assert.equal(card.find(p => p.y === 164).label, charged.name.toUpperCase()); assert.ok(card.every(p => !/\bHP\b|\bMP\b|\bATK\b|\bDEF\b/.test(p.label)), "foe statistics remain undisclosed"); assert.ok(s.paints.some(p => p.kind === "cursor" && p.x === charged.x - 10));
  assert.equal(textAt(s, 204, 6)[0].label, "ABCDEFGH: CHOOSE"); assert.equal(textAt(s, 214, 6)[0].label, "IJKLMNOP: BACK"); s.tick("a"); assert.equal(s.c.B.acts[0].target, charged); assert.equal(s.c.B.who, 1); assert.equal(s.resources(), before); s.tick("b"); assert.equal(s.c.B.who, 0); assert.equal(s.c.B.acts.length, 0); assert.equal(charged.charged, true); assert.equal(s.resources(), before);
});
check("ally/item/magic target facts, pending Back+A and resource reservations retain their existing paths", () => {
  const s = session(256); gather(s); s.c.B.pops = []; command(s, "DEFEND"); const before = s.resources(); chooseSpell(s, "Mend"); s.draw(); assertCard(s, "TARGET 1/4"); assert.equal(textAt(s, 184, 6)[0].label, "HP " + s.c.party[0].hp + "/" + s.c.party[0].max); assert.equal(textAt(s, 194, 6)[0].label, "MP " + s.c.party[0].mp + "/" + s.c.party[0].mmax);
  s.tick("b", "a"); assert.equal(s.c.B.sub, "magic"); assert.equal(!!s.pressed.a, false); s.tick(); assert.equal(s.c.B.sub, "magic"); assert.equal(s.resources(), before);
  s.tick("b"); command(s, "ITEM"); s.tick("a"); assert.equal(s.c.B.sub, "target"); const item = s.c.B.pending.item; s.draw(); assertCard(s, "TARGET 1/4"); assert.ok(!textAt(s, 174, 6)[0].label.includes("CHARGED")); s.tick("a"); assert.equal(s.c.B.acts.at(-1).item, item); const stock = s.api.battleItemStock(item); s.tick("b"); assert.equal(s.api.battleItemStock(item), stock + 1); assert.equal(s.resources(), before);
  // Resume the known offensive caster using ordinary prior-hero Defend choices, without initiative/action execution.
  while (s.c.B.who < s.c.party.findIndex(m => m.job === "Runecaster")) command(s, "DEFEND"); chooseSpell(s, "Ember"); s.draw(); assertCard(s, "TARGET 1/4 CHARGED"); assert.equal(textAt(s, 184, 6)[0].label, "FIRE / FOE"); assert.equal(textAt(s, 194, 6).length, 0); assert.equal(s.resources(), before);
});
check("controlled former missing-badge and missing-target-suffix variants fail the visible invariants", () => {
  const call = "    drawChargeBadge(f, ft.length > 0);"; assert.ok(source.includes(call)); const old = session(320, "prism", source.replace(call, "")); const f = gather(old); old.c.B.pops = []; old.draw(); assert.throws(() => assertBadge(old, f), assert.AssertionError);
  const suffix = '(charged ? " CHARGED" : "")'; assert.ok(source.includes(suffix)); const missing = session(256, "prism", source.replace(suffix, '""')); gather(missing); missing.c.B.pops = []; command(missing, "ATTACK"); missing.draw(); assert.throws(() => assertCard(missing, "TARGET 1/4 CHARGED"), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline (compile only)" });
console.log("battle charge cue: " + groups + " focused groups passed; controlled VM/paint/atlas peers, no route/combat/browser/native acceptance");
