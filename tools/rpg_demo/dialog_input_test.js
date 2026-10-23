// SPDX-License-Identifier: MIT
// DOM-free regression: node --max-old-space-size=128 tools/rpg_demo/dialog_input_test.js
// Actual dialog/inn/request callbacks and catalogs; persistent production hit edges, no browser/game loop/storage.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const party = data("party").party.prism.members, inn = data("interiors").interiors.prism.Inn;
const villager = data("prism-village").npcs.find(n => n.request);
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; };
const source = [line("const hit ="), line("const VOICE ="), line("function wakeAt("),
  between("function makeMember(", "/* Recruits:"), between("let dlg = null;", "function wrap("),
  between("function innPrompt(", "function openChest("), between("function villageRequest(", "function castLine("),
  between("const STATUS =", "/* ---------- bestiary"),
  "this.api = { makeMember, say, ask, dialogTick, innPrompt, villageRequest, dialog: () => dlg };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(productionSource = source) {
  const sounds = [], pressed = {}, c = {
    D: { interiors: { Inn: clone(inn) } }, START_LEVEL: 15, party: [], pressed, gold: 1000,
    bag: { [villager.request.item]: 1 }, state: { quests: {}, day: 1, minute: 480 }, B: null,
    fade: 0, fadeCb: null, saves: 0, map: { cue: "INN" },
    roster: () => c.party, sfx: sound => sounds.push(sound), cue() {}, toast() {},
    saveGame: () => { c.saves++; return true; }, saveSummary: () => "Fixture journey"
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = party.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  c.party[0].hp = 1; c.party[0].mp = 0; c.party[0].status = { poison: true };
  return { c, sounds, pressed, api: c.api,
    tick: (keys = [], dt = 0) => { keys.forEach(k => { pressed[k] = true; }); if (c.api.dialog()) c.api.dialogTick(dt); } };
}
const resources = s => JSON.stringify({ party: s.c.party, gold: s.c.gold, bag: s.c.bag, state: s.c.state, fade: s.c.fade, saves: s.c.saves });
function reveal(s) { const d = s.api.dialog(); d.shown = d.pages[d.i].length; }
function assertInnCancel(productionSource = source) {
  const s = session(productionSource); s.api.innPrompt(); reveal(s); const before = resources(s);
  s.tick(["a", "b"]); assert.equal(resources(s), before, "Back cannot charge/heal/save while Confirm is pressed");
  assert.match(s.api.dialog().pages[0], /COME BACK ANY TIME/); assert.equal(s.pressed.a, false); assert.equal(s.pressed.b, false);
  s.tick(); assert.equal(s.api.dialog().shown, 0, "closing choice cannot reveal its callback's new dialog"); return s;
}
function assertRevealWaits(productionSource = source) {
  const s = session(productionSource), choices = []; s.api.ask("QUESTION", ["YES", "NO"], index => choices.push(index));
  s.tick(["a", "b"]); assert.equal(s.api.dialog().shown, 8); s.tick();
  assert.deepEqual(choices, [], "revealing text cannot also choose/cancel next frame"); assert.ok(s.api.dialog().choice);
}
function assertOneAdvance(productionSource = source) {
  const s = session(productionSource); s.api.say(["FIRST", "N", "THIRD"]); reveal(s); s.tick(["a", "b"]);
  assert.equal(s.api.dialog().i, 1); s.tick([], 0.05); s.tick();
  assert.equal(s.api.dialog().i, 1, "a second buffered button cannot skip another completed page");
  assert.equal(s.pressed.a, false); assert.equal(s.pressed.b, false);
}
check("Back plus Confirm cancels a real inn transaction", () => assertInnCancel());
check("Back plus Confirm keeps a real village request item and reward unchanged", () => {
  const s = session(); s.api.villageRequest(clone(villager)); reveal(s); const before = resources(s);
  s.tick(["a", "b"]); assert.equal(resources(s), before); assert.match(s.api.dialog().pages[0], /I UNDERSTAND/);
  assert.equal(s.pressed.a, false); s.tick(); assert.equal(s.api.dialog().shown, 0);
});
check("normal Confirm still rests, charges once, and runs the inn's actual callback", () => {
  const s = session(); s.api.innPrompt(); reveal(s); s.tick(["a"]);
  assert.equal(s.c.gold, 1000 - inn.rest_price); assert.ok(s.c.party.every(m => m.hp === m.max && m.mp === m.mmax));
  assert.equal(s.c.party[0].status.poison, undefined); assert.equal(s.c.fade, 1);
  s.c.fadeCb(); assert.equal(s.c.saves, 1); assert.match(s.api.dialog().pages[0], /GOOD MORNING/);
});
check("normal Confirm still fulfills the real village request once", () => {
  const s = session(); s.api.villageRequest(clone(villager)); reveal(s); s.tick(["a"]);
  assert.equal(s.c.bag[villager.request.item], 0); assert.equal(s.c.gold, 1000 + villager.request.gold);
  assert.equal(s.c.state.quests[villager.request.id], true); s.tick(); assert.equal(s.c.gold, 1000 + villager.request.gold);
});
for (const options of [["YES", "NO"], ["GO", "NEXT"]]) for (const keys of [["b"], ["a", "b"]])
  check(options[1] + " retains callback index one for " + keys.join("+"), () => {
    const s = session(), choices = []; s.api.ask("QUESTION", options, index => choices.push(index)); reveal(s);
    s.tick(keys); assert.deepEqual(choices, [1]); assert.equal(s.api.dialog(), null);
  });
for (const index of [0, 1]) check("Confirm alone still selects question choice " + index, () => {
  const s = session(), choices = []; s.api.ask("QUESTION", ["YES", "NO"], value => choices.push(value)); reveal(s);
  if (index) s.tick(["down"]); s.tick(["a"]); assert.deepEqual(choices, [index]);
});
check("simultaneous reveal buttons wait for a fresh choice", () => assertRevealWaits());
check("simultaneous completed-page buttons advance exactly one page", () => assertOneAdvance());
for (const key of ["a", "b"]) check("a normal " + key + " advances a completed plain dialog", () => {
  const s = session(); s.api.say(["FIRST", "SECOND"]); reveal(s); s.tick([key]); assert.equal(s.api.dialog().i, 1);
});
check("last-page callback receives one transition without a second-button leak", () => {
  const s = session(); let callbacks = 0;
  s.api.say(["LAST"], () => { callbacks++; s.api.say(["FOLLOWUP"]); }); reveal(s); s.tick(["a", "b"]);
  s.tick([], 0.05); assert.equal(callbacks, 1); assert.equal(s.api.dialog().shown, 2.25, "callback dialog types normally");
  assert.equal(s.pressed.a, false); assert.equal(s.pressed.b, false);
});
check("B-only input retains the existing incomplete-text buffer behavior", () => {
  const s = session(); s.api.say(["HI", "NEXT"]); s.tick(["b"]); assert.equal(s.api.dialog().shown, 0);
  assert.equal(s.pressed.b, true); s.tick([], 0.05); assert.equal(s.api.dialog().i, 0); assert.equal(s.api.dialog().shown, 2);
  s.tick(); assert.equal(s.api.dialog().i, 1, "B still advances only after typewriter completion");
});
check("text speed, voice blip and Start handling remain unchanged", () => {
  const s = session(); s.api.say(["ABCDEF"], null, 9); s.tick([], 3 / 45);
  assert.equal(s.api.dialog().shown, 3); assert.ok(s.sounds.includes("BLIP:9")); reveal(s); s.tick(["start"]);
  assert.ok(s.api.dialog()); assert.equal(s.pressed.start, true, "dialog does not add a Start action");
});
check("controlled former choice priority fails the same inn transaction assertion", () => {
  const guard = '    if (hit("b")) { sfx("TICK"); const c = dlg.choice; hit("a"); dlg = null; c.cancel ? c.cancel() : c.then(1); return; }';
  assert.ok(source.includes(guard)); const confirm = source.match(/^    if \(hit\("a"\)\) \{ sfx\("PICK"\);[^\r\n]*$/m);
  assert.ok(confirm); const late = guard.replace('    if ', '    else if ').replace('hit("a"); ', "");
  const legacy = source.replace(guard, "").replace(confirm[0], confirm[0] + "\n" + late);
  assert.throws(() => assertInnCancel(legacy), assert.AssertionError);
});
check("controlled former reveal leaves the cancelled-choice edge detectable", () => {
  const revealLine = '    if (hit("a")) { dlg.shown = page.length; hit("b"); }'; assert.ok(source.includes(revealLine));
  const legacy = source.replace(revealLine, '    if (hit("a")) dlg.shown = page.length;');
  assert.throws(() => assertRevealWaits(legacy), assert.AssertionError);
});
check("controlled former plain advance fails the same adjacent-page assertion", () => {
  const consume = '  const confirm = hit("a"), back = hit("b");'; assert.ok(source.includes(consume));
  const legacy = source.replace(consume, "").replace("  if (confirm || back) {", '  if (hit("a") || hit("b")) {');
  assert.notEqual(legacy, source); assert.throws(() => assertOneAdvance(legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or DOM work.
console.log("Prismheart dialog input checks: " + checks + " passed; full inline script compiles.");
