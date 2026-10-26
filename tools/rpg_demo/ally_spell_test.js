// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/ally_spell_test.js
// Executes the production action/member/status/item functions with the real Prismheart catalogs.
// No browser, game loop, storage, build output or production data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const members = data("party").party.prism.members;
const spells = data("spells").spells.filter(s => s.realm === "prism");
const gear = {};
for (const shop of Object.values(data("interiors").interiors.prism))
  for (const item of shop.stock || []) if (item.effect) gear[item.name] = item;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
const source = [
  between("function makeMember(", "/* Recruits:"),
  between("const ITEM_KINDS =", "function menuTick()"),
  between("function useItem(", "/* Four rows"),
  between("const STATUS =", "function roundStatuses()"),
  between("function pop(", "/* Foe turns by"),
  "this.api = { makeMember, doAction, useItem };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(productionSource = source) {
  const sounds = [], c = {
    D: {}, START_LEVEL: 15, W: 320, party: [], reserve: [], bag: {}, GEAR: gear,
    map: { kind: "town" }, roster: () => c.party.concat(c.reserve), alive: list => list.filter(m => m.hp > 0),
    sfx: sound => sounds.push(sound), rnd: (a, b) => (a + b) / 2,
    B: { wait: 0, msg: "", fx: null, queue: [], pops: [], flash: {}, foes: [
      { name: "First foe", key: "first", hp: 500, max: 500, def: 10, beh: "simple", x: 0, y: 0, size: 56 },
      { name: "Second foe", key: "second", hp: 500, max: 500, def: 10, beh: "simple", x: 64, y: 0, size: 56 }
    ] }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = ["Lightmender", "Bladeward"].map(job => c.api.makeMember(members.find(m => m.job === job), 15));
  c.party[1].hp = 20;
  return { c, sounds, caster: c.party[0], ally: c.party[1], spell: name => spells.find(s => s.name === name) };
}
const action = (s, name, target = s.ally) => ({ kind: "magic", who: s.caster, spell: s.spell(name), target });
const resources = (s, target) => JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag, target });
function noEffects(s, target, before) {
  assert.equal(resources(s, target), before, "target, party, MP, foes and bag remain unchanged");
  assert.equal(s.c.B.fx, null, "no spell animation starts");
  assert.equal(s.c.B.pops.length, 0, "no heal or status effects appear");
  assert.equal(s.sounds.includes("SPELL"), false, "no casting sound");
}
function refused(s, target, before) {
  noEffects(s, target, before);
  assert.match(s.c.B.msg, /IS DOWN|NO LONGER HERE/, "refusal explains the unavailable target");
  assert.match(s.c.B.msg, /IS NOT CAST/, "refusal makes clear that the spell was not spent");
  assert.doesNotMatch(s.c.B.msg, / CASTS /, "refusal does not claim a successful spell");
}

check("the actual spell catalog has no revival spells", () => {
  assert.equal(spells.some(s => /revive/.test((s.status || "") + (s.effect || ""))), false);
  assert.equal(spells.find(s => s.name === "Mend").mp, 5);
});
for (const name of ["Mend", "Ward"]) for (const kind of ["fallen", "missing", "detached", "enemy", "all"]) {
  check(name + " refuses a " + kind + " ally before MP or effects", () => {
    const s = session();
    if (kind === "fallen") s.ally.hp = 0; // Selected while standing, then knocked out earlier in the round.
    const target = kind === "missing" ? null : kind === "detached" ? { ...s.ally } : kind === "enemy" ? s.c.B.foes[0] : kind === "all" ? "all" : s.ally;
    const before = resources(s, target); s.c.api.doAction(action(s, name, target)); refused(s, target, before);
  });
}
check("ordinary living-target Mend still heals and spends its actual MP cost", () => {
  const s = session(), sp = s.spell("Mend"), hp = s.ally.hp, mp = s.caster.mp;
  s.c.api.doAction(action(s, "Mend"));
  assert.equal(s.ally.hp, Math.min(s.ally.max, hp + Math.round(sp.power * 1.5 + s.caster.st.spr * 3)));
  assert.equal(s.caster.mp, mp - sp.mp); assert.equal(s.c.B.fx.targets[0], s.ally);
});
check("ordinary living-target Ward still applies protection and spends MP", () => {
  const s = session(), mp = s.caster.mp; s.c.api.doAction(action(s, "Ward"));
  assert.equal(s.ally.status.protect, 4); assert.equal(s.caster.mp, mp - s.spell("Ward").mp);
  assert.equal(s.c.B.fx.targets[0], s.ally);
});
check("insufficient MP still refuses without target or resource changes", () => {
  const s = session(); s.caster.mp = 0; const before = resources(s, s.ally);
  s.c.api.doAction(action(s, "Mend")); noEffects(s, s.ally, before); assert.match(s.c.B.msg, /OUT OF MP/);
});
check("a downed caster remains unable to act", () => {
  const s = session(); s.caster.hp = 0; const before = resources(s, s.ally);
  s.c.api.doAction(action(s, "Mend")); noEffects(s, s.ally, before); assert.equal(s.c.B.wait, 0);
});
check("single-target offensive magic still retargets a defeated foe", () => {
  const s = session(), foes = s.c.B.foes, mp = s.caster.mp; foes[0].hp = 0;
  s.c.api.doAction(action(s, "Ember", foes[0]));
  assert.equal(foes[0].hp, 0); assert.ok(foes[1].hp < 500);
  assert.equal(s.caster.mp, mp - s.spell("Ember").mp); assert.equal(s.c.B.fx.targets[0], foes[1]);
});
check("all-enemy magic still affects each standing foe", () => {
  const s = session(), mp = s.caster.mp; s.c.api.doAction(action(s, "Glint", "all"));
  assert.ok(s.c.B.foes.every(f => f.hp < 500)); assert.equal(s.c.B.fx.targets.length, 2);
  assert.equal(s.caster.mp, mp - s.spell("Glint").mp);
});
check("the dedicated revival item still raises a fallen ally", () => {
  const s = session(); s.ally.hp = 0; s.c.bag["Feather of Waking"] = 1;
  s.c.api.doAction({ kind: "item", who: s.caster, item: "Feather of Waking", target: s.ally });
  assert.equal(s.ally.hp, Math.ceil(s.ally.max / 4)); assert.equal(s.c.bag["Feather of Waking"], 0);
});
check("removing the execution guard reproduces the former unintended revival", () => {
  const from = source.indexOf('    if (s.target === "ally" &&'), to = source.indexOf('    who.mp -= s.mp;', from);
  assert.ok(from >= 0 && to > from, "the production execution guard exists before MP consumption");
  const oldSource = source.slice(0, from) + source.slice(to);
  const s = session(oldSource); s.ally.hp = 0; const before = resources(s, s.ally);
  s.c.api.doAction(action(s, "Mend"));
  assert.ok(s.ally.hp > 0, "historical expression reproduces unintended revival");
  assert.throws(() => noEffects(s, s.ally, before), assert.AssertionError, "regression assertion detects the former bug");
});
console.log("Prismheart ally spell checks: " + checks + " passed.");
