// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/battle_target_card_test.js
// Actual chooser/undo/queue and painter, canonical party/spells/items/duplicate-foe formation.
// Canvas-command capture only; no action execution, game boot, assets, DOM, browser or native runtime.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x)), partyData = data("party").party.prism, catalog = data("spells").spells;
const foeData = data("prism-bestiary").types, formation = data("prism-encounters").zones.plains.formations.find(f => f.enemies.length === 3 && f.enemies.every(k => k === f.enemies[0]));
assert.ok(formation, "authored duplicate-foe formation exists");
const gear = {};
for (const shop of Object.values(data("interiors").interiors.prism)) for (const item of shop.stock || [])
  if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "const fieldSpells ="), between("const STATUS =", "function inflict("), line("function wrap("),
  between("function startBattle(", "const ELEM ="), line("const ELEM ="), line("const CMDS ="), line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="),
  between("function nextChooser(", "function pop("), between("function spellHint(", "/* ---------- title:"), between("function titlePrompt(", "function drawTitle("),
  "this.api={makeMember,startBattle,battleTick,advanceChooser,nextChooser,drawBattle,drawBattleTarget,battleItems,battleItemStock,battleCmds,spellOf,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, production = source) {
  const paints = [], cursors = [], sounds = [], pressed = new Set(), calls = { rng: 0, storage: 0 };
  const known = new Set(partyData.members.flatMap(m => m.spells)), fixedMath = Object.create(Math);
  fixedMath.random = () => { calls.rng++; throw new Error("painting cannot consume RNG"); };
  const c = { W: width, H: 224, D: { realm_key: "prism", party: clone(partyData), spells: clone(catalog.filter(s => s.realm === "prism" && (known.has(s.name) || s.tier <= 2))),
      foes: Object.fromEntries(foeData.map(f => [f.key, clone(f)])), dungeons: [], backdrop_for_zone: { plains: "field" }, rects: { backdrops: {}, spells: {}, sprites: {} } },
    GEAR: clone(gear), party: [], reserve: [], bag: {}, gold: 237, state: { beaten: new Set(), sinceBattle: 0, minute: 480 },
    map: { kind: "world", cue: "FIELD" }, mode: "field", B: null, fade: 0, fadeCb: null, settingsFramePaused: true,
    window: {}, PAD: null, IM: { spells: "spells", backdrops: "backdrops" }, Math: fixedMath, performance: { now: () => 0 },
    hit(key) { const value = pressed.has(key); pressed.delete(key); return value; },
    rnd(a) { calls.rng++; return a; }, clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)),
    passTime() {}, meet() {}, cue() {}, sfx: name => sounds.push(name), toast() {},
    saveGame() { calls.storage++; throw new Error("painting cannot save"); },
    localStorage: { getItem() { calls.storage++; throw new Error("painting cannot read storage"); }, setItem() { calls.storage++; throw new Error("painting cannot write storage"); } },
    spr() {}, gauge() {}, win() {}, cursor: (x, y) => cursors.push({ x, y }), tw: value => String(value).length * 6,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ label, x, y, color, w: label.length * 6, h: 8 }); },
    g: { fillStyle: "", fillRect() {}, drawImage() {} }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  c.reserve = [c.api.makeMember(c.D.party.members.find(m => m.job === "Beastcaller"), 15)];
  c.api.startBattle("plains", null, formation.enemies); c.fadeCb();
  const resources = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold, state: { ...c.state, beaten: [...c.state.beaten] } });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, battle: c.B, map: c.map, mode: c.mode, fade: c.fade, calls });
  const s = { c, paints, cursors, sounds, pressed, calls, resources,
    tick(...keys) { keys.forEach(k => pressed.add(k)); c.api.battleTick(0); },
    draw() { paints.length = 0; cursors.length = 0; const before = snapshot(); c.api.drawBattle(); assert.equal(snapshot(), before, "painting changed state/resources/queue/RNG/storage"); return paints; },
    card() { return paints.filter(p => p.x === 6 && p.y >= 152 && p.y <= 214); }
  };
  s.tick("a"); assert.equal(c.B.phase, "cmd"); return s;
}
function command(s, name) {
  assert.equal(s.c.B.phase, "cmd"); assert.equal(s.c.B.sub, null);
  const commands = Array.from(s.c.api.battleCmds()), wanted = commands.indexOf(name); assert.ok(wanted >= 0, name);
  for (let i = 0; s.c.B.cmd !== wanted && i < commands.length; i++) s.tick("down");
  assert.equal(s.c.B.cmd, wanted); s.tick("a");
}
function advanceTo(s, index) { for (let i = 0; s.c.B.who < index && i < 4; i++) command(s, "DEFEND"); assert.equal(s.c.B.who, index); }
function spell(s, name) {
  command(s, "MAGIC"); const options = s.c.party[s.c.B.who].spells.map(s.c.api.spellOf).filter(Boolean), index = options.findIndex(sp => sp.name === name); assert.ok(index >= 0, name);
  for (let i = 0; i < index; i++) s.tick("down"); assert.equal(s.c.B.oi, index); s.tick("a");
}
function item(s, name) {
  command(s, "ITEM"); const index = Array.from(s.c.api.battleItems()).indexOf(name); assert.ok(index >= 0, name);
  for (let i = 0; i < index; i++) s.tick("down"); s.tick("a");
}
function assertCard(s, action, target = s.c.B.list[s.c.B.target]) {
  s.draw(); const card = s.card(), at = y => card.find(p => p.y === y), columns = s.c.W < 320 ? 18 : 23, split = s.c.W < 320 ? 120 : 150;
  assert.ok(at(152).label.startsWith(action.toUpperCase()), "selected action is named");
  assert.equal(at(174).label, "TARGET " + (s.c.B.target + 1) + "/" + s.c.B.list.length);
  if (target.name.length < columns) assert.equal(at(164).label, target.name.toUpperCase());
  for (const p of card) { assert.ok(p.x >= 0 && p.y >= 144 && p.x + p.w <= split - 6 && p.y + p.h <= 224, "card outside command window " + JSON.stringify(p));
    assert.ok([...p.label].every(ch => s.c.api.chars.includes(ch)), "unsupported font glyph"); }
  assert.ok(at(204).label.endsWith(": CHOOSE")); assert.ok(at(214).label.endsWith(": BACK")); return card;
}
const hasCard = s => s.card().some(p => p.y === 174 && /^TARGET /.test(p.label));
for (const width of [320, 256]) check("actual duplicate-foe attack at " + width + ": selected identity/index, no foe stats, queue and undo", () => {
  const s = session(width); s.c.B.foes[0].hp = 0;
  Object.assign(s.c.B.foes[1], { hp: 730319, max: 730321, atk: 730323, def: 730325, spd: 730327 });
  const before = s.resources(); command(s, "ATTACK"); assert.equal(s.c.B.list.length, 2); assert.equal(s.c.B.list[0], s.c.B.foes[1]);
  s.tick("right"); const target = s.c.B.list[1]; assert.equal(target, s.c.B.foes[2]); assert.equal(target.name, s.c.B.foes[1].name);
  const card = assertCard(s, "ATTACK", target); assert.equal(card.length, 5); assert.ok(card.every(p => !/HP|MP|ATK|DEF|7303/.test(p.label)));
  assert.ok(s.cursors.some(p => p.x === target.x - 10), "existing sprite cursor points to that same foe");
  s.tick("a"); assert.equal(s.c.B.acts.length, 1); assert.equal(s.c.B.acts[0].target, target); assert.equal(s.c.B.who, 1); assert.equal(s.resources(), before);
  s.tick("b"); assert.equal(s.c.B.who, 0); assert.equal(s.c.B.acts.length, 0); assert.equal(s.resources(), before);
});
for (const width of [320, 256]) check("actual Mend at " + width + ": living-only list, exact ally facts, Back+A and plan undo", () => {
  const s = session(width), caster = s.c.party.findIndex(m => m.job === "Lightmender"); s.c.party[3].hp = 0;
  advanceTo(s, caster); const planned = s.c.B.acts.length, before = s.resources(); spell(s, "Mend");
  assert.equal(s.c.B.sub, "target"); assert.deepEqual(Array.from(s.c.B.list), s.c.party.filter(p => p.hp > 0)); assert.ok(!s.c.B.list.includes(s.c.reserve[0]));
  s.tick("right"); const target = s.c.B.list[1], card = assertCard(s, "MEND", target), sp = s.c.api.spellOf("Mend");
  assert.equal(card.find(p => p.y === 152).label, "MEND " + sp.mp + "MP");
  assert.equal(card.find(p => p.y === 184).label, "HP " + target.hp + "/" + target.max); assert.equal(card.find(p => p.y === 194).label, "MP " + target.mp + "/" + target.mmax);
  s.tick("b", "a"); assert.equal(s.c.B.sub, "magic"); assert.equal(s.c.B.acts.length, planned); assert.equal(s.pressed.has("a"), false); s.tick(); assert.equal(s.c.B.sub, "magic");
  s.tick("a"); s.tick("right"); const chosen = s.c.B.list[1]; s.tick("a"); assert.equal(s.c.B.acts.at(-1).target, chosen); assert.equal(s.c.B.acts.at(-1).spell.name, "Mend");
  assert.equal(s.resources(), before); s.tick("b"); assert.equal(s.c.B.who, caster); assert.equal(s.c.B.acts.length, planned); assert.equal(s.resources(), before);
});
check("actual Feather item exposes the downed recipient and preserves stock through cancel, plan and undo", () => {
  const s = session(256), target = s.c.party[2]; target.hp = 0; s.c.bag = { "Feather of Waking": 1 }; const before = s.resources(); item(s, "Feather of Waking");
  assert.deepEqual(Array.from(s.c.B.list), s.c.party); assert.ok(!s.c.B.list.includes(s.c.reserve[0])); s.tick("right"); s.tick("right");
  const card = assertCard(s, "FEATHER OF WAKING", target); assert.equal(card.find(p => p.y === 184).label, "HP 0/" + target.max); assert.equal(card.find(p => p.y === 184).color, "#f87878");
  s.tick("b", "a"); assert.equal(s.c.B.sub, "item"); assert.equal(s.c.B.acts.length, 0); s.tick(); assert.equal(s.c.B.sub, "item");
  s.tick("a"); s.tick("right"); s.tick("right"); s.tick("a"); assert.equal(s.c.B.acts[0].target, target); assert.equal(s.c.B.acts[0].item, "Feather of Waking");
  assert.equal(s.c.api.battleItemStock("Feather of Waking"), 0); assert.equal(s.resources(), before);
  s.tick("b"); assert.equal(s.c.B.who, 0); assert.equal(s.c.B.acts.length, 0); assert.equal(s.c.api.battleItemStock("Feather of Waking"), 1); assert.equal(s.resources(), before);
});
check("actual offensive Ember shows existing spell meaning and MP shortage still refuses before targets", () => {
  const s = session(256), caster = s.c.party.findIndex(m => m.job === "Runecaster"); advanceTo(s, caster); const before = s.resources(), planned = s.c.B.acts.length;
  spell(s, "Ember"); const card = assertCard(s, "EMBER"); assert.equal(card.find(p => p.y === 184).label, "FIRE / FOE"); assert.equal(card.some(p => p.y === 194), false);
  s.tick("b"); assert.equal(s.c.B.sub, "magic"); assert.equal(s.resources(), before); assert.equal(s.c.B.acts.length, planned);
  const sp = s.c.api.spellOf("Ember"); s.c.party[caster].mp = sp.mp - 1; s.tick("a"); assert.equal(s.c.B.sub, "magic"); assert.equal(s.c.B.acts.length, planned); s.draw(); assert.equal(hasCard(s), false);
});
check("canonical all-foe spell and Smoke Pouch still bypass recipient selection without spending", () => {
  const s = session(), caster = s.c.party.findIndex(m => m.job === "Runecaster"), sp = s.c.api.spellOf("Tremor"); assert.equal(sp.target, "all_enemies");
  s.c.party[caster].spells.push(sp.name); // Valid already-learned canonical lesson; learning itself is outside this presentation fixture.
  advanceTo(s, caster); const before = s.resources(), planned = s.c.B.acts.length; spell(s, sp.name);
  assert.equal(s.c.B.sub, null); assert.equal(s.c.B.acts.length, planned + 1); assert.equal(s.c.B.acts.at(-1).target, "all"); assert.equal(s.resources(), before); s.draw(); assert.equal(hasCard(s), false);
  const smoke = session(); smoke.c.bag = { "Smoke Pouch": 1 }; const prior = smoke.resources(); item(smoke, "Smoke Pouch");
  assert.equal(smoke.c.B.sub, null); assert.equal(smoke.c.B.acts[0].target, null); assert.equal(smoke.resources(), prior); smoke.draw(); assert.equal(hasCard(smoke), false);
});
for (const width of [320, 256]) check("accepted long call signs/large values and eight-character physical labels fit at " + width, () => {
  const s = session(width), caster = s.c.party.findIndex(m => m.job === "Lightmender"), target = s.c.party[0];
  target.name = "ß".repeat(64); target.hp = target.max = target.mp = target.mmax = Number.MAX_SAFE_INTEGER;
  s.c.PAD = { devices: () => [{ index: 3 }], label(action, index) { assert.equal(index, 3); return action === "confirm" ? "ABCDEFGH" : "12345678"; } };
  advanceTo(s, caster); spell(s, "Mend"); const before = s.resources(), card = assertCard(s, "MEND", target), columns = width < 320 ? 18 : 23, cap = width < 320 ? "999+" : "9999+";
  const name = card.find(p => p.y === 164).label; assert.equal(name.length, columns); assert.ok(name.endsWith("...")); assert.ok(/^S+\.\.\.$/.test(name));
  assert.equal(card.find(p => p.y === 184).label, "HP " + cap + "/" + cap); assert.equal(card.find(p => p.y === 194).label, "MP " + cap + "/" + cap);
  assert.equal(card.find(p => p.y === 204).label, "ABCDEFGH: CHOOSE"); assert.equal(card.find(p => p.y === 214).label, "12345678: BACK");
  assert.equal(target.name, "ß".repeat(64)); assert.equal(target.hp, Number.MAX_SAFE_INTEGER); assert.equal(s.resources(), before);
});
check("last eligible chooser queues the same target and later painting neither rerolls nor spends", () => {
  const s = session(); s.c.party.slice(1).forEach(m => { m.hp = 0; }); const before = s.resources(); command(s, "ATTACK"); const target = s.c.B.list[0]; s.tick("a");
  assert.equal(s.c.B.phase, "act"); assert.equal(s.c.B.acts[0].target, target); assert.ok(s.c.B.queue.includes(s.c.B.acts[0])); assert.ok(s.calls.rng > 0, "ordinary initiative still rolls while building the queue");
  assert.equal(s.resources(), before); s.draw(); assert.equal(hasCard(s), false); assert.equal(s.calls.storage, 0);
});
check("absent pending uses existing message; Portal target mode preserves the same legacy message branch", () => {
  for (const portal of [false, true]) { const s = session(256); command(s, "ATTACK"); s.c.B.msg = "KEEP THE BATTLE MESSAGE.";
    if (portal) s.c.D.realm_key = "portal"; else delete s.c.B.pending; // Isolated branch-compatibility setup, not a Portal encounter projection.
    s.draw(); assert.equal(hasCard(s), false); const message = s.paints.filter(p => p.x === 10 && p.y >= 152).map(p => p.label).join(" "); assert.equal(message, "KEEP THE BATTLE MESSAGE."); }
});
check("controlled former target-message renderer fails the selected-action/recipient assertion", () => {
  const old = source.replace("    drawBattleTarget(split);", '    wrap(B.msg || "", compact ? 16 : 22).slice(0, 5).forEach((l, i) => text(l, 10, 152 + i * 13));'); assert.notEqual(old, source);
  const s = session(256, old); command(s, "ATTACK"); assert.throws(() => assertCard(s, "ATTACK"));
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("battle target card: " + checks + " focused groups passed; actual chooser/painter capture only, no action/assets/browser/native acceptance");
