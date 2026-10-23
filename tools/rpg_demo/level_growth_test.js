// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/level_growth_test.js
// Uses production party factory, victory/level-up and inn functions with authored realm catalogs.
// Bounded defeated-foe fixtures; no battle bot, browser, game loop, real storage or data writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const parties = data("party").party, interiors = data("interiors").interiors;
const bestiaries = { portal: data("portal-bestiary").types, prism: data("prism-bestiary").types };
const portalZones = data("portal-encounters").zones;
const clone = value => JSON.parse(JSON.stringify(value));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix));
  assert.ok(found, "production declaration exists: " + prefix); return found;
}
const source = [
  between("const START_LEVEL =", "/* Recruits:"), line("const alive ="), line("const clearAll ="), line("let B = null;"),
  between("function recoverStolenGold()", "function hurtFoe("), between("function endRound()", "function finishBattle()"), between("function innPrompt()", "function openChest("),
  "this.api = { start: () => { party = buildParty(); }, makeMember, endRound, innPrompt, getParty: () => party, getReserve: () => reserve, " +
  "getGold: () => gold, getBattle: () => B, setBattle: value => { B = value; } };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(realm, productionSource = source) {
  const sounds = [], prompts = [], felled = [];
  const c = {
    D: { party: clone(parties[realm]), gear: {}, interiors: clone(interiors[realm]), dungeons: [],
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    map: { kind: "interior", name: "Inn", cue: "TOWN" }, fade: 0, fadeCb: null,
    cue() {}, sfx: name => sounds.push(name), fell: foes => felled.push(...foes.map(f => f.key)),
    ask: (question, options, then) => prompts.push({ question, options, then })
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 }); c.api.start();
  return { c, api: c.api, realm, sounds, prompts, felled };
}
function victory(s, keys) {
  assert.ok(keys.length > 0 && keys.length <= 4, "victory fixture stays within the existing four-foe battle limit");
  const foes = keys.map(key => {
    const row = bestiaries[s.realm].find(f => f.key === key); assert.ok(row, "authored foe exists: " + key);
    return { ...clone(row), hp: 0 };
  });
  s.api.setBattle({ foes, phase: "act", round: 1, acts: [], queue: [] }); s.api.endRound();
  assert.equal(s.api.getBattle().phase, "end"); assert.equal(s.api.getBattle().result, "win");
}
function drips(s, n) { for (let i = 0; i < n; i++) victory(s, ["portal_best_drip"]); }
function gelfins(s, n) { for (let i = 0; i < n; i++) victory(s, ["prism_best_gelfin"]); }
function memberData(s, job) { return s.c.D.party.members.find(m => m.job === job); }
function resources(m) { return JSON.stringify({ hp: m.hp, max: m.max, mp: m.mp, mmax: m.mmax, st: m.st }); }
function assertMirelGain(m) {
  assert.equal(m.lv, 2); assert.equal(m.mmax, 26, "Mirel receives the authored six MP of earned capacity");
}
check("three ordinary Portal Drip wins grant Mirel's authored level-two MP", () => {
  const s = session("portal"), m = s.api.getParty()[1], before = clone(m);
  assert.equal(m.name, "Mirel"); assert.equal(m.next, 30); assert.equal(m.mp, 20);
  drips(s, 3); assertMirelGain(m); assert.equal(m.mp, 26);
  const fresh = s.api.makeMember(memberData(s, m.job), 2);
  assert.equal(m.mmax, fresh.mmax); assert.equal(m.max, fresh.max); assert.equal(m.hp, before.hp + 7);
  assert.equal(m.exp, 6); assert.equal(m.next, 35); assert.equal(s.api.getGold(), 138);
  for (const key of Object.keys(before.st)) assert.equal(m.st[key], before.st[key] + 1);
  assert.equal(JSON.stringify(m.equip), JSON.stringify(before.equip)); assert.equal(JSON.stringify(m.spells), JSON.stringify(before.spells));
  assert.equal(s.api.getBattle().msg, "VICTORY! 12 EXP AND 6 GOLD.");
  assert.ok(s.api.getBattle().endLines.includes("Mirel REACHES LEVEL 2!")); assert.equal(s.felled.length, 3);
});
check("earned MP preserves spent MP rather than fully healing the caster", () => {
  const s = session("portal"), m = s.api.getParty()[1]; m.mp = 3; m.hp -= 10;
  const missingMP = m.mmax - m.mp, missingHP = m.max - m.hp;
  drips(s, 3); assertMirelGain(m); assert.equal(m.mp, 9); assert.equal(m.mmax - m.mp, missingMP);
  assert.equal(m.max - m.hp, missingHP); assert.ok(m.mp < m.mmax);
});
check("Prism Ysolde's next earned level grants five MP and retains thresholds", () => {
  const s = session("prism"), m = s.api.getParty()[1], max = m.mmax; m.mp -= 11;
  assert.equal(m.lv, 15); assert.equal(m.next, 400); gelfins(s, 22);
  assert.equal(m.lv, 16); assert.equal(m.mmax, max + 5); assert.equal(m.mp, m.mmax - 11);
  assert.equal(m.exp, 18); assert.equal(m.next, 472);
  assert.equal(m.mmax, s.api.makeMember(memberData(s, m.job), 16).mmax);
});
check("a real three-Moss-Drip formation grants MP once for each earned level", () => {
  const formation = Object.values(portalZones).flatMap(z => z.formations).find(f => f.enemies.length === 3 && f.enemies.every(k => k === "portal_best_moss_drip"));
  assert.ok(formation, "the three-Moss-Drip formation is authored");
  const s = session("portal"), m = s.api.getParty()[1], before = clone(m); m.mp = 4; victory(s, formation.enemies);
  assert.equal(m.lv, 3); assert.equal(m.mmax, 32); assert.equal(m.mp, 16); assert.equal(m.exp, 10); assert.equal(m.next, 41);
  assert.equal(m.max, before.max + 14); assert.equal(m.hp, before.hp + 14); assert.equal(s.api.getGold(), 156);
  for (const key of Object.keys(before.st)) assert.equal(m.st[key], before.st[key] + 2);
});
check("a recruited reserve gains MP at its existing half-EXP pace", () => {
  const s = session("prism"), data = s.c.D.party.members.find(m => m.job === "Beastcaller");
  assert.equal(data.joins, "after Cinder Forge"); const reserve = s.api.makeMember(data, 15); reserve.mp -= 7;
  s.api.getReserve().push(reserve); const max = reserve.mmax; gelfins(s, 44);
  assert.equal(reserve.lv, 15); assert.equal(reserve.exp, 396); assert.equal(reserve.mmax, max);
  gelfins(s, 1); assert.equal(reserve.lv, 16); assert.equal(reserve.exp, 5); assert.equal(reserve.mmax, max + 3);
  assert.equal(reserve.mp, reserve.mmax - 7); assert.equal(s.api.getParty()[1].exp, 455);
});
check("zero-MP-growth heroes stay at zero MP after earning a level", () => {
  const s = session("prism"), m = s.api.getParty()[0]; assert.equal(memberData(s, m.job).growth.mp, 0);
  gelfins(s, 22); assert.equal(m.lv, 16); assert.equal(m.mp, 0); assert.equal(m.mmax, 0);
});
check("downed members retain the existing no-EXP and no-growth policy", () => {
  const s = session("portal"), m = s.api.getParty()[1]; m.hp = 0; m.mp = 7; m.exp = 29; const before = JSON.stringify(m);
  drips(s, 1); assert.equal(JSON.stringify(m), before); assert.equal(s.api.getGold(), 126);
});
check("victories below the threshold grant no resource or stat growth", () => {
  const s = session("portal"), m = s.api.getParty()[1]; m.mp = 3; m.hp -= 10; const before = resources(m);
  drips(s, 2); assert.equal(m.lv, 1); assert.equal(m.exp, 24); assert.equal(m.next, 30); assert.equal(resources(m), before);
});
check("the normal inn restores the newly earned MP cap at the same price", () => {
  const s = session("portal"), m = s.api.getParty()[1]; m.mp = 3; drips(s, 3); assert.equal(m.mp, 9);
  const gold = s.api.getGold(), price = s.c.D.interiors.Inn.rest_price || 10;
  s.api.innPrompt(); assert.equal(s.prompts.length, 1); s.prompts[0].then(0);
  assert.equal(m.mp, 26); assert.equal(m.mp, m.mmax); assert.equal(s.api.getGold(), gold - price);
  assert.equal(s.c.fade, 1); assert.equal(typeof s.c.fadeCb, "function"); // Do not run the later save callback.
});
check("older missing capacity is preserved, with only the next earned increment added", () => {
  const s = session("prism"), m = s.api.getParty()[1];
  // A level-sixteen older journey may retain its original level-fifteen cap. Do not migrate or backfill it here.
  m.lv = 16; m.next = 472; m.exp = 453; m.mp = 40; const oldMax = m.mmax;
  gelfins(s, 1); assert.equal(m.lv, 17); assert.equal(m.mmax, oldMax + 5); assert.equal(m.mp, 45);
  assert.equal(m.mmax, s.api.makeMember(memberData(s, m.job), 17).mmax - 5);
});
const preFix = source.replace("m.mmax += growth.mp; m.mp += growth.mp; ", "");
assert.notEqual(preFix, source, "the controlled pre-fix removes earned MP growth");
check("the Portal capacity assertion detects pre-fix missing growth", () => {
  const s = session("portal", preFix); drips(s, 3);
  assert.throws(() => assertMirelGain(s.api.getParty()[1]), /six MP of earned capacity/);
});
check("the Prism capacity assertion detects pre-fix missing growth", () => {
  const s = session("prism", preFix), m = s.api.getParty()[1], max = m.mmax; gelfins(s, 22);
  assert.throws(() => assert.equal(m.mmax, max + 5, "Ysolde receives five MP of earned capacity"), /five MP of earned capacity/);
});
console.log("Prismheart/Portal level growth: " + checks + " focused checks passed");
