// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/held_action_test.js
// Real Portal browser catalog repro: Web Spinner/Night Bell can precede level-one heroes.
// Prism's default level-15 roster outruns its current Bind/Paralyze foes; no default-Prism battle observation claimed.
// Runs production action/foe/chooser/queue/status functions, without browser, game loop or native/host modules.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const members = data("party").party.portal.members, spells = data("spells").spells.filter(s => s.realm === "portal");
const foes = data("portal-bestiary").types, encounters = JSON.stringify(data("portal-encounters")), gear = {};
for (const shop of Object.values(data("interiors").interiors.portal))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"),
  between("const ITEM_KINDS =", "function menuTick()"), between("function useItem(", "/* Four rows"),
  between("const STATUS =", "/* ---------- bestiary"), line("function nextChooser("),
  between("function advanceChooser(", "function endRound()"),
  "this.api = { makeMember, doAction, foeTurn, nextChooser, advanceChooser, roundStatuses, cure, inflict, landHit, spdOf };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(productionSource = source, key = "portal_best_web_spinner", targetIndex = 0) {
  const f = foes.find(value => value.key === key), sounds = [], fixedMath = Object.create(Math);
  assert.ok(f && encounters.includes('"' + key + '"'), "real foe occurs in the Portal encounter catalog");
  const c = { D: { realm_profile: { start_level: 1 } }, START_LEVEL: 15, ACTIVE: 4, W: 320,
    party: [], reserve: [], bag: { "Herb Tonic": 2 }, GEAR: clone(gear), map: { kind: "town" }, gold: 120,
    rnd: (a, b) => (a + b) / 2, ri: () => targetIndex, Math: fixedMath, sfx: value => sounds.push(value),
    roster: () => c.party.concat(c.reserve),
    B: { phase: "cmd", who: 2, acts: [], queue: [], round: 1, turn: 0, t: 0, wait: 0, msg: "", fx: null, pops: [], flash: {},
      foes: [{ key: f.key, name: f.name, hp: f.hp, max: f.hp, atk: f.attack, def: f.defence, spd: f.speed,
        beh: f.behaviour, x: 24, y: 26, size: 56 }] }
  };
  fixedMath.random = () => 0.1; // A real hit (>= .06), real status infliction (< .3), no attack miss or critical.
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = members.map(member => c.api.makeMember(member, 1));
  return { c, sounds, actor: c.party[targetIndex], foe: c.B.foes[0], spell: name => spells.find(s => s.name === name) };
}
function action(s, kind) {
  if (kind === "magic") return { kind, who: s.actor, spell: s.spell("Ember"), target: s.foe };
  if (kind === "item") return { kind, who: s.actor, item: "Herb Tonic", target: s.actor };
  return { kind, who: s.actor, target: s.foe };
}
const resources = s => JSON.stringify({ party: s.c.party, foes: s.c.B.foes, bag: s.c.bag, phase: s.c.B.phase, result: s.c.B.result });
function assertSkipped(s, queued, status) {
  const before = resources(s); s.sounds.length = 0; s.c.B.fx = null; s.c.api.doAction(queued);
  assert.equal(resources(s), before, "held action cannot damage, spend MP/items, defend or escape");
  assert.equal(s.c.B.wait, 0.45); assert.equal(s.c.B.msg, s.actor.name + " IS " + (status === "bind" ? "BOUND" : "PARALYZED") + ".");
  assert.equal(s.c.B.fx, null); assert.deepEqual(s.sounds, []);
}
function inflictedBeforeQueued(productionSource = source, status = "bind", kind = "attack") {
  const s = session(productionSource, status === "bind" ? "portal_best_web_spinner" : "portal_best_night_bell");
  const queued = action(s, kind); // The hero selected this while able to act.
  s.c.B.acts = s.c.party.map(member => member === s.actor ? queued : { kind: "defend", who: member });
  assert.equal(s.c.api.nextChooser(0), 0); s.c.api.advanceChooser();
  const foeIndex = s.c.B.queue.findIndex(a => a.kind === "foe"), actorIndex = s.c.B.queue.indexOf(queued);
  assert.ok(foeIndex >= 0 && actorIndex > foeIndex, "actual initiative queue puts this real foe before the hero");
  while (s.c.B.queue[0] !== queued) s.c.api.doAction(s.c.B.queue.shift());
  assert.ok(s.actor.hp > 0 && s.actor.status[status], "real foeTurn hit inflicted the status before the queued action");
  assert.equal(s.c.api.nextChooser(0), 1, "affected hero is also skipped by the established chooser");
  assertSkipped(s, s.c.B.queue.shift(), status); return s;
}
for (const status of ["bind", "paralyze"]) for (const kind of ["attack", "item"])
  check("ordinary Portal " + status + " inflicted before queued " + kind + " cancels that action", () => inflictedBeforeQueued(source, status, kind));
check("Web Spinner binding also cancels Mirel's already selected spell", () => {
  const s = session(source, "portal_best_web_spinner", 1), queued = action(s, "magic");
  assert.ok(s.actor.spells.includes(queued.spell.name), "the real Sage knows this spell");
  assert.ok(s.c.api.spdOf({ kind: "foe", who: s.foe }) > s.c.api.spdOf(queued));
  s.c.api.doAction({ kind: "foe", who: s.foe }); assert.ok(s.actor.hp > 0 && s.actor.status.bind);
  assertSkipped(s, queued, "bind");
});
for (const status of ["bind", "paralyze"]) for (const kind of ["attack", "magic", "item", "defend", "run"])
  check(status + " prevents queued " + kind + " effects", () => {
    const s = session(source, "portal_best_web_spinner", 1); s.c.api.inflict(s.actor, status);
    assertSkipped(s, action(s, kind), status);
  });
for (const status of ["bind", "paralyze"]) check("curing " + status + " restores the next selected action", () => {
  const s = session(source, "portal_best_web_spinner", 1); s.c.api.inflict(s.actor, status);
  assertSkipped(s, action(s, "magic"), status); assert.equal(s.c.api.cure(s.actor, status), true);
  assert.equal(s.c.api.nextChooser(1), 1); const mp = s.actor.mp; s.c.api.doAction(action(s, "magic"));
  assert.equal(s.actor.mp, mp - s.spell("Ember").mp); assert.ok(s.foe.hp < s.foe.max);
});
for (const status of ["bind", "paralyze"]) check(status + " keeps its two-round timer and expiration restores actions", () => {
  const s = session(); s.c.api.inflict(s.actor, status); assertSkipped(s, action(s, "attack"), status);
  assert.equal(s.actor.status[status], 2); s.c.api.roundStatuses(); assert.equal(s.actor.status[status], 1);
  assertSkipped(s, action(s, "attack"), status); s.c.api.roundStatuses(); assert.equal(s.actor.status[status], undefined);
  s.c.api.doAction(action(s, "attack")); assert.ok(s.foe.hp < s.foe.max);
});
for (const kind of ["attack", "magic", "item", "defend", "run"]) check("unaffected " + kind + " still works", () => {
  const s = session(source, "portal_best_web_spinner", 1); s.actor.hp = 1; const mp = s.actor.mp;
  s.c.api.doAction(action(s, kind));
  if (kind === "attack") assert.ok(s.foe.hp < s.foe.max);
  if (kind === "magic") { assert.equal(s.actor.mp, mp - s.spell("Ember").mp); assert.ok(s.foe.hp < s.foe.max); }
  if (kind === "item") { assert.equal(s.c.bag["Herb Tonic"], 1); assert.ok(s.actor.hp > 1); }
  if (kind === "defend") assert.equal(s.actor.defend, true);
  if (kind === "run") { assert.equal(s.c.B.phase, "end"); assert.equal(s.c.B.result, "run"); }
});
check("sleep still skips immediately, and an actual waking hit restores action", () => {
  const s = session(); s.c.api.inflict(s.actor, "sleep"); const before = resources(s);
  s.c.api.doAction(action(s, "attack")); assert.equal(resources(s), before); assert.equal(s.c.B.wait, 0.45); assert.match(s.c.B.msg, /ASLEEP/);
  s.c.api.landHit(s.actor, 1); assert.equal(s.actor.status.sleep, undefined);
  s.c.api.doAction(action(s, "attack")); assert.ok(s.foe.hp < s.foe.max);
});
check("a downed hero still skips before the held-status message", () => {
  const s = session(); s.c.api.inflict(s.actor, "bind"); s.actor.hp = 0; const before = resources(s);
  s.c.api.doAction(action(s, "attack")); assert.equal(resources(s), before); assert.equal(s.c.B.wait, 0); assert.equal(s.c.B.msg, "");
});
check("Bind and Paralyze do not change foe turns", () => {
  const s = session(); s.c.api.inflict(s.foe, "bind"); s.c.api.inflict(s.foe, "paralyze"); const hp = s.actor.hp;
  s.c.api.doAction({ kind: "foe", who: s.foe }); assert.ok(s.actor.hp < hp); assert.ok(s.actor.status.bind);
});
check("the existing confused attack still executes its own behavior", () => {
  const s = session(); s.c.api.inflict(s.actor, "confuse"); const hp = s.c.party[1].hp;
  s.c.api.doAction({ kind: "attack", who: s.actor, confused: true }); assert.ok(s.c.party[1].hp < hp);
});
check("removing the actual held-status guard reproduces both earlier-in-round failures", () => {
  const guard = /  const heldStatus =[^\r\n]*\r?\n  if \(heldStatus\) \{[^\r\n]*\}\r?\n/;
  assert.ok(guard.test(source)); const legacy = source.replace(guard, "");
  for (const status of ["bind", "paralyze"])
    assert.throws(() => inflictedBeforeQueued(legacy, status), assert.AssertionError);
});
console.log("Shared browser held-action checks: " + checks + " passed (real Portal catalog; not default-Prism runtime proof).");
