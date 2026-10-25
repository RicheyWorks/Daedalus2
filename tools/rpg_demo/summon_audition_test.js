// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/summon_audition_test.js
// Actual chord/menu/painter excerpts and real summons table/unlocked, with finite fake audio nodes.
// No audio, browser, device, full audio engine, full-IIFE, combat or runtime acceptance execution.
// Explicit square/wide/tall atlas rectangles and 5x7 text recording are diagnostic paint peers.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Summons = require("./summons.js");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const builder = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = n => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", n + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x));
const parties = data("party").party, interiors = data("interiors").interiors, menus = data("menus").layouts;
const spells = data("spells").spells, bosses = data("prism-bosses").bosses;
function tuples(name) { const m = builder.match(new RegExp("^" + name + " = \\[([^\\r\\n]+)\\]$", "m")); assert.ok(m, name); return [...m[1].matchAll(/\("([^"]+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]); }
const quest = tuples("QUEST"), optional = tuples("OPTIONAL_QUEST"), final = builder.match(/^FINAL = "([^"]+)"$/m)[1];
const scale = JSON.parse(builder.match(/^FINAL_SCALE = (\{[^\r\n]+\})$/m)[1]);
const pyRound = n => { const f = Math.floor(n), r = n - f; return r < 0.5 ? f : r > 0.5 ? f + 1 : f + f % 2; };
const routes = quest.concat(optional).map(([landmark, name]) => {
  const boss_data = clone(bosses.find(b => b.dungeon === name)); assert.ok(boss_data);
  if (name === final) { boss_data.hp = Math.trunc(boss_data.hp * scale.hp); boss_data.attack = pyRound(boss_data.attack * scale.attack); boss_data.demo_scale = clone(scale); }
  return { landmark, name, final: name === final, optional: optional.some(([, n]) => n === name), boss_data };
});
const table = Summons.table(routes.map(d => d.boss_data), "prism"); assert.equal(table.length, 3);
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(s, prefix); return s; }
const chord = between("function playChord(", "function nextChooser(");
// Removing only the new return bookkeeping preserves the original production scheduling statements.
const oldChord = chord.replace("function playChord(", "function oldPlayChord(")
  .replace("  const timeline = { context: actx, startsAt: [], endsAt: t0 };\n", "")
  .replace(" timeline.startsAt.push(t); timeline.endsAt = Math.max(timeline.endsAt, t + 1.7);", "")
  .replace("  return timeline;\n", "");
assert.notEqual(oldChord, chord); assert.ok(!oldChord.includes("timeline"));
const cleanup = between("  for (const k in pressed)", '  if (mode === "title") drawTitle();');
const source = [line("const CHARS ="), line("const tw ="), line("const hit ="), line("function clearActionButtons()"), line("function cursor("),
  between("function spr(", "function win("), between("function gauge(", "/* ---------- party ---------- */"),
  between("const START_LEVEL =", "/* ---------- maps"), between("let menu = null;", "function drawEquip("),
  between("const STATUS =", "/* ---------- bestiary:"), between("function spellHint(", "function drawBattle("),
  between("function titlePrompt(", "function drawTitle("), line("const SUMMONS ="), line("const mySpirits ="), line("const ELEM ="), chord, oldChord,
  "function cleanup(now){\n" + cleanup + "\n}",
  "this.api={start:()=>{party=buildParty();},openMenu,menuTick,openSummonBook,summonBookTick,auditionSummon,drawSummonBook,playChord,oldPlayChord,cleanup,mySpirits,SUMMONS,roster,chars:CHARS," +
  "menu:()=>menu,audition:()=>summonAudition,view:()=>({mode,menu,pressed,pressedAt,now,fade})," +
  "resources:()=>({party,reserve,bag,gold,state:{...state,beaten:Array.from(state.beaten),ways:Array.from(state.ways)},opened:Array.from(opened),map,P,D,B})};"
].join("\n");
class FakeContext {
  constructor(currentTime = 10, state = "running") { this.currentTime = currentTime; this.state = state; this.nodes = []; this.lifecycle = []; }
  node(kind) {
    const n = { kind, id: this.nodes.length, type: "", frequency: { value: 0 }, connections: [], starts: [], stops: [] };
    n.connect = target => n.connections.push(target.id);
    n.start = t => n.starts.push(t); n.stop = t => n.stops.push(t);
    n.gain = { events: [], setValueAtTime(v, t) { this.events.push(["set", v, t]); }, linearRampToValueAtTime(v, t) { this.events.push(["linear", v, t]); }, exponentialRampToValueAtTime(v, t) { this.events.push(["exponential", v, t]); } };
    this.nodes.push(n); return n;
  }
  createBiquadFilter() { return this.node("filter"); }
  createOscillator() { return this.node("oscillator"); }
  createGain() { return this.node("gain"); }
  resume() { this.lifecycle.push("resume"); throw new Error("fixture must not unlock or resume audio"); }
  suspend() { this.lifecycle.push("suspend"); throw new Error("fixture must not change audio settings"); }
  close() { this.lifecycle.push("close"); throw new Error("fixture must not close a context"); }
  graph() { return this.nodes.map(n => ({ kind: n.kind, id: n.id, type: n.type, hz: n.frequency.value, connections: n.connections, starts: n.starts, stops: n.stops, gain: n.gain.events })); }
}
let groups = 0;
function check(label, fn) { try { fn(); groups++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(width = 320, realm = "prism", change = s => s) {
  const paints = [], sounds = [], pressed = {}, pressedAt = {}, calls = { rng: 0, storage: 0, combat: 0 }, gear = {};
  for (const r of ["portal", realm]) for (const shop of Object.values(interiors[r])) for (const it of shop.stock || []) if (it.effect || it.attack != null || it.defence != null) gear[it.name] = clone(it);
  const math = Object.create(Math); math.random = () => { calls.rng++; throw new Error("audition must not consume gameplay RNG"); };
  const reference = { ...Summons, damage() { calls.combat++; throw new Error("not a battle"); }, refusal() { calls.combat++; throw new Error("not a battle readiness check"); } };
  const rects = { "ui:Cursor": [0, 0, 16, 8] };
  table.forEach((sp, i) => { rects["Boss_" + sp.warden] = [512 * (i + 1), 0, ...[[112, 112], [224, 112], [112, 224]][i]]; });
  const known = new Set(parties[realm].members.flatMap(m => m.spells));
  const c = { D: { realm_key: realm, party: clone(parties[realm]), gear, dungeons: clone(routes), menus: clone(menus[realm]), rects: { sprites: rects }, spells: clone(spells.filter(s => s.realm === realm && (known.has(s.name) || s.tier <= 2))), ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, Math: math, pressed, pressedAt, now: 0, cursorNow: 0, PAD: null, B: { phase: "cmd", acts: [{ kind: "retained-choice" }], queue: [], summoned: [] },
    actx: null, sfxGain: { id: "sfx-bus" }, fade: 0, mode: "field", map: { kind: "town" }, P: { x: 7, y: 9, dir: "left" },
    state: { beaten: new Set(), ways: new Set(), seen: {}, fish: {}, quests: {}, day: 1, minute: 600, air: null, returnTo: null, steps: 0, sinceBattle: 0 }, opened: new Set(["retained/chest"]),
    window: { PrismSummons: reference }, PrismSummons: reference, IM: { sprites: "sprite-atlas-peer" }, performance: { now: () => c.cursorNow },
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), sfx: x => sounds.push(x), shardCount: () => 0, clockText: () => "D1 10:00", isNight: () => false,
    text(value, x, y, color = "#ffffff") { const label = String(value).toUpperCase(); paints.push({ kind: "text", label, x, y, w: label.length * 6, h: 8, color }); },
    g: { fillStyle: "", fillRect(x, y, w, h) { paints.push({ kind: "rect", x, y, w, h, color: this.fillStyle }); },
      drawImage(sheet, sx, sy, sw, sh, x, y, w, h) { assert.equal(sheet, "sprite-atlas-peer"); const name = Object.keys(rects).find(n => { const r = rects[n]; return sy === r[1] && sx >= r[0] && sx < r[0] + r[2]; }); assert.ok(name); paints.push({ kind: "image", name, x, y, w, h }); } },
    localStorage: Object.fromEntries(["getItem", "setItem", "removeItem"].map(k => [k, () => { calls.storage++; throw new Error("audition cannot access native saves"); }])),
    saveGame() { calls.storage++; throw new Error("audition cannot save"); }
  };
  vm.createContext(c); vm.runInContext(change(source), c, { timeout: 1000 }); c.api.start();
  const resources = () => JSON.stringify(c.api.resources());
  return { c, api: c.api, paints, sounds, calls, resources,
    tick(...keys) { c.now += 16; keys.forEach(k => { pressed[k] = true; pressedAt[k] = c.now; }); c.api.menuTick(); c.api.cleanup(c.now); },
    draw() { paints.length = 0; const before = resources(), view = JSON.stringify(c.api.view()), effects = JSON.stringify({ sounds, calls, graph: c.actx && c.actx.graph(), audition: c.api.audition() && { startsAt: c.api.audition().startsAt, endsAt: c.api.audition().endsAt, warden: c.api.audition().warden } }); c.api.drawSummonBook(); assert.equal(resources(), before); assert.equal(JSON.stringify(c.api.view()), view); assert.equal(JSON.stringify({ sounds, calls, graph: c.actx && c.actx.graph(), audition: c.api.audition() && { startsAt: c.api.audition().startsAt, endsAt: c.api.audition().endsAt, warden: c.api.audition().warden } }), effects); return paints; },
    labels(confirm = "ABCDEFGH", cancel = "IJKLMNOP", menu = "QRSTUVWX") { c.PAD = { devices: () => [{ index: 0 }], label: a => ({ confirm, cancel, menu })[a] }; }
  };
}
function context(s, stage = "magic-who", earned = table) {
  earned.forEach(sp => s.c.state.beaten.add(sp.warden)); s.api.openMenu(); s.tick("down"); s.tick("a"); assert.equal(s.api.menu().sub, "magic-who");
  if (stage === "magic") { s.tick("a"); assert.equal(s.api.menu().sub, "magic"); }
  s.tick("start"); assert.equal(s.api.menu().sub, "summons"); return s;
}
const texts = (s, y) => s.paints.filter(p => p.kind === "text" && (y === undefined || p.y === y));
const glints = s => s.paints.filter(p => p.kind === "rect" && p.w === 4 && p.h === 4 && p.y === 151 && p.color.startsWith("rgba(244,232,255,"));
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-10, a + " != " + b);
function edges(s) { for (const k of ["a", "b", "start", "left", "right", "up", "down"]) assert.equal(!!s.c.pressed[k], false, k); }
function bounds(s) { for (const p of s.paints) { assert.ok(Number.isFinite(p.x + p.y + p.w + p.h)); assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= s.c.W && p.y + p.h <= 224, JSON.stringify(p)); if (p.kind === "text") assert.ok([...p.label].every(ch => s.api.chars.includes(ch)), p.label); } }
function assertGraph(ctx, sp, start = 10) {
  const filters = ctx.nodes.filter(n => n.kind === "filter"), os = ctx.nodes.filter(n => n.kind === "oscillator"), gains = ctx.nodes.filter(n => n.kind === "gain");
  assert.equal(ctx.nodes.length, 7); assert.equal(filters.length, 1); assert.equal(os.length, 3); assert.equal(gains.length, 3);
  const lp = filters[0]; assert.equal(lp.type, "lowpass"); assert.equal(lp.frequency.value, 1200); assert.deepEqual(lp.connections, ["sfx-bus"]);
  sp.chord.forEach((note, i) => { const o = os[i], gn = gains[i], t = start + note.at_ms / 1000; assert.equal(o.type, "sine"); assert.equal(o.frequency.value, Math.min(note.hz, 360)); assert.ok(o.frequency.value <= 360); assert.deepEqual(o.connections, [gn.id]); assert.deepEqual(gn.connections, [lp.id]); assert.deepEqual(gn.gain.events, [["set", 0, t], ["linear", 0.3, t + 0.04], ["exponential", 0.0001, t + 1.6]]); assert.deepEqual(o.starts, [t]); assert.deepEqual(o.stops, [t + 1.7]); });
  assert.deepEqual(ctx.lifecycle, []);
}
check("canonical earned Wardens retain three exact rolled triads and no optional/final spirit", () => {
  assert.equal(Summons.MAX_HZ, 360); assert.equal(Summons.NOTE_GAIN, 0.3); assert.equal(Summons.ROLL_MS, 110);
  for (const sp of table) { assert.equal(sp.chord.length, 3); sp.chord.forEach((n, i) => { assert.equal(n.hz, Summons.hzOf(n.semis)); assert.equal(n.gain, 0.3); assert.equal(n.at_ms, i * 110); }); }
  const s = context(session(), "magic-who", []); routes.filter(d => d.optional || d.final).forEach(d => s.c.state.beaten.add(d.boss_data.name)); assert.equal(s.api.mySpirits().length, 0); s.c.actx = new FakeContext(); s.tick("right"); assert.equal(s.c.actx.nodes.length, 0); assert.equal(s.api.audition(), null);
});
check("metadata records actual note starts/stops while the unchanged three-sine graph matches the old scheduler", () => {
  for (const sp of table) { const s = session(), current = new FakeContext(), original = new FakeContext(); s.c.actx = current; const result = s.api.playChord(sp); assertGraph(current, sp); s.c.actx = original; assert.equal(s.api.oldPlayChord(sp), undefined); assert.deepEqual(current.graph(), original.graph()); assert.equal(result.context, current); assert.deepEqual(Array.from(result.startsAt), current.nodes.filter(n => n.kind === "oscillator").map(n => n.starts[0])); assert.equal(result.endsAt, Math.max(...current.nodes.flatMap(n => n.stops))); near(result.endsAt, 11.92); }
  // A diagnostic high-frequency probe verifies the existing cap; this is not an authored new spirit.
  const s = session(), high = clone(table[0]); high.chord[2].hz = 900; s.c.actx = new FakeContext(); s.api.playChord(high); assertGraph(s.c.actx, high);
});
check("direct battle chord interface remains ungated and its ignored return does not change the audio graph", () => {
  const s = context(session()); s.c.actx = new FakeContext(); s.tick("right"); const timeline = s.api.audition(); assert.equal(s.c.actx.nodes.length, 7);
  s.api.playChord(table[0]); assert.equal(s.c.actx.nodes.length, 14); assert.equal(s.api.audition(), timeline); assert.deepEqual(s.c.actx.graph().slice(0, 7), s.c.actx.graph().slice(7).map(n => ({ ...n, id: n.id - 7, connections: n.connections.map(id => typeof id === "number" ? id - 7 : id) })));
});
check("Right uses the earned selection after Up/Down without any gameplay transaction", () => {
  const s = context(session(), "magic"); s.c.actx = new FakeContext(); const before = s.resources(), m = s.api.menu(), who = m.who, ii = m.ii;
  s.tick("down", "right"); assert.equal(m.si, 1); assert.equal(s.api.audition().warden, table[1].warden); assertGraph(s.c.actx, table[1]); assert.equal(s.resources(), before); assert.equal(m.who, who); assert.equal(m.ii, ii); edges(s); assert.deepEqual(s.calls, { rng: 0, storage: 0, combat: 0 });
  s.c.actx.currentTime = s.api.audition().endsAt; s.tick("up", "right"); assert.equal(m.si, 0); assert.equal(s.api.audition().warden, table[0].warden); assert.equal(s.c.actx.nodes.length, 14); assert.equal(s.resources(), before);
});
check("absent, suspended and closed contexts refuse without unlocking, resuming, creating nodes or bypassing settings", () => {
  for (const [state, notice] of [[null, "SOUND HAS NOT STARTED."], ["suspended", "SOUND IS PAUSED."], ["closed", "SOUND IS UNAVAILABLE."]]) { const s = context(session(256)); s.c.actx = state && new FakeContext(10, state); const before = s.resources(), soundCount = s.sounds.length; s.tick("right"); assert.equal(s.api.menu().summonNote, notice); assert.equal(s.api.audition(), null); assert.equal(s.sounds.length, soundCount); if (s.c.actx) { assert.equal(s.c.actx.nodes.length, 0); assert.deepEqual(s.c.actx.lifecycle, []); } s.draw(); bounds(s); assert.ok(texts(s, 196).some(p => p.label === notice)); assert.equal(s.resources(), before); }
});
check("global audio-clock cooldown survives selection, menu closure/reopening and unrelated wall-clock jumps", () => {
  const s = context(session()); s.c.actx = new FakeContext(); s.tick("right"); const first = s.api.audition(); s.tick("down", "right"); assert.equal(s.c.actx.nodes.length, 7); assert.equal(s.api.audition(), first);
  s.tick("b"); s.c.now += 86400000; s.c.cursorNow = 1e12; s.tick("start"); s.tick("right"); assert.equal(s.c.actx.nodes.length, 7); assert.equal(s.api.audition(), first); s.c.now = -1000000; s.c.cursorNow = -300; s.tick("right"); assert.equal(s.c.actx.nodes.length, 7);
  s.c.actx.currentTime = first.endsAt; s.tick("right"); assert.equal(s.c.actx.nodes.length, 14); assert.notEqual(s.api.audition(), first); near(s.api.audition().startsAt[0], first.endsAt);
});
check("suspension freezes audio-clock lifetime and a replacement for a closed context can schedule freshly", () => {
  const s = context(session()); s.c.actx = new FakeContext(); s.tick("right"); const first = s.api.audition(), old = s.c.actx; old.currentTime = first.startsAt[1]; old.state = "suspended"; s.tick("right"); s.c.now += 999999; s.tick("b"); s.tick("start"); old.state = "running"; s.tick("right"); assert.equal(old.nodes.length, 7); assert.equal(s.api.audition(), first);
  old.state = "closed"; s.c.actx = new FakeContext(0); s.draw(); assert.equal(glints(s).length, 0); s.tick("right"); assert.equal(s.c.actx.nodes.length, 7); assert.equal(s.api.audition().context, s.c.actx); near(s.api.audition().endsAt, 1.92); assert.deepEqual(old.lifecycle, []);
});
check("every close action beats simultaneous Right/navigation, drains edges and preserves the captured book", () => {
  for (const stage of ["magic-who", "magic"]) for (const close of [["a"], ["b"], ["start"], ["a", "b", "start"]]) { const s = context(session(), stage); s.c.actx = new FakeContext(); const m = s.api.menu(), before = s.resources(), kept = { who: m.who, ii: m.ii, spell: m.spell, msg: m.msg };
    s.tick(...close, "up", "down", "left", "right"); assert.equal(m.sub, stage); assert.equal(s.c.actx.nodes.length, 0); edges(s); assert.equal(s.resources(), before); for (const key of Object.keys(kept)) assert.equal(m[key], kept[key]); s.tick(); assert.equal(m.sub, stage); assert.equal(s.c.actx.nodes.length, 0);
    s.tick("start"); s.tick("right"); assert.equal(s.c.actx.nodes.length, 7, "released/new Right can audition after re-entry"); }
});
check("empty and Portal paths never schedule an audition or expose an unearned chord", () => {
  const empty = context(session(), "magic-who", []); empty.c.actx = new FakeContext(); empty.tick("up", "down", "left", "right"); empty.draw(); bounds(empty); assert.equal(empty.c.actx.nodes.length, 0); assert.equal(glints(empty).length, 0); assert.ok(texts(empty).some(p => p.label === "NO SPIRITS YET."));
  const p = session(256, "portal"); p.c.actx = new FakeContext(); p.api.openMenu(); p.tick("down"); p.tick("a"); const before = p.resources(); p.tick("start"); assert.equal(p.api.menu().sub, "magic-who"); assert.equal(p.api.mySpirits().length, 0); assert.equal(p.c.actx.nodes.length, 0); assert.equal(p.resources(), before); assert.equal(p.api.audition(), null);
});
check("glints follow actual three note onsets, remain frozen with audio time, and end exactly at the final stop", () => {
  const s = context(session()); s.c.actx = new FakeContext(); s.tick("right"); const played = s.api.audition();
  for (let i = 0; i < 3; i++) { s.c.actx.currentTime = played.startsAt[i]; s.draw(); assert.equal(glints(s).length, i + 1); assert.ok(texts(s, 66).some(p => p.label === "CHORD")); }
  s.c.actx.state = "suspended"; s.draw(); const paint = JSON.stringify(s.paints); s.c.now += 1e9; s.c.cursorNow = 0; s.draw(); assert.equal(JSON.stringify(s.paints), paint); assert.ok(texts(s, 196).some(p => p.label === "SOUND IS PAUSED."));
  s.c.actx.currentTime = played.endsAt; s.draw(); assert.equal(glints(s).length, 0); assert.ok(!texts(s, 66).some(p => p.label === "CHORD")); s.c.actx.currentTime = played.startsAt[0]; s.c.actx.state = "closed"; s.draw(); assert.equal(glints(s).length, 0);
});
for (const width of [320, 256]) check("selected Warden/art/onset binding, bounded feedback and mapped footer remain paint-only at " + width, () => {
  const s = context(session(width)); s.labels(); s.c.actx = new FakeContext(); const caster = s.api.roster()[s.api.menu().who]; caster.name = "ß".repeat(64); caster.mp = caster.mmax = Number.MAX_SAFE_INTEGER;
  for (let index = 0; index < table.length; index++) { s.api.menu().si = index; s.c.actx.currentTime += 3; s.tick("right"); const played = s.api.audition(); s.c.actx.currentTime = played.startsAt[2];
    for (const blink of [0, 300]) { s.c.cursorNow = blink; s.draw(); bounds(s); assert.equal(glints(s).length, 3); const image = s.paints.find(p => p.kind === "image" && p.name === "Boss_" + table[index].warden); assert.ok(image); assert.ok(image.w <= 72 && image.h <= 72); const r = s.c.D.rects.sprites[image.name]; assert.equal(image.w / image.h, r[2] / r[3]); assert.ok(s.paints.indexOf(image) < s.paints.indexOf(glints(s)[0])); assert.equal(texts(s, 212)[0].label, "ABCDEFGH/IJKLMNOP/QRSTUVWX: BACK"); assert.ok(texts(s, 22).some(p => p.label === "MP 9999+/9999+")); }
    s.api.menu().si = (index + 1) % table.length; s.draw(); assert.equal(glints(s).length, 0); assert.ok(!texts(s, 66).some(p => p.label === "CHORD")); }
  const sp = table[s.api.menu().si]; s.c.actx.currentTime += 3; s.tick("right"); delete s.c.D.rects.sprites["Boss_" + sp.warden]; s.draw(); bounds(s); assert.equal(glints(s).length, 1); assert.ok(!s.paints.some(p => p.kind === "image" && p.name.startsWith("Boss_"))); s.labels("INVALID LABEL", "<BAD>", "TOO LONG LABEL"); s.draw(); assert.equal(texts(s, 212)[0].label, "Z/SPACE/X/ESC/ENTER: BACK"); assert.deepEqual(s.calls, { rng: 0, storage: 0, combat: 0 });
});
check("controlled old Right/cooldown/selection-binding variants violate the corresponding behavioral invariant", () => {
  const right = 'if (hit("right") && n) auditionSummon(spirits[clamp(menu.si || 0, 0, n - 1)]);'; assert.ok(source.includes(right));
  const noRight = context(session(320, "prism", s => s.replace(right, 'hit("right");'))); noRight.c.actx = new FakeContext(); noRight.tick("right"); assert.throws(() => assert.equal(noRight.c.actx.nodes.length, 7), assert.AssertionError);
  const cooldown = '  if (summonAudition && summonAudition.context === actx && actx.currentTime < summonAudition.endsAt) return;'; assert.ok(source.includes(cooldown));
  const repeat = context(session(320, "prism", s => s.replace(cooldown, ""))); repeat.c.actx = new FakeContext(); repeat.tick("right"); repeat.tick("right"); assert.throws(() => assert.equal(repeat.c.actx.nodes.length, 7), assert.AssertionError);
  const binding = ' && summonAudition.warden === spirit.warden'; assert.ok(source.includes(binding)); const wrong = context(session(320, "prism", s => s.replace(binding, ""))); wrong.c.actx = new FakeContext(); wrong.tick("right"); wrong.tick("down"); wrong.draw(); assert.throws(() => assert.equal(glints(wrong).length, 0), assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline (compile only)" });
console.log("summon audition: " + groups + " focused groups passed; fake audio graph and paint peers only, no audible/browser/device/runtime acceptance");
