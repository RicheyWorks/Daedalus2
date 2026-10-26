// SPDX-License-Identifier: MIT
// Focused offline check: node --max-old-space-size=128 tools/rpg_demo/stolen_gold_recovery_test.js
// Actual formation selection, theft, attacks, poison, escape and victory functions with authored Prism catalogs.
// Deterministic in-range RNG is fixture-only. No browser, assets, storage, build or native work.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value)), partyData = data("party").party.prism;
const foes = data("prism-bestiary").types, encounters = data("prism-encounters").zones, allSpells = data("spells").spells;
const gear = {}, thiefKey = "prism_best_cutthroat", harpyKey = "prism_best_gale_harpy";
for (const realm of ["portal", "prism"]) for (const store of Object.values(data("interiors").interiors[realm]))
  for (const item of store.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
const pair = encounters.plains.formations.find(f => f.enemies.length === 2 && f.enemies.every(k => k === thiefKey));
const trio = encounters.plains.formations.find(f => f.enemies.length === 3 && f.enemies.filter(k => k === thiefKey).length === 2 && f.enemies.includes(harpyKey));
assert.ok(pair && trio, "the actual plains table offers two Cutthroats, with or without a Gale Harpy");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [between("const START_LEVEL =", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("function passTime(", "function wakeAt("), between("const ITEM_KINDS =", "function menuTick()"),
  between("function useItem(", "/* Four rows"), between("const STATUS =", "/* ---------- bestiary"),
  line("const beastKey ="), line("function meet("), line("function fell("), line("let B = null;"),
  between("function pickFormation(", "const ELEM ="), line("const ELEM ="), line("const CMDS ="),
  between("function nextChooser(", "function bossGate("),
  "this.api = { begin: () => { party = buildParty(); gold = 200; }, startBattle, doAction, foeTurn, hurtFoe, endRound, finishBattle, recoverStolenGold, " +
  "party: () => party, reserve: () => reserve, bag: () => bag, gold: () => gold, battle: () => B };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(formation = pair, productionSource = source) {
  const sounds = [], cues = [], fixedMath = Object.create(Math), known = new Set(partyData.members.flatMap(m => m.spells));
  const c = { D: { party: clone(partyData), gear: clone(gear), dungeons: [],
      spells: clone(allSpells.filter(s => s.realm === "prism" && (known.has(s.name) || s.tier <= 2))),
      foes: Object.fromEntries(foes.map(f => [f.key, clone(f)])), zones: clone(encounters), backdrop_for_zone: { plains: "plain" } },
    W: 320, map: { kind: "world", cue: "FIELD" }, mode: "field", fade: 0, fadeCb: null,
    state: { day: 1, minute: 480, sinceBattle: 0, seen: {}, beaten: new Set() }, Math: fixedMath, roll: 0.1,
    rnd: (a, b) => (a + b) / 2, ri: a => a, hit: () => false,
    sfx: sound => sounds.push(sound), cue: name => cues.push(name), toast() {}, playChord() {},
    localStorage: { setItem() { throw new Error("battle recovery must not save"); } } };
  fixedMath.random = () => c.roll;
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.begin();
  const total = encounters.plains.formations.reduce((sum, f) => sum + f.weight, 0), index = encounters.plains.formations.indexOf(formation);
  c.roll = (encounters.plains.formations.slice(0, index).reduce((sum, f) => sum + f.weight, 0) + formation.weight / 2) / total;
  c.api.startBattle("plains"); c.fadeCb(); c.fade = 0; c.roll = 0.1;
  assert.deepEqual(Array.from(c.api.battle().foes, f => f.key), formation.enemies, "actual weighted formation picker selects the authored encounter");
  c.api.battle().phase = "act";
  return { c, api: c.api, sounds, cues, thieves: c.api.battle().foes.filter(f => f.beh === "steal") };
}
const progress = s => JSON.stringify({ party: s.api.party().map(m => ({ lv: m.lv, exp: m.exp, next: m.next })), reserve: s.api.reserve() });
function steal(s, thief = s.thieves[0]) {
  const before = s.api.gold(), held = thief.stolen || 0; s.api.doAction({ kind: "foe", who: thief });
  const amount = before - s.api.gold(); assert.ok(amount > 0 && s.api.party()[0].hp > 0);
  assert.equal(thief.stolen, held + amount); assert.match(s.api.battle().msg, /SNATCHES .* GOLD/); return amount;
}
function kill(s, thief = s.thieves[0]) {
  s.api.doAction({ kind: "attack", who: s.api.party()[0], target: thief }); assert.equal(thief.hp, 0, "the real seasoned Bladeward fells a real Cutthroat");
}
function escape(s, kind) {
  const before = progress(s), gold = s.api.gold(), bag = s.api.bag(), count = bag["Smoke Pouch"] || 0;
  if (kind === "smoke") { bag["Smoke Pouch"] = 1; s.api.doAction({ kind: "item", who: s.api.party()[0], item: "Smoke Pouch", target: null }); assert.equal(bag["Smoke Pouch"], 0); }
  else s.api.doAction({ kind: "run", who: s.api.party()[0] });
  const battle = s.api.battle(); assert.equal(battle.result, "run"); assert.equal(battle.phase, "end");
  assert.equal(s.api.gold(), gold, "escaping grants no ordinary foe gold"); assert.equal(progress(s), before, "escaping grants no EXP or levels");
  if (kind !== "smoke") assert.equal(bag["Smoke Pouch"] || 0, count);
  s.api.finishBattle(); s.c.fadeCb(); assert.equal(s.api.battle(), null); assert.equal(s.c.mode, "field");
  assert.equal(s.api.gold(), gold); assert.equal(progress(s), before);
  assert.ok(Object.values(s.c.state.seen).every(entry => entry.felled === 0), "this gold fix does not add partial-battle kill counters");
}
for (const kind of ["run", "smoke"]) check("felled thief's gold remains recovered after actual " + kind + " escape", () => {
  const s = session(trio), amount = steal(s), before = progress(s); kill(s);
  assert.equal(s.api.gold(), 200); assert.equal(s.thieves[0].stolen, 0); assert.equal(s.api.battle().recoveredGold, amount);
  assert.equal(progress(s), before, "felling a thief grants no early EXP"); assert.ok(s.api.battle().foes.some(f => f.hp > 0)); escape(s, kind);
});
check("a living thief retains its held gold until it falls", () => {
  const s = session(trio), first = steal(s, s.thieves[0]), second = steal(s, s.thieves[1]); kill(s, s.thieves[0]);
  assert.equal(s.api.gold(), 200 - second); assert.equal(s.thieves[1].stolen, second); assert.equal(s.api.battle().recoveredGold, first);
  assert.equal(s.api.recoverStolenGold(), 0); escape(s, "run"); assert.equal(s.api.gold(), 200 - second);
});
check("repeated damage settlement and live rounds cannot refund the same ledger twice", () => {
  const s = session(trio), amount = steal(s); kill(s); const earned = progress(s);
  for (let i = 0; i < 3; i++) {
    assert.equal(s.api.recoverStolenGold(), 0); s.api.hurtFoe(s.thieves[0], 0); s.api.endRound();
    assert.equal(s.api.gold(), 200); assert.equal(s.api.battle().recoveredGold, amount); assert.equal(progress(s), earned);
  }
});
check("multiple thefts by one thief recover their actual accumulated amount once", () => {
  const s = session(), first = steal(s), second = steal(s); assert.equal(s.thieves[0].stolen, first + second);
  kill(s); assert.equal(s.api.gold(), 200); assert.equal(s.api.battle().recoveredGold, first + second); assert.equal(s.api.recoverStolenGold(), 0);
});
check("real poison spell and round damage return a fallen thief's gold before escape", () => {
  const s = session(trio), amount = steal(s), thief = s.thieves[0], caster = s.api.party()[2], spell = s.c.D.spells.find(sp => sp.name === "Blight");
  assert.ok(spell && spell.status === "poison" && caster.mp >= spell.mp); s.api.hurtFoe(thief, thief.hp - 1);
  s.api.doAction({ kind: "magic", who: caster, spell, target: thief }); assert.ok(thief.status.poison); assert.equal(thief.hp, 1);
  const before = progress(s); s.api.endRound(); assert.equal(thief.hp, 0); assert.equal(s.api.gold(), 200);
  assert.equal(s.api.battle().recoveredGold, amount); assert.equal(progress(s), before); escape(s, "smoke");
});
check("end-round fallback settles a direct HP-hook death with other foes alive", () => {
  const s = session(trio), amount = steal(s); s.thieves[0].hp = 0; s.api.endRound();
  assert.equal(s.api.gold(), 200); assert.equal(s.thieves[0].stolen, 0); assert.equal(s.api.battle().recoveredGold, amount);
  s.api.endRound(); assert.equal(s.api.gold(), 200); escape(s, "run");
});
for (const directHook of [false, true]) check("full victory retains normal gold, EXP and cumulative TAKE BACK message; hook=" + directHook, () => {
  const s = session(), first = steal(s, s.thieves[0]), second = steal(s, s.thieves[1]), b = s.api.battle();
  const gold = b.foes.reduce((sum, f) => sum + f.gold, 0), exp = b.foes.reduce((sum, f) => sum + f.exp, 0), initial = s.api.party().map(m => m.exp);
  if (directHook) b.foes.forEach(f => { f.hp = 0; }); else { kill(s, s.thieves[0]); kill(s, s.thieves[1]); assert.equal(s.api.gold(), 200, "ordinary kill rewards still wait for full victory"); }
  s.api.endRound(); assert.equal(s.api.gold(), 200 + gold); assert.equal(b.phase, "end"); assert.equal(b.result, "win");
  assert.equal(b.recoveredGold, first + second); assert.ok(b.foes.every(f => f.stolen === 0));
  assert.equal(b.msg, "VICTORY! " + exp + " EXP AND " + gold + " GOLD."); assert.ok(b.endLines.includes("YOU TAKE BACK " + (first + second) + " STOLEN GOLD."));
  s.api.party().forEach((m, i) => assert.equal(m.exp, initial[i] + exp)); const paid = s.api.gold();
  assert.equal(s.api.recoverStolenGold(), 0); assert.equal(s.api.gold(), paid); assert.equal(s.c.state.seen[thiefKey].felled, 2);
});
check("a no-theft victory keeps the ordinary rewards and has no recovery message", () => {
  const s = session(), b = s.api.battle(), gold = b.foes.reduce((sum, f) => sum + f.gold, 0), exp = b.foes.reduce((sum, f) => sum + f.exp, 0);
  kill(s, s.thieves[0]); kill(s, s.thieves[1]); assert.equal(s.api.gold(), 200); assert.equal(b.recoveredGold || 0, 0);
  s.api.endRound(); assert.equal(s.api.gold(), 200 + gold); assert.ok(!b.endLines.some(line => /TAKE BACK/.test(line)));
  s.api.party().forEach(m => assert.equal(m.exp, exp));
});
check("unchanged undead revival still resolves before final-death settlement", () => {
  const s = session(), raw = foes.find(f => f.behaviour === "undead"); assert.ok(raw);
  // This checks the generic damage helper's placement only: undead are not given invented theft behavior or held gold.
  const f = { key: raw.key, name: raw.name, hp: raw.hp, max: raw.hp, beh: raw.behaviour, x: 24, y: 26, size: 56 };
  s.api.battle().foes.push(f); s.api.hurtFoe(f, f.hp); assert.ok(f.hp > 0 && f.rose); assert.equal(s.api.gold(), 200);
  s.api.hurtFoe(f, f.hp); assert.equal(f.hp, 0); assert.equal(s.api.gold(), 200); assert.equal(s.api.battle().recoveredGold || 0, 0);
});
check("controlled missing death settlement reproduces the old kill-then-run loss", () => {
  const guard = "  if (f.hp <= 0) recoverStolenGold();"; assert.ok(source.includes(guard));
  const s = session(trio, source.replace(guard, "")); steal(s); kill(s);
  assert.throws(() => assert.equal(s.api.gold(), 200, "fallen-thief recovery must happen before RUN can end the battle"), assert.AssertionError);
  escape(s, "run"); assert.ok(s.api.gold() < 200, "the former path lost the defeated thief's held gold on escape");
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or a game loop.
console.log("Prismheart stolen gold recovery checks: " + checks + " passed; full inline script compiles.");
