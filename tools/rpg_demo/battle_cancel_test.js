// SPDX-License-Identifier: MIT
// Focused DOM-free check: node --max-old-space-size=128 tools/rpg_demo/battle_cancel_test.js
// Actual battle planning, logical button edges, frame expiry and authored party/item/spirit catalogs.
// Persistent edges span adjacent ticks; no browser, native runtime, game loop or builds are launched.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const members = data("party").party.prism, spells = data("spells").spells.filter(s => s.realm === "prism");
const Summons = require("./summons.js"), gear = {};
const bosses = data("prism-bosses").bosses.filter(b => ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "The Shattered Heart"].includes(b.dungeon));
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end, text = html) {
  const a = text.indexOf(start), b = text.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return text.slice(a, b);
}
function line(prefix) {
  const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found;
}
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [between("const LOGICAL =", "const KEYMAP ="), between("const hit =", "/* ---------- controllers:"),
  line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="),
  between("function makeMember(", "/* Recruits:"), line("const spellOf ="), line("const alive ="),
  between("const ITEM_KINDS =", "function menuTick()"), between("const STATUS =", "function roundStatuses()"),
  line("const CMDS ="), line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="),
  between("function nextChooser(", "function pop("),
  "function frameCleanup(now) {\n" + cleanup + "\n}",
  "this.api = { makeMember, battleTick, battleItems, battleItemStock, mySpirits, battleCmds, setHeld, menuRepeat, " +
  "frameCleanup, inputs: () => ({ pressed, held, pressedAt, SRC }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(productionSource = source, who = 1) {
  const sounds = [], notices = [], c = {
    D: { realm_key: "prism", party: clone(members), spells: clone(spells), dungeons: clone(bosses.map(b => ({ boss_data: b }))) },
    GEAR: clone(gear), party: [], reserve: [], bag: { "Herb Tonic": 1, "Clear Draught": 1, "Feather of Waking": 1 },
    state: { beaten: new Set(bosses.filter(b => b.shard).map(b => b.name)) },
    PrismSummons: Summons, window: { PrismSummons: Summons },
    W: 320, mode: "battle", dlg: null, fade: 0, now: 0, performance: { now: () => c.now },
    rnd: (a, b) => (a + b) / 2, clamp: (n, low, high) => Math.max(low, Math.min(high, n)),
    sfx: sound => sounds.push(sound), toast: (title, message) => notices.push([title, message]),
    doAction: () => { throw new Error("unexpected action execution while cancelling a command"); },
    endRound: () => { throw new Error("unexpected round completion while cancelling a command"); },
    finishBattle: () => { throw new Error("unexpected battle exit"); },
    B: { phase: "cmd", who, cmd: 0, target: 0, sub: null, list: [], acts: [], queue: [], oi: 0,
      t: 0, fx: null, pops: [], flash: {}, msg: "", round: 1, wait: 0, summoned: [],
      foes: [{ name: "Gale Harpy", hp: 100, max: 100, spd: 15, beh: "simple" },
        { name: "Storm Harpy", hp: 100, max: 100, spd: 16, beh: "simple" }] }
  };
  vm.createContext(c); vm.runInContext(productionSource, c, { timeout: 1000 });
  c.party = members.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  return { c, sounds, notices, api: c.api,
    tick: (...keys) => {
      c.now += 16;
      for (const key of keys) { c.api.inputs().pressed[key] = true; c.api.inputs().pressedAt[key] = c.now; }
      c.api.menuRepeat(c.now); c.api.battleTick(0.016); c.api.frameCleanup(c.now);
    } };
}
function chooseCommand(s, command) {
  s.c.B.cmd = s.api.battleCmds().indexOf(command); assert.ok(s.c.B.cmd >= 0, "actual command exists: " + command); s.tick("a");
}
function prepare(route, productionSource = source) {
  const s = session(productionSource);
  if (route.startsWith("target:")) {
    const kind = route.split(":")[1]; chooseCommand(s, kind.toUpperCase());
    if (kind === "magic") { s.c.B.oi = s.c.party[s.c.B.who].spells.indexOf("Mend"); assert.ok(s.c.B.oi >= 0); s.tick("a"); }
    if (kind === "item") { s.c.B.oi = s.api.battleItems().indexOf("Herb Tonic"); assert.ok(s.c.B.oi >= 0); s.tick("a"); }
    assert.equal(s.c.B.sub, "target");
  } else chooseCommand(s, route.toUpperCase());
  s.sounds.length = 0; return s;
}
const resources = s => JSON.stringify({ party: s.c.party, reserve: s.c.reserve, bag: s.c.bag, foes: s.c.B.foes, summoned: s.c.B.summoned });
const choice = s => JSON.stringify({ sub: s.c.B.sub, who: s.c.B.who, cmd: s.c.B.cmd, oi: s.c.B.oi, target: s.c.B.target,
  acts: s.c.B.acts, queue: s.c.B.queue, phase: s.c.B.phase, pending: s.c.B.pending });
function assertCancelled(route, productionSource = source, both = true) {
  const s = prepare(route, productionSource), original = resources(s), beforePlans = s.c.B.acts.slice(), who = s.c.B.who;
  const destination = route.startsWith("target:") ? route === "target:attack" ? null : route.split(":")[1] : null;
  s.tick(...(both ? ["a", "b"] : ["b"]));
  assert.equal(s.c.B.sub, destination); assert.equal(s.c.B.who, who); assert.deepEqual(s.c.B.acts, beforePlans);
  assert.equal(resources(s), original, "Back spends no resources and cannot target, summon or enqueue");
  assert.equal(s.api.inputs().pressed.a, false, "concurrent Confirm is consumed");
  const settled = choice(s); s.tick();
  assert.equal(choice(s), settled, "without a fresh edge the cancelled choice stays cancelled on the next tick");
  assert.equal(resources(s), original); assert.ok(s.sounds.every(sound => sound === "TICK")); return s;
}
for (const route of ["target:attack", "target:magic", "target:item", "summon", "magic", "item"])
  check("Back+A cancels " + route + " without a delayed command", () => assertCancelled(route));
for (const route of ["target:attack", "target:magic", "target:item", "summon", "magic", "item"])
  check("Back alone retains the existing " + route + " destination", () => assertCancelled(route, source, false));
function assertEmptyOptions(route, productionSource = source) {
  const s = session(productionSource);
  // An existing first-hero item plan is the reservation authority. Corin in the second
  // roster slot supplies the actual no-spells case; exhausted options must not turn Back
  // into an unintended previous-hero cancellation on the next tick.
  [s.c.party[0], s.c.party[1]] = [s.c.party[1], s.c.party[0]];
  s.c.B.acts = [{ kind: "item", who: s.c.party[0], item: "Herb Tonic", target: s.c.party[0] }];
  if (route === "item") s.c.bag = { "Herb Tonic": 1 };
  if (route === "summon") s.c.state.beaten.clear();
  s.c.B.sub = route; s.c.B.cmd = route === "summon" ? 5 : s.api.battleCmds().indexOf(route.toUpperCase());
  if (route === "magic") assert.equal(s.c.party[1].spells.length, 0);
  if (route === "item") assert.equal(s.api.battleItems().length, 0);
  if (route === "summon") assert.equal(s.api.mySpirits().length, 0);
  assert.equal(s.api.battleItemStock("Herb Tonic"), 0);
  const original = resources(s), prior = s.c.B.acts[0]; s.tick("a", "b");
  assert.equal(s.c.B.sub, null); assert.equal(s.c.B.who, 1); assert.equal(s.c.B.acts[0], prior); assert.equal(s.c.B.acts.length, 1);
  assert.equal(resources(s), original); assert.equal(s.api.inputs().pressed.a, false); assert.equal(s.api.inputs().pressed.b, false);
  const settled = choice(s); s.tick(); assert.equal(choice(s), settled, "empty-list Back cannot pop the prior hero next tick");
  assert.equal(s.api.battleItemStock("Herb Tonic"), 0); assert.ok(s.sounds.every(sound => sound === "TICK"));
}
for (const route of ["magic", "item", "summon"])
  check("Back+A exits empty " + route + " options without releasing a previous hero's item plan", () => assertEmptyOptions(route));
function assertPriorReservation(productionSource = source) {
  const s = session(productionSource, 0); chooseCommand(s, "ITEM");
  s.c.B.oi = s.api.battleItems().indexOf("Herb Tonic"); s.tick("a"); s.tick("a");
  assert.equal(s.c.B.who, 1); assert.equal(s.c.B.acts.length, 1); assert.equal(s.api.battleItemStock("Herb Tonic"), 0);
  const original = resources(s); s.tick("a", "b");
  assert.equal(s.c.B.who, 0); assert.equal(s.c.B.sub, null); assert.equal(s.c.B.acts.length, 0);
  assert.equal(s.api.battleItemStock("Herb Tonic"), 1, "popping the prior action releases its reservation");
  assert.equal(resources(s), original, "reservation release changes no physical inventory or MP");
  assert.equal(s.api.inputs().pressed.a, false);
  const settled = choice(s); s.tick(); assert.equal(choice(s), settled, "the cancelled prior hero does not choose again automatically");
  return s;
}
check("previous-hero Back+A releases the queued item reservation without a replacement action", () => assertPriorReservation());
function assertFirstHero(productionSource = source) {
  const s = session(productionSource, 0), original = resources(s); s.tick("a", "b");
  assert.equal(s.c.B.sub, null); assert.equal(s.c.B.who, 0); assert.equal(s.c.B.acts.length, 0);
  assert.equal(resources(s), original); assert.equal(s.api.inputs().pressed.a, false);
  const settled = choice(s); s.tick(); assert.equal(choice(s), settled); return s;
}
check("first-hero Back+A cancels Confirm even when there is no earlier plan", () => assertFirstHero());
for (const kind of ["attack", "magic", "item"]) check("normal " + kind + " target Confirm still queues exactly once", () => {
  const s = prepare("target:" + kind), original = resources(s), actor = s.c.party[s.c.B.who], target = s.c.B.list[0];
  s.tick("a"); assert.equal(s.c.B.acts.length, 1); assert.equal(s.c.B.acts[0].kind, kind);
  assert.equal(s.c.B.acts[0].who, actor); assert.equal(s.c.B.acts[0].target, target); assert.equal(resources(s), original);
  assert.equal(s.c.B.who, 2); s.tick(); assert.equal(s.c.B.acts.length, 1); assert.equal(s.c.B.sub, null);
  if (kind === "item") assert.equal(s.api.battleItemStock("Herb Tonic"), 0);
});
check("normal summon Confirm still plans the actual unlocked spirit without spending early", () => {
  const s = prepare("summon"), original = resources(s), spirit = s.api.mySpirits()[0];
  assert.ok(spirit && spirit.mp <= s.c.party[1].mp); s.tick("a");
  assert.equal(s.c.B.acts.length, 1); assert.equal(s.c.B.acts[0].kind, "summon"); assert.equal(s.c.B.acts[0].spirit.name, spirit.name);
  assert.equal(resources(s), original); s.tick(); assert.equal(s.c.B.acts.length, 1);
});
check("a cancelled submenu accepts a fresh released/new Confirm while held sources stay held", () => {
  const s = prepare("magic"); s.api.setHeld("kb", "a", true); s.api.setHeld("kb", "b", true); s.tick();
  assert.equal(s.c.B.sub, null); assert.equal(s.api.inputs().held.a, true); assert.equal(s.api.inputs().held.b, true);
  s.tick(); assert.equal(s.c.B.sub, null);
  s.api.setHeld("kb", "a", false); s.api.setHeld("kb", "b", false); s.api.setHeld("kb", "a", true); s.tick();
  assert.equal(s.c.B.sub, "magic");
});
check("ordinary direction navigation and held direction repeat retain their existing behavior", () => {
  const s = prepare("target:attack"); s.tick("right"); assert.equal(s.c.B.target, 1); s.tick(); assert.equal(s.c.B.target, 1);
  s.api.setHeld("kb", "left", true); s.tick(); assert.equal(s.c.B.target, 0);
  s.c.now += 400; s.tick(); assert.equal(s.c.B.target, 1, "held direction repeats after its original delay");
  s.api.setHeld("kb", "left", false);
});
check("Start remains unassigned in battle choices and retains the existing bounded buffer", () => {
  const s = prepare("magic"), original = choice(s); s.tick("start"); assert.equal(choice(s), original);
  assert.equal(s.api.inputs().pressed.start, true); s.tick("a", "b"); assert.equal(s.c.B.sub, null);
  assert.equal(s.api.inputs().pressed.start, true, "cancelling Confirm does not add a Start action");
  for (let i = 0; i < 10; i++) s.tick(); assert.equal(s.api.inputs().pressed.start, false, "existing 150ms expiry still clears unused Start");
});
function removeBackDrain(route) {
  const bounds = route.startsWith("target:") ? ['    if (B.sub === "target")', '    if (B.sub === "summon")']
    : route === "summon" ? ['    if (B.sub === "summon")', '    if (B.sub === "magic" || B.sub === "item")']
    : ['    if (B.sub === "magic" || B.sub === "item")', '    const cmds = battleCmds();'];
  const block = between(...bounds, source), guard = block.match(/^      if \(hit\("b"\)\) \{[^\r\n]*\}\r?$/m);
  assert.ok(guard && guard[0].includes('hit("a");'), "actual Back guard drains Confirm for " + route);
  return source.replace(block, block.replace(guard[0], guard[0].replace('hit("a"); ', "")));
}
for (const route of ["target:attack", "target:magic", "target:item", "summon", "magic", "item"])
  check("controlled legacy " + route + " Back leaves a detectable next-tick Confirm", () =>
    assert.throws(() => assertCancelled(route, removeBackDrain(route)), assert.AssertionError));
for (const route of ["magic", "item", "summon"]) check("controlled Back after " + route + " validation leaves the prior-plan leak detectable", () => {
  const bounds = route === "summon" ? ['    if (B.sub === "summon")', '    if (B.sub === "magic" || B.sub === "item")']
    : ['    if (B.sub === "magic" || B.sub === "item")', '    const cmds = battleCmds();'];
  const block = between(...bounds, source), guard = block.match(/^      if \(hit\("b"\)\) \{[^\r\n]*\}\r?$/m);
  assert.ok(guard); const rest = block.replace(guard[0], ""), at = rest.indexOf('      if (hit("a"))'); assert.ok(at >= 0);
  const legacy = source.replace(block, rest.slice(0, at) + guard[0] + "\n" + rest.slice(at));
  assert.throws(() => assertEmptyOptions(route, legacy), assert.AssertionError);
});
check("controlled original previous/first-hero guards reproduce the unwanted selection", () => {
  const block = between('    const cmds = battleCmds();', '    if (hit("a")) {', source);
  const at = block.indexOf('    if (hit("b"))'); assert.ok(at >= 0, "explicit command Back guard exists");
  const legacy = source.replace(block, block.slice(0, at) + '    if (hit("b") && B.acts.length) { const last = B.acts.pop(); B.who = party.indexOf(last.who); sfx("TICK"); return; }\n');
  assert.throws(() => assertPriorReservation(legacy), assert.AssertionError);
  assert.throws(() => assertFirstHero(legacy), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline);
new vm.Script(inline[1], { filename: "index.html:inline" }); // Compile only; never execute boot or DOM work.
console.log("Prismheart battle cancel checks: " + checks + " passed; full inline script compiles.");
