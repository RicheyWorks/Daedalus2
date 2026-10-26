// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/battle_stolen_gold_cue_test.js
// Actual theft/settlement/choice/painter excerpts; canonical plains formations and Grass/Flowers metadata.
// Finite controlled rolls and explicit 112px atlas rectangles are diagnostic peers, not route/full-fight acceptance.
// Portal uses a Prism-foe guard probe; dual CHARGED+STOLEN and one long spell-hint peer are synthetic.
// No DOM/browser/audio/native storage/build/full-IIFE execution.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x)), parties = data("party").party, catalog = data("spells").spells;
const types = data("prism-bestiary").types, zones = data("prism-encounters").zones, world = data("worldmap-tiles");
const byKey = Object.fromEntries(types.map(f => [f.key, f]));
const layouts = zones.plains.formations.filter(f => f.enemies.some(k => byKey[k].behaviour === "steal"));
const first = layouts.find(f => f.enemies.length === 4 && f.enemies.every(k => k === "prism_best_cutthroat")); assert.ok(first);
const gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("const hit ="), line("const rnd ="), line("const ri ="),
  between("function makeMember(", "/* Recruits:"), between("const atkOf =", "/* ---------- maps"), between("const ITEM_KINDS =", "const fieldSpells ="),
  between("const STATUS =", "/* ---------- bestiary:"), line("const beastKey ="), line("function meet("), line("function fell("),
  between("function passTime(", "function wakeAt("), between("function pickFormation(", "const ELEM ="), line("const ELEM ="), line("const CMDS ="), line("const SUMMONS ="), line("const mySpirits ="), line("const battleCmds ="),
  between("function nextChooser(", "function bossGate("), line("function wrap("), between("function spellHint(", "/* ---------- title:"), between("function titlePrompt(", "function drawTitle("),
  "function cleanup(now){\n" + cleanup + "\n}",
  "doAction=watch('doAction',doAction);foeTurn=watch('foeTurn',foeTurn);hurtFoe=watch('hurtFoe',hurtFoe);recoverStolenGold=watch('recoverStolenGold',recoverStolenGold);endRound=watch('endRound',endRound);finishBattle=watch('finishBattle',finishBattle);",
  "this.api={makeMember,pickFormation,startBattle,battleTick,advanceChooser,doAction,foeTurn,foeHit,hurtFoe,recoverStolenGold,endRound,finishBattle,drawBattle,drawBattleTarget,drawStolenBadge,tags,inflict,cure,roundStatuses,cleanup,battleItems,battleItemStock,battleCmds,spellOf,spellHint,wrap,chars:CHARS,statuses:STATUS};"
].join("\n");
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", production = source) {
  const paints = [], sounds = [], pressed = {}, pressedAt = {}, rolls = [], calls = { rng: 0, storage: 0 };
  const math = Object.create(Math); math.random = () => { calls.rng++; assert.ok(rolls.length, "unexpected RNG: no AI/refund/action may run while painting"); return rolls.shift(); };
  const known = new Set(parties[realm].members.flatMap(m => m.spells)), rects = {};
  types.forEach((f, i) => { rects["Foe_" + f.key] = [i * 128, 0, 112, 112]; });
  parties[realm].members.forEach((m, i) => { rects["Party_" + m.job] = [i * 128, 128, 112, 112]; });
  const c = { W: width, H: 224, D: { realm_key: realm, realm_profile: realm === "portal" ? { start_level: 1 } : null, party: clone(parties[realm]),
      spells: clone(catalog.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), foes: clone(byKey), zones: clone(zones), dungeons: [],
      backdrop_for_zone: { plains: "field-peer" }, rects: { sprites: rects, spells: {}, backdrops: { "field-peer": [0, 0, 320, 180] } } },
    GEAR: clone(gear), party: [], reserve: [], bag: { "Herb Tonic": 2, "Feather of Waking": 1, "Smoke Pouch": 1 }, gold: 237,
    state: { beaten: new Set(), seen: {}, sinceBattle: 11, day: 1, minute: 480 }, map: { kind: "world", cue: "FIELD" },
    B: null, mode: "field", goT: 0, fade: 0, fadeCb: null, settingsFramePaused: true, now: 0, pressed, pressedAt,
    window: {}, PAD: null, Math: math, IM: { backdrops: "backdrop-peer", spells: "spell-atlas-peer" }, performance: { now: () => 0 },
    painting: false, watch(name, fn) { return (...args) => { assert.equal(c.painting, false, "painter called " + name); calls[name] = (calls[name] || 0) + 1; return fn(...args); }; },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), cue() {}, sfx: value => sounds.push(value), toast() {},
    saveGame() { calls.storage++; throw new Error("stolen cue cannot save"); },
    localStorage: Object.fromEntries(["getItem", "setItem", "removeItem"].map(k => [k, () => { calls.storage++; throw new Error("stolen cue cannot access native storage"); }])),
    spr(sheet, name, x, y, sx, sw, sh, scale = 1) { const r = c.D.rects.sprites[name]; assert.ok(r, name); paints.push({ kind: "sprite", name, x, y, w: (sw || r[2]) * scale, h: (sh || r[3]) * scale }); },
    cursor(x, y) { paints.push({ kind: "cursor", x, y, w: 8, h: 8 }); },
    gauge(x, y, w, fraction, color) { paints.push({ kind: "gauge", x, y, w, h: 5, fraction, color }); },
    win(x, y, w, h) { paints.push({ kind: "window", x, y, w, h }); }, tw: value => String(value).length * 6,
    text(value, x, y, color = "#ffffff", shadow = "#202040") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color, shadow }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); }, drawImage(image, sx, sy, sw, sh, x, y, w, h) { paints.push({ kind: "image", image, x, y, w, h }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  const resources = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold, state: { ...c.state, beaten: [...c.state.beaten] } });
  const snapshot = () => JSON.stringify({ resources: resources(), D: c.D, map: c.map, B: c.B, mode: c.mode, goT: c.goT, fade: c.fade, pressed, pressedAt, now: c.now, calls, sounds, rolls });
  const s = { c, api: c.api, paints, sounds, pressed, calls, resources,
    rolls(...values) { assert.equal(rolls.length, 0, "previous controlled rolls not consumed"); rolls.push(...values); },
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.battleTick(0); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = snapshot(); c.painting = true; try { c.api.drawBattle(); } finally { c.painting = false; } assert.equal(snapshot(), before, "paint changed ledger/refund/actions/AI/input/resources/RNG/storage"); return paints; },
    start(layout = first) { c.api.startBattle("plains", null, layout.enemies); c.fadeCb(); s.tick("a"); c.fade = 0; assert.equal(c.B.phase, "cmd"); return s; },
    labels() { c.PAD = { devices: () => [{ index: 0 }], label: a => ({ confirm: "ABCDEFGH", cancel: "IJKLMNOP" })[a] }; }
  };
  return s.start();
}
const at = (s, y, x) => s.paints.filter(p => p.kind === "text" && p.y === y && (x === undefined || p.x === x));
const progress = s => JSON.stringify({ party: s.c.party.map(m => ({ lv: m.lv, exp: m.exp, next: m.next })), reserve: s.c.reserve });
const intersects = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
function steal(s, thief = s.c.B.foes[0]) {
  assert.equal(thief.beh, "steal"); const before = s.c.gold, held = thief.stolen || 0, rng = s.calls.rng;
  s.rolls(0, 0.5, 0.5, 0.1); s.api.doAction({ kind: "foe", who: thief });
  const amount = before - s.c.gold; assert.equal(amount, Math.min(before, 4 + Math.round(thief.atk / 2))); assert.ok(amount > 0); assert.equal(thief.stolen, held + amount); assert.equal(s.calls.rng - rng, 4); assert.match(s.c.B.msg, /SNATCHES .* GOLD/); return amount;
}
function command(s, name) { assert.equal(s.c.B.sub, null); const cmds = Array.from(s.api.battleCmds()), index = cmds.indexOf(name); assert.ok(index >= 0); for (let i = 0; s.c.B.cmd !== index && i < cmds.length; i++) s.tick("down"); s.tick("a"); }
function chooseSpell(s, name) { command(s, "MAGIC"); const list = s.c.party[s.c.B.who].spells.map(s.api.spellOf).filter(Boolean), index = list.findIndex(sp => sp.name === name); assert.ok(index >= 0); for (let i = 0; i < index; i++) s.tick("down"); s.tick("a"); }
function backing(s, label) { const text = s.paints.find(p => p.kind === "text" && p.label === label); return text && s.paints.find(p => p.kind === "rect" && p.color === "#101526" && p.x === text.x - 3 && p.y === text.y - 1 && p.w === 48 && p.h === 9); }
function stolenBadges(s) { return s.paints.filter(p => p.kind === "text" && p.label === "STOLEN"); }
function assertBadge(s, f) {
  const stacks = (s.api.tags(f).length ? 1 : 0) + (f.charged ? 1 : 0), x = Math.round(Math.max(0, Math.min(s.c.W - 48, f.x + f.size / 2 - 24))), y = Math.round(f.y + f.size - 7 - stacks * 11);
  const word = stolenBadges(s).find(p => p.x === x + 3 && p.y === y + 1); assert.ok(word, f.name + " live ledger " + f.stolen); assert.equal(word.shadow, null); assert.equal(word.color, "#f8d878");
  const rect = s.paints.find(p => p.kind === "rect" && p.color === "#101526" && p.x === x && p.y === y && p.w === 48 && p.h === 9); assert.ok(rect); assert.ok(word.x + word.w <= x + 48); assert.ok(y >= 0 && y + 9 <= 144);
  const lastArt = Math.max(...s.paints.map((p, i) => p.kind === "sprite" || p.kind === "image" ? i : -1)), firstWindow = s.paints.findIndex(p => p.kind === "window"); assert.ok(s.paints.indexOf(rect) > lastArt && s.paints.indexOf(rect) < firstWindow);
  return rect;
}
function bounds(s) { for (const p of s.paints) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function card(s, expected) { const row = at(s, 174, 6)[0], split = s.c.W < 320 ? 120 : 150; assert.equal(row.label, expected); const result = s.paints.filter(p => p.kind === "text" && p.x === 6 && p.y >= 152); result.forEach(p => assert.ok(p.x + p.w <= split - 6 && p.y + p.h <= 224, JSON.stringify(p))); return result; }
check("Grass and Flowers both project to plains, whose weighted table includes real duplicate Cutthroats", () => {
  for (const tile of ["Grass", "Flowers"]) { const metadata = world.tiles.find(t => t.realm === "prism" && t.tile === tile); assert.ok(metadata); assert.equal(metadata.encounter_zone, "plains"); assert.ok(world.demo_maps.prism.some(row => row.includes(tile))); }
  const s = session(), index = zones.plains.formations.indexOf(first), total = zones.plains.formations.reduce((sum, f) => sum + f.weight, 0), before = zones.plains.formations.slice(0, index).reduce((sum, f) => sum + f.weight, 0);
  s.rolls((before + first.weight / 2) / total); assert.deepEqual(Array.from(s.api.pickFormation("plains")), first.enemies); assert.ok(layouts.every(f => f.enemies.length <= 4));
});
check("actual repeated theft grows each same-name holder's own live ledger and paint never refunds it", () => {
  const s = session(), original = s.c.gold, [a, b] = s.c.B.foes, firstAmount = steal(s, a), secondAmount = steal(s, a), otherAmount = steal(s, b);
  assert.equal(a.name, b.name); assert.notEqual(a, b); assert.equal(a.stolen, firstAmount + secondAmount); assert.equal(b.stolen, otherAmount); assert.equal(s.c.gold, original - a.stolen - b.stolen); assert.equal(s.api.recoverStolenGold(), 0);
  s.c.B.pops = []; s.draw(); assert.equal(stolenBadges(s).length, 2); assertBadge(s, a); assertBadge(s, b); const before = s.resources(); s.draw(); assert.equal(s.resources(), before); assert.equal(s.calls.storage, 0);
  // Direct turn/painter seams model the next updated ledger without running a whole round or caching a menu snapshot.
  command(s, "ATTACK"); s.draw(); card(s, "1/4 STOLEN " + a.stolen + "G"); steal(s, a); s.c.B.pops = []; s.draw(); card(s, "1/4 STOLEN " + a.stolen + "G");
});
check("final hurtFoe death returns that holder exactly once, removes its cue and leaves another live ledger", () => {
  const s = session(), original = s.c.gold, [a, b] = s.c.B.foes, returned = steal(s, a), held = steal(s, b), xp = progress(s);
  s.api.hurtFoe(a, a.hp); assert.equal(a.hp, 0); assert.equal(a.stolen, 0); assert.equal(s.c.gold, original - held); assert.equal(s.c.B.recoveredGold, returned); assert.equal(progress(s), xp);
  s.api.hurtFoe(a, 0); assert.equal(s.api.recoverStolenGold(), 0); assert.equal(s.c.gold, original - held); s.c.B.pops = []; s.draw(); assert.equal(stolenBadges(s).length, 1); assertBadge(s, b); assert.equal(b.stolen, held);
});
check("a real poison round tick settles a dead holder before the next choice; victory only adds ordinary loot", () => {
  const s = session(), original = s.c.gold, f = s.c.B.foes[0], amount = steal(s, f); s.api.hurtFoe(f, f.hp - 1); s.api.inflict(f, "poison"); const xp = progress(s);
  s.api.endRound(); assert.equal(f.hp, 0); assert.equal(f.stolen, 0); assert.equal(s.c.gold, original); assert.equal(s.c.B.recoveredGold, amount); assert.equal(progress(s), xp); assert.equal(s.c.B.phase, "cmd"); s.c.B.pops = []; s.draw(); assert.equal(stolenBadges(s).length, 0);
  s.api.endRound(); assert.equal(s.c.gold, original); const ordinary = s.c.B.foes.reduce((sum, foe) => sum + foe.gold, 0); s.c.B.foes.forEach(foe => { if (foe.hp > 0) s.api.hurtFoe(foe, foe.hp); }); s.api.endRound(); assert.equal(s.c.gold, original + ordinary); assert.equal(s.c.B.result, "win"); assert.ok(s.c.B.endLines.includes("YOU TAKE BACK " + amount + " STOLEN GOLD.")); assert.equal(s.api.recoverStolenGold(), 0);
});
check("RUN and Smoke retain living theft losses and prior refunds without EXP or ordinary gold rewards", () => {
  for (const kind of ["run", "smoke"]) { const s = session(), original = s.c.gold, [a, b] = s.c.B.foes; steal(s, a); const held = steal(s, b); s.api.hurtFoe(a, a.hp); const gold = s.c.gold, xp = progress(s), smoke = s.c.bag["Smoke Pouch"];
    if (kind === "run") { s.rolls(0.1); s.api.doAction({ kind: "run", who: s.c.party[0] }); } else s.api.doAction({ kind: "item", who: s.c.party[0], item: "Smoke Pouch", target: null });
    assert.equal(s.c.B.result, "run"); assert.equal(s.c.B.phase, "end"); assert.equal(s.c.gold, original - held); assert.equal(s.c.gold, gold); assert.equal(progress(s), xp); assert.equal(s.c.bag["Smoke Pouch"], smoke - (kind === "smoke" ? 1 : 0)); s.api.finishBattle(); s.c.fadeCb(); assert.equal(s.c.B, null); assert.equal(s.c.mode, "field"); assert.equal(s.c.gold, gold); assert.equal(progress(s), xp); assert.equal(s.calls.storage, 0); }
});
check("defeat settles an already dead ledger, leaves live theft lost and grants no victory payment", () => {
  const s = session(), original = s.c.gold, [dead, live] = s.c.B.foes; const returned = steal(s, dead), held = steal(s, live), xp = progress(s); dead.hp = 0; s.c.party.forEach(m => { m.hp = 0; });
  s.api.endRound(); assert.equal(dead.stolen, 0); assert.equal(live.stolen, held); assert.equal(s.c.B.recoveredGold, returned); assert.equal(s.c.gold, original - held); assert.equal(s.c.B.result, "lose"); assert.equal(progress(s), xp); s.api.finishBattle(); assert.equal(s.c.B, null); assert.equal(s.c.mode, "gameover"); assert.equal(s.c.gold, original - held); assert.equal(s.calls.storage, 0);
});
for (const width of [320, 256]) check("all canonical plains thief layouts keep live STOLEN after all art/effects and clear of HUD at " + width, () => {
  const s = session(width);
  for (const layout of layouts) { s.start(layout); s.c.B.foes.forEach((f, i) => { if (f.beh === "steal") f.stolen = 12 + i; if (i % 3 === 1) f.status = { poison: true }; if (i % 3 === 2) f.status = { sleep: 3, blind: 4 }; });
    const sp = s.api.spellOf("Ember"); s.c.D.rects.spells["fx:" + sp.name] = [0, 0, 480, 48]; s.c.B.fx = { name: sp.name, t: 0.2, targets: [s.c.B.foes.at(-1)] }; s.draw(); bounds(s);
    const expected = s.c.B.foes.filter(f => f.stolen > 0); assert.equal(stolenBadges(s).length, expected.length); const marked = expected.map(f => assertBadge(s, f)); for (let i = 0; i < marked.length; i++) for (let j = i + 1; j < marked.length; j++) assert.ok(!intersects(marked[i], marked[j])); assert.deepEqual(at(s, 147).map(p => p.label), ["PARTY", "HP", "MP"]); }
});
check("every canonical status rotates independently and synthetic charge+theft stacks three distinct readable rows", () => {
  for (const width of [320, 256]) { const s = session(width), f = s.c.B.foes[0]; f.stolen = 12;
    for (const key of Object.keys(s.api.statuses)) { f.status = { [key]: 3 }; s.draw(); const stolen = assertBadge(s, f), status = s.paints.find(p => p.kind === "rect" && p.w === 24 && p.h === 9 && p.x === f.x + f.size / 2 - 12); assert.ok(status); assert.equal(status.y - stolen.y, 11); }
    // Ordinary catalog thieves do not charge; this explicit robustness witness only proves composable drawing.
    f.charged = true; f.status = { poison: true, sleep: 3, blind: 4 }; const rotated = [];
    for (const time of [0, 1.2, 2.4]) { s.c.B.t = time; s.draw(); bounds(s); const stolen = assertBadge(s, f), charged = backing(s, "CHARGED"), status = s.paints.find(p => p.kind === "rect" && p.w === 24 && p.h === 9 && p.x === f.x + f.size / 2 - 12); assert.ok(charged && status); assert.equal(charged.y - stolen.y, 11); assert.equal(status.y - charged.y, 11); assert.ok(!intersects(stolen, charged) && !intersects(charged, status)); rotated.push(s.paints.find(p => p.kind === "text" && p.x === status.x + 3 && p.y === status.y + 1).label); }
    assert.deepEqual(rotated, ["PSN", "SLP", "BLN"]); assert.equal(f.stolen, 12); }
});
check("zero ledger/dead flash/Portal suppress cues, while an uncharged positive holder remains visible", () => {
  const s = session(), f = s.c.B.foes[0]; f.stolen = 0; s.draw(); assert.equal(stolenBadges(s).length, 0); delete f.charged; f.stolen = 12; s.draw(); assertBadge(s, f); assert.ok(!s.paints.some(p => p.kind === "text" && p.label === "CHARGED"));
  f.hp = 0; s.c.B.flash[f.key + f.x] = 0.2; s.draw(); assert.equal(stolenBadges(s).length, 0); assert.ok(s.paints.some(p => p.kind === "sprite" && p.name === f.img && p.x === f.x)); assert.equal(f.stolen, 12, "paint never settles a stale dead ledger");
  const p = session(256, "portal"); p.c.B.foes[0].stolen = 12; p.draw(); assert.equal(stolenBadges(p).length, 0); command(p, "ATTACK"); p.draw(); assert.equal(at(p, 174, 6).length, 0); assert.ok(!p.paints.some(t => t.kind === "text" && /STOLEN|RECLAIM/.test(t.label)));
});
for (const width of [320, 256]) check("selected same-name holder amounts and bounded caps stay exact through choose/undo at " + width, () => {
  const s = session(width), [a, b] = s.c.B.foes; steal(s, a); steal(s, a); steal(s, b); s.c.B.pops = []; s.labels(); const before = s.resources(); command(s, "ATTACK"); s.draw(); let facts = card(s, "1/4 STOLEN " + a.stolen + "G"); assert.ok(facts.some(p => p.y === 184 && p.label === "DEFEAT TO RECLAIM"));
  s.tick("right"); assert.equal(s.c.B.list[s.c.B.target], b); s.draw(); card(s, "2/4 STOLEN " + b.stolen + "G"); assert.ok(s.paints.some(p => p.kind === "cursor" && p.x === b.x - 10)); assert.equal(a.name, b.name); s.tick("a"); assert.equal(s.c.B.acts[0].target, b); assert.equal(s.resources(), before); s.tick("b"); assert.equal(s.c.B.acts.length, 0); assert.equal(s.c.B.who, 0); assert.equal(s.resources(), before);
  command(s, "ATTACK"); for (const amount of [999, 1000, Number.MAX_SAFE_INTEGER]) { a.stolen = amount; s.draw(); bounds(s); facts = card(s, "1/4 STOLEN " + (amount > 999 ? "999+" : amount) + "G"); assert.equal(a.stolen, amount); assert.ok(facts.every(p => !/\bHP\b|\bMP\b|\bATK\b|\bDEF\b/.test(p.label))); }
  // Metadata sentinels distinguish the held ledger from ordinary loot and combat stats; no mechanics execute here.
  a.gold = 730319; a.atk = 730323; a.def = 730325; s.draw(); facts = card(s, "1/4 STOLEN 999+G"); assert.ok(!facts.some(p => /7303/.test(p.label))); assert.equal(at(s, 204, 6)[0].label, "ABCDEFGH: CHOOSE"); assert.equal(at(s, 214, 6)[0].label, "IJKLMNOP: BACK");
});
check("canonical magic facts and a synthetic two-line wrap survive; ally/item facts/cancel reservations stay intact", () => {
  for (const width of [320, 256]) { const s = session(width), thief = s.c.B.foes[0]; steal(s, thief); s.c.B.pops = []; const before = s.resources();
    // Direct pending-card setup uses canonical runtime spells; none of their current enemy hints needs two lines.
    command(s, "ATTACK"); const candidates = s.c.D.spells.filter(sp => sp.target === "enemy"), observed = new Set();
    for (const sp of candidates) { s.c.B.pending = { kind: "magic", who: s.c.party[2], spell: sp }; s.draw(); const count = s.api.wrap(s.api.spellHint(sp), width < 320 ? 18 : 23).slice(0, 2); count.forEach((label, i) => assert.equal(at(s, 184 + i * 10, 6)[0].label, label)); observed.add(count.length); const tips = s.paints.filter(p => p.kind === "text" && p.label === "DEFEAT TO RECLAIM"); assert.equal(tips.length, count.length < 2 ? 1 : 0); card(s, "1/4 STOLEN " + thief.stolen + "G"); }
    assert.deepEqual([...observed], [1]);
    // Explicit long-element presentation peer, not an authored spell/cast/ordinary reachability claim.
    const long = { ...s.api.spellOf("Siphon"), element: "FIRE AND LIGHTNING" }; s.c.B.pending = { kind: "magic", who: s.c.party[2], spell: long }; s.draw(); const two = s.api.wrap(s.api.spellHint(long), width < 320 ? 18 : 23).slice(0, 2); assert.equal(two.length, 2); two.forEach((label, i) => assert.equal(at(s, 184 + i * 10, 6)[0].label, label)); assert.ok(!s.paints.some(p => p.kind === "text" && p.label === "DEFEAT TO RECLAIM")); card(s, "1/4 STOLEN " + thief.stolen + "G");
    s.c.B.pending = { kind: "attack", who: s.c.party[0] }; s.tick("b", "a"); assert.equal(s.c.B.sub, null); assert.equal(!!s.pressed.a, false); s.tick(); assert.equal(s.c.B.acts.length, 0);
    command(s, "DEFEND"); chooseSpell(s, "Mend"); s.draw(); card(s, "TARGET 1/4"); assert.equal(at(s, 184, 6)[0].label, "HP " + s.c.party[0].hp + "/" + s.c.party[0].max); assert.equal(at(s, 194, 6)[0].label, "MP " + s.c.party[0].mp + "/" + s.c.party[0].mmax); assert.ok(!s.paints.some(p => p.kind === "text" && p.label === "DEFEAT TO RECLAIM")); s.tick("b", "a"); assert.equal(s.c.B.sub, "magic"); s.tick("b");
    command(s, "ITEM"); s.tick("a"); const item = s.c.B.pending.item; s.draw(); card(s, "TARGET 1/4"); s.tick("a"); const reserved = s.api.battleItemStock(item); s.tick("b"); assert.equal(s.api.battleItemStock(item), reserved + 1); assert.equal(s.resources(), before); }
});
check("controlled missing-badge and wrong-ledger variants fail these visible invariants", () => {
  const call = "    drawStolenBadge(f, (ft.length ? 1 : 0) + (f.charged ? 1 : 0));"; assert.ok(source.includes(call)); const old = session(320, "prism", source.replace(call, "")); const f = old.c.B.foes[0]; f.stolen = 12; old.draw(); assert.throws(() => assertBadge(old, f), assert.AssertionError);
  const amount = '(target.stolen > 999 ? "999+" : target.stolen)'; assert.ok(source.includes(amount)); const wrong = session(256, "prism", source.replace(amount, '(target.gold > 999 ? "999+" : target.gold)')); wrong.c.B.foes[0].stolen = 12; command(wrong, "ATTACK"); wrong.draw(); assert.throws(() => card(wrong, "1/4 STOLEN 12G"), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline (compile only)" });
console.log("battle stolen gold cue: " + groups + " focused groups passed; VM/roll/paint/atlas peers only, no route/full-fight/browser/native acceptance");
