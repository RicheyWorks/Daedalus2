// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/battle_readability_test.js
// Actual battle painter, status helpers, formation placement and canonical catalogs.
// Paint-command capture only: no DOM, assets, browser, game loop or native runtime.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8").replace(/\r\n/g, "\n");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, spells = data("spells").spells, foes = data("prism-bestiary").types;
const formations = data("prism-encounters").zones;
const ordinaryFour = formations.airship.formations.find(f => f.enemies.length === 4);
assert.ok(ordinaryFour, "canonical four-foe formation exists");
function between(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "production section exists: " + start); return html.slice(a, b);
}
const line = prefix => { const result = html.split("\n").find(l => l.startsWith(prefix)); assert.ok(result, prefix); return result; };
const source = [line("const START_LEVEL ="), line("const CHARS ="),
  between("function makeMember(", "/* Recruits:"), between("const STATUS =", "function inflict("),
  between("function startBattle(", "const ELEM ="), line("function wrap("),
  between("function spellHint(", "/* ---------- title:"),
  "this.api = { makeMember, startBattle, statusPill, drawBattle, tags, statuses: STATUS, chars: CHARS, spellHint };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source) {
  const commands = [], record = (kind, item) => commands.push({ kind, ...item });
  const fixedMath = Object.create(Math); fixedMath.random = () => { throw new Error("drawing cannot consume combat randomness"); };
  const c = { W: width, H: 224, party: [], reserve: [], bag: { "Herb Tonic": 2 }, gold: 237,
    state: { sinceBattle: 0, minute: 480, beaten: new Set() }, map: { cue: "FIELD" }, mode: "field", fade: 0, fadeCb: null,
    settingsFramePaused: true, Math: fixedMath, IM: { backdrops: "backdrops", spells: "spells" },
    D: { realm_key: realm, realm_profile: realm === "portal" ? { start_level: 1 } : null,
      party: clone(parties[realm]), spells: clone(spells.filter(s => s.realm === realm)),
      foes: Object.fromEntries(foes.map(f => [f.key, clone(f)])), dungeons: [], backdrop_for_zone: { airship: "sky" },
      rects: { backdrops: { sky: [0, 0, 320, 180] }, spells: {}, sprites: {} } },
    performance: { now: () => 0 }, passTime() {}, meet() {}, cue() {}, sfx() {},
    clamp: (n, lo, hi) => Math.max(lo, Math.min(hi, n)), battleCmds: () => ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN", "SUMMON"],
    mySpirits: () => [], battleItems: () => [], spellOf: name => c.D.spells.find(s => s.name === name),
    saveGame() { throw new Error("drawing cannot save"); },
    spr: (sheet, name, x, y, sx, sw, sh, scale) => record("sprite", { sheet, name, x, y, scale }),
    cursor: (x, y) => record("cursor", { x, y }), win: (x, y, w, h) => record("window", { x, y, w, h }),
    gauge: (x, y, w, fraction, color) => record("gauge", { x, y, w, h: 5, fraction, color }),
    text: (label, x, y, color = "#ffffff", shadow = "#202040") => record("text", { label: String(label).toUpperCase(), x, y, color, shadow, w: String(label).length * 6, h: 8 }),
    tw: label => String(label).length * 6,
    g: { fillStyle: "", fillRect(x, y, w, h) { record("rect", { x, y, w, h, color: this.fillStyle }); },
      drawImage(image, sx, sy, sw, sh, x, y, w, h) { record("image", { image, x, y, w, h }); } }
  };
  vm.createContext(c); vm.runInContext(production, c, { timeout: 1000 });
  c.party = c.D.party.members.filter(m => m.joins === "start").map(m => c.api.makeMember(m, realm === "portal" ? 1 : 15));
  c.api.startBattle("airship", null, ordinaryFour.enemies); c.B.phase = "cmd"; c.B.sub = "target"; c.B.list = c.B.foes; c.B.target = 0;
  const snapshot = () => JSON.stringify({ party: c.party, reserve: c.reserve, bag: c.bag, gold: c.gold,
    state: { ...c.state, beaten: Array.from(c.state.beaten) }, battle: c.B, mode: c.mode, fade: c.fade });
  return { c, commands, api: c.api, draw(allowFlash = false) {
    commands.length = 0; const before = snapshot(), flash = clone(c.B.flash); c.api.drawBattle();
    if (allowFlash) { const after = c.B.flash; c.B.flash = flash; assert.equal(snapshot(), before, "only the inherited flash countdown may mutate during drawing"); c.B.flash = after; }
    else assert.equal(snapshot(), before, "drawing preserves resources, statuses, targets and progress");
    return commands;
  } };
}
const intersects = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
function pillAt(s, x, y) { return s.commands.find(p => p.kind === "rect" && p.color === "#101526" && p.x === x && p.y === y && p.w === 24 && p.h === 9); }
function pillText(s, pill) {
  assert.ok(pill, "status has a dark readable backing");
  const label = s.commands.find(p => p.kind === "text" && p.x === pill.x + 3 && p.y === pill.y + 1);
  assert.ok(label); assert.equal(label.shadow, null); assert.ok(label.x + label.w <= pill.x + pill.w);
  const edge = s.commands.find(p => p.kind === "rect" && p.x === pill.x && p.y === pill.y && p.w === 1 && p.h === 9 && p.color === label.color);
  assert.ok(edge, "pill keeps the status-colored leading edge"); return label;
}
function assertAfterArt(s) {
  const pills = s.commands.filter(p => p.kind === "rect" && p.color === "#101526" && p.y < 144);
  assert.equal(pills.length, s.c.B.foes.filter(f => f.hp > 0 && s.api.tags(f).length).length);
  const finalArt = Math.max(...s.commands.map((p, i) => p.kind === "sprite" || (p.kind === "image" && p.image === "spells") ? i : -1));
  for (const pill of pills) {
    assert.ok(s.commands.indexOf(pill) > finalArt, "every foe pill paints after every sprite and atlas effect");
    assert.ok(pill.x >= 0 && pill.x + pill.w <= s.c.W && pill.y >= 0 && pill.y + pill.h <= 144);
    pillText(s, pill);
  }
}
function assertHud(s, expectedNumbers = null) {
  const compact = s.c.W < 320, x = compact ? 128 : 158, hpRight = compact ? 220 : 276, mpRight = compact ? 246 : 310,
    pillX = compact ? 172 : 216, max = compact ? 999 : 9999, nameLength = compact ? 7 : 9;
  const texts = s.commands.filter(p => p.kind === "text" && p.x >= x && p.y >= 147);
  const header = texts.filter(p => p.y === 147);
  assert.deepEqual(header.map(p => p.label), ["PARTY", "HP", "MP"]);
  assert.deepEqual(header.map(p => p.color), ["#a0a8c0", "#a8e0a0", "#a0c8ff"]);
  for (let i = 0; i < s.c.party.length; i++) {
    const m = s.c.party[i], y = 159 + i * 15, rows = texts.filter(p => p.y === y);
    const name = rows.find(p => p.x === x), hp = rows.find(p => p.x + p.w === hpRight), mp = rows.find(p => p.x + p.w === mpRight);
    assert.ok(name && hp && mp, "separate name, HP and MP text on row " + i);
    assert.equal(name.label, String(m.name).toUpperCase().slice(0, nameLength));
    const shown = n => n > max ? max + "+" : String(n);
    assert.equal(hp.label, expectedNumbers ? expectedNumbers[0] : shown(m.hp)); assert.equal(mp.label, expectedNumbers ? expectedNumbers[1] : shown(m.mp));
    assert.equal(mp.color, "#a0c8ff"); assert.equal(hp.color, name.color); assert.ok(name.x + name.w <= pillX);
    assert.ok(pillX + 24 <= hp.x && hpRight < mp.x, "names/statuses/HP/MP never overprint each other");
    for (const t of [name, hp, mp]) {
      assert.ok(t.x >= x && t.x + t.w <= s.c.W - 10 && t.y + t.h < 224);
      assert.ok(Array.from(t.label).every(k => s.api.chars.includes(k)), "visible values use supported glyphs");
    }
    const gauge = s.commands.find(p => p.kind === "gauge" && p.y === y + 9);
    assert.ok(gauge); assert.equal(gauge.x, x); assert.equal(gauge.w, compact ? 90 : 116); assert.equal(gauge.fraction, m.hp / m.max);
    assert.ok(gauge.y + gauge.h < 224 && gauge.y + gauge.h <= y + 15);
    const pill = pillAt(s, pillX, y - 1), tags = Array.from(s.api.tags(m));
    if (m.hp > 0 && tags.length) assert.equal(pillText(s, pill).label, s.api.statuses[tags[Math.floor(s.c.B.t / 1.2) % tags.length]].tag);
    else assert.equal(pill, undefined, "no stale party badge on KO or clean member");
  }
}
for (const width of [320, 256]) check("canonical overlapping four-foe art and atlas effects finish before readable status pills at " + width, () => {
  const s = session(width), f = s.c.B.foes;
  assert.ok(intersects({ x: f[0].x, y: f[0].y, w: f[0].size, h: f[0].size }, { x: f[2].x, y: f[2].y, w: f[2].size, h: f[2].size }));
  f.forEach(foe => { foe.status = { poison: true }; }); const spell = s.c.D.spells.find(sp => sp.name === "Ember") || s.c.D.spells[0];
  s.c.D.rects.spells["fx:" + spell.name] = [0, 0, 480, 48]; s.c.B.fx = { name: spell.name, t: 0.2, targets: [f[0], f[2], s.c.party[0]] };
  s.draw(); assertAfterArt(s); assert.equal(s.commands.filter(p => p.kind === "image" && p.image === "spells").length, 3);
});
for (const width of [320, 256]) check("every actual status has a legible foe/party pill and rotates without changing statuses at " + width, () => {
  const s = session(width), foe = s.c.B.foes[0], member = s.c.party[0], pillX = width === 320 ? 216 : 172;
  for (const [key, info] of Object.entries(s.api.statuses)) {
    foe.status = { [key]: 3 }; member.status = { [key]: 3 }; s.draw();
    assert.equal(pillText(s, pillAt(s, foe.x + foe.size / 2 - 12, foe.y + foe.size - 7)).label, info.tag);
    assert.equal(pillText(s, pillAt(s, pillX, 158)).label, info.tag); assertAfterArt(s);
  }
  const statuses = { poison: true, sleep: 3, protect: 4, unknown: 3, burn: 0 }; foe.status = clone(statuses); member.status = clone(statuses);
  for (let i = 0; i < 6; i++) { s.c.B.t = i * 1.21; s.draw(); const expected = ["PSN", "SLP", "WRD"][i % 3];
    assert.equal(pillText(s, pillAt(s, pillX, 158)).label, expected); assertHud(s); }
});
for (const width of [320, 256]) check("ordinary authored start and quest-level party values remain exact and separate at " + width, () => {
  for (const realm of ["prism", "portal"]) for (const level of [realm === "portal" ? 1 : 15, 28]) {
    const s = session(width, realm); s.c.party = s.c.D.party.members.slice(0, 4).map(m => s.api.makeMember(m, level));
    s.c.party[0].name = "ABCDEFGHI"; s.c.party.forEach(m => { m.status = { protect: 4 }; }); s.draw(); assertHud(s);
    for (const m of s.c.party) assert.ok(m.hp <= (width === 320 ? 9999 : 999) && m.mp <= (width === 320 ? 9999 : 999));
  }
});
for (const width of [320, 256]) check("legal restored long names and large integer stats use bounded truthful display at " + width, () => {
  const s = session(width), m = s.c.party[0]; m.name = "L".repeat(64); m.max = m.mmax = Number.MAX_SAFE_INTEGER; m.status = { haste: 4 };
  for (const n of [0, 1, 999, 1000, 9999, 10000, 999999, Number.MAX_SAFE_INTEGER]) { m.hp = n; m.mp = n; s.draw(); assertHud(s); }
});
for (const width of [320, 256]) check("selected command row, low HP and KO remain distinct at " + width, () => {
  const s = session(width), split = width === 320 ? 150 : 120;
  for (let i = 0; i < s.c.party.length; i++) {
    s.c.B.who = i; s.draw(); assertHud(s); const highlights = s.commands.filter(p => p.kind === "rect" && p.color === "#30304c");
    assert.equal(highlights.length, 1); const h = highlights[0]; assert.equal(h.y, 158 + i * 15); assert.equal(h.x, split + 6);
    assert.ok(h.x + h.w <= width - 8 && h.y + h.h < 224);
    const label = s.commands.find(p => p.kind === "text" && p.x === split + 8 && p.y === h.y + 1); assert.ok(s.commands.indexOf(h) < s.commands.indexOf(label));
  }
  const m = s.c.party[0]; m.hp = 1; m.status = { poison: true }; s.draw(); assertHud(s);
  assert.equal(s.commands.find(p => p.kind === "text" && p.x === split + 8 && p.y === 159).color, "#fff070");
  assert.equal(s.commands.find(p => p.kind === "gauge" && p.y === 168).color, "#e8b85c");
  m.hp = 0; s.c.B.foes[0].hp = 0; s.c.B.foes[0].status = { poison: true }; s.draw(); assertHud(s);
  assert.equal(s.commands.find(p => p.kind === "text" && p.x === split + 8 && p.y === 159).color, "#f87878");
  assert.equal(pillAt(s, s.c.B.foes[0].x + 16, s.c.B.foes[0].y + 49), undefined);
  assert.equal(s.commands.find(p => p.kind === "sprite" && p.name === m.sprite).x, width - 50);
  s.c.B.phase = "act"; s.draw(); assert.equal(s.commands.some(p => p.kind === "rect" && p.color === "#30304c"), false);
});
check("target cursors and existing selected-spell footer keep their current behavior", () => {
  for (const width of [320, 256]) {
    const s = session(width); s.c.B.list = [s.c.party[1]]; s.c.B.target = 0; s.draw();
    assert.ok(s.commands.some(p => p.kind === "cursor" && p.x === width - 70 && p.y === 50));
    const actor = s.c.party[0], spell = s.c.D.spells.find(sp => sp.name === "Mend"); assert.ok(spell);
    actor.spells = [spell.name]; s.c.B.sub = "magic"; s.c.B.oi = 0; s.draw(); assertHud(s);
    const footer = s.commands.filter(p => p.kind === "text" && p.x === 6 && p.y >= 190);
    assert.deepEqual(footer.map(p => p.label), [spell.name.toUpperCase(), s.api.spellHint(spell)]);
    assert.deepEqual(footer.map(p => p.y), [190, 201]); assert.ok(footer.every(p => p.x + p.w <= (width === 320 ? 144 : 114)));
  }
});
check("command picker actor stays inside its window for new and restored long names", () => {
  for (const width of [320, 256]) {
    const s = session(width); s.c.B.sub = null;
    for (const name of ["ABCDEFGHI", "L".repeat(64)]) {
      s.c.party[0].name = name; s.draw(); assertHud(s);
      const actor = s.commands.find(p => p.kind === "text" && p.x === 86 && p.y === 152);
      assert.ok(actor); assert.equal(actor.label, name.slice(0, width === 320 ? 9 : 5));
      assert.ok(actor.x + actor.w <= (width === 320 ? 150 : 120) - 4);
      for (const cmd of ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN", "SUMMON"])
        assert.ok(s.commands.some(p => p.kind === "text" && p.x === 22 && p.label === cmd));
    }
  }
});
check("active flash drawing retains its one fixed decrement and paused drawing stays pure", () => {
  const s = session(), f = s.c.B.foes[0], key = f.key + f.x; f.status = { poison: true }; s.c.B.flash[key] = 0.2;
  s.draw(); assert.equal(s.c.B.flash[key], 0.2); assertAfterArt(s); s.c.settingsFramePaused = false; s.draw(true);
  assert.equal(s.c.B.flash[key], 0.2 - 1 / 60); s.c.settingsFramePaused = true; const remaining = s.c.B.flash[key]; s.draw(); assert.equal(s.c.B.flash[key], remaining);
});
check("pill coordinates round and unknown statuses paint nothing", () => {
  const s = session(); s.commands.length = 0; s.api.statusPill("unknown", 1, 1); assert.equal(s.commands.length, 0);
  s.api.statusPill("poison", 20.4, 30.6); assert.equal(pillText(s, pillAt(s, 20, 31)).label, "PSN");
});
check("controlled former interleaving, missing labels and unbounded numeric rendering fail these invariants", () => {
  const a = source.indexOf("  // Paint tags after every sprite"), b = source.indexOf("  for (const p of B.pops)", a); assert.ok(a >= 0 && b > a);
  const art = '    spr("sprites", f.img, f.x, f.y, 0, null, null, f.size / 112);';
  const interleaved = (source.slice(0, a) + source.slice(b)).replace(art, art + '\n    const ft = f.hp > 0 ? tags(f) : []; if (ft.length) statusPill(ft[0], f.x + f.size / 2 - 12, f.y + f.size - 7);');
  assert.notEqual(interleaved, source); assert.throws(() => { const s = session(320, "prism", interleaved); s.c.B.foes.forEach(f => { f.status = { poison: true }; }); s.draw(); assertAfterArt(s); }, assert.AssertionError);
  const labels = source.replace('  text("PARTY", statsX, 147, "#a0a8c0"); text("HP", hpRight - 12, 147, "#a8e0a0"); text("MP", mpRight - 12, 147, "#a0c8ff");', "");
  assert.notEqual(labels, source); assert.throws(() => { const s = session(320, "prism", labels); s.draw(); assertHud(s); }, assert.AssertionError);
  const large = source.replace('const statText = n => n > (compact ? 999 : 9999) ? (compact ? "999+" : "9999+") : String(n);', 'const statText = n => String(n);');
  assert.notEqual(large, source); assert.throws(() => { const s = session(256, "prism", large); s.c.party[0].hp = s.c.party[0].max = Number.MAX_SAFE_INTEGER; s.draw(); assertHud(s); }, assert.AssertionError);
});
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/); assert.ok(inline); new vm.Script(inline[1], { filename: "index.html inline" });
console.log("battle readability: " + checks + " focused groups passed; paint-command checks only, no runtime/asset acceptance");
