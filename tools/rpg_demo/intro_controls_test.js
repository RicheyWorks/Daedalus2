// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/intro_controls_test.js
// Actual onboarding/prompt/input metadata, authored Portal intro and save-help rows; no browser/storage/boot.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const portal = fs.readFileSync(path.join(__dirname, "portal_realm.py"), "utf8");
const portalIntro = JSON.parse(portal.match(/"intro": (\[[\s\S]*?\]),/)[1]);
const lore = "WELCOME TO PRISMHEART. WARDENS STIR ACROSS THE ISLE, EACH ONE GROWN AROUND A SHARD OF THE HEART. THE ELDER IN TOWN KNOWS MORE.";
const touch = Array.from(html.matchAll(/<button data-k="([^"]+)"[^>]*>([^<]+)<\/button>/g), m => ({ action: m[1], label: m[2] }));
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const CHARS ="), between("const KEYMAP =", "const keyboardCodes ="),
  line("let journeySerial ="),
  line("const PAD_TO_DEMO ="), line("let dlg = null;"), line("function say("), line("function wrap("),
  between("function beginJourney(", "function titleTick("), between("function titlePrompt(", "function drawTitle("),
  "if (SETTINGS) {\n" + between('  SETTINGS.extend({ tab: "GAMEPLAY", section: "Saved Game"', '  SETTINGS.onAction("SaveErase"') + "\n}",
  "this.api = { beginJourney, titlePrompt, wrap, dialog: () => dlg, chars: CHARS, keys: KEYMAP, padMap: PAD_TO_DEMO };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(options = {}, productionSource = source) {
  const timers = [], visits = [], rows = [], labels = [], settingsReads = [], c = {
    D: { realm_profile: options.profile }, mode: "field", // Observe the intro after the downstream arrival fade.
    PAD: options.pad ? {
      devices: () => [{ index: 7 }], label: (action, index) => { labels.push({ action, index }); return options.pad[action]; }
    } : null,
    SETTINGS: options.noSettings ? null : {
      loaded: () => options.loaded !== false,
      get: key => { settingsReads.push(key); return options.tips !== false; },
      extend: group => rows.push(...group.rows)
    },
    setTimeout: (callback, ms) => timers.push({ callback, ms }),
    townMap: () => "existing-town", goto: (...args) => visits.push(args), saveSummary: () => "Existing journey",
    localStorage: { setItem() { throw new Error("onboarding must not save"); }, removeItem() { throw new Error("onboarding must not erase"); } }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  return { c, api: c.api, timers, visits, rows, labels, settingsReads,
    start() { c.api.beginJourney(); return this; }, reveal() { assert.equal(timers.length, 1); assert.equal(timers[0].ms, 600); timers[0].callback(); return c.api.dialog(); } };
}
function controls(s) {
  const dialog = s.start().reveal(); assert.equal(dialog.pages[0], lore);
  assert.equal(dialog.pages.length, 3); assert.equal(dialog.then, null); assert.equal(dialog.voice, 0);
  assert.equal(dialog.pages[2], "JOURNEY HAS YOUR MAP AND ROUTE PIN. ORDER PREVIEWS YOUR FRONT LINE. SAVE OUTSIDE DUNGEONS OR REST AT AN INN.");
  const match = dialog.pages[1].match(/^PRESS ([^.]+) TO TALK\. PRESS ([^.]+) FOR MENU\./);
  assert.ok(match, "the controls page names physical talk and menu options");
  for (const page of dialog.pages) {
    const lines = s.api.wrap(page, 48);
    assert.ok(lines.length <= 4 && lines.every(text => text.length <= 48), "the entire page fits the current 320px dialog");
    assert.ok(Array.from(page).every(char => s.api.chars.includes(char)), "all dialog glyphs exist in the bitmap font");
  }
  assert.ok(dialog.pages[1].endsWith("THE ROAD SOUTH LEAVES TOWN.")); return match.slice(1);
}
function fallback(productionSource = source, pad) {
  const s = session({ pad }, productionSource), [talk, menu] = controls(s);
  const expected = { Z: "KeyZ", SPACE: "Space", ENTER: "Enter" };
  for (const [printed, action] of [[talk, "a"], [menu, "start"]]) {
    const physical = printed.match(/^(.+) OR TAP (.+)$/); assert.ok(physical, "touch controls are clearly separated from keyboard keys");
    for (const label of physical[1].split("/")) assert.ok(expected[label] && s.api.keys[expected[label]] === action,
      "every advertised keyboard option maps to the real action");
    assert.ok(touch.some(button => button.label === physical[2] && button.action === action), "the advertised touch label maps to the real action");
  }
  return s;
}
check("keyboard and touch fallbacks match actual input metadata and fit the dialog", () => fallback());
check("connected pad labels use the same confirm/menu actions as the input translator", () => {
  const s = session({ pad: { confirm: "b", menu: "start" } }); assert.deepEqual(controls(s), ["B", "START"]);
  assert.deepEqual(s.labels, [{ action: "confirm", index: 7 }, { action: "menu", index: 7 }]);
  assert.equal(s.api.padMap.confirm, "a"); assert.equal(s.api.padMap.menu, "start");
});
check("maximum supported pad-label length and plus glyphs still fit", () => {
  const s = session({ pad: { confirm: "BUTTON01", menu: "A+B+C+D+" } }); assert.deepEqual(controls(s), ["BUTTON01", "A+B+C+D+"]);
});
for (const invalid of ["", "NINECHARS", "\u24b6", "<B>", "START MENU"]) check("invalid pad label falls back safely: " + JSON.stringify(invalid), () => {
  fallback(source, { confirm: invalid, menu: invalid });
});
check("the onboarding delay does not show dialog early and preserves the town arrival", () => {
  const s = session().start(); assert.equal(s.api.dialog(), null);
  assert.deepEqual(s.visits, [["existing-town", 11, 15, "up"]]); s.reveal(); assert.ok(s.api.dialog());
});
check("loaded tutorial preference off suppresses only the intro", () => {
  const s = session({ tips: false }).start(); assert.equal(s.timers.length, 0); assert.equal(s.api.dialog(), null);
  assert.deepEqual(s.visits, [["existing-town", 11, 15, "up"]]); assert.deepEqual(s.settingsReads, ["TipsTutorials"]);
});
for (const options of [{ tips: true }, { loaded: false, tips: false }, { noSettings: true }]) check("default tutorial availability " + JSON.stringify(options), () => {
  const s = session(options); controls(s); assert.equal(s.settingsReads.length, options.loaded === false || options.noSettings ? 0 : 1);
});
check("the actual authored Portal intro and profile spawn remain untouched", () => {
  const profile = { intro: portalIntro, start_spawn: { x: 5, y: 6 } }, before = JSON.stringify(profile);
  const s = session({ profile, pad: { confirm: "B", menu: "START" } }).start(), dialog = s.reveal();
  assert.deepEqual(Array.from(dialog.pages), portalIntro); assert.equal(JSON.stringify(profile), before);
  assert.deepEqual(s.visits, [["existing-town", 5, 6, "up"]]); assert.equal(dialog.voice, 0); assert.equal(dialog.then, null);
  assert.deepEqual(s.labels, [], "authored realm text does not evaluate default Prism control prompts");
});
check("controlled former logical-button-only intro fails the same physical-controls check", () => {
  const dynamic = /titlePrompt\("confirm", "Z\/SPACE OR TAP A"\)[\s\S]*?" FOR MENU\. THE ROAD SOUTH LEAVES TOWN\."/;
  assert.ok(dynamic.test(source), "existing default controls expression");
  const legacy = source.replace(dynamic, '"TALK TO PEOPLE WITH A. OPEN THE MENU WITH START. THE ROAD SOUTH LEAVES TOWN."');
  assert.throws(() => fallback(legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot, DOM or the game loop.
console.log("Prismheart intro control checks: " + checks + " passed; full inline script compiles.");
