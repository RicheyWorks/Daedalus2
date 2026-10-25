// SPDX-License-Identifier: MIT
// node --max-old-space-size=128 tools/rpg_demo/formation_view_test.js
// Actual formation painter/preview/ORDER handler with canonical recruits, gear and spells.
// DOM-free command capture only; no app boot, assets, browser, storage, build or native runtime.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const parties = data("party").party, shops = data("interiors").interiors, spells = data("spells").spells, menus = data("menus").layouts;
const gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(shops[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const found = html.split(/\r?\n/).find(s => s.startsWith(prefix)); assert.ok(found, prefix); return found; }
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* Recruits:"), between("function recruitsFor(", "function recruitBeaten("),
  line("const atkOf ="), line("const defOf ="), line("const spellOf ="),
  between("let menu = null;", "function drawEquip("), between("const STATUS =", "function inflict("),
  between("function titlePrompt(", "function drawTitle("),
  "this.api = { start: () => { party = buildParty(); }, recruit, roster, atkOf, defOf, openMenu, menuTick, drawMenu, drawFormation, formationPreview, " +
  "party: () => party, reserve: () => reserve, menu: () => menu, chars: CHARS, " +
  "groups: (front, back) => { party = front; reserve = back; }, " +
  "snapshot: () => ({ party, reserve, bag, gold, menu, state: {...state, beaten:[...state.beaten], ways:[...state.ways]}, opened:[...opened], pressed }) };"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (error) { error.message = label + ": " + error.message; throw error; } }
function session(width = 320, realm = "prism", production = source, labels = null) {
  const draws = [], sounds = [], c = { D: { realm_key: realm, party: clone(parties[realm]), gear: clone(gear), menus: clone(menus[realm]),
      spells: clone(spells.filter(s => s.realm === realm && (s.tier <= 2 || parties[realm].members.some(m => m.spells.includes(s.name))))), rects: { sprites: {} },
      ...(realm === "portal" ? { realm_profile: { start_level: 1 } } : {}) },
    W: width, H: 224, pressed: {}, B: null, mode: "field", map: { kind: "town" },
    state: { beaten: new Set(), seen: {}, fish: {}, quests: {}, ways: new Set(), day: 1, minute: 480, air: null, returnTo: null }, opened: new Set(["existing/chest"]),
    PAD: labels ? { devices: () => [{index:2}], label: action => labels[action] } : null,
    Math: Object.assign(Object.create(Math), { random() { throw new Error("formation cannot consume RNG"); } }),
    sfx: value => sounds.push(value), clamp: (n,a,b) => Math.max(a,Math.min(b,n)), tw: value => String(value).toUpperCase().length * 6,
    drawField() {}, shardCount: () => 0, clockText: () => "D1 08:00", isNight: () => false,
    text: (value,x,y,color="#ffffff") => draws.push({kind:"text",value:String(value).toUpperCase(),x,y,color,w:String(value).toUpperCase().length*6,h:8}),
    cursor: (x,y) => draws.push({kind:"cursor",x,y}), win: (x,y,w,h) => draws.push({kind:"window",x,y,w,h}),
    gauge: (x,y,w,fraction,color) => draws.push({kind:"gauge",x,y,w,h:5,fraction,color}),
    spr: (sheet,name,x,y,sx,sw,sh,scale) => { const r=c.D.rects.sprites[name] || [0,0,64,64]; draws.push({kind:"sprite",name,x,y,w:r[2]*scale,h:r[3]*scale}); },
    g: { fillStyle:"", fillRect(x,y,w,h) { draws.push({kind:"rect",x,y,w,h,color:this.fillStyle}); } },
    saveGame() { throw new Error("formation cannot save"); }, toast() { throw new Error("formation cannot toast"); },
    localStorage: { getItem() { throw new Error("formation cannot read storage"); }, setItem() { throw new Error("formation cannot write storage"); } }
  };
  for (const member of c.D.party.members) c.D.rects.sprites["Party_"+member.job]=[0,0,64,64];
  vm.createContext(c); vm.runInContext(production,c,{timeout:1000}); c.api.start();
  return {c,api:c.api,draws,sounds,
    tick(...keys) { keys.forEach(k=>{c.pressed[k]=true;}); c.api.menuTick(); },
    enter() { c.api.openMenu(); c.api.menu().idx=4; this.tick("a"); assert.equal(c.api.menu().sub,"order"); return this; },
    draw() { draws.length=0; const before=JSON.stringify(c.api.snapshot()), soundCount=sounds.length; c.api.drawMenu();
      assert.equal(JSON.stringify(c.api.snapshot()),before,"drawing leaves roster/resources/input/progress unchanged"); assert.equal(sounds.length,soundCount); return draws; }
  };
}
function earned(s) { for (const name of ["Cinder Forge","Windcut Aerie","Sunwell Sanctum","Gearwright's Folly"]) s.api.recruit(name); assert.equal(s.api.roster().length,8); return s; }
function memberState(s) { return JSON.stringify(s.api.roster().map(m=>({job:m.job,value:m})).sort((a,b)=>a.job.localeCompare(b.job))); }
function progress(s) { const snap=s.api.snapshot(); return JSON.stringify({bag:snap.bag,gold:snap.gold,state:snap.state,opened:snap.opened}); }
function preview(s) { const before=JSON.stringify(s.api.snapshot()), front=s.api.party(), back=s.api.reserve(), people=s.api.roster(); const result=s.api.formationPreview();
  assert.equal(JSON.stringify(s.api.snapshot()),before,"preview is read-only"); assert.equal(s.api.party(),front); assert.equal(s.api.reserve(),back);
  s.api.roster().forEach((m,i)=>assert.equal(m,people[i])); return result;
}
const textAt = (s,y) => s.draws.find(d=>d.kind==="text"&&d.x===12&&d.y===y);
function assertBounds(s) {
  assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="FORMATION"),"Prism ORDER dispatches the dedicated formation view");
  for (const d of s.draws) {
    if (d.kind==="text") { assert.ok(d.x>=0&&d.y>=0&&d.x+d.w<=s.c.W&&d.y+d.h<=s.c.H,"text fits: "+d.value);
      for (const ch of d.value) assert.ok(s.api.chars.includes(ch),"supported glyph: "+ch); }
    if (["window","rect","sprite","gauge"].includes(d.kind)) assert.ok(d.x>=0&&d.y>=0&&d.x+d.w<=s.c.W&&d.y+d.h<=s.c.H,"paint rectangle fits");
  }
}
function swapCase(pick,target,labelPattern,color) {
  const s=earned(session()).enter(), people=s.api.roster(), members=memberState(s), saved=progress(s);
  s.api.menu().ii=pick; s.tick("a"); assert.equal(s.api.menu().pick,pick); s.api.menu().ii=target;
  const p=preview(s); assert.match(p.text,labelPattern); assert.equal(p.color,color);
  s.draw(); assert.equal(textAt(s,200).value,p.text.toUpperCase());
  const expected=people.slice(); [expected[pick],expected[target]]=[expected[target],expected[pick]];
  s.tick("a"); assert.equal(s.api.menu().pick,-1); assert.equal(s.api.menu().msg,"ORDER CHANGED.");
  s.api.roster().forEach((m,i)=>assert.equal(m,expected[i])); assert.equal(memberState(s),members); assert.equal(progress(s),saved);
}
for (const width of [320,256]) check("all eight canonical roles and selected facts at "+width,()=>{
  const s=earned(session(width)).enter(); assert.equal(s.api.party().length,4); assert.equal(s.api.reserve().length,4);
  for (let i=0;i<8;i++) { s.api.menu().ii=i; const m=s.api.roster()[i]; s.draw(); assertBounds(s);
    assert.equal(textAt(s,164).value,m.name.toUpperCase()+" - "+m.job.toUpperCase());
    assert.equal(textAt(s,176).value,"HP "+m.hp+" MP "+m.mp+" ATK "+s.api.atkOf(m)+" DEF "+s.api.defOf(m));
    assert.equal(textAt(s,188).value,"MAGIC: "+(m.spells.length?m.spells.join(", ").toUpperCase():"NONE"));
    const x=i<4?48:width/2+48,y=54+(i%4)*24;
    assert.ok(s.draws.some(d=>d.kind==="text"&&d.x===x&&d.y===y+10&&d.value===m.job.toUpperCase()));
    assert.ok(s.draws.some(d=>d.kind==="cursor"&&d.x===(i<4?10:width/2+10)&&d.y===y));
  }
});
for (const width of [320,256]) check("known-spell overflow keeps exact prefix and +N at "+width,()=>{
  const s=earned(session(width)).enter(), m=s.api.roster().find(m=>m.job==="Runecaster");
  // Projected non-ally lessons use the existing Runecaster shop recipient rule.
  m.spells=s.c.D.spells.filter(sp=>sp.target!=="ally").map(sp=>sp.name); s.api.menu().ii=s.api.roster().indexOf(m); s.draw(); assertBounds(s);
  const value=textAt(s,188).value, match=value.match(/^MAGIC: (.+) \+(\d+)$/); assert.ok(match);
  const shown=match[1].split(", "); assert.deepEqual(shown,Array.from(m.spells.slice(0,shown.length),x=>x.toUpperCase()));
  assert.equal(+match[2],m.spells.length-shown.length); assert.ok(shown.length>0&&shown.length<m.spells.length);
});
check("first pick has a supported visible X and preview changes nothing",()=>{
  const s=earned(session()).enter(); s.api.menu().ii=7; s.tick("a"); const before=memberState(s); s.draw(); assertBounds(s);
  assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="X"&&d.x===170&&d.y===136)); assert.ok(!s.draws.some(d=>d.kind==="text"&&d.value==="*"));
  preview(s); assert.equal(memberState(s),before);
});
check("reserve-in preview matches actual second-Confirm swap",()=>swapCase(0,7,/^IN: Brannoc \/ OUT: Corin$/,"#78f8a0"));
check("reverse pick order gives the same reserve-in result",()=>swapCase(7,0,/^IN: Brannoc \/ OUT: Corin$/,"#78f8a0"));
check("front-only reorder preview matches the existing transaction",()=>swapCase(0,1,/^SWAP: Corin \/ Ysolde$/,"#fff070"));
check("reserve-only reorder preview matches the existing transaction",()=>swapCase(4,7,/^SWAP: Fennick \/ Brannoc$/,"#fff070"));
check("self pick retains the same four-front roster",()=>swapCase(3,3,/^KEEP Rook IN PLACE\.$/,"#fff070"));
check("standing-front refusal is previewed and commit keeps all members/resources",()=>{
  const s=earned(session()).enter(); s.api.party().forEach((m,i)=>{m.hp=i===0?1:0;}); s.api.reserve()[3].hp=0;
  s.api.menu().ii=0;s.tick("a");s.api.menu().ii=7;const before=s.api.roster(),members=memberState(s),saved=progress(s);
  const p=preview(s);assert.match(p.text,/SOMEONE STANDING/);assert.equal(p.color,"#f87878");s.tick("a");
  assert.equal(s.api.menu().msg,p.text);assert.equal(s.api.menu().pick,-1);s.api.roster().forEach((m,i)=>assert.equal(m,before[i]));assert.equal(memberState(s),members);assert.equal(progress(s),saved);
});
check("living reserve can replace a downed front member",()=>{
  const s=earned(session()).enter();s.api.party().forEach(m=>{m.hp=0;});const incoming=s.api.reserve()[3];s.api.menu().ii=0;s.tick("a");s.api.menu().ii=7;
  assert.equal(preview(s).color,"#78f8a0");s.tick("a");assert.equal(s.api.party()[0],incoming);assert.ok(s.api.party().some(m=>m.hp>0));
});
check("Back plus Confirm cancels selection then exits without a leaked swap/reopen",()=>{
  const s=earned(session()).enter();s.api.menu().ii=0;s.tick("a");s.api.menu().ii=7;const before=memberState(s),saved=progress(s);
  s.tick("b","a");assert.equal(s.api.menu().sub,"order");assert.equal(s.api.menu().pick,-1);assert.equal(!!s.c.pressed.a,false);s.tick();
  assert.equal(memberState(s),before);assert.equal(progress(s),saved);s.tick("b","a");assert.equal(s.api.menu().sub,null);s.tick();assert.equal(s.api.menu().sub,null);assert.equal(memberState(s),before);
});
for (const width of [320,256]) check("legacy three-front roster scrolls five reserves and previews normalization at "+width,()=>{
  const s=earned(session(width)), people=s.api.roster();s.api.groups(people.slice(0,3),people.slice(3));s.enter();
  s.api.menu().ii=7;s.draw();assertBounds(s);assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="2-5/5"));
  s.tick("a");s.api.menu().ii=0;s.draw();assertBounds(s);assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="X"&&d.x===width/2+10&&d.y===136));
  s.tick("b");s.api.menu().ii=0;s.tick("a");assert.match(preview(s).text,/^FRONT AFTER: 4 MEMBERS\.$/);
  s.tick("a");assert.equal(s.api.party().length,4);assert.equal(s.api.reserve().length,4);s.api.roster().forEach((m,i)=>assert.equal(m,people[i]));
});
for (const width of [320,256]) check("accepted long names/large values and physical help fit at "+width,()=>{
  const s=earned(session(width,"prism",source,{confirm:"ABCDEFGH",cancel:"12345678"})).enter(),m=s.api.party()[0];
  m.name="L".repeat(64);m.hp=m.max=m.mp=m.mmax=Number.MAX_SAFE_INTEGER;m.st.str=m.st.vit=Number.MAX_SAFE_INTEGER;s.api.menu().ii=0;
  s.draw();assertBounds(s);assert.equal(textAt(s,176).value,"HP 9999+ MP 999+ ATK 999+ DEF 999+");
  assert.match(textAt(s,212).value,/ABCDEFGH PICK 12345678 BACK$/);s.tick("a");s.draw();assertBounds(s);assert.match(textAt(s,212).value,/ABCDEFGH SWAP 12345678 BACK$/);
  s.api.menu().ii=7;s.draw();assertBounds(s);
});
check("empty reserve, downed portrait and missing sprite are readable",()=>{
  const s=session().enter(),m=s.api.party()[0];m.hp=0;delete s.c.D.rects.sprites[m.sprite];s.draw();assertBounds(s);
  assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="NO RESERVES YET."));assert.ok(s.draws.some(d=>d.kind==="text"&&d.value===m.name.toUpperCase()&&d.color==="#f87878"));
});
check("Portal ORDER keeps its original menu/party view and swap rule",()=>{
  const s=session(256,"portal").enter(),before=s.api.roster();s.draw();assert.ok(!s.draws.some(d=>d.kind==="text"&&d.value==="FORMATION"));
  assert.ok(s.draws.some(d=>d.kind==="text"&&d.value==="ORDER"));s.api.menu().ii=0;s.tick("a");s.api.menu().ii=1;s.tick("a");assert.equal(s.api.party()[0],before[1]);assert.equal(s.api.party()[1],before[0]);
});
check("controlled former generic ORDER rendering lacks the formation decision view",()=>{
  const gate=line('  if (sub === "order" &&');assert.ok(source.includes(gate));const previous=source.replace(gate,"");
  const s=earned(session(320,"prism",previous)).enter();s.draw();assert.throws(()=>assertBounds(s),assert.AssertionError);
});
const inline=html.match(/<script>\s*([\s\S]*?)<\/script>/);assert.ok(inline);new vm.Script(inline[1],{filename:"index.html:inline"}); // Compile only.
console.log("Prismheart formation view: "+checks+" focused groups passed; DOM-free paint/handler checks only.");
