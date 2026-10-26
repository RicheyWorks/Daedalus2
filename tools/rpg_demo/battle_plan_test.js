// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/battle_plan_test.js
// Actual chooser, reservations, summon authority, undo/initiative and painter; canonical Prism records.
// Command capture only. No action execution, assets, DOM, browser, shared host or native runtime.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8"), PrismSummons = require("./summons.js");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8")), clone = x => JSON.parse(JSON.stringify(x));
const partyData = data("party").party.prism, spells = data("spells").spells, foes = data("prism-bestiary").types, bosses = data("prism-bosses").bosses;
const formation = data("prism-encounters").zones.plains.formations.find(f => f.enemies.length === 3 && f.enemies.every(k => k === f.enemies[0])); assert.ok(formation);
const questNames = Array.from(builder.match(/^QUEST = \[([^\r\n]+)\]$/m)[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g), m => m[2]);
const questBosses = bosses.filter(b => questNames.includes(b.dungeon)), gear = {};
for (const shop of Object.values(data("interiors").interiors.prism)) for (const item of shop.stock || [])
  if (item.attack != null || item.defence != null || item.effect) gear[item.name] = clone(item);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
const line = prefix => { const found = html.split("\n").find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"), between("const ITEM_KINDS =", "const fieldSpells ="),
  between("const STATUS =", "function inflict("), line("function wrap("), between("function startBattle(", "const ELEM ="), line("const ELEM ="),
  line("const CMDS ="), line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="), between("function nextChooser(", "function pop("),
  between("function spellHint(", "/* ---------- title:"), between("function titlePrompt(", "function drawTitle("),
  "this.api={makeMember,startBattle,battleTick,advanceChooser,drawBattle,drawBattlePlan,battleCmds,mySpirits,spellOf,battleItems,battleItemStock,commands:CMDS,chars:CHARS};"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, unlocked = false, production = source) {
  const paints = [], cursors = [], pressed = new Set(), calls = { rng: 0, storage: 0 }, known = new Set(partyData.members.flatMap(m => m.spells));
  const fixedMath = Object.create(Math); fixedMath.random = () => { calls.rng++; throw new Error("painting must not roll randomness"); };
  const c = { W: width, H: 224, D: { realm_key: "prism", party: clone(partyData), spells: clone(spells.filter(s => s.realm === "prism" && (known.has(s.name) || s.tier <= 2))),
      foes: Object.fromEntries(foes.map(f => [f.key, clone(f)])), dungeons: clone(questBosses).map(b => ({ boss_data: b })), backdrop_for_zone: { plains: "field" }, rects: { backdrops: {}, sprites: {}, spells: {} } },
    GEAR: clone(gear), party: [], reserve: [], bag: { "Herb Tonic": 2, "Smoke Pouch": 1 }, gold: 237,
    state: { beaten: new Set(unlocked ? questBosses.map(b => b.name) : []), sinceBattle: 0, minute: 480 }, map: { kind: "world", cue: "FIELD" },
    mode: "field", B: null, fade: 0, fadeCb: null, settingsFramePaused: true, window: { PrismSummons }, PrismSummons, PAD: null,
    IM: { spells: "spells", backdrops: "backdrops" }, Math: fixedMath, performance: { now: () => 0 },
    hit(key) { const found = pressed.has(key); pressed.delete(key); return found; }, rnd(a) { calls.rng++; return a; },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), passTime() {}, meet() {}, cue() {}, sfx() {}, toast() {},
    saveGame() { calls.storage++; throw new Error("viewing plans must not save"); }, localStorage: { getItem() { calls.storage++; throw new Error("storage read"); }, setItem() { calls.storage++; throw new Error("storage write"); } },
    spr() {}, gauge() {}, win() {}, cursor: (x, y) => cursors.push({ x, y }), tw: value => String(value).length * 6,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", fillRect() {}, drawImage() {} }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  c.api.startBattle("plains", null, formation.enemies); c.fadeCb();
  const resources = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold, state: { ...c.state, beaten: [...c.state.beaten] } });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, battle: c.B, map: c.map, mode: c.mode, fade: c.fade, calls });
  const s = { c, paints, cursors, pressed, calls, resources,
    tick(...keys) { keys.forEach(k => pressed.add(k)); c.api.battleTick(0); },
    draw() { paints.length = 0; cursors.length = 0; const before = snapshot(); c.api.drawBattle(); assert.equal(snapshot(), before, "painting changed resources, acts, queue, RNG or storage"); return paints; }
  }; s.tick("a"); assert.equal(c.B.phase, "cmd"); return s;
}
function command(s, name) {
  assert.equal(s.c.B.phase, "cmd"); assert.equal(s.c.B.sub, null); const cmds = Array.from(s.c.api.battleCmds()), wanted = cmds.indexOf(name); assert.ok(wanted >= 0, name);
  for (let i = 0; s.c.B.cmd !== wanted && i < cmds.length; i++) s.tick("down"); assert.equal(s.c.B.cmd, wanted); s.tick("a");
}
function attack(s, target = 0) { command(s, "ATTACK"); for (let i = 0; i < target; i++) s.tick("right"); const who = s.c.B.list[s.c.B.target]; s.tick("a"); return who; }
function magic(s, name, target = 0) {
  command(s, "MAGIC"); const options = s.c.party[s.c.B.who].spells.map(s.c.api.spellOf).filter(Boolean), n = options.findIndex(sp => sp.name === name); assert.ok(n >= 0, name);
  for (let i = 0; i < n; i++) s.tick("down"); s.tick("a");
  if (s.c.B.sub === "target") { for (let i = 0; i < target; i++) s.tick("right"); s.tick("a"); }
}
function item(s, name, target = 0) {
  command(s, "ITEM"); const n = Array.from(s.c.api.battleItems()).indexOf(name); assert.ok(n >= 0, name);
  for (let i = 0; i < n; i++) s.tick("down"); s.tick("a");
  if (s.c.B.sub === "target") { for (let i = 0; i < target; i++) s.tick("right"); s.tick("a"); }
}
function openPlan(s) {
  const who = s.c.B.who, acts = Array.from(s.c.B.acts), queue = s.c.B.queue, before = s.resources(), rng = s.calls.rng;
  command(s, "PLAN"); assert.equal(s.c.B.sub, "plan"); assert.equal(s.c.B.who, who); assert.equal(s.c.B.queue, queue); assert.equal(s.resources(), before); assert.equal(s.calls.rng, rng);
  assert.equal(s.c.B.acts.length, acts.length); acts.forEach((act, i) => assert.equal(s.c.B.acts[i], act)); s.draw(); assert.ok(s.paints.some(p => p.label === "TURN PLAN"));
  assert.ok(s.paints.some(p => p.label === "CHOICE ORDER / " + acts.length + " PLANNED")); return acts;
}
function closePlan(s, ...keys) { s.tick(...(keys.length ? keys : ["a"])); assert.equal(s.c.B.sub, null); }
function planBounds(s) {
  assert.ok(s.paints.every(p => p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W - 12 && p.y + p.h <= 224), "plan text fits canvas margins");
  assert.ok(s.paints.every(p => [...p.label].every(ch => s.c.api.chars.includes(ch))), "plan font supports all text");
  assert.ok(s.paints.some(p => p.label === "CHOICE ORDER. TURN ORDER MAY DIFFER."));
  assert.ok(s.paints.some(p => p.label === "CLOSE, THEN BACK TO UNDO ONE."));
}
function row(s, index, actor, action, target) {
  const y = 50 + index * 40, label = at => s.paints.find(p => p.x === 12 && p.y === at).label;
  assert.equal(label(y), (index + 1) + ". " + actor.toUpperCase()); assert.equal(label(y + 12), action.toUpperCase()); assert.equal(label(y + 24), target.toUpperCase());
}
const base = ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN"];
for (const width of [320, 256]) check("original indices, six/seven-command scrolling and wrap at " + width, () => {
  for (const unlocked of [false, true]) { const s = session(width, unlocked), cmds = Array.from(s.c.api.battleCmds());
    assert.deepEqual(cmds.slice(0, 5), base); assert.deepEqual(cmds.slice(5), unlocked ? ["SUMMON", "PLAN"] : ["PLAN"]);
    for (let index = 0; index < cmds.length; index++) { assert.equal(s.c.B.cmd, index); s.draw();
      const choices = s.paints.filter(p => p.x === 22 && p.y >= 152), first = Math.max(0, index - 5);
      assert.deepEqual(choices.map(p => p.label), cmds.slice(first, first + 6)); assert.ok(choices.every(p => p.y >= 152 && p.y + 8 <= 220));
      assert.equal(s.cursors.length, 1); assert.equal(s.cursors[0].y, 152 + (index - first) * 12);
      if (unlocked) assert.ok(s.paints.some(p => p.x === 86 && p.y === 166 && p.label === (index + 1) + "/7")); s.tick("down"); }
    assert.equal(s.c.B.cmd, 0); s.tick("up"); assert.equal(s.c.B.cmd, cmds.length - 1); s.draw(); assert.equal(s.cursors[0].y, 212);
  }
});
for (const width of [320, 256]) check("zero through three real plans at " + width + ": exact actors, duplicate foe/ally targets and undo", () => {
  const s = session(width), before = s.resources(); openPlan(s); assert.ok(s.paints.some(p => p.label === "NO CHOICES YET.")); planBounds(s); closePlan(s);
  const foe = attack(s, 1); assert.equal(foe, s.c.B.foes[1]); assert.equal(foe.name, s.c.B.foes[0].name); openPlan(s);
  row(s, 0, s.c.party[0].name, "ATTACK", "TO " + foe.name + " / FOE 2"); closePlan(s);
  magic(s, "Mend", 3); const ally = s.c.party[3]; assert.equal(s.c.B.acts[1].target, ally); openPlan(s);
  row(s, 1, s.c.party[1].name, "MEND " + s.c.api.spellOf("Mend").mp + "MP", "TO " + ally.name + " / ALLY 4"); closePlan(s);
  item(s, "Herb Tonic", 0); const acts = openPlan(s); assert.equal(acts.length, 3); assert.equal(acts[2].target, s.c.party[0]);
  row(s, 2, s.c.party[2].name, "HERB TONIC", "TO " + s.c.party[0].name + " / ALLY 1"); planBounds(s); assert.equal(s.resources(), before); assert.equal(s.calls.rng, 0); assert.equal(s.calls.storage, 0);
  closePlan(s, "b", "a", "start", "left", "right", "up", "down"); assert.ok(["a", "b", "start", "left", "right", "up", "down"].every(k => !s.pressed.has(k)));
  assert.equal(s.c.B.who, 3); assert.equal(s.c.B.acts.length, 3); s.tick(); assert.equal(s.c.B.sub, null); assert.equal(s.c.B.acts.length, 3);
  s.tick("b"); assert.equal(s.c.B.who, 2); assert.equal(s.c.B.acts.length, 2); assert.equal(s.c.api.battleItemStock("Herb Tonic"), 2); assert.equal(s.resources(), before);
});
check("actual defend, run and Smoke Pouch plans are SELF or attempts, with no execution or spending", () => {
  const s = session(256), before = s.resources(); command(s, "DEFEND"); command(s, "RUN"); item(s, "Smoke Pouch");
  openPlan(s); row(s, 0, s.c.party[0].name, "DEFEND", "SELF"); row(s, 1, s.c.party[1].name, "RUN", "ESCAPE ATTEMPT"); row(s, 2, s.c.party[2].name, "SMOKE POUCH", "ESCAPE ATTEMPT");
  assert.equal(s.c.B.acts[2].target, null); assert.equal(s.c.party[0].defend, false); assert.equal(s.c.B.queue, undefined); assert.equal(s.resources(), before); planBounds(s);
});
check("actual unlocked summon and canonical all-foe magic retain chosen spirit/spell references and costs", () => {
  const s = session(256, true), caster = s.c.party[2], spell = s.c.api.spellOf("Tremor"); caster.spells.push(spell.name); // Already-learned canonical lesson fixture.
  const before = s.resources(); command(s, "DEFEND"); const spirits = s.c.api.mySpirits(); assert.ok(spirits.length); command(s, "SUMMON"); s.tick("a");
  const summon = s.c.B.acts[1]; assert.equal(summon.spirit.name, spirits[0].name); assert.equal(summon.target, "all"); magic(s, spell.name); assert.equal(s.c.B.acts[2].spell, spell);
  openPlan(s); row(s, 1, s.c.party[1].name, summon.spirit.name + " " + summon.spirit.mp + "MP", "ALL FOES");
  row(s, 2, caster.name, spell.name + " " + spell.mp + "MP", "ALL FOES"); assert.equal(s.resources(), before); assert.equal(s.c.B.summoned, undefined); assert.equal(s.calls.rng, 0); planBounds(s);
});
function closeEdges(production = source) {
  for (const keys of [["a"], ["b"], ["start"], ["b", "a", "start", "up", "down", "left", "right"]]) {
    const s = session(256, false, production); attack(s); openPlan(s); const cmd = s.c.B.cmd, before = s.resources();
    s.tick("up", "down", "left", "right"); assert.equal(s.c.B.sub, "plan"); assert.equal(s.c.B.cmd, cmd);
    closePlan(s, ...keys); assert.ok(["a", "b", "start", "up", "down", "left", "right"].every(k => !s.pressed.has(k)));
    s.tick(); assert.equal(s.c.B.sub, null); assert.equal(s.c.B.who, 1); assert.equal(s.c.B.acts.length, 1); assert.equal(s.resources(), before);
    s.tick("b"); assert.equal(s.c.B.who, 0); assert.equal(s.c.B.acts.length, 0); assert.equal(s.resources(), before);
  }
}
check("all close buttons drain concurrent edges; only fresh command Back undoes a plan", () => { closeEdges(); });
for (const width of [320, 256]) check("long actor/target names, mapped eight-character buttons and privacy fit at " + width, () => {
  const s = session(width); s.c.party.forEach(m => { m.name = "ß".repeat(64); }); const target = s.c.B.foes[1]; target.name = "ß".repeat(64); target.hp = target.max = 730319; target.atk = 730321;
  attack(s, 1); s.c.PAD = { devices: () => [{ index: 4 }], label(action, index) { assert.equal(index, 4); return action === "confirm" ? "ABCDEFGH" : "12345678"; } };
  const before = s.resources(); openPlan(s); planBounds(s); const actor = s.paints.find(p => p.y === 50), recipient = s.paints.find(p => p.y === 74), footer = s.paints.find(p => p.y === 212);
  assert.ok(actor.label.endsWith("...")); assert.ok(recipient.label.endsWith(" / FOE 2")); assert.ok(recipient.label.includes("..."));
  assert.equal(footer.label, "ABCDEFGH: CLOSE  12345678: CLOSE"); assert.ok(s.paints.every(p => !/730319|730321|\bHP\b|\bATK\b|\bDEF\b/.test(p.label)));
  assert.equal(target.name, "ß".repeat(64)); assert.equal(s.resources(), before);
});
check("PLAN never queues or rolls; final chooser still builds the original initiative queue once", () => {
  const s = session(); command(s, "DEFEND"); command(s, "DEFEND"); command(s, "DEFEND"); const before = s.resources(), refs = s.c.B.acts.slice();
  openPlan(s); assert.equal(s.c.B.queue, undefined); assert.equal(s.calls.rng, 0); closePlan(s); const target = attack(s, 2);
  assert.equal(s.c.B.phase, "act"); assert.equal(s.c.B.acts.length, 4); assert.equal(s.c.B.acts[3].target, target); refs.push(s.c.B.acts[3]);
  for (const act of refs) assert.equal(s.c.B.queue.filter(q => q === act).length, 1); assert.equal(s.c.B.queue.length, 4 + s.c.B.foes.length); assert.ok(s.calls.rng > 0);
  assert.equal(s.resources(), before); s.draw(); assert.equal(s.paints.some(p => p.label === "TURN PLAN"), false); assert.equal(s.calls.storage, 0);
});
check("Portal keeps its original command array identity, five-row placement and no PLAN entry", () => {
  const s = session(256, true); s.c.D.realm_key = "portal"; assert.equal(s.c.api.battleCmds(), s.c.api.commands); assert.deepEqual(Array.from(s.c.api.battleCmds()), base);
  // Realm-guard compatibility on this canonical Prism battle setup; no claim of Portal encounter projection.
  s.draw(); const rows = s.paints.filter(p => p.x === 22 && p.y >= 152); assert.deepEqual(rows.map(p => p.label), base); assert.deepEqual(rows.map(p => p.y), [152, 165, 178, 191, 204]);
  assert.equal(s.paints.some(p => p.label === "PLAN" || p.label === "TURN PLAN"), false); assert.equal(s.paints.some(p => p.x === 86 && p.y === 166), false);
});
check("controlled missing command, accidental advance and short-circuit close variants fail the same invariants", () => {
  const absent = source.replace(line("const battleCmds ="), 'const battleCmds = () => mySpirits().length ? CMDS.concat(["SUMMON"]) : CMDS;'); assert.notEqual(absent, source);
  assert.throws(() => openPlan(session(256, false, absent)), assert.AssertionError);
  const advance = source.replace('else if (c === "PLAN") { B.sub = "plan"; }', 'else if (c === "PLAN") { B.sub = "plan"; advanceChooser(); }'); assert.notEqual(advance, source);
  assert.throws(() => openPlan(session(256, false, advance)), assert.AssertionError);
  const leaked = source.replace('const back = hit("b"), confirm = hit("a"), start = hit("start");', 'const back = hit("b"), confirm = back || hit("a"), start = hit("start");'); assert.notEqual(leaked, source);
  assert.throws(() => closeEdges(leaked), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("battle plan: " + checks + " focused groups passed; actual chooser/painter capture only, no action/assets/browser/native acceptance");
