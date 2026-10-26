// SPDX-License-Identifier: MIT
// Focused DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/storage_failure_test.js
// Extracts actual storage, inn, final-victory, ending and button-edge handlers; no browser,
// art, audio, real storage, build, native runtime or production catalog writes are started.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const parties = JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg/party.json"), "utf8")).party;
const Save = require("./journey-save.js");
const clone = value => JSON.parse(JSON.stringify(value));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start);
  return html.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix));
  assert.ok(found, "production declaration exists: " + prefix); return found;
}
const source = [
  between("const LOGICAL =", "const KEYMAP ="), between("const KEYMAP =", "const keyboardCodes ="), line("const hit ="),
  line("const roster ="), between("function makeMember(", "/* Recruits:"),
  between('  SETTINGS.onAction("SaveErase"', '  SETTINGS.on("TouchControls"'),
  between("function innPrompt()", "function openChest("),
  between("function finishBattle()", "function bossGate()"),
  between("function saveGame()", "function saveSummary()"),
  between("function titlePrompt(", "function drawTitle()"),
  between("let ending = null;", "function drawGameOver()"),
  "this.api = { makeMember, saveGame, innPrompt, finishBattle, endingTick, drawEnding, titlePrompt, setHeld, hit, " +
  "ending: () => ending, hold: (key, down) => setHeld('test', key, down), keys: KEYMAP };"
].join("\n");
let checks = 0;
function check(label, fn) {
  try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; }
}
function session(realm = "prism", productionSource = source) {
  const records = new Map(), notices = [], dialogs = [], draws = [], actions = {};
  const key = realm + ".save.v1";
  const c = {
    SAVE_KEY: key, START_LEVEL: 15, W: realm === "portal" ? 256 : 320, H: 224,
    D: { realm_key: realm, realm: realm === "prism" ? "Prismheart" : "Portal Realm", party: clone(parties[realm]),
      interiors: { Inn: { rest_price: 10 } }, dungeons: [] },
    party: [], reserve: [], bag: { "Herb Tonic": 3 }, gold: 100,
    state: { beaten: new Set(["PyreWarden"]), seen: {}, air: null, fish: {}, quests: {}, day: 2, minute: 600 },
    opened: new Set(["dungeon0/0:1,2"]), B: null, mode: "field", fade: 0, fadeCb: null, titleT: 17,
    map: { kind: "dungeon", cue: "CAVE", info: { boss: { gate: { x: 0, y: 0 } } }, grid: [["BossGate"]] },
    performance: { now: () => 100 },
    SETTINGS: { onAction: (name, fn) => { actions[name] = fn; } },
    PAD: null, IM: { title: {} },
    localStorage: {
      setItem: (name, text) => { c.writeAttempts++; if (c.failWrite) throw new Error("storage full"); records.set(name, text); },
      removeItem: name => { c.eraseAttempts++; if (c.failErase) throw new Error("storage denied"); records.delete(name); }
    },
    failWrite: false, failErase: false, writeAttempts: 0, eraseAttempts: 0,
    say: lines => dialogs.push(Array.from(lines)), toast: (title, sub) => notices.push({ title, sub }),
    ask: (message, choices, choose) => { c.choose = choose; },
    wakeAt: hour => { c.state.day++; c.state.minute = hour * 60; },
    clearAll: members => members.forEach(m => { m.status = {}; }), saveSummary: () => "Recorded journey", sfx() {}, cue: name => { c.lastCue = name; },
    tw: label => String(label).length * 6,
    text: (label, x, y, color) => draws.push({ label: String(label), x, y, color }),
    g: { fillStyle: "", fillRect() {}, drawImage() {} }
  };
  if (realm === "portal") c.D.realm_profile = { start_level: 1 };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  c.reserve = c.D.party.members.filter(m => m.joins !== "start").slice(0, 1).map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  return { c, api: c.api, key, records, notices, dialogs, draws, actions };
}
function seed(s) {
  assert.equal(s.api.saveGame(), true);
  const raw = s.records.get(s.key);
  assert.equal(Save.read(raw, s.c.D.realm_key, s.c.D.party.members).ok, true, "real catalog writer is readable");
  return raw;
}
function finishVictory(s, final = true) {
  s.c.B = { result: "win", boss: true, prevCue: "CAVE", foes: [{ boss: true, final, bossName: "PrismDevourer", name: "Prism Devourer" }] };
  s.api.finishBattle(); const cb = s.c.fadeCb; assert.equal(typeof cb, "function"); s.c.fadeCb = null; cb();
}
function press(s, keys, dt = 0.01) {
  keys.forEach(k => s.api.hold(k, true)); s.api.endingTick(dt); keys.forEach(k => s.api.hold(k, false));
}
function badEnding(s) {
  const original = seed(s); s.c.failWrite = true; const refs = [s.c.party, s.c.bag, s.c.state.beaten];
  finishVictory(s);
  assert.equal(s.c.mode, "ending"); assert.equal(s.api.ending().saved, false);
  assert.equal(s.c.state.beaten.has("PrismDevourer"), true); assert.equal(s.c.map.grid[0][0], "Floor");
  assert.deepEqual([s.c.party, s.c.bag, s.c.state.beaten], refs, "live victory remains intact");
  assert.equal(s.records.get(s.key), original, "previous saved bytes remain intact");
  return original;
}
function failedErase(s) {
  const original = seed(s); s.c.failErase = true; s.actions.SaveErase();
  assert.equal(s.records.get(s.key), original);
  assert.equal(s.notices.at(-1).title, "Saved journey not erased");
  assert.match(s.notices.at(-1).sub, /record was kept/);
  assert.ok(!s.notices.some(n => n.title === "Saved journey erased"));
}
function failedInn(s) {
  const original = seed(s); s.c.failWrite = true; s.api.innPrompt(); s.c.choose(0); s.c.fadeCb();
  assert.equal(s.records.get(s.key), original);
  assert.match(s.dialogs.at(-1).join(" "), /COULD NOT BE SAVED.*KEEP THIS GAME OPEN.*TRY SAVE/);
  assert.equal(s.notices.at(-1).title, "Journey not saved");
}
check("complete production inline script compiles without executing the game", () => {
  const script = html.match(/<script>\s*([\s\S]*?)<\/script>/);
  assert.ok(script, "main inline script exists"); new vm.Script(script[1], { filename: "index.html inline script" });
});
for (const realm of ["prism", "portal"]) {
  check(realm + ": failed erase is truthful and a later retry removes only this realm", () => {
    const s = session(realm); const other = realm === "prism" ? "portal.save.v1" : "prism.save.v1";
    s.records.set(other, "other realm record"); failedErase(s);
    s.c.failErase = false; s.actions.SaveErase();
    assert.equal(s.records.has(s.key), false); assert.equal(s.records.get(other), "other realm record");
    assert.equal(s.notices.at(-1).title, "Saved journey erased"); assert.equal(s.c.eraseAttempts, 2);
  });
  check(realm + ": a failed inn save keeps paid rest and warns how to retry", () => {
    const s = session(realm), original = seed(s);
    s.c.party.concat(s.c.reserve).forEach(m => { m.hp = 1; m.mp = 0; m.status = { poison: true }; });
    s.c.failWrite = true; s.api.innPrompt(); s.c.choose(0); s.c.fadeCb();
    assert.equal(s.c.gold, 90); assert.equal(s.c.state.minute, 420);
    s.c.party.concat(s.c.reserve).forEach(m => { assert.equal(m.hp, m.max); assert.equal(m.mp, m.mmax); assert.deepEqual(Object.keys(m.status), []); });
    assert.equal(s.records.get(s.key), original);
    assert.match(s.dialogs.at(-1).join(" "), /RESTED.*COULD NOT BE SAVED.*KEEP THIS GAME OPEN.*TRY SAVE/);
    assert.equal(s.notices.at(-1).title, "Journey not saved");
  });
  check(realm + ": a successful inn save still records the rested journey", () => {
    const s = session(realm); s.api.innPrompt(); s.c.choose(0); s.c.fadeCb();
    assert.equal(s.notices.at(-1).title, "Journey saved");
    assert.equal(JSON.parse(s.records.get(s.key)).gold, 90);
    assert.match(s.dialogs.at(-1).join(" "), /WRITTEN IN THE INN'S BOOK/);
  });
}
check("declining or being unable to afford rest does not write or change party", () => {
  const s = session(), before = JSON.stringify(s.c.party);
  s.api.innPrompt(); s.c.choose(1); assert.equal(s.c.gold, 100); assert.equal(s.c.writeAttempts, 0);
  s.c.gold = 0; s.api.innPrompt(); s.c.choose(0);
  assert.equal(s.c.writeAttempts, 0); assert.equal(JSON.stringify(s.c.party), before);
});
check("final-victory write failure keeps both live victory and the prior save", () => {
  const s = session(); badEnding(s); assert.equal(s.notices.at(-1).title, "Victory not saved");
});
check("failed ending retries stay on the ending; recovered storage saves victory before a new title press", () => {
  const s = session(), original = badEnding(s); s.api.endingTick(4);
  press(s, ["a"]); assert.equal(s.c.mode, "ending"); assert.equal(s.records.get(s.key), original);
  s.c.failWrite = false; press(s, ["start"]);
  assert.equal(s.c.mode, "ending"); assert.equal(s.api.ending().saved, true);
  const saved = JSON.parse(s.records.get(s.key)); assert.ok(saved.beaten.includes("PrismDevourer"));
  assert.equal(s.notices.at(-1).title, "Victory saved");
  assert.equal(Save.read(s.records.get(s.key), "prism", s.c.D.party.members).ok, true);
  press(s, ["start"]); assert.equal(s.c.mode, "title"); assert.equal(s.c.titleT, 0);
});
check("held retry or exit buttons do not repeat without a release", () => {
  const s = session(); badEnding(s); s.api.endingTick(4);
  s.api.hold("a", true); s.api.endingTick(0.01); const attempts = s.c.writeAttempts;
  s.c.failWrite = false; s.api.endingTick(0.01); assert.equal(s.c.writeAttempts, attempts);
  s.api.hold("a", false); s.api.hold("a", true); s.api.endingTick(0.01);
  assert.equal(s.api.ending().saved, true); s.api.endingTick(0.01); assert.equal(s.c.mode, "ending");
});
check("Back wins over simultaneous retry and returns the unsaved live victory to play", () => {
  const s = session(), original = badEnding(s); s.api.endingTick(4); const attempts = s.c.writeAttempts;
  press(s, ["b", "a", "start"]);
  assert.equal(s.c.mode, "field"); assert.equal(s.api.ending(), null); assert.equal(s.c.lastCue, "CAVE");
  assert.equal(s.c.writeAttempts, attempts); assert.equal(s.records.get(s.key), original);
  assert.equal(s.c.state.beaten.has("PrismDevourer"), true);
  assert.match(s.dialogs.at(-1).join(" "), /NOT SAVED.*LEAVE THE DUNGEON.*SAVE IN THE FIELD MENU/);
  for (const k of ["a", "start", "b"]) assert.equal(s.api.hit(k), false);
});
check("ordinary saved ending returns to title and consumes simultaneous A/Start edges", () => {
  const s = session(); finishVictory(s); assert.equal(s.api.ending().saved, true); s.api.endingTick(4);
  press(s, ["a", "start"]); assert.equal(s.c.mode, "title");
  assert.equal(s.api.hit("a"), false); assert.equal(s.api.hit("start"), false);
  assert.equal(s.c.writeAttempts, 1, "no unnecessary save on leaving a successfully saved ending");
});
check("nonfinal boss victories retain the ordinary gate and story route without autosave", () => {
  const s = session(); s.c.shardCount = () => 1; finishVictory(s, false);
  assert.equal(s.c.mode, "field"); assert.equal(s.c.writeAttempts, 0); assert.equal(s.api.ending(), null);
  assert.match(s.dialogs.at(-1).join(" "), /GATE CRUMBLES/);
});
check("failed ending prompts remain visible with long valid pad labels at both realm widths", () => {
  for (const realm of ["prism", "portal"]) {
    const s = session(realm); badEnding(s); s.c.PAD = { devices: () => [{ index: 0 }], label: a => a === "cancel" ? "BUTTON88" : "BUTTON99" };
    s.api.drawEnding(); const prompts = s.draws.slice(-4);
    assert.deepEqual(prompts.map(p => p.label), ["VICTORY NOT SAVED", "KEEP THIS GAME OPEN.", "PRESS BUTTON99 TO RETRY SAVE", "PRESS BUTTON88 TO KEEP PLAYING"]);
    for (const p of prompts) {
      assert.ok(p.x >= 0 && p.x + s.c.tw(p.label) + 1 <= s.c.W, "glyphs and shadows fit the screen width");
      assert.ok(p.y >= s.c.H - 72 && p.y + 8 <= s.c.H, "glyphs remain in their persistent notice area");
    }
  }
});
check("invalid pad labels use the existing keyboard/touch fallbacks", () => {
  const s = session(); s.c.PAD = { devices: () => [{ index: 0 }], label: () => "a label too long" };
  assert.equal(s.api.titlePrompt(), "PRESS START"); assert.equal(s.api.titlePrompt("cancel", "X/ESC/B"), "PRESS X/ESC/B");
});
check("without a pad, recovery names the real keyboard and touch controls", () => {
  for (const realm of ["prism", "portal"]) {
    const s = session(realm); badEnding(s); s.api.drawEnding();
    assert.equal(s.api.keys.Enter, "start"); assert.equal(s.api.keys.KeyX, "b"); assert.equal(s.api.keys.Escape, "b");
    assert.match(html, /<button data-k="start"/); assert.match(html, /<button data-k="b"/);
    assert.deepEqual(s.draws.slice(-2).map(p => p.label), ["PRESS ENTER/START TO RETRY SAVE", "PRESS X/ESC/B TO KEEP PLAYING"]);
    for (const p of s.draws.slice(-2)) assert.ok(p.x >= 0 && p.x + s.c.tw(p.label) + 1 <= s.c.W);
  }
});
check("controlled original silent erase, inn save and title-return behaviors are rejected", () => {
  const oldErase = source.replace('SETTINGS.onAction("SaveErase", eraseSavedJourney);',
    'SETTINGS.onAction("SaveErase", () => { try { localStorage.removeItem(SAVE_KEY); } catch (e) {} toast("Saved journey erased"); });');
  assert.notEqual(oldErase, source); assert.throws(() => failedErase(session("prism", oldErase)), assert.AssertionError);
  const from = source.indexOf("function endingTick(dt)"), to = source.indexOf("function drawEnding()", from);
  const oldEnding = source.slice(0, from) + 'function endingTick(dt) { ending.t += dt; if (ending.t > 3 && (hit("a") || hit("start"))) { ending = null; mode = "title"; titleT = 0; cue("TITLE"); } }\n' + source.slice(to);
  assert.throws(() => { const s = session("prism", oldEnding); badEnding(s); s.api.endingTick(4); press(s, ["a"]); assert.equal(s.c.mode, "ending"); }, assert.AssertionError);
  const originalInn = 'function innPrompt() { const price = (D.interiors.Inn || {}).rest_price || 10; ask("REST?", ["YES", "NO"], i => { if (i === 1 || gold < price) return; gold -= price; roster().forEach(m => { m.hp = m.max; m.mp = m.mmax; }); clearAll(roster()); fade = 1; fadeCb = () => { cue(map.cue); wakeAt(7); const ok = saveGame(); say(["GOOD MORNING! YOUR PARTY IS RESTED."].concat(ok ? ["YOUR JOURNEY HAS BEEN WRITTEN IN THE INN\'S BOOK."] : []), null, 6); if (ok) toast("Journey saved", saveSummary()); }; }); }\n';
  const oldInn = source.replace(between("function innPrompt()", "function openChest("), originalInn);
  assert.notEqual(oldInn, source); assert.throws(() => failedInn(session("prism", oldInn)), assert.AssertionError);
});
console.log("storage failure: " + checks + " focused groups passed");
