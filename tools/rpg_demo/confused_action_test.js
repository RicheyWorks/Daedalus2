// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/confused_action_test.js
// Actual Prismheart initiative/action/status/foe functions and catalogs. No browser,
// game loop, storage, build output, assets or native/shared-host code is executed.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const partyData = data("party").party.prism, spells = data("spells").spells.filter(s => s.realm === "prism");
const harpy = data("prism-bestiary").types.find(f => f.key === "prism_best_gale_harpy"), gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = ['"use strict";', between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "function menuTick()"), between("function useItem(", "/* Four rows"),
  between("const STATUS =", "/* ---------- bestiary"), line("function nextChooser("),
  between("function advanceChooser(", "function endRound()"),
  "this.api = { makeMember, doAction, foeTurn, advanceChooser, nextChooser, roundStatuses, cure, inflict, landHit, spdOf };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(productionSource = source) {
  const sounds = [], selections = [], fixedMath = Object.create(Math);
  const c = { D: { party: clone(partyData), spells: clone(spells) }, START_LEVEL: 15, ACTIVE: 4, W: 320,
    party: [], reserve: [], GEAR: clone(gear), bag: { "Herb Tonic": 2, "Feather of Waking": 1 }, gold: 100,
    map: { kind: "town" }, Math: fixedMath, targetIndex: 0, initiative: false, speedCalls: 0,
    // sort compares spdOf(b) then spdOf(a). These in-range rolls let this real Harpy
    // precede the real AGI-19 caster, while the other hero's Defend still goes first.
    rnd: (min, max) => min === 0 && max === 6 && c.initiative ? (++c.speedCalls % 2 ? 0.5 : 5.5) : (min + max) / 2,
    ri: (min, max) => { selections.push([min, max]); return c.targetIndex === "last" ? max : c.targetIndex; },
    roster: () => c.party.concat(c.reserve), sfx: sound => sounds.push(sound),
    B: { phase: "cmd", who: 1, acts: [], queue: [], round: 1, turn: 0, t: 0, wait: 0, msg: "", fx: null, pops: [], flash: {},
      foes: [{ key: harpy.key, name: harpy.name, hp: harpy.hp, max: harpy.hp, atk: harpy.attack,
        def: harpy.defence, spd: harpy.speed, beh: harpy.behaviour, x: 24, y: 26, size: 56 }] } };
  fixedMath.random = () => 0.1; // Real hit (>= .06), real status infliction (< .3), no ordinary attack miss/critical.
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = ["Lightmender", "Bladeward"].map(job => c.api.makeMember(partyData.members.find(m => m.job === job), 15));
  c.party[1].hp -= 80;
  return { c, sounds, selections, actor: c.party[0], ally: c.party[1], foe: c.B.foes[0], spell: name => spells.find(s => s.name === name) };
}
function action(s, kind) {
  if (kind === "magic") return Object.freeze({ kind, who: s.actor, spell: s.spell("Mend"), target: s.ally });
  if (kind === "item") return Object.freeze({ kind, who: s.actor, item: "Herb Tonic", target: s.ally });
  return Object.freeze({ kind, who: s.actor, target: s.foe });
}
function inflictedBeforeQueued(kind, productionSource = source) {
  const s = session(productionSource), planned = action(s, kind);
  assert.equal(s.actor.st.agi, 19); assert.equal(s.foe.spd, 15);
  if (kind === "magic") assert.ok(s.actor.spells.includes(planned.spell.name), "the real caster knows the queued heal");
  s.c.B.acts = [planned, { kind: "defend", who: s.ally }];
  s.c.initiative = true; s.c.api.advanceChooser(); s.c.initiative = false;
  const foeIndex = s.c.B.queue.findIndex(a => a.kind === "foe"), actorIndex = s.c.B.queue.indexOf(planned);
  assert.ok(foeIndex >= 0 && actorIndex > foeIndex, "real initiative queue puts the Harpy ahead of the actor");
  assert.equal(Object.hasOwn(planned, "confused"), false, "the hero selected this before confusion");
  while (s.c.B.queue[0] !== planned) s.c.api.doAction(s.c.B.queue.shift());
  assert.ok(s.actor.hp > 0 && s.actor.status.confuse === 3, "real Harpy foeTurn inflicts Confuse before the planned action");
  assert.equal(s.c.api.nextChooser(0), 1, "the existing next-round chooser also recognizes Confuse");
  s.sounds.length = 0; s.c.B.pops.length = 0; s.selections.length = 0; return { ...s, planned };
}
function assertSwing(s, destination = "friend") {
  const mp = s.actor.mp, bag = JSON.stringify(s.c.bag), ownHp = s.actor.hp, allyHp = s.ally.hp, foeHp = s.foe.hp;
  const keys = Object.keys(s.planned), kind = s.planned.kind, target = s.planned.target;
  s.c.targetIndex = destination === "friend" ? 0 : "last"; s.c.api.doAction(s.planned);
  assert.match(s.c.B.msg, /IS CONFUSED AND HITS/, "newly confused actor uses the established swing branch");
  assert.equal(s.actor.hp, ownHp, "a confused swing never targets its own actor");
  assert.equal(s.actor.mp, mp, "a replaced planned spell spends no MP");
  assert.equal(JSON.stringify(s.c.bag), bag, "a replaced planned item spends no stock");
  assert.equal(s.c.B.fx, null, "no planned spell animation starts");
  assert.equal(s.actor.status.confuse, 3, "swing conversion does not renew or consume status duration");
  assert.ok(s.sounds.includes("SWING")); assert.equal(s.sounds.includes("SPELL"), false); assert.equal(s.sounds.includes("ITEM"), false);
  if (destination === "friend") { assert.ok(s.ally.hp < allyHp); assert.equal(s.foe.hp, foeHp); }
  else { assert.ok(s.foe.hp < foeHp); assert.equal(s.ally.hp, allyHp); }
  assert.deepEqual(Object.keys(s.planned), keys); assert.equal(s.planned.kind, kind); assert.equal(s.planned.target, target);
  assert.equal(Object.hasOwn(s.planned, "confused"), false, "the original queued action object is not rewritten");
}
check("this Confuse foe is authored in the actual shipped shard-quest route", () => {
  assert.equal(harpy.behaviour, "status_confuse"); assert.equal(harpy.speed, 15);
  const dungeon = data("dungeons").dungeons.prism.find(d => d.name === "Windcut Aerie");
  assert.equal(dungeon.floors[0].encounters.zone, "mountain");
  const formation = data("prism-encounters").zones.mountain.formations.find(f => f.enemies.includes(harpy.key));
  assert.ok(formation && formation.weight > 0, "positive-weight reachable quest formation includes Gale Harpy");
});
check("complete production inline script compiles without executing the game", () => {
  const script = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(script);
  new vm.Script(script[1], { filename: "index.html inline script" });
});
for (const kind of ["magic", "item", "attack"]) for (const target of ["friend", "foe"])
  check("same-round Confuse replaces planned " + kind + " with an ordinary confused swing at a " + target, () => assertSwing(inflictedBeforeQueued(kind), target));
check("confused targeting excludes the actor and downed members/foes", () => {
  for (const destination of ["friend", "foe"]) {
    const s = inflictedBeforeQueued("magic"), fallen = s.c.api.makeMember(partyData.members.find(m => m.job === "Shadowstep"), 15);
    fallen.hp = 0; s.c.party.push(fallen);
    const deadFoe = { ...s.foe, key: "already fallen foe", hp: 0 }; s.c.B.foes.push(deadFoe);
    assertSwing(s, destination); assert.deepEqual(s.selections, [[0, 1]], "only the one living friend and one living foe are offered");
    assert.equal(fallen.hp, 0); assert.equal(deadFoe.hp, 0);
  }
});
for (const kind of ["magic", "item", "attack"]) check("a blow that clears Confuse before queued " + kind + " restores its original action", () => {
  const s = inflictedBeforeQueued(kind), mp = s.actor.mp, stock = s.c.bag["Herb Tonic"], hp = s.ally.hp, foeHp = s.foe.hp;
  s.c.api.landHit(s.actor, 1); assert.equal(s.actor.status.confuse, undefined);
  s.c.api.doAction(s.planned); assert.doesNotMatch(s.c.B.msg, /IS CONFUSED/);
  if (kind === "magic") { assert.equal(s.actor.mp, mp - s.planned.spell.mp); assert.ok(s.ally.hp > hp); }
  else if (kind === "item") { assert.equal(s.c.bag["Herb Tonic"], stock - 1); assert.ok(s.ally.hp > hp); }
  else assert.ok(s.foe.hp < foeHp);
});
check("an initially confused actor keeps the existing queued confused action", () => {
  const s = session(); s.c.api.inflict(s.actor, "confuse");
  s.c.B.acts = [{ kind: "defend", who: s.ally }]; s.c.api.advanceChooser();
  const planned = s.c.B.queue.find(a => a.who === s.actor);
  assert.ok(planned && planned.confused && planned.kind === "attack");
  const hp = s.ally.hp, mp = s.actor.mp; s.c.targetIndex = 0; s.c.api.doAction(planned);
  assert.match(s.c.B.msg, /IS CONFUSED AND HITS/); assert.ok(s.ally.hp < hp); assert.equal(s.actor.mp, mp);
});
check("curing an initially confused automatic action still skips that old action", () => {
  const s = session(); s.c.api.inflict(s.actor, "confuse"); s.c.B.acts = [{ kind: "defend", who: s.ally }]; s.c.api.advanceChooser();
  const planned = s.c.B.queue.find(a => a.who === s.actor); assert.ok(planned.confused);
  s.c.api.cure(s.actor, "confuse");
  const before = JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }); s.c.api.doAction(planned);
  assert.equal(JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }), before); assert.equal(s.c.B.wait, 0);
});
for (const held of ["sleep", "bind", "paralyze"]) check(held + " retains priority over a newly confused actor", () => {
  const s = inflictedBeforeQueued("magic"); s.c.api.inflict(s.actor, held);
  const before = JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }); s.sounds.length = 0;
  s.c.api.doAction(s.planned);
  assert.equal(JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }), before); assert.equal(s.c.B.wait, 0.45);
  assert.match(s.c.B.msg, /IS ASLEEP|IS BOUND|IS PARALYZED/); assert.equal(s.sounds.includes("SWING"), false);
});
check("a downed confused actor still cannot act", () => {
  const s = inflictedBeforeQueued("item"); s.actor.hp = 0;
  const before = JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }); s.c.api.doAction(s.planned);
  assert.equal(JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag }), before); assert.equal(s.c.B.wait, 0);
});
check("Confuse duration and hit recovery keep their established rules", () => {
  const s = inflictedBeforeQueued("magic"); assertSwing(s); s.c.api.roundStatuses(); assert.equal(s.actor.status.confuse, 2);
  s.c.api.roundStatuses(); s.c.api.roundStatuses(); assert.equal(s.actor.status.confuse, undefined);
  s.c.api.inflict(s.actor, "confuse"); s.c.api.landHit(s.actor, 1); assert.equal(s.actor.status.confuse, undefined);
});
for (const kind of ["magic", "item", "attack"]) check("an ordinary unconfused " + kind + " still performs its selected action", () => {
  const s = session(), planned = action(s, kind), mp = s.actor.mp, stock = s.c.bag["Herb Tonic"], hp = s.ally.hp, foeHp = s.foe.hp;
  s.c.api.doAction(planned); assert.doesNotMatch(s.c.B.msg, /IS CONFUSED/);
  if (kind === "magic") { assert.equal(s.actor.mp, mp - planned.spell.mp); assert.ok(s.ally.hp > hp); }
  else if (kind === "item") { assert.equal(s.c.bag["Herb Tonic"], stock - 1); assert.ok(s.ally.hp > hp); }
  else assert.ok(s.foe.hp < foeHp);
});
check("removing the actual conversion reproduces all three formerly unaffected planned actions", () => {
  const pattern = /^  if \(a\.kind !== "foe" && has\(who, "confuse"\) && !a\.confused\) a = \{ kind: "attack", who, confused: true \};\r?$/m;
  assert.ok(pattern.test(source), "production conversion exists after the held-status checks");
  const legacy = source.replace(pattern, "");
  for (const kind of ["magic", "item", "attack"])
    assert.throws(() => assertSwing(inflictedBeforeQueued(kind, legacy)), assert.AssertionError);
});
console.log("Prismheart confused action checks: " + checks + " passed.");
