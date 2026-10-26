// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/spell_fx_test.js
// Actual recruited casters, actions/statuses, battle tick/frame and spell painters.
// Canvas-command peers only; no DOM, assets, browser, complete IIFE or native runtime.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, partyData = parties.prism, spells = data("spells").spells.filter(s => s.realm === "prism"), foes = data("prism-bestiary").types;
const boss = data("prism-bosses").bosses.find(b => b.name === "PyreWarden"), gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(data("interiors").interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
const sturdy = foes.filter(f => f.behaviour !== "undead").sort((a, b) => b.hp - a.hp)[0], undead = foes.find(f => f.behaviour === "undead");
assert.ok(sturdy && undead && boss);
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const result = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(result, prefix); return result; };
const source = [line("const START_LEVEL ="), line("const ACTIVE ="), line("const roster ="), line("const rnd ="), line("const ri ="),
  between("function makeMember(", "function recruitBeaten("), between("const atkOf =", "/* ---------- maps"),
  between("const STATUS =", "/* ---------- bestiary"), between("function battleTick(", "function advanceChooser()"),
  between("function pop(", "/* Foe turns by"), line("function wrap("),
  between("function spellHint(", "/* ---------- title:"),
  between("function gameplayInputBlocked()", "function resetGameplayInput()"),
  between("function frame(now)", "/* ---------- harness hooks"),
  "this.api = { makeMember, recruit, doAction, battleTick, frame, cure, has, battlePoint, drawBespokeSpellFx, drawBattle };"
].join("\n");
const legacyActions = source.replace(/B\.fx = \{ name: s\.name, t: 0, targets[\s\S]*?\};/, "B.fx = { name: s.name, t: 0, targets };")
  .replace("      B.fx.statusLanded = ok;\n", "");
assert.notEqual(legacyActions, source, "controlled baseline removes only the new action metadata");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, production = source) {
  const commands = [], sounds = [], stack = [], stats = { rng: 0, polls: 0, raf: 0, audio: 0 }, pressed = new Set();
  const fixedMath = Object.create(Math), record = (kind, item = {}) => commands.push({ kind, ...item });
  const g = { fillStyle: "#123456", globalAlpha: 0.37, clipping: null, path: null,
    save() { stack.push({ fillStyle: this.fillStyle, globalAlpha: this.globalAlpha, clipping: this.clipping }); record("save"); },
    restore() { assert.ok(stack.length, "balanced canvas restore"); Object.assign(this, stack.pop()); record("restore"); },
    beginPath() { this.path = null; record("beginPath"); }, rect(x, y, w, h) { this.path = { x, y, w, h }; record("clipRect", this.path); },
    clip() { this.clipping = this.path; record("clip", { bounds: this.clipping }); },
    fillRect(x, y, w, h) { record("rect", { x, y, w, h, color: this.fillStyle, alpha: this.globalAlpha, clip: this.clipping }); },
    drawImage(image, sx, sy, sw, sh, x, y, w, h) { record("image", { image, x, y, w, h, alpha: this.globalAlpha, clip: this.clipping }); }
  };
  const c = { W: width, H: 224, T: 16, party: [], reserve: [], bag: { "Herb Tonic": 2 }, gold: 237, dlg: null,
    state: { beaten: new Set(), minute: 480, steps: 0 }, map: { cue: "FIELD", kind: "world" }, mode: "battle", fade: 0, fadeCb: null,
    D: { party: clone(partyData), spells: clone(spells), rects: { backdrops: {}, sprites: {}, spells: Object.fromEntries(["Gust", "Drowse", "Lull"].map(n => ["fx:" + n, [0, 0, 480, 48]])) } },
    GEAR: clone(gear), IM: { spells: "atlas", backdrops: "backdrop" }, Math: fixedMath, rolls: [], drawing: false, now: 1000, last: 1000, SPEED: 1,
    settingsTransition: false, settingsFramePaused: true, pageInactive: false, document: { hidden: false },
    PAD: { poll: () => { stats.polls++; }, binding: () => false }, PANEL: { isOpen: () => c.panelOpen }, panelOpen: false,
    LOGICAL: ["up", "down", "left", "right", "a", "b", "start"], pressed: {}, pressedAt: {},
    performance: { now: () => c.now }, requestAnimationFrame: () => { stats.raf++; }, menuRepeat() {},
    hit: key => { const found = pressed.has(key); pressed.delete(key); return found; },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), sfx: value => sounds.push(value), cue() {},
    battleCmds: () => ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN"], mySpirits: () => [],
    endRound() { throw new Error("expiry fixture must not finish a battle round"); },
    saveGame() { throw new Error("effects cannot save"); },
    spr: (sheet, name, x, y) => record("sprite", { sheet, name, x, y }), cursor: (x, y) => record("cursor", { x, y }),
    win: (x, y, w, h) => record("window", { x, y, w, h }), gauge: (x, y, w) => record("gauge", { x, y, w }),
    text: (label, x, y, color = "#ffffff", shadow = "#202040") => record("text", { label: String(label).toUpperCase(), x, y, color, shadow, alpha: g.globalAlpha, clip: g.clipping }),
    tw: value => String(value).length * 6, g, jukeTick: () => { stats.audio++; }
  };
  fixedMath.random = () => { if (c.drawing) throw new Error("drawing cannot consume combat randomness"); stats.rng++; return c.rolls.length ? c.rolls.shift() : 0.1; };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = partyData.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, 15));
  c.api.recruit("Cinder Forge"); c.api.recruit("Sunwell Sanctum");
  const makeFoe = f => ({ key: f.key, name: f.name, hp: f.hp, max: f.hp, atk: f.attack, def: f.defence, spd: f.speed,
    exp: f.exp || 0, gold: f.gold || 0, beh: f.behaviour, el: f.element, size: 56, x: 24, y: 26 });
  c.B = { phase: "act", who: 1, cmd: 0, sub: null, t: 0, turn: 0, round: 1, wait: 0, queue: [], acts: [],
    msg: "", fx: null, pops: [], flash: {}, foes: [makeFoe(sturdy)] };
  const snapshot = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold, state: { ...c.state, beaten: Array.from(c.state.beaten) }, battle: c.B, rng: stats.rng });
  const draw = (effectOnly = true) => {
    commands.length = 0; const before = snapshot(), canvasBefore = { fillStyle: g.fillStyle, globalAlpha: g.globalAlpha, clipping: g.clipping };
    c.drawing = true; try { effectOnly ? c.api.drawBespokeSpellFx(c.B.fx) : c.api.drawBattle(); } finally { c.drawing = false; }
    assert.equal(snapshot(), before, "draws preserve combat state and RNG count"); assert.equal(stack.length, 0);
    if (effectOnly) assert.deepEqual({ fillStyle: g.fillStyle, globalAlpha: g.globalAlpha, clipping: g.clipping }, canvasBefore, "effect restores canvas state");
    return clone(commands);
  };
  return { c, api: c.api, stats, commands, sounds, makeFoe, draw,
    // Front-line fixture placement after actual recruitment; this does not execute ORDER (covered by the progression fixture).
    promote(job) { const i = c.reserve.findIndex(m => m.job === job); assert.ok(i >= 0, "authored recruit exists in reserve: " + job);
      const actor = c.reserve.splice(i, 1)[0], previous = c.party[1]; c.party[1] = actor; c.reserve.push(previous); return actor; },
    step(ms) { c.now += ms; c.api.frame(c.now); }
  };
}
function cast(s, name, options = {}) {
  const actor = s.promote(name === "Gust" ? "Beastcaller" : "Chronoseer"), spell = spells.find(sp => sp.name === name);
  assert.ok(actor.spells.includes(name), "the real recruited caster knows this spell");
  if (options.undead) s.c.B.foes = [s.makeFoe(undead)];
  if (options.boss) s.c.B.foes = [{ ...s.makeFoe(boss), boss: true, bossName: boss.name, beh: null, size: 112, x: 30, y: 10 }];
  const target = s.c.B.foes[0]; if (options.existing) target.status = { [spell.status]: 3 };
  if (options.noMp) actor.mp = spell.mp - 1; if (options.deadCaster) actor.hp = 0;
  s.c.rolls = [options.roll === undefined ? 0.1 : options.roll]; const beforeMp = actor.mp;
  s.api.doAction(Object.freeze({ kind: "magic", who: actor, spell, target }));
  return { actor, spell, target, beforeMp };
}
function combat(s) {
  const b = s.c.B, fx = b.fx && { name: b.fx.name, t: b.fx.t, targets: b.fx.targets };
  return JSON.stringify({ party: s.c.party, reserve: s.c.reserve, bag: s.c.bag, gold: s.c.gold,
    battle: { ...b, fx }, sounds: s.sounds, rng: s.stats.rng });
}
const symbols = (commands, name) => name === "Drowse" ? commands.filter(p => p.kind === "text" && p.label === "Z")
  : commands.filter(p => p.kind === "rect" && ["#e5c0ff", "#ab88d8", "#ffe6a0"].includes(p.color));
const pixels = commands => commands.filter(p => p.kind === "rect");
function assertEffectCanvas(commands, width) {
  assert.equal(commands.filter(p => p.kind === "save").length, 1); assert.equal(commands.at(-1).kind, "restore");
  const clip = commands.find(p => p.kind === "clipRect"); assert.deepEqual(clip, { kind: "clipRect", x: 0, y: 0, w: width, h: 144 });
  assert.ok(pixels(commands).length > 0, "authored effect draws pixels");
  for (const p of commands.filter(p => p.kind === "rect" || p.kind === "text")) {
    assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y)); assert.equal(p.x, Math.round(p.x)); assert.equal(p.y, Math.round(p.y));
    assert.deepEqual(p.clip, { x: 0, y: 0, w: width, h: 144 }); assert.ok(p.alpha >= 0 && p.alpha <= 1);
    if (p.kind === "rect") { assert.ok(p.w > 0 && p.h > 0); assert.ok(p.x >= 0 && p.x + p.w <= width && p.y >= 0 && p.y + p.h <= 144); }
  }
}
check("canonical Fennick and Quill join on authored routes and retain their real spell lists", () => {
  const s = session(); const f = s.c.reserve.find(m => m.job === "Beastcaller"), q = s.c.reserve.find(m => m.job === "Chronoseer");
  assert.equal(f.name, "Fennick"); assert.equal(q.name, "Quill"); assert.ok(f.spells.includes("Gust")); assert.ok(q.spells.includes("Drowse") && q.spells.includes("Lull"));
  assert.equal(partyData.members.find(m => m.job === f.job).joins, "after Cinder Forge"); assert.equal(partyData.members.find(m => m.job === q.job).joins, "after Sunwell Sanctum");
});
for (const [name, options] of [["Gust", {}], ["Drowse", {}], ["Drowse", { roll: 0.99 }], ["Drowse", { existing: true }],
  ["Drowse", { boss: true }], ["Drowse", { undead: true }], ["Lull", {}], ["Lull", { roll: 0.99 }], ["Lull", { existing: true }],
  ["Gust", { noMp: true }], ["Drowse", { deadCaster: true }]])
  check(name + "/" + JSON.stringify(options) + " keeps pre-metadata MP, damage, statuses, messages and RNG calls", () => {
    const current = session(), old = session(320, legacyActions), info = cast(current, name, options); cast(old, name, options);
    assert.equal(combat(current), combat(old));
    if (options.noMp || options.deadCaster) assert.equal(current.c.B.fx, null);
    else { const fx = current.c.B.fx; assert.equal(fx.caster, info.actor); assert.equal(fx.casterJob, info.actor.job); assert.equal(fx.status, info.spell.status); assert.equal(fx.element, info.spell.element);
      assert.equal(info.actor.mp, info.beforeMp - info.spell.mp); assert.equal(fx.statusLanded, name !== "Gust" && !options.existing && !options.boss && !options.undead && options.roll !== 0.99);
      assert.equal(current.stats.rng, options.existing ? 0 : 1); }
  });
for (const width of [320, 256]) for (const name of ["Gust", "Drowse", "Lull"])
  check(name + " effect is clipped, deterministic, pure and RNG-free at " + width, () => {
    const s = session(width); cast(s, name); s.c.B.fx.t = 0.32; const first = s.draw(); assertEffectCanvas(first, width); assert.deepEqual(s.draw(), first);
    if (name !== "Gust") assert.ok(symbols(first, name).length > 0);
  });
for (const name of ["Drowse", "Lull"]) check(name + " symbols require this cast to land and the target to remain living with that status", () => {
  for (const options of [{ roll: 0.99 }, { existing: true }, ...(name === "Drowse" ? [{ boss: true }, { undead: true }] : [])]) {
    const s = session(); cast(s, name, options); s.c.B.fx.t = 0.3; const draw = s.draw(); assert.ok(pixels(draw).length > 0); assert.equal(symbols(draw, name).length, 0);
    assert.ok(s.c.B.pops.some(p => p.txt === (options.boss ? "IMMUNE" : "MISS")));
  }
  for (const change of ["cured", "dead"]) {
    const s = session(), info = cast(s, name); s.c.B.fx.t = 0.3;
    if (change === "cured") assert.equal(s.api.cure(info.target, info.spell.status), true); else info.target.hp = 0;
    const draw = s.draw(); assert.ok(pixels(draw).length > 0); assert.equal(symbols(draw, name).length, 0);
  }
});
check("battle points follow current selected, KO and responsive party positions and reject nonparticipants", () => {
  for (const width of [320, 256]) {
    const s = session(width), target = s.c.party[1], foe = s.c.B.foes[0]; s.c.B.phase = "cmd"; s.c.B.who = 1;
    assert.deepEqual(clone(s.api.battlePoint(target)), { x: width - 51, y: 55 }); target.hp = 0;
    assert.deepEqual(clone(s.api.battlePoint(target)), { x: width - 33, y: 55 });
    assert.deepEqual(clone(s.api.battlePoint(foe)), { x: foe.x + 28, y: foe.y + 28 });
    assert.equal(s.api.battlePoint(null), null); assert.equal(s.api.battlePoint({ hp: 1 }), null); assert.equal(s.api.battlePoint(s.c.reserve[0]), null);
  }
});
check("invalid/reserve effect targets are ignored and a removed wind caster cannot create ribbons", () => {
  for (const name of ["Gust", "Drowse", "Lull"]) {
    const s = session(), info = cast(s, name); s.c.B.fx.t = 0.32; const valid = s.draw();
    s.c.B.fx.targets = [null, { hp: 1 }, s.c.reserve[0], info.target]; assert.deepEqual(s.draw(), valid);
    if (name === "Gust") { s.c.party.splice(s.c.party.indexOf(info.actor), 1); assert.equal(pixels(s.draw()).length, 0); }
  }
});
check("actual Portal job metadata retains atlas frames without enabling Prism bespoke effects", () => {
  const jobs = parties.portal.members;
  assert.ok(jobs.length > 0 && jobs.every(m => !["Chronoseer", "Beastcaller"].includes(m.job)));
  for (const width of [320, 256]) for (const member of jobs) for (const name of ["Gust", "Drowse", "Lull"]) {
    const s = session(width), caster = s.api.makeMember(member, 1), spell = spells.find(sp => sp.name === name), target = s.c.B.foes[0];
    s.c.party[1] = caster; if (spell.status) target.status = { [spell.status]: 3 };
    s.c.B.fx = { name, t: 0.3, targets: [target], caster, casterJob: caster.job, status: spell.status, statusLanded: true, element: spell.element };
    const draw = s.draw(false); assert.equal(draw.filter(p => p.kind === "image" && p.image === "atlas").length, 1);
    assert.equal(draw.filter(p => p.kind === "save").length, 0, "nonmatching real Portal job does not enter bespoke painter");
  }
  const s = session(); cast(s, "Drowse"); s.c.B.fx.name = "Ember"; assert.deepEqual(s.draw(), []);
});
function orderedEffect(s) {
  const commands = s.draw(false), atlas = commands.findIndex(p => p.kind === "image" && p.image === "atlas"), overlay = commands.findIndex(p => p.kind === "save"),
    restored = commands.findIndex(p => p.kind === "restore"), pill = commands.findIndex(p => p.kind === "rect" && p.color === "#101526"), window = commands.findIndex(p => p.kind === "window");
  assert.ok(atlas >= 0 && atlas < overlay && overlay < restored && restored < pill && pill < window, "atlas, bespoke effect, status pill and HUD paint in order");
}
check("full battle painter retains atlas -> bespoke -> status pills -> HUD at both widths", () => {
  for (const width of [320, 256]) { const s = session(width); cast(s, "Drowse"); s.c.B.fx.t = 0.3; orderedEffect(s); }
});
check("missing atlas targets paint no ghost frame while valid target frames remain identical", () => {
  for (const width of [320, 256]) {
    const s = session(width), info = cast(s, "Drowse"); s.c.B.fx.t = 0.3;
    const valid = s.draw(false).filter(p => p.kind === "image" && p.image === "atlas"); assert.equal(valid.length, 1);
    s.c.B.fx.targets = [undefined, null, info.target];
    assert.deepEqual(s.draw(false).filter(p => p.kind === "image" && p.image === "atlas"), valid);
    s.c.B.fx.targets = [undefined, null]; assert.equal(s.draw(false).filter(p => p.kind === "image" && p.image === "atlas").length, 0);
  }
});
check("an actual queued Drowse after the last foe falls exits before spending or creating any effect", () => {
  const s = session(), actor = s.promote("Chronoseer"), spell = spells.find(sp => sp.name === "Drowse"), target = s.c.B.foes[0];
  target.hp = 0; const mp = actor.mp, rng = s.stats.rng;
  s.c.B.queue = [{ kind: "magic", who: actor, spell, target }]; s.api.doAction(s.c.B.queue.shift());
  assert.equal(actor.mp, mp); assert.equal(s.stats.rng, rng); assert.equal(s.c.B.wait, 0); assert.equal(s.c.B.queue.length, 0); assert.equal(s.c.B.fx, null);
  const draw = s.draw(false); assert.equal(draw.filter(p => p.kind === "image" && p.image === "atlas").length, 0); assert.equal(draw.filter(p => p.kind === "save").length, 0);
  // The early live-foe guard prevents targets[undefined] here. The separate missing-target fixture exercises defensive drawing only.
});
check("actual battle tick and paused frame preserve effect age and expire after the existing .65 seconds", () => {
  const s = session(); cast(s, "Gust"); s.c.B.fx.t = 0.2; s.c.B.wait = 1000; const effect = s.c.B.fx;
  s.c.document.hidden = true; s.step(10000); assert.equal(effect.t, 0.2); assert.equal(s.c.B.fx, effect); assert.equal(s.c.last, s.c.now);
  s.c.document.hidden = false; s.c.panelOpen = true; s.step(10000); assert.equal(effect.t, 0.2);
  s.c.panelOpen = false; s.step(16); assert.ok(Math.abs(effect.t - 0.216) < 1e-12); assert.equal(s.stats.polls, 3); assert.equal(s.stats.raf, 3); assert.equal(s.stats.audio, 3);
  effect.t = 0.65; s.api.battleTick(0); assert.equal(s.c.B.fx, effect); s.api.battleTick(0.001); assert.equal(s.c.B.fx, null);
});
check("controlled missing overlay and false success symbols fail the behavioral invariants", () => {
  const noOverlay = source.replace("    drawBespokeSpellFx(B.fx);", ""); assert.notEqual(noOverlay, source);
  assert.throws(() => { const s = session(320, noOverlay); cast(s, "Drowse"); s.c.B.fx.t = 0.3; orderedEffect(s); }, assert.AssertionError);
  const oldApplied = source.replace("fx.statusLanded && target.hp > 0 && has(target, fx.status)", "target.hp > 0 && has(target, fx.status)"); assert.notEqual(oldApplied, source);
  assert.throws(() => { const s = session(320, oldApplied); cast(s, "Drowse", { existing: true }); s.c.B.fx.t = 0.3; assert.equal(symbols(s.draw(), "Drowse").length, 0); }, assert.AssertionError);
  const ghost = source.replace("if (!t) continue; ", ""); assert.notEqual(ghost, source);
  assert.throws(() => { const s = session(320, ghost); cast(s, "Drowse"); s.c.B.fx.targets = [undefined]; assert.equal(s.draw(false).filter(p => p.kind === "image" && p.image === "atlas").length, 0); }, assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("spell effects: " + checks + " focused groups passed; commands/offline only, no asset or runtime acceptance");
