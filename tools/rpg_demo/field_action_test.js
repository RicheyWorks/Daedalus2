// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/field_action_test.js
// Actual field-menu actions, member factory, item/status helpers and catalogs; no browser or game loop.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const partyData = data("party").party.prism, spells = data("spells").spells.filter(s => s.realm === "prism"), gear = {};
for (const shop of Object.values(data("interiors").interiors.prism))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end, text = html) {
  const a = text.indexOf(start), b = text.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return text.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found;
}
const source = [line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), line("const spellOf ="),
  between("let menu = null;", "/* Four rows"), between("const STATUS =", "/* ---------- bestiary"),
  "this.api = { start: () => { party = buildParty(); }, makeMember, openMenu, menuTick, fieldItems, fieldSpells, " +
  "party: () => party, reserve: () => reserve, bag: () => bag, menu: () => menu };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(productionSource = source) {
  const sounds = [], pressed = {}, c = {
    D: { party: clone(partyData), gear: clone(gear), spells: clone(spells) }, pressed,
    mode: "field", map: { kind: "town" }, B: null, fade: 0, fadeCb: null,
    sfx: sound => sounds.push(sound), clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)),
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start(); c.api.openMenu();
  c.api.party()[0].hp = 20;
  return { c, api: c.api, sounds, pressed,
    // Keep unconsumed edges between calls: a missing Confirm drain must fail the next-frame assertion.
    tick: (...keys) => { keys.forEach(k => { pressed[k] = true; }); c.api.menuTick(); } };
}
function prepare(sub, productionSource = source, picked = true) {
  const s = session(productionSource), m = s.api.menu();
  Object.assign(m, { sub, idx: sub === "item" ? 0 : sub === "order" ? 4 : 1,
    who: 1, target: 0, ii: 0, pick: sub === "order" && picked ? 0 : -1 });
  m.spell = s.c.D.spells.find(sp => sp.name === "Mend");
  if (sub === "item") m.ii = s.api.fieldItems().indexOf("Herb Tonic");
  if (sub === "order") m.ii = 1;
  s.sounds.length = 0; return s;
}
const resources = s => JSON.stringify({ party: s.api.party(), reserve: s.api.reserve(), bag: s.api.bag() });
function assertCancelled(sub, productionSource = source, picked = true, adjust = () => {}) {
  const s = prepare(sub, productionSource, picked), m = s.api.menu(); adjust(s);
  const before = resources(s), refs = s.api.party().slice(); s.tick("b", "a");
  const destination = sub === "magic-target" ? "magic" : sub === "magic" ? "magic-who" : sub === "order" && picked ? "order" : null;
  assert.equal(m.sub, destination, "Back follows the existing submenu destination");
  assert.equal(resources(s), before, "Back cannot use items/MP, heal, or change roster order");
  s.api.party().forEach((member, i) => assert.equal(member, refs[i], "companion identity/order preserved"));
  if (sub === "order") assert.equal(m.pick, -1, "Back clears an existing swap selection");
  assert.ok(s.sounds.every(sound => sound === "TICK"), "Back never confirms or produces action effects");
  assert.equal(s.pressed.a, false, "simultaneous Confirm consumed");
  s.tick(); assert.equal(m.sub, destination, "no stale Confirm changes the next frame's submenu");
  assert.equal(resources(s), before, "no delayed action on the next frame");
  if (sub === "order") assert.equal(m.pick, -1); return s;
}
for (const sub of ["item", "magic-who", "magic", "magic-target", "order"])
  check("Back plus Confirm cancels " + sub + " without an action or delayed input", () => assertCancelled(sub));
check("ORDER Back with no first selection exits instead of starting a swap", () => assertCancelled("order", source, false));
check("Back exits a caster with no spells before Confirm can refuse", () => assertCancelled("magic-who", source, true, s => { s.api.menu().who = 0; }));
check("Back exits an unaffordable spell before Confirm can refuse", () => assertCancelled("magic", source, true, s => { s.api.party()[1].mp = 0; }));
check("Back exits a battle-only spell before Confirm can refuse", () => assertCancelled("magic", source, true, s => { s.api.menu().who = 2; }));
check("Back cancels healing a fallen target without spending or refusal", () => assertCancelled("magic-target", source, true, s => { s.api.party()[0].hp = 0; }));
check("Back cancels an out-of-MP targeted spell", () => assertCancelled("magic-target", source, true, s => { s.api.party()[1].mp = 0; }));
check("Confirm alone still uses exactly one real healing item", () => {
  const s = prepare("item"), bag = s.api.bag(), target = s.api.party()[1]; target.hp = 1;
  const before = bag["Herb Tonic"]; s.tick("a");
  assert.equal(bag["Herb Tonic"], before - 1); assert.ok(target.hp > 1); assert.equal(s.api.menu().sub, "item");
  s.tick(); assert.equal(bag["Herb Tonic"], before - 1, "one press cannot consume twice");
});
check("the normal caster/spell/target chain still spends MP and heals", () => {
  const s = prepare("magic-who"), m = s.api.menu(), caster = s.api.party()[1], target = s.api.party()[0];
  s.tick("a"); assert.equal(m.sub, "magic"); s.tick("a"); assert.equal(m.sub, "magic-target");
  const hp = target.hp, mp = caster.mp, sp = m.spell; s.tick("a");
  assert.equal(caster.mp, mp - sp.mp); assert.equal(target.hp, Math.min(target.max, hp + Math.round(sp.power * 1.5 + caster.st.spr * 3)));
  s.tick(); assert.equal(caster.mp, mp - sp.mp, "one press cannot cast twice");
});
for (const reason of ["fallen", "out-of-MP"]) check("Confirm-only " + reason + " healing rules remain unchanged", () => {
  const s = prepare("magic-target"); if (reason === "fallen") s.api.party()[0].hp = 0; else s.api.party()[1].mp = 0;
  const before = resources(s); s.tick("a"); assert.equal(resources(s), before);
  assert.match(s.api.menu().msg, reason === "fallen" ? /TOO LATE/ : /NOT ENOUGH MP/); assert.equal(s.api.menu().sub, "magic-target");
});
check("two normal ORDER confirms still swap the selected companions", () => {
  const s = prepare("order", source, false), m = s.api.menu(), before = s.api.party().slice();
  m.ii = 0; s.tick("a"); assert.equal(m.pick, 0); m.ii = 1; s.tick("a");
  assert.equal(s.api.party()[0], before[1]); assert.equal(s.api.party()[1], before[0]);
  assert.equal(m.pick, -1); assert.equal(m.sub, "order");
});
check("Back alone preserves the established ORDER selection-cancel behavior", () => {
  const s = prepare("order"), before = resources(s); s.tick("b");
  assert.equal(s.api.menu().sub, "order"); assert.equal(s.api.menu().pick, -1); assert.equal(resources(s), before);
  s.tick("b"); assert.equal(s.api.menu().sub, null);
});
function assertDownCaster(sub, productionSource = source, stale = false, longName = false) {
  const s = prepare(stale ? "magic-who" : sub, productionSource), caster = s.api.party()[1], m = s.api.menu();
  if (stale) { s.tick("a"); s.tick("a"); assert.equal(m.sub, "magic-target"); }
  caster.hp = 0; if (longName) caster.name = "A very long saved companion name";
  const before = resources(s); s.sounds.length = 0; s.tick("a");
  assert.equal(resources(s), before, "downed caster cannot spend MP, use items or heal anyone");
  assert.equal(m.sub, sub, "downed caster stays at the current choice");
  assert.match(m.msg, / IS DOWN\. REVIVE FIRST\.$/); assert.ok(m.msg.length <= 34, "revival guidance fits one message row");
  assert.deepEqual(s.sounds, ["LOCKED"]); assert.equal(s.pressed.a, false);
  s.tick(); assert.equal(resources(s), before, "refused Confirm cannot cast on the next frame"); return s;
}
check("downed Ysolde cannot enter field spell selection", () => assertDownCaster("magic-who"));
check("a directly prepared target choice rechecks the downed caster", () => assertDownCaster("magic-target"));
check("a caster knocked out after target selection cannot finish the stale spell", () => assertDownCaster("magic-target", source, true));
check("downed-caster revival guidance stays visible for a long saved name", () => assertDownCaster("magic-who", source, false, true));
for (const sub of ["magic-who", "magic-target"])
  check("Back plus Confirm still cancels " + sub + " before a downed-caster refusal", () =>
    assertCancelled(sub, source, true, s => { s.api.party()[1].hp = 0; }));
check("an actual Feather revival restores ordinary field casting", () => {
  const s = assertDownCaster("magic-who"), m = s.api.menu(), caster = s.api.party()[1], bag = s.api.bag();
  const feathers = bag["Feather of Waking"], mp = caster.mp; assert.ok(feathers > 0);
  Object.assign(m, { sub: "item", who: 1, ii: s.api.fieldItems().indexOf("Feather of Waking") }); s.tick("a");
  assert.equal(caster.hp, Math.ceil(caster.max / 4)); assert.equal(bag["Feather of Waking"], feathers - 1);
  Object.assign(m, { sub: "magic-who", who: 1, ii: 0 }); s.tick("a"); s.tick("a"); assert.equal(m.sub, "magic-target");
  const target = s.api.party()[0], hp = target.hp; s.tick("a");
  assert.equal(caster.mp, mp - m.spell.mp); assert.ok(target.hp > hp); assert.equal(bag["Feather of Waking"], feathers - 1);
});
check("a living caster moved to reserve by ORDER can still heal", () => {
  const s = prepare("order"), m = s.api.menu(), caster = s.api.party()[1];
  s.api.reserve().push(s.api.makeMember(s.c.D.party.members.find(member => member.job === "Beastcaller"), 15));
  Object.assign(m, { pick: 1, ii: 4 }); s.tick("a"); assert.equal(s.api.reserve()[0], caster);
  Object.assign(m, { sub: "magic-who", who: 4, ii: 0 }); s.tick("a"); s.tick("a");
  assert.equal(m.sub, "magic-target"); const mp = caster.mp, hp = s.api.party()[0].hp; s.tick("a");
  assert.equal(caster.mp, mp - m.spell.mp); assert.ok(s.api.party()[0].hp > hp);
});
check("removing the actual two caster guards reproduces both old failures", () => {
  const pattern = /^      if \(caster\.hp <= 0\) \{[^\r\n]*\}\r?$/gm;
  assert.equal((source.match(pattern) || []).length, 2, "two production caster checks are covered");
  const legacy = source.replace(pattern, "");
  for (const sub of ["magic-who", "magic-target"])
    assert.throws(() => assertDownCaster(sub, legacy), assert.AssertionError);
});
function undoCancelPriority(sub) {
  const next = { item: '  if (sub === "magic-who")', "magic-who": '  if (sub === "magic")',
    magic: '  if (sub === "magic-target")', "magic-target": '  if (sub === "equip")', order: "function equipCandidates(" }[sub];
  const block = between('  if (sub === "' + sub + '") {', next, source);
  const guard = block.match(/^    if \(hit\("b"\)\) \{[^\r\n]*\}\r?$/m);
  assert.ok(guard && guard[0].includes('hit("a")') && guard[0].includes("return;"), "actual cancel-first guard exists: " + sub);
  const rest = block.replace(guard[0], ""), at = sub === "order" ? rest.lastIndexOf("\n  }") : rest.lastIndexOf("\n    return;");
  assert.ok(at >= 0);
  // Restore former order using the current production branch itself; no copied action implementation.
  const lateGuard = guard[0].replace('hit("a"); ', "").replace("return;", "");
  return source.replace(block, rest.slice(0, at) + "\n" + lateGuard + rest.slice(at));
}
for (const sub of ["item", "magic-who", "magic", "magic-target", "order"])
  check("controlled late-Back " + sub + " fails the same cancellation regression", () => {
    const legacy = undoCancelPriority(sub);
    assert.throws(() => assertCancelled(sub, legacy), assert.AssertionError);
  });
console.log("Prismheart field action checks: " + checks + " passed.");
